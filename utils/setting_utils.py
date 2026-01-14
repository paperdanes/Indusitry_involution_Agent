from __future__ import annotations

import streamlit as st
from utils import settings
from typing import List

def llm_defaults_from_settings() -> dict:
    return {k: getattr(settings, k, None) for k in settings.LLM_KEYS}
def init_llm_cfg_once() -> None:
    # 仅在会话首次初始化默认值（默认来自 settings.py）
    if "_llm_defaults" not in st.session_state:
        st.session_state["_llm_defaults"] = llm_defaults_from_settings()
    if "_llm_active" not in st.session_state:
        st.session_state["_llm_active"] = dict(st.session_state["_llm_defaults"])

    # 用 active 值初始化 UI widget 值
    a = st.session_state["_llm_active"]
    st.session_state.setdefault("ui_api_key", str(a.get("DASHSCOPE_API_KEY") or ""))

    # BASE_URL：预设 + 自定义
    cur_base = str(a.get("BASE_URL") or "")
    preset_name = next((name for name, url in settings.BASE_URL_PRESETS.items() if url == cur_base), "自定义")
    st.session_state.setdefault("ui_base_preset", preset_name)
    st.session_state.setdefault("ui_base_custom", "" if preset_name != "自定义" else cur_base)

    # MODEL：预设 + 自定义
    cur_model = str(a.get("MODEL") or "")
    model_preset = cur_model if cur_model in settings.MODEL_PRESETS else "__CUSTOM__"
    st.session_state.setdefault("ui_model_preset", model_preset)
    st.session_state.setdefault("ui_model_custom", "" if model_preset != "__CUSTOM__" else cur_model)

    st.session_state.setdefault("ui_temperature", float(a.get("TEMPERATURE", 0.2)))
    st.session_state.setdefault("ui_top_p", float(a.get("TOP_P", 0.9)))
    st.session_state.setdefault("ui_max_tokens", int(a.get("MAX_TOKENS", 4096)))

    if "_rag_defaults" not in st.session_state:
        st.session_state["_rag_defaults"] = llm_defaults_from_settings()
    if "_rag_active" not in st.session_state:
        st.session_state["_rag_active"] = dict(st.session_state["_rag_defaults"])
    a = st.session_state["_rag_active"]

    # EMBED_MODEL：预设 + 自定义
    cur_em = str(a.get("EMBED_MODEL") or "")
    em_preset = cur_em if cur_em in settings.EMBED_MODEL_PRESETS else "__CUSTOM__"
    st.session_state.setdefault("ui_embed_model_preset", em_preset)
    st.session_state.setdefault("ui_embed_model_custom",
                                "" if em_preset != "__CUSTOM__" else cur_em)

    st.session_state.setdefault("ui_embed_dim",int(a.get("EMBED_DIM", 1024) or 1024))
    st.session_state.setdefault("ui_embed_batch",int(a.get("EMBED_BATCH", 10) or 10))
    st.session_state.setdefault("ui_rag_store_dir",str(a.get("RAG_STORE_DIR") or ""))
    st.session_state.setdefault("ui_top_k", int(a.get("TOP_K", 10) or 10))
    st.session_state.setdefault("ui_output_dir", str(a.get("OUTPUT_DIR") or ""))



def apply_llm_active_to_settings(active: dict) -> None:
    # 统一类型，避免 slider/number_input 返回类型不一致
    settings.DASHSCOPE_API_KEY = str(active.get("DASHSCOPE_API_KEY") or "")
    settings.BASE_URL = str(active.get("BASE_URL") or "")
    settings.MODEL = str(active.get("MODEL") or "")
    settings.TEMPERATURE = float(active.get("TEMPERATURE", 0.2))
    settings.TOP_P = float(active.get("TOP_P", 0.9))
    settings.MAX_TOKENS = int(active.get("MAX_TOKENS", 4096))
    settings.EMBED_MODEL = str(active.get("EMBED_MODEL") or "")
    settings.EMBED_DIM = int(active.get("EMBED_DIM", 1024))
    settings.EMBED_BATCH = int(active.get("EMBED_BATCH", 10))
    settings.RAG_STORE_DIR = str(active.get("RAG_STORE_DIR") or "")
    settings.TOP_K = int(active.get("TOP_K", 10))
    settings.OUTPUT_DIR = str(active.get("OUTPUT_DIR") or "")




# -----------------------------
# 运行前参数校验函数
# -----------------------------
def sidebar_missing_items(
    *,
    require_llm: bool = False,
    require_embed: bool = False,
    require_rag_dir: bool = False,
    require_output_dir: bool = False,
) -> List[str]:
    """
    返回缺失/不合规项列表（用于提示用户到左侧边栏设置）。
    - require_llm：校验 API_KEY / BASE_URL / MODEL
    - require_embed：校验 EMBED_MODEL / EMBED_DIM / EMBED_BATCH
    - require_rag_dir：校验 RAG_STORE_DIR
    - require_output_dir：校验 OUTPUT_DIR
    """
    a = st.session_state.get("_llm_active", {}) or {}
    missing: List[str] = []

    def _nonempty(k: str) -> bool:
        return bool(str(a.get(k) or "").strip())

    if require_llm:
        if not _nonempty("DASHSCOPE_API_KEY"):
            missing.append("模型_API_KEY（DASHSCOPE_API_KEY）")
        base_url = str(a.get("BASE_URL") or "").strip()
        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            missing.append("URL地址（BASE_URL，应以 http(s) 开头）")
        if not _nonempty("MODEL"):
            missing.append("模型（MODEL）")

    if require_embed:
        if not _nonempty("EMBED_MODEL"):
            missing.append("向量化模型（EMBED_MODEL）")
        try:
            dim = int(a.get("EMBED_DIM", 0))
        except Exception:
            dim = 0
        if dim <= 0:
            missing.append("向量维度（EMBED_DIM，需为正整数）")
        try:
            batch = int(a.get("EMBED_BATCH", 0))
        except Exception:
            batch = 0
        if not (1 <= batch <= 10):
            missing.append("向量化批大小（EMBED_BATCH，建议 1~10）")
    if require_rag_dir:
        if not _nonempty("RAG_STORE_DIR"):
            missing.append("本地知识向量库目录（RAG_STORE_DIR）")
    if require_output_dir:
        if not _nonempty("OUTPUT_DIR"):
            missing.append("数据输出地址（OUTPUT_DIR）")
    return missing

def guard_feature_run(
    feature_name: str,
    *,
    require_llm: bool = False,
    require_embed: bool = False,
    require_rag_dir: bool = False,
    require_output_dir: bool = False,
) -> bool:
    """
    功能运行前简单校验：若缺失必要参数，提示用户到左侧边栏设置并“应用设置”。
    返回 True 表示可继续运行；False 表示不应运行本次操作。
    """
    missing = sidebar_missing_items(
        require_llm=require_llm,
        require_embed=require_embed,
        require_rag_dir=require_rag_dir,
        require_output_dir=require_output_dir,
    )
    if missing:
        st.warning(
            f"【{feature_name}】运行校验未通过：请先在左侧边栏完成必要参数设置!”。\n\n"
            + "缺失/不合规项：\n- " + "\n- ".join(missing)
        )
        try:
            st.toast(f"{feature_name}：请先在左侧边栏完成参数设置")
        except Exception:
            pass
        return False
    return True
