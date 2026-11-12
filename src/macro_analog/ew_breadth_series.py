"""Indicators 3 and 5: monthly series and the five-analog comparison.
3 = S&P 500 (cap) / S&P 500 Equal Weight: Yardeni extraction to 2006-08, Schwab $SPXEW + $SPX after (same index, matches to 0.6%).
5 = % of S&P 500 stocks above 200-dma: Yardeni 2008-2023-12, point-in-time rebuild after (weekly, last week of month)."""
import json
import pandas as pd
from . import ingest
from .market import load_spx

E = ingest.ROOT / "data" / "external"
ANALOGS = ["2000-11", "2006-09", "2018-01", "2023-11", "2025-06", "2026-10"]


def monthly_ratio():
    y = pd.read_csv(E / "yardeni_sp500_ew_cw_daily_1990_2023.csv", parse_dates=["date"]).set_index("date")
    ew = json.load(open(ingest.latest("spxew_schwab")))["candles"]
    ew = pd.Series({pd.Timestamp(c["datetime"], unit="ms").normalize(): c["close"] for c in ew})
    spx = load_spx(ingest.latest("spx_schwab"))
    sch = (spx / ew.reindex(spx.index)).dropna()
    yr = (y["sp500_cap_weighted"] / y["sp500_equal_weighted"])[: "2006-08-13"]  # CW/EW, base 1.0 at 1989-12-31
    sch = sch * (yr.iloc[-1] / sch[sch.index >= "2006-08-14"].iloc[0])  # rebase Schwab raw ratio to the Yardeni base
    full = pd.concat([yr, sch[sch.index >= "2006-08-14"]])
    return full.groupby(full.index.to_period("M")).last().rename("cw_over_ew")


def monthly_breadth():
    a = pd.read_csv(E / "yardeni_sp500_pct_above_200dma_weekly_2008_2023.csv", parse_dates=["week_ending"]).set_index("week_ending")["pct_above_200dma"]
    b = pd.read_csv(E / "sp500_breadth_rebuilt_2023_2026.csv", parse_dates=["week_ending"]).set_index("week_ending")["pct_above_200dma"]
    full = pd.concat([a, b[b.index > a.index.max()]])
    full = full[full.index <= pd.Timestamp("2026-11-11")]
    return full.groupby(full.index.to_period("M")).last().rename("pct_above_200dma")


def main():
    m = pd.concat([monthly_ratio(), monthly_breadth()], axis=1)
    m.index = m.index.astype(str)
    m.to_csv(E / "ind3_ind5_monthly.csv")
    rows = []
    for a in ANALOGS:
        p = pd.Period(a)
        g = lambda k, col: m[col].get(str(p - k))
        rows.append(dict(month=a, cw_ew=g(0, "cw_over_ew"), cw_ew_chg6=None if g(6, "cw_over_ew") is None else g(0, "cw_over_ew") / g(6, "cw_over_ew") - 1,
                         cw_ew_chg12=g(0, "cw_over_ew") / g(12, "cw_over_ew") - 1 if g(12, "cw_over_ew") else None,
                         breadth200=g(0, "pct_above_200dma"), breadth200_avg6=m["pct_above_200dma"].loc[str(p - 5):str(p)].mean() if a >= "2008-06" else None))
    t = pd.DataFrame(rows).set_index("month")
    print(t.round(3).to_string())
    t.to_csv(E / "ind3_ind5_analog_table.csv")


if __name__ == "__main__":
    main()
