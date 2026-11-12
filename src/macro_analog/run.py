"""P0 pipeline (Revised-history mode): python -m macro_analog.run [--as-of 2026-11-10]

Signal convention: features for observation month m are used with a signal date = last trading
day of month m+1 (m's payrolls/CPI are published during m+1, so nothing is look-ahead).
Candidate pool = months whose full 12m outcome is realized, with signal date >= 1990-01.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

import pandas as pd

from . import ingest
from .analogs import dedup, distances
from .features import FEATURES, GROUPS, build_features, load_series
from .market import load_spx, outcome, month_end_day
from .plots import plot_macro_paths, plot_outcomes

ROOT = ingest.ROOT
BASE = {"unrate": "UNRATE", "unrate_chg6": "UNRATE", "pay_g3": "PAYEMS", "pay_g6": "PAYEMS",
        "cpi_ann6": "CPIAUCSL", "core_ann6": "CPILFESL", "ff": "FEDFUNDS", "ff_chg6": "FEDFUNDS"}
WEIGHT_SETS = {"40/30/30": (0.4, 0.3, 0.3), "33/33/33": (1 / 3, 1 / 3, 1 / 3), "50/25/25": (0.5, 0.25, 0.25)}


def md(df: pd.DataFrame, fmt="{:.2f}") -> str:
    d = df.reset_index() if df.index.name else df
    rows = ["| " + " | ".join(map(str, d.columns)) + " |", "|" + "---|" * len(d.columns)]
    for _, r in d.iterrows():
        rows.append("| " + " | ".join(fmt.format(v) if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default="2026-11-10")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--min-gap-months", type=int, default=18)
    ap.add_argument("--out", default=str(ROOT / "outputs" / "p0"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    w = dict(zip(GROUPS, WEIGHT_SETS["40/30/30"]))

    names = ["PAYEMS", "UNRATE", "CPIAUCSL", "CPILFESL", "FEDFUNDS"]
    rev = {n: load_series(ingest.latest(f"fred_{n}_revised")) for n in names}
    asof = {n: load_series(ingest.latest(f"fred_{n}_asof{a.as_of}")) for n in names}
    f_rev, f_asof = build_features(rev), build_features(asof)
    target_m = f_asof.index.max()
    target = f_asof.loc[target_m]
    assert not target[FEATURES].isna().any(), f"target {target_m} has missing features"

    # --- snapshot (as-of vintage) ---
    snap = pd.DataFrame({"value": target[FEATURES]})
    snap["base_series"] = [BASE[f] for f in FEATURES]
    snap["observation_month"] = str(target_m)
    snap["release_date"] = [ingest.first_release_date(BASE[f], f"{target_m}-01", a.as_of) for f in FEATURES]
    snap["data_vintage"] = f"ALFRED as of {a.as_of}"
    snap.index.name = "feature"
    snap.to_csv(out / "current_macro_snapshot.csv")

    # --- outcomes for every month, then the candidate pool ---
    spx = load_spx(ingest.latest("spx_schwab"))
    rows = {}
    for m in f_rev.index:
        if m + 1 >= spx.index[0].to_period("M"):
            o = outcome(spx, m + 1)
            if o:
                rows[m] = o
    outc = pd.DataFrame.from_dict(rows, orient="index")
    pool = f_rev.loc[outc.index].dropna(subset=FEATURES)
    pool = pool[pool.index != target_m]

    ranked = distances(pool[FEATURES], target, w)
    usrec = load_series(ingest.latest("fred_USREC_revised"))

    def decorate(df):
        d = df.join(outc[["signal_date", "end_date", "R_3m", "R_6m", "R_12m", "MDD_12m", "worst_from_entry",
                          "mdd_peak_date", "mdd_trough_date", "dd_ge_10", "dd_ge_20"]])
        d["nber_recession"] = [bool(usrec.get(m, 0) == 1) for m in d.index]
        d["zlb"] = d["ff"] < 0.25
        d.index = d.index.astype(str)
        d.index.name = "obs_month"
        return d

    top5 = decorate(dedup(ranked, a.top_k, a.min_gap_months))
    top20 = decorate(ranked.head(20))
    top5.to_csv(out / "analog_top5.csv")
    top20.to_csv(out / "analog_top20_raw.csv")
    top5[["signal_date", "end_date", "R_3m", "R_6m", "R_12m", "MDD_12m", "worst_from_entry",
          "mdd_peak_date", "mdd_trough_date", "dd_ge_10", "dd_ge_20"]].to_csv(out / "sp500_outcomes.csv")

    # --- weight sensitivity (matching only) ---
    sens = {}
    for name, ws in WEIGHT_SETS.items():
        r = distances(pool[FEATURES], target, dict(zip(GROUPS, ws)))
        sens[name] = ", ".join(map(str, dedup(r, a.top_k, a.min_gap_months).index))

    # --- plots ---
    months = [pd.Period(m) for m in top5.index]
    plot_macro_paths(f_rev, f_asof, target_m, months, str(out / "analog_paths"))
    paths, labels = [], []
    for m in months:
        o = outc.loc[m]
        paths.append(spx.loc[o["signal_date"]:o["end_date"]])
        labels.append(f"{m} -> signal {o['signal_date'].date()}  R12 {o['R_12m']:+.1%}  MDD {o['MDD_12m']:.1%}")
    plot_outcomes(paths, labels, str(out / "sp500_outcomes"))

    # --- provenance + report ---
    manifest = [json.loads(l) for l in open(ingest.RAW / "manifest.jsonl")]
    json.dump(dict(run_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(), as_of=a.as_of, mode="Revised (history) + ALFRED as-of vintage for the current snapshot",
                   params=dict(weights=w, top_k=a.top_k, min_gap_months=a.min_gap_months, features=FEATURES),
                   pool=dict(n=len(pool), first=str(pool.index.min()), last=str(pool.index.max())),
                   git_commit="not available (not a git repository)", raw_files=manifest),
              open(out / "provenance.json", "w"), indent=1)

    show = ["D", "contrib_employment", "contrib_inflation", "contrib_policy", "unrate", "pay_g3", "pay_g6",
            "cpi_ann6", "core_ann6", "ff", "ff_chg6", "nber_recession", "zlb"]
    oc = ["signal_date", "R_12m", "MDD_12m", "worst_from_entry", "mdd_trough_date", "dd_ge_10", "dd_ge_20"]
    fmt = lambda df: df.assign(**{c: df[c].dt.date for c in df.select_dtypes("datetime").columns})
    report = f"""# Macro analog research - P0 (Revised-history mode)

As-of: {a.as_of}. Current observation month: {target_m}. Pool: {len(pool)} months ({pool.index.min()} to {pool.index.max()}), only months with realized 12m S&P outcomes. Weights employment/inflation/policy = 40/30/30. No backtest yet (P1): nothing here is a validated forecast.

## Current snapshot
{md(snap.drop(columns="data_vintage"), "{:.3f}")}

CPI YoY is excluded by design: Oct 2025 CPI was never published, so Oct 2026 YoY has no base. Inflation uses 6-month annualized headline and core CPI.

## Top {a.top_k} analogs (>= {a.min_gap_months} months apart)
{md(top5[show], "{:.2f}")}

## Raw top 20 (no de-duplication)
{md(top20[show[:4] + ["unrate", "core_ann6", "ff"]], "{:.2f}")}

## S&P 500 price outcomes (entry = last trading day of month after observation month)
{md(fmt(top5[oc]), "{:.3f}")}

Mean R12: {top5['R_12m'].mean():+.1%}; median {top5['R_12m'].median():+.1%}; range {top5['R_12m'].min():+.1%} to {top5['R_12m'].max():+.1%}. Five overlapping-era cases: descriptive only, not a probability.

## Weight sensitivity (top 5 months)
{chr(10).join(f"- {k}: {v}" for k, v in sens.items())}

## Limits
Revised data, not point-in-time, for the history; price index only (no dividends); the SPX series is a single provider (Schwab) not yet cross-checked; shocks, valuation and policy regime differences are not modeled; this is description, not causal.
"""
    (out / "report.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
