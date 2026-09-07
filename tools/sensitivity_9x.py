# -*- coding: utf-8 -*-
"""
sensitivity_9x.py - G1 修复: 给"净效益/9x"装置信区间
===================================================
一次 2000MC 引擎跑 @6% 得到行业冲击与升值路径,
随后对 7 个参数做 800 组拉丁采样, 在确定性公式上重算:
  净效益 = 资本流入(5y) + 资本深化 - 出口损失(解析)
输出: 5/25/50/75/95 分位 + tornado 前8 效应 + json
说明: 敏感性代理(固定 6% 路径, 不重跑 MC), 用于话术区间, 非新点估计。
Run: python sensitivity_9x.py
"""
import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import os
import json
import sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model import MacroParams, ScenarioEngine, load_project_config
from capital_inflow import CapitalInflowModule, CapitalConfig
from dataclasses import replace

N_SAMPLE = 800
RNG = np.random.default_rng(2026)


def base_run():
    mp, cc = load_project_config()
    p = replace(mp, n_simulations=2000, seed=42)
    r = ScenarioEngine(p, capital_cfg=cc).run()
    return (np.median(r["appreciation"], axis=0),
            r["industry_profit"].iloc[-1],
            float(r["industry_profit"]["export_lowend"].iloc[-1] * 100))


def analytic_net(appr, industry_final, lowend_pct, cfg, margin, lam_e_scale):
    """确定性净效益: inflow/deepen 来自模块(无MC), loss 解析缩放。"""
    cap = CapitalInflowModule(cfg).compute(appr, None)
    inflow = cap["cumulative_inflow"]
    deepen = cap["deepening_gain"]
    shock_low = industry_final["export_lowend"] * lam_e_scale
    shock_hi = industry_final["export_hightech"] * lam_e_scale
    pool = 3.5 * margin * 5
    loss = pool * (0.4 * shock_low + 0.6 * shock_hi)
    return inflow + deepen - loss


def main():
    appr, ind_final, lowend = base_run()
    base_cfg = load_project_config()[1]
    base_margin = 0.10
    base_net = analytic_net(appr, ind_final, lowend, base_cfg,
                            base_margin, 1.0)
    print("基准(6%%): net=%.3f T$  (引擎瀑布约 2.68)" % base_net)

    draws = {
        "equity_inflow_rate": (base_cfg.equity_inflow_rate * 0.6,
                               base_cfg.equity_inflow_rate * 1.6),
        "bond_inflow_rate": (base_cfg.bond_inflow_rate * 0.6,
                             base_cfg.bond_inflow_rate * 1.6),
        "fdi_inflow_rate": (base_cfg.fdi_inflow_rate * 0.6,
                            base_cfg.fdi_inflow_rate * 1.6),
        "dollar_drain_boost": (0.15, 0.95),
        "deepen_return": (0.09, 0.22),
        "exporter_margin": (0.06, 0.14),
        "lam_e_scale": (0.7, 1.3),
    }
    keys = list(draws.keys())
    nets = np.empty(N_SAMPLE)
    sample = {}
    for k in keys:
        lo, hi = draws[k]
        sample[k] = RNG.uniform(lo, hi, N_SAMPLE)
    for i in range(N_SAMPLE):
        kw = {k: float(sample[k][i]) for k in keys
              if k in {"equity_inflow_rate", "bond_inflow_rate",
                       "fdi_inflow_rate", "dollar_drain_boost",
                       "deepen_return"}}
        cfg = replace(base_cfg, **kw)
        margin = float(sample["exporter_margin"][i])
        lam = float(sample["lam_e_scale"][i])
        nets[i] = analytic_net(appr, ind_final, lowend, cfg, margin, lam)

    q = np.percentile(nets, [5, 25, 50, 75, 95])
    scale = 2.68 / base_net    # 代理锚回引擎瀑布点估计 2.68
    ratio = (nets * scale) / 0.31   # 9x 倍数基线 ~8.6
    rq = np.percentile(ratio, [5, 25, 50, 75, 95])
    print("net T$: p5=%.2f p25=%.2f p50=%.2f p75=%.2f p95=%.2f" % tuple(q))
    print("9x 倍数: p5=%.1f p50=%.1f p95=%.1f" % (rq[0], rq[2], rq[4]))

    # tornado: 单参±(p25,p75)中位移动
    effects = {}
    for k in keys:
        lo, hi = np.percentile(sample[k], [25, 75])
        idx_lo = (sample[k] <= lo + 1e-12) | (sample[k] >= hi - 1e-12)
        # 简化: 用参数与 net 的 Spearman 排序相关表征方向
        rank = np.argsort(np.argsort(sample[k]))
        rnk = np.argsort(np.argsort(nets))
        rho = np.corrcoef(rank, rnk)[0, 1]
        effects[k] = rho
    order = sorted(effects, key=lambda k: -abs(effects[k]))[:8]

    out = {"base_net": round(float(base_net), 3),
           "net_pct": [round(float(x), 3) for x in q],
           "ratio_9x_pct": [round(float(x), 2) for x in rq],
           "note": "固定6%路径的确定性代理(800采样); 用于话术区间, 非新点估计",
           "top_effects_spearman": {k: round(float(effects[k]), 3) for k in order}}
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "sensitivity_9x.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("saved sensitivity_9x.json")


if __name__ == "__main__":
    main()
