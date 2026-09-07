# 文件地图(STRUCTURE)· 大国博弈下的财政·货币·产业一体化政策模拟器

> 定位见 `docs/VISION.md`。原则:入口留在根目录(兼容 GitHub Actions 与 Pages),
> 内部按职责分目录;根目录只放"能直接跑/被管道引用"的文件。

## 根目录(入口与管道)

| 文件 | 作用 |
|---|---|
| `scenario_runner.py` | 统一入口: `--mode market\|policy\|oil\|all` |
| `run_all.py` / `run_real.py` | 市场情景管线(假设参数 / 真实数据校准) |
| `export_dashboard.py` / `dashboard_template.html` | 生成 dashboard(每日管道引用) |
| `dashboard.html` / `index.html` / `dashboard_data.json` | 产物(Pages 部署,由 export 重生成) |
| `policy_engine.py` | 政策算法门面(canonical;内部在 `modules/`) |
| `model.py` / `capital_inflow.py` | 市场 6 模块引擎 + 资本流入 |
| `data_loader.py` / `calibrate.py` / `backtest.py` | 真实数据层与验证 |
| `visualize.py` / `viz_en.py` | 图表(浅色研报风) |
| `outlook.py` / `oil_year_scenario.py` / `news_watch.yaml` | 年度展望/油价推演/事件表 |
| `config.yaml` / `policy_params.yaml` | ★ 参数唯一真源(市场层/政策层) |

## 目录

| 目录 | 内容 |
|---|---|
| `modules/` | 政策引擎拆分(core/inflation/trade/capital/industry/evaluate/optimizer) |
| `params/` | 参数库(生成物:弹性CSV/传导JSON/校准历史 log;真源=两个 yaml) |
| `tools/` | 维护工具:draw_maps / params_snapshot / sensitivity_9x |
| `docs/` | 愿景(VISION) · 文件地图(本文件) · 项目地图(PROJECT_MAP) · 版本(VERSION) · 体系图与知识指南(中英) · 研究/校准/统一/回测文档 |
| `assets/` | 图(system_map ×2、dashboard 预览、日卡/结论卡) |
| `charts/` / `charts_real/` | 引擎图表输出 |
| `report/` | 中/英 PDF 研究报告 |
| `data/raw/` | 真实数据缓存(FRED/腾讯/akshare) |
| `social/` | 传播(标题库) |
| `demo.ipynb` / 其余 md | 演示与旧说明(README_QUICKSTART 待并入 README) |

## 归属红线

- 新代码先问:是入口(根)、引擎内部(modules/)、工具(tools/)、还是参数镜像(params/)?放错即杂乱;
- 产物一律标记 generated;真源只有 config.yaml + policy_params.yaml;
- 公共仓库不收录:本地私有归档 `_policy_legacy_archive/`、密钥、交接日志。
