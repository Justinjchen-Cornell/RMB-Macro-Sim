"""
宏观场景推演模型 (Macro Scenario Simulation Model)
=================================================

核心逻辑链：
  汇率变动 → [输入性通胀 / 出口竞争力 / 资本流动] → 行业利润 & 出口量 → 资产价格重估

模块结构：
  1. ExchangeRateModule    - 人民币汇率路径生成
  2. InflationModule       - 输入性通胀传导 (汇率 → PPI → CPI)
  3. ExportModule          - 出口量弹性 (Marshall-Lerner 条件)
  4. IndustryProfitModule  - 行业利润 = f(汇率, 通胀, 出口量, 利率)
  5. AssetPriceModule      - 权益/债券/商品/汇率的联合定价
  6. CapitalInflowModule   - 资本流入 (融资红利 + 资本深化, 见 capital_inflow.py)
  7. ScenarioEngine        - 场景驱动 + Monte Carlo

依赖：numpy, pandas, matplotlib
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 资本流入模块 (独立文件, 不反向依赖 model.py)
from capital_inflow import CapitalInflowModule, CapitalConfig

# ── 全局参数容器 ──────────────────────────────────────────────
@dataclass
class MacroParams:
    """宏观结构参数（可从外部 YAML/JSON 覆盖）"""
    # ── 汇率 ──
    cny_spot: float = 7.20          # 基准 USD/CNY
    cny_annual_apprec: float = 0.06  # 年化升值幅度 (6%)
    cny_vol: float = 0.04           # 汇率波动率

    # ── 通胀传导 ──
    import_share: float = 0.18       # 进口占中间投入比例
    ppi_pass_through: float = 0.55   # 汇率→PPI 传递系数
    cpi_from_ppi: float = 0.30       # PPI→CPI 传递系数

    # ── 出口弹性 (Marshall-Lerner) ──
    export_price_elasticity: float = -0.45  # 本币升值1% → 出口量变化
    import_price_elasticity: float = 0.35   # 本币升值1% → 进口量变化

    # ── 利率 ──
    us_10y: float = 0.0481          # 美国10年国债收益率
    cn_10y: float = 0.0169          # 中国10年国债收益率
    rate_diff_mean: float = 0.0312  # 利差均值 (us - cn)
    rate_diff_vol: float = 0.008    # 利差波动率

    # ── 行业权重 (A股映射) ──
    industry_weights: Dict[str, float] = field(default_factory=lambda: {
        "export_lowend": 0.08,   # 低端制造业/小家电
        "export_hightech": 0.12, # 高新技术出口
        "domestic_consumption": 0.20,
        "real_estate": 0.10,
        "infrastructure": 0.10,
        "new_energy": 0.10,
        "semiconductor": 0.08,
        "commodity_metals": 0.06,
        "power_compute": 0.06,
        "gold": 0.04,
        "bank_insurance": 0.06,
    })

    # ── 行业敏感度 (5年累计升值对利润的弹性, % 利润变化 per 10% 升值) ──
    #  经济含义: 人民币累计升值10%, 该行业利润相对基准变化多少个百分点
    fx_sensitivity: Dict[str, float] = field(default_factory=lambda: {
        "export_lowend": -8.0,       # 低端出口：最受伤 (缺乏议价)
        "export_hightech": -3.0,     # 高技术出口：有部分议价能力
        "domestic_consumption": 1.0,
        "real_estate": 1.5,
        "infrastructure": 0.5,
        "new_energy": -1.5,
        "semiconductor": 2.0,        # 进口设备成本下降
        "commodity_metals": 4.0,     # 人民币购买力增强 + 全球定价
        "power_compute": 2.5,
        "gold": 3.5,
        "bank_insurance": 0.5,
    })

    # ── 模拟设置 ──
    n_years: int = 5
    n_simulations: int = 2000
    seed: int = 42


# ═══════════════════════════════════════════════════════════════
#  Module 1: 汇率路径
# ═══════════════════════════════════════════════════════════════
class ExchangeRateModule:
    """
    生成 USD/CNY 路径 (几何布朗运动 + 漂移)
    d(S) / S = μ·dt + σ·dW
    其中 μ = -cny_annual_apprec (升值 = 汇率数字下降)
    """
    def __init__(self, params: MacroParams):
        self.p = params

    def simulate(self, n_years: int, n_sims: int, seed: int = 42) -> np.ndarray:
        """返回 (n_sims, n_years+1) 的汇率路径"""
        np.random.seed(seed)
        dt = 1.0
        drift = -self.p.cny_annual_apprec   # 升值 → 汇率值下降
        vol = self.p.cny_vol

        S = np.zeros((n_sims, n_years + 1))
        S[:, 0] = self.p.cny_spot

        for t in range(1, n_years + 1):
            Z = np.random.standard_normal(n_sims)
            S[:, t] = S[:, t - 1] * np.exp((drift - 0.5 * vol**2) * dt + vol * np.sqrt(dt) * Z)

        return S

    def cumulative_appreciation(self, path: np.ndarray) -> np.ndarray:
        """计算累计升值幅度 (正=升值)"""
        return (self.p.cny_spot / path - 1) * 100  # 百分比


# ═══════════════════════════════════════════════════════════════
#  Module 2: 输入性通胀传导
# ═══════════════════════════════════════════════════════════════
class InflationModule:
    """
    PPI(t) = ppi_pass_through × Δ(进口价格指数)
    CPI(t) = cpi_from_ppi × PPI(t) + (1 - cpi_from_ppi) × CPI(t-1)  [部分滞后]
    """
    def __init__(self, params: MacroParams):
        self.p = params

    def compute(self, exchange_rate_path: np.ndarray) -> Dict[str, np.ndarray]:
        """
        输入: (n_sims, T) 汇率路径
        输出: PPI 冲击 & CPI 路径
        """
        S = exchange_rate_path
        # 汇率变化率 (正 = 贬值 = 通胀压力)
        fx_change = (S[:, 1:] - S[:, :-1]) / S[:, :-1]

        # PPI 冲击
        ppi_shock = self.p.ppi_pass_through * fx_change / self.p.import_share

        # CPI: 部分传递 + 滞后
        n_sims, T = S.shape
        cpi = np.zeros((n_sims, T))
        cpi[:, 0] = 0.02  # 基准2%

        for t in range(1, T):
            cpi[:, t] = (self.p.cpi_from_ppi * ppi_shock[:, t - 1] +
                         (1 - self.p.cpi_from_ppi) * cpi[:, t - 1])
            cpi[:, t] = np.clip(cpi[:, t], -0.05, 0.15)

        return {"ppi": ppi_shock, "cpi": cpi}


# ═══════════════════════════════════════════════════════════════
#  Module 3: 出口量弹性
# ═══════════════════════════════════════════════════════════════
class ExportModule:
    """
    出口量变动 = 出口价格弹性 × 本币升值幅度
    同时考虑: 贸易伙伴收入弹性 (外需)
    """
    def __init__(self, params: MacroParams):
        self.p = params

    def compute(self, appreciation_pct: np.ndarray,
                foreign_demand_growth: float = 0.03) -> Dict[str, np.ndarray]:
        """
        appreciation_pct: (n_sims, T) 累计升值幅度 (%)
        返回: 出口量指数变化
        """
        # 本币升值 → 出口量下降
        export_volume_change = (self.p.export_price_elasticity *
                                appreciation_pct / 100)
        # 外需拉动 (正)
        export_volume_change += foreign_demand_growth

        return {
            "export_volume_change": export_volume_change,
            "net_export_contribution": export_volume_change * 0.20,  # 净出口占GDP约20%
        }


# ═══════════════════════════════════════════════════════════════
#  Module 4: 行业利润冲击
# ═══════════════════════════════════════════════════════════════
class IndustryProfitModule:
    """
    行业利润冲击 = 汇率敏感度 × 升值幅度
                  + 通胀冲击 (成本端)
                  + 出口量效应
                  + 利率效应
    """
    def __init__(self, params: MacroParams):
        self.p = params

    def compute(self, appreciation_pct: np.ndarray,
                cpi_path: np.ndarray,
                export_change: np.ndarray) -> pd.DataFrame:
        """
        计算各行业年度利润冲击 (相对基准的百分比变化)。

        模型: ΔΠ_i(t) = [sens_i × (apprec(t) - apprec(t-1)) / 10]
                        + inflation_effect + export_effect + rate_effect

        其中 sens_i = 每10%累计升值的利润弹性 (来自 config)
        通胀/出口/利率效应做归一化, 确保总冲击落在 [-30%, +30%] 经济合理区间。
        """
        # 取中位数路径 (n_sims, T) → (T,)
        apprec = np.median(appreciation_pct, axis=0)
        cpi_med = np.median(cpi_path, axis=0)
        exp_med = np.median(export_change, axis=0)

        T = len(apprec)
        results = {}

        for industry, sens in self.p.fx_sensitivity.items():
            # ① 汇率效应: 逐年递增, 线性累积 (每10%升值 → sens% 利润变化)
            #   apprec 单位为 %, 所以 apprec/10 = "多少个10%"
            fx_effect = sens * (apprec / 10.0) / 100.0   # → 小数

            # ② 通胀效应 (温和, 全年CPI的1/3以内)
            if industry in ["commodity_metals", "gold", "power_compute"]:
                inflation_effect = 0.15 * cpi_med   # 资源品小幅受益
            elif industry in ["export_lowend", "domestic_consumption"]:
                inflation_effect = -0.10 * cpi_med  # 消费端承压
            else:
                inflation_effect = 0.03 * cpi_med   # 中性

            # ③ 出口量效应 (仅出口行业, 弹性较小)
            if "export" in industry:
                export_effect = 0.15 * exp_med
            else:
                export_effect = np.zeros(T)

            # ④ 利率效应 (利差收窄 → 估值修复, 小量)
            rate_effect = 0.05 * (apprec / 100.0)

            # 合计并裁剪到经济合理区间
            total = fx_effect + inflation_effect + export_effect + rate_effect
            total = np.clip(total, -0.30, 0.30)
            results[industry] = total

        df = pd.DataFrame(results)
        df.index = [f"Y{i}" for i in range(T)]
        return df


# ═══════════════════════════════════════════════════════════════
#  Module 5: 资产价格联合定价
# ═══════════════════════════════════════════════════════════════
class AssetPriceModule:
    """
    权益:  E(R) = 无风险 + β×(汇率效应 + 盈利效应)
    债券:  收益率 = cn_10y + 期限溢价 + 通胀预期
    商品:  与美元负相关 + 供需
    黄金:  与实际利率负相关 + 央行购金
    """
    def __init__(self, params: MacroParams):
        self.p = params

    def equity_return(self, industry_profit: pd.DataFrame) -> pd.Series:
        """
        加权行业利润冲击 → 指数年化收益贡献。
        逻辑: 行业利润冲击是"5年累计相对变化", 分摊到每年 ≈ 冲击/5。
        再叠加基准盈利增长(约8%, 来自新质生产力驱动)。
        """
        weights = pd.Series(self.p.industry_weights)
        aligned = industry_profit[[c for c in weights.index if c in industry_profit.columns]]
        weighted = aligned * weights[aligned.columns].values
        cumul = weighted.sum(axis=1)          # 各年累计冲击
        annualized = cumul / max(len(cumul), 1)  # 分摊到每年
        base_growth = 0.08                     # 新质生产力驱动基准盈利增长
        return base_growth + annualized        # 年化

    def bond_return(self, cpi_path: np.ndarray, year_index: int = -1) -> float:
        """
        债券年化持有期收益 (简化久期模型)。
        R_bond ≈ coupon + roll_down - duration × Δy
        在升值+温和通胀情景下, 中国国债收益率小幅上行 → 资本损失,
        但票息(1.69%)为底。净年化约 0~2%。
        """
        cpi_terminal = np.median(cpi_path[:, year_index])
        # 升值情景下通胀可控, 收益率温和上行 ~30-50bp
        yield_change = 0.004 + 0.3 * max(cpi_terminal, 0)
        duration = 6.0  # 近似7年期国债修正久期
        coupon = self.p.cn_10y
        cap_loss = -duration * yield_change
        return coupon + cap_loss  # 年化

    def gold_return(self, appreciation_pct: np.ndarray,
                    cpi_path: np.ndarray) -> np.ndarray:
        """
        黄金年化收益 (简化因子模型, 单位: 年化小数)。
        因子:
          - 实际利率 (负相关)
          - 央行购金 / 去美元化 (结构性 +3~5%)
          - 人民币升值对人民币计价黄金的拖累
        输出裁剪到 [-5%, +20%] 合理区间。
        """
        apprec = np.median(appreciation_pct, axis=0)   # (T,)
        cpi = np.median(cpi_path, axis=0)              # (T,)

        real_rate = self.p.us_10y - cpi               # 美国实际利率
        structural = 0.04                              # 央行购金+避险结构性贡献
        usd_gold = 0.05 - 1.5 * real_rate             # 美元金价 (实际利率敏感性1.5)
        cny_effect = -0.15 * (apprec / 100.0)         # 人民币升值拖累人民币金价

        gold = usd_gold + structural + cny_effect
        gold = np.clip(gold, -0.05, 0.20)
        return gold

    def commodity_return(self, cpi_path: np.ndarray) -> np.ndarray:
        """
        工业金属年化收益 = 全球需求(中国PMI代理) + 通胀弹性
        简化: 2% 基准 + 0.5×CPI + 中国实体需求溢价(1%)
        """
        cpi = np.median(cpi_path, axis=0)
        base = 0.02
        inflation_beta = 0.5 * np.clip(cpi, -0.02, 0.08)
        china_premium = 0.01   # 中国作为最大制造国的需求支撑
        return base + inflation_beta + china_premium


# ═══════════════════════════════════════════════════════════════
#  Scenario Engine
# ═══════════════════════════════════════════════════════════════
class ScenarioEngine:
    """编排所有模块，生成完整场景输出"""

    def __init__(self, params: Optional[MacroParams] = None,
                 capital_cfg: Optional[CapitalConfig] = None):
        self.params = params or MacroParams()
        self.capital_cfg = capital_cfg or CapitalConfig()
        self.results: Dict = {}

    def run(self) -> Dict:
        p = self.params

        # 1. 汇率
        fx_mod = ExchangeRateModule(p)
        fx_path = fx_mod.simulate(p.n_years, p.n_simulations, p.seed)
        apprec = fx_mod.cumulative_appreciation(fx_path)

        # 2. 通胀
        infl_mod = InflationModule(p)
        infl = infl_mod.compute(fx_path)

        # 3. 出口
        exp_mod = ExportModule(p)
        export = exp_mod.compute(apprec)

        # 4. 行业利润
        ind_mod = IndustryProfitModule(p)
        industry_profit = ind_mod.compute(apprec, infl["cpi"],
                                          export["export_volume_change"])

        # 5. 资产价格
        asset_mod = AssetPriceModule(p)
        equity_ret = asset_mod.equity_return(industry_profit)
        bond_ret = asset_mod.bond_return(infl["cpi"])
        gold_ret = asset_mod.gold_return(apprec, infl["cpi"])
        commodity_ret = asset_mod.commodity_return(infl["cpi"])

        # 6. 资本流入 (收益侧: 融资红利 + 资本深化)
        cap_mod = CapitalInflowModule(self.capital_cfg)
        apprec_median = np.median(apprec, axis=0)   # (T,) 百分数
        capital = cap_mod.compute(apprec_median, industry_profit)

        self.results = {
            "fx_path": fx_path,
            "appreciation": apprec,
            "cpi": infl["cpi"],
            "ppi": infl["ppi"],
            "export_volume": export["export_volume_change"],
            "industry_profit": industry_profit,
            "equity_return": equity_ret,
            "bond_return": bond_ret,
            "gold_return": gold_ret,
            "commodity_return": commodity_ret,
            "capital_inflow": capital,   # 新: 资本流入全景 (含净效益瀑布)
        }
        return self.results

    # ── 可视化 ────────────────────────────────────────────────
    def plot(self, save_dir: str = "/data/workspace/macro_sim/charts"):
        import os
        os.makedirs(save_dir, exist_ok=True)
        from matplotlib import font_manager
        for name in ["Microsoft YaHei", "SimHei", "PingFang SC",
                     "Noto Sans CJK SC", "WenQuanYi Micro Hei"]:
            if name in {f.name for f in font_manager.fontManager.ttflist}:
                plt.rcParams["font.family"] = name
                break
        plt.rcParams["axes.unicode_minus"] = False

        res = self.results
        years = list(range(self.params.n_years + 1))

        # ── 图1: 汇率路径 (分位数带) ──
        fig, ax = plt.subplots(figsize=(10, 5))
        path = res["fx_path"]
        median = np.median(path, axis=0)
        p25 = np.percentile(path, 25, axis=0)
        p75 = np.percentile(path, 75, axis=0)
        ax.plot(years, median, "b-", lw=2, label="中位数路径")
        ax.fill_between(years, p25, p75, alpha=0.3, color="blue", label="25%-75%分位")
        ax.axhline(self.params.cny_spot, color="gray", ls="--", alpha=0.7, label="基准7.20")
        ax.set_title("USD/CNY 路径模拟 (GBM + 6%年化升值漂移)", fontsize=13)
        ax.set_xlabel("年")
        ax.set_ylabel("USD/CNY")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(f"{save_dir}/01_fx_path.png", dpi=130)
        plt.close(fig)

        # ── 图2: CPI 路径 ──
        fig, ax = plt.subplots(figsize=(10, 5))
        cpi = res["cpi"]
        ax.plot(years[1:], np.median(cpi, axis=0)[1:], "r-o", label="CPI (中位数)")
        ax.axhline(0.02, color="gray", ls="--", alpha=0.7, label="2% 目标")
        ax.set_title("输入性通胀传导: CPI路径", fontsize=13)
        ax.set_xlabel("年")
        ax.set_ylabel("CPI (%)")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(f"{save_dir}/02_cpi_path.png", dpi=130)
        plt.close(fig)

        # ── 图3: 行业利润冲击 (最终年 Y4) ──
        fig, ax = plt.subplots(figsize=(11, 6))
        final = res["industry_profit"].iloc[-1].sort_values()
        colors = ["#e74c3c" if v < 0 else "#27ae60" for v in final]
        bars = ax.barh(range(len(final)), final.values, color=colors, alpha=0.85)
        ax.set_yticks(range(len(final)))
        ax.set_yticklabels(final.index, fontsize=9)
        ax.axvline(0, color="black", lw=0.8)
        ax.set_title(f"行业利润冲击 (Y{len(final)-1} 相对基准, %)", fontsize=13)
        ax.set_xlabel("利润变化 (%)")
        ax.grid(alpha=0.3, axis="x")
        fig.tight_layout()
        fig.savefig(f"{save_dir}/03_industry_profit.png", dpi=130)
        plt.close(fig)

        # ── 图4: 资产收益对比 ──
        fig, ax = plt.subplots(figsize=(9, 5))
        assets = {
            "A股(加权)": float(res["equity_return"].iloc[-1]),
            "中国国债": float(res["bond_return"]),
            "黄金": float(np.median(res["gold_return"])),
            "工业金属": float(np.median(res["commodity_return"])),
        }
        names = list(assets.keys())
        vals = list(assets.values())
        colors = ["#3498db", "#95a5a6", "#f39c12", "#e67e22"]
        bars = ax.bar(names, vals, color=colors, alpha=0.85)
        ax.axhline(0, color="black", lw=0.8)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, v + 0.01,
                    f"{v:.1%}", ha="center", fontsize=11, fontweight="bold")
        ax.set_title("5年期年化收益模拟 (中位数情景)", fontsize=13)
        ax.set_ylabel("年化收益率")
        ax.grid(alpha=0.3, axis="y")
        fig.tight_layout()
        fig.savefig(f"{save_dir}/04_asset_returns.png", dpi=130)
        plt.close(fig)

        # ── 图5: 出口量变化 ──
        fig, ax = plt.subplots(figsize=(10, 5))
        exp_v = res["export_volume"]
        # 低端 vs 高端
        low = exp_v[:, -1] if exp_v.ndim > 1 else exp_v[-1]
        ax.plot(years[1:], np.median(exp_v, axis=0)[1:], "m-s", label="净出口贡献")
        ax.axhline(0, color="black", lw=0.8)
        ax.set_title("净出口贡献变化 (Marshall-Lerner)", fontsize=13)
        ax.set_xlabel("年")
        ax.set_ylabel("GDP占比变化 (%)")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(f"{save_dir}/05_export.png", dpi=130)
        plt.close(fig)

        print(f"[✓] 图表已保存至 {save_dir}/")


# ═══════════════════════════════════════════════════════════════
#  命令行入口
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import os

    print("=" * 60)
    print("  宏观场景推演模型 (Macro Scenario Simulation Model)")
    print("  人民币升值 → 通胀/出口/行业利润 → 资产价格")
    print("=" * 60)

    # ── 基准情景 ──
    print("\n▶ 运行基准情景 (人民币年化升值6%)...")
    engine = ScenarioEngine()
    results = engine.run()
    engine.plot()

    # ── 输出摘要 ──
    print("\n" + "─" * 50)
    print("  模拟结果摘要 (中位数路径, 第5年)")
    print("─" * 50)

    apprec_final = np.median(results["appreciation"], axis=0)[-1]
    print(f"\n  人民币累计升值:     {apprec_final:.1f}%")
    print(f"  USD/CNY 终值:       {np.median(results['fx_path'], axis=0)[-1]:.2f}")

    cpi_final = np.median(results["cpi"], axis=0)[-1]
    print(f"  CPI (第5年):        {cpi_final:.1%}")

    print(f"\n  行业利润冲击 (Y4):")
    for ind, val in results["industry_profit"].iloc[-1].sort_values().items():
        flag = "↓" if val < 0 else "↑"
        print(f"    {ind:25s} {flag} {val:+.1%}")

    print(f"\n  资产年化收益 (5年中位):")
    print(f"    A股(加权):         {float(results['equity_return'].iloc[-1]):.1%}")
    print(f"    中国国债:           {float(results['bond_return']):.1%}")
    print(f"    黄金:               {float(np.median(results['gold_return'])):.1%}")
    print(f"    工业金属:           {float(np.median(results['commodity_return'])):.1%}")

    # ── 资本流入瀑布 ──
    if "capital_inflow" in results:
        cap = results["capital_inflow"]
        print(f"\n  资本流入净效益瀑布 (5年累计, T$):")
        print(f"    出口部门利润损失:   {cap['export_loss']:>+8.2f}")
        print(f"    资本净流入(融资):   {cap['cumulative_inflow']:>+8.2f}")
        print(f"    资本深化(GDP增量): {cap['deepening_gain']:>+8.2f}")
        print(f"    ───────────────────────────")
        print(f"    净效益:             {cap['net_benefit']:>+8.2f}")

    # ── 敏感性分析：不同升值速度 ──
    print("\n" + "─" * 50)
    print("  敏感性分析: 升值速度 vs 行业利润 & 资产收益")
    print("─" * 50)

    scenarios = [
        ("快速升值 (10%/年)", 0.10),
        ("基准 (6%/年)", 0.06),
        ("慢速升值 (3%/年)", 0.03),
        ("不升值 (0%)", 0.00),
    ]

    print(f"\n  {'情景':<20s} {'低端制造':>10s} {'半导体':>10s} {'金属/黄金':>10s} {'A股加权':>10s}")
    print("  " + "─" * 62)

    for name, apprec_rate in scenarios:
        p2 = MacroParams(cny_annual_apprec=apprec_rate, seed=123)
        eng2 = ScenarioEngine(p2)
        r2 = eng2.run()

        low = r2["industry_profit"]["export_lowend"].iloc[-1]
        semi = r2["industry_profit"]["semiconductor"].iloc[-1]
        metal = r2["industry_profit"]["commodity_metals"].iloc[-1]
        eq = float(r2["equity_return"].iloc[-1])

        print(f"  {name:<20s} {low:>+10.1%} {semi:>+10.1%} {metal:>+10.1%} {eq:>+10.1%}")

    print("\n" + "=" * 60)
    print("  ✓ 完成。详见 charts/ 目录下的图表。")
    print("=" * 60)
