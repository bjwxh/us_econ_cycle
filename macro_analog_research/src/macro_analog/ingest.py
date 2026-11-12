"""Download and cache raw source data. Raw files are append-only (never overwritten) and every
download is logged with source URL, UTC download time, units and row counts."""
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

FRED_META = {
    "PAYEMS": dict(unit="thousands of persons", seasonal_adjustment="SA", frequency="monthly"),
    "UNRATE": dict(unit="percent", seasonal_adjustment="SA", frequency="monthly"),
    "CPIAUCSL": dict(unit="index 1982-84=100", seasonal_adjustment="SA", frequency="monthly"),
    "CPILFESL": dict(unit="index 1982-84=100", seasonal_adjustment="SA", frequency="monthly"),
    "DFF": dict(unit="percent", seasonal_adjustment="NSA", frequency="daily"),
}
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
STAMP = "%Y%m%dT%H%M%SZ"


def _get(url: str, tries: int = 3) -> bytes:
    """FRED drops connections that send a custom User-Agent, so the urllib default is used."""
    for k in range(tries):
        try:
            return urllib.request.urlopen(url, timeout=120).read()
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(3 * (k + 1))


def _log(raw_dir: Path, rec: dict) -> None:
    with open(raw_dir / "provenance_log.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")


def _latest_or_download(raw_dir, prefix, fetch, refresh):
    """Return (path, downloaded_at_utc). `fetch()` must return raw CSV bytes."""
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(raw_dir.glob(f"{prefix}_*.csv"))
    if existing and not refresh:
        path = existing[-1]
    else:
        stamp = pd.Timestamp.now(tz="UTC").strftime(STAMP)
        path = raw_dir / f"{prefix}_{stamp}.csv"
        path.write_bytes(fetch())
    return path, pd.to_datetime(path.stem.split("_")[-1], format=STAMP, utc=True)


def load_fred(series_id: str, raw_dir, refresh=False):
    url = FRED_URL + series_id
    fetch = lambda: _get(url)
    path, dl = _latest_or_download(raw_dir, f"FRED_{series_id}", fetch, refresh)
    df = pd.read_csv(path)
    df.columns = ["date", "value"]
    s = pd.Series(pd.to_numeric(df["value"], errors="coerce").to_numpy(),
                  index=pd.to_datetime(df["date"]), name=series_id)
    rec = dict(series_id=series_id, provider="FRED (St. Louis Fed), latest revised values", source_url=url,
               downloaded_at_utc=str(dl), file=path.name, rows=len(s), non_missing=int(s.notna().sum()),
               first_obs=str(s.dropna().index.min().date()), last_obs=str(s.dropna().index.max().date()),
               **FRED_META[series_id])
    if not (Path(raw_dir) / "provenance_log.jsonl").exists() or path.name not in (Path(raw_dir) / "provenance_log.jsonl").read_text():
        _log(Path(raw_dir), rec)
    return s, rec


def load_spx(raw_dir, refresh=False):
    """S&P 500 PRICE index daily close from Yahoo Finance (^GSPC) via yfinance. Unofficial source,
    personal-research use; dividends excluded."""
    def fetch():
        import yfinance as yf
        px = yf.download("^GSPC", start="1950-01-01", progress=False, auto_adjust=False)["Close"].squeeze().dropna()
        return px.rename("close").to_csv().encode()
    path, dl = _latest_or_download(raw_dir, "YAHOO_GSPC", fetch, refresh)
    df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    s = df["close"].astype(float)
    rec = dict(series_id="^GSPC", provider="Yahoo Finance via yfinance (unofficial; price index, no dividends)",
               source_url="https://finance.yahoo.com/quote/%5EGSPC/history", downloaded_at_utc=str(dl),
               file=path.name, rows=len(s), first_obs=str(s.index.min().date()), last_obs=str(s.index.max().date()),
               unit="index points", seasonal_adjustment="n/a", frequency="daily")
    if not (Path(raw_dir) / "provenance_log.jsonl").exists() or path.name not in (Path(raw_dir) / "provenance_log.jsonl").read_text():
        _log(Path(raw_dir), rec)
    return s, rec
