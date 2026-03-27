"""
LLM 分析调度器：核心业务逻辑。

流程：
  1. 从数据库获取帖子和评论（直接导入，无 sys.path hack）
  2. 智能采样评论
  3. 按 token 预算分批
  4. 逐批调用 LLM 分析
  5. 多批结果合并
  6. 结果写入 PostAnalysis 表
  7. 触发商机批量生成（一帖多商机）
"""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import litellm
from sqlmodel import Session, select

from app.config import settings
from app.models.post import Post, AnalysisStatus
from app.models.comment import Comment
from app.models.post_analysis import PostAnalysis
from app.prompts import (
    SYSTEM_PROMPT,
    build_post_context,
    build_comments_text,
    COMPREHENSIVE_ANALYSIS_PROMPT,
    BATCH_ANALYSIS_PROMPT,
    MERGE_BATCHES_PROMPT,
)
from app.services.comment_sampler import sample_comments
from app.services.token_budget import split_into_batches, estimate_tokens

logger = logging.getLogger(__name__)

# 禁用 litellm 冗余日志
litellm.suppress_debug_info = True


def _call_llm(prompt: str, model: str = "") -> tuple[str, int]:
    """
    调用 LLM，返回 (响应文本, 消耗 token 数)。
    通过 LiteLLM 支持 OpenAI、Claude、DeepSeek、Gemini 等。
    """
    model = model or settings.LLM_MODEL

    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": settings.LLM_MAX_TOKENS,
        "temperature": settings.LLM_TEMPERATURE,
    }

    # Gemini 通过 GEMINI_API_KEY 环境变量鉴权，不能直接传 api_key 参数
    is_gemini = model.startswith("gemini/")
    if settings.LLM_API_KEY and not is_gemini:
        kwargs["api_key"] = settings.LLM_API_KEY
    if settings.LLM_API_BASE:
        kwargs["api_base"] = settings.LLM_API_BASE

    response = litellm.completion(**kwargs)
    content = response.choices[0].message.content or ""
    tokens_used = response.usage.total_tokens if response.usage else estimate_tokens(prompt + content)
    return content, tokens_used


def _extract_json(text: str) -> Dict[str, Any]:
    """从 LLM 响应中提取 JSON，容错处理 markdown 代码块。"""
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    logger.warning(f"[analyzer] JSON 解析失败，原始内容: {text[:200]}")
    return {}


def _analyze_single_batch(
    post_context_str: str,
    comments: List[Dict[str, Any]],
    comment_count_total: int,
    model: str = "",
) -> tuple[Dict[str, Any], int]:
    """单批次全面分析，返回 (分析结果 JSON, 消耗 token)。"""
    comments_text = build_comments_text(comments)
    prompt = COMPREHENSIVE_ANALYSIS_PROMPT.format(
        post_context=post_context_str,
        comment_count=len(comments),
        total_comments=comment_count_total,
        comments_text=comments_text,
    )
    raw, tokens = _call_llm(prompt, model)
    result = _extract_json(raw)
    return result, tokens


def _analyze_batch(
    post_context_str: str,
    comments: List[Dict[str, Any]],
    batch_num: int,
    total_batches: int,
    model: str = "",
) -> tuple[Dict[str, Any], int]:
    """多批次模式下单批分析。"""
    comments_text = build_comments_text(
        comments, batch_info=f"Batch {batch_num}/{total_batches}"
    )
    prompt = BATCH_ANALYSIS_PROMPT.format(
        post_context=post_context_str,
        batch_num=batch_num,
        total_batches=total_batches,
        comments_text=comments_text,
    )
    raw, tokens = _call_llm(prompt, model)
    result = _extract_json(raw)
    return result, tokens


def _merge_batch_results(
    post_context_str: str,
    batch_results: List[Dict[str, Any]],
    model: str = "",
) -> tuple[Dict[str, Any], int]:
    """合并多批次分析结果为最终结论。"""
    batch_results_json = json.dumps(batch_results, ensure_ascii=False, indent=2)
    prompt = MERGE_BATCHES_PROMPT.format(
        post_context=post_context_str,
        batch_count=len(batch_results),
        batch_results_json=batch_results_json,
    )
    raw, tokens = _call_llm(prompt, model)
    result = _extract_json(raw)
    return result, tokens


def analyze_post(
    session: Session,
    post_id: int,
    model: str = "",
) -> Optional[PostAnalysis]:
    """
    对指定帖子执行完整的 LLM 分析流水线。
    结果写入 PostAnalysis 表，同时为每个达到阈值的商机创建 Opportunity 记录。

    Args:
        session: 数据库会话
        post_id: 帖子的数据库 ID
        model: LLM 模型名（空字符串使用配置默认值）

    Returns:
        PostAnalysis 记录，失败时返回 None
    """
    from app.services.opportunity_engine import generate_opportunities_from_analysis

    model = model or settings.LLM_MODEL
    logger.info(f"[analyzer] 开始分析帖子 id={post_id}, model={model}")

    post = session.get(Post, post_id)
    if not post:
        logger.error(f"[analyzer] 帖子 id={post_id} 不存在")
        return None

    # 更新状态为分析中
    post.analysis_status = AnalysisStatus.ANALYZING
    session.add(post)
    session.commit()

    # 获取评论（按评分降序）
    comments_db = session.exec(
        select(Comment).where(Comment.post_id == post_id).order_by(Comment.score.desc())
    ).all()

    # 转为字典格式供采样器使用
    comments_raw = [
        {
            "reddit_id": c.reddit_id,
            "body": c.body,
            "score": c.score,
            "author": c.author,
            "depth": c.depth,
            "parent_reddit_id": c.parent_reddit_id,
        }
        for c in comments_db
    ]

    if len(comments_raw) < 3:
        post.analysis_status = AnalysisStatus.SKIPPED
        session.add(post)
        session.commit()
        logger.info(f"[analyzer] 帖子 {post_id} 评论数不足 3 条，跳过分析")
        return None

    # 采样
    sampled = sample_comments(comments_raw, post_reddit_id=post.reddit_id)
    logger.info(f"[analyzer] 采样: {len(comments_raw)} → {len(sampled)} 条评论")

    # 构造帖子上下文
    post_context_str = build_post_context(
        title=post.title,
        selftext=post.selftext or "",
        subreddit=post.subreddit_name,
        score=post.score,
        num_comments=post.num_comments,
    )

    total_tokens = 0
    final_result: Dict[str, Any] = {}

    try:
        batches = split_into_batches(sampled, model=model)

        if len(batches) == 1:
            final_result, tokens = _analyze_single_batch(
                post_context_str, batches[0], len(comments_raw), model
            )
            total_tokens += tokens
        else:
            batch_results = []
            for i, batch in enumerate(batches, 1):
                logger.info(f"[analyzer] 分批分析: {i}/{len(batches)}")
                batch_result, tokens = _analyze_batch(
                    post_context_str, batch, i, len(batches), model
                )
                batch_results.append(batch_result)
                total_tokens += tokens

            final_result, tokens = _merge_batch_results(
                post_context_str, batch_results, model
            )
            total_tokens += tokens

    except Exception as e:
        logger.error(f"[analyzer] 帖子 {post_id} LLM 分析失败: {e}")
        post.analysis_status = AnalysisStatus.FAILED
        session.add(post)
        session.commit()

        # 记录错误信息到已有的 PostAnalysis（如存在）
        existing = session.exec(
            select(PostAnalysis).where(PostAnalysis.post_id == post_id)
        ).first()
        if existing:
            existing.error_message = str(e)[:500]
            existing.updated_at = datetime.now(timezone.utc)
            session.add(existing)
            session.commit()
        return None

    # 提取多商机数组（最多5条）
    opportunities_raw = final_result.get("opportunities", [])
    if not isinstance(opportunities_raw, list):
        opportunities_raw = []

    # 限制最多5个，并按评分降序
    opportunities_raw = sorted(
        opportunities_raw[:settings.MAX_OPPORTUNITIES_PER_POST],
        key=lambda o: int(o.get("opportunity_score", 0)),
        reverse=True,
    )

    max_score = max(
        (int(o.get("opportunity_score", 0)) for o in opportunities_raw),
        default=0,
    )

    # 写入或更新 PostAnalysis
    existing = session.exec(
        select(PostAnalysis).where(PostAnalysis.post_id == post_id)
    ).first()
    analysis = existing or PostAnalysis(post_id=post_id)

    analysis.pain_points = final_result.get("pain_points")
    analysis.willingness_to_pay = final_result.get("willingness_to_pay")
    analysis.tech_feasibility = final_result.get("tech_feasibility")
    analysis.competition = final_result.get("competition")
    analysis.operational_risks = final_result.get("operational_risks")
    analysis.opportunities_raw = opportunities_raw
    analysis.max_opportunity_score = max_score
    analysis.opportunities_count = len(opportunities_raw)
    analysis.model_used = model
    analysis.comments_total = len(comments_raw)
    analysis.comments_sampled = len(sampled)
    analysis.tokens_used = total_tokens
    analysis.error_message = None
    analysis.updated_at = datetime.now(timezone.utc)

    session.add(analysis)

    # 更新 Post 状态
    post.analysis_status = AnalysisStatus.DONE
    session.add(post)
    session.commit()
    session.refresh(analysis)

    logger.info(
        f"[analyzer] 帖子 {post_id} 分析完成: max_score={max_score},"
        f" opportunities={len(opportunities_raw)}, tokens={total_tokens}"
    )

    # 批量生成商机记录（达到阈值的才生成）
    if opportunities_raw:
        try:
            generated = generate_opportunities_from_analysis(session, analysis, post, opportunities_raw)
            logger.info(f"[analyzer] 生成 {len(generated)} 条商机记录 (post_id={post_id})")
        except Exception as e:
            logger.warning(f"[analyzer] 商机生成失败 (post_id={post_id}): {e}")

    return analysis
