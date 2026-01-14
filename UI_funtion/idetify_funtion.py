
# -*- coding: utf-8 -*-
from __future__ import annotations
import traceback
from typing import Any, Callable, Dict, Sequence

import streamlit as st

def render_involution_identify_tab(
    *,
    settings: Any,
    company_list: Sequence[str],

    # ---- 依赖注入：来自 app.py 的函数/工具 ----
    guard_feature_run_fn: Callable[..., bool],
    identify_fn: Callable[..., Dict[str, Any]],
    identify_no_rag_fn: Callable[..., Dict[str, Any]],
    safe_get_fn: Callable[..., Any],
    render_labels_block_fn: Callable[..., None],
    render_rag_hits_fn: Callable[..., None],
    json_bytes_fn: Callable[[Any], bytes],
    now_tag_fn: Callable[[], str],
    save_json_fn: Callable[..., str],
) -> None:
    """功能2：内卷标签识别（可选启用RAG，标签可视化，JSON展示/下载/可选保存）"""

    st.subheader("🏷️ 内卷标签识别")
    st.caption("支持启用/禁用本地知识库，对标签进行可视化展示。")

    store_dir_default = st.session_state.get(
        "global_store_dir",
        str(getattr(settings, "RAG_STORE_DIR", "rag_store"))
    )

    col_in, col_out = st.columns([1, 2], gap="large")

    # =========================
    # 左侧：输入区
    # =========================
    with col_in:
        # 公司名：下拉单选 + 其他自填
        id_selected = st.selectbox(
            "公司名（必填）",
            options=list(company_list) + ["其他"],
            index=0,
            key="id_company_select",
        )
        company_ok = True
        if id_selected == "其他":
            company_other = st.text_input(
                "请输入汽车企业名称",
                value="",
                placeholder="例如：赛力斯、哪吒汽车、阿维塔……",
                key="id_company_other",
            )
            company = company_other.strip()
            if not company:
                company_ok = False
                st.error("此项为必填项！")
        else:
            company = str(id_selected).strip()

        default_query = f"请对{company}汽车企业，给出至少3个标签，并判断是否存在内卷式竞争（如果证据不足请说明）。"

        # 是否启用 RAG
        enable_rag = st.checkbox("启用本地知识库（可选）", value=True, key="i_enable_rag")
        if enable_rag:
            top_k_default = int(getattr(settings, "TOP_K", 10))
            top_k = st.number_input(
                "证据检索条数",min_value=1,max_value=25,value=top_k_default,
                step=1,key="id_topk",)
            store_dir = st.text_input(
                "本地知识向量库地址",value=store_dir_default,key="id_store",)
            st.session_state["global_store_dir"] = store_dir

        # 保存输出到本地
        save_local = st.checkbox("自动保存输出到本地（可选）", value=True, key="id_save")
        output_dir_default = str(getattr(settings, "OUTPUT_DIR", "output"))
        if save_local:
            output_dir = st.text_input(
                "输出目录 (其他功能输出目录不会统一修改！）",
                value=output_dir_default,
                key="id_outdir",
            )
        # 运行按钮：公司名为空时直接禁用，避免点击后才报错
        run_btn = st.button(
            "开始识别",type="primary",use_container_width=True,
            key="id_run",disabled=not company_ok)
    # =========================
    # 右侧：输出区
    # =========================
    with col_out:
        if run_btn:
            if not guard_feature_run_fn(
                "内卷标签识别",
                require_llm=True,require_rag_dir=bool(enable_rag),require_output_dir=bool(save_local),
            ):
                pass
            else:
                with st.spinner("正在识别..."):
                    try:
                        if enable_rag:
                            out = identify_fn(
                                default_query,
                                top_k=int(top_k),
                                store_dir=str(store_dir),
                            )
                        else:
                            out = identify_no_rag_fn(default_query)

                        st.session_state["identify_last_out"] = out
                        st.session_state["identify_last_company"] = company
                    except Exception as e:
                        st.error("识别执行失败。")
                        st.write("错误信息：", str(e))
                        st.code(traceback.format_exc())
                        st.stop()

        out = st.session_state.get("identify_last_out")
        if not out:
            st.info("请填写左侧参数并点击“开始识别”。")
            return

        company_for_name = st.session_state.get("identify_last_company", "company")
        has_invo = safe_get_fn(out, ["overall", "has_involution"], default=None)
        conf = safe_get_fn(out, ["overall", "confidence"], default=None)

        st.markdown("#### 结论摘要")
        s1, s2 = st.columns(2)
        with s1:
            st.metric("是否存在内卷", value=str(has_invo) if has_invo is not None else "N/A")
        with s2:
            st.metric("整体置信度", value=str(conf) if conf is not None else "N/A")

        st.divider()
        render_labels_block_fn(out.get("labels"))

        st.divider()
        st.markdown("#### 结构化输出（JSON）")
        st.json(out)

        cdl1, cdl2 = st.columns([1, 1])
        with cdl1:
            st.download_button(
                "下载 JSON",
                data=json_bytes_fn(out),
                file_name=f"identify_{company_for_name}_{now_tag_fn()}.json",
                mime="application/json",
                use_container_width=True,
            )

        with cdl2:
            if save_local:
                try:
                    saved_path = save_json_fn(out, out_dir=str(output_dir), prefix="identify", tag=str(company_for_name))
                    st.success(f"已保存：{saved_path}")
                except Exception as e:
                    st.warning("保存失败（不影响展示）。")
                    st.write(str(e))

        st.divider()
        render_rag_hits_fn(safe_get_fn(out, ["rag", "hits"], default=[]))
