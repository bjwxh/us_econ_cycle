# macro_analog_research

Implements `us_macro_historical_analog_research_spec.md` v1.0, **phase P0**: match today's US employment / inflation / policy-rate state to every past month-end, then show what the S&P 500 did in the 12 months after the closest matches.

## Run
```bash
pip install -r <(python3 -c "import tomllib;print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))")   # or install pandas numpy matplotlib pyyaml yfinance pyarrow
cd macro_analog_research
PYTHONPATH=src python3 -m macro_analog.cli snapshot     --as-of 2026-11-06T14:00:00-05:00
PYTHONPATH=src python3 -m macro_analog.cli find-analogs --top-k 5 --min-gap-months 18
PYTHONPATH=src python3 -m macro_analog.cli outcomes     --horizon-months 12
PYTHONPATH=src python3 -m macro_analog.cli report        # everything + acceptance checks + report.md
PYTHONPATH=src python3 -m pytest -q tests
```
Options: `--as-of`, `--top-k`, `--min-gap-months`, `--horizon-months`, `--weights 40,30,30`, `--refresh` (re-download; old raw files are kept), `--out-dir`. Defaults live in `config/default.yaml`. `backtest` is a P1 placeholder and exits with "not available".

## What it is, and is not
- **Data mode: revised data with rule-based release times, not point-in-time.** Labor data are usable from the first Friday of the next month, CPI from the 15th, the daily fed funds rate from the next day. These are rules, not recorded release dates; real vintages (ALFRED, needs a `FRED_API_KEY`) are P1.
- Features: unemployment level and 6-month change; payroll growth over 3 and 6 months (% of the earlier level); CPI and core CPI year over year, core CPI 6-month annualised; effective fed funds (`DFF`) level and 6-month change. Median/IQR scaling is fitted on the candidate pool only.
- `D = 0.40*D_employment + 0.30*D_inflation + 0.30*D_policy`; each group distance is the mean of its features' squared standardised differences.
- Politics, valuation, tech weights and market returns are never inputs to matching.
- Missing observations stay blank; any signal needing one is excluded.
- S&P 500 data: Yahoo Finance via yfinance (unofficial; price index, no dividends). BLS pages return HTTP 403 to scripts, so snapshot values are FRED's and are marked "not independently verified".

## Outputs (`outputs/`)
`current_macro_snapshot.csv`, `analog_top5.csv`, `analog_top20_raw.csv`, `sp500_outcomes.csv`, `analog_paths.png/pdf`, `sp500_outcomes.png/pdf`, `validation.json`, `provenance.json`, `report.md`. Raw downloads and their log are in `data/raw/` (append-only); full candidate tables in `data/processed/`.

## Not yet done (P1/P2)
Point-in-time vintages and release calendar, walk-forward backtest and benchmarks, sensitivity analysis (weights, trend windows, excluding crisis periods, shadow rate), PCE alternative, background annotations (NBER, shocks, valuation, politics).
