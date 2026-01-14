# identify.py
from __future__ import annotations

from typing import List, Optional
from utils import settings
from rag.rag import FaissRAG
from utils.prompts import build_identify_messages  # type: ignore
from utils.llm import chat_json  # type: ignore
from utils.json_utils import save_json, pretty_print_json  # type: ignore

def _get_store_dir() -> str:
    return getattr(settings, "RAG_STORE_DIR", "rag_store")

def load_rag_or_none(store_dir: Optional[str] = None) -> Optional[FaissRAG]:
    """
    若库存在且非空：返回 FaissRAG；否则返回 None（后续走“无 RAG 对话”路径）。
    """
    d = store_dir or _get_store_dir()
    rag = FaissRAG.load(d)
    return None if rag.is_empty() else rag

def identify(
    user_query: str,
    *,
    top_k: int = 12,
    store_dir: Optional[str] = None,
) -> dict:
    """
    默认从本地知识库检索证据；
    若库不存在或为空：直接对话，不走 RAG。
    """
    rag = load_rag_or_none(store_dir)
    evidence: List[dict] = []
    if rag is not None:
        evidence = rag.search(user_query, top_k=top_k)

    #优先传 evidence；如签名不同，用兜底逻辑
    try:
        messages = build_identify_messages(user_query, evidence_hits=evidence)
    except TypeError:
        rag_text = "\n\n".join([h.get("text", "") for h in evidence]) if evidence else ""
        messages = build_identify_messages(user_query, evidence_hits=rag_text)  # type: ignore

    out = chat_json(messages)

    # 把证据附加回输出，便于可解释性与调试
    if isinstance(out, dict):
        out.setdefault("rag", {})
        out["rag"]["used"] = bool(evidence)
        out["rag"]["top_k"] = int(top_k)
        out["rag"]["store_dir"] = store_dir or _get_store_dir()
        out["rag"]["hits"] = evidence

    return out


def identify_from_none(user_query: str) -> dict:
    """
    “无 RAG”识别接口。
    """
    messages = build_identify_messages(user_query, evidence_hits=[])
    out = chat_json(messages)
    if isinstance(out, dict):
        out.setdefault("rag", {})
        out["rag"]["used"] = False
    return out

# ---------------------------
# 本地快速测试
# ---------------------------
if __name__ == "__main__":
    car_name = "比亚迪"
    query = f"请对{car_name}汽车企业，给出至少3个标签，并判断是否存在内卷式竞争（如果证据不足请说明）。"

    out = identify(query, top_k=getattr(settings, "TOP_K", 10))
    path = save_json(out, out_dir=getattr(settings, "OUTPUT_DIR", "output"), prefix="identify", tag=car_name)

    pretty_print_json(out)
    print(f"\n输出已保存：{path}")

    try:
        print(f"{car_name}公司是否存在内卷：{out['overall']['has_involution']}")

        print(f"置信度: {out['overall']['confidence']}")
    except Exception:
        pass
