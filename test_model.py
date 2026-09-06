"""
单元测试 (Unit Tests)
====================
验证模型各模块的数学正确性与边界条件。
运行: python -m pytest test_model.py -v
"""

import numpy as np
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from model import (
    MacroParams, ExchangeRateModule, InflationModule,
    ExportModule, IndustryProfitModule, AssetPriceModule, ScenarioEngine
)
from model import load_project_config
from capital_inflow import CapitalInflowModule, CapitalConfig


def test_fx_simulation_shape():
    """汇率路径形状应为 (n_sims, n_years+1)"""
    p = MacroParams(n_years=5, n_simulations=100, seed=42)
    fx = ExchangeRateModule(p)
    path = fx.simulate(5, 100, 42)
    assert path.shape == (100, 6), f"Expected (100, 6), got {path.shape}"
    # 起始值应为基准汇率
    assert np.allclose(path[:, 0], 6.7108)
    print("✓ test_fx_simulation_shape")


def test_fx_appreciation_monotonic():
    """升值情景下, 累计升值应为正"""
    p = MacroParams(cny_annual_apprec=0.06, n_years=5, n_simulations=100, seed=42)
    fx = ExchangeRateModule(p)
    path = fx.simulate(5, 100, 42)
    apprec = fx.cumulative_appreciation(path)
    # 终值升值幅度 > 0
    assert np.median(apprec[:, -1]) > 0
    print("✓ test_fx_appreciation_monotonic")


def test_no_appreciation_zero_effect():
    """不升值情景下, 汇率终值 ≈ 起始值"""
    p = MacroParams(cny_annual_apprec=0.0, n_years=5, n_simulations=500, seed=42)
    fx = ExchangeRateModule(p)
    path = fx.simulate(5, 500, 42)
    final = np.median(path[:, -1])
    assert abs(final - 6.7108) < 0.15, f"Expected ~6.7108, got {final}"
    print("✓ test_no_appreciation_zero_effect")


def test_industry_profit_bounds():
    """行业利润冲击应裁剪在 [-30%, +30%]"""
    p = MacroParams()
    eng = ScenarioEngine(p)
    r = eng.run()
    df = r["industry_profit"]
    assert (df.values >= -0.31).all() and (df.values <= 0.31).all(), \
        "行业利润超出 [-30%, +30%] 约束"
    print("✓ test_industry_profit_bounds")


def test_export_lowend_most_negative():
    """低端制造业应为受损最大的行业 (升值情景)"""
    p = MacroParams(cny_annual_apprec=0.06, seed=42)
    eng = ScenarioEngine(p)
    r = eng.run()
    final = r["industry_profit"].iloc[-1]
    assert final["export_lowend"] < 0, "低端制造应受损"
    # 应比高技术出口更差
    assert final["export_lowend"] < final["export_hightech"], \
        "低端制造应比高技术出口更受损"
    print("✓ test_export_lowend_most_negative")


def test_resource_sector_benefit():
    """资源品 (commodity_metals, gold) 应在升值中受益"""
    p = MacroParams(cny_annual_apprec=0.06, seed=42)
    eng = ScenarioEngine(p)
    r = eng.run()
    final = r["industry_profit"].iloc[-1]
    assert final["commodity_metals"] > 0, "金属应受益"
    assert final["gold"] > 0, "黄金应受益"
    print("✓ test_resource_sector_benefit")


def test_asset_returns_finite():
    """所有资产收益应为有限实数"""
    p = MacroParams()
    eng = ScenarioEngine(p)
    r = eng.run()
    for name in ["equity_return", "bond_return", "gold_return", "commodity_return"]:
        val = r[name]
        assert np.all(np.isfinite(val)), f"{name} 含非有限值"
    print("✓ test_asset_returns_finite")


def test_reproducibility():
    """相同seed应产生相同结果"""
    p = MacroParams(seed=123)
    e1 = ScenarioEngine(p).run()
    e2 = ScenarioEngine(p).run()
    assert np.allclose(e1["fx_path"], e2["fx_path"]), "结果不可复现"
    print("✓ test_reproducibility")


def test_full_pipeline():
    """完整流程应无异常"""
    p = MacroParams()
    eng = ScenarioEngine(p)
    r = eng.run()
    assert "industry_profit" in r
    assert "equity_return" in r
    assert "gold_return" in r
    assert "capital_inflow" in r, "资本流入模块应挂接进引擎"
    print("✓ test_full_pipeline")


# ────────────────────────────────────────────────────────
#  资本流入模块测试
# ────────────────────────────────────────────────────────
def _fake_industry_df(shock_low=-0.28, shock_hi=-0.11):
    """构造 6 行 (Y0..Y5) 的行业利润冲击 df"""
    idx = [f"Y{i}" for i in range(6)]
    return pd.DataFrame({
        "export_lowend": [0.0] * 5 + [shock_low],
        "export_hightech": [0.0] * 5 + [shock_hi],
        "semiconductor": [0.0] * 5 + [0.08],
    }, index=idx)


def test_capital_waterfall_identity():
    """瀑布恒等式: 净效益 = 流入 + 深化 - 出口损失"""
    apprec = np.array([0, 5, 10, 16, 23, 32])   # 百分数, 含t0
    mod = CapitalInflowModule(CapitalConfig())
    res = mod.compute(apprec, _fake_industry_df())
    lhs = res["net_benefit"]
    # export_loss 为负值 → 净效益 = 流入 + 深化 + 损失(负)
    rhs = res["cumulative_inflow"] + res["deepening_gain"] + res["export_loss"]
    assert abs(lhs - rhs) < 1e-9, f"瀑布不闭合: {lhs} vs {rhs}"
    assert lhs < res["cumulative_inflow"] + res["deepening_gain"], \
        "存在出口损失时净效益应小于收益合计"
    print("✓ test_capital_waterfall_identity")


def test_capital_zero_appreciation_minimal():
    """不升值时流入应显著低于快速升值情景"""
    apprec0 = np.zeros(6)
    apprec1 = np.array([0, 10, 20, 30, 40, 50])
    mod = CapitalInflowModule(CapitalConfig())
    r0 = mod.compute(apprec0, _fake_industry_df())
    r1 = mod.compute(apprec1, _fake_industry_df())
    assert r1["cumulative_inflow"] > r0["cumulative_inflow"] * 1.1, \
        "快速升值应显著放大资本流入"
    print("✓ test_capital_zero_appreciation_minimal")


def test_capital_flows_positive_finite():
    """所有渠道流入应为正且有限"""
    apprec = np.array([0, 5, 10, 16, 23, 32])
    res = CapitalInflowModule().compute(apprec, _fake_industry_df())
    by = res["by_year"]
    assert (by.values >= 0).all() and np.isfinite(by.values).all()
    assert len(by) == 5, f"应只有5个流入年, 得到 {len(by)}"
    print("✓ test_capital_flows_positive_finite")


def test_capital_export_loss_sign():
    """升值应造成出口利润损失 (负值), 且低端权重损失>0"""
    apprec = np.array([0, 5, 10, 16, 23, 32])
    res = CapitalInflowModule().compute(apprec, _fake_industry_df())
    assert res["export_loss"] < 0, "升值情景出口利润损失应为负"
    assert res["export_detail"]["loss_ts"] < 0
    print("✓ test_capital_export_loss_sign")


def test_capital_sector_allocation_sums():
    """A股行业配置之和 ≈ A股累计流入"""
    apprec = np.array([0, 5, 10, 16, 23, 32])
    res = CapitalInflowModule().compute(apprec, _fake_industry_df())
    eq_total = float(np.sum(res["annual_flows"]["equity"]))
    alloc_total = sum(res["sector_allocation"].values())
    assert abs(alloc_total - eq_total) < 1e-6, f"{alloc_total} vs {eq_total}"
    print("✓ test_capital_sector_allocation_sums")


def test_capital_engine_reproducible():
    """引擎含资本模块后结果仍可复现"""
    p = MacroParams(seed=7)
    e1 = ScenarioEngine(p).run()
    e2 = ScenarioEngine(p).run()
    assert e1["capital_inflow"]["net_benefit"] == e2["capital_inflow"]["net_benefit"]
    print("✓ test_capital_engine_reproducible")



def test_config_yaml_is_source_of_truth():
    """config.yaml 装载应能往返, 且关键默认值一致 (真源校验)"""
    import os
    p, cc = load_project_config()
    assert abs(p.cny_spot - 6.7108) < 1e-9, p.cny_spot
    assert abs(p.cny_annual_apprec - 0.06) < 1e-9
    assert len(p.fx_sensitivity) == 11 and len(p.industry_weights) == 11
    assert abs(cc.equity_inflow_rate - 0.10879) < 1e-6
    assert abs(cc.deepen_return - 0.156) < 1e-6
    print("✓ test_config_yaml_is_source_of_truth")


def test_config_missing_file_falls_back():
    """config.yaml 缺失时应回退内置默认值而非崩溃"""
    p, cc = load_project_config(path="__no_such_file__.yaml")
    assert p.cny_spot == 6.7108
    print("✓ test_config_missing_file_falls_back")


if __name__ == "__main__":
    print("=" * 50)
    print("  运行单元测试...")
    print("=" * 50)
    test_fx_simulation_shape()
    test_fx_appreciation_monotonic()
    test_no_appreciation_zero_effect()
    test_industry_profit_bounds()
    test_export_lowend_most_negative()
    test_resource_sector_benefit()
    test_asset_returns_finite()
    test_reproducibility()
    test_full_pipeline()
    # 资本流入模块
    test_capital_waterfall_identity()
    test_capital_zero_appreciation_minimal()
    test_capital_flows_positive_finite()
    test_capital_export_loss_sign()
    test_capital_sector_allocation_sums()
    test_capital_engine_reproducible()
    test_config_yaml_is_source_of_truth()
    test_config_missing_file_falls_back()
    print("\n" + "=" * 50)
    print("  全部测试通过 ✓")
    print("=" * 50)

