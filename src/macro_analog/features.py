"""Monthly macro features. Observation month m = month the data describe.

Units: UNRATE and rates in percent / percentage points; PAYEMS growth in percent of the
employment level (PAYEMS is in thousands of persons); CPI changes are annualized percent
computed from SA index levels. Missing months stay NaN (never zero-filled).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

EMP = ["unrate", "unrate_chg6", "pay_g3", "pay_g6"]
INF = ["cpi_ann6", "core_ann6"]
POL = ["ff", "ff_chg6"]
GROUPS = {"employment": EMP, "inflation": INF, "policy": POL}
FEATURES = EMP + INF + POL


def load_series(path: Path) -> pd.Series:
    obs = json.load(open(path))["observations"]
    s = pd.Series({pd.Period(o["date"][:7], "M"): (np.nan if o["value"] == "." else float(o["value"]))
                   for o in obs})
    return s.sort_index()


def build_features(raw: dict) -> pd.DataFrame:
    """raw: dict of monthly Series keyed PAYEMS, UNRATE, CPIAUCSL, CPILFESL, FEDFUNDS."""
    idx = pd.period_range(min(s.index.min() for s in raw.values()),
                          max(s.index.max() for s in raw.values()), freq="M")
    r = {k: v.reindex(idx) for k, v in raw.items()}  # gaps (e.g. 2025-10) stay NaN
    f = pd.DataFrame(index=idx)
    f["unrate"] = r["UNRATE"]
    f["unrate_chg6"] = r["UNRATE"] - r["UNRATE"].shift(6)
    f["pay_g3"] = (r["PAYEMS"] / r["PAYEMS"].shift(3) - 1) * 100
    f["pay_g6"] = (r["PAYEMS"] / r["PAYEMS"].shift(6) - 1) * 100
    f["cpi_ann6"] = ((r["CPIAUCSL"] / r["CPIAUCSL"].shift(6)) ** 2 - 1) * 100
    f["core_ann6"] = ((r["CPILFESL"] / r["CPILFESL"].shift(6)) ** 2 - 1) * 100
    f["ff"] = r["FEDFUNDS"]
    f["ff_chg6"] = r["FEDFUNDS"] - r["FEDFUNDS"].shift(6)
    return f
