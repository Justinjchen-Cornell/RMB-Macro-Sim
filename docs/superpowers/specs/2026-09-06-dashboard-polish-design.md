# RMB-Macro-Sim 打磨设计 · 2026-09-06

> Superpowers brainstorming 产出。用户批准项:深色品牌风、单文件静态 dashboard、推 GitHub + 开 Pages。

## 决策记录

| # | 议题 | 决策 | 理由 |
|---|---|---|---|
| D1 | 图表风格 | **浅色研报风**(白底纸感、专业排版,券商研报式) | 用户最终拍板;雪球/公众号/邮件阅读友好 |
| D2 | dashboard | **单文件 HTML + 预设情景 JSON(内嵌)**,零依赖 | 浏览器无法跑 MC;预设法诚实、可双击、可挂 Pages |
| D3 | 分发 | 推 GitHub **并启用 Pages**(main 根目录,dashboard.html) | 公开仓库即时可演示 |
| D4 | 参数治理 | **config.yaml 成为唯一真源**(补 loader),修复"装饰品"问题 | 实用性 P1 |
| D5 | 图表管线 | 统一到 visualize + run_all;删除 model.plot 死路径双管线 | 修复 Linux 路径/命名冲突 |
| D6 | 代码审查 | 出正式报告 docs/code_review_2026-09-06.md(P0/P1/P2) | 可追溯 |

## 展示层(D1+D2)

- **视觉基准(浅色研报风)**:纸白底 #ffffff/#f8fafc、墨色 #111827、主色蓝 #2563eb、损益金 #d97706/红 #e11d48/绿 #059669;细网格 #e2e8f0;标题加粗+色条;研报式排版
- **报告图(新增)**:`plot_scenario_wall()` 情景巨幕图 — 3 行(A/B/C)×[FX 扇形带 | 行业冲击条 | 净效益瀑布缩略],一图讲完"净效益≈损失9倍"的故事;存 charts/08_scenario_wall.png
- **dashboard.html**:浅色研报风;顶部三情景结论卡;中部 FX 路径 SVG、行业条形(可排序)、瀑布;底部预设切换;免责声明;亲和但专业的细节
- **presets**:export_dashboard.py 预跑 8 组:升值 {0,3,6,10}% × 资本{基准} + {6%×激进美元荒} + {惯性2.7%} → JSON 内嵌 HTML(另写 index.html 副本供 Pages)

## 实用性(D4/D5/D6)

- model.py:MacroParams.from_yaml / load_params;yaml 增 industry_weights 节;run_all 默认读 config.yaml
- model.plot() 移除,__main__ 复用统一管线;默认目录 charts/(相对)
- calibrate/data_loader:resample("M")→("ME");.env 祖先搜索 + FRED_API_KEY 环境变量;克隆无 key 友好报错
- __init__.py 导出补齐 + __version__ 2.0.0
- 测试:新增 from_yaml 往返、presets JSON 结构;全量回归 15+3 保持绿

## 验收

1. python run_all.py → charts/ 08 张图无警告无死路径
2. python export_dashboard.py → dashboard.html 双击可用(数据完整、预设可切)
3. python test_model.py + test_real_calib.py 全绿
4. git push;Pages 生效,dashboard 可公开访问
5. docs/code_review_2026-09-06.md 出具
