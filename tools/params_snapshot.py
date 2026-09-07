# -*- coding: utf-8 -*-
"""
params_snapshot.py - Phase 1: params/ 库(生成物, 非真源)
==========================================================
唯一真源: config.yaml(市场层) + policy_params.yaml(政策层) + 代码默认值。
本脚本把当前生效参数快照导出为审计/外部引用格式:
  params/trade_elasticity.csv     分行业/分渠道弹性
  params/transmission_matrix.json 传导矩阵快照
  params/calibration_history.log  校准历史(每次校准/回测人工或脚本追加)

Run: python params_snapshot.py   (建议每次校准后重跑/追加 log)
"""
import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import csv
import json
import os
import sys
import datetime as dt

BASE = os.path.dirname(os.path.abspath(__file__))
P_DIR = os.path.join(BASE, "params")
os.makedirs(P_DIR, exist_ok=True)
sys.path.insert(0, BASE)

import yaml
from policy_engine import UnifiedParams, ImportTools


def _yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main():
    p = UnifiedParams()
    pol = _yaml(os.path.join(BASE, "policy_params.yaml"))
    cfg = _yaml(os.path.join(BASE, "config.yaml"))
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    # ---- trade_elasticity.csv ----
    rows = [
        ["channel", "parameter", "value", "source"],
        ["goods_export", "lam_e", p.lam_e, "policy_params.yaml"],
        ["goods_import", "lam_m", p.lam_m, "policy_params.yaml"],
        ["services", "lam_svc", p.lam_svc, "policy_params.yaml"],
        ["export_volume", "export_price_elasticity",
         cfg.get("export", {}).get("export_price_elasticity", ""), "config.yaml"],
        ["import_volume", "import_price_elasticity",
         cfg.get("export", {}).get("import_price_elasticity", ""), "config.yaml"],
        ["tariff_tool", "tariff_elasticity", 0.60, "policy_engine"],
        ["procurement_tool", "procurement_max_increment_t", 0.08, "policy_engine"],
        ["access_tool", "svc_import_elasticity", 0.45, "policy_engine"],
        ["demand_tool", "demand_income_elasticity", 0.50, "policy_engine"],
    ]
    with open(os.path.join(P_DIR, "trade_elasticity.csv"), "w",
              newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

    # ---- transmission_matrix.json ----
    capital = cfg.get("capital", {})
    matrix = {
        "generated": now,
        "note": "生成物快照; 唯一真源 = config.yaml + policy_params.yaml + 代码默认",
        "oil_to_cpi": {"lags_cum": round(sum(p.oil_lags), 4),
                       "ept": p.ept,
                       "appr_offset_factor": "ept"},
        "fx_to_sector": cfg.get("fx_sensitivity", {}),
        "capital_inflow": {k: capital.get(k) for k in
                           ["equity_inflow_rate", "bond_inflow_rate",
                            "fdi_inflow_rate", "dollar_drain_boost",
                            "apprec_elasticity", "deepen_return"]},
        "flight_curve": {"k_norm": 13.3, "linear": 0.30,
                         "nonlinear_pow": 1.5, "threshold_speed": 0.06},
        "reserves": {"base_t": p.reserves_t, "floor_t": p.reserves_floor_t},
        "redlines": {"flight_gdp_pct": p.flight_redline,
                     "deind_gdp_pct": p.deind_gdp_redline,
                     "deind_profit_pct": p.deind_profit_redline},
        "industry_weights": cfg.get("industry_weights", {}),
    }
    with open(os.path.join(P_DIR, "transmission_matrix.json"), "w",
              encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=1)

    # ---- calibration_history.log ----
    hist = os.path.join(P_DIR, "calibration_history.log")
    first = not os.path.exists(hist)
    with open(hist, "a", encoding="utf-8") as f:
        if first:
            f.write("# 校准历史 (calibration_history) - 每次校准/回测追加一行\n")
        f.write("%s | v3.0 | init snapshot | "
                "lam_e=%s lam_m=%s ept=%s openness=%s | 9x median=9.7 (7.0-13.0) | "
                "真源: config.yaml+policy_params.yaml\n"
                % (now, p.lam_e, p.lam_m, p.ept, p.openness))

    print("params/ written:")
    for name in ["trade_elasticity.csv", "transmission_matrix.json",
                 "calibration_history.log"]:
        print("  -", name, os.path.getsize(os.path.join(P_DIR, name)), "B")


if __name__ == "__main__":
    main()
