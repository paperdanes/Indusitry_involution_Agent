# llm.py
# 基础大模型对话框架
from __future__ import annotations
import json
import re
from openai import OpenAI
import numpy as np
from utils import settings
from typing import Any, Dict, List

def _extract_json_object(text: str) -> str:
    """
    从输出中提取json框架数据，便于后续格式化处理。
    """
    text = text.strip()
    # 直接就是 JSON
    if text.startswith("{") and text.endswith("}"):
        return text

    # 尝试截取第一个 {...}
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("No JSON object found in model output.")
    return m.group(0)

def chat_json(messages: List[Dict[str, Any]], *, model: str | None = None) -> Dict[str, Any]:
    """
    调用 chat_once，然后解析 JSON；解析失败报错
    """
    raw = chat_once(messages, model=model)
    js = _extract_json_object(raw)
    return json.loads(js)

def embed_texts(texts: List[str]) -> np.ndarray:
    """
    返回 shape=(n, dim) 的 float32 numpy 数组
    text-embedding-v4 文档提示最大行数 10，所以这里按批次切分 :contentReference[oaicite:2]{index=2}
    """
    client = get_client()

    all_vecs: List[List[float]] = []
    bs = max(1, int(getattr(settings, "EMBED_BATCH", 10)))

    for i in range(0, len(texts), bs):
        batch = texts[i:i + bs]
        resp = client.embeddings.create(
            model=settings.EMBED_MODEL,
            input=batch,
            dimensions=settings.EMBED_DIM,
            encoding_format="float"
        )
        # OpenAI兼容返回：resp.data[j].embedding
        for item in resp.data:
            all_vecs.append(item.embedding)

    arr = np.array(all_vecs, dtype=np.float32)
    return arr


def embed_query(text: str) -> np.ndarray:
    return embed_texts([text])[0]

def get_client() -> OpenAI:
    #st.markdown(str(settings.DASHSCOPE_API_KEY))
    # OpenAI 兼容：只需要 api_key + base_url
    return OpenAI(
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.BASE_URL,
    )


def chat_once(messages: List[Dict[str, Any]], *, model: str | None = None) -> str:
    client = get_client()
    resp = client.chat.completions.create(
        model=model or settings.MODEL,
        messages=messages,
        temperature=settings.TEMPERATURE,
        top_p=settings.TOP_P,
        max_tokens=settings.MAX_TOKENS,
    )
    return resp.choices[0].message.content


def smoke_test() -> None:
    messages = [
        {"role": "system", "content": "你是一个严谨的助理。"},
        {"role": "user", "content": "用一句话解释什么是“行业内卷”。"},
    ]
    out = chat_once(messages)
    print("=== Qwen API Smoke Test Output ===")
    print(out)

# ---------------------------
# 本地快速测试
# ---------------------------
if __name__ == "__main__":
    smoke_test()
