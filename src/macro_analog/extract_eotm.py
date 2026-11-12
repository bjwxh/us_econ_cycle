import pymupdf, pandas as pd, numpy as np
pg = pymupdf.open("refs/semiquincententacles-amv.pdf")[11]
k = 72/110; rect = pymupdf.Rect(460*k, 262*k, 860*k, 515*k)
# axis calibration read from the chart's own tick marks: y 10% at 322.26, 15% at 304.67 ; x 1985 at 327.0, 1995 at 378.3
y_of = lambda y: 10 + (322.26 - y) / (322.26 - 304.67) * 5
x_of = lambda x: 1985 + (x - 327.0) / (378.3 - 327.0) * 10
cols = {(0.0, 0.412, 0.639): "top10_mktcap_pct", (0.639, 0.506, 0.137): "top10_fwd_earnings_pct"}
out = {}
for d in pg.get_drawings():
    if not d["rect"].intersects(rect) or len(d["items"]) < 300 or d.get("color") is None: continue
    name = cols[tuple(round(c, 3) for c in d["color"])]
    pts = []
    for it in d["items"]:
        pts += [(it[1].x, it[1].y), (it[-1].x, it[-1].y)]   # segment start and end, for both 'l' and 'c' items
    pts = sorted(set(pts))
    xs = np.array([x_of(x) for x, _ in pts]); ys = np.array([y_of(y) for _, y in pts])
    # chart x position -> fractional year; read the curve at each month's mid-point (linear interpolation)
    months = pd.period_range("1985-01", "2026-06", freq="M")
    mid = np.array([m.year + (m.month - 0.5) / 12 for m in months])
    ok = (mid >= xs.min()) & (mid <= xs.max())
    out[name] = pd.Series(np.where(ok, np.interp(mid, xs, ys), np.nan), index=months)
df = pd.DataFrame(out)
df.index.name = "month"
df.round(2).to_csv("data/external/gs_top10_concentration_eotm_jun2026.csv")
print(df.index.min(), df.index.max(), len(df)); print(df.isna().sum().to_dict())
for m in ["2000-03","2000-11","2006-09","2018-01","2023-11","2025-06"]:
    r = df.loc[pd.Period(m)] if pd.Period(m) in df.index else None
    print(m, None if r is None else r.round(1).to_dict())
