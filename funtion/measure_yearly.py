# measure_yearly.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import os
import re
from utils import settings
from utils.llm import chat_json
from utils.metrics_b import build_compact_series_with_entropy
from utils.plotting import plot_involution_trend
from utils.prompts import build_year_measure_messages
from utils.json_utils import save_json, pretty_print_json
# RAG导入测试
try:
    from rag.rag import FaissRAG
except Exception as e:
    raise ImportError("缺少 rag.py 或 FaissRAG。请确认 rag.py 在同目录且包含 FaissRAG.load/search/is_empty。") from e

# -----------------------------
# 年度时间切分
# -----------------------------
@dataclass(frozen=True)
class YearPeriod:
    label: str       # "2010"
    start: str       # "2010-01-01"
    end: str         # "2010-12-31"


def _extract_year(s: str) -> int:
    """
    支持输入：'YYYY' 或 'YYYY-MM-DD' 或 'YYYY/MM/DD' 等，提取年份。
    """
    s = (s or "").strip()
    m = re.match(r"^\s*(\d{4})", s)
    if not m:
        raise ValueError(f"无法解析年份：{s!r}（请用 'YYYY' 或 'YYYY-MM-DD'）")
    return int(m.group(1))


def split_to_years(start: str, end: str) -> List[YearPeriod]:
    ys = _extract_year(start)
    ye = _extract_year(end)
    if ys > ye:
        raise ValueError(f"start 年份不能大于 end：{ys} > {ye}")

    years: List[YearPeriod] = []
    for y in range(ys, ye + 1):
        years.append(
            YearPeriod(
                label=str(y),
                start=f"{y}-01-01",
                end=f"{y}-12-31",
            )
        )
    return years

# -----------------------------
# RAG 的 query 组织
# -----------------------------
def _rag_query(company: str, ylabel: str, start: str, end: str) -> str:
    """
    只允许用户限制“车企+时间窗口”，所以检索 query 也只用这些信息组织。
    """
    return f"{company} {ylabel} {start}~{end} 产能 利用率 价格 降价 毛利 专利 招聘 竞争 集中度 同质化"


def _load_store(store_dir: Optional[str] = None) -> FaissRAG:
    d = store_dir or getattr(settings, "RAG_STORE_DIR", "rag_store")
    return FaissRAG.load(d)

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

# -----------------------------
# 主函数：按年份循环测度
# -----------------------------
def measure_company_yearly(
    company: str,
    start: str,
    end: str,
    *,
    rag_store_dir: Optional[str] = None,
    rag_top_k: int = 10,
    output_plot_dir: str = "output",
) -> Dict[str, Any]:
    # 获取年份列表
    years = split_to_years(start, end)
    # 获取知识库地址
    store = _load_store(rag_store_dir)
    use_rag = not store.is_empty()

    series: List[Dict[str, Any]] = []
    for y in years:
        y_query = _rag_query(company, y.label, y.start, y.end)

        # 年度：若库非空则检索；库为空则 hits=[]
        hits = store.search(y_query, top_k=rag_top_k) if use_rag else []

        # 年度：调用一次模型（prompts 若未实现 year 版，回退用 quarter 版）
        messages = build_year_measure_messages(company, y.label, y.start, y.end, hits)
        one_out = chat_json(messages)

        # 标准化：把年度结果放进 series，便于复用 attach_index / plotting
        period = one_out.get("period") or y.label
        series.append(
            {
                "period": period,  # 推荐模型输出也用 "2010"；这里兼容已有结构
                "metrics": one_out.get("metrics", {}),
                "confidence": one_out.get("overall_confidence", 0.5),
                "rationale": one_out.get("rationale", ""),
                "used_evidence": one_out.get("used_evidence", []),
                "notes": one_out.get("notes", []),
            }
        )

    # 如 store 具备 close()，兼容旧实现；FaissRAG 通常不需要
    if hasattr(store, "close"):
        try:
            store.close()
        except Exception:
            pass

    result: Dict[str, Any] = {
        "company": company,
        "time_range": {"start": start, "end": end},
        "period_unit": "year",
        "periods": [y.label for y in years],
        "series": series,
        "rag": {
            "used": bool(use_rag),
            "store_dir": rag_store_dir or getattr(settings, "RAG_STORE_DIR", "rag_store"),
            "top_k": int(rag_top_k),
            "store_empty": not use_rag,
        },
        "notes": [
            "按年份依次循环生成：每个年份（可选）RAG检索 + 一次LLM生成。",
            "若向量库为空，则不使用RAG，直接生成年度测度结果。",
        ],
    }

    # 内卷指数（0-100）+ top贡献（保留）
    result = build_compact_series_with_entropy(result)

    # 趋势图（保留）
    _ensure_dir(output_plot_dir)
    fig_path = plot_involution_trend(result, out_path=f"{output_plot_dir}/{company}_involution_trend.png")
    result["plot_path"] = fig_path

    return result
# -----------------------------
# 主函数(no_rag)：不适用本地知识库按年份循环测度
# -----------------------------
def measure_company_yearly_from_none(
    company: str,
    start: str,
    end: str,
    *,
    output_plot_dir: str = "output",
) -> Dict[str, Any]:
    # 获取年份列表
    years = split_to_years(start, end)

    series: List[Dict[str, Any]] = []
    for y in years:
        y_query = _rag_query(company, y.label, y.start, y.end)

        # 年度：调用一次模型（prompts 若未实现 year 版，回退用 quarter 版）
        messages = build_year_measure_messages(company, y.label, y.start, y.end,rag_hits=[])
        one_out = chat_json(messages)

        # 标准化：把年度结果放进 series，便于复用 attach_index / plotting
        period = one_out.get("period") or y.label
        series.append(
            {
                "period": period,  # 推荐模型输出也用 "2010"；这里兼容已有结构
                "metrics": one_out.get("metrics", {}),
                "confidence": one_out.get("overall_confidence", 0.5),
                "rationale": one_out.get("rationale", ""),
                "used_evidence": one_out.get("used_evidence", []),
                "notes": one_out.get("notes", []),
            }
        )

    result: Dict[str, Any] = {
        "company": company,
        "time_range": {"start": start, "end": end},
        "period_unit": "year",
        "periods": [y.label for y in years],
        "series": series,
        "rag": {
            "used": False,
            "store_dir": "未启动本地知识库",
            "top_k": 0,
            "store_empty": True,
        },
        "notes": [
            "按年份依次循环生成：每个年份（可选）RAG检索 + 一次LLM生成。",
            "若向量库为空，则不使用RAG，直接生成年度测度结果。",
        ],
    }

    # 内卷指数（0-100）+ top贡献（保留）
    result = build_compact_series_with_entropy(result)
    # 趋势图（保留）
    _ensure_dir(output_plot_dir)
    fig_path = plot_involution_trend(result, out_path=f"{output_plot_dir}/{company}_involution_trend.png")
    result["plot_path"] = fig_path

    return result
# -----------------------------
# 交互式循环（保留“多次运行/多年数据”的需求）
# -----------------------------
def interactive_loop() -> None:
    print("=== 年度内卷测度（按年份循环）===")
    print("输入 exit/quit 结束。")

    while True:
        company = input("\n公司名（或 exit 退出）: ").strip()
        if company.lower() in {"exit", "quit", "q"}:
            break

        start = input("起始年份（如 2010）: ").strip()
        end = input("结束年份（如 2024）: ").strip()

        out = measure_company_yearly(company, start, end, rag_top_k=getattr(
            settings, "TOP_K", 10))

        pretty_print_json(out)
        saved = save_json(out, out_dir="output", prefix="measure_yearly", tag=company)
        print(f"\n[Saved] {saved}")
        print(f"[Plot ] {out.get('plot_path')}")

# ---------------------------
# 本地快速测试
# ---------------------------
if __name__ == "__main__":
    # 方式A：交互循环（推荐：满足“多次运行/多年数据”）
    #interactive_loop()

    # 方式B：如需固定参数跑一次，注释 interactive_loop()，改用如下写法：
    company = "比亚迪"
    start = "2011"
    end = "2016"
    out = measure_company_yearly(company, start, end, rag_top_k=10,output_plot_dir="output")
    pretty_print_json(out)
    saved = save_json(out, out_dir="output", prefix="measure_yearly", tag=company)
    print(f"\n[Saved] {saved}")
    print(f"[Plot ] {out.get('plot_path')}")
