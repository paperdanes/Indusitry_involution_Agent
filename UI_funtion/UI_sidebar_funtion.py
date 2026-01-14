from __future__ import annotations

import streamlit as st
from typing import Any, Callable, Dict, Mapping, Sequence,List

### 侧边栏设置
def render_llm_settings_sidebar(
    *,
    settings: Any,
    base_url_presets: Mapping[str, str],
    model_presets: Sequence[str],
    embed_model_presets: Sequence[str],
    init_cfg_once: Callable[[], None],
    apply_active_to_settings: Callable[[Dict[str, Any]], None],
    rerun: Callable[[], None],
) -> Dict[str, Any]:
    """
    渲染 Sidebar：LLM/Embedding/RAG/输出目录设置 + 应用/恢复默认 + 当前生效参数展示
    """
    def _toast(msg: str) -> None:
        try:
            st.toast(msg)
        except Exception:
            pass

    # 同步全局 store_dir（用 global_store_dir 作为默认库目录）
    if "global_store_dir" not in st.session_state and getattr(settings, "RAG_STORE_DIR", None):
        st.session_state["global_store_dir"] = str(settings.RAG_STORE_DIR)

    with st.sidebar:
        st.markdown("### LLM模型设置")
        st.text_input("模型_API_KEY", key="ui_api_key", type="password")

        st.selectbox("URL地址预设", options=list(base_url_presets.keys()), key="ui_base_preset")
        if st.session_state.get("ui_base_preset") == "自定义":
            st.text_input("自定义 BASE_URL", key="ui_base_custom")

        st.selectbox("模型预设", options=list(model_presets) + ["__CUSTOM__"], key="ui_model_preset")
        if st.session_state.get("ui_model_preset") == "__CUSTOM__":
            st.text_input("自定义 MODEL", key="ui_model_custom")

        st.slider("TEMPERATURE", min_value=0.0, max_value=2.0, step=0.05, key="ui_temperature")
        st.slider("TOP_P", min_value=0.0, max_value=1.0, step=0.05, key="ui_top_p")
        st.number_input("MAX_TOKENS", min_value=256, max_value=32768, step=256, key="ui_max_tokens")

        st.markdown("### 向量化设置")
        st.selectbox("向量化模型预设", options=list(embed_model_presets), key="ui_embed_model_preset")
        if st.session_state.get("ui_embed_model_preset") == "__CUSTOM__":
            st.text_input("自定义 EMBED_MODEL", key="ui_embed_model_custom")

        st.number_input("向量维度", min_value=64, max_value=4096, step=64, key="ui_embed_dim")
        st.number_input("向量化批大小（受模型限制）", min_value=1, max_value=10, step=1, key="ui_embed_batch")

        st.markdown("### RAG / 输出目录")
        st.text_input("本地知识向量库（默认C盘！切记！必须为英文目录）", key="ui_rag_store_dir")
        st.number_input("证据检索条数", min_value=1, max_value=50, step=1, key="ui_top_k")
        st.text_input("数据输出地址（默认C盘！输出目录）", key="ui_output_dir")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("应用设置", type="primary", use_container_width=True):
                base_url = (
                    base_url_presets.get(st.session_state.get("ui_base_preset"), "")
                    if st.session_state.get("ui_base_preset") != "自定义"
                    else str(st.session_state.get("ui_base_custom") or "").strip()
                )
                model = (
                    str(st.session_state.get("ui_model_preset") or "")
                    if st.session_state.get("ui_model_preset") != "__CUSTOM__"
                    else str(st.session_state.get("ui_model_custom") or "").strip()
                )
                # 这里修正：若选择了预设，就直接用预设值，不要强行写死 text-embedding-v4
                embed_model = (
                    str(st.session_state.get("ui_embed_model_preset") or "")
                    if st.session_state.get("ui_embed_model_preset") != "__CUSTOM__"
                    else str(st.session_state.get("ui_embed_model_custom") or "").strip()
                )

                new_active = {
                    "DASHSCOPE_API_KEY": str(st.session_state.get("ui_api_key") or "").strip(),
                    "BASE_URL": str(base_url).strip(),
                    "MODEL": str(model).strip(),
                    "TEMPERATURE": float(st.session_state.get("ui_temperature", 0.2)),
                    "TOP_P": float(st.session_state.get("ui_top_p", 0.9)),
                    "MAX_TOKENS": int(st.session_state.get("ui_max_tokens", 4096)),
                    "EMBED_MODEL": str(embed_model).strip(),
                    "EMBED_DIM": int(st.session_state.get("ui_embed_dim", 1024)),
                    "EMBED_BATCH": int(st.session_state.get("ui_embed_batch", 10)),
                    "RAG_STORE_DIR": str(st.session_state.get("ui_rag_store_dir") or "").strip(),
                    "TOP_K": int(st.session_state.get("ui_top_k", 10)),
                    "OUTPUT_DIR": str(st.session_state.get("ui_output_dir") or "").strip(),
                }

                # 简单校验
                if not new_active["DASHSCOPE_API_KEY"]:
                    st.error("DASHSCOPE_API_KEY 不能为空。")
                elif not (new_active["BASE_URL"].startswith("http://") or new_active["BASE_URL"].startswith("https://")):
                    st.error("BASE_URL 需要是 http(s) 开头的地址。")
                elif not new_active["MODEL"]:
                    st.error("MODEL 不能为空。")
                elif not new_active["EMBED_MODEL"]:
                    st.error("EMBED_MODEL 不能为空。")
                elif new_active["EMBED_DIM"] <= 0:
                    st.error("EMBED_DIM 必须为正整数。")
                elif not (1 <= new_active["EMBED_BATCH"] <= 10):
                    st.error("EMBED_BATCH 建议为 1~10（避免 embedding 接口批量限制）。")
                elif not new_active["RAG_STORE_DIR"]:
                    st.error("RAG_STORE_DIR 不能为空。")
                elif not new_active["OUTPUT_DIR"]:
                    st.error("OUTPUT_DIR 不能为空。")
                else:
                    st.session_state["_llm_active"] = new_active
                    apply_active_to_settings(new_active)

                    # 同步现有页面里使用的全局 store_dir
                    st.session_state["global_store_dir"] = str(getattr(settings, "RAG_STORE_DIR", ""))

                    st.success("设置成功：LLM/Embedding/RAG参数已应用（全局生效）")
                    _toast("设置成功：LLM/Embedding/RAG参数已应用（全局生效）")
                    rerun()

        with c2:
            if st.button("恢复默认", use_container_width=True):
                # 确保 defaults 存在
                init_cfg_once()
                st.session_state["_llm_active"] = dict(st.session_state.get("_llm_defaults", {}))

                # 清理 UI 控件值，让 init_cfg_once 重新回填默认
                for k in [
                    "ui_api_key", "ui_base_preset", "ui_base_custom",
                    "ui_model_preset", "ui_model_custom",
                    "ui_temperature", "ui_top_p", "ui_max_tokens",
                    "ui_embed_model_preset", "ui_embed_model_custom",
                    "ui_embed_dim", "ui_embed_batch",
                    "ui_rag_store_dir", "ui_top_k", "ui_output_dir",
                ]:
                    st.session_state.pop(k, None)

                init_cfg_once()
                apply_active_to_settings(st.session_state["_llm_active"])
                st.session_state["global_store_dir"] = str(getattr(settings, "RAG_STORE_DIR", ""))

                st.success("已恢复默认参数")
                _toast("已恢复默认设置。")
                rerun()

        with st.expander("当前生效参数", expanded=False):
            a = st.session_state.get("_llm_active", {})
            show = dict(a)
            if show.get("DASHSCOPE_API_KEY"):
                show["DASHSCOPE_API_KEY"] = "***"
            st.json(show)

    return st.session_state.get("_llm_active", {})
