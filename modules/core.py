"""modules/core - 参数与参数装载 (唯一真源 yaml 镜像)。"""
import dataclasses
import os
from dataclasses import dataclass, field
from typing import List
import numpy as np
import math

@dataclass
class UnifiedParams:
    # 贸易
    lam_e: float = 0.35
    lam_m: float = 0.45
    lam_svc: float = 0.25
    # 汇率传递: 5期滞后累计 ~0.14 (油价) ; 升值对冲 EPT
    oil_lags: List[float] = field(default_factory=lambda: [0.02, 0.03, 0.04, 0.03, 0.02])
    ept: float = 0.35
    # 资本账户分层
    openness: float = 0.40
    fdi_share: float = 0.30
    portfolio_share: float = 0.35
    nee_share: float = 0.20
    hot_share: float = 0.15
    rmb_intl: float = 0.15
    us_retaliation_sensitivity: float = 0.5
    # 红线 (双口径并立)
    flight_redline: float = 35.0       # 走资红线 (% GDP, V2b口径)
    deind_gdp_redline: float = 35.0    # 去工业化红线 GDP 侵蚀 (% GDP)
    deind_profit_redline: float = 35.0 # 去工业化红线 利润冲击 (%, V2a口径)
    cca_redline: float = 55.0
    # 宏观基线
    gdp_usd_t: float = 19.0
    exports_t: float = 3.5
    imports_t: float = 2.3
    svc_export_t: float = 0.4
    svc_import_t: float = 0.6
    reserves_t: float = 3.2
    reserves_floor_t: float = 2.5
    fiscal_budget_gdp: float = 3.0     # 财政赤字容忍 (% GDP)
    # 油价
    oil_base: float = 90.0
    oil_shock: float = 1.30            # +30% 情景




@dataclass
class ImportTools:
    tariff: float = 0.20
    procurement: float = 0.30
    access: float = 0.20
    demand: float = 0.15




def load_policy_params(path=None):
    """政策层参数真源: policy_params.yaml (缺失时用内置默认, 与历史数值一致)。"""
    import yaml as _yaml
    import os as _os
    if path is None:
        path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                             "policy_params.yaml")
    p = UnifiedParams()
    if not _os.path.exists(path):
        return p
    with open(path, encoding="utf-8") as f:
        d = _yaml.safe_load(f) or {}
    keys = {f.name for f in dataclasses.fields(p)}
    for k, v in d.items():
        if k in keys:
            setattr(p, k, v)
    return p


