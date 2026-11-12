"""CLI.  Run from macro_analog_research/ :  PYTHONPATH=src python3 -m macro_analog.cli <command> [options]"""
import argparse
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import analogs, features as F, ingest, market, plots, validate
from .release_calendar import ET

ROOT = Path(__file__).resolve().parents[2]
MODE = "REVISED data (latest FRED values) with rule-based release times; NOT point-in-time"
SRC = {"unrate_level": ("UNRATE", "unrate_obs_month", "unrate_release_ts"),
       "unrate_chg_6m": ("UNRATE", "unrate_obs_month", "unrate_release_ts"),
       "payroll_growth_3m": ("PAYEMS", "labor_obs_month", "labor_release_ts"),
       "payroll_growth_6m": ("PAYEMS", "labor_obs_month", "labor_release_ts"),
       "cpi_yoy": ("CPIAUCSL", "cpi_obs_month", "cpi_release_ts"),
       "core_cpi_yoy": ("CPILFESL", "core_cpi_obs_month", "core_cpi_release_ts"),
       "core_cpi_6m_ann": ("CPILFESL", "core_cpi_obs_month", "core_cpi_release_ts"),
       "ffr_level": ("DFF", "ffr_obs_date", None), "ffr_chg_6m": ("DFF", "ffr_obs_date", None)}
UNITS = {"unrate_level": "%", "unrate_chg_6m": "pp", "payroll_growth_3m": "% of employment", "payroll_growth_6m": "% of employment",
         "cpi_yoy": "% YoY", "core_cpi_yoy": "% YoY", "core_cpi_6m_ann": "% annualised", "ffr_level": "%", "ffr_chg_6m": "pp"}


def load_cfg(a) -> dict:
    cfg = yaml.safe_load(open(ROOT / "config" / "default.yaml"))
    if a.as_of:
        cfg["as_of"] = a.as_of
    if getattr(a, "top_k", None):
        cfg["top_k"] = a.top_k
    if getattr(a, "min_gap_months", None):
        cfg["min_gap_months"] = a.min_gap_months
    if getattr(a, "horizon_months", None):
        cfg["horizon_months"] = a.horizon_months
    if getattr(a, "weights", None):
        w = [float(x) for x in a.weights.split(",")]
        cfg["weights"] = dict(zip(["employment", "inflation", "policy"], [x / sum(w) for x in w]))
    return cfg


def pipeline(cfg: dict, refresh: bool = False) -> dict:
    raw = ROOT / "data" / "raw"
    as_of = pd.Timestamp(cfg["as_of"]).tz_convert(ET)
    series, recs = {}, []
    for sid in ingest.FRED_META:
        series[sid], r = ingest.load_fred(sid, raw, refresh)
        recs.append(r)
    px, prec = ingest.load_spx(raw, refresh)
    px = px.loc[: as_of.tz_localize(None).normalize() + pd.Timedelta(days=1)]
    recs.append(prec)
    inp = F.prepare(series, cfg["release_rules"])
    last_month = as_of.tz_localize(None).replace(day=1) - pd.DateOffset(months=1)   # latest month already ended
    months = pd.date_range("1948-01-01", last_month, freq="MS")
    state = F.build_state_table(inp, months, cfg["zlb_threshold_pct"])
    current = F.state_at(as_of, inp, cfg["zlb_threshold_pct"])
    out = market.outcomes(px, months, cfg["horizon_months"])
    cand = state.loc[state.index.intersection(out.index)]
    pool = cand.dropna(subset=F.FEATURES)
    feats = [f for g in cfg["groups"].values() for f in g]
    scaler = analogs.fit_scaler(pool, feats)
    ranked = analogs.rank_candidates(pool, pd.Series(current), cfg["groups"], cfg["weights"], scaler)
    top5 = analogs.select_top(ranked, cfg["top_k"], cfg["min_gap_months"])
    raw_top = ranked.head(cfg["raw_top_n"])
    return dict(cfg=cfg, as_of=as_of, series=series, recs=recs, px=px, state=state, current=current, out=out, cand=cand, pool=pool,
                scaler=scaler, ranked=ranked, top5=top5, raw_top=raw_top)


def _join(R, idx):
    keep = F.FEATURES + ["real_rate_headline", "zlb_flag"]
    d = R["ranked"].loc[idx, ["D", *[f"D_{g}" for g in R["cfg"]["groups"]], *[f"z2_{f}" for f in F.FEATURES]]]
    d = R["pool"].loc[idx, keep].join(d)
    d = d.join(R["out"].loc[idx])
    d.index.name = "signal_month"
    return d


def emit_snapshot(R, out_dir):
    cur, recs = R["current"], {r["series_id"]: r for r in R["recs"]}
    rows = []
    for f in F.FEATURES:
        sid, om, rt = SRC[f]
        obs = cur[om]
        rows.append(dict(as_of=R["as_of"].isoformat(), feature=f, value=cur[f], unit=UNITS[f], series_id=sid,
                         observation=str(pd.Timestamp(obs).date()) if pd.notna(obs) else "missing",
                         release_timestamp_et=str(cur[rt]) if rt else "next-day rule (daily series)",
                         release_time_basis="rule-based (not a recorded release time)",
                         source_url=recs[sid]["source_url"], downloaded_at_utc=recs[sid]["downloaded_at_utc"],
                         official_check="not independently verified: bls.gov returns HTTP 403 to scripts; value is FRED's"))
    snap = pd.DataFrame(rows)
    snap.to_csv(out_dir / "current_macro_snapshot.csv", index=False)
    return snap


def emit_analogs(R, out_dir):
    t5, t20 = _join(R, R["top5"].index), _join(R, R["raw_top"].index)
    t5.to_csv(out_dir / "analog_top5.csv")
    t20.to_csv(out_dir / "analog_top20_raw.csv")
    R["ranked"].to_csv(ROOT / "data" / "processed" / "all_candidates_ranked.csv")
    return t5, t20


def emit_outcomes(R, out_dir):
    idx = R["top5"].index.union(R["raw_top"].index)
    o = R["out"].loc[idx].copy()
    o["in_top5"], o["in_raw_top20"] = o.index.isin(R["top5"].index), o.index.isin(R["raw_top"].index)
    o.to_csv(out_dir / "sp500_outcomes.csv")
    R["out"].to_csv(ROOT / "data" / "processed" / "all_candidate_outcomes.csv")
    plots.plot_macro_paths(R["state"], R["current"], R["top5"], out_dir, MODE)
    plots.plot_outcomes(R["px"], R["top5"], R["out"], R["out"].loc[R["pool"].index], R["raw_top"], out_dir, R["cfg"]["horizon_months"])
    return o


def _md(df: pd.DataFrame) -> str:
    h = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
    return h + "\n".join("| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False)) + "\n"


def emit_report(R, out_dir, snap, t5, t20, checks):
    cfg, P = R["cfg"], R["pool"]
    H = cfg["horizon_months"]
    f1 = lambda v: f"{v:.2f}"
    top = t5.reset_index()
    tab5 = pd.DataFrame({"signal": top.signal_month.dt.strftime("%Y-%m"), "unemp %": top.unrate_level.map(f1), "unemp 6m chg pp": top.unrate_chg_6m.map(f1),
                         "payroll 3m %": top.payroll_growth_3m.map(f1), "payroll 6m %": top.payroll_growth_6m.map(f1), "CPI yoy %": top.cpi_yoy.map(f1),
                         "core yoy %": top.core_cpi_yoy.map(f1), "FFR %": top.ffr_level.map(f1), "FFR 6m chg pp": top.ffr_chg_6m.map(f1),
                         "ZLB": top.zlb_flag.map({True: "ZLB", False: ""}), "D": top.D.map(f1), "D emp": top.D_employment.map(f1),
                         "D infl": top.D_inflation.map(f1), "D policy": top.D_policy.map(f1)})
    res = pd.DataFrame({"signal": top.signal_month.dt.strftime("%Y-%m"), "R 3m %": (100 * top.r_3m).map("{:+.1f}".format),
                        "R 6m %": (100 * top.r_6m).map("{:+.1f}".format), f"R {H}m %": (100 * top.r_h).map("{:+.1f}".format),
                        f"MDD {H}m %": (100 * top.mdd_h).map("{:.1f}".format), "worst vs entry %": (100 * top.worst_from_entry).map("{:.1f}".format),
                        "MDD trough date": top.mdd_trough_date.dt.date, "DD>=10%": top.dd_ge_10.map({True: "yes", False: "no"}),
                        "DD>=20%": top.dd_ge_20.map({True: "yes", False: "no"})})
    r12 = 100 * t5.r_h
    allr = 100 * R["out"].loc[P.index, "r_h"]
    t20r = 100 * t20.r_h
    raw = t20.reset_index()
    tab20 = pd.DataFrame({"rank": range(1, len(raw) + 1), "signal": raw.signal_month.dt.strftime("%Y-%m"), "D": raw.D.map(f1),
                          f"R {H}m %": (100 * raw.r_h).map("{:+.1f}".format), f"MDD {H}m %": (100 * raw.mdd_h).map("{:.1f}".format)})
    sn = snap[["feature", "value", "unit", "series_id", "observation", "release_timestamp_et"]].copy()
    sn["value"] = sn["value"].map(f1)
    chk = pd.DataFrame(checks).assign(passed=lambda d: d.passed.map({True: "PASS", False: "FAIL"}))[["name", "passed", "detail"]]
    cur = R["current"]
    txt = f"""# US macro historical-analog report (spec v1.0, phase P0)

**Data mode: {MODE}.** Every figure below comes from the latest-revised FRED history; release times are *rules* (labor: first Friday of the following month 08:30 ET; CPI: the 15th, conservative; fed funds: next day), not recorded vintage dates. Real point-in-time vintages and the walk-forward backtest are phase P1 and are **not available** in this report.

**As-of:** {R['as_of']}.  **Market data:** S&P 500 price index (no dividends) from Yahoo Finance via yfinance; unofficial source, personal research use.

## 1. Current macro snapshot
{_md(sn)}
Official cross-check: not independently verified (bls.gov blocks scripted access, HTTP 403); values are FRED's. Where the rule says a report should be out but FRED lacks it, the table shows the observation actually used. The snapshot uses labor data for {pd.Timestamp(cur['labor_obs_month']):%Y-%m} and CPI for {pd.Timestamp(cur['cpi_obs_month']):%Y-%m}: they are different months because the October CPI is not yet published.

## 2. Five closest historical month-ends (de-duplicated: at least {cfg['min_gap_months']} months apart)
Distance D = {cfg['weights']['employment']:.2f}·D_employment + {cfg['weights']['inflation']:.2f}·D_inflation + {cfg['weights']['policy']:.2f}·D_policy; each D_group is the mean squared median/IQR-standardised difference of its features. Scanned {len(P)} month-end signals ({P.index.min():%Y-%m} to {P.index.max():%Y-%m}); the scan covers every eligible month, no period is hard-coded.
{_md(tab5)}
## 3. S&P 500 price outcomes after those signals (not used for selection)
{_md(res)}
Five cases is a small, partly clustered sample. {H}-month return: mean {r12.mean():+.1f}%, median {r12.median():+.1f}%, range {r12.min():+.1f}% to {r12.max():+.1f}%. For reference, across all {len(P)} candidate months the median is {allr.median():+.1f}% and {100 * (allr > 0).mean():.0f}% are positive. These are descriptive; they are not a forecast and not a probability.

## 4. Raw top 20 (no de-duplication)
{_md(tab20)}
Median {H}-month return of the raw top 20: {t20r.median():+.1f}%; share positive: {100 * (t20r > 0).mean():.0f}%. Adjacent months cluster into a few episodes, which is why the de-duplicated list above exists.

## 5. Limits of this version
- Revised data and rule-based release times only. Early-period figures include later revisions (and seasonal-factor changes) that were not known then.
- Zero-lower-bound months are flagged (effective rate below {cfg['zlb_threshold_pct']}%), but QE periods are not separately flagged, and no shadow-rate sensitivity is run.
- No sensitivity analysis (weights, trend windows, excluding crisis periods), no out-of-sample backtest, no benchmark comparison: phase P1.
- Background for each analog (NBER status, shocks, valuation, politics) is not included; it needs verified sources and is explanation only.
- Missing observations (for example October 2025 unemployment and CPI) are left blank and any signal needing them is excluded.

## 6. Acceptance checks on this run
{_md(chk)}
"""
    (out_dir / "report.md").write_text(txt)


def emit_provenance(R, out_dir):
    cfg = R["cfg"]
    try:
        import subprocess
        h = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip() or "not available (not a git repository)"
    except Exception:
        h = "not available"
    prov = dict(generated_at_utc=str(pd.Timestamp.now(tz="UTC")), data_mode=MODE, as_of=str(R["as_of"]), parameters=cfg,
                python=sys.version.split()[0], platform=platform.platform(), git_commit=h,
                packages={m: __import__(m).__version__ for m in ("pandas", "numpy", "matplotlib", "yfinance")},
                candidates=dict(n=len(R["pool"]), first=str(R["pool"].index.min().date()), last=str(R["pool"].index.max().date())),
                sources=R["recs"])
    json.dump(prov, open(out_dir / "provenance.json", "w"), indent=2, default=str)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="macro_analog")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("snapshot", "find-analogs", "outcomes", "report", "backtest"):
        p = sub.add_parser(name)
        p.add_argument("--as-of")
        p.add_argument("--top-k", type=int)
        p.add_argument("--min-gap-months", type=int)
        p.add_argument("--horizon-months", type=int)
        p.add_argument("--weights", help="employment,inflation,policy e.g. 40,30,30")
        p.add_argument("--refresh", action="store_true", help="re-download raw data (new timestamped files; old ones kept)")
        p.add_argument("--out-dir", default=str(ROOT / "outputs"))
        if name == "backtest":
            p.add_argument("--start"); p.add_argument("--end")
    a = ap.parse_args(argv)
    if a.cmd == "backtest":
        print("backtest: not available in P0 (needs point-in-time vintages, phase P1)")
        return 1
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    R = pipeline(load_cfg(a), a.refresh)
    snap = emit_snapshot(R, out_dir)
    if a.cmd == "snapshot":
        print(snap[["feature", "value", "observation"]].to_string(index=False))
        return 0
    t5, t20 = emit_analogs(R, out_dir)
    if a.cmd == "find-analogs":
        print(t5[["D", "D_employment", "D_inflation", "D_policy"]].round(3).to_string())
        return 0
    emit_outcomes(R, out_dir)
    if a.cmd == "outcomes":
        print(R["out"].loc[R["top5"].index, ["r_h", "mdd_h", "worst_from_entry"]].round(3).to_string())
        return 0
    checks = validate.run_checks(current=R["current"], state=R["state"], pool=R["pool"], ranked=R["ranked"], top5=R["top5"], raw_top=R["raw_top"],
                                 outcomes=R["out"].loc[R["pool"].index], px_last=R["px"].index[-1], cfg=R["cfg"])
    json.dump(checks, open(out_dir / "validation.json", "w"), indent=2)
    emit_provenance(R, out_dir)
    emit_report(R, out_dir, snap, t5, t20, checks)
    print(pd.DataFrame(checks)[["name", "passed"]].to_string(index=False))
    return 0 if all(c["passed"] for c in checks) else 2


if __name__ == "__main__":
    sys.exit(main())
