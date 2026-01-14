# feature_kb_manager.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple

import streamlit as st


def render_kb_management_tab(
    *,
    settings: Any,
    # ---- 依赖注入：避免循环 import，把 app.py 里已有函数传进来 ----
    store_status_fn: Callable[..., Dict[str, Any]],
    list_docs_fn: Callable[..., List[Dict[str, Any]]],
    guard_feature_run_fn: Callable[..., bool],
    remove_doc_by_id_fn: Callable[..., bool],
    is_subpath_fn: Callable[..., bool],
    rerun_fn: Callable[[], None],
    ensure_dir_fn: Callable[[str], None],
    now_tag_fn: Callable[[], str],
    add_files_into_store_fn: Callable[..., Any],
    clear_store_files_fn: Callable[..., int],
) -> None:
    """功能1：本地知识库管理（上传入库 / 删除 / 清空 / 状态展示）。"""

    st.subheader("📚 本地知识库管理")
    st.caption("支持：文件切片向量化入库；文件删除；清空库。")

    default_store_dir = str(getattr(settings, "RAG_STORE_DIR", "rag_store"))
    if "global_store_dir" not in st.session_state:
        st.session_state["global_store_dir"] = default_store_dir

    col_l, col_r = st.columns([1, 2], gap="large")

    # -----------------------------
    # 左侧：库目录与上传/清空配置
    # -----------------------------
    with col_l:
        st.markdown("#### 目标库设置")
        store_dir = st.text_input(
            "本地知识库目录（全英文地址）",
            value=st.session_state["global_store_dir"],
            key="kb_store_dir",
        )
        st.session_state["global_store_dir"] = store_dir

        uploaded = st.file_uploader(
            "选择上传文件",
            accept_multiple_files=True,
        )
        keep_original_name = st.checkbox("保留原文件名（重名自动加后缀）", value=True, key="kb_keep_name")

        add_btn = st.button("上传并入库", type="primary", use_container_width=True, key="kb_add_btn")

        st.markdown("#### 上传入库")
        upload_dir = st.text_input(
            "上传文件落盘目录(文件删除操作需要，请勿随意更改）",
            value=os.path.join(store_dir, "data", "uploads"),
            key="kb_upload_dir",
        )

        st.divider()
        st.markdown("#### 清空操作")
        confirm_clear = st.checkbox(
            "我确认要清空整个向量库（会删除index/chunks/manifest所有文件）",
            value=False,
            key="kb_confirm_clear",
        )
        clear_btn = st.button(
            "清空向量库",
            type="secondary",
            use_container_width=True,
            disabled=not confirm_clear,
            key="kb_clear_btn",
        )

    # -----------------------------
    # 右侧：库状态/文档列表/删除/执行操作
    # -----------------------------
    with col_r:
        # 当前向量库状态
        try:
            status = store_status_fn(store_dir=st.session_state["global_store_dir"])
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("知识库是否为空", str(status.get("empty")))
            c2.metric("向量长度", str(status.get("dim")))
            c3.metric("切片数量", str(status.get("ntotal")))
            c4.metric("文件数", str(status.get("docs")))

            with st.expander("查看库状态详情", expanded=False):
                st.json(status)
        except Exception as e:
            st.error("读取库状态失败。")
            st.write(str(e))
            st.code(traceback.format_exc())
            st.stop()

        # 向量库文件列表
        docs = list_docs_fn(store_dir=st.session_state["global_store_dir"])
        if docs:
            st.markdown("#### 已入库文档列表")
            st.dataframe(docs, use_container_width=True, hide_index=True)

            options: List[Tuple[str, str]] = []
            for d in docs:
                did = str(d.get("doc_id", ""))
                src = d.get("source_path", "")
                label = f"{did} | {src}"
                options.append((label, did))

            labels = [x[0] for x in options]
            label_to_id = {x[0]: x[1] for x in options}

            st.markdown("#### 删除库文件")
            sel = st.selectbox("选择要删除的文档", options=labels, key="kb_del_select")
            also_delete_file = st.checkbox(
                "同时删除源文件（仅当文件位于 store_dir 子目录内才会删除，防误删）",
                value=False,
                key="kb_also_del_file",
            )
            del_btn = st.button("删除选中文档", use_container_width=True, key="kb_del_btn")

            if del_btn:
                if not guard_feature_run_fn("本地知识库管理-删除", require_rag_dir=True):
                    pass
                else:
                    doc_id = label_to_id.get(sel, "")
                    src_path: Optional[str] = None
                    for d in docs:
                        if str(d.get("doc_id")) == str(doc_id):
                            src_path = str(d.get("source_path")) if d.get("source_path") is not None else None
                            break

                    with st.spinner("正在删除..."):
                        try:
                            ok = remove_doc_by_id_fn(st.session_state["global_store_dir"], doc_id=doc_id)
                            if ok:
                                st.success("已从向量库移除。")
                                if also_delete_file and src_path and os.path.exists(src_path):
                                    if is_subpath_fn(src_path, st.session_state["global_store_dir"]):
                                        try:
                                            os.remove(src_path)
                                            st.success("已删除源文件（磁盘）。")
                                        except Exception as e:
                                            st.warning(f"源文件删除失败：{e}")
                                    else:
                                        st.warning("源文件不在 store_dir 子目录下，已跳过磁盘删除（仅移除向量库索引）。")
                                rerun_fn()
                            else:
                                st.warning("未找到该 doc_id（可能已被删除）。")
                        except Exception as e:
                            st.error("删除失败。")
                            st.write(str(e))
                            st.code(traceback.format_exc())
        else:
            st.info("当前库没有文档。请在左侧上传文件入库。")

        # 上传入库
        if add_btn:
            if not guard_feature_run_fn("本地知识库管理-上传入库", require_llm=True, require_embed=True, require_rag_dir=True):
                pass
            else:
                if not uploaded:
                    st.warning("未选择任何文件。")
                else:
                    ensure_dir_fn(upload_dir)
                    saved_paths: List[str] = []
                    for uf in uploaded:
                        base = uf.name if keep_original_name else f"upload_{now_tag_fn()}"
                        safe = os.path.basename(base)
                        target = os.path.join(upload_dir, safe)
                        if os.path.exists(target):
                            stem, ext = os.path.splitext(safe)
                            target = os.path.join(upload_dir, f"{stem}_{now_tag_fn()}{ext}")

                        with open(target, "wb") as f:
                            f.write(uf.getbuffer())
                        saved_paths.append(target)

                    with st.spinner("正在切片向量化并入库，等待时间可能较长..."):
                        try:
                            added = add_files_into_store_fn(st.session_state["global_store_dir"], saved_paths)
                            st.success("入库完成。")
                            with st.expander("查看入库结果（added_docs）", expanded=False):
                                st.json(added)
                            rerun_fn()
                        except Exception as e:
                            st.error("入库失败。")
                            st.write(str(e))
                            st.code(traceback.format_exc())

        # 清空向量库
        if clear_btn:
            if not guard_feature_run_fn("本地知识库管理-清空", require_rag_dir=True):
                pass
            else:
                with st.spinner("正在清空向量库持久化文件..."):
                    try:
                        removed = clear_store_files_fn(st.session_state["global_store_dir"])
                        st.success(f"清空完成，删除文件数：{removed}")
                        rerun_fn()
                    except Exception as e:
                        st.error("清空失败。")
                        st.write(str(e))
                        st.code(traceback.format_exc())
