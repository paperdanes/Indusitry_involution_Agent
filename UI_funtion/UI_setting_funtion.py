from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import streamlit as st

from utils.json_to_word import json_report_to_docx
from utils.utils import ensure_dir, abspath, safe_get
from rag.rag import FaissRAG

# -----------------------------
# Rag知识库管理函数
# -----------------------------
def load_store_fresh(store_dir: str):
    ensure_dir(store_dir)
    return FaissRAG.load(store_dir)

def store_status(store_dir: str) -> Dict[str, Any]:
    rag = load_store_fresh(store_dir)
    try:
        ntotal = int(rag.index.ntotal) if rag.index is not None else 0
    except Exception:
        ntotal = 0
    try:
        docs_count = len(rag.docs) if getattr(rag, "docs", None) is not None else 0
    except Exception:
        docs_count = 0
    try:
        empty = bool(rag.is_empty())
    except Exception:
        empty = (ntotal == 0)
    return {
        "store_dir": abspath(store_dir),
        "empty": empty,
        "dim": getattr(rag, "dim", None),
        "ntotal": ntotal,
        "docs": docs_count,
    }

def list_docs(store_dir: str) -> List[Dict[str, Any]]:
    rag = load_store_fresh(store_dir)
    if not hasattr(rag, "list_docs"):
        return []
    try:
        out = rag.list_docs()
        return out if isinstance(out, list) else []
    except Exception:
        return []

def add_files_into_store(store_dir: str, paths: List[str]) -> Dict[str, Any]:
    rag = load_store_fresh(store_dir)
    added = rag.add_files(paths)
    rag.save(store_dir)
    return added if isinstance(added, dict) else {"added": added}

def remove_doc_from_store_by_id(store_dir: str, doc_id: str) -> bool:
    rag = load_store_fresh(store_dir)
    ok = rag.remove_doc(doc_id=doc_id, source_path=None)
    rag.save(store_dir)
    return bool(ok)

def clear_store_files(store_dir: str) -> int:
    removed = 0
    # 优先使用 store_paths
    if hasattr(FaissRAG, "store_paths"):
        p = FaissRAG.store_paths(store_dir)
        for k in ["index", "chunks", "manifest"]:
            fp = p.get(k)
            if fp and os.path.exists(fp):
                os.remove(fp)
                removed += 1
        return removed

    # 兜底：常见文件名
    for name in ["index.faiss", "chunks.jsonl", "manifest.json"]:
        fp = os.path.join(store_dir, name)
        if os.path.exists(fp):
            os.remove(fp)
            removed += 1
    return removed

# -----------------------------
# 证据链导出函数
# -----------------------------
def render_rag_hits(hits: Any) -> None:
    if not hits:
        st.info("未返回证据片段（可能是向量库为空或未启用 RAG）。")
        return
    if not isinstance(hits, list):
        st.warning("证据结构不是 list；原始内容如下：")
        st.write(hits)
        return
    st.markdown("#### 本地知识库证据片段")
    st.caption("每条证据的具体字段取决于 rag.search(...) 的返回结构。")
    for i, h in enumerate(hits, start=1):
        if not isinstance(h, dict):
            with st.expander(f"Hit #{i}"):
                st.write(h)
            continue
        score = h.get("score", h.get("similarity", h.get("distance")))
        src = h.get("source", h.get("meta", {}).get("source") if isinstance(h.get("meta"), dict) else None)
        title = f"Hit #{i}"
        if score is not None:
            title += f" | score={score}"
        if src:
            title += f" | source={src}"
        with st.expander(title):
            text = h.get("text") or h.get("content") or ""
            if text:
                st.markdown("**text**")
                st.write(text)
                st.divider()
            st.markdown("**raw hit dict**")
            st.json(h)


def render_labels_block(labels: Any) -> None:
    if not labels:
        st.info("输出中未发现 labels 字段或 labels 为空。")
        return
    if not isinstance(labels, list):
        st.warning("labels 字段不是 list；原始内容如下：")
        st.write(labels)
        return

    rows: List[Dict[str, Any]] = []
    for it in labels:
        if not isinstance(it, dict):
            continue
        rows.append(
            {
                "label_id": it.get("label_id"),
                "label_name": it.get("label_name"),
                "score": it.get("score"),
                "confidence": it.get("confidence"),
                "evidence_level": it.get("evidence_level"),
            }
        )
    import pandas as pd

    df = pd.DataFrame(rows)
    st.markdown("#### 标签表格")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.divider()
    st.markdown("#### 标签详情")

    for it in labels:
        if not isinstance(it, dict):
            continue
        name = it.get("label_name") or it.get("label_id") or "label"
        lid = it.get("label_id", "")
        score = it.get("score")
        conf = it.get("confidence")
        ev_level = it.get("evidence_level")

        title = f"{name}"
        if lid:
            title += f"（{lid}）"
        if score is not None:
            title += f" | 分数={score}"
        if conf is not None:
            title += f" | 置信度={conf}"

        with st.expander(title, expanded=False):
            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                st.metric("分数", value=str(score) if score is not None else "N/A")
                try:
                    if score is not None:
                        s = float(score)
                        s = max(0.0, min(100.0, s))
                        st.progress(s / 100.0)
                except Exception:
                    pass
            with c2:
                st.metric("置信度", value=str(conf) if conf is not None else "N/A")
                try:
                    if conf is not None:
                        c = float(conf)
                        c = max(0.0, min(1.0, c))
                        st.progress(c)
                except Exception:
                    pass
            with c3:
                st.write("evidence_level:", ev_level if ev_level is not None else "N/A")

            rationale = it.get("rationale")
            if rationale:
                st.markdown("**相关说明**")
                st.write(rationale)

            evidences = it.get("evidences")
            if evidences:
                st.markdown("**参考信息**")
                st.write(evidences)


# -----------------------------
# 政策仿真所需函数
# -----------------------------
def split_policies(raw: str) -> List[str]:
    """
    优先按空行分隔；若无空行则按以“- ”开头的行切分；否则视为单条。
    """
    text = (raw or "").strip()
    if not text:
        return []

    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    if len(blocks) >= 2:
        return blocks

    lines = [ln.rstrip() for ln in text.splitlines()]
    if sum(1 for ln in lines if ln.strip().startswith("- ")) >= 2:
        cur: List[str] = []
        out: List[str] = []
        for ln in lines:
            if ln.strip().startswith("- "):
                if cur:
                    out.append("\n".join(cur).strip())
                    cur = []
                cur.append(ln.strip()[2:])
            else:
                cur.append(ln)
        if cur:
            out.append("\n".join(cur).strip())
        return [x for x in out if x]

    return [text]


def get_pol_section(pol: Dict[str, Any], x: Any, sec: str) -> Dict[str, Any]:
    """兼容 '3.x.1'（字面量x）与 '3.<x>.1'（展开编号）两种键名。"""
    k1 = f"3.x.{sec}"
    if k1 in pol and isinstance(pol[k1], dict):
        return pol[k1]
    k2 = f"3.{x}.{sec}"
    if k2 in pol and isinstance(pol[k2], dict):
        return pol[k2]
    for k, v in pol.items():
        if isinstance(k, str) and k.startswith("3.") and k.endswith(f".{sec}") and isinstance(v, dict):
            return v
    return {}

def range_mid(r: Any) -> Optional[float]:
    if isinstance(r, (list, tuple)) and len(r) == 2:
        a, b = r
        try:
            return (float(a) + float(b)) / 2.0
        except Exception:
            return None
    return None

def export_docx_bytes(report_json: Dict[str, Any], output_dir: str, filename: str) -> bytes:
    """docx文件生成和保存"""
    ensure_dir(output_dir)
    out_path = os.path.join(output_dir, filename)
    json_report_to_docx(report_json, out_path)
    with open(out_path, "rb") as f:
        return f.read()
# -----------------------------
# 政策干预仿真
# -----------------------------
def render_policy_outputs(out: Dict[str, Any]) -> None:
    import pandas as pd

    meta = out.get("meta", {}) if isinstance(out.get("meta"), dict) else {}
    ch2_21 = safe_get(out, ["chapter2", "2.1"], default={})

    baseline_range = ch2_21.get("involution_index_baseline_range")
    baseline_mid = range_mid(baseline_range)

    st.markdown("#### 概览")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("行业范围", value=str(meta.get("industry_scope", ""))[:28] or "N/A")
    with c2:
        st.metric("仿真跨度（月）", value=str(meta.get("time_horizon_months", "N/A")))
    with c3:
        st.metric("政策数量", value=str(meta.get("policy_count", "N/A")))
    with c4:
        st.metric("基准内卷指数（中值）", value=(f"{baseline_mid:.1f}" if baseline_mid is not None else "N/A"))

    st.caption(
        f"基准内卷指数区间：{baseline_range if baseline_range is not None else '未提供'} | "
        f"RAG used：{safe_get(out, ['rag','used'], default=False)}"
    )

    policies = safe_get(out, ["chapter3", "policies"], default=[])
    if not isinstance(policies, list) or not policies:
        st.warning("第三章 policies 为空或格式不正确。")
        return

    rows: List[Dict[str, Any]] = []
    for pol in policies:
        if not isinstance(pol, dict):
            continue
        x = pol.get("x")
        name = pol.get("policy_name")
        s4 = get_pol_section(pol, x, "4")
        inv = s4.get("involution_index") if isinstance(s4.get("involution_index"), dict) else {}
        b = inv.get("baseline_range")
        a = inv.get("after_range")
        c = inv.get("change_range")
        conf = inv.get("confidence")

        rows.append(
            {
                "政策序号": x,
                "政策名称": name,
                "基准区间": b,
                "政策后区间": a,
                "变化区间": c,
                "变化中值": range_mid(c),
                "置信度": conf,
            }
        )

    df = pd.DataFrame(rows).sort_values(by="政策序号")
    # 便于可视化的中值列
    df["基准中值"] = df["基准区间"].apply(range_mid)
    df["政策后中值"] = df["政策后区间"].apply(range_mid)
    st.markdown("#### 政策影响汇总")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if "置信度" in df.columns and df["置信度"].notna().any():
        conf_df = df[["政策序号", "政策名称", "置信度"]].copy()
        conf_df["label"] = conf_df["政策序号"].astype(str) + "-" + conf_df["政策名称"].astype(str)
        conf_df = conf_df.set_index("label")[["置信度"]]
        st.markdown("#### 影响评估置信度")
        st.bar_chart(conf_df)

    ch4 = out.get("chapter4", {}) if isinstance(out.get("chapter4"), dict) else {}
    sec41 = ch4.get("4.1", {}) if isinstance(ch4.get("4.1"), dict) else {}
    st.divider()
    st.markdown("#### 4.1 推荐方案")
    colA, colB, colC = st.columns(3)
    with colA:
        st.markdown("**主推**")
        st.write(sec41.get("primary") or "（无）")
    with colB:
        st.markdown("**备选**")
        st.write(sec41.get("secondary") or "（无）")
    with colC:
        st.markdown("**不建议**")
        st.write(sec41.get("not_recommended") or "（无）")

    # 政策明细
    st.divider()
    st.markdown("#### 第三章：逐政策明细")
    for pol in policies:
        if not isinstance(pol, dict):
            continue
        x = pol.get("x")
        name = pol.get("policy_name") or f"政策{x}"

        with st.expander(f"政策 {x}：{name}", expanded=False):
            s1 = get_pol_section(pol, x, "1")
            s2 = get_pol_section(pol, x, "2")
            s3 = get_pol_section(pol, x, "3")
            s4 = get_pol_section(pol, x, "4")

            st.markdown("**3.x.1 政策内容**")
            if s1.get("policy_measures"):
                st.markdown("- 政策措施")
                st.write(s1.get("policy_measures"))
            if s1.get("parameters"):
                st.markdown("- 参数")
                st.write(s1.get("parameters"))

            st.markdown("**3.x.2 政策作用机制**")
            if s2.get("mechanism_chain"):
                st.markdown("- 作用链条")
                st.write(s2.get("mechanism_chain"))
            if s2.get("primary_levers"):
                st.markdown("- 主要作用杠杆")
                st.write(s2.get("primary_levers"))

            st.markdown("**3.x.3 适用场景与边界条件**")
            if s3.get("applicable_when"):
                st.markdown("- 适用场景")
                st.write(s3.get("applicable_when"))
            if s3.get("boundary_conditions"):
                st.markdown("- 边界条件")
                st.write(s3.get("boundary_conditions"))
            if s3.get("failure_modes"):
                st.markdown("- 失效模式")
                st.write(s3.get("failure_modes"))

            st.markdown("**3.x.4 政策对企业行为/产业行为的影响**")
            inv = s4.get("involution_index") if isinstance(s4.get("involution_index"), dict) else {}
            if inv:
                st.write(inv)

            beh = s4.get("behavior_impacts") if isinstance(s4.get("behavior_impacts"), dict) else {}
            if beh:
                beh_rows = []
                order = [
                    ("pricing", "定价"),
                    ("capacity", "产能"),
                    ("rnd", "研发"),
                    ("channels", "渠道"),
                    ("supply_chain_terms", "供应链账期"),
                    ("mna_exit", "并购退出"),
                ]
                for k, cn in order:
                    item = beh.get(k, {}) if isinstance(beh.get(k), dict) else {}
                    beh_rows.append(
                        {
                            "维度": cn,
                            "direction": item.get("direction"),
                            "text": item.get("text"),
                        }
                    )
                st.markdown("- 行为影响（方向/解释）")
                st.dataframe(beh_rows, use_container_width=True, hide_index=True)

            if s4.get("kpis"):
                st.markdown("- 关键 KPI")
                st.write(s4.get("kpis"))
            if s4.get("side_effects"):
                st.markdown("- 潜在副作用")
                st.write(s4.get("side_effects"))






