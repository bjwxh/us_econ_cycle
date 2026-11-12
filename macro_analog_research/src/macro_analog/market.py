"""S&P 500 outcomes after each signal. Never used for matching."""
import numpy as np
import pandas as pd


def path_stats(prices: np.ndarray) -> dict:
    """prices[0] is the entry close. Max drawdown (MDD) = worst fall from the running peak,
    where the peak starts at the entry price and includes every later close; worst_from_entry is
    the lowest close relative to entry (a different number)."""
    running = np.maximum.accumulate(prices)
    dd = prices / running - 1
    t = int(np.argmin(dd))
    peak = int(np.argmax(prices[: t + 1]))
    w = int(np.argmin(prices))
    return dict(mdd=float(dd[t]), mdd_trough_i=t, mdd_peak_i=peak,
                worst_from_entry=float(prices[w] / prices[0] - 1), worst_i=w, ret=float(prices[-1] / prices[0] - 1))


def _end_date(px: pd.Series, eom_target: pd.Timestamp):
    """Last trading day <= target; None if the data does not yet cover the whole month."""
    i = px.index.searchsorted(eom_target, side="right") - 1
    if i < 0:
        return None
    d = px.index[i]
    # realised if data runs past d, or no business day remains between d and the target month-end
    covered = px.index[-1] > d or len(pd.bdate_range(d + pd.Timedelta(days=1), eom_target)) == 0
    return d if covered else None


def outcomes(px: pd.Series, signal_months: pd.DatetimeIndex, horizon: int = 12) -> pd.DataFrame:
    """Entry = last trading day on/before the signal month's end. Exit = last trading day on/before
    the end of the month `horizon` months later. Months whose exit is not yet realised are dropped."""
    rows = []
    for m in signal_months:
        eom = m + pd.offsets.MonthEnd(0)
        i0 = px.index.searchsorted(eom, side="right") - 1
        if i0 < 0:
            continue
        d0 = px.index[i0]
        rec = dict(signal_month=m, entry_date=d0, entry_price=float(px.iloc[i0]))
        ok = True
        for h in sorted({3, 6, 12, horizon}):
            de = _end_date(px, eom + pd.offsets.MonthEnd(h))
            if de is None:
                ok = h != horizon
                continue
            rec[f"r_{h}m"] = float(px.loc[de] / px.iloc[i0] - 1)
            if h == horizon:
                rec["r_h"] = rec[f"r_{h}m"]
            if h == horizon:
                seg = px.loc[d0:de].to_numpy()
                s = path_stats(seg)
                dates = px.loc[d0:de].index
                rec.update(end_date=de, mdd_h=s["mdd"], mdd_peak_date=dates[s["mdd_peak_i"]],
                           mdd_trough_date=dates[s["mdd_trough_i"]], worst_from_entry=s["worst_from_entry"],
                           worst_date=dates[s["worst_i"]], dd_ge_10=s["mdd"] <= -0.10, dd_ge_20=s["mdd"] <= -0.20)
        if ok and "end_date" in rec:
            rows.append(rec)
    return pd.DataFrame(rows).set_index("signal_month")
