# 代码审查报告 · RMB-Macro-Sim · 2026-09-06

> 范围: model.py / capital_inflow.py / visualize.py / run_all.py / run_real.py /
> data_loader.py / calibrate.py / export_dashboard.py / build_report.py / 测试套件

---

## 结论

无 P0(安全/数据完整性)问题。P1 共 8 项 —— **本次全部修复并测试回归**;
P2 共 5 项 —— 记录留待后续。测试: 17/17(模型)+ 3/3(校准)通过。

---

## P1(已修复)

| # | 问题 | 修复 |
|---|---|---|
| P1-1 | `config.yaml` 从未被代码读取(装饰品), 用户改配置无效 | `load_project_config()`: yaml = 唯一真源, 补齐 industry_weights/利差节; run_all 默认读取 |
| P1-2 | `model.plot()` 默认 `/data/workspace/...`(Linux 死路径) + 与 run_all 图表命名冲突的双管线 | plot() 移除; `python model.py` 转发 run_all 统一管线 |
| P1-3 | `resample("M")` pandas 弃用告警 ×3 | 全量替换为 `"ME"` |
| P1-4 | FRED key 查找路径脆弱(硬编码相对层级), 独立克隆无法用 | 优先 `FRED_API_KEY` 环境变量, 再向上 6 层搜 .env; 缺失时报可读错误 |
| P1-5 | 资本瀑布公式符号错误(损失被重复扣除, 净效益虚高 +3.30 vs 正确 +2.68) | `net = inflow + deepening + loss(负值)`; 恒等式测试加方向断言 |
| P1-6 | 腾讯 K线行宽 6/7 字段不齐导致崩溃 | 取前 6 列健壮解析; spot 解析改用响应变量名 |
| P1-7 | `__init__.py` 未导出新模块, 版本陈旧 | 导出 CapitalInflowModule/CapitalConfig/load_project_config; v2.0.0 |
| P1-8 | 中文字体硬编码 Linux 字体(Windows 渲染豆腐块) | Microsoft YaHei/SimHei/… 自动探测(visualize + model 统一) |

## P2(记录, 待后续)

| # | 问题 | 建议 |
|---|---|---|
| P2-1 | `np.random.seed` 全局副作用 | 迁移 `np.random.default_rng`, 模块注入 rng |
| P2-2 | 出口"数量"弹性仍用 -0.45 假设(总值检验不显著) | 接入贸易量/数量指数数据后重估 |
| P2-3 | 北向 2024-08 后"黑暗期" | 港交所季度持股披露 / Wind 反推 |
| P2-4 | demo.ipynb 与 v2 管线(资本模块/新图)脱节 | 重写为 v2 演示或移除 |
| P2-5 | 行业 β 为顾问级, 未自动写回 fx_sensitivity | 利润面板数据 + 显著性子集自动更新 |

## 审查亮点(维持)

- 模块无循环依赖(capital_inflow/data_loader/calibrate 单向);
- 引擎确定性: 固定 seed 可复现(含资本模块, 有测试);
- 缓存层 data/raw 支持离线复现; 报告/仪表盘全部可由脚本再生。
