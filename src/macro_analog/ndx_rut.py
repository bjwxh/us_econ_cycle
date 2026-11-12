"""Indicators 2 and 4: $NDX/$SPX and $RUT/$SPX from Schwab daily closes (price indexes). Table + chart."""
import json, time
import pandas as pd
import requests
import matplotlib.pyplot as plt
from . import ingest
from .market import load_spx
from .plots import SURFACE, INK, INK2, MUTED, SERIES, _style, _save
from .ew_breadth_series import E, ANALOGS


def fetch(sym):
    r = requests.get("https://api.schwabapi.com/marketdata/v1/pricehistory",
                     headers={"Authorization": f"Bearer {ingest._schwab_access_token()}"},
                     params=dict(symbol=sym, periodType="year", frequencyType="daily", frequency=1,
                                 startDate=int(pd.Timestamp("1989-12-01", tz="UTC").timestamp() * 1000),
                                 endDate=int(time.time() * 1000), needExtendedHoursData="false"), timeout=60)
    r.raise_for_status()
    stamp = ingest._now()
    name = sym.strip("$").lower()
    (ingest.RAW / f"{name}_schwab_{stamp}.json").write_text(r.text)
    ingest._log(dict(series_id=sym, provider="Schwab pricehistory daily", downloaded_at_utc=stamp, unit="index points, price only",
                     file=f"{name}_schwab_{stamp}.json"))
    c = r.json()["candles"]
    return pd.Series({pd.Timestamp(x["datetime"], unit="ms").normalize(): x["close"] for x in c})


def main():
    spx = load_spx(ingest.latest("spx_schwab"))
    out = {}
    for sym, col in (("$NDX", "ndx_spx"), ("$RUT", "rut_spx")):
        s = fetch(sym)
        print(sym, s.index.min().date(), "->", s.index.max().date(), len(s))
        r = (s / spx.reindex(s.index)).dropna()
        out[col] = r.groupby(r.index.to_period("M")).last()
    m = pd.DataFrame(out)
    m.to_csv(E / "ind2_ind4_monthly.csv")
    rows = []
    for a in ANALOGS:
        p = pd.Period(a)
        row = dict(month=a)
        for c in m:
            v = m[c].get(p)
            row[c] = v
            for k in (6, 12):
                b = m[c].get(p - k)
                row[f"{c}_chg{k}"] = None if v is None or b is None or pd.isna(b) else v / b - 1
        rows.append(row)
    t = pd.DataFrame(rows).set_index("month")
    print(t.round(3).to_string())
    t.to_csv(E / "ind2_ind4_analog_table.csv")

    rank = list(pd.read_csv(ingest.ROOT / "outputs" / "p0" / "analog_top5.csv")["obs_month"])
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.5), facecolor=SURFACE)
    mm = m.copy(); mm.index = mm.index.to_timestamp()
    for ax, (c, title) in zip(axes, [("ndx_spx", "Nasdaq 100 / S&P 500 (price indexes; ratio level)"),
                                     ("rut_spx", "Russell 2000 / S&P 500 (price indexes; ratio level)")]):
        _style(ax)
        s = mm[c].dropna()
        ax.plot(s.index, s.values, color=MUTED, lw=1.4)
        for a in ANALOGS:
            t0 = pd.Period(a).to_timestamp()
            if t0 in s.index:
                cur = a == ANALOGS[-1]
                ax.scatter([t0], [s[t0]], color=INK if cur else SERIES[rank.index(a)], s=60, zorder=3, edgecolor=SURFACE, linewidth=1.5)
                ax.annotate(f"{a}  {s[t0]:.2f}", (t0, s[t0]), xytext=({"2023-11": (-30, -22), "2025-06": (-60, 12), "2026-10": (8, 10)} if c == "ndx_spx" else {"2023-11": (-30, 12), "2025-06": (-30, -20), "2026-10": (8, 10)}).get(a, (8, 10)), textcoords="offset points",
                            color=INK if cur else INK2, fontsize=9, fontweight="bold" if cur else "normal")
        ax.set_title(title, loc="left", color=INK, fontsize=10.5)
    fig.tight_layout()
    _save(fig, str(ingest.ROOT / "outputs" / "p0" / "ndx_rut"))


if __name__ == "__main__":
    main()
