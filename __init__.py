"""
宏观场景推演模型 (Macro Scenario Simulation Model)
================================================
人民币升值 → 通胀/出口/行业利润 → 资产价格重估

快速开始:
    from macro_sim.model import ScenarioEngine, MacroParams

    engine = ScenarioEngine()
    results = engine.run()
    engine.plot()
"""
from .model import (
    MacroParams,
    ExchangeRateModule,
    InflationModule,
    ExportModule,
    IndustryProfitModule,
    AssetPriceModule,
    ScenarioEngine,
)

__version__ = "1.0.0"
