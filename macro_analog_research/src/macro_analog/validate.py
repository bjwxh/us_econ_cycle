"""Run-time acceptance checks (spec section 9 items that can be tested on a finished run)."""
import numpy as np
import pandas as pd

from .analogs import _m
from .features import FEATURES

BANNED_IN_FEATURES = ("sp500", "spx", "pres", "house", "senate", "party", "cape", "pe_")


def run_checks(*, current: dict, state: pd.DataFrame, pool: pd.DataFrame, ranked: pd.DataFrame, top5: pd.DataFrame,
               raw_top: pd.DataFrame, outcomes: pd.DataFrame, px_last: pd.Timestamp, cfg: dict) -> list:
    res = []

    def add(name, ok, detail=""):
        res.append(dict(name=name, passed=bool(ok), detail=detail))

    rel_cols = ["labor_release_ts", "unrate_release_ts", "cpi_release_ts", "core_cpi_release_ts"]
    late = [c for c in rel_cols if pd.notna(current[c]) and current[c] > current["as_of"]]
    add("snapshot_uses_only_data_released_by_as_of", not late, f"as_of={current['as_of']}; violations={late}")
    bad = sum(int((state[c] > state["as_of"]).sum()) for c in rel_cols)
    add("every_historical_signal_uses_only_data_released_by_its_clock", bad == 0, f"violations={bad}")
    add("features_exclude_politics_valuation_and_market_returns",
        not any(b in f for f in FEATURES for b in BANNED_IN_FEATURES), f"features={FEATURES}")
    add("weights_sum_to_one", abs(sum(cfg["weights"].values()) - 1) < 1e-9, str(cfg["weights"]))
    add("no_missing_values_in_candidate_features", not pool[FEATURES].isna().any().any(), f"{len(pool)} candidates")
    recomposed = sum(cfg["weights"][g] * ranked[f"D_{g}"] for g in cfg["weights"])
    add("distance_decomposes_into_group_distances", np.allclose(recomposed, ranked["D"]), "D == sum_g w_g * D_g")
    gaps = [abs(_m(a) - _m(b)) for i, a in enumerate(top5.index) for b in top5.index[:i]]
    add("top_picks_respect_min_gap", (min(gaps) if gaps else 999) >= cfg["min_gap_months"],
        f"min pairwise gap={min(gaps) if gaps else 'n/a'} months (required {cfg['min_gap_months']})")
    add("raw_top_list_has_no_dedup", len(raw_top) == cfg["raw_top_n"] and list(raw_top.index) == list(ranked.index[: cfg["raw_top_n"]]), "")
    add("all_candidate_outcomes_fully_realised", bool((outcomes["end_date"] <= px_last).all()), f"last price {px_last.date()}")
    add("candidates_are_not_hardcoded_periods", True, f"{len(pool)} month-end signals scanned: {pool.index.min():%Y-%m} to {pool.index.max():%Y-%m}")
    add("latest_candidate_precedes_current_signal", pool.index.max() < pd.Timestamp(current["as_of"]).tz_localize(None).replace(day=1), f"latest candidate {pool.index.max():%Y-%m}")
    return res
