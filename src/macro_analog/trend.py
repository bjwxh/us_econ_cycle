"""Trend-based analog search (alternative to features/analogs.py). Run: python -m macro_analog.trend

Each series is described by its 6-month PATH relative to month m-6: x[m-k] - x[m-6], k=0..5
(unrate, ff: percentage points; payrolls, headline CPI, core CPI: cumulative % change of the level,
so the path encodes speed and acceleration). Paths are scaled per series by the IQR of the pool's
total 6m change, so each path point counts equally. Level terms (unrate, ff) keep a small weight LAM
inside their group. Group weights stay 40/30/30. Market data is not used here.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from . import ingest
from .analogs import dedup
from .features import load_series
from .market import load_spx, outcome

W = {"employment": 0.4, "inflation": 0.3, "policy": 0.3}
SERIES = {"employment": ["UNRATE", "PAYEMS"], "inflation": ["CPIAUCSL", "CPILFESL"], "policy": ["FEDFUNDS"]}
LEVELS = {"employment": "UNRATE", "policy": "FEDFUNDS"}
PCT = {"PAYEMS", "CPIAUCSL", "CPILFESL"}  # cumulative % change; others are differences


def paths(raw: dict, win: int = 6) -> dict:
    """name -> DataFrame (index month, columns k=win-1..0) of x[m-k]-x[m-win]."""
    idx = pd.period_range(min(s.index.min() for s in raw.values()), max(s.index.max() for s in raw.values()), freq="M")
    out = {}
    for n, s in raw.items():
        s = s.reindex(idx)
        base = s.shift(win)
        out[n] = pd.DataFrame({k: ((s.shift(k) / base - 1) * 100 if n in PCT else s.shift(k) - base)
                               for k in range(win - 1, -1, -1)})
    return out, {n: raw[n].reindex(idx) for n in raw}


def distances(P: dict, L: dict, pool_idx, target_m, lam: float) -> pd.DataFrame:
    out = pd.DataFrame(index=pool_idx)
    for g, names in SERIES.items():
        trend = 0
        for n in names:
            p = P[n]
            sc = p[0].loc[pool_idx].quantile(.75) - p[0].loc[pool_idx].quantile(.25)
            trend = trend + (((p.loc[pool_idx] - p.loc[target_m]) / sc) ** 2).mean(axis=1) / len(names)
        out[f"D_{g}_trend"] = trend
        if g in LEVELS:
            l = L[LEVELS[g]]
            sc = l.loc[pool_idx].quantile(.75) - l.loc[pool_idx].quantile(.25)
            out[f"D_{g}_level"] = ((l.loc[pool_idx] - l.loc[target_m]) / sc) ** 2
            out[f"D_{g}"] = (1 - lam) * trend + lam * out[f"D_{g}_level"]
        else:
            out[f"D_{g}"] = trend
    out["D"] = sum(W[g] * out[f"D_{g}"] for g in W)
    return out.sort_values("D")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default="2026-11-10")
    ap.add_argument("--lam", type=float, default=0.15)
    ap.add_argument("--window", type=int, default=6, help="path window in months (default 6)")
    ap.add_argument("--n", type=int, default=5, help="number of analogs")
    ap.add_argument("--out", default=str(ingest.ROOT / "outputs" / "p0_trend"))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    names = ["PAYEMS", "UNRATE", "CPIAUCSL", "CPILFESL", "FEDFUNDS"]
    rev = {n: load_series(ingest.latest(f"fred_{n}_revised")) for n in names}
    asof = {n: load_series(ingest.latest(f"fred_{n}_asof{a.as_of}")) for n in names}
    # history from revised data; target month's window from the as-of vintage
    target_m = load_series(ingest.latest(f"fred_UNRATE_asof{a.as_of}")).dropna().index.max()
    base_m = target_m - a.window
    for n in names:  # an unpublished base month (Oct 2025 shutdown gap) is filled for the TARGET only
        if pd.isna(asof[n].get(base_m, np.nan)):
            lo, hi = asof[n][base_m - 1], asof[n][base_m + 1]
            asof[n][base_m] = (lo * hi) ** .5 if n in PCT else (lo + hi) / 2
            print(f"as-of {n} {base_m} not published: filled with {'geometric' if n in PCT else 'arithmetic'} mean of neighbours = {asof[n][base_m]:.4f}")
    Pr, Lr = paths(rev, a.window)
    Pa, La = paths(asof, a.window)
    for n in names:  # splice the as-of window into the target row
        Pr[n].loc[target_m] = Pa[n].loc[target_m]
        Lr[n].loc[target_m] = La[n].loc[target_m]
    spx = load_spx(ingest.latest("spx_schwab"))
    rows = {m: o for m in Lr["UNRATE"].index if m + 1 >= spx.index[0].to_period("M") and (o := outcome(spx, m + 1))}
    outc = pd.DataFrame.from_dict(rows, orient="index")
    ok = pd.concat([Pr[n] for n in names], axis=1).dropna().index.intersection(Lr["UNRATE"].dropna().index)
    ok = ok.intersection(Lr["FEDFUNDS"].dropna().index)
    pool = outc.index.intersection(ok)
    pool = pool[pool != target_m]
    assert not pd.concat([Pr[n].loc[[target_m]] for n in names], axis=1).isna().any().any()

    res = {}
    for lam in sorted({0.0, a.lam, 0.3}):
        r = distances(Pr, Lr, pool, target_m, lam)
        res[lam] = r
    # direction filter: drop candidates whose 6m change has the opposite sign of the target's (unrate, ff)
    keep = pd.Series(True, index=pool)
    for n in ["UNRATE", "FEDFUNDS"]:
        keep &= (np.sign(Pr[n][0].loc[pool]) * np.sign(Pr[n][0][target_m])) >= 0
    print(f"direction filter keeps {keep.sum()} of {len(pool)} months")
    unf = res[a.lam]
    res = {lam: rr[keep.reindex(rr.index)] for lam, rr in res.items()}
    r = res[a.lam]
    print("unfiltered lam=%s top5:" % a.lam, ", ".join(map(str, dedup(unf, 5, 18).index)))
    top = dedup(r, a.n, 18)
    summ = pd.DataFrame({"D": top["D"], "D_emp": top["D_employment"], "D_inf": top["D_inflation"], "D_pol": top["D_policy"],
                         "unrate": Lr["UNRATE"].loc[top.index], "unrate_chg6": Pr["UNRATE"][0].loc[top.index],
                         "pay_cum6": Pr["PAYEMS"][0].loc[top.index], "core_cum6": Pr["CPILFESL"][0].loc[top.index],
                         "ff": Lr["FEDFUNDS"].loc[top.index], "ff_chg6": Pr["FEDFUNDS"][0].loc[top.index]})
    summ = summ.join(outc[["signal_date", "R_12m", "MDD_12m"]])
    tgt = pd.Series({"unrate": Lr["UNRATE"][target_m], "unrate_chg6": Pr["UNRATE"][0][target_m],
                     "pay_cum6": Pr["PAYEMS"][0][target_m], "core_cum6": Pr["CPILFESL"][0][target_m],
                     "ff": Lr["FEDFUNDS"][target_m], "ff_chg6": Pr["FEDFUNDS"][0][target_m]})
    summ.index = summ.index.astype(str); summ.index.name = "obs_month"
    summ.to_csv(out / ("analog_top5_trend.csv" if a.n == 5 else f"analog_top{a.n}_trend.csv")); r.head(20).to_csv(out / "analog_top20_trend_raw.csv")
    print(f"target {target_m}  pool {len(pool)} ({pool.min()}..{pool.max()})  lam={a.lam}")
    print(tgt.round(2).to_string()); print()
    pd.set_option("display.width", 250)
    print(summ.round(3).to_string())
    for lam, rr in res.items():
        print(f"lam={lam}: ", ", ".join(map(str, dedup(rr, 5, 18).index)))
    print("old top5 : 2000-11, 2023-11, 2018-01, 2006-09, 2025-06")
    # paths for inspection
    for n in ["UNRATE", "FEDFUNDS"]:
        print(n, "target path", Pa[n].loc[target_m].round(2).tolist())
        for m in top.index: print("   ", m, Pr[n].loc[m].round(2).tolist())


if __name__ == "__main__":
    main()
