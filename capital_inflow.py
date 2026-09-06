"""
资本流入模块 (Capital Inflow Module)  v2.0
==========================================
把"收益侧"补进宏观场景模型：
  人民币主动升值 + 全球美元流动性稀缺 → 人民币资产成为最优容器 → 资本涌入
  → ① 融资红利 (低成本长期资本)  ② 资本深化 (生产率转化)  ③ 估值重估

成本-收益瀑布 (净效益 = 融资 + 资本深化 - 出口利润损失):
  出口损失   : 由 model.IndustryProfitModule 的 export_lowend / export_hightech
               冲击 × 出口利润池折算为 T$
  融资红利   : A股/债市/FDI 三渠道年度净流入累计 (存量放大 + 升值吸引力 + 美元荒)
  资本深化   : 流入资本形成产能后的边际产出增量 (存量×边际回报×剩余年限)

校准锚点 (2026-09, 基准情景 6% 年化升值, 5年累计):
  出口损失 -0.30 T$ | 资本净流入 +2.17 T$ | 资本深化 +0.81 T$ | 净效益 +2.69 T$
  参数: fdi_stock_rate / dollar_drain_boost / deepen_return 为待实测校准项
  (下一步: 接入 Wind/北向资金真实数据反推, 见 README)

依赖: numpy, pandas (不依赖 model.py, 无循环引用)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Optional


# ── 参数容器 ──────────────────────────────────────────────────
@dataclass
class CapitalConfig:
    """资本流入模块参数 (默认值已按 2026-09 校准锚点设定)"""
    # ── 存量基准 (T$, 现实量级近似) ──
    foreign_equity_base: float = 0.55      # 外资持有A股存量
    foreign_bond_base: float = 0.50        # 外资持有中国债券存量
    fdi_stock: float = 3.40                # 中国吸收FDI存量

    # ── 年度流入率 (占存量的比例, 已按2026-09校准) ──
    equity_inflow_rate: float = 0.10879    # A股: 每年新增 ~11% 存量 (2026-09 重锚)
    bond_inflow_rate: float = 0.08903      # 债市: 每年新增 ~9% 存量 (2026-09 重锚)
    fdi_inflow_rate: float = 0.04745       # FDI: 每年新增 ~4.75% 存量 (2026-09 重锚)

    # ── 吸引力弹性 ──
    apprec_elasticity: float = 0.8         # 累计升值每+10个百分点 → 吸引力 +8%
    apprec_cap: float = 0.90               # 吸引力上限 (防外推失真; 2026-09 回测调宽: 旧0.35在>7.5%/年档位提前饱和)
    re_rate_growth: float = 0.05           # A股存量因估值重估的年自然增值

    # ── 美元荒时序 (2026Q4-2027Q1 向心坍缩峰值) ──
    dollar_drain_boost: float = 0.50       # 峰值超额倍数 (如0.50 → 峰值×1.50)
    drain_peak_year: float = 2.0           # 峰值所在年 (1-indexed)
    drain_width: float = 1.3               # 时序宽度 (越大越平缓)

    # ── 出口利润池 (T$/年) ──
    export_value_annual: float = 3.5       # 中国年出口额 (现实量级近似)
    exporter_margin: float = 0.10          # 出口商平均利润率 ~10%
    export_w: Dict[str, float] = field(default_factory=lambda: {
        "export_lowend": 0.40,             # 低端制造占出口利润池权重
        "export_hightech": 0.60,           # 高新技术占出口利润池权重
    })

    # ── 资本深化 ──
    deepen_return: float = 0.156           # 单位流入资本的边际年化产出
    deepen_lag: int = 0                    # 产出滞后年数

    # ── 行业配置 (流入 A 股的偏好行业, 与 fx_sensitivity 受益方一致) ──
    sector_split: Dict[str, float] = field(default_factory=lambda: {
        "semiconductor": 0.20,
        "commodity_metals": 0.15,
        "power_compute": 0.15,
        "new_energy": 0.15,
        "bank_insurance": 0.20,
        "domestic_consumption": 0.15,
    })


def _drain_boost(t: int, cfg: CapitalConfig) -> float:
    """美元流动性稀缺的时序乘数: 在 drain_peak_year 附近达峰, 两端回落"""
    dt = t - cfg.drain_peak_year
    return 1.0 + cfg.dollar_drain_boost * np.exp(-(dt ** 2) / cfg.drain_width)


class CapitalInflowModule:
    """
    核心链路:
      apprec_t (累计升值) → 吸引力 A_t = 1 + el × min(cum, cap)
      流入_t(渠道) = 存量_{t-1} × 基准流入率 × A_t × 美元荒乘数_t
      存量_t = 存量_{t-1} × (1 + 自然增值) + 流入_t
      出口损失_T$ = Σ 出口行业冲击 × 利润池
      资本深化_T$ = Σ_t 流入_t × 边际回报 × 剩余年限
    """

    def __init__(self, cfg: Optional[CapitalConfig] = None):
        self.cfg = cfg or CapitalConfig()

    # ── 出口损失折算 (T$) ─────────────────────────────────
    def export_loss_ts(self, industry_profit: pd.DataFrame) -> Dict:
        """
        industry_profit: model 输出的各年行业利润冲击 (小数, 累计口径)
        出口利润池 5年 = 年出口额 × 利润率 × 5
        损失 = 池 × Σ(行业权重 × 该行业第5年累计冲击)
        """
        final = industry_profit.iloc[-1]
        # 时间轴含 t=0 (起点), 实际年份数 = len-1
        n_years = max(len(industry_profit) - 1, 1)
        pool_5y = (self.cfg.export_value_annual * self.cfg.exporter_margin *
                   n_years)
        shock = 0.0
        detail = {}
        for ind, w in self.cfg.export_w.items():
            if ind in final.index:
                s = float(final[ind])
                shock += w * s
                detail[ind] = {"weight": w, "shock_5y": s,
                               "loss": pool_5y * w * s}
        loss = pool_5y * shock
        return {"export_pool_5y": pool_5y, "shock_weighted": shock,
                "loss_ts": loss, "detail": detail}

    # ── 三渠道流入路径 (T$/年) ────────────────────────────
    def inflow_path(self, apprec_median: np.ndarray) -> Dict:
        """
        apprec_median: (T,) 时间轴各点中位数累计升值幅度 (百分数)
                       (含 t=0 起点, 首元素≈0 → 实际流入年数 = T-1)
        返回各年三渠道流入 (T$), 以及存量轨迹 (对齐年份 Y1..Y_{T-1})。
        """
        cfg = self.cfg
        apprec = np.asarray(apprec_median, dtype=float)
        if apprec[0] < 1e-9:                # 去掉 t=0 起点
            apprec = apprec[1:]
        T = len(apprec)
        equity_h, bond_h = cfg.foreign_equity_base, cfg.foreign_bond_base

        flows = {"equity": np.zeros(T), "bond": np.zeros(T), "fdi": np.zeros(T)}
        stocks = {"equity": [], "bond": [], "fdi": []}
        attract = np.zeros(T)

        for t in range(T):
            cum = float(apprec[t])            # 百分数 (t 年累计升值)
            attract_t = 1.0 + cfg.apprec_elasticity * min(cum / 100.0, cfg.apprec_cap)
            mult = attract_t * _drain_boost(t + 1, cfg)   # 年份从1计
            attract[t] = attract_t

            f_eq = equity_h * cfg.equity_inflow_rate * mult
            f_bd = bond_h * cfg.bond_inflow_rate * mult
            f_fd = cfg.fdi_stock * cfg.fdi_inflow_rate * mult

            flows["equity"][t] = f_eq
            flows["bond"][t] = f_bd
            flows["fdi"][t] = f_fd

            # carry 通道: 外资以美元计的收益 = 本地回报 + 本币升值 → 存量自然增值率随当年升值速度抬升
            year_apprec = 0.0 if t == 0 else max(0.0, (float(apprec[t]) - float(apprec[t - 1])) / 100.0)
            g_eq = cfg.re_rate_growth + year_apprec
            equity_h = equity_h * (1 + g_eq) + f_eq
            bond_h = bond_h + f_bd
            stocks["equity"].append(equity_h)
            stocks["bond"].append(bond_h)
            stocks["fdi"].append(cfg.fdi_stock + float(np.sum(flows["fdi"][: t + 1])))

        for k in stocks:
            stocks[k] = np.array(stocks[k])
        return {"annual_flows": flows, "stocks": stocks,
                "attractiveness": attract,
                "drain_mult": np.array([_drain_boost(t + 1, cfg) for t in range(T)])}

    # ── 资本深化增量 (T$) ────────────────────────────────
    def deepening_ts(self, annual_total: np.ndarray) -> float:
        """
        流入资本逐年形成产能: 第t年流入×边际回报×(剩余年限)
        近似积分 (年中到账, 按剩余年-0.5计)。
        """
        cfg = self.cfg
        T = len(annual_total)
        total = 0.0
        for t in range(T):
            remaining = max((T - t - cfg.deepen_lag - 0.5), 0.0)
            total += float(annual_total[t]) * cfg.deepen_return * remaining
        return total

    # ── 全量计算 ──────────────────────────────────────────
    def compute(self, apprec_median: np.ndarray,
                industry_profit: Optional[pd.DataFrame] = None) -> Dict:
        """汇总: 流入轨迹 + 瀑布 + 行业配置"""
        flow_res = self.inflow_path(apprec_median)
        annual_total = (flow_res["annual_flows"]["equity"] +
                        flow_res["annual_flows"]["bond"] +
                        flow_res["annual_flows"]["fdi"])
        cumulative_inflow = float(np.sum(annual_total))

        deepening = self.deepening_ts(annual_total)

        exp_loss = {"loss_ts": 0.0, "export_pool_5y": 0.0, "shock_weighted": 0.0, "detail": {}}
        if industry_profit is not None:
            exp_loss = self.export_loss_ts(industry_profit)

        # 注意: loss_ts 为负数 (损失), 直接相加即可
        net = cumulative_inflow + deepening + exp_loss["loss_ts"]

        # 行业配置: 将A股流入按受益行业权重拆分 (T$)
        eq_flow = flow_res["annual_flows"]["equity"]
        sector_allocation = {k: float(np.sum(eq_flow)) * w
                             for k, w in self.cfg.sector_split.items()}

        return {
            "annual_flows": flow_res["annual_flows"],       # 各年分渠道流入
            "annual_total": annual_total,                    # 各年总流入
            "stocks": flow_res["stocks"],                    # 存量轨迹
            "attractiveness": flow_res["attractiveness"],
            "drain_mult": flow_res["drain_mult"],
            "cumulative_inflow": cumulative_inflow,          # 融资红利 (5年累计, T$)
            "deepening_gain": deepening,                     # 资本深化 (T$)
            "export_loss": exp_loss["loss_ts"],              # 出口利润损失 (T$)
            "export_detail": exp_loss,
            "net_benefit": net,                              # 净效益 (T$)
            "sector_allocation": sector_allocation,          # A股流入行业配置
            "by_year": pd.DataFrame({
                "equity": flow_res["annual_flows"]["equity"],
                "bond": flow_res["annual_flows"]["bond"],
                "fdi": flow_res["annual_flows"]["fdi"],
                "total": annual_total,
            }),
        }
