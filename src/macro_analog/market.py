"""S&P 500 (price index) forward returns and drawdowns from daily closes."""
import json
from pathlib import Path

import pandas as pd


def load_spx(path: Path) -> pd.Series:
    c = json.load(open(path))["candles"]
    s = pd.Series({pd.Timestamp(x["datetime"], unit="ms").normalize(): x["close"] for x in c}).sort_index()
    assert s.index.is_unique and (s.index.dayofweek < 5).all(), "unexpected SPX calendar"
    return s


def month_end_day(spx: pd.Series, period: pd.Period):
    """Last trading day in `period`, or None if the month is not fully observed."""
    if period >= spx.index[-1].to_period("M"):
        return None  # last data month may be incomplete
    days = spx.index[(spx.index.to_period("M") == period)]
    return days[-1] if len(days) else None


def path_stats(close: pd.Series) -> dict:
    """close: daily closes from entry (first element) to horizon end, inclusive."""
    entry = close.iloc[0]
    dd = close / close.cummax() - 1
    trough = dd.idxmin()
    return dict(
        ret=close.iloc[-1] / entry - 1,
        mdd=dd.min(), mdd_trough_date=trough, mdd_peak_date=close.loc[:trough].idxmax(),
        worst_from_entry=close.min() / entry - 1, worst_from_entry_date=close.idxmin(),
    )


def outcome(spx: pd.Series, signal_period: pd.Period) -> dict | None:
    """Entry = close on last trading day of signal_period. Horizon end = last trading day of
    signal_period + h months (h=3,6,12). Returns None unless the 12m horizon is fully realized."""
    entry_day = month_end_day(spx, signal_period)
    end12 = month_end_day(spx, signal_period + 12)
    if entry_day is None or end12 is None:
        return None
    close = spx.loc[entry_day:end12]
    st = path_stats(close)
    out = dict(signal_date=entry_day, end_date=end12, entry_close=close.iloc[0],
               R_12m=st["ret"], MDD_12m=st["mdd"], mdd_peak_date=st["mdd_peak_date"],
               mdd_trough_date=st["mdd_trough_date"], worst_from_entry=st["worst_from_entry"],
               worst_from_entry_date=st["worst_from_entry_date"],
               dd_ge_10=bool(st["mdd"] <= -0.10), dd_ge_20=bool(st["mdd"] <= -0.20))
    for h in (3, 6):
        e = month_end_day(spx, signal_period + h)
        out[f"R_{h}m"] = spx[e] / close.iloc[0] - 1
    return out
