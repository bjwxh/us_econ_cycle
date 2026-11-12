"""Bridge the top-10 share of S&P 500 market cap from the last Goldman/J.P. Morgan chart point (about 2026-06)
to today, using Schwab prices and market caps of the largest US companies.

share_t = k * sum(top-10 company caps at t) / SPX_t, where company cap_t = cap_now * price_t / price_now
(constant share count over a few months) and k is calibrated so that the bridge reproduces the Goldman
series over its last months. The S&P 500 total market cap is proportional to the index level (the divisor
only moves with index maintenance), so SPX_t stands in for the unknown denominator.

python -m macro_analog.concentration     (fetch + build; writes data/external/top10_cap_share_bridge.csv)
"""
import datetime as dt
import json
import time

import pandas as pd
import requests

from . import ingest

CANDIDATES = ["AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "LLY", "BRK/B", "WMT", "JPM",
              "AMD", "MU", "V", "JNJ", "XOM"]
START = "2026-01-02"
GS_CSV = ingest.ROOT / "data" / "external" / "gs_top10_concentration_eotm_jun2026.csv"


def _get(url, **params):
    r = requests.get(url, headers={"Authorization": f"Bearer {ingest._schwab_access_token()}"}, params=params, timeout=60)
    r.raise_for_status()
    return r


def fetch() -> dict:
    stamp = ingest._now()
    fund = _get("https://api.schwabapi.com/marketdata/v1/instruments", symbol=",".join(CANDIDATES), projection="fundamental").text
    p = ingest.RAW / f"schwab_fundamentals_{stamp}.json"
    p.write_text(fund)
    ingest._log(dict(series_id="company market caps", provider="Schwab marketdata instruments (fundamental)",
                     source_url="https://api.schwabapi.com/marketdata/v1/instruments", downloaded_at_utc=stamp,
                     vintage_date="latest", unit="USD", seasonal_adjustment="n/a", file=p.name))
    start_ms = int(dt.datetime.strptime(START, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    px = {}
    for s in CANDIDATES + ["$SPX"]:
        px[s] = json.loads(_get("https://api.schwabapi.com/marketdata/v1/pricehistory", symbol=s, periodType="year",
                                frequencyType="daily", frequency=1, startDate=start_ms,
                                endDate=int(time.time() * 1000), needExtendedHoursData="false").text)
    p2 = ingest.RAW / f"schwab_top_company_prices_{stamp}.json"
    p2.write_text(json.dumps(px))
    ingest._log(dict(series_id="daily closes of largest US companies", provider="Schwab marketdata pricehistory",
                     source_url="https://api.schwabapi.com/marketdata/v1/pricehistory", downloaded_at_utc=stamp,
                     vintage_date="latest", unit="USD per share (split-adjusted by provider)", seasonal_adjustment="n/a", file=p2.name))
    return dict(fund=p, px=p2)


def build(fund_path, px_path) -> pd.DataFrame:
    fund = {i["fundamental"]["symbol"]: i["fundamental"] for i in json.load(open(fund_path))["instruments"]}
    raw = json.load(open(px_path))
    close = {}
    for s, j in raw.items():
        idx = pd.to_datetime([c["datetime"] for c in j["candles"]], unit="ms", utc=True).tz_localize(None).normalize()
        close[s] = pd.Series([c["close"] for c in j["candles"]], index=idx)
    close = pd.DataFrame(close).dropna()
    spx = close.pop("$SPX")
    now_px = close.iloc[-1]
    cap_now = pd.Series({s: fund[s.replace("/", "/")]["marketCap"] for s in close.columns})
    caps = close / now_px * cap_now                      # company cap over time (constant shares)
    top10 = caps.apply(lambda r: r.nlargest(10).sum(), axis=1)
    names = caps.apply(lambda r: ",".join(r.nlargest(10).index), axis=1)
    return pd.DataFrame(dict(top10_cap=top10, spx=spx, raw_ratio=top10 / spx, members=names))


def main():
    files = fetch()
    df = build(files["fund"], files["px"])
    gs = pd.read_csv(GS_CSV, index_col=0)["top10_mktcap_pct"]
    gs.index = pd.PeriodIndex(gs.index, freq="M")
    # calibrate k on the last 3 months of the Goldman series that the daily data covers (monthly mean of each)
    m = df.groupby(df.index.to_period("M")).mean(numeric_only=True)
    ov = [p for p in gs.dropna().index[-3:] if p in m.index]
    k_each = {str(p): gs[p] / m.loc[p, "raw_ratio"] for p in ov}
    k = sum(k_each.values()) / len(k_each)
    df["top10_cap_share_pct"] = df["raw_ratio"] * k
    print("calibration k per month (rel. to mean):", {a: round(b / k, 3) for a, b in k_each.items()})
    out = ingest.ROOT / "data" / "external" / "top10_cap_share_bridge.csv"
    df.round(4).to_csv(out)
    print(df[["top10_cap", "spx", "top10_cap_share_pct", "members"]].iloc[[0, 40, 80, 100, 120, -30, -10, -1]])
    print("implied total S&P 500 cap now, $T:", round(df.top10_cap.iloc[-1] / (df.top10_cap_share_pct.iloc[-1] / 100) / 1e12, 1))


if __name__ == "__main__":
    main()
