# 宏观场景推演模型 — 快速上手

## 安装与运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行完整模拟 (生成图表 + 终端摘要)
python run_all.py

# 3. 运行单元测试
python test_model.py

# 4. (可选) Jupyter 交互式探索
jupyter notebook demo.ipynb
```

## 项目结构

```
macro_sim/
├── model.py            # 核心模型 (5大模块 + ScenarioEngine) ★
├── visualize.py        # 图表生成 (深色金融风)
├── run_all.py          # 一键运行入口 ★
├── config.yaml         # 参数配置 (可调)
├── test_model.py       # 单元测试
├── demo.ipynb          # 交互式演示 (Jupyter)
├── requirements.txt    # Python 依赖
├── __init__.py         # 包入口
├── README.md           # 完整算法文档
├── charts/             # 自动生成的图表
└── 快速上手.md          # 本文件
```

## 三步上手

### Step 1: 调整假设 (`config.yaml`)
```yaml
exchange_rate:
  cny_annual_apprec: 0.06   # 改成你预期的升值速度
```

### Step 2: 运行
```bash
python run_all.py
```

### Step 3: 看结果
- 终端：行业利润冲击 + 资产收益摘要 + **资本净效益瀑布**
- `charts/`：7张核心图表（含资本瀑布、三渠道流入图）

## 核心 API

```python
from model import ScenarioEngine, MacroParams

# 自定义参数
params = MacroParams(cny_annual_apprec=0.10, n_simulations=5000)

# 运行
engine = ScenarioEngine(params)
results = engine.run()

# 取数
results["fx_path"]              # 汇率路径 (n_sim, T)
results["industry_profit"]      # 行业利润 (DataFrame, T x 11)
results["equity_return"]        # A股加权年化
results["gold_return"]          # 黄金年化
results["capital_inflow"]       # 资本流入全景 (含净效益瀑布)

# 定制资本流入参数
from capital_inflow import CapitalConfig
cfg = CapitalConfig(equity_inflow_rate=0.15, dollar_drain_boost=0.8)
engine = ScenarioEngine(params, capital_cfg=cfg)
```

## 作为库使用

```python
from macro_sim import ScenarioEngine, MacroParams

engine = ScenarioEngine(MacroParams())
r = engine.run()

# 接入你自己的分析流程
my_portfolio = r["industry_profit"][["semiconductor", "gold", "commodity_metals"]]
```

---

> ⚠️ 模型为教学/研究用途，不构成投资建议。
