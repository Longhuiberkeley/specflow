# Quantitative Research Domain Checklist

Questions for systematic trading, prediction markets, sports analytics, and ML-for-finance alike. Quant work mixes *software you can specify* with *edge you can only measure* — the concept→artifact map below keeps the two apart.

## Concept → Artifact Map (quant)

The single most useful reference for this domain. Pick the artifact by what the concept *is*, not by gut:

| Concept | Right artifact | Why |
|---|---|---|
| Desired profit / edge / Sharpe / ROI | **autoresearch goal + metric** (`COMP.metric_name`) | Not testable software behaviour — it's a measured outcome. Never a REQ. |
| "No lookahead bias" / data leakage | **REQ** (non-functional) + `leakage_audit` lens | A testable property of the code/feature pipeline. |
| Reproducibility / seed control / frozen runs | **REQ** + autoresearch EXPT fingerprinting | A verifiable property; experiments must re-produce. |
| Scraper / data pipeline / feature store code | **STORY** (implements) + **ARCH** (the component) | Implementable work and its structure. |
| A single offline training/backtest run | **EXPT** (autoresearch) | Frozen, reproducible result. |
| Ephemeral live capture (quotes, prices, or events only available briefly) | **RUN** + **MONITOR** (ops pack) | Not reproducible — its own memory class; MONITOR.captures records what you grabbed + freshness. |
| A deployed model/bot going live | **RUN** (ops pack) | Deployment frozen at deploy-time; `derives_from` the EXPT/REQ it promotes/satisfies. |
| Performance / drift over time | **MONITOR** (ops pack) with `signals` | Append-only journal; drift is one signal type among many. |
| "Retrain when oos_decay > X" / kill-switch | **REQ** (threshold) + MONITOR breach → new LOOP with `derives_from MON-NNN` | The threshold is specifiable; the trigger fires via monitoring. |

Rule of thumb: *can you write a test that fails if it's wrong?* → REQ/STORY/EXPT. *Is it a number you're trying to move?* → autoresearch metric. *Does it only exist while running?* → RUN/MONITOR.

## Data reality

1. **What is the data?** Source, how far back, granularity?
2. **Point-in-time vs snapshot?** Is point-in-time integrity maintained (including delisted/removed instruments, markets, or entities), or is this a current-only snapshot?
3. **Granularity & alignment?** How are instruments/markets/entities time-aligned for joins?

## Split & leakage

1. **How is the train/validation/test split (or rolling/walk-forward) chosen, and is that choice itself validated?**
2. **Is OOS genuinely untouched?** Any normalisation or statistics fit on the full series?

## Costs

1. **Are fees, spread, slippage, and market impact modelled, and does the claimed edge survive them?**

## Regime robustness

1. **Does the result hold across market regimes, time periods, and liquidity conditions?**

## Multiple testing

1. **How many configurations were searched, and is the reported number adjusted for that search?** (e.g., deflated/adjusted metrics)
