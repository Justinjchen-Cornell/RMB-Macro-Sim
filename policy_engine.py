"""policy_engine - canonical facade (v3.0)."""

from modules.core import UnifiedParams, ImportTools, load_policy_params
from modules.inflation import oil_cpi_raw, inflation_net
from modules.trade import trade_surplus_t, import_policy_delta
from modules.capital import (_sigmoid, capital_path, flight_pct_gdp,
                              capital_components, us_retaliation,
                              intl_control_conflict)
from modules.industry import deind_dual
from modules.evaluate import evaluate
from modules.optimizer import (balanced_year, optimize_unified,
                                sweep_table, policy_needed_at)
from modules.optimizer import TOOL_SETS
PREMISE = "前提: 以升值为主动力, 进口政策只补足差额"

def main():
    cb = None
    try:
        cb = _engine_profit_cb()
    except Exception as e:
        print("  [note] repo engine cb unavailable:", type(e).__name__)
    print("=" * 102)
    print("  policy_engine - 统一系统 (V2a 利润 x V2b GDP x V3 工具 x V4 外储/报复)")
    print("  原则: 以升值为主动力, 进口政策只补足差额 (非替代升值)")
    print("=" * 102)
    print()
    print("[1] 固定速度带求最小政策度 (开放度 0.40 / 0.25):")
    print("  %-5s %-6s %-9s %-10s %-10s %-8s %-9s %-6s" %
          ("速%", "政策k", "顺差T", "政策承担%", "速度承担%", "利润%", "外储T", "判定"))
    res = {}
    for op in (0.40, 0.25):
        for sp in (0.05, 0.06, 0.07, 0.08):
            r = policy_needed_at(sp, profit_cb=cb, openness=op)
            res[(op, round(sp * 100))] = r
            print("  %-5.0f %-6.2f %-9.2f %-10.0f %-10.0f %-8.1f %-9.2f %-6s"
                  % (r["speed"], r["k"], r["surplus_t"],
                     r["share_policy_pct"], r["share_speed_pct"],
                     r["deind"]["profit_shock_pct"], r["reserves_end"],
                     r["verdict"][:5]))
        print("  " + "-" * 96)
    rec = res[(0.40, 6)]
    print()
    print("[2] 推荐读数 @ 6%%/年 (open 0.40): 政策力度 k=%.2f -> 政策承担 %.0f%%, "
          "速度承担 %.0f%% | 顺差 %.2fT | 去工业 GDP侵蚀 %.1f%% / 利润 %.1f%% | "
          "财政 %.2f%%GDP" % (rec["k"], rec["share_policy_pct"],
                              rec["share_speed_pct"], rec["surplus_t"],
                              rec["deind"]["gdp_erode_pt"],
                              rec["deind"]["profit_shock_pct"],
                              rec["fiscal_gdp_pct"]))
    print()
    print("[3] 口径对照(6%%/年): 利润口径(引擎) %.1f%% vs GDP口径(解析) %.1f%%; "
          "红线均为 35" % (rec["deind"]["profit_shock_pct"],
                            rec["deind"]["gdp_erode_pt"]))
    print()
    print("  注: 不设速度偏好时联合优化会滑向 ~0.75%/年(政策替代升值) -")
    print("      违背以升值为主动力的原则, 已弃用自由解; 固定速度带求解为规范用法。")




if __name__ == "__main__":
    main()
