"""Read the vector charts of refs/breadth.pdf (Yardeni Research, 30 Dec 2023) into CSVs.

Fig 1  : S&P 500 market-cap-weighted and equal-weighted price indexes, daily, log axis, 1990 - 2023-12-29
Fig 6/8: % of S&P 500 companies above their 200-dma / 50-dma (weekly 40wma/10wma approximation), 2008 - 2023-12-29

Needs pymupdf (not a project dependency).  python -m macro_analog.extract_yardeni
"""
import numpy as np
import pandas as pd
import pymupdf

from . import ingest
from .market import load_spx

PDF = ingest.ROOT / "refs" / "breadth.pdf"
OUT = ingest.ROOT / "data" / "external"
END = pd.Timestamp("2023-12-29")


def _points(d):
    out = []
    for it in d["items"]:
        for q in ((it[1].x, it[1].y), (it[-1].x, it[-1].y)):
            if not out or q != out[-1]:
                out.append(q)
    return out


def _lines(pg, y0, y1):
    seen, res = set(), []
    for d in pg.get_drawings():
        if len(d["items"]) > 150 and y0 - 30 <= d["rect"].y0 and d["rect"].y1 <= y1 + 30:
            key = (tuple(round(c, 2) for c in d["color"]), len(d["items"]))
            if key not in seen:
                seen.add(key)
                res.append((key[0], _points(d)))
    return res


def _to_date(x, x0, x1, start, end):
    return (start + pd.to_timedelta((np.asarray(x) - x0) / (x1 - x0) * (end - start).days, unit="D")).normalize()


def fig1(doc):
    pg = doc[2]
    labs = sorted((round((w[1] + w[3]) / 2, 2), float(w[4])) for w in pg.get_text("words")
                  if 560 < (w[0] + w[2]) / 2 < 570 and 90 < (w[1] + w[3]) / 2 < 360 and w[4].isdigit() and len(w[4]) >= 3)
    (ya, va), (yb, vb) = labs[0], labs[-1]                                   # 7000 at the top, 250 at the bottom
    ln = lambda y: np.exp(np.log(va) + (y - ya) / (yb - ya) * (np.log(vb) - np.log(va)))
    spx = load_spx(ingest.latest("spx_schwab")).loc["1990-01-01":"2023-12-29"]
    lines = _lines(pg, 90, 350)
    blue = next(p for c, p in lines if c == (0.0, 0.0, 1.0))
    red = next(p for c, p in lines if c == (1.0, 0.0, 0.0))
    start, x0, x1 = pd.Timestamp("1990-01-01"), 63.03, 521.9
    frames = {}
    for name, p in (("cw", blue), ("ew", red)):
        p = p[::-1]                                                          # the path is drawn newest -> oldest
        s = pd.Series(ln(np.array([q[1] for q in p])), index=_to_date([q[0] for q in p], x0, x1, start, END))
        frames[name] = s.groupby(level=0).last()
    # the label-centre calibration is a constant fraction off; fix it with the market-cap line, which IS the S&P 500
    j = pd.concat([np.log(frames["cw"]).rename("p"), np.log(spx).rename("t")], axis=1, join="inner")
    off = (j.t - j.p).mean()
    print(f"fig1: constant calibration offset {off * 100:+.2f}% ; cw vs Schwab $SPX on {len(j)} matched days: "
          f"residual sd {(j.p + off - j.t).std() * 100:.2f}%")
    df = pd.DataFrame({k: v * np.exp(off) for k, v in frames.items()})
    df.index.name = "date"
    df = df.rename(columns={"cw": "sp500_cap_weighted", "ew": "sp500_equal_weighted"})
    df["ew_to_cw_ratio"] = df.sp500_equal_weighted / df.sp500_cap_weighted
    return df.dropna()


def breadth(doc, page, top_fig_is_sp100=True):
    """Return (200dma or 50dma) series from the lower chart (S&P 500) of the given 0-based page."""
    pg = doc[page]
    ticks = sorted({round(i[1].y, 1) for d in pg.get_drawings() for i in d["items"]
                    if i[0] == "l" and abs(i[1].x - 549.0) < 0.2 and abs(i[2].x - 555.0) < 0.2 and 440 < i[1].y < 660})
    y0, y100 = ticks[-1], ticks[0]            # major ticks: 0% at the bottom, 100% at the top
    line = _lines(pg, 440, 660)[0][1]
    x0, x1 = 63.31, 520.2
    vals = (y0 - np.array([q[1] for q in line])) / (y0 - y100) * 100
    s = pd.Series(vals, index=_to_date([q[0] for q in line], x0, x1, pd.Timestamp("2008-01-01"), END))
    if s.index[0] > s.index[-1]:
        s = s.iloc[::-1]
    s.index = s.index.to_period("W-FRI").to_timestamp(how="end").normalize()
    s = s.groupby(level=0).last()
    return s, (y0, y100)


def main():
    doc = pymupdf.open(PDF)
    OUT.mkdir(parents=True, exist_ok=True)
    f1 = fig1(doc)
    f1.round(3).to_csv(OUT / "yardeni_sp500_ew_cw_daily_1990_2023.csv")
    print("fig1 rows", len(f1), f1.index.min().date(), f1.index.max().date(), "| last EW", f1.sp500_equal_weighted.iloc[-1].round(1),
          "(report label 6402.89) | last CW", f1.sp500_cap_weighted.iloc[-1].round(1))
    for name, page in (("pct_above_200dma", 4), ("pct_above_50dma", 5)):
        s, ticks = breadth(doc, page)
        s.rename(name).round(2).to_csv(OUT / f"yardeni_sp500_{name}_weekly_2008_2023.csv", index_label="week_ending")
        print(name, len(s), s.index.min().date(), s.index.max().date(), "last", s.iloc[-1].round(1), "ticks", ticks)


if __name__ == "__main__":
    main()
