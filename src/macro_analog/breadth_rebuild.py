"""Rebuild '% of S&P 500 stocks above their 200-dma' for Dec 2023 -> today, with point-in-time membership.

Method (same as the Yardeni chart): weekly (Friday) closes, 'above 200-dma' = weekly close > 40-week average,
'above 50-dma' = weekly close > 10-week average.
Membership at date t = today's constituents (Wikipedia), with the later joins removed and the later leavers added back
(ChartRow lists who joined/left between quarterly SPY filings). Join dates: Wikipedia 'Date added'; leave dates: last
trading day of the price series if the stock was acquired, otherwise the quarterly rebalance date.
Stocks with no price history (mostly acquired companies) cannot be scored; coverage is reported.

python -m macro_analog.breadth_rebuild [--fetch]
"""
import argparse
import datetime as dt
import io
import json
import time

import numpy as np
import pandas as pd
import requests

from . import ingest

RAW, EXT = ingest.RAW, ingest.ROOT / "data" / "external"
WIKI = RAW / "wikipedia_sp500_constituents_20261111.html"
CHART = RAW / "chartrow_sp500_changes_20261111.html"
PRICE_START = "2022-01-01"
FIRST_WEEK = pd.Timestamp("2023-01-06")


def schwab_sym(t: str) -> str:
    return t.replace(".", "/")


def changes() -> pd.DataFrame:
    rows = []
    for x in pd.read_html(io.StringIO(CHART.read_text()))[1:]:
        x = x.copy()
        x["window"] = x["Between filings"].ffill()
        rows.append(x)
    a = pd.concat(rows, ignore_index=True)
    a["w0"] = pd.to_datetime(a["window"].str.split("–").str[0].str.strip(), format="%b %d, %Y")
    a["w1"] = pd.to_datetime(a["window"].str.split("–").str[1].str.strip(), format="%b %d, %Y")
    a["ticker"] = a["Company"].str.extract(r"\(([A-Z.\-]+)\)\s*$")
    return a[a.w1 >= "2023-01-01"]


def current() -> pd.DataFrame:
    t = pd.read_html(io.StringIO(WIKI.read_text()))[0]
    t["Date added"] = pd.to_datetime(t["Date added"], errors="coerce")
    return t


def rebalance_date(w1: pd.Timestamp) -> pd.Timestamp:
    """Last day as a member for a stock dropped at the quarterly rebalance in the quarter ending w1 (3rd Friday + 3d)."""
    m = pd.Timestamp(year=w1.year, month=w1.month, day=1) if w1.day > 5 else (w1 - pd.Timedelta(days=5)).replace(day=1)
    fridays = pd.date_range(m, m + pd.offsets.MonthEnd(0), freq="W-FRI")
    return fridays[2] + pd.Timedelta(days=3)


def fetch(tickers):
    tok = ingest._schwab_access_token()
    start_ms = int(dt.datetime.strptime(PRICE_START, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    out, t0 = {}, time.time()
    for i, tk in enumerate(tickers):
        for attempt in range(4):
            r = requests.get("https://api.schwabapi.com/marketdata/v1/pricehistory", headers={"Authorization": f"Bearer {tok}"},
                             params=dict(symbol=schwab_sym(tk), periodType="year", frequencyType="daily", frequency=1,
                                         startDate=start_ms, endDate=int(time.time() * 1000), needExtendedHoursData="false"), timeout=60)
            if r.status_code in (429, 500, 502, 503):
                time.sleep(2 * (attempt + 1)); continue
            break
        c = r.json().get("candles", []) if r.status_code == 200 else []
        out[tk] = [[x["datetime"], x["close"]] for x in c]
        time.sleep(0.12)
        if i % 100 == 0:
            print(f"  fetched {i}/{len(tickers)} ({time.time() - t0:.0f}s)")
    stamp = ingest._now()
    p = RAW / f"schwab_sp500_stock_closes_{stamp}.json"
    p.write_text(json.dumps(out))
    ingest._log(dict(series_id="daily closes of S&P 500 current + departed constituents", provider="Schwab marketdata pricehistory",
                     source_url="https://api.schwabapi.com/marketdata/v1/pricehistory", downloaded_at_utc=stamp, vintage_date="latest",
                     unit="USD per share", seasonal_adjustment="n/a", file=p.name))
    return p


def load_closes(path):
    raw = json.load(open(path))
    d = {}
    for tk, c in raw.items():
        if c:
            d[tk] = pd.Series([x[1] for x in c], index=pd.to_datetime([x[0] for x in c], unit="ms", utc=True).tz_localize(None).normalize())
    return pd.DataFrame(d).sort_index()


def events(cur, ch, closes):
    """(date, ticker, +1 join / -1 leave) after 2023-01-01."""
    wiki_added = cur.set_index("Symbol")["Date added"]
    ev = []
    for _, r in ch.iterrows():
        tk = r.ticker
        if r.Change == "Joined":
            d = wiki_added.get(tk)
            d = d if (tk in wiki_added.index and pd.notna(d) and d >= r.w0 - pd.Timedelta(days=7)) else rebalance_date(r.w1)
            ev.append((d, tk, +1))
        else:
            d = rebalance_date(r.w1) if r.w1 <= pd.Timestamp("2026-09-30") else r.w0 + (r.w1 - r.w0) / 2
            if tk in closes and closes[tk].last_valid_index() < closes.index[-1] - pd.Timedelta(days=3):
                d = closes[tk].last_valid_index() + pd.Timedelta(days=1)          # acquired: leaves when it stops trading
            ev.append((d, tk, -1))
    return sorted((e for e in ev if isinstance(e[1], str)), key=lambda e: e[0])


def members_at(t, cur_set, ev):
    s = set(cur_set)
    for d, tk, kind in reversed(ev):
        if d <= t:
            break
        s.discard(tk) if kind > 0 else s.add(tk)
    return s


def compute(closes, cur, ch):
    ev = events(cur, ch, closes)
    cur_set = set(cur.Symbol)
    named_no_ticker = ch[ch.ticker.isna()]
    wk = closes.groupby(closes.index.to_period("W-FRI")).last()
    wk.index = wk.index.to_timestamp(how="end").normalize()
    m200, m50 = wk.rolling(40, min_periods=40).mean(), wk.rolling(10, min_periods=10).mean()
    rows = []
    for w in wk.index[wk.index >= FIRST_WEEK]:
        mem = members_at(w, cur_set, ev)
        have = [t for t in mem if t in wk.columns and pd.notna(wk.at[w, t]) and pd.notna(m200.at[w, t])]
        # members that left before a week-end must not be scored after their last price: handled by membership dates
        rows.append(dict(week_ending=w, pct_above_200dma=100 * np.mean([wk.at[w, t] > m200.at[w, t] for t in have]),
                         pct_above_50dma=100 * np.mean([wk.at[w, t] > m50.at[w, t] for t in have if pd.notna(m50.at[w, t])]),
                         n_members=len(mem), n_scored=len(have)))
    out = pd.DataFrame(rows).set_index("week_ending")
    out["coverage"] = out.n_scored / out.n_members
    return out, ev, named_no_ticker


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args()
    cur, ch = current(), changes()
    tickers = sorted(set(cur.Symbol) | set(ch.ticker.dropna()))
    path = fetch(tickers) if a.fetch else ingest.latest("schwab_sp500_stock_closes")
    closes = load_closes(path)
    print(f"closes: {closes.shape[1]} of {len(tickers)} tickers have data")
    out, ev, nt = compute(closes, cur, ch)
    out.round(3).to_csv(EXT / "sp500_breadth_rebuilt_2023_2026.csv")
    yd = pd.read_csv(EXT / "yardeni_sp500_pct_above_200dma_weekly_2008_2023.csv", index_col=0, parse_dates=True).iloc[:, 0]
    ov = pd.concat([out.pct_above_200dma.rename("rebuilt"), yd.rename("yardeni")], axis=1, join="inner")
    print(f"overlap weeks {len(ov)}: corr {ov.corr().iloc[0, 1]:.3f}, mean diff (rebuilt - Yardeni) {np.mean(ov.rebuilt - ov.yardeni):+.1f} pp, "
          f"mean abs diff {np.mean(np.abs(ov.rebuilt - ov.yardeni)):.1f} pp, last week {ov.iloc[-1].round(1).to_dict()}")
    print("coverage min/median:", out.coverage.min().round(3), out.coverage.median().round(3))
    print(out.iloc[[0, 26, 52, 78, 104, 130, -1]].round(1))


if __name__ == "__main__":
    main()
