# feature_involution_measure_yearly.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Sequence

import streamlit as st


def _render_yearly_series_table(out: Dict[str, Any], metrics: Sequence[Dict[str, Any]]) -> None:
    series = out.get("series", [])
    if not isinstance(series, list) or not series:
        st.info("未返回 series 数据。")
        return

    company = out.get("company") or "未知公司"
    key2name = {m.get("key"): m.get("name") for m in metrics if isinstance(m, dict) and m.get("key")}

    # 权重信息
    weights: Dict[str, Any] = {}
    entropy_fusion = out.get("entropy_fusion", {})
    if isinstance(entropy_fusion, dict) and isinstance(entropy_fusion.get("weights"), dict):
        weights = entropy_fusion.get("weights", {}) or {}

    rows: List[Dict[str, Any]] = []
    text_blocks: List[Dict[str, Any]] = []

    for item in series:
        if not isinstance(item, dict):
            continue

        metrics_obj = item.get("metrics", {})
        if not isinstance(metrics_obj, dict):
            metrics_obj = {}

        period = item.get("period", "未知年度")
        idx = item.get("involution_index_0_1")

        rationale = item.get("rationale")
        notes = item.get("notes")

        if notes is None:
            notes_list: List[str] = []
        elif isinstance(notes, list):
            # 你原代码里用了 notes[1:]，这里保留该行为（如果确实需要跳过第一条）
            notes_list = [str(x) for x in notes[1:]]
        else:
            notes_list = [str(notes)]

        notes_text = "\n".join([f"- {x}" for x in notes_list]) if notes_list else ""

        row: Dict[str, Any] = {
            "公司": company,
            "年份": period,
            "融合计算指标": idx,
            "原因说明": str(rationale) if rationale is not None else "",
            "备注": notes_text,
        }
        for k, cn in key2name.items():
            if cn:
                row[str(cn)] = metrics_obj.get(k)

        rows.append(row)

        if rationale or notes_list:
            text_blocks.append({"period": period, "rationale": str(rationale or ""), "notes": notes_list})

    if weights:
        weight_row: Dict[str, Any] = {
            "公司": company,
            "年份": "熵权法权重",
            "融合计算指标": None,
        }
        for k, cn in key2name.items():
            if cn:
                weight_row[str(cn)] = weights.get(k)
        rows.append(weight_row)

    st.markdown("#### 年度序列")
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if text_blocks:
        st.markdown("#### 年度说明")
        for tb in text_blocks:
            with st.expander(f"{tb['period']}：文本说明", expanded=False):
                if tb.get("rationale"):
                    st.markdown("**原因说明**")
                    st.info(tb["rationale"])
                if tb.get("notes"):
                    st.markdown("**备注**")
                    st.markdown("\n".join([f"- {x}" for x in tb["notes"]]))


def render_involution_measure_yearly_tab(
    *,
    settings: Any,
    company_list: Sequence[str],
    metrics: Sequence[Dict[str, Any]],

    guard_feature_run_fn: Callable[..., bool],
    measure_yearly_fn: Callable[..., Dict[str, Any]],
    measure_yearly_no_rag_fn: Callable[..., Dict[str, Any]],
    json_bytes_fn: Callable[[Any], bytes],
    now_tag_fn: Callable[[], str],
    save_json_fn: Callable[..., str],
) -> None:
    """功能3：内卷测定（年度趋势）"""

    st.subheader("📈 内卷测定（年度趋势）")
    st.caption("按年份循环测度，输出年度测度结果与内卷趋势图。")

    store_dir_default = st.session_state.get(
        "global_store_dir",
        str(getattr(settings, "RAG_STORE_DIR", "rag_store"))
    )

    col_in, col_out = st.columns([1, 2], gap="large")

    # =========================
    # 左侧：输入区
    # =========================
    with col_in:
        m_selected = st.selectbox(
            "公司名（必填）",
            options=list(company_list) + ["其他"],
            index=0,
            key="m_company_select",
        )

        company_ok = True
        if m_selected == "其他":
            company_other = st.text_input(
                "请输入汽车企业名称",
                value="",
                placeholder="例如：赛力斯、哪吒汽车、阿维塔……",
                key="m_company_other",
            )
            company = company_other.strip()
            if not company:
                company_ok = False
                st.error("此项为必填项！")
        else:
            company = str(m_selected).strip()

        # 年份选择：selectbox（保证合法输入）
        year_now = datetime.now().year
        years = list(range(2014, year_now))  # 与你原逻辑一致：到 year_now-1

        c1, c2 = st.columns(2)
        with c1:
            start = st.selectbox("起始年份", years, index=years.index(2015) if 2015 in years else 0, key="m_start")
        with c2:
            end = st.selectbox("结束年份", years, index=years.index(2024) if 2024 in years else len(years) - 1, key="m_end")

        year_ok = True
        if start > end:
            year_ok = False
            st.error("起始年份不能大于结束年份。")

        enable_rag = st.checkbox("启用本地知识库（RAG）", value=True, key="m_enable_rag")

        # 兜底默认值，避免右侧调用时变量未定义
        rag_top_k_default = int(getattr(settings, "TOP_K", 10))
        rag_top_k: int = rag_top_k_default
        rag_store_dir: str = store_dir_default

        if enable_rag:
            rag_top_k = st.number_input(
                "RAG top_k",
                min_value=1, max_value=50,
                value=rag_top_k_default,
                step=1,
                key="m_topk",
            )
            rag_store_dir = st.text_input(
                "向量库目录（store_dir）",
                value=store_dir_default,
                key="m_store",
            )
            st.session_state["global_store_dir"] = rag_store_dir

        # 输出目录：建议始终提供（趋势图一般需要落盘生成）
        output_dir_default = str(getattr(settings, "OUTPUT_DIR", "output"))
        save_local = st.checkbox("保存输出到本地", value=True, key="m_save")

        output_plot_dir = st.text_input(
            "输出目录 (其他功能输出目录不会统一修改！）",
            value=output_dir_default,
            key="m_outdir",
        )

        run_btn = st.button(
            "开始测定",
            type="primary",
            use_container_width=True,
            key="m_run",
            disabled=(not company_ok) or (not year_ok),
        )

    # =========================
    # 右侧：输出区
    # =========================
    with col_out:
        if run_btn:
            if not guard_feature_run_fn(
                "内卷测定（年度趋势）",
                require_llm=True,
                require_rag_dir=bool(enable_rag),
                require_output_dir=True,
            ):
                pass
            else:
                with st.spinner("正在按年份循环测度..."):
                    try:
                        if enable_rag:
                            out = measure_yearly_fn(
                                company=company,
                                start=str(start),
                                end=str(end),
                                rag_store_dir=str(rag_store_dir),
                                rag_top_k=int(rag_top_k),
                                output_plot_dir=str(output_plot_dir),
                            )
                        else:
                            out = measure_yearly_no_rag_fn(
                                company=company,
                                start=str(start),
                                end=str(end),
                                output_plot_dir=str(output_plot_dir),
                            )

                        st.session_state["yearly_last_out"] = out
                        st.session_state["yearly_last_company"] = company
                    except Exception as e:
                        st.error("年度测定执行失败。")
                        st.write("错误信息：", str(e))
                        st.code(traceback.format_exc())
                        st.stop()

        out = st.session_state.get("yearly_last_out")
        if not out:
            st.info("请填写左侧参数并点击“开始测定”。")
            return

        company_for_name = st.session_state.get("yearly_last_company", "company")

        plot_path = out.get("plot_path")
        if plot_path and isinstance(plot_path, str) and os.path.exists(plot_path):
            st.markdown("#### 趋势图")
            st.image(plot_path, use_container_width=True)
            try:
                with open(plot_path, "rb") as f:
                    st.download_button(
                        "下载趋势图（PNG）",
                        data=f.read(),
                        file_name=os.path.basename(plot_path),
                        mime="image/png",
                        use_container_width=True,
                    )
            except Exception:
                pass
        else:
            st.info("未找到趋势图文件。")

        st.divider()
        _render_yearly_series_table(out, metrics=metrics)

        st.divider()
        with st.expander("查看完整 JSON 输出", expanded=False):
            st.json(out)

        cdl1, cdl2 = st.columns([1, 1])
        with cdl1:
            st.download_button(
                "下载 JSON",
                data=json_bytes_fn(out),
                file_name=f"measure_yearly_{company_for_name}_{now_tag_fn()}.json",
                mime="application/json",
                use_container_width=True,
            )

        with cdl2:
            if save_local:
                try:
                    saved_path = save_json_fn(
                        out,
                        out_dir=str(output_plot_dir),
                        prefix="measure_yearly",
                        tag=str(company_for_name),
                    )
                    st.success(f"已保存：{saved_path}")
                except Exception as e:
                    st.warning("保存失败（不影响展示）。")
                    st.write(str(e))

        st.divider()
        st.markdown("#### RAG 使用情况")
        st.json(out.get("rag", {}))
