"""Features known at an as-of timestamp. A value is usable only if its release time <= as_of.
Missing values stay NaN (never zero-filled); a signal with any NaN feature is not a candidate."""
import numpy as np
import pandas as pd

from . import release_calendar as rc

FEATURES = ["unrate_level", "unrate_chg_6m", "payroll_growth_3m", "payroll_growth_6m",
            "cpi_yoy", "core_cpi_yoy", "core_cpi_6m_ann", "ffr_level", "ffr_chg_6m"]
MONTHLY = ["PAYEMS", "UNRATE", "CPIAUCSL", "CPILFESL"]


def prepare(series: dict, rules: dict) -> dict:
    """Full monthly grids (gaps become NaN rows) plus rule-based release times, extended 3 months
    past the last observation so we can tell when the rules say a report is out but our data lacks it."""
    out = {}
    for sid in MONTHLY:
        s = series[sid]
        idx = pd.date_range(s.index.min(), s.index.max(), freq="MS")
        ext = pd.date_range(s.index.min(), s.index.max() + pd.offsets.MonthBegin(3), freq="MS")
        out[sid] = dict(values=s.reindex(idx).to_numpy(float), index=idx,
                        avail_ns=rc.monthly_release_times(ext, rules[sid]).tz_convert("UTC").asi8, ext=ext)
    out["DFF"] = series["DFF"].dropna().sort_index()
    return out


def _pos(d: dict, as_of: pd.Timestamp):
    """(position used, position the rule expects, release timestamp of the used observation)."""
    expected = int(np.searchsorted(d["avail_ns"], as_of.tz_convert("UTC").value, side="right")) - 1
    used = min(expected, len(d["index"]) - 1)
    rel = pd.Timestamp(d["avail_ns"][used], tz="UTC").tz_convert(rc.ET) if used >= 0 else pd.NaT
    return used, expected, rel


def _val(d, p):
    return d["values"][p] if 0 <= p < len(d["values"]) else np.nan


def state_at(as_of: pd.Timestamp, inp: dict, zlb_threshold: float = 0.30) -> dict:
    row = {}
    meta = {}
    for sid in MONTHLY:
        p, e, rel = _pos(inp[sid], as_of)
        meta[sid] = dict(p=p, obs_month=inp[sid]["index"][p] if p >= 0 else pd.NaT, release_ts=rel,
                         rule_expected_obs_month=inp[sid]["ext"][e] if e >= 0 else pd.NaT)
    pu, pp, pc, pk = (meta[s]["p"] for s in ["UNRATE", "PAYEMS", "CPIAUCSL", "CPILFESL"])
    U, P, C, K = (inp[s] for s in ["UNRATE", "PAYEMS", "CPIAUCSL", "CPILFESL"])
    row["unrate_level"] = _val(U, pu)
    row["unrate_chg_6m"] = _val(U, pu) - _val(U, pu - 6)                       # percentage points
    row["payroll_growth_3m"] = 100 * (_val(P, pp) - _val(P, pp - 3)) / _val(P, pp - 3)   # % of employment level 3m ago
    row["payroll_growth_6m"] = 100 * (_val(P, pp) - _val(P, pp - 6)) / _val(P, pp - 6)
    row["cpi_yoy"] = 100 * (_val(C, pc) / _val(C, pc - 12) - 1)
    row["core_cpi_yoy"] = 100 * (_val(K, pk) / _val(K, pk - 12) - 1)
    row["core_cpi_6m_ann"] = 100 * ((_val(K, pk) / _val(K, pk - 6)) ** 2 - 1)   # compounded annualised
    dff = inp["DFF"]
    d_obs = dff.index[dff.index <= rc.daily_available_through(as_of)]
    if len(d_obs):
        d0 = d_obs[-1]
        row["ffr_level"] = float(dff.loc[d0])
        d6 = d0 - pd.DateOffset(months=6)
        row["ffr_chg_6m"] = row["ffr_level"] - float(dff.asof(d6)) if d6 >= dff.index[0] else np.nan
        row["ffr_obs_date"] = d0
    else:
        row.update(ffr_level=np.nan, ffr_chg_6m=np.nan, ffr_obs_date=pd.NaT)
    # diagnostics (not in the distance)
    row["real_rate_headline"] = row["ffr_level"] - row["cpi_yoy"]
    row["zlb_flag"] = bool(row["ffr_level"] < zlb_threshold) if np.isfinite(row["ffr_level"]) else False
    row["labor_obs_month"], row["labor_release_ts"] = meta["PAYEMS"]["obs_month"], meta["PAYEMS"]["release_ts"]
    row["unrate_obs_month"], row["unrate_release_ts"] = meta["UNRATE"]["obs_month"], meta["UNRATE"]["release_ts"]
    row["cpi_obs_month"], row["cpi_release_ts"] = meta["CPIAUCSL"]["obs_month"], meta["CPIAUCSL"]["release_ts"]
    row["core_cpi_obs_month"], row["core_cpi_release_ts"] = meta["CPILFESL"]["obs_month"], meta["CPILFESL"]["release_ts"]
    row["rule_expected_labor_month"] = meta["PAYEMS"]["rule_expected_obs_month"]
    row["rule_expected_cpi_month"] = meta["CPIAUCSL"]["rule_expected_obs_month"]
    row["as_of"] = as_of
    return row


def month_end_as_of(month_start: pd.Timestamp) -> pd.Timestamp:
    """Signal clock for a historical month: the month's last calendar day, 16:00 ET."""
    eom = month_start + pd.offsets.MonthEnd(0)
    return (eom + pd.Timedelta(hours=16)).tz_localize(rc.ET)


def build_state_table(inp: dict, months: pd.DatetimeIndex, zlb_threshold: float = 0.30) -> pd.DataFrame:
    rows = {m: state_at(month_end_as_of(m), inp, zlb_threshold) for m in months}
    df = pd.DataFrame.from_dict(rows, orient="index")
    num = FEATURES + ["real_rate_headline"]
    df[num] = df[num].astype(float)   # mixed timestamp/number rows otherwise leave these as object dtype
    return df
