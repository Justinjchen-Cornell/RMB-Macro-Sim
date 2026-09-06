"""
RMB-Macro-Sim (人民币升值宏观模拟)
==================================
人民币升值 → 通胀/出口/行业利润 → 资产定价 + 资本流入(融资红利/资本深化)

快速开始:
    python run_all.py             # 一键: config.yaml 参数 → 7 图 + 净效益瀑布
    python run_real.py --charts   # 真实数据(FRED/腾讯/北向)校准 + 三情景巨幕图
    python export_dashboard.py    # 单文件交互仪表盘 dashboard.html
    python build_report.py        # 中文研报 HTML + PDF (report/)

    from model import ScenarioEngine, MacroParams, load_project_config
    mp, cc = load_project_config()          # config.yaml = 参数真源
    r = ScenarioEngine(mp, capital_cfg=cc).run()
"""
from .model import (
    MacroParams,
    ExchangeRateModule,
    InflationModule,
    ExportModule,
    IndustryProfitModule,
    AssetPriceModule,
    ScenarioEngine,
    load_project_config,
)
from .capital_inflow import CapitalInflowModule, CapitalConfig

__version__ = "2.0.0"
