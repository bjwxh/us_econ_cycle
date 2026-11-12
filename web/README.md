# Web app

Static site (no build step). Open `web/index.html` directly or serve `web/`.

- `data.js` is generated: `PYTHONPATH=src python3 scripts/build_web_data.py` (reads `outputs/p0_trend_w12/`, `data/`).
- `img/explain/{en,zh}/N.webp` are the How-it-works images (step 6 is cropped to the method-flow strip; the period list is rendered from `data.js`).
- Monthly update: refresh data, re-run the analog match, re-run `build_web_data.py` (update `AS_OF` in it).
- Deployed by `.github/workflows/pages.yml` (publishes `web/`).
