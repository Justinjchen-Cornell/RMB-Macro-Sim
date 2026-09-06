#!/usr/bin/env python3
"""
FX Baseline Watchdog — 防止 RMB-Macro-Sim 静默使用过期基准
============================================================
每日 dashboard 刷新后运行。检查三点：
  1. freshness: dashboard_data.json 是否最近生成(<7天)
  2. live flag : 上次刷新是否真的拉到实时数据 (live.live == True)
  3. spot drift: 当前真实 USD/CNY 与 dashboard 起点偏差是否 >2%

任一异常 → 打印原因并 exit 1（供 GitHub Actions 开 Issue）。

用法:
    python fx_watchdog.py                 # 读本地 dashboard_data.json + 实时腾讯汇率
    python fx_watchdog.py --json URL      # 读远程 URL
"""
import argparse
import json
import os
import sys
import datetime as dt

BASE = os.path.dirname(os.path.abspath(__file__))
SPOT_TOLERANCE = 0.02      # 起点与真实 spot 允许偏差 2%
MAX_AGE_DAYS = 7           # 数据允许最大年龄


def fetch_real_spot():
    """拉腾讯实时 USD/CNY（与 data_loader 同源）。失败返回 None。"""
    try:
        sys.path.insert(0, BASE)
        from data_loader import fetch_tencent_spot
        spot = fetch_tencent_spot(["whUSDCNY"])
        v = spot.get("whUSDCNY", {}).get("price")
        return float(v) if v else None
    except Exception:
        return None


def check(path):
    problems = []
    with open(path, encoding="utf-8") as f:
        d = json.load(f)

    # 1) freshness
    try:
        gen = dt.datetime.strptime(d.get("generated", ""), "%Y-%m-%d %H:%M")
        age_days = (dt.datetime.now() - gen).total_seconds() / 86400.0
        if age_days > MAX_AGE_DAYS:
            problems.append(f"STALE: generated={d.get('generated')} ({age_days:.0f} days old)")
    except ValueError:
        problems.append(f"STALE: unparseable generated={d.get('generated')!r}")

    # 2) live flag
    live = d.get("live") or {}
    if not live.get("live"):
        problems.append(f"OFFLINE: last refresh used offline defaults (live.live=false, note='{live.get('note')}')")

    # 3) spot drift vs real
    real = fetch_real_spot()
    spot = live.get("spot")
    if real is None:
        problems.append("FETCH-ERR: cannot reach Tencent spot (network?) — run again or investigate")
    elif not isinstance(spot, (int, float)):
        problems.append(f"NO-SPOT: dashboard live.spot missing ({spot!r})")
    else:
        drift = abs(real - spot) / real
        if drift > SPOT_TOLERANCE:
            problems.append(
                f"DRIFT: real spot={real} vs dashboard start={spot} "
                f"({drift*100:.1f}% > {SPOT_TOLERANCE*100:.0f}%) — regenerate with live calibration")

    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(BASE, "dashboard_data.json"),
                    help="path or URL to dashboard_data.json")
    args = ap.parse_args()

    if args.json.startswith("http"):
        import urllib.request
        with urllib.request.urlopen(args.json, timeout=20) as r:
            p = os.path.join(BASE, "_remote_dash.json")
            open(p, "wb").write(r.read())
            path = p
    else:
        path = args.json

    if not os.path.exists(path):
        print(f"ERROR: {path} not found")
        sys.exit(1)

    problems = check(path)
    if problems:
        print("FX WATCHDOG: " + "; ".join(problems))
        sys.exit(1)
    print("FX WATCHDOG: OK (fresh, live, spot within tolerance)")
    sys.exit(0)


if __name__ == "__main__":
    main()
