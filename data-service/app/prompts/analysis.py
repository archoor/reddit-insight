"""
六维度分析 + 多商机输出 Prompt 模板。

核心变化：opportunity_assessment 从单对象改为 opportunities[] 数组，最多5条。
每条商机独立打分，引用对应的痛点证据。
"""
from typing import Any, Dict, List


def build_post_context(
    title: str,
    selftext: str,
    subreddit: str,
    score: int,
    num_comments: int,
) -> str:
    """构造帖子上下文字符串。"""
    body_preview = (selftext or "")[:600]
    if selftext and len(selftext) > 600:
        body_preview += "... [truncated]"
    return (
        f"SUBREDDIT: r/{subreddit}\n"
        f"POST TITLE: {title}\n"
        f"POST SCORE: {score} | COMMENTS: {num_comments}\n"
        f"POST BODY:\n{body_preview or '(no body text)'}"
    )


def build_comments_text(comments: List[Dict[str, Any]], batch_info: str = "") -> str:
    """将评论列表格式化为供 LLM 阅读的文本。"""
    lines = []
    if batch_info:
        lines.append(f"[{batch_info}]")
    for i, c in enumerate(comments, 1):
        score = c.get("score", 0)
        body = (c.get("body") or "").strip()[:800]
        reason = c.get("sample_reason", "")
        lines.append(f"Comment #{i} [score:{score}] [{reason}]:\n{body}")
    return "\n\n".join(lines)


# ─── Prompt 1: 综合分析（单批次或最终合并用）───────────────────────────────

COMPREHENSIVE_ANALYSIS_PROMPT = """Analyze the following Reddit post and its comments from a BUSINESS OPPORTUNITY perspective.

{post_context}

COMMENTS ({comment_count} sampled from {total_comments} total):
{comments_text}

Identify ALL distinct business opportunities in this discussion (maximum 5).
Each opportunity should target a different user segment, pain point, or solution approach.

Provide a comprehensive business analysis in the following JSON format:

{{
  "pain_points": {{
    "items": [
      {{
        "description": "specific pain point description",
        "intensity": 8,
        "frequency_mentions": 3,
        "evidence_quotes": ["exact quote from comment 1", "exact quote from comment 2"],
        "existing_solutions": ["solution users mentioned"],
        "solution_gaps": ["what these solutions are missing"]
      }}
    ],
    "top_pain_point": "the single most critical pain point in one sentence"
  }},
  "willingness_to_pay": {{
    "score": 7,
    "signals": [
      {{
        "type": "explicit_payment_mention / price_complaint / workaround_cost",
        "quote": "exact quote showing payment signal",
        "implication": "what this suggests about WTP"
      }}
    ],
    "price_sensitivity": "low / medium / high",
    "suggested_price_range": "$X-$Y per month",
    "budget_mentions": ["any specific budget amounts mentioned"]
  }},
  "tech_feasibility": {{
    "feasibility_score": 7,
    "tech_stack_suggested": ["Python", "REST API"],
    "complexity": "low / medium / high",
    "estimated_dev_time": "2-4 weeks for MVP",
    "key_challenges": ["challenge 1", "challenge 2"],
    "required_integrations": ["third-party service 1"]
  }},
  "competition": {{
    "competitors_mentioned": [
      {{
        "name": "CompetitorName",
        "weakness": "what users complain about it",
        "quote": "exact user quote"
      }}
    ],
    "market_gap": "description of the unmet need",
    "differentiation_opportunities": ["opportunity 1", "opportunity 2"],
    "switching_barriers": "how hard it is for users to switch solutions"
  }},
  "operational_risks": {{
    "sustainability_score": 6,
    "recurring_need": true,
    "churn_risks": ["risk 1", "risk 2"],
    "operational_challenges": ["challenge 1"],
    "moat_potential": "description of potential competitive moat",
    "regulatory_concerns": ["concern 1 or empty array"]
  }},
  "opportunities": [
    {{
      "opportunity_score": 72,
      "title": "concise opportunity title (max 60 chars)",
      "summary": "2-3 sentence executive summary of this specific opportunity",
      "recommendation": "Build / Validate / Skip",
      "target_audience": "specific description of who would pay for this",
      "monetization_model": "SaaS subscription / one-time / freemium / marketplace",
      "market_size_estimate": "rough market size description",
      "key_features": ["MVP feature 1", "MVP feature 2", "MVP feature 3"],
      "risks": ["top risk 1", "top risk 2"],
      "pain_point_refs": [0, 1],
      "willingness_to_pay_score": 7,
      "pain_point_intensity": 8,
      "tech_difficulty": 4,
      "sustainability_score": 6
    }}
  ]
}}

IMPORTANT: The "opportunities" array must contain 1 to 5 items. Only include opportunities with opportunity_score >= 40. Order by opportunity_score descending."""


# ─── Prompt 2: 批次分析（评论太多时每批独立分析）───────────────────────────

BATCH_ANALYSIS_PROMPT = """Analyze the following Reddit post comments for business insights. This is batch {batch_num} of {total_batches}.

{post_context}

COMMENTS (batch {batch_num}/{total_batches}):
{comments_text}

Extract business signals from these comments and respond in JSON:

{{
  "pain_points": [
    {{
      "description": "pain point description",
      "intensity": 7,
      "evidence_quotes": ["quote 1"],
      "frequency": 1
    }}
  ],
  "payment_signals": [
    {{
      "quote": "exact quote",
      "type": "explicit_payment / price_complaint / workaround_cost"
    }}
  ],
  "competitors_mentioned": [
    {{
      "name": "tool name",
      "weakness": "why users dislike it",
      "quote": "exact quote"
    }}
  ],
  "feature_requests": [
    {{
      "description": "what users want",
      "quote": "exact quote"
    }}
  ],
  "key_insights": ["insight 1", "insight 2"]
}}"""


# ─── Prompt 3: 批次结果合并 ──────────────────────────────────────────────

MERGE_BATCHES_PROMPT = """You have analyzed a Reddit post in {batch_count} batches. Below are the batch analysis results.

{post_context}

BATCH RESULTS:
{batch_results_json}

Now synthesize all batch results into a single comprehensive analysis.
- Merge duplicate pain points (combine their evidence and sum frequencies)
- Keep conflicting viewpoints and note the disagreement
- Rank pain points by combined intensity * frequency
- Identify ALL distinct business opportunities (maximum 5)
- Only include opportunities with opportunity_score >= 40

Respond in the same JSON format as a comprehensive analysis:

{{
  "pain_points": {{
    "items": [
      {{
        "description": "merged pain point",
        "intensity": 8,
        "frequency_mentions": 5,
        "evidence_quotes": ["quote from batch 1", "quote from batch 2"],
        "existing_solutions": [],
        "solution_gaps": []
      }}
    ],
    "top_pain_point": "the single most critical pain point"
  }},
  "willingness_to_pay": {{
    "score": 7,
    "signals": [],
    "price_sensitivity": "medium",
    "suggested_price_range": "$X-$Y/month",
    "budget_mentions": []
  }},
  "tech_feasibility": {{
    "feasibility_score": 7,
    "tech_stack_suggested": [],
    "complexity": "medium",
    "estimated_dev_time": "X weeks for MVP",
    "key_challenges": [],
    "required_integrations": []
  }},
  "competition": {{
    "competitors_mentioned": [],
    "market_gap": "description",
    "differentiation_opportunities": [],
    "switching_barriers": "description"
  }},
  "operational_risks": {{
    "sustainability_score": 6,
    "recurring_need": true,
    "churn_risks": [],
    "operational_challenges": [],
    "moat_potential": "description",
    "regulatory_concerns": []
  }},
  "opportunities": [
    {{
      "opportunity_score": 72,
      "title": "opportunity title (max 60 chars)",
      "summary": "2-3 sentence executive summary",
      "recommendation": "Build / Validate / Skip",
      "target_audience": "description",
      "monetization_model": "SaaS subscription",
      "market_size_estimate": "description",
      "key_features": ["feature 1", "feature 2"],
      "risks": ["risk 1"],
      "pain_point_refs": [0],
      "willingness_to_pay_score": 7,
      "pain_point_intensity": 8,
      "tech_difficulty": 4,
      "sustainability_score": 6
    }}
  ]
}}"""
