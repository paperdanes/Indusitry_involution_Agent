from __future__ import annotations
from typing import List, Optional, Union, Dict, Any
from utils import settings
from rag.rag import FaissRAG
from utils.prompts import build_policy_simulation_messages
from utils.llm import chat_json
from utils.json_utils import save_json, pretty_print_json

def _get_store_dir() -> str:
    return getattr(settings, "RAG_STORE_DIR", "rag_store")

def load_rag_or_none(store_dir: Optional[str] = None) -> Optional[FaissRAG]:

    d = store_dir or _get_store_dir()
    rag = FaissRAG.load(d)
    return None if rag.is_empty() else rag


def simulate_policy(
    policy_input: Union[str, List[str]],
    *,
    industry_scope: str = "中国新能源汽车行业",
    time_horizon_months: int = 24,
    top_k: int = 12,
    store_dir: Optional[str] = None,
) -> dict:

    if isinstance(policy_input, list):
        policy_text = "\n".join([f"- {x}" for x in policy_input if str(x).strip()])
    else:
        policy_text = str(policy_input).strip()

    rag = load_rag_or_none(store_dir)
    evidence: List[Dict[str, Any]] = []
    if rag is not None:
        retrieval_query = (
            f"{industry_scope} 内卷 价格战 产能 研发 渠道 供应链 并购 退出 政策干预\n"
            f"用户政策设定：{policy_text}"
        )
        evidence = rag.search(retrieval_query, top_k=top_k)

    try:
        messages = build_policy_simulation_messages(
            policy_input_text=policy_text,
            industry_scope=industry_scope,
            time_horizon_months=time_horizon_months,
            evidence_hits=evidence,
        )
    except TypeError:

        messages = build_policy_simulation_messages(policy_text, evidence)

    out = chat_json(messages)

    # RAG
    if isinstance(out, dict):
        out.setdefault("rag", {})
        out["rag"]["used"] = bool(evidence)
        out["rag"]["top_k"] = int(top_k)
        out["rag"]["store_dir"] = store_dir or _get_store_dir()
        out["rag"]["hits"] = evidence

    return out


def simulate_policy_from_none(
    policy_input: Union[str, List[str]],
    *,
    industry_scope: str = "中国新能源汽车行业",
    time_horizon_months: int = 24,
) -> dict:
    """无RAG."""
    if isinstance(policy_input, list):
        policy_text = "\n".join([f"- {x}" for x in policy_input if str(x).strip()])
    else:
        policy_text = str(policy_input).strip()

    messages = build_policy_simulation_messages(
        policy_input_text=policy_text,
        industry_scope=industry_scope,
        time_horizon_months=time_horizon_months,
        evidence_hits=[],
    )
    out = chat_json(messages)
    if isinstance(out, dict):
        out.setdefault("rag", {})
        out["rag"]["used"] = False
    return out

# ---------------------------
# 本地快速测试
# ---------------------------
if __name__ == "__main__":
    policies = [
        "对低于成本的恶性降价开展联合执法，要求价格调整前进行成本与毛利披露，并对连续多轮大幅降价设定审查触发条件。",
        "建立产能与项目备案的预警阈值机制：当行业产能利用率连续低于某阈值时，暂停新增产能审批，并引导存量整合。",
    ]

    out = simulate_policy(
        policies,
        industry_scope="中国新能源汽车行业",
        time_horizon_months=24,
        top_k=getattr(settings, "TOP_K", 12),
    )

    path = save_json(
        out,
        out_dir=getattr(settings, "OUTPUT_DIR", "output"),
        prefix="policy_sim",
        tag="NEV",
    )

    pretty_print_json(out)
    print(f"\n输出已保存：{path}")
