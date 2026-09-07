# RMB-Macro-Sim · Macro Simulation of RMB Appreciation

> 🎯 **Positioning**: a macro-policy sandbox for fiscal × monetary × industrial policy under great-power games (core: state asset management, weak-FX strong-CNY, industrial upgrading) — pace control, tool choice, extreme-case resilience, winners & losers. See [VISION.md](docs/VISION.md) | [STRUCTURE.md](docs/STRUCTURE.md).

> ⚠️ Research framework. Contains normative value judgments (the "Lu three principles"); not objective forecasts — not investment advice.

> **Quantify the macro impact of a controlled RMB (CNY) appreciation** —
> Monte Carlo transmission model, real-data calibration, interactive dashboard,
> and bilingual research reports.

[![Live Dashboard](https://img.shields.io/badge/dashboard-LIVE-2563eb?logo=github)](https://justinjchen-cornell.github.io/RMB-Macro-Sim/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-20%2F20-green)]()
![Chart style](https://img.shields.io/badge/style-light%20research%20report-f8fafc)

---

## 🖥️ Live dashboard

Click the badge above, or run locally:

```bash
python export_dashboard.py     # writes dashboard.html (self-contained)
```

![Dashboard preview](assets/dashboard_preview.png)

![System architecture](assets/system_map_en.png)

**System map & plain-language guide:** [English](docs/System_Map_and_Knowledge_Guide_2026-09.md) · [中文版](docs/体系图解与知识地图_2026-09.md) — layer roles, number provenance, confusions clarified.

**System map & plain-language knowledge guide (CN):** [docs/体系图解与知识地图_2026-09.md](docs/体系图解与知识地图_2026-09.md) · `assets/system_map.png` — data → market engine × policy engine × cross-validation → products.

**Dashboard includes:**
- 🎚️ **CNY move slider −5% … +15% (step 0.5%, 41 grids)** — pre-run Monte Carlo
  grids (400 runs each); drag to watch industry shocks, FX paths, the waterfall
  and macro risk move in real time — depreciation scenarios included;
  differentiated by a backtest-driven parameter revision (see § Backtesting);
- 🏛️ **Macro risk cards** — GDP-equivalent impact (profit-margin-adjusted),
  employment exposure (10k jobs), weighted profit-shock index and a risk tier
  (low/mid/high), recomputed for every slider tick;
- 🏛️ **Macro risk cards** — GDP-equivalent impact (profit-margin-adjusted),
  employment exposure (10k jobs), weighted profit-shock index and a risk tier
  (low/mid/high), computed per scenario;
- 🗺️ **Industry × year heatmap** — 11 sectors × Y1–Y5 cumulative profit shocks;
- 🧭 **Signal-to-action rules** - 5 threshold triggers (R1 fast-appreciation activation < 6.30, R2 thesis falsification > 7.00, R3 PBOC fixing spread, R4 fiscal-regime tell, R5 inflow validation), status auto-checked against the live spot;
- 📰 **Daily reading card** (`social_cards.py`) - 4:5 shareable PNG regenerated every morning with the pipeline (spot, outlook, macro risk);
- 🔮 **Annual outlook panel (3 envelopes)** — for every year: low / base /
  high USD/CNY paths blending calibrated inertia drift with a maintainable
  news/event watch table (`news_watch.yaml`); shows yearly level, % move,
  envelope band and the CNY amount change per USD 10,000;
- 🧭 Scenario chips: 0%/3%/6%/10%, conservative vs aggressive capital inflow,
  real-calibrated, realized-inertia — plus full waterfall, FX fan charts,
  A-share/bond/gold/metal returns.

---

## 🧠 What the model does

```
FX path (GBM, calibrated)
   └→ Import inflation (PPI → CPI lag)
   └→ Export competitiveness (Marshall-Lerner)
   └→ 11-sector profit shocks (FX x sensitivity + inflation + exports + rates)
   └→ Asset pricing (A-shares / bonds / gold / commodities)
   └→ Capital inflow engine (financing + capital deepening, dollar-drain profile)
```

Net benefit = **capital inflow + capital deepening − export profit loss**.

**Headline result (6%/yr, 5y, 2,000 MC):**

| Item | Amount (T$) |
|---|---:|
| Export-sector profit loss | −0.31 |
| Financing inflow | +2.17 |
| Capital deepening | +0.82 |
| **Net benefit** | **+2.68 (≈ 9× the cost)** |

The conclusion is robust to the appreciation pace: even at the realized
2.7%-per-year inertia path the net benefit stays ≈ +2.6 T$.

---

## 🔬 Real-data layer (2026-09)

| Source | Use |
|---|---|
| FRED (DEXCHUS, China exports) | USD/CNY daily vol/drift calibration; export elasticity test |
| Tencent Finance (FX spot + K-line, ETF proxies) | live spot 6.71; industry FX betas (2019-26) |
| akshare / Eastmoney (northbound) | equity inflow-rate calibration (6.5%/yr historical normal) |

Calibrations drive the "real-calibrated" and "inertia" scenarios and the daily
refresh pipeline. See `real_data_report_2026-09-06.md` and `calib_results.json`.

---

## 🚀 Quick start

```bash
pip install numpy pandas matplotlib pyyaml requests     # core
pip install fredapi akshare                             # optional real data

python run_all.py                  # config.yaml → 7 charts + waterfall summary
python run_real.py --charts        # real-data calibration + 3-scenario wall
python policy_engine.py            # v3.0 policy layer: Lu 3 principles unified
                                   # (dual-metric redlines, min-policy-k, reserves)
python export_dashboard.py         # interactive dashboard (single file)
python backtest.py                 # diagnostics: northbound-FX regression,
                                   # FX-episode sector check, flatness analysis
python social_cards.py             # daily reading card + 1:1 opinion cards
python build_report.py             # 9-page Chinese report (HTML+PDF)
python build_report_en.py          # 8-page English report (HTML+PDF)

python test_model.py               # 17 unit tests (engine + capital + config)
python test_real_calib.py          # 3 offline calibration tests
```

### Daily live refresh (GitHub Actions)

`.github/workflows/daily-dashboard.yml` runs every day at 10:23 Beijing time:
`export_dashboard.py --live` fetches FRED/Tencent, recalibrates spot/vol/inertia,
updates the dashboard and auto-commits; GitHub Pages rebuilds automatically.
Add `FRED_API_KEY` in Settings → Secrets (falls back to offline cache otherwise).

### Research reports

- `report/人民币升值宏观影响研究报告_2026-09-06.pdf` (Chinese, 9 pages)
- `report/RMB_Appreciation_Impact_Report_2026-09-06.pdf` (English, 8 pages)
- `real_data_report_2026-09-06.md` — calibration notes and limitations
- `docs/backtest_2026-09.md` — backtest findings & parameter revision log

---

## 📂 Repository layout

```
model.py / capital_inflow.py    6-module engine + capital waterfall (carry channel)
data_loader.py / calibrate.py   real data (FRED/Tencent/northbound) + estimators
backtest.py                     empirical diagnostics (northbound-FX, episodes)
outlook.py + news_watch.yaml    yearly outlook: inertia + news-event scoring
run_all.py / run_real.py        scenario pipelines (assumption & real-data)
policy_engine.py                v3.0 unified policy engine (V2a x V2b x V3 x V4)
export_dashboard.py             dashboard generator (8 presets + 41-grid slider)
social_cards.py                 daily reading + opinion cards (assets/, social/)
build_report.py / _en.py        Chinese & English report builders (HTML→PDF)
viz_en.py                       English chart twins (light research style)
dashboard.html / index.html     self-contained interactive dashboard
docs/ report/ assets/ data/     specs, reviews, reports, cards, caches
```

---

## ⚠️ Disclaimer & limitations

Research framework only — **not investment advice**. Model parameters are
calibrated assumptions; GDP/employment figures are *profit-shock equivalents*
(8% margin, 0.5 employment elasticity), not forecasts. Northbound daily data
ends at the 2024-08 disclosure reform (dark period). Data as of 2026-09.
Sources: FRED, Tencent Finance, akshare.

Apache-2.0 · © 2026 Justinjchen · Built with collaborative AI-assisted research.
v2.1 (2026-09-06): propagation & utility pack, −5%…+15% slider, backtest-driven parameter revision — see docs/backtest_2026-09.md.
v3.0 (2026-09): unified policy layer (policy_engine.py) - Lu-three-principles quantified (dual-metric redlines, layered oil-CPI, S-curve capital, reserves floor, 4 import tools, min-policy-k). Policy band 5-7%/yr; @6% k=0.05 (policy 16% / speed 84%). Legacy v2/v3 archived.
