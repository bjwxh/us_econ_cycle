"""Build web/data.js (window.DATA = ...) for the web app from the 12-month-window analog run.

Run from the project root:  PYTHONPATH=src python3 scripts/build_web_data.py
"""
import json
from pathlib import Path

import pandas as pd

from macro_analog import interactive as I

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "outputs" / "p0_trend_w12" / "analog_top10_trend.csv"
AS_OF = "2026-11-10"
I.LOOKBACK = 24                      # 25 monthly points per panel, month -24 .. 0

payload = I.build_payload(AS_OF, CSV, market=True)
top = pd.read_csv(CSV)
payload["meta"] = dict(as_of=AS_OF, target=payload["series"][0]["id"],
                       analogs=[dict(id=r.obs_month, rank=i + 1, D=round(float(r.D), 3)) for i, r in top.iterrows()])
# dark-theme palette: 10 bright analog colours (no yellow: yellow is reserved for the current state)
PALETTE = ["#00d4ff", "#f9677f", "#b388ff", "#4ade80", "#ff9f43", "#ff7ac6", "#7aa7ff", "#b5e61d", "#2dd4bf", "#cbd5e1"]
for s_, c in zip(payload["series"][1:], PALETTE):
    s_["color"] = c
payload["series"][0]["color"] = "#ffe600"
payload["colors"] = dict(bg="#061128", cyan="#00fcff", yellow="#ffe600", ink="#ffffff", ink2="#c8d4e6",
                         muted="#8aa0b8", grid="#2a3b57", up="#4ade80", down="#f9677f")
payload["meta"]["n_candidates"] = len(pd.period_range("1990-01", pd.Period(payload["series"][0]["id"]) - 13, freq="M"))
payload["panels"] = [dict(key=p["key"], section=p.get("section")) for p in payload["panels"]]
for s in payload["series"]:
    s.pop("label", None)
out = ROOT / "web" / "data.js"
out.write_text("window.DATA = " + json.dumps(payload, separators=(",", ":")) + ";\n")
print(out, out.stat().st_size, "bytes;", len(payload["series"]) - 1, "analogs;", len(payload["x"]), "points")
