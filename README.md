# Cont-Kukanov SOR Simulator

This project implements a backtesting and optimization framework for a Smart Order Router (SOR), based on the static cost model introduced by Cont & Kukanov in “Optimal Order Placement in Limit Order Markets.” The goal is to optimally route a 5,000-share buy order across multiple venues in a way that minimizes execution cost — while accounting for market depth, execution risk, and queue penalties.

Project Structure:
backtest.py
The main script that handles everything:

Cleans and parses the raw Level-1 market data (l1_day.csv)

Constructs one venue snapshot per timestamp

Implements the exact allocator logic provided in allocator_pseudocode.txt

Performs a full backtest of the static SOR across all timestamps

Tunes three key risk parameters via a grid search

Outputs performance metrics and the optimal parameter set in JSON format

The script runs efficiently and only depends on numpy, pandas, and the Python standard library.


Parameter Tuning Strategy:
I used a basic grid search over three parameters:

Parameter	Values Searched
lambda_over	0.1, 0.5, 1.0
lambda_under	0.1, 0.5, 1.0
theta_queue	0.0, 0.01, 0.05

This produces 27 combinations, all of which are tested across the 9-minute historical data window. The combination that results in the lowest total cost is selected as the best configuration.

Suggested Realism Improvement:
Right now, the model assumes we can always fill up to the displayed size, which isn't always realistic. A worthwhile improvement would be to incorporate queue position-based slippage — for example:

Assign a probability of fill based on position in the order book queue.

Adjust execution volume dynamically based on observed outflows or historical fill rates.

Penalize allocations more heavily when they rely on deep or unlikely-to-fill sizes.

This would help the allocator make more conservative and realistic decisions, particularly under uncertain or competitive market conditions.

