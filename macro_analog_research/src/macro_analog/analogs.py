"""Standardised distance, group decomposition, de-duplicated top-k."""
import numpy as np
import pandas as pd


def fit_scaler(pool: pd.DataFrame, features: list) -> pd.DataFrame:
    """Median / IQR on the candidate pool known at the as-of date (no later data)."""
    q = pool[features].quantile([0.25, 0.5, 0.75])
    iqr = (q.loc[0.75] - q.loc[0.25]).replace(0, np.nan)
    if iqr.isna().any():
        raise ValueError(f"zero IQR for {list(iqr.index[iqr.isna()])}")
    return pd.DataFrame({"center": q.loc[0.5], "scale": iqr})


def rank_candidates(pool: pd.DataFrame, current: pd.Series, groups: dict, weights: dict, scaler: pd.DataFrame) -> pd.DataFrame:
    """D = sum_g w_g * D_g, D_g = mean over the group's features of squared standardised differences."""
    assert abs(sum(weights.values()) - 1) < 1e-9, "weights must sum to 1"
    feats = [f for g in groups.values() for f in g]
    if pool[feats].isna().any().any() or current[feats].isna().any():
        raise ValueError("missing feature values must be excluded before ranking, never filled")
    z2 = ((pool[feats].astype(float) - current[feats].astype(float)) / scaler["scale"]) ** 2
    out = z2.add_prefix("z2_")
    for g, fs in groups.items():
        out[f"D_{g}"] = z2[fs].mean(axis=1)
    out["D"] = sum(weights[g] * out[f"D_{g}"] for g in groups)
    return out.sort_values("D")


def _m(ts) -> int:
    return ts.year * 12 + ts.month


def select_top(ranked: pd.DataFrame, k: int, min_gap_months: int) -> pd.DataFrame:
    """Greedy by distance; every pick at least `min_gap_months` away from all earlier picks."""
    picks = []
    for ts in ranked.index:
        if all(abs(_m(ts) - _m(p)) >= min_gap_months for p in picks):
            picks.append(ts)
        if len(picks) == k:
            break
    return ranked.loc[picks]
