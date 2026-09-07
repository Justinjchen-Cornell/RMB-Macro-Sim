"""modules/inflation - 油价/汇率 -> CPI 传导对冲。"""
from .core import UnifiedParams

def oil_cpi_raw(oil_price_series, p: UnifiedParams):
    """油价→CPI 滞后分布输入压力(每期). 输入为价格水平列表。"""
    out = []
    prev = p.oil_base
    acc = 0.0
    for i, px in enumerate(oil_price_series):
        yoy = px / prev - 1.0
        for lag, w in enumerate(p.oil_lags):
            t = i + lag
            while len(out) <= t:
                out.append(0.0)
            out[t] += w * yoy
        prev = px
    return [x * 100.0 for x in out[:len(oil_price_series)]]  # CPI pp




def inflation_net(appr_rate, p: UnifiedParams, horizon=5, oil_pct=0.30):
    """分层: 油价输入压力(5期累计 ~0.14*oil) vs 升值对冲(ept*appr累积)。"""
    raw = sum(p.oil_lags) * oil_pct * 100.0
    offset = min(raw, p.ept * appr_rate * 100.0 * horizon)
    return {"raw_pp": round(raw, 2), "offset_pp": round(offset, 2),
            "net_pp": round(max(0.0, raw - offset), 2),
            "absorbed_pct": round(min(100.0, offset / raw * 100.0), 1)}


