"""Chart for indicators 3 and 5 with the five analogs and the current month marked."""
import pandas as pd
import matplotlib.pyplot as plt
from .plots import SURFACE, INK, INK2, MUTED, SERIES, _style, _save
from .ew_breadth_series import E, ANALOGS
from . import ingest


def main():
    m = pd.read_csv(E / "ind3_ind5_monthly.csv", index_col=0)
    m.index = pd.PeriodIndex(m.index, freq="M").to_timestamp()
    rank = list(pd.read_csv(E.parents[1] / "outputs" / "p0" / "analog_top5.csv")["obs_month"])
    col_of = {a: SERIES[rank.index(a)] for a in rank}
    off = {"2000-11": (8, 8), "2006-09": (8, 8), "2018-01": (8, 8), "2023-11": (8, -20), "2025-06": (-38, 12), "2026-10": (8, 10)}
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.5), facecolor=SURFACE)
    specs = [("cw_over_ew", "S&P 500 cap-weighted / equal-weighted (1989-12 = 1.0; higher = mega-cap leadership)"),
             ("pct_above_200dma", "% of S&P 500 stocks above their 200-day average (monthly, last week)")]
    for ax, (col, title) in zip(axes, specs):
        _style(ax)
        s = m[col].dropna()
        ax.plot(s.index, s.values, color=MUTED, lw=1.4)
        for i, a in enumerate(ANALOGS):
            t = pd.Period(a).to_timestamp()
            if t in s.index:
                cur = a == ANALOGS[-1]
                c = INK if cur else col_of[a]
                ax.scatter([t], [s[t]], color=c, s=60, zorder=3, edgecolor=SURFACE, linewidth=1.5)
                ax.annotate(f"{a}  {s[t]:.2f}" if col == "cw_over_ew" else f"{a}  {s[t]:.0f}", (t, s[t]), xytext=off[a],
                            textcoords="offset points", color=INK if cur else INK2, fontsize=9, fontweight="bold" if cur else "normal")
        ax.set_title(title, loc="left", color=INK, fontsize=10.5)
    axes[1].text(0.30, 0.04, "2000-11 and 2006-09: no data (series starts 2008)\n2008-2023-12: Yardeni (extracted); later: rebuilt with point-in-time membership",
                 transform=axes[1].transAxes, color=INK2, fontsize=8.5, va="bottom")
    fig.tight_layout()
    _save(fig, str(ingest.ROOT / "outputs" / "p0" / "ew_breadth"))


if __name__ == "__main__":
    main()
