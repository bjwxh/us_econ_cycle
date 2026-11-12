import numpy as np
import pandas as pd
import pytest

from macro_analog.analogs import dedup, distances
from macro_analog.features import FEATURES, build_features
from macro_analog.market import path_stats


def _s(vals):
    return pd.Series(vals, index=pd.bdate_range("2020-01-01", periods=len(vals)))


def test_mdd_rise_then_fall_but_ends_up():
    st = path_stats(_s([100, 150, 120, 130]))
    assert st["ret"] == pytest.approx(0.30)
    assert st["mdd"] == pytest.approx(-0.20)            # 150 -> 120
    assert st["worst_from_entry"] == pytest.approx(0.0)  # never below entry
    assert st["mdd_peak_date"] == _s([100, 150]).index[1]


def test_mdd_includes_entry_as_peak_and_differs_from_worst():
    st = path_stats(_s([100, 120, 90, 110]))
    assert st["mdd"] == pytest.approx(-0.25)             # 120 -> 90
    assert st["worst_from_entry"] == pytest.approx(-0.10)
    assert path_stats(_s([100, 95, 90]))["mdd"] == pytest.approx(-0.10)  # entry is the peak


def _raw(n=24):
    idx = pd.period_range("2020-01", periods=n, freq="M")
    pay = pd.Series(150000 + 100 * np.arange(n, dtype=float), index=idx)
    return dict(PAYEMS=pay, UNRATE=pd.Series(4.0, index=idx), CPIAUCSL=pd.Series(100 * 1.002 ** np.arange(n), index=idx),
                CPILFESL=pd.Series(100 * 1.001 ** np.arange(n), index=idx), FEDFUNDS=pd.Series(1.0, index=idx))


def test_units_and_missing_not_zero_filled():
    raw = _raw()
    raw["UNRATE"].iloc[10] = np.nan
    f = build_features(raw)
    assert f["pay_g3"].iloc[-1] == pytest.approx(300 / (150000 + 100 * 20) * 100)  # percent of level, thousands cancel
    assert f["cpi_ann6"].iloc[-1] == pytest.approx((1.002 ** 12 - 1) * 100)
    assert np.isnan(f["unrate"].iloc[10]) and np.isnan(f["unrate_chg6"].iloc[16])


def test_distance_decomposes_and_rejects_nan():
    rng = np.random.default_rng(0)
    pool = pd.DataFrame(rng.normal(size=(50, len(FEATURES))), columns=FEATURES,
                        index=pd.period_range("2000-01", periods=50, freq="M"))
    target = pool.iloc[7].copy()
    w = dict(employment=0.4, inflation=0.3, policy=0.3)
    d = distances(pool, target, w)
    assert d.index[0] == pool.index[7] and d["D"].iloc[0] == pytest.approx(0)
    assert (d["D"] - d[[c for c in d if c.startswith("contrib_")]].sum(axis=1)).abs().max() < 1e-12
    bad = pool.copy(); bad.iloc[0, 0] = np.nan
    with pytest.raises(ValueError):
        distances(bad, target, w)


def test_dedup_gap():
    idx = pd.period_range("2000-01", periods=100, freq="M")
    ranked = pd.DataFrame({"D": np.arange(100)}, index=idx)
    top = dedup(ranked, 5, 18)
    gaps = [abs((a - b).n) for i, a in enumerate(top.index) for b in top.index[:i]]
    assert len(top) == 5 and min(gaps) >= 18
