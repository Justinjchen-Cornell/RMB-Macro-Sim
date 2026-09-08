# RMB-Macro-Sim · 版本与状态单点 (VERSION.md)

| 项 | 值 |
| 定位 | 宏观政策沙盒(大国博弈·财政货币产业一体化), 见 docs/VISION.md |
|---|---|
| 版本 | **3.0.0** (__init__.py) |
| 更新 | 2026-09-07 |
| 引擎 | policy_engine.py (canonical) + 6 模块市场引擎 |
| 测试 | 17+3 (test_model.py + test_real_calib.py) |
| Dashboard | dashboard.html 单文件 · 41 档滑块 · Pages 自动刷新 |
| 参数真源 | config.yaml (市场) + policy_params.yaml (政策, v3.1 起) |
| 文档索引 | docs/PROJECT_MAP.md |
| 版本徽章 | README 顶部"tests-20/20 / v3.0" 均以此表为准 |

## 完成态(2026-09 收尾)

- Grill G1-G19 改进: Batch E(7 项)+ M(1/2/3/4/5/6)+ H1-H5 全部落地
- 走资/9x/带宽数字均已锚定与区间化(见 docs/H2-H5_scope_2026-09.md)
- 定位: 宏观政策沙盒(VISION.md)· 文件地图(STRUCTURE.md)· 项目地图(PROJECT_MAP.md)
- 结构: 入口(根)+ 引擎(modules/)+ 工具(tools/)+ 参数库(params/)+ 文档(docs/)+ 表达(assets/report/social)
- 报告: report/宏观政策沙盒_详细研究报告_v3_2026-09.pdf (15 页, build_report_v3.py 可再生)
- 下一步候选: ①季度持仓槽位首条入库 ②港交所月度页解析 ③图表/文档英文补齐 ④发布材料(v3.0 项目发布帖)
