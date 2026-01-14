# prompts.py
# 整套系统提示词工程
from __future__ import annotations
from typing import List, Dict, Any

TAXONOMY = [
    {"id": "L1_PRICE_WAR", "name": "价格战主导", "definition": "持续降价/补贴/金融让利为主要竞争手段，导致行业价格下行与利润挤压。"},
    {"id": "L2_CAPACITY_GLUT", "name": "产能严重过剩", "definition": "规划/投产产能与销量/产量不匹配，出现扩产竞赛与低利用率并存。"},
    {"id": "L3_TECH_HOMOGEN", "name": "创新同质化", "definition": "技术路线/专利主题/产品卖点高度趋同，差异集中在可复制参数。"},
    {"id": "L4_MARKETING_ARMS", "name": "营销内耗与渠道补贴竞赛", "definition": "高额投放、返利补贴、渠道内耗以换取短期销量。"},
    {"id": "L5_SUPPLYCHAIN_SQUEEZE", "name": "供应链压价与账期扩张", "definition": "通过延长账期、压价把压力传导给供应链，风险外溢。"},
    {"id": "L6_TALENT_INTERNAL", "name": "人才挤压与组织内卷", "definition": "招聘/考核偏短期冲刺，组织频繁调整，长期研发能力受损。"},
    {"id": "L7_FIN_STRESS", "name": "财务承压与以价换量", "definition": "利润与现金流承压，被迫以价换量，形成恶性循环。"},
    {"id": "L8_REG_ARBITRAGE", "name": "合规套利与政策依赖型竞争", "definition": "优势主要来自补贴/地方政策/口径套利而非产品效率。"}
]


def build_identify_messages(user_query: str, evidence_hits: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    evidence_hits: rag.search() 返回的 list[ {chunk_id, doc_id, score, text} ]
    """
    taxonomy_text = "\n".join([f"- {x['id']}：{x['name']}（{x['definition']}）" for x in TAXONOMY])

    # 证据块（可为空）
    if evidence_hits:
        ev_lines = []
        for i, h in enumerate(evidence_hits, 1):
            snippet = (h["text"] or "").replace("\n", " ").strip()
            ev_lines.append(
                f"[{i}] chunk_id={h['chunk_id']} doc_id={h['doc_id']} score={h['score']:.4f}\n"
                f"TEXT: {snippet}\n"
            )
        evidence_text = "\n".join(ev_lines)
    else:
        evidence_text = "（无检索结果）"

    system = f"""
    你是一名“新能源汽车行业竞争与产业组织”分析助手，任务是识别材料所反映的“内卷式竞争”特征。
    你会收到：用户问题 + RAG检索到的证据片段（可能为空）。
    要求：
    1) 输出必须是**严格 JSON**，不要输出任何额外文字、解释或 Markdown。
    2) 至少输出 3 个标签（从给定 taxonomy 中选择），可以输出 3-6 个最相关的标签。
    3) 允许在证据不足时依赖你的行业知识进行推断（风险由用户承担），但必须在相应标签里标注 evidence_level：
       - "strong"：有明确证据片段支撑
       - "weak"：证据间接或不充分
       - "none"：几乎无证据，主要为模型推断
    4) 证据引用不是强制：如有证据，请尽量引用 chunk_id；如无则 evidences 置空数组。
    5) 对每个标签给出 score(0-100)、confidence(0-1)、rationale（专业、可执行、尽量对应材料语句或行业机制）。
    6) overall.has_involution 需给出；若信息不足可给 true/false 但 confidence 要相应降低。

    taxonomy（可选标签）：
    {taxonomy_text}

    输出 JSON 结构必须为：
    {{
      "overall": {{"has_involution": bool, "confidence": float, "summary": str}},
      "labels": [
        {{
          "label_id": str,
          "label_name": str,
          "score": int,
          "confidence": float,
          "evidence_level": "strong"|"weak"|"none",
          "rationale": str,
          "evidences": [{{"chunk_id": str, "doc_id": str}}]
        }}
      ],
      "notes": [str]
    }}
    """

    user = f"""用户问题：{user_query}  RAG证据片段：{evidence_text}"""

    return [
        {"role": "system", "content": system.strip()},
        {"role": "user", "content": user.strip()},
    ]

from typing import List, Dict, Any

# 统一把指标都压到 0-100 的强度量表（LLM 负责生成该强度）
# direction: +1 表示越大越“内卷严重”；-1 表示越大越“缓解内卷”（计算时会做 100-x 反转）
METRICS = [
    {"key": "capital_intensity_level", "name": "资本密集度程度", "direction": +1},
    {"key": "capacity_utilization_pct", "name": "产能利用率", "direction": +1},
    {"key": "rnd_expense_ratio", "name": "研发费用率", "direction": +1},
    {"key": "rnd_personnel_intensity", "name": "研发人员投入强度", "direction": +1},
    {"key": "digital_intangible_asset_investment_intensity", "name": "数字无形资产投入", "direction": +1},
    {"key": "digital_talent_investment_intensity", "name": "数字化人才投入强度", "direction": +1},
    {"key": "employee_training_investment_intensity", "name": "员工培训投入强度", "direction": +1},
    {"key": "high_level_human_capital_investment_intensity", "name": "高层人力投入强度", "direction": +1},
    {"key": "management_expense_ratio", "name": "管理费用率", "direction": +1},
    {"key": "board_meeting_intensity", "name": "董监高会议强度", "direction": +1},
    {"key": "sales_expense_ratio", "name": "销售费用率", "direction": +1},
    {"key": "sales_personnel_intensity", "name": "销售人员投入强度", "direction": +1},
]

def build_year_measure_messages(
    company: str,
    year_label: str,
    y_start: str,
    y_end: str,
    rag_hits: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    metric_lines = "\n".join([f"- {m['key']}：{m['name']}" for m in METRICS])

    # 强制使用 RAG：即便证据弱，也要在 rationale 里体现“参考了哪些片段的哪些要点”
    ev_lines = []
    for i, h in enumerate(rag_hits, 1):
        txt = (h.get("text") or "").replace("\n", " ").strip()
        ev_lines.append(
            f"[{i}] chunk_id={h['chunk_id']} score={h['score']:.4f}\n"
            f"TEXT: {txt[:260]}"
        )
    evidence_text = "\n".join(ev_lines) if ev_lines else "结合自己的经验和学习知识综合分析"

    system = f"""
    你是一位资深新能源行业分析师，拥有10年以上行业研究经验。
    请基于最新可获取的行业数据，从以下十二个指标方面对新能源汽车行业进行全面的内卷程度分析。
    要求生成企业在指定年份的量化指标估计，并输出严格JSON。
    
    硬性要求：
    1) 只输出严格 JSON，不要任何额外文字/Markdown。
    2）每一个指标都要有数据，如果用户提供依据不足，请根据你的经验和知识分析。
    3) 输出仅限一个年份：{year_label}（{y_start}~{y_end}）。
    4) 指标尽量量化：0-1 强度量表（或明确%）；并给每个指标置信度(0-1)。
    5) 为避免截断：rationale <= 120字；notes每条<=150字。
    6) 所有confidence不可以是0.5
    7） 按照一般规律，数字无形资产投入、数字化人才投入强度、员工培训投入强度、销售人员投入强度逐年上升明显。


    需要输出的指标（必须全部给出）：
    {metric_lines}

    输出 JSON 结构必须为：
    {{
      "company": str,
      "period": str,
      "time_window": {{"start": str, "end": str}},
      "metrics": {{
        "capital_intensity_level": float,
        "capacity_utilization_pct": float,
        "rnd_expense_ratio": float,
        "rnd_personnel_intensity": float,
        "digital_intangible_asset_investment_intensity": float,
        "digital_talent_investment_intensity": float,
        "employee_training_investment_intensity": float,
        "high_level_human_capital_investment_intensity": float,
        "management_expense_ratio": float,
        "board_meeting_intensity": float,
        "sales_expense_ratio": float,
        "sales_personnel_intensity": float
      }},
      "metric_confidence": {{
        "capital_intensity_level": float,
        "capacity_utilization_pct": float,
        "rnd_expense_ratio": float,
        "rnd_personnel_intensity": float,
        "digital_intangible_asset_investment_intensity": float,
        "digital_talent_investment_intensity": float,
        "employee_training_investment_intensity": float,
        "high_level_human_capital_investment_intensity": float,
        "management_expense_ratio": float,
        "board_meeting_intensity": float,
        "sales_expense_ratio": float,
        "sales_personnel_intensity": float
      }},
      "overall_confidence": float,
      "rationale": str,
      "used_evidence": [{{"chunk_id": str, "doc_id": str}}],
      "notes": [str]
    }}
    """.strip()

    user = f"""
    企业：{company}
    年份：{year_label}（{y_start}~{y_end}）
    RAG证据片段：
    {evidence_text}
    """.strip()

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]



from typing import List, Dict, Any

def build_policy_simulation_messages(
    *,
    policy_input_text: str,
    industry_scope: str = "中国新能源汽车行业",
    time_horizon_months: int = 24,
    evidence_hits: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Build messages for the 'policy intervention simulation & plan generation' feature.

    The model MUST output strict JSON following the user's fixed report framework:
      - 第一章 引言 / 1.1 概述
      - 第二章 行业状态 / 2.1 当前状态 / 2.2 趋势预测
      - 第三章 政策情景设定（逐政策 3.x.1~3.x.4）
      - 第四章 政策建议（4.1~4.3）

    evidence_hits: rag.search() returns list[{chunk_id, doc_id, score, text}]
    """

    # Evidence blocks (may be empty)
    if evidence_hits:
        ev_lines = []
        for i, h in enumerate(evidence_hits, 1):
            txt = (h.get("text") or "").replace("\n", " ").strip()
            ev_lines.append(
                f"[{i}] chunk_id={h.get('chunk_id')} doc_id={h.get('doc_id')} score={float(h.get('score', 0)):.4f}\n"
                f"TEXT: {txt[:320]}\n"
            )
        evidence_text = "\n".join(ev_lines)
    else:
        evidence_text = "（无检索结果：必须在disclaimer与notes说明证据不足，并降低confidence）"

    system = """
    你是一名“新能源汽车产业反内卷政策仿真与方案生成”高级分析助手。
    你将收到：
    1) 用户输入的 1 个或多个政策假设（policy_input_text，可能是自然语言、要点或简化条款）
    2) 来自知识库检索的证据片段（RAG evidence，可能为空）

    你的任务：在单次输出中，完成“政策干预情景仿真 + 报告化输出”，并严格按照用户指定的报告框架生成结构化 JSON。

    重要约束（硬性）：
    1) 只输出严格 JSON，不要输出任何额外文字、解释、Markdown、代码块。
    2) JSON 必须完全符合下方给定 schema：字段不得缺失、不得新增同层级字段名；允许在字段值里填 null/[] 表示缺失。
    3) 必须体现“仿真”结果：对每个政策给出对内卷指数（0-100）的影响区间与置信度，并解释作用机制。
    4) 若 policy_input_text 未给出可量化参数：不得编造精确百分比；可以给“范围/强弱/触发条件”描述，并用区间表达不确定性。
    5) 证据使用：若 evidence 非空，请在 evidence_used 中尽量引用 >=3 条 chunk_id，并在各章/各政策分析里体现引用要点；若证据为空，evidence_used 置空并在 notes 说明“证据为空，以下为基于常识与行业逻辑的推演”。
    6) 语言：全部用中文；表述要专业、克制、可执行；避免空话。
    7) 数值规范：
       - involution_index_*_range 统一为 [min,max]，0<=min<=max<=100
       - confidence 取值 (0,1]，不得等于 0.5
       - 若无法估计范围，填 null 并在 notes 说明原因
    8) 长度控制：
       - 每个 text 至少500字的论述；每个 bullets 列表不超过 7 条。

    内卷指数（0-100）口径（用于一致性，不需要解释过多）：
    - 0 表示竞争秩序健康、创新驱动、利润可持续
    - 100 表示极端“以价换量/扩产竞赛/同质化/账期挤压”并存的恶性内卷

    输出 JSON 必须为以下结构（严格一致）：
    {
      "meta": {
        "industry_scope": str,
        "time_horizon_months": int,
        "policy_count": int,
        "assumptions": [str]
      },
      "chapter1": {
        "title": "引言",
        "1.1": {
          "title": "新能源汽车行业内卷现象概述",
          "text": str,
          "bullets": [str],
          "key_risks": [str],
          "evidence": [{"chunk_id": str, "doc_id": str}]
        }
      },
      "chapter2": {
        "title": "行业状态",
        "2.1": {
          "title": "当前新能源行业状态",
          "text": str,
          "bullets": [str],
          "involution_index_baseline_range": [float, float] | null,
          "confidence": float,
          "evidence": [{"chunk_id": str, "doc_id": str}]
        },
        "2.2": {
          "title": "未来趋势预测",
          "text": str,
          "bullets": [str],
          "trend_points": [str],
          "risk_triggers": [str],
          "evidence": [{"chunk_id": str, "doc_id": str}]
        }
      },
      "chapter3": {
        "title": "政策情景设定",
        "policies": [
          {
            "x": int,
            "policy_name": str,
            "3.x.1": {
              "title": "政策内容",
              "policy_measures": [str],
              "parameters": [{"name": str, "value": str | null, "note": str}]
            },
            "3.x.2": {
              "title": "政策作用机制",
              "mechanism_chain": [str],
              "primary_levers": ["定价","产能","研发","渠道","供应链账期","并购退出","其他"]
            },
            "3.x.3": {
              "title": "适用场景与边界条件",
              "applicable_when": [str],
              "boundary_conditions": [str],
              "failure_modes": [str]
            },
            "3.x.4": {
              "title": "政策对企业行为/产业行为的影响",
              "involution_index": {
                "baseline_range": [float, float] | null,
                "after_range": [float, float] | null,
                "change_range": [float, float] | null,
              },
              "behavior_impacts": {
                "pricing": {"direction": "up|down|mixed", "text": str},
                "capacity": {"direction": "up|down|mixed", "text": str},
                "rnd": {"direction": "up|down|mixed", "text": str},
                "channels": {"direction": "up|down|mixed", "text": str},
                "supply_chain_terms": {"direction": "up|down|mixed", "text": str},
                "mna_exit": {"direction": "up|down|mixed", "text": str}
              },
              "kpis": [str],
              "side_effects": [str]
            }
          }
        ]
      },
      "chapter4": {
        "title": "政策建议",
        "4.1": {
          "title": "推荐方案（主推/备选/不建议）",
          "primary": [{"policy_x": int, "why": str}],
          "secondary": [{"policy_x": int, "why": str}],
          "not_recommended": [{"policy_x": int, "why": str}]
        },
        "4.2": {
          "title": "分场景选择规则",
          "rules": [
            {
              "scene": str,
              "triggers": [str],
              "recommended_policy_x": [int],
              "expected_results": [str],
              "watchouts": [str]
            }
          ]
        },
        "4.3": {
          "title": "配套机制及注意事项",
          "supporting_mechanisms": [str],
          "governance_and_disclosure": [str],
          "exit_and_consumer_protection": [str],
          "monitoring_and_iteration": [str]
        }
      },
      "evidence_used": [{"chunk_id": str, "doc_id": str, "reason": str}],
      "notes": [str],
      "disclaimer": str
    }
    """.strip()

    user = f"""
行业范围：{industry_scope}
仿真时间跨度：{time_horizon_months}
用户政策输入（可能包含多个政策；请你先拆分为 1..n 并命名 policy_name）：
{policy_input_text}
RAG证据片段（如非空必须使用并引用 chunk_id/doc_id）：
{evidence_text}
""".strip()

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
