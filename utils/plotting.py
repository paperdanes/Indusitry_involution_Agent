# plotting.py
# 针对于功能二的独立绘图调用
from __future__ import annotations
from typing import List, Dict, Any
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

def plot_involution_trend(measure_json: Dict[str, Any], out_path: str = "outputs/involution_trend.png") -> str:
    series = measure_json.get("series", [])
    periods = [x["period"] for x in series]
    values = [x.get("involution_index_0_1", None) for x in series]

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 4), dpi=200)
    plt.plot(periods, values, marker="o")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Involution Index (0-1)")
    plt.xlabel("Period")
    plt.tight_layout()
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    return str(out)
