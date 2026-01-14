# Industry Involution Agent

面向“新能源汽车行业内卷识别与反内卷政策辅助”的 Agent 系统。  
本项目支持基于本地知识库（RAG）对企业/行业材料进行检索增强分析，输出结构化的“内卷识别结果”与“政策干预模拟建议”。
---

## 功能
- **RAG 知识库**：支持导入企业财报、专利、招聘、产能公告、价格信息等材料，构建本地向量检索。
- **内卷识别**：对企业行为进行标签化判定（如价格战、产能扩张、技术同质化、营销内耗、供应链挤压等），输出证据与置信度。
- **政策模拟**：基于识别结果，生成可执行的政策干预组合与风险评估（如价格约束、产能调控、研发补贴、行业协同等）。
- **结构化输出**：支持 JSON 化结果，便于后续报表系统集成。
---

## 项目结构
```
  Industry Involution Agent
  ├─ function/          # 业务核心逻辑（识别 / 测度 / 政策）
  │  ├─ identify.py
  │  ├─ measure_yearly.py
  │  └─ policy.py
  ├─ rag/               # RAG 底座（向量存储与检索管理）
  │  ├─ rag.py
  │  └─ rag_store_manager.py
  ├─ UI_function/       # UI 逻辑层（面向 Streamlit 等前端）
  │  ├─ kb_manager_function.py
  │  ├─ identify_function.py
  │  ├─ measure_yearly_function.py
  │  ├─ policy_function.py
  │  └─ UI_setting / sidebar
  ├─ utils/             # 通用工具与底层能力
  │  ├─ llm.py
  │  ├─ prompts.py
  │  ├─ metrics_b.py
  │  ├─ json_utils.py
  │  └─ json_to_word.py
  ├─ app.py             # 项目主入口
  ├─ requirements.txt   # 依赖列表
  └─ README.md
```
---
## 快速开始

### 1) 创建环境
```bash
conda create -n agent python==3.11
conda activate agent
pip install -r requirements.txt
```
### 2) Demo运行
```bash
streamlit run app.py
```


