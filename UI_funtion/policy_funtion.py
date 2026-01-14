
# -*- coding: utf-8 -*-
from __future__ import annotations

import os

from typing import Any, Callable, Dict, List

import streamlit as st

from utils.settings import MAX_RETRY


def render_policy_simulation_tab(
    *,
    settings: Any,
    # ---- 依赖注入：来自 app.py 的函数/工具 ----
    guard_feature_run_fn: Callable[..., bool],
    split_policies_fn: Callable[[str], List[str]],
    now_tag_fn: Callable[[], str],
    safe_get_fn: Callable[..., Any],

    simulate_policy_fn: Callable[..., Dict[str, Any]],
    simulate_policy_no_rag_fn: Callable[..., Dict[str, Any]],

    render_policy_outputs_fn: Callable[[Dict[str, Any]], None],
    render_rag_hits_fn: Callable[[Any], None],
    json_bytes_fn: Callable[[Any], bytes],
    export_docx_bytes_fn: Callable[..., bytes],
    save_json_fn: Callable[..., str],
) -> None:
    """功能4：政策仿真干预（失败最多重试 max_retry 次）"""

    st.subheader("🧪政策仿真干预")
    st.caption("输入 1 个或多个政策设定，生成标准JSON报告，并支持导出Word及可视化汇总。")

    store_dir_default = st.session_state.get(
        "global_store_dir",
        str(getattr(settings, "RAG_STORE_DIR", "rag_store"))
    )

    col_in, col_out = st.columns([1, 2], gap="large")

    # =========================
    # 左侧：输入区
    # =========================
    with col_in:
        industry_scope = st.text_input(
            "行业范围（industry_scope）",
            value="中国新能源汽车行业（含BEV/PHEV）",
            key="p_scope",
        )
        horizon = st.number_input(
            "仿真跨度（月）",
            min_value=6, max_value=120,
            value=24, step=6,
            key="p_horizon",
        )
        enable_rag = st.checkbox("启用本地知识库（RAG）", value=True, key="p_enable_rag")

        if enable_rag:
            top_k_default = int(getattr(settings, "TOP_K", 12))
            top_k = st.number_input("RAG top_k",
                min_value=1, max_value=50,value=top_k_default, step=1,key="p_topk",)
            store_dir = st.text_input(
                "向量库目录（store_dir）",value=store_dir_default,key="p_store",)
            st.session_state["global_store_dir"] = store_dir

        st.markdown("#### 政策输入")
        policy_raw = st.text_area(
            "支持：空行分隔多政策；或用“- ”开头的多行。",
            value=(
                "对低于成本的恶性降价开展联合执法，要求价格调整前进行成本与毛利披露，并对连续多轮大幅降价设定审查触发条件。\n\n"
                "建立产能与项目备案的预警阈值机制：当行业产能利用率连续低于某阈值时，暂停新增产能审批，并引导存量整合。"
            ),
            height=220,
            key="p_text",
        )

        save_local = st.checkbox("保存输出到本地", value=True, key="p_save")
        if save_local:
            output_dir_default = str(getattr(settings, "OUTPUT_DIR", "output"))
            output_policy_dir = st.text_input("输出目录 (其他功能输出目录不会统一修改！）", value=output_dir_default, disabled=not save_local, key="p_outdir")

        run_btn = st.button("开始仿真", type="primary", use_container_width=True, key="p_run")

    # =========================
    # 右侧：输出区
    # =========================
    with col_out:
        if run_btn:
            if not guard_feature_run_fn(
                "政策仿真干预",require_llm=True,require_rag_dir=bool(enable_rag),
                require_output_dir=bool(save_local),):
                pass
            else:
                policies = split_policies_fn(policy_raw)
                if not policies:
                    st.warning("请按照规定格式输入政策内容！")
                else:
                    for i in range(1, MAX_RETRY + 1):
                        with st.spinner(
                                f"正在进行政策仿真与报告生成...（第 {i} 次）"):
                            try:
                                if enable_rag:
                                    out = simulate_policy_fn(
                                        policies,
                                        industry_scope=str(industry_scope),
                                        time_horizon_months=int(horizon),
                                        top_k=int(top_k),
                                        store_dir=str(store_dir),
                                    )
                                else:
                                    out = simulate_policy_no_rag_fn(
                                        policies,
                                        industry_scope=str(industry_scope),
                                        time_horizon_months=int(horizon),
                                    )

                                st.session_state["policy_last_out"] = out
                                st.session_state["policy_last_tag"] = now_tag_fn()
                            except Exception as e:
                                st.error("政策仿真执行重试中。")
                        # 成功：直接保存并退出循环
                        if out:
                            st.toast(f"政策仿真成功")
                            st.session_state["policy_last_out"] = out
                            st.session_state["policy_last_tag"] = now_tag_fn()
                            break

                        # 失败：未到上限则提示并继续；到上限则落库错误信息并提示失败
                        if i < MAX_RETRY + 1:
                            st.warning(f"第 {i} 次政策仿真失败，正在自动重试...")
                            continue

                        st.session_state["policy_last_out"] = None
                        st.session_state["policy_last_err"] = {
                            "message": "政策仿真返回结构不完整（policies 为空或格式不正确）。",
                        }
                        st.error(
                            f"政策仿真连续 {MAX_RETRY} 次失败，请检查模型配置/网络/政策输入格式后重试。")

        out = st.session_state.get("policy_last_out")
        if not out:
            st.info("请在左侧输入政策设定并点击“开始仿真”。")
        else:
            # 主要可视化展示
            render_policy_outputs_fn(out)
            st.divider()
            st.markdown("#### 导出")
            tag = st.session_state.get("policy_last_tag", now_tag_fn())

            dl1, dl2, dl3 = st.columns([1, 1, 1])
            with dl1:
                st.download_button(
                    "下载 JSON",
                    data=json_bytes_fn(out),
                    file_name=f"policy_sim_{tag}.json",
                    mime="application/json",
                    use_container_width=True,
                )
            with dl2:
                # Word文本输出
                try:
                    docx_name = f"policy_sim_report_{tag}.docx"
                    if save_local:
                        docx_bytes = export_docx_bytes_fn(out,
                                                        output_dir=output_policy_dir,
                                                        filename=docx_name)
                    else:
                        # no local save: write to temp and read
                        tmp_dir = os.path.join(".", "_tmp")
                        docx_bytes = export_docx_bytes_fn(out, output_dir=tmp_dir,
                                                        filename=docx_name)
                    st.download_button(
                        "下载 Word（DOCX）",
                        data=docx_bytes,
                        file_name=docx_name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.warning("Word 导出失败。")
                    st.write(str(e))
            with dl3:
                if save_local:
                    try:
                        saved_path = save_json_fn(out,
                                                  out_dir=output_policy_dir,
                                                  prefix="policy_sim",
                                                  tag="NEV")
                        st.success(f"JSON 已保存：{saved_path}")
                    except Exception as e:
                        st.warning("JSON 保存失败（不影响下载）。")
                        st.write(str(e))

            st.divider()
            with st.expander("查看完整 JSON 输出", expanded=False):
                st.json(out)

            st.divider()
            render_rag_hits_fn(safe_get_fn(out, ["rag", "hits"], default=[]))
