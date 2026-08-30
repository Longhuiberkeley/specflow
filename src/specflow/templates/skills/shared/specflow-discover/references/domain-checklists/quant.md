# Quant / Algo-Betting Domain Checklist

Questions for systematic-trading, backtesting, and prediction-market / sports-betting projects. Quant work mixes *software you can specify* with *edge you can only measure* — the concept→artifact map below keeps the two apart.

## Concept → Artifact Map (quant)

The single most useful reference for this domain. Pick the artifact by what the concept *is*, not by gut:

| Concept | Right artifact | Why |
|---|---|---|
| Desired profit / edge / Sharpe / ROI | **autoresearch goal + metric** (`COMP.metric_name`) | Not testable software behaviour — it's a measured outcome. Never a REQ. |
| "No lookahead bias" / data leakage | **REQ** (non-functional) + `leakage_audit` lens | A testable property of the code/feature pipeline. |
| Reproducibility / seed control / frozen runs | **REQ** + autoresearch EXPT fingerprinting | A verifiable property; experiments must re-produce. |
| Scraper / data pipeline / feature store code | **STORY** (implements) + **ARCH** (the component) | Implementable work and its structure. |
| A single offline training/backtest run | **EXPT** (autoresearch) | Frozen, reproducible result. |
| Live odds / ephemeral data capture (only online briefly) | **RUN** + **MONITOR** (ops pack) | Not reproducible — its own memory class; MONITOR.captures records what you grabbed + freshness. |
| A deployed model/bot going live | **RUN** (ops pack) | Deployment frozen at deploy-time; `derives_from` the EXPT/REQ it promotes/satisfies. |
| Performance / drift over time | **MONITOR** (ops pack) with `signals` | Append-only journal; drift is one signal type among many. |
| "Retrain when oos_decay > X" / kill-switch | **REQ** (threshold) + MONITOR breach → new LOOP with `derives_from MON-NNN` | The threshold is specifiable; the trigger fires via monitoring. |

Rule of thumb: *can you write a test that fails if it's wrong?* → REQ/STORY/EXPT. *Is it a number you're trying to move?* → autoresearch metric. *Does it only exist while running?* → RUN/MONITOR.

## Data & Sourcing

1. **Data source?** "Historical bars/ticks, odds feeds, alternative data? Vendor API, scraped, or exchange direct? How far back?"
2. **Survivorship & look-ahead?** "Point-in-time data (no delisted/removed contestants), or current-only snapshot? Point-in-time is mandatory to avoid bias."
3. **Granularity & alignment?** "Tick/second/minute/daily? How are instruments/contests time-aligned for joins?"
4. **Costs modelled in data?** "Are fees, spread, slippage, and betting margin/vig present in the historical record, or applied in code?"

## Methodology (bias prevention)

5. **Train/val/out-of-sample split?** "Three-way split with OOS truly untouched? Walk-forward (rolling) or fixed cutoff? OOS is the only number that matters."
6. **Lookahead/leakage controls?** "Feature computation uses only data available at decision time? Any normalisation fit on the full series (leak)? Map this to a REQ + the `leakage_audit` lens."
7. **Transaction costs & slippage?** "Per-trade costs, market impact, slippage modelled realistically? Edge that vanishes after costs isn't edge."
8. **Multiple-comparisons guard?** "How many strategies/params were tried? Is the reported edge adjusted for the search (Bonferroni/PBO/deflated Sharpe)?"

## Validation & Robustness

9. **Walk-forward / regime robustness?** "Does edge hold across regimes (bull/bear, high/low liquidity, regular/postseason)? Or is it one regime?"
10. **Position sizing / risk?** "Fixed, Kelly-fractional, vol-targeted? What's the max drawdown assumption and the capital-at-risk limit?"
11. **Reproducibility?** "Can a fresh agent re-run the exact backtest from the EXPT fingerprint + parameters and get the same number? If not, it's not a result yet."

## Live Operations (Layer 2 & 3)

12. **What goes live?** "Which model/strategy is deployed, where (paper/broker/live), from which EXPT? → a **RUN** (ops pack)."
13. **What do you monitor?** "Live P&L vs backtest, fill rates, data-feed freshness, and drift signals (e.g. oos_decay). → periodic **MONITOR** entries."
14. **Retrain / kill triggers?** "What threshold (drawdown, drift, decay) triggers a retrain (new LOOP) or a kill-switch (retire the RUN)? Make the threshold a REQ; fire it from a MONITOR."
