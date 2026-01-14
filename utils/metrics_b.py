# entropy_fusion.py
from __future__ import annotations
import math
import statistics
from typing import Any, Dict, List, Optional
from utils.prompts import METRICS

# ---------------------------
# 清洗工具
# ---------------------------
def safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def clip01(v: float) -> float:
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def quantile(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if q <= 0:
        return sorted_vals[0]
    if q >= 1:
        return sorted_vals[-1]
    n = len(sorted_vals)
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    w = pos - lo
    return sorted_vals[lo] * (1 - w) + sorted_vals[hi] * w


def winsorize(values: List[Optional[float]], q: float = 0.01, min_n: int = 5) -> List[Optional[float]]:
    valid = [v for v in values if v is not None]
    if len(valid) < min_n:
        return values
    valid_sorted = sorted(valid)
    lo = quantile(valid_sorted, q)
    hi = quantile(valid_sorted, 1 - q)
    out: List[Optional[float]] = []
    for v in values:
        if v is None:
            out.append(None)
        else:
            out.append(lo if v < lo else (hi if v > hi else v))
    return out


def impute(values: List[Optional[float]], strategy: str = "median", default: float = 0.5) -> List[float]:
    valid = [v for v in values if v is not None]
    if not valid:
        return [default for _ in values]
    fill = (sum(valid) / len(valid)) if strategy == "mean" else statistics.median(valid)
    return [fill if v is None else v for v in values]


def apply_direction(v: float, direction: int) -> float:
    # direction=-1：反向（仍保持在[0,1]）
    return v if direction == +1 else (1.0 - v)

# ---------------------------
# 熵权法权重
# ---------------------------
def entropy_weights(X: List[List[float]]) -> List[float]:
    n = len(X)
    if n == 0:
        return []
    m = len(X[0]) if X[0] else 0
    if m == 0:
        return []

    if n < 2:
        return [1.0 / m for _ in range(m)]

    col_sums = [0.0] * m
    for i in range(n):
        for j in range(m):
            col_sums[j] += X[i][j]

    # 概率矩阵 P
    P = [[0.0] * m for _ in range(n)]
    for j in range(m):
        s = col_sums[j]
        if s <= 1e-12:
            for i in range(n):
                P[i][j] = 1.0 / n
        else:
            for i in range(n):
                P[i][j] = X[i][j] / s

    k = 1.0 / math.log(n)
    e = [0.0] * m
    for j in range(m):
        acc = 0.0
        for i in range(n):
            p = P[i][j]
            if p > 0:
                acc += p * math.log(p)
        e[j] = -k * acc  # [0,1]

    d = [max(0.0, 1.0 - ej) for ej in e]
    dsum = sum(d)
    if dsum <= 1e-12:
        return [1.0 / m for _ in range(m)]
    return [dj / dsum for dj in d]


# ---------------------------
# 计算：同一公司跨年熵权 + 输出精简 series
# ---------------------------
def get_confidence(item: Dict[str, Any]) -> float:
    """
    优先级取：
      1) item["overall_confidence"]
      2) metric_confidence 的均值
      3) 缺省 0.5
    """
    v = safe_float(item.get("overall_confidence"))
    if v is not None:
        return clip01(v)

    mc = item.get("metric_confidence") or {}
    vals = []
    if isinstance(mc, dict):
        for vv in mc.values():
            fv = safe_float(vv)
            if fv is not None:
                vals.append(clip01(fv))
    if vals:
        return float(sum(vals) / len(vals))
    return 0.5


def build_compact_series_with_entropy(
    measure_json: Dict[str, Any],
    metrics_cfg: List[Dict[str, Any]] = METRICS,
    *,
    outlier_policy: str = "clip",     # "clip" 或 "drop"
    winsor_q: float = 0.01,
    impute_strategy: str = "median",  # "median" 或 "mean"
    top_contrib_k: Optional[int] = None,  # 只保留TopK贡献；None=全量
) -> Dict[str, Any]:
    """
    将 measure_json["series"] 重建为你希望的精简格式，并写入：
      - involution_index_0_100：0-100
      - contributions_all：按 contribution 降序
    """
    series_in = list(measure_json.get("series") or [])
    if not series_in:
        measure_json["series"] = []
        measure_json["entropy_fusion"] = {"used": False, "reason": "series为空"}
        return measure_json

    # 排序：优先用 measure_json["periods"]，否则按 period 尝试数字排序
    periods = measure_json.get("periods")
    if isinstance(periods, list) and periods:
        order = {str(p): i for i, p in enumerate(periods)}
        series_in.sort(key=lambda it: order.get(str(it.get("period", "")), 10**9))
    else:
        def _k(it: Dict[str, Any]):
            p = str(it.get("period", ""))
            try:
                return (0, int(p))
            except ValueError:
                return (1, p)
        series_in.sort(key=_k)

    n = len(series_in)
    m = len(metrics_cfg)

    # 按列抽取并清洗，得到同向的 X[n][m]（均在[0,1]）
    col_meta = {"per_metric": {}}
    cols: List[List[float]] = []

    for cfg in metrics_cfg:
        key = cfg["key"]
        direction = int(cfg.get("direction", +1))

        raw: List[Optional[float]] = []
        out_of_range = 0
        for item in series_in:
            v0 = safe_float(((item.get("metrics") or {}) if isinstance(item.get("metrics"), dict) else {}).get(key))
            if v0 is None:
                raw.append(None)
                continue

            if outlier_policy == "drop":
                if v0 < 0.0 or v0 > 1.0:
                    raw.append(None)
                    out_of_range += 1
                else:
                    raw.append(v0)
            else:
                if v0 < 0.0 or v0 > 1.0:
                    out_of_range += 1
                raw.append(clip01(v0))

        raw = winsorize(raw, q=winsor_q, min_n=5)
        filled = impute(raw, strategy=impute_strategy, default=0.5)
        aligned = [clip01(apply_direction(v, direction)) for v in filled]  # 同向化

        cols.append(aligned)
        col_meta["per_metric"][key] = {
            "direction": direction,
            "out_of_range_handled": out_of_range,
            "missing_filled": sum(1 for v in raw if v is None),
        }

    X: List[List[float]] = [[0.0] * m for _ in range(n)]
    for j in range(m):
        for i in range(n):
            X[i][j] = cols[j][i]

    # 熵权
    w = entropy_weights(X)

    # 生成想要的 series 输出
    series_out: List[Dict[str, Any]] = []
    for i, item in enumerate(series_in):
        period = str(item.get("period", ""))
        metrics_out = item.get("metrics") if isinstance(item.get("metrics"), dict) else {}

        # 年度贡献拆解（用 0-100 口径）
        contrib_list: List[Dict[str, Any]] = []
        total_1 = 0.0

        for j, cfg in enumerate(metrics_cfg):
            x_0_1 = X[i][j]               # 清洗+同向后的 0-1
            contribution = x_0_1 * w[j]

            total_1 += contribution
            contrib_list.append({
                "metric": cfg["key"],
                "severity_0_1": round(x_0_1, 3),  # 字段名按示例保留
                "weight": round(float(w[j]), 8),
                "contribution": float(contribution),       # 保留高精度便于核对
            })

        contrib_list.sort(key=lambda x: x["contribution"], reverse=True)
        if isinstance(top_contrib_k, int) and top_contrib_k > 0:
            contrib_list = contrib_list[:top_contrib_k]

        series_out.append({
            "period": period,
            "metrics": metrics_out,
            "confidence": round(float(get_confidence(item)), 6),
            "rationale": item.get("rationale") or "",
            "used_evidence": item.get("used_evidence") or [],
            "notes": item.get("notes") or [],
            "involution_index_0_1": round(float(total_1), 2),
            "contributions_all": contrib_list,
        })

    # 写回
    measure_json["series"] = series_out

    # 把权重与清洗信息放到顶层，便于调试与追溯
    measure_json["entropy_fusion"] = {
        "used": True,
        "method": "entropy_weight",
        "outlier_policy": outlier_policy,
        "winsor_q": winsor_q,
        "impute_strategy": impute_strategy,
        "weights": {cfg["key"]: round(float(wj), 10) for cfg, wj in zip(metrics_cfg, w)},
        "cleaning_stats": col_meta,
    }
    return measure_json


# ---------------------------
# 本地快速测试
# ---------------------------
if __name__ == "__main__":
    demo = {
        "company": "BYD",
        "period_unit": "year",
        "periods": ["2011", "2012"],
        "series": [
            {
                "company": "BYD",
                "period": "2011",
                "metrics": {
                    "capital_intensity_level": 0.75,
                    "capacity_utilization_pct": 0.68,
                    "rnd_expense_ratio": 0.065,
                    "rnd_personnel_intensity": 0.18,
                    "digital_intangible_asset_investment_intensity": 0.08,
                    "digital_talent_investment_intensity": 0.12,
                    "employee_training_investment_intensity": 0.14,
                    "high_level_human_capital_investment_intensity": 0.16,
                    "management_expense_ratio": 0.09,
                    "board_meeting_intensity": 0.6,
                    "sales_expense_ratio": 0.075,
                    "sales_personnel_intensity": 0.22
                },
                "overall_confidence": 0.75,
                "rationale": "示例文本",
                "used_evidence": [],
                "notes": ["note1"]
            },
            {
                "company": "BYD",
                "period": "2012",
                "metrics": {
                    "capital_intensity_level": 0.70,
                    "capacity_utilization_pct": 0.72,
                    "rnd_expense_ratio": None,     # 缺失 -> 中位数填补
                    "rnd_personnel_intensity": 0.20,
                    "digital_intangible_asset_investment_intensity": 0.10,
                    "digital_talent_investment_intensity": 0.13,
                    "employee_training_investment_intensity": 0.12,
                    "high_level_human_capital_investment_intensity": 0.17,
                    "management_expense_ratio": 0.10,
                    "board_meeting_intensity": 0.55,
                    "sales_expense_ratio": 1.2,    # 异常 -> clip到1
                    "sales_personnel_intensity": 0.25
                },
                "overall_confidence": 0.73,
                "rationale": "示例文本2",
                "used_evidence": [],
                "notes": []
            }
        ],
    }

    out = build_compact_series_with_entropy(demo, METRICS, top_contrib_k=None)
    for s in out["series"]:
        print(s["period"], s["involution_index_0_1"])
        print(s["contributions_all"][:2])
    print("weights:", out["entropy_fusion"]["weights"])