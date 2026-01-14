
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List

# -----------------------------
# 小工具函数
# -----------------------------
def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")

def safe_get(obj: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    cur: Any = obj
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return default if cur is None else cur

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def abspath(p: str) -> str:
    return os.path.abspath(os.path.expanduser(p))

def is_subpath(child: str, parent: str) -> bool:
    try:
        child_abs = abspath(child)
        parent_abs = abspath(parent)
        return os.path.commonpath([child_abs, parent_abs]) == parent_abs
    except Exception:
        return False
