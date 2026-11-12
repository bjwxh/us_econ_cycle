"""Charts. Blue = current period, orange = historical analogs. Both PNG and PDF are written."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CUR, ANA = "#2a78d6", "#eb6834"
INK, SUB, MUTED, GRID, BG, DOT = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb", "#b9b8b0"
PANELS = [("unrate_level", "Unemployment rate, %"), ("payroll_growth_6m", "Payroll growth, 6 mo, %"),
          ("cpi_yoy", "CPI inflation YoY, %"), ("core_cpi_yoy", "Core CPI YoY, %"), ("ffr_level", "Effective fed funds, %")]


def _style(ax):
    ax.set_facecolor(BG)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)


def _save(fig, out_dir, stem):
    for ext in ("png", "pdf"):
        fig.savefig(out_dir / f"{stem}.{ext}", dpi=150, facecolor=BG)
    plt.close(fig)


def plot_macro_paths(state, current, top5, out_dir, mode_label):
    """12 months of inputs BEFORE each signal (x = months before signal; x=0 is the signal). Inputs only."""
    last = state.index[state.index <= pd.Timestamp(current["as_of"]).tz_localize(None).replace(day=1) - pd.DateOffset(months=1)][-1]
    cx = np.arange(-12, 0)
    cur_rows = state.loc[[last - pd.DateOffset(months=k) for k in range(11, -1, -1)]]
    fig, axs = plt.subplots(len(PANELS), len(top5), figsize=(15, 12), sharey="row", sharex=True, facecolor=BG, squeeze=False)
    for j, (m, r) in enumerate(top5.iterrows()):
        hist = state.loc[[m - pd.DateOffset(months=k) for k in range(12, -1, -1)]]
        for i, (f, lab) in enumerate(PANELS):
            ax = axs[i, j]
            _style(ax)
            ax.plot(np.arange(-12, 1), hist[f].to_numpy(float), color=ANA, lw=2, zorder=3)
            ax.plot(np.append(cx, 0), np.append(cur_rows[f].to_numpy(float), current[f]), color=CUR, lw=2.2, zorder=4)
            if j == 0:
                ax.set_ylabel(lab, fontsize=9, color=SUB)
            if i == 0:
                ax.set_title(f"{m:%Y-%m}  (rank {j + 1})\ndistance {r['D']:.2f}", fontsize=10, color=INK, loc="left", fontweight="bold")
            if i == len(PANELS) - 1:
                ax.set_xlabel("Months before signal", fontsize=8.5, color=SUB)
    fig.suptitle("Inputs in the 12 months before each signal: analog (orange) vs current (blue)", x=0.04, y=0.995, ha="left",
                 fontsize=14, color=INK, fontweight="bold")
    fig.text(0.04, 0.94, f"{mode_label}.\nx = 0 is the signal date (analogs: month-end; current: the as-of snapshot). Same y-scale along each row. "
             "Breaks in the blue line = no published value (left blank).", fontsize=9, color=SUB, va="bottom", linespacing=1.5)
    fig.subplots_adjust(left=0.08, right=0.99, top=0.9, bottom=0.05, hspace=0.25, wspace=0.08)
    _save(fig, out_dir, "analog_paths")


def plot_outcomes(px, top5, outcomes, cand_out, raw_top, out_dir, H=12):
    fig = plt.figure(figsize=(15, 9.5), facecolor=BG)
    gs = fig.add_gridspec(2, 5, height_ratios=[1.5, 1], hspace=0.45, wspace=0.12)
    axs = [fig.add_subplot(gs[0, j]) for j in range(5)]
    segs = {m: px.loc[outcomes.loc[m].entry_date:outcomes.loc[m].end_date] for m in top5.index}
    lo = min(100 * v.min() / v.iloc[0] for v in segs.values())
    hi = max(100 * v.max() / v.iloc[0] for v in segs.values())
    for j, (m, _) in enumerate(top5.iterrows()):
        o = outcomes.loc[m]
        seg = segs[m]
        x = (seg.index - seg.index[0]).days / 30.4375
        y = 100 * seg.to_numpy() / seg.iloc[0]
        ax = axs[j]
        _style(ax)
        ax.axhline(100, color=MUTED, lw=0.9)
        ax.plot(x, y, color=ANA, lw=1.8)
        t = (o.mdd_trough_date - seg.index[0]).days / 30.4375
        ax.plot([t], [100 * px.loc[o.mdd_trough_date] / seg.iloc[0]], "o", color=INK, ms=6, mec=BG, mew=1.5)
        ax.set_title(f"signal {m:%Y-%m}", fontsize=10.5, color=INK, loc="left", fontweight="bold", pad=34)
        ax.text(0, 1.02, f"{H}m return {100 * o.r_h:+.0f}%\nmax drawdown {100 * o.mdd_h:.0f}%", transform=ax.transAxes,
                fontsize=9, color=SUB, va="bottom", linespacing=1.4)
        ax.set_ylim(lo - 3, hi + 3)
        if j:
            ax.tick_params(labelleft=False)
        ax.set_xlim(0, H)
        ax.set_xticks(list(range(0, H + 1, 3 if H <= 12 else 6)))
        ax.set_xlabel("Months after signal", fontsize=8.5, color=SUB)
        if j == 0:
            ax.set_ylabel("S&P 500, signal-day close = 100", fontsize=9, color=SUB)
    for k, (col, title, mult) in enumerate([("r_h", f"{H}-month price return, %", 100), ("mdd_h", f"Max drawdown within the {H} months, %", 100)]):
        ax = fig.add_subplot(gs[1, 0:2] if k == 0 else gs[1, 3:5])
        _style(ax)
        ax.grid(axis="x", color=GRID, lw=0.7)
        ax.grid(axis="y", visible=False)
        rng = np.random.default_rng(0)
        groups = [("All candidates", cand_out[col], DOT, 8, 0.55), ("Raw top 20", outcomes.loc[raw_top.index, col], ANA, 26, 0.9),
                  ("Top 5", outcomes.loc[top5.index, col], ANA, 60, 1.0)]
        for yy, (lab, v, c, s, a) in enumerate(groups):
            ax.scatter(mult * v.to_numpy(), yy + rng.uniform(-0.18, 0.18, len(v)), s=s, color=c, alpha=a,
                       edgecolor=BG if yy else "none", linewidth=0.8, zorder=3 + yy)
            ax.plot([mult * v.median()] * 2, [yy - 0.3, yy + 0.3], color=INK, lw=2, zorder=6)
        ax.set_yticks(range(3))
        ax.set_yticklabels([g[0] for g in groups], fontsize=9, color=SUB)
        ax.set_title(title + "  (black tick = median)", fontsize=10.5, color=INK, loc="left", fontweight="bold")
        ax.axvline(0, color=MUTED, lw=0.9)
    fig.suptitle(f"What the S&P 500 did in the {H} months after each analog signal", x=0.04, y=0.995, ha="left", fontsize=14, color=INK, fontweight="bold")
    fig.text(0.04, 0.945, "Daily closes, price index (no dividends). These outcomes were NOT used to select the analogs. Dot = day of the max-drawdown trough.",
             fontsize=9, color=SUB, va="bottom")
    fig.subplots_adjust(left=0.1, right=0.99, top=0.84, bottom=0.07)
    _save(fig, out_dir, "sp500_outcomes")
