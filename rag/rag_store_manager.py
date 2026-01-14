# rag_store_manager.py
# rag本地知识库管理
from __future__ import annotations

import os
import argparse
from typing import List, Optional

from utils import settings
from rag import FaissRAG


def _store_dir(cli_store_dir: Optional[str] = None) -> str:
    return cli_store_dir or getattr(settings, "RAG_STORE_DIR", "rag_store")


def cmd_status(store_dir: str) -> int:
    rag = FaissRAG.load(store_dir)
    print(f"store_dir: {os.path.abspath(store_dir)}")
    print(f"empty: {rag.is_empty()}")
    print(f"dim: {rag.dim}")
    print(f"ntotal: {rag.index.ntotal if rag.index is not None else 0}")
    print(f"docs: {len(rag.docs)}")
    if rag.docs:
        for d in rag.list_docs():
            print(f"- {d['doc_id']} | chunks={d['n_chunks']} | {d['source_path']}")
    return 0


def cmd_add(store_dir: str, paths: List[str]) -> int:
    rag = FaissRAG.load(store_dir)
    added = rag.add_files(paths)
    rag.save(store_dir)
    print(f"added_docs: {len(added)}")
    for did, entry in added.items():
        print(f"- {did} | chunks={entry.get('n_chunks')} | {entry.get('source_path')}")
    return 0


def cmd_remove(store_dir: str, doc_id: Optional[str], path: Optional[str]) -> int:
    rag = FaissRAG.load(store_dir)
    ok = rag.remove_doc(doc_id=doc_id, source_path=path)
    rag.save(store_dir)
    print("removed" if ok else "not_found")
    return 0 if ok else 2


def cmd_clear(store_dir: str) -> int:
    # 直接清空持久化文件
    p = FaissRAG.store_paths(store_dir)
    removed = 0
    for k in ["index", "chunks", "manifest"]:
        fp = p[k]
        if os.path.exists(fp):
            os.remove(fp)
            removed += 1
    print(f"cleared_files: {removed}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Manage persistent FAISS RAG store: add/remove/status/clear",
    )
    p.add_argument("--store", default=None, help="RAG store directory (default: settings.RAG_STORE_DIR or ./rag_store)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("status", help="Show store status")
    s1.set_defaults(_fn="status")

    s2 = sub.add_parser("add", help="Add documents into store")
    s2.add_argument("paths", nargs="+", help="File paths to ingest (txt/pdf/docx/...)")
    s2.set_defaults(_fn="add")

    s3 = sub.add_parser("remove", help="Remove a document from store")
    g = s3.add_mutually_exclusive_group(required=True)
    g.add_argument("--doc-id", dest="doc_id", help="Document id to remove")
    g.add_argument("--path", dest="path", help="Source file path to remove (matches stored absolute path)")
    s3.set_defaults(_fn="remove")

    s4 = sub.add_parser("clear", help="Clear the whole store (delete index/manifest/chunks files)")
    s4.set_defaults(_fn="clear")

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    store_dir = _store_dir(args.store)

    if args._fn == "status":
        return cmd_status(store_dir)
    if args._fn == "add":
        return cmd_add(store_dir, args.paths)
    if args._fn == "remove":
        return cmd_remove(store_dir, getattr(args, "doc_id", None), getattr(args, "path", None))
    if args._fn == "clear":
        return cmd_clear(store_dir)

    return 1

# ---------------------------
# 本地快速测试
# ---------------------------
if __name__ == "__main__":
    raise SystemExit(main())
    #查看库状态
    #python rag_store_manager.py status

    #往库里加资料（txt/pdf/docx 都支持）
    #python rag_store_manager.py add ./rag_store/data/data.txt

    #删除资料（两种方式二选一）
    #python rag_store_manager.py remove --doc-id 7d8c...abcd
    #python rag_store_manager.py remove --path rag_store/data/data.txt