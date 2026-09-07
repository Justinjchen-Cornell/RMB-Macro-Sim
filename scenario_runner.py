# -*- coding: utf-8 -*-
"""
scenario_runner.py - 多情景统一入口 (Phase 4)
=============================================
  python scenario_runner.py --mode market   # 市场情景: run_all 全管线
  python scenario_runner.py --mode policy   # 政策算法: policy_engine CLI
  python scenario_runner.py --mode oil      # 5年油价分年推演
  python scenario_runner.py --mode all      # 顺序跑以上全部
"""
import sys
import argparse


def run_market():
    import run_all
    run_all.main()


def run_policy():
    import policy_engine
    policy_engine.main()


def run_oil():
    import oil_year_scenario
    oil_year_scenario.run()


def main():
    ap = argparse.ArgumentParser(description="RMB-Macro-Sim scenario runner")
    ap.add_argument("--mode", default="all",
                    choices=["market", "policy", "oil", "all"])
    args = ap.parse_args()
    seq = ["market", "policy", "oil"] if args.mode == "all" else [args.mode]
    for m in seq:
        print()
        print("#" * 30, " scenario:", m, "#" * 30, flush=True)
        {"market": run_market, "policy": run_policy, "oil": run_oil}[m]()


if __name__ == "__main__":
    main()
