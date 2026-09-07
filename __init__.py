"""
RMB-Macro-Sim v3.0 - 人民币宏观政策模拟系统
==========================================
市场情景层: 6 模块 MC 引擎 (FX/通胀/出口/行业利润/资产定价/资本流入)
政策算法层: policy_engine.py - 卢氏三原则统一系统
  (V2a 利润口径 x V2b GDP口径 x V3 进口政策工具 x V4 外储/博弈)

快速开始:
    python run_all.py            # 市场情景: config.yaml -> 图表 + 瀑布
    python policy_engine.py      # 政策算法: 双口径/最小政策k/联合读数
    python export_dashboard.py   # 交互仪表盘 (含政策卡)
    python run_real.py --charts  # 真实数据校准三情景
"""
from .model import (
    MacroParams, ExchangeRateModule, InflationModule, ExportModule,
    IndustryProfitModule, AssetPriceModule, ScenarioEngine,
    load_project_config,
)
from .capital_inflow import CapitalInflowModule, CapitalConfig
from .policy_engine import (
    UnifiedParams, ImportTools, evaluate, policy_needed_at,
    flight_pct_gdp, us_retaliation, intl_control_conflict,
)

__version__ = "3.0.0"
