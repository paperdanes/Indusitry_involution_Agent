# -*- coding: utf-8 -*-
"""\
  1) 本地知识库管理（RAG 库管理）
  2) 内卷标签识别
  3) 内卷测定（年度测度/趋势）
  4) 政策仿真干预（输出 JSON + 导出 Word + 可视化）
streamlit run app.py
"""
from __future__ import annotations
from UI_funtion.UI_setting_funtion import store_status, \
    remove_doc_from_store_by_id, add_files_into_store, clear_store_files, \
    list_docs, render_labels_block, render_rag_hits, export_docx_bytes, \
    render_policy_outputs, split_policies
from UI_funtion.UI_sidebar_funtion import render_llm_settings_sidebar
from UI_funtion.idetify_funtion import render_involution_identify_tab
from UI_funtion.kb_manager_funtion import render_kb_management_tab
from UI_funtion.measure_yearly_funtion import \
    render_involution_measure_yearly_tab
from UI_funtion.policy_funtion import render_policy_simulation_tab
from utils.setting_utils import guard_feature_run
import traceback
import streamlit as st
from utils.prompts import METRICS
from utils.setting_utils import init_llm_cfg_once, apply_llm_active_to_settings
from utils.settings import *
from utils.utils import ensure_dir, is_subpath, now_tag, safe_get, json_bytes

# -----------------------------
# 页面定义
# -----------------------------
st.set_page_config(
    page_title="新能源汽车行业内卷识别系统",
    layout="wide",
    initial_sidebar_state="collapsed",
)
# -----------------------------
# 加载函数文件
# -----------------------------
@st.cache_resource(show_spinner=False)
def _load_project_modules():
    from utils import settings
    from funtion.identify import identify, identify_from_none
    from funtion.measure_yearly import measure_company_yearly,measure_company_yearly_from_none
    from utils.json_utils import save_json
    from rag.rag import FaissRAG
    from funtion.policy import simulate_policy, simulate_policy_from_none
    from utils.json_to_word import json_report_to_docx
    return (
        settings,
        identify,
        identify_from_none,
        measure_company_yearly,
        measure_company_yearly_from_none,
        save_json,
        FaissRAG,
        simulate_policy,
        simulate_policy_from_none,
        json_report_to_docx,
    )

def _require_modules():
    try:
        return _load_project_modules()
    except Exception as e:
        st.error("项目依赖导入失败：请确认本文件与项目代码在同一目录，且依赖模块可被正确 import。")
        st.write("错误信息：", str(e))
        st.code(traceback.format_exc())
        st.stop()
(
    settings,
    identify_fn,
    identify_no_rag_fn,
    measure_yearly_fn,
    measure_yearly_no_rag_fn,
    save_json_fn,
    FaissRAG,
    simulate_policy_fn,
    simulate_policy_no_rag_fn,
    json_report_to_docx_fn,
) = _require_modules()

def _rerun() -> None:
    # 代码重运行，考虑 Streamlit 版本兼容
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass

# 初始化并把“当前生效配置”写回 settings（使全局一致生效）
init_llm_cfg_once()
apply_llm_active_to_settings(st.session_state["_llm_active"])

## 侧边栏设置
render_llm_settings_sidebar(
    settings=settings,
    base_url_presets=BASE_URL_PRESETS,
    model_presets=MODEL_PRESETS,
    embed_model_presets=EMBED_MODEL_PRESETS,
    init_cfg_once=init_llm_cfg_once,
    apply_active_to_settings=apply_llm_active_to_settings,
    rerun=_rerun,
)

# -----------------------------
# UI功能选择界面
# -----------------------------
st.markdown(
    """
    <div style="text-align:center; margin-top: 6px;">
        <h2 style="margin-bottom: 6px;">新能源汽车行业内卷识别与反内卷政策辅助系统</h2>
    </div>
    """,unsafe_allow_html=True)
tabs = st.tabs(["📚 本地知识库管理", "🏷️ 内卷标签识别", "📈 内卷测定", "🧪 政策仿真干预"])

# =====================================
# 功能 1: 本地知识库管理
# =====================================
with tabs[0]:
    render_kb_management_tab(
        settings=settings,
        store_status_fn=store_status,
        list_docs_fn=list_docs,
        guard_feature_run_fn=guard_feature_run,
        remove_doc_by_id_fn=remove_doc_from_store_by_id,
        is_subpath_fn=is_subpath,
        rerun_fn=_rerun,
        ensure_dir_fn=ensure_dir,
        now_tag_fn=now_tag,
        add_files_into_store_fn=add_files_into_store,
        clear_store_files_fn=clear_store_files,
    )

# =====================================
# 功能 2: 内卷标签识别
# =====================================
with tabs[1]:
    render_involution_identify_tab(
        settings=settings,
        company_list=SCOMPANY_LIST,
        guard_feature_run_fn=guard_feature_run,
        identify_fn=identify_fn,
        identify_no_rag_fn=identify_no_rag_fn,
        safe_get_fn=safe_get,
        render_labels_block_fn=render_labels_block,
        render_rag_hits_fn=render_rag_hits,
        json_bytes_fn=json_bytes,
        now_tag_fn=now_tag,
        save_json_fn=save_json_fn,
    )

# =====================================
# 功能 3: 内卷测定（年度趋势）
# =====================================
with tabs[2]:
    render_involution_measure_yearly_tab(
        settings=settings,
        company_list=SCOMPANY_LIST,
        metrics=METRICS,
        guard_feature_run_fn=guard_feature_run,
        measure_yearly_fn=measure_yearly_fn,
        measure_yearly_no_rag_fn=measure_yearly_no_rag_fn,
        json_bytes_fn=json_bytes,
        now_tag_fn=now_tag,
        save_json_fn=save_json_fn,
    )
# =====================================
# 功能 4: 政策仿真干预
# =====================================
with tabs[3]:
    render_policy_simulation_tab(
        settings=settings,
        guard_feature_run_fn=guard_feature_run,
        split_policies_fn=split_policies,
        now_tag_fn=now_tag,
        safe_get_fn=safe_get,
        simulate_policy_fn=simulate_policy_fn,
        simulate_policy_no_rag_fn=simulate_policy_no_rag_fn,
        render_policy_outputs_fn=render_policy_outputs,
        render_rag_hits_fn=render_rag_hits,
        json_bytes_fn=json_bytes,
        export_docx_bytes_fn=export_docx_bytes,
        save_json_fn=save_json_fn,
    )
