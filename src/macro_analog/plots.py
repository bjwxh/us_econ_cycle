"""Charts. Palette: validated reference categorical slots 1-5 (light surface), current state in ink."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]


def _style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, lw=0.8)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=INK2, length=0, labelsize=9)


def _save(fig, stem):
    fig.savefig(f"{stem}.png", dpi=160, facecolor=SURFACE)
    fig.savefig(f"{stem}.pdf", facecolor=SURFACE)
    plt.close(fig)


def plot_macro_paths(feats_rev, feats_asof, target_m, analog_months, stem, lookback=12):
    panels = [("unrate", "Unemployment rate (%)"), ("pay_g6", "Payrolls, 6-month growth (%)"),
              ("core_ann6", "Core CPI, 6-month annualized (%)"), ("ff", "Effective fed funds (%)")]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), facecolor=SURFACE, sharex=True)
    x = list(range(-lookback, 1))
    for ax, (col, title) in zip(axes.flat, panels):
        _style(ax)
        for i, m in enumerate(analog_months):
            ax.plot(x, feats_rev[col].loc[m - lookback:m].values, color=SERIES[i], lw=1.8,
                    label=f"{m} (analog {i + 1})")
        ax.plot(x, feats_asof[col].loc[target_m - lookback:target_m].values, color=INK, lw=2.6,
                label=f"{target_m} (current, as known)")
        ax.set_title(title, loc="left", color=INK, fontsize=10.5)
    for ax in axes[1]:
        ax.set_xlabel("Months relative to observation month", color=INK2, fontsize=9)
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, labelcolor=INK2, fontsize=9)
    fig.suptitle("Macro path in the 12 months before each match (analogs use revised data)", x=0.01,
                 ha="left", color=INK, fontsize=12)
    fig.tight_layout(rect=(0, 0.07, 1, 0.96))
    _save(fig, stem)


def plot_outcomes(paths, labels, stem):
    """paths: list of daily close Series from entry to 12m end."""
    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=SURFACE)
    _style(ax)
    ax.axhline(100, color=MUTED, lw=1)
    for i, (p, lab) in enumerate(zip(paths, labels)):
        ax.plot(range(len(p)), p.values / p.iloc[0] * 100, color=SERIES[i], lw=1.8, label=lab)
    ax.set_xlabel("Trading days after signal date (entry close = 100)", color=INK2, fontsize=9)
    ax.set_title("S&P 500 price index, 12 months after each analog (not used in matching)", loc="left",
                 color=INK, fontsize=11.5)
    ax.legend(frameon=False, labelcolor=INK2, fontsize=9, loc="upper left")
    fig.tight_layout()
    _save(fig, stem)
