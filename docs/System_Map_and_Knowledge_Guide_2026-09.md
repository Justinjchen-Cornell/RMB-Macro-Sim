# System Map & Knowledge Guide (plain language) · RMB-Macro-Sim v3.0

![System architecture](../assets/system_map_en.png)

> Source: `assets/system_map_en.png` (zoomable). Chinese edition:
> [体系图解与知识地图_2026-09.md](体系图解与知识地图_2026-09.md)

---

## 0. The system in one sentence

**With free data we answer two questions: (1) what RMB appreciation would do to the
economy and assets (market scenarios); (2) how fast appreciation is *consistent with*
the three policy principles — absorb import inflation, rebalance the trade surplus,
and prevent capital flight / deindustrialization (policy algorithm). A third layer
cross-checks the "where are we now" signal with the Gold/Oil framework, and everything
is delivered through one interactive dashboard.**

Three layers, do not mix:
- **Market layer answers "what would happen"** (description: scenarios)
- **Policy layer answers "what should happen"** (normative: the 3 principles)
- **Cross layer answers "where are we now"** (signal: what to trust today)

## 1. What each layer does

| Layer | Key output | Logic in one line |
|---|---|---|
| ① Data | FRED / Tencent / akshare + news_watch | free, cacheable, reproducible |
| ② Market engine | 41-grid slider, sector shocks, waterfall | FX → inflation → exports → sectors → assets + capital inflow |
| ③ Policy engine | dual-metric redlines, min-policy-k, band 5-6.5% | translate the 3 principles into constraints |
| ④ Cross-validation | GOR × easing, oil drill-down, 3 boards | independent checks from another framework |
| ⑤ Products | dashboard / PDFs / daily card / weekly | one conclusion, many skins |

## 2. Where the numbers come from

| Number you see | Source | Assumption behind it | Trust |
|---|---|---|---|
| Net benefit +2.68T$ (≈9× loss) | capital-inflow module | inflow 11%, dollar-drain ×1.5, marginal return 0.156 | ⚠️ point estimate — read the band (1.99 conservative ↔ 3.91 aggressive) |
| Low-end mfg −28.8% (6%) | industry module | −8% profit per +10% cumulative appreciation | medium (elasticity assumption; clip ±60%) |
| easing +0.30 | goldmac | 5 FRED series, rolling-10y z-score | medium-high (sample 2016-09+ = 10y, shorter than paper 30y; release-lag +1/+2m checks keep quarterly hit 65-67.5%; revised-final data, mild upward bias possible but small) |
| Flight 9.6% (6%, openness 0.4) | policy_engine | normalized v2 calibration curve | ⚠️ no external data anchor — do not treat as measurement |
| Surplus 0.30T (6% + k=0.05) | policy_engine | elasticities 0.35/0.45, tools scaled by k | medium (elasticity assumptions) |
| Policy band 5-6.5% | policy_engine | all redlines hold inside; 8%+ breaches profit redline (40.5) | medium (premise: appreciation as primary engine) |
| 2026 outlook 6.39 (−4.8%) | outlook | inertia 2.7% + news-event scores | low-medium (subjective events; read 3-envelope 6.33-6.60) |

**Three rules when reading numbers**: ① read the interval, not the point; ② never mix
metrics (profit-% vs GDP-%); ③ assumptions are documented above.

## 3. Five things that confuse people (clarified)

1. **Why recommend gold when "CNY gold is −5%"?** The model reports CNY-denominated
   returns; USD gold stays positive (CB buying, de-dollarization). Use a strong RMB to
   buy USD gold — do not add the two currencies' returns.
2. **Do easing and GOR disagree?** GOR prices gold vs oil (relative); easing prices the
   macro wind for gold (absolute). One steers oil (the spear), one guards gold (the shield).
3. **Is "policy band 5-6.5%" a forecast?** No — it is the speed range at which all redlines
   hold *given the three principles*. That the realized 1y drift (~6.2%) falls inside is
   corroboration of policy intent, not a guarantee.
4. **Why two deindustrialization numbers (28.8 vs 2.9)?** One measures sector *profit*
   shock (%), the other GDP-share erosion (%). Compare each to its own 35 redline; never
   cross-compare magnitudes.
5. **Does 48% cash contradict "+8% A-shares"?** No — sequencing: the freeze hits first
   (all assets fall together), the bargain phase buys in 3 tranches, the +8% re-rating
   comes after. Cash is for the bargain, not a bearish call.

## 4. How to go deeper

- Why a sector wins/loses → `real_data_report` (industry FX betas) + industry module
- How policy numbers are computed → `python policy_engine.py` (full CLI table)
- Change news assumptions → edit `news_watch.yaml` → `python export_dashboard.py`
- Validate → `python backtest.py` / `python test_model.py` (17+3 green)

---
*Research framework, not investment advice. v3.0 · 2026-09.*
