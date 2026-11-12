import numpy as np
import pandas as pd
import pytest

from macro_analog import analogs, features as F, market
from macro_analog.release_calendar import ET

RULES = {"PAYEMS": "first_friday_next_month_0830", "UNRATE": "first_friday_next_month_0830",
         "CPIAUCSL": "day15_next_month_0830", "CPILFESL": "day15_next_month_0830", "DFF": "next_day_0900"}


def synthetic(n=36, unrate=None):
    idx = pd.date_range("2000-01-01", periods=n, freq="MS")
    series = {"PAYEMS": pd.Series(100000 + 100 * np.arange(n), idx, dtype=float),            # thousands, +100k per month
              "UNRATE": pd.Series(4.0 + 0.05 * np.arange(n), idx),
              "CPIAUCSL": pd.Series(100 * 1.02 ** (np.arange(n) / 12), idx),                 # exactly 2% a year
              "CPILFESL": pd.Series(100 * 1.01 ** np.arange(n), idx)}                         # 1% a month
    if unrate is not None:
        series["UNRATE"] = unrate
    d = pd.date_range("1999-01-01", "2003-01-01", freq="D")
    series["DFF"] = pd.Series(2.0, d)
    series["DFF"].loc["2001-06-01":] = 3.0
    return series


def ts(s):
    return pd.Timestamp(s, tz=ET)


# ---- unit conversions -------------------------------------------------------------------
def test_units_and_transforms():
    inp = F.prepare(synthetic(), RULES)
    row = F.state_at(ts("2002-06-30 16:00"), inp)           # latest labor obs = 2002-05 (released first Friday of June)
    assert row["labor_obs_month"] == pd.Timestamp("2002-05-01")
    p = 100000 + 100 * 28                                    # PAYEMS at 2002-05 (index 28)
    assert row["payroll_growth_3m"] == pytest.approx(100 * 300 / (p - 300))   # percent of the level 3 months earlier
    assert row["payroll_growth_6m"] == pytest.approx(100 * 600 / (p - 600))
    assert row["unrate_chg_6m"] == pytest.approx(0.05 * 6)                    # percentage points
    assert row["cpi_yoy"] == pytest.approx(2.0)                               # index-based YoY, percent
    assert row["core_cpi_6m_ann"] == pytest.approx(100 * (1.01 ** 12 - 1))    # compounded annualisation
    assert row["ffr_level"] == 3.0 and row["ffr_chg_6m"] == pytest.approx(0.0)   # step to 3.0 happened 13 months earlier
    mid = F.state_at(ts("2001-09-30 16:00"), inp)                                 # 6 months earlier the rate was 2.0
    assert mid["ffr_level"] == 3.0 and mid["ffr_chg_6m"] == pytest.approx(1.0)


# ---- no look-ahead -----------------------------------------------------------------------
def test_value_not_usable_before_its_release_time():
    inp = F.prepare(synthetic(), RULES)
    before = F.state_at(ts("2000-03-03 08:00"), inp)         # Feb data is released Fri 2000-03-03 08:30 ET
    after = F.state_at(ts("2000-03-03 09:00"), inp)
    assert before["labor_obs_month"] == pd.Timestamp("2000-01-01")
    assert after["labor_obs_month"] == pd.Timestamp("2000-02-01")
    assert before["labor_release_ts"] <= before["as_of"] and after["labor_release_ts"] <= after["as_of"]


def test_all_month_end_signals_use_only_released_data():
    inp = F.prepare(synthetic(), RULES)
    st = F.build_state_table(inp, pd.date_range("2001-01-01", "2002-12-01", freq="MS"))
    for c in ["labor_release_ts", "unrate_release_ts", "cpi_release_ts", "core_cpi_release_ts"]:
        assert (st[c] <= st["as_of"]).all()


def test_daily_policy_rate_excludes_as_of_day():
    s = synthetic()
    s["DFF"].loc["2001-06-15"] = 9.0
    inp = F.prepare(s, RULES)
    assert F.state_at(ts("2001-06-15 14:00"), inp)["ffr_obs_date"] == pd.Timestamp("2001-06-14")


# ---- missing data is never filled --------------------------------------------------------
def test_missing_observation_stays_nan():
    s = synthetic()
    u = s["UNRATE"].copy()
    u.loc["2002-05-01"] = np.nan
    s["UNRATE"] = u
    row = F.state_at(ts("2002-06-30 16:00"), F.prepare(s, RULES))
    assert np.isnan(row["unrate_level"]) and np.isnan(row["unrate_chg_6m"])
    assert row["payroll_growth_3m"] > 0                      # other series unaffected


# ---- market outcomes ----------------------------------------------------------------------
def test_mdd_after_a_rally_with_higher_close():
    st = market.path_stats(np.array([100, 150, 120, 160.0]))
    assert st["ret"] == pytest.approx(0.60)
    assert st["mdd"] == pytest.approx(120 / 150 - 1)         # -20% from the 150 peak even though the close is higher
    assert st["worst_from_entry"] == pytest.approx(0.0)      # never below the entry price: a different number


def test_mdd_peak_starts_at_entry_price():
    st = market.path_stats(np.array([100, 120, 90, 110.0]))
    assert st["mdd"] == pytest.approx(90 / 120 - 1)
    assert st["worst_from_entry"] == pytest.approx(-0.10)
    st = market.path_stats(np.array([100, 90, 95.0]))        # falls straight from the entry price
    assert st["mdd"] == pytest.approx(-0.10)


def test_unrealised_horizon_is_dropped():
    days = pd.bdate_range("2000-01-03", "2001-06-29")
    px = pd.Series(np.linspace(100, 130, len(days)), days)
    out = market.outcomes(px, pd.date_range("2000-01-01", "2001-06-01", freq="MS"))
    assert out.index.max() == pd.Timestamp("2000-06-01")      # June 2000 + 12 months = June 2001, the last full month
    assert (out.end_date <= px.index[-1]).all()
    assert out.loc["2000-01-01", "entry_date"] == pd.Timestamp("2000-01-31")


# ---- distance, weights, de-duplication ---------------------------------------------------
GROUPS = {"employment": ["a", "b"], "inflation": ["c"], "policy": ["d"]}
W = {"employment": 0.4, "inflation": 0.3, "policy": 0.3}


def pool(n=60, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.normal(size=(n, 4)), index=pd.date_range("1990-01-01", periods=n, freq="MS"), columns=list("abcd"))


def test_distance_decomposes_and_weights_sum_to_one():
    p = pool()
    cur = pd.Series([0.1, 0.2, 0.3, 0.4], index=list("abcd"))
    r = analogs.rank_candidates(p, cur, GROUPS, W, analogs.fit_scaler(p, list("abcd")))
    assert sum(W.values()) == pytest.approx(1)
    assert np.allclose(r["D"], sum(W[g] * r[f"D_{g}"] for g in W))
    assert np.allclose(r["D_employment"], (r["z2_a"] + r["z2_b"]) / 2)     # group = mean of its features, so group size does not matter
    assert r["D"].is_monotonic_increasing


def test_missing_features_are_rejected_not_zeroed():
    p = pool()
    cur = pd.Series([0.1, 0.2, 0.3, 0.4], index=list("abcd"))
    sc = analogs.fit_scaler(p, list("abcd"))
    p.iloc[3, 1] = np.nan
    with pytest.raises(ValueError):
        analogs.rank_candidates(p, cur, GROUPS, W, sc)


def test_top_picks_are_separated_and_raw_list_is_untouched():
    p = pool(120)
    cur = p.iloc[50] + 0.01
    r = analogs.rank_candidates(p, cur, GROUPS, W, analogs.fit_scaler(p, list("abcd")))
    top = analogs.select_top(r, 5, 18)
    gaps = [abs(analogs._m(a) - analogs._m(b)) for i, a in enumerate(top.index) for b in top.index[:i]]
    assert len(top) == 5 and min(gaps) >= 18
    assert top.index[0] == r.index[0]                                       # best month is always kept
