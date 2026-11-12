"""Release-time rules. REVISED-data mode only: these are rules, not recorded vintage dates.
Real first-release timestamps (ALFRED) are a P1 item; anything built on these rules is labelled
'revised data, rule-based release times', never 'point in time'."""
import pandas as pd

ET = "America/New_York"


def first_friday(month_start: pd.Timestamp) -> pd.Timestamp:
    return month_start + pd.Timedelta(days=(4 - month_start.weekday()) % 7)


def monthly_release_times(obs_months: pd.DatetimeIndex, rule: str) -> pd.DatetimeIndex:
    """Release timestamp (tz-aware, ET) for each monthly observation (month-start dates)."""
    nxt = obs_months + pd.offsets.MonthBegin(1)
    if rule == "first_friday_next_month_0830":
        days = pd.DatetimeIndex([first_friday(m) for m in nxt])
    elif rule == "day15_next_month_0830":
        days = nxt + pd.Timedelta(days=14)
    else:
        raise ValueError(f"unknown monthly release rule: {rule}")
    return (days + pd.Timedelta(hours=8, minutes=30)).tz_localize(ET)


def daily_available_through(as_of: pd.Timestamp) -> pd.Timestamp:
    """Last DFF observation date usable at as_of (rule next_day_0900): strictly before as_of's ET calendar date."""
    day = as_of.tz_convert(ET).normalize().tz_localize(None)
    return day - pd.Timedelta(days=1)
