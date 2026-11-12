# US macro historical-analog report (spec v1.0, phase P0)

**Data mode: REVISED data (latest FRED values) with rule-based release times; NOT point-in-time.** Every figure below comes from the latest-revised FRED history; release times are *rules* (labor: first Friday of the following month 08:30 ET; CPI: the 15th, conservative; fed funds: next day), not recorded vintage dates. Real point-in-time vintages and the walk-forward backtest are phase P1 and are **not available** in this report.

**As-of:** 2026-11-06 14:00:00-05:00.  **Market data:** S&P 500 price index (no dividends) from Yahoo Finance via yfinance; unofficial source, personal research use.

## 1. Current macro snapshot
| feature | value | unit | series_id | observation | release_timestamp_et |
|---|---|---|---|---|---|
| unrate_level | 4.10 | % | UNRATE | 2026-10-01 | 2026-11-06 08:30:00-05:00 |
| unrate_chg_6m | -0.20 | pp | UNRATE | 2026-10-01 | 2026-11-06 08:30:00-05:00 |
| payroll_growth_3m | 0.26 | % of employment | PAYEMS | 2026-10-01 | 2026-11-06 08:30:00-05:00 |
| payroll_growth_6m | 0.31 | % of employment | PAYEMS | 2026-10-01 | 2026-11-06 08:30:00-05:00 |
| cpi_yoy | 3.72 | % YoY | CPIAUCSL | 2026-09-01 | 2026-10-15 08:30:00-04:00 |
| core_cpi_yoy | 2.57 | % YoY | CPILFESL | 2026-09-01 | 2026-10-15 08:30:00-04:00 |
| core_cpi_6m_ann | 2.85 | % annualised | CPILFESL | 2026-09-01 | 2026-10-15 08:30:00-04:00 |
| ffr_level | 3.88 | % | DFF | 2026-11-04 | next-day rule (daily series) |
| ffr_chg_6m | 0.24 | pp | DFF | 2026-11-04 | next-day rule (daily series) |

Official cross-check: not independently verified (bls.gov blocks scripted access, HTTP 403); values are FRED's. Where the rule says a report should be out but FRED lacks it, the table shows the observation actually used. The snapshot uses labor data for 2026-10 and CPI for 2026-09: they are different months because the October CPI is not yet published.

## 2. Five closest historical month-ends (de-duplicated: at least 18 months apart)
Distance D = 0.40·D_employment + 0.30·D_inflation + 0.30·D_policy; each D_group is the mean squared median/IQR-standardised difference of its features. Scanned 813 month-end signals (1958-02 to 2025-10); the scan covers every eligible month, no period is hard-coded.
| signal | unemp % | unemp 6m chg pp | payroll 3m % | payroll 6m % | CPI yoy % | core yoy % | FFR % | FFR 6m chg pp | ZLB | D | D emp | D infl | D policy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-07 | 4.10 | 0.00 | 0.06 | 0.10 | 2.68 | 2.91 | 4.33 | 0.00 |  | 0.05 | 0.07 | 0.05 | 0.02 |
| 2007-06 | 4.40 | -0.10 | 0.31 | 0.68 | 2.71 | 2.27 | 5.31 | 0.14 |  | 0.05 | 0.05 | 0.07 | 0.05 |
| 2000-10 | 3.90 | -0.10 | 0.21 | 0.56 | 3.46 | 2.53 | 6.59 | 0.53 |  | 0.07 | 0.03 | 0.01 | 0.20 |
| 2019-01 | 3.90 | -0.10 | 0.30 | 0.57 | 2.00 | 2.25 | 2.40 | 0.49 |  | 0.08 | 0.03 | 0.16 | 0.07 |
| 2023-12 | 3.70 | 0.10 | 0.28 | 0.67 | 3.13 | 4.02 | 5.33 | 0.25 |  | 0.09 | 0.10 | 0.12 | 0.05 |

## 3. S&P 500 price outcomes after those signals (not used for selection)
| signal | R 3m % | R 6m % | R 12m % | MDD 12m % | worst vs entry % | MDD trough date | DD>=10% | DD>=20% |
|---|---|---|---|---|---|---|---|---|
| 2025-07 | +7.9 | +9.5 | +18.1 | -9.1 | -1.6 | 2026-03-30 | no | no |
| 2007-06 | +1.6 | -2.3 | -14.9 | -18.6 | -15.3 | 2008-03-10 | yes | no |
| 2000-10 | -4.4 | -12.6 | -25.9 | -32.6 | -32.4 | 2001-09-21 | yes | yes |
| 2019-01 | +8.9 | +10.2 | +19.3 | -6.8 | 0.0 | 2019-06-03 | no | no |
| 2023-12 | +10.2 | +14.5 | +23.3 | -8.5 | -1.7 | 2024-08-05 | no | no |

Five cases is a small, partly clustered sample. 12-month return: mean +4.0%, median +18.1%, range -25.9% to +23.3%. For reference, across all 813 candidate months the median is +10.6% and 75% are positive. These are descriptive; they are not a forecast and not a probability.

## 4. Raw top 20 (no de-duplication)
| rank | signal | D | R 12m % | MDD 12m % |
|---|---|---|---|---|
| 1 | 2025-07 | 0.05 | +18.1 | -9.1 |
| 2 | 2007-06 | 0.05 | -14.9 | -18.6 |
| 3 | 2006-09 | 0.06 | +14.3 | -9.4 |
| 4 | 2007-01 | 0.06 | -4.2 | -16.3 |
| 5 | 2007-04 | 0.06 | -6.5 | -18.6 |
| 6 | 2025-06 | 0.06 | +20.9 | -9.1 |
| 7 | 2007-03 | 0.07 | -6.9 | -18.6 |
| 8 | 2006-10 | 0.07 | +12.4 | -9.4 |
| 9 | 2006-12 | 0.07 | +3.5 | -10.1 |
| 10 | 2000-10 | 0.07 | -25.9 | -32.6 |
| 11 | 2024-05 | 0.08 | +12.0 | -18.9 |
| 12 | 2019-01 | 0.08 | +19.3 | -6.8 |
| 13 | 2025-05 | 0.08 | +28.2 | -9.1 |
| 14 | 2006-08 | 0.08 | +13.1 | -9.4 |
| 15 | 2006-07 | 0.08 | +14.0 | -6.3 |
| 16 | 2019-05 | 0.08 | +10.6 | -33.9 |
| 17 | 2018-11 | 0.09 | +13.8 | -15.7 |
| 18 | 2000-11 | 0.09 | -13.3 | -30.0 |
| 19 | 2006-11 | 0.09 | +5.7 | -10.1 |
| 20 | 2025-03 | 0.09 | +16.3 | -12.1 |

Median 12-month return of the raw top 20: +12.2%; share positive: 70%. Adjacent months cluster into a few episodes, which is why the de-duplicated list above exists.

## 5. Limits of this version
- Revised data and rule-based release times only. Early-period figures include later revisions (and seasonal-factor changes) that were not known then.
- Zero-lower-bound months are flagged (effective rate below 0.3%), but QE periods are not separately flagged, and no shadow-rate sensitivity is run.
- No sensitivity analysis (weights, trend windows, excluding crisis periods), no out-of-sample backtest, no benchmark comparison: phase P1.
- Background for each analog (NBER status, shocks, valuation, politics) is not included; it needs verified sources and is explanation only.
- Missing observations (for example October 2025 unemployment and CPI) are left blank and any signal needing them is excluded.

## 6. Acceptance checks on this run
| name | passed | detail |
|---|---|---|
| snapshot_uses_only_data_released_by_as_of | PASS | as_of=2026-11-06 14:00:00-05:00; violations=[] |
| every_historical_signal_uses_only_data_released_by_its_clock | PASS | violations=0 |
| features_exclude_politics_valuation_and_market_returns | PASS | features=['unrate_level', 'unrate_chg_6m', 'payroll_growth_3m', 'payroll_growth_6m', 'cpi_yoy', 'core_cpi_yoy', 'core_cpi_6m_ann', 'ffr_level', 'ffr_chg_6m'] |
| weights_sum_to_one | PASS | {'employment': 0.4, 'inflation': 0.3, 'policy': 0.3} |
| no_missing_values_in_candidate_features | PASS | 813 candidates |
| distance_decomposes_into_group_distances | PASS | D == sum_g w_g * D_g |
| top_picks_respect_min_gap | PASS | min pairwise gap=19 months (required 18) |
| raw_top_list_has_no_dedup | PASS |  |
| all_candidate_outcomes_fully_realised | PASS | last price 2026-11-06 |
| candidates_are_not_hardcoded_periods | PASS | 813 month-end signals scanned: 1958-02 to 2025-10 |
| latest_candidate_precedes_current_signal | PASS | latest candidate 2025-10 |

