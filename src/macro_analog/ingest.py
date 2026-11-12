"""Download raw data (append-only) and record provenance.

FRED key: env FRED_API_KEY, else ~/.api_keys/fred/fred_api.json.
Schwab: reads ~/.api_keys/schwab/data_token.json / data_api.json read-only; a refreshed
access token is kept in memory and never written back.
"""
import base64
import datetime as dt
import json
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
FRED_URL = "https://api.stlouisfed.org/fred"
SCHWAB_DIR = Path.home() / ".api_keys" / "schwab"

# series_id -> (unit, seasonal_adjustment)
FRED_SERIES = {
    "PAYEMS": ("thousands of persons", "SA"),
    "UNRATE": ("percent", "SA"),
    "CPIAUCSL": ("index 1982-84=100", "SA"),
    "CPILFESL": ("index 1982-84=100", "SA"),
    "FEDFUNDS": ("percent, monthly average", "NSA"),
    "DFF": ("percent, daily", "NSA"),
    "USREC": ("0/1 NBER recession indicator", "NSA"),
}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _log(entry: dict) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    with open(RAW / "manifest.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def fred_key() -> str:
    key = os.environ.get("FRED_API_KEY")
    if key:
        return key
    return json.load(open(Path.home() / ".api_keys" / "fred" / "fred_api.json"))["api_key"]


def fetch_fred(series_id: str, start: str = "1989-01-01", vintage: str | None = None) -> Path:
    """vintage=None -> latest revised history. vintage='YYYY-MM-DD' -> data as known on that date."""
    params = dict(api_key=fred_key(), file_type="json", series_id=series_id, observation_start=start)
    if vintage:
        params.update(realtime_start=vintage, realtime_end=vintage)
    r = requests.get(f"{FRED_URL}/series/observations", params=params, timeout=60)
    r.raise_for_status()
    stamp = _now()
    tag = f"asof{vintage}" if vintage else "revised"
    path = RAW / f"fred_{series_id}_{tag}_{stamp}.json"
    RAW.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text)
    unit, sa = FRED_SERIES[series_id]
    _log(dict(series_id=series_id, provider="FRED", source_url=f"{FRED_URL}/series/observations?series_id={series_id}",
              downloaded_at_utc=stamp, vintage_date=vintage or "latest", unit=unit,
              seasonal_adjustment=sa, file=path.name))
    return path


def _schwab_access_token() -> str:
    tok = json.load(open(SCHWAB_DIR / "data_token.json"))["token"]
    if tok["expires_at"] - time.time() > 120:
        return tok["access_token"]
    api = json.load(open(SCHWAB_DIR / "data_api.json"))
    basic = base64.b64encode(f"{api['api_key']}:{api['api_secret']}".encode()).decode()
    r = requests.post("https://api.schwabapi.com/v1/oauth/token",
                      headers={"Authorization": f"Basic {basic}"},
                      data={"grant_type": "refresh_token", "refresh_token": tok["refresh_token"]}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def fetch_spx(start: str = "1990-01-01") -> Path:
    start_ms = int(dt.datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    r = requests.get("https://api.schwabapi.com/marketdata/v1/pricehistory",
                     headers={"Authorization": f"Bearer {_schwab_access_token()}"},
                     params=dict(symbol="$SPX", periodType="year", frequencyType="daily", frequency=1,
                                 startDate=start_ms, endDate=int(time.time() * 1000),
                                 needExtendedHoursData="false"), timeout=60)
    r.raise_for_status()
    stamp = _now()
    path = RAW / f"spx_schwab_{stamp}.json"
    path.write_text(r.text)
    _log(dict(series_id="$SPX", provider="Schwab marketdata pricehistory (daily candles)",
              source_url="https://api.schwabapi.com/marketdata/v1/pricehistory", downloaded_at_utc=stamp,
              vintage_date="latest", unit="index points, price return only", seasonal_adjustment="n/a",
              file=path.name))
    return path


def latest(prefix: str) -> Path:
    files = sorted(RAW.glob(f"{prefix}_*.json"))
    if not files:
        raise FileNotFoundError(f"no raw file for {prefix}; run the fetch step")
    return files[-1]


def first_release_date(series_id: str, obs_date: str, as_of: str) -> str | None:
    """Date `obs_date` first appeared in FRED/ALFRED (initial release only), known by `as_of`."""
    r = requests.get(f"{FRED_URL}/series/observations",
                     params=dict(api_key=fred_key(), file_type="json", series_id=series_id,
                                 observation_start=obs_date, observation_end=obs_date,
                                 realtime_start="2020-01-01", realtime_end=as_of, output_type=4), timeout=60)
    r.raise_for_status()
    obs = r.json()["observations"]
    return obs[0]["realtime_start"] if obs else None
