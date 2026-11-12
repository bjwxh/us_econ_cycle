"""Distance-based analog search. Market data is never used here."""
import numpy as np
import pandas as pd

from .features import GROUPS


def distances(pool: pd.DataFrame, target: pd.Series, weights: dict) -> pd.DataFrame:
    """pool: candidate feature rows (no NaN); target: feature Series. Robust scaling (median/IQR)
    is fitted on the pool only. D_group = mean squared standardized difference in the group;
    D = sum_g w_g * D_group, so each group contributes by its weight, not its feature count."""
    cols = [c for g in GROUPS.values() for c in g]
    if pool[cols].isna().any().any() or target[cols].isna().any():
        raise ValueError("NaN in features; drop incomplete months before matching")
    assert abs(sum(weights.values()) - 1) < 1e-9 and set(weights) == set(GROUPS)
    med = pool[cols].median()
    iqr = pool[cols].quantile(0.75) - pool[cols].quantile(0.25)
    assert (iqr > 0).all()
    z = (pool[cols] - med) / iqr
    zt = (target[cols] - med) / iqr
    out = pd.DataFrame(index=pool.index)
    for g, fs in GROUPS.items():
        out[f"D_{g}"] = ((z[fs] - zt[fs]) ** 2).mean(axis=1)
    out["D"] = sum(weights[g] * out[f"D_{g}"] for g in GROUPS)
    for g in GROUPS:
        out[f"contrib_{g}"] = weights[g] * out[f"D_{g}"]
    return out.join(pool[cols]).sort_values("D")


def dedup(ranked: pd.DataFrame, k: int, min_gap_months: int) -> pd.DataFrame:
    """Greedy: walk the ranking, keep a month only if >= min_gap_months from all kept months."""
    kept = []
    for m in ranked.index:
        if all(abs((m - p).n) >= min_gap_months for p in kept):
            kept.append(m)
        if len(kept) == k:
            break
    return ranked.loc[kept]
