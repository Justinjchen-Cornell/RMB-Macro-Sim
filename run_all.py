"""
运行入口 (Entry Point)
===================
执行完整模拟流程：模型计算 → 图表生成 → 报告输出
"""

import os
import sys
import numpy as np
import pandas as pd

# 确保可以导入 model.py
sys.path.insert(0, os.path.dirname(__file__))

from model import (
    MacroParams, ExchangeRateModule, InflationModule,
    ExportModule, IndustryProfitModule, AssetPriceModule, ScenarioEngine,
    load_project_config,
)
from dataclasses import replace
from visualize import (
    plot_fx_scenarios, plot_industry_heatmap,
    plot_asset_radar, plot_transmission_chain,
    plot_sensitivity_table, plot_capital_waterfall, plot_capital_inflow_trends
)

OUT = os.path.join(os.path.dirname(__file__), "charts")
os.makedirs(OUT, exist_ok=True)


def main():
    print("=" * 64)
    print("  宏观场景推演引擎 v1.0")
    print("  人民币升值 → 通胀/出口/行业利润 → 资产价格")
    print("=" * 64)

    # ────────────────────────────────────────────────────────
    #  Part 1: 多情景汇率路径  (基准参数来自 config.yaml)
    # ────────────────────────────────────────────────────────
    print("\n[1/5] 生成多情景汇率路径...  (基准参数: config.yaml)")

    base_params, base_capital = load_project_config()
    scenarios = {
        "快速升值(10%)": replace(base_params, cny_annual_apprec=0.10),
        "基准(6%)":       replace(base_params, cny_annual_apprec=0.06),
        "慢速升值(3%)":   replace(base_params, cny_annual_apprec=0.03),
        "不升值(0%)":     replace(base_params, cny_annual_apprec=0.00),
    }

    all_paths = {}
    for name, params in scenarios.items():
        eng = ScenarioEngine(params, capital_cfg=base_capital)
        r = eng.run()
        all_paths[name] = r["fx_path"]

    plot_fx_scenarios(all_paths, os.path.join(OUT, "01_fx_scenarios.png"))
    print("  ✓ 01_fx_scenarios.png")

    # ────────────────────────────────────────────────────────
    #  Part 2: 基准情景完整模拟
    # ────────────────────────────────────────────────────────
    print("\n[2/5] 运行基准情景 (6%升值)...")

    engine = ScenarioEngine(base_params, capital_cfg=base_capital)
    results = engine.run()

    # 行业热力图
    plot_industry_heatmap(results["industry_profit"], os.path.join(OUT, "02_heatmap.png"))
    print("  ✓ 02_heatmap.png")

    # 传导链条
    plot_transmission_chain(os.path.join(OUT, "03_chain.png"))
    print("  ✓ 03_chain.png")

    # ────────────────────────────────────────────────────────
    #  Part 3: 资本流入图表 (成本-收益瀑布 + 分渠道趋势)
    # ────────────────────────────────────────────────────────
    print("\n[3/5] 生成资本流入图表...")

    capital = results["capital_inflow"]
    plot_capital_waterfall(capital, os.path.join(OUT, "04_capital_waterfall.png"))
    print("  ✓ 04_capital_waterfall.png")
    plot_capital_inflow_trends(capital, os.path.join(OUT, "05_capital_inflows.png"))
    print("  ✓ 05_capital_inflows.png")

    # ────────────────────────────────────────────────────────
    #  Part 4: 资产收益雷达
    # ────────────────────────────────────────────────────────
    print("\n[4/5] 生成资产收益对比...")

    asset_data = {
        "A股加权": float(np.median(results["equity_return"])),
        "中国国债": float(results["bond_return"]),
        "黄金": float(np.median(results["gold_return"])),
        "工业金属": float(np.median(results["commodity_return"])),
    }
    plot_asset_radar(asset_data, os.path.join(OUT, "06_radar.png"))
    print("  ✓ 06_radar.png")

    # ────────────────────────────────────────────────────────
    #  Part 5: 敏感性分析
    # ────────────────────────────────────────────────────────
    print("\n[5/5] 计算敏感性矩阵...")

    sens_data = {}
    for name, params in scenarios.items():
        eng = ScenarioEngine(params, capital_cfg=base_capital)
        r = eng.run()
        ip = r["industry_profit"].iloc[-1]
        sens_data[name] = {
            "低端制造": ip["export_lowend"],
            "半导体": ip["semiconductor"],
            "金属/黄金": ip["commodity_metals"],
            "A股加权": float(r["equity_return"].iloc[-1]),
        }

    sens_df = pd.DataFrame(sens_data).T
    sens_df.index = ["快速(10%)", "基准(6%)", "慢速(3%)", "不升值"]

    plot_sensitivity_table(sens_df, os.path.join(OUT, "07_sensitivity.png"))
    print("  ✓ 07_sensitivity.png")

    # ────────────────────────────────────────────────────────
    #  打印摘要
    # ────────────────────────────────────────────────────────
    print("\n" + "=" * 64)
    print("  模拟结果摘要")
    print("=" * 64)

    apprec_final = np.median(results["appreciation"], axis=0)[-1]
    print(f"\n  人民币累计升值 (5年):  {apprec_final:.1f}%")
    print(f"  USD/CNY 终值:         {np.median(results['fx_path'], axis=0)[-1]:.2f}")

    print(f"\n  行业利润冲击 (Y4, 中位数):")
    for ind, val in results["industry_profit"].iloc[-1].sort_values().items():
        flag = "↓" if val < 0 else "↑"
        print(f"    {ind:25s} {flag} {val:+.1%}")

    print(f"\n  资产年化收益 (5年中位):")
    for k, v in asset_data.items():
        print(f"    {k:10s} {v:+.1%}")

    print(f"\n  敏感性矩阵:")
    print(sens_df.round(3).to_string())

    print(f"\n  资本流入净效益瀑布 (5年累计, T$):")
    cap = results["capital_inflow"]
    print(f"    出口部门利润损失:   {cap['export_loss']:>+8.2f}")
    print(f"    资本净流入(融资):   {cap['cumulative_inflow']:>+8.2f}")
    print(f"    资本深化(GDP增量): {cap['deepening_gain']:>+8.2f}")
    print(f"    ─────────────────────────────")
    print(f"    净效益:             {cap['net_benefit']:>+8.2f}")

    print(f"\n{'=' * 64}")
    print(f"  ✓ 完成! 图表: {OUT}/")
    print(f"{'=' * 64}")


if __name__ == "__main__":
    main()
