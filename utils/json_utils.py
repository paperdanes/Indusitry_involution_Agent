# json_utils.py
from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def safe_filename(name: str, max_len: int = 80) -> str:
    """
    生成安全文件名：去掉非法字符、压缩空白、限制长度
    """
    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^\w\u4e00-\u9fff\-\._]+", "", name)  # 允许中文、字母数字、-_.
    return name[:max_len] if len(name) > max_len else name


def save_json(
    data: Any,
    *,
    out_dir: str = "outputs",
    filename: Optional[str] = None,
    prefix: str = "未知数据",
    tag: str = "",
) -> str:
    """
    保存 JSON 到文件并返回保存路径（字符串）
    - filename: 不传则自动生成：{prefix}_{tag}_{timestamp}.json
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        tag_part = f"_{_safe_filename(tag)}" if tag else ""
        filename = f"{_safe_filename(prefix)}{tag_part}_{ts}.json"
    else:
        filename = _safe_filename(filename)

    file_path = out_path / filename

    # 兜底：遇到不可序列化对象时转成 str（一般不会发生，除非你把 numpy 类型塞进来）
    def _default(o: Any):
        return str(o)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=_default)

    return str(file_path)


def pretty_print_json(data: Any) -> None:
    """
    控制台格式化输出 JSON
    """
    print(json.dumps(data, ensure_ascii=False, indent=2))
