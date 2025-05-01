import pandas as pd
import numpy as np
import json
from itertools import product

df = pd.read_csv("l1_day.csv")
df = df.sort_values("ts_event")

df = df.groupby(['ts_event', 'publisher_id'], as_index=False).first()

snapshots = {}
for ts, group in df.groupby('ts_event'):
    snapshot = {}
    for _, row in group.iterrows():
        snapshot[row['publisher_id']] = {
            'ask': row['ask_px_00'],
            'ask_size': row['ask_sz_00'],
            'fee': 0.0,
            'rebate': 0.0
        }
    snapshots[ts] = snapshot

def compute_cost(split, venues, order_size, λo, λu, θ):
    executed = 0
    cash_spent = 0
    for i, shares in enumerate(split):
        venue = venues[i]
        exe = min(shares, venue['ask_size'])
        executed += exe
        cash_spent += exe * (venue['ask'] + venue['fee'])
        rebate = max(shares - exe, 0) * venue['rebate']
        cash_spent -= rebate

    underfill = max(order_size - executed, 0)
    overfill = max(executed - order_size, 0)
    return cash_spent + θ * (underfill + overfill) + λu * underfill + λo * overfill

def allocate(order_size, venues, λo, λu, θ, step=100):
    N = len(venues)
    splits = [[]]

    for v in range(N):
        new_splits = []
        for alloc in splits:
            used = sum(alloc)
            max_v = min(order_size - used, venues[v]['ask_size'])
            for q in range(0, max_v + 1, step):
                new_splits.append(alloc + [q])
        splits = new_splits

    best_cost = float('inf')
    best_split = None
    for alloc in splits:
        if sum(alloc) != order_size:
            continue
        cost = compute_cost(alloc, venues, order_size, λo, λu, θ)
        if cost < best_cost:
            best_cost = cost
            best_split = alloc

    return best_split, best_cost

def run_backtest(snapshots, λo, λu, θ, order_size=5000):
    remaining = order_size
    executed = 0
    cash_spent = 0

    for ts in sorted(snapshots.keys()):
        if remaining <= 0:
            break
        venues_dict = snapshots[ts]
        venues = list(venues_dict.values())

        split, _ = allocate(remaining, venues, λo, λu, θ)

        if split is None:
            continue  

        fill = 0
        cost = 0
        for i, shares in enumerate(split):
            exe = min(shares, venues[i]['ask_size'])
            fill += exe
            cost += exe * (venues[i]['ask'] + venues[i]['fee'])

        executed += fill
        cash_spent += cost
        remaining -= fill

    avg_price = cash_spent / executed if executed else 0
    return cash_spent, avg_price


def baseline_best_ask(snapshots, order_size=5000):
    remaining = order_size
    cash_spent = 0
    executed = 0
    for ts in sorted(snapshots.keys()):
        best = None
        best_px = float('inf')
        for venue in snapshots[ts].values():
            if venue['ask_size'] > 0 and venue['ask'] < best_px:
                best = venue
                best_px = venue['ask']
        if not best: continue
        fill = min(best['ask_size'], remaining)
        cash_spent += fill * best['ask']
        executed += fill
        remaining -= fill
        if remaining <= 0:
            break
    avg = cash_spent / executed if executed else 0
    return cash_spent, avg

param_grid = product([0.01, 0.05, 0.1], [0.01, 0.05, 0.1], [0.0, 0.0005])

best_result = None
for λo, λu, θ in param_grid:
    spent, avg = run_backtest(snapshots, λo, λu, θ)
    if not best_result or spent < best_result['spent']:
        best_result = {
            'lambda_over': λo,
            'lambda_under': λu,
            'theta_queue': θ,
            'spent': spent,
            'avg': avg
        }

def calc_bps(base, smart):
    return round(10000 * (base - smart) / base, 2)

best_ask_spent, best_ask_avg = baseline_best_ask(snapshots)

output = {
    "best_params": {
        "lambda_over": best_result['lambda_over'],
        "lambda_under": best_result['lambda_under'],
        "theta_queue": best_result['theta_queue'],
    },
    "smart_router": {
        "cash_spent": round(best_result['spent'], 2),
        "avg_fill_price": round(best_result['avg'], 4)
    },
    "best_ask": {
        "cash_spent": round(best_ask_spent, 2),
        "avg_fill_price": round(best_ask_avg, 4),
        "savings_bps": calc_bps(best_ask_spent, best_result['spent'])
    }
}

print(json.dumps(output, indent=2))
