"""Chart: top-10 share of S&P 500 market cap and forward earnings (Goldman chart, read from the J.P. Morgan PDF)
plus the Schwab-based bridge to today.  python -m macro_analog.plot_concentration"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from . import ingest
from .plots import GRID, INK, INK2, MUTED, SERIES, SURFACE, _save, _style

EXT = ingest.ROOT / "data" / "external"
ANALOGS = ["2000-11", "2023-11", "2018-01", "2006-09", "2025-06"]     # same order/colors as analog_paths.png
CURRENT = "2026-10"


def main():
    gs = pd.read_csv(EXT / "gs_top10_concentration_eotm_jun2026.csv", index_col=0)
    gs.index = pd.PeriodIndex(gs.index, freq="M")
    cap, eps = gs["top10_mktcap_pct"].dropna(), gs["top10_fwd_earnings_pct"].dropna()
    br = pd.read_csv(EXT / "top10_cap_share_bridge.csv", index_col=0, parse_dates=True)["top10_cap_share_pct"]
    br_m = br.groupby(br.index.to_period("M")).mean()
    t = lambda s: s.index.to_timestamp() if isinstance(s.index, pd.PeriodIndex) else s.index

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 9), facecolor=SURFACE, gridspec_kw=dict(height_ratios=[3, 2]))
    for ax in (a1, a2):
        _style(ax)
        ax.set_ylim(10, 45)
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))

    # --- top panel: full history ---
    a1.plot(t(eps), eps, color=MUTED, lw=1.6)
    a1.plot(t(cap), cap, color=INK, lw=2.2)
    a1.plot(br.loc["2026-05-15":].index, br.loc["2026-05-15":], color=INK, lw=2.2, ls=(0, (2, 1.2)))
    box = dict(fc=SURFACE, ec="none", pad=1.5, alpha=0.9)
    a1.text(pd.Timestamp("2026-12-15"), 43.0, "Top 10 share of\nmarket cap", color=INK, fontsize=9.5, va="center")
    a1.text(pd.Timestamp("2026-12-15"), 33.5, "Top 10 share of\n12m forward earnings", color=INK2, fontsize=9.5, va="center")
    off = {"2000-11": (0, -20), "2023-11": (-30, -3), "2018-01": (0, -20), "2006-09": (0, -20), "2025-06": (-6, -22)}
    for i, m in enumerate(ANALOGS):
        p = pd.Period(m)
        a1.plot(p.to_timestamp(), cap[p], "o", ms=9, color=SERIES[i], mec=SURFACE, mew=1.8, zorder=5)
        a1.annotate(m, (p.to_timestamp(), cap[p]), xytext=off[m], textcoords="offset points", ha="center", fontsize=9, color=INK2, bbox=box)
    cur = pd.Period(CURRENT)
    a1.plot(cur.to_timestamp(), br_m[cur], "o", ms=9, color=INK, mec=SURFACE, mew=1.8, zorder=5)
    a1.annotate(f"{CURRENT}\n(current)", (cur.to_timestamp(), br_m[cur]), xytext=(12, -22), textcoords="offset points",
                ha="left", fontsize=9, color=INK, bbox=box)
    a1.set_xlim(pd.Timestamp("1985-01-01"), pd.Timestamp("2030-03-01"))
    a1.set_title("Top-10 company share of S&P 500 market cap and earnings, 1985 to Nov 2026", loc="left", color=INK, fontsize=12)

    # --- bottom panel: zoom with the bridge check ---
    z0 = pd.Period("2025-01")
    box = dict(fc=SURFACE, ec="none", pad=1.5, alpha=0.9)
    a2.plot(t(eps.loc[z0:]), eps.loc[z0:], color=MUTED, lw=1.8)
    a2.plot(t(cap.loc[z0:]), cap.loc[z0:], color=INK, lw=2.4)
    a2.plot(br.loc["2026-01":].index, br.loc["2026-01":], color=INK, lw=1.6, ls=(0, (2, 2)))
    a2.axvspan(pd.Timestamp("2026-03-01"), pd.Timestamp("2026-06-01"), color=GRID, alpha=0.7, lw=0)
    a2.text(pd.Timestamp("2026-04-15"), 11.2, "bridge calibrated\nto the chart here", ha="center", fontsize=8.5, color=INK2)
    a2.annotate("Goldman chart (extracted)", (pd.Timestamp("2025-02-01"), 42.3), fontsize=9, color=INK)
    a2.annotate("Schwab prices + market caps\n(bridge, dashed)", (pd.Timestamp("2026-06-15"), 42.3), fontsize=9, color=INK)
    a2.annotate("12m forward earnings share\n(chart ends 2026-05)", (pd.Timestamp("2025-05-01"), 22.0), fontsize=9, color=INK2)
    for i, m in enumerate(ANALOGS):
        if pd.Period(m) >= z0:
            p = pd.Period(m)
            a2.plot(p.to_timestamp(), cap[p], "o", ms=9, color=SERIES[i], mec=SURFACE, mew=1.8, zorder=5)
            a2.annotate(m, (p.to_timestamp(), cap[p]), xytext=(0, -18), textcoords="offset points", ha="center", fontsize=9, color=INK2, bbox=box)
    a2.plot(cur.to_timestamp(), br_m[cur], "o", ms=9, color=INK, mec=SURFACE, mew=1.8, zorder=5)
    a2.annotate(f"{CURRENT} (current)", (cur.to_timestamp(), br_m[cur]), xytext=(0, -17), textcoords="offset points", ha="center", fontsize=9, color=INK)
    a2.set_xlim(pd.Timestamp("2025-01-01"), pd.Timestamp("2026-12-01"))
    a2.set_title("Zoom: last 2 years, and the check of the bridge against the chart", loc="left", color=INK, fontsize=11)

    fig.text(0.01, 0.01, "Sources: Goldman Sachs Global Investment Research chart (5 Jun 2026), values read from the vector chart in the J.P. Morgan "
             "Eye on the Market PDF, about +/-1-2 pp; Jun-Nov 2026 market-cap share rebuilt from Schwab (error about +/-1.5 pp). "
             "Earnings share cannot be bridged.", fontsize=7.5, color=INK2, wrap=True)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    _save(fig, str(ingest.ROOT / "outputs" / "p0" / "top10_concentration"))


if __name__ == "__main__":
    main()
