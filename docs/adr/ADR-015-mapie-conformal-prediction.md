# ADR-015: MAPIE conformal prediction for calibrated forecast intervals

- **Status:** Accepted
- **Date:** 2026-04-25
- **Deciders:** mrsladoje + team
- **Related:** PRD §11.6, §6.4 FR-W.6, §17 M9b, §16.2; ADR-001 (Hybrid rule-based + PINN), ADR-006 (Three failure-model families)

## Context

Apollo's forecasts are the substrate of every interesting demo move: "the heater fails in 8 hours," "swap the blade now or lose batch X," "Universe C avoids cascade B at hour 6." All of those are point predictions emerging from rule-based decay equations and the heater PINN. A point prediction without an uncertainty band is rhetorically weak — judges from HP know that any forecast is a distribution, and a single number invites the "how confident are you" question we cannot answer with hand-waving.

We need a way to attach a calibrated `(lower, upper)` band to every health/RUL forecast that (a) does not require retraining the underlying predictors, (b) gives a *theoretical* coverage guarantee rather than a Bayesian heuristic, (c) costs under two hours to integrate, and (d) is empirically validatable on a held-out scenario inside the 36-hour budget. This need surfaced during the April 25 SOTA scan; it is a late add layered onto an already-shipped Phase 1.

## Decision

Adopt **MAPIE 1.3** (`scikit-learn-contrib`, Apr 2026) and wrap each per-component decay/PINN predictor with `MapieTimeSeriesRegressor` configured for **EnbPi** (Ensemble batch Prediction Intervals) with block bootstrap. EnbPi is built for sequential data and produces a `(point, lower, upper)` triple at each forecast horizon under a 95 % nominal coverage target.

We persist forecasts in a new `forecasts(run_id, t, component_id, horizon_min, point, lower, upper, ci_level)` table (PRD §14) and render them as a shaded Recharts `Area` band around the health curve. Empirical coverage is validated on the `Stressed` scenario as a held-out set; the demo gate is **≥ 90 % empirical coverage at 95 % nominal CI** (PRD §16.2). Pitch line: *"heater fails in 8.0 h ± 2.3 h, 95 % CI — guarantee, not guess."*

## Alternatives Considered

| Alternative | Why rejected |
| --- | --- |
| Monte Carlo dropout on the PINN | Only the heater is a neural net; gives no intervals for the five rule-based components. No coverage guarantee. |
| Bayesian neural network (variational / MCMC) | Days of retraining; instability on small synthetic data; only covers the heater. |
| Deep ensembles (5–10 PINN seeds) | 5× training cost, MPS compile thrash, only addresses one component, intervals are heuristic not calibrated. |
| Hand-set ±N % bands or rolling SD | Not calibrated; trivially attacked by a judge ("why ±15 %?"); empirically miscovers. |
| `nonconformist` / older split-conformal libs | No native time-series block-bootstrap; we'd hand-roll the sequential adaptation. |
| Quantile regression forests | Would replace, not wrap, our predictors; loses physics narrative; per-component retraining. |

## Consequences

**Positive:**
- Distribution-free coverage guarantee covering both rule-based and PINN forecasts via one library.
- Visually obvious wow factor — shaded bands narrow as data accumulates, widen under regime shift.
- Coverage check on `Stressed` is a measurable artifact for the technical report (NFR alignment with §16.2).
- Independent of the underlying predictor, so swapping the PINN for a fallback regressor (R-2) does not break intervals.

**Negative / accepted tradeoffs:**
- EnbPi block-bootstrap requires storing residuals; ~10 MB extra per run. Acceptable.
- Adds 1.5 h to the critical path (M9b). Mitigated by being the highest-ROI add and the *last* feature cut per §17.
- Coverage guarantee assumes exchangeability of residuals within a regime; under abrupt cascade onset the bands will *temporarily* under-cover. We disclose this in the technical report.

**Neutral / mitigations:**
- Forecast horizon capped at 60 simulated minutes to keep bands usefully tight; longer horizons render but with a visible widening.

## References

- PRD §11.6, §6.4 FR-W.6, §14 (`forecasts` table), §16.2, §17 M9b
- MAPIE: https://mapie.readthedocs.io/
- Xu & Xie, *Conformal Prediction Interval for Dynamic Time-Series* (EnbPi), ICML 2021
