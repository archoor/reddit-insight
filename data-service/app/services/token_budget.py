"""
Token 预算管理：精确计算评论 token 消耗，动态决定分批大小。
使用 tiktoken 进行 token 估算（对 GPT-4 系列精确，其他模型近似）。
"""
import logging
from typing import Any, Dict, List

import tiktoken

from app.config import settings

logger = logging.getLogger(__name__)

# 编码器缓存，避免重复初始化
_ENCODING_CACHE: Dict[str, tiktoken.Encoding] = {}


def _get_encoding(model: str) -> tiktoken.Encoding:
    """获取或缓存指定模型的 tiktoken 编码器。"""
    if model not in _ENCODING_CACHE:
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            # 非 OpenAI 模型（如 Claude / DeepSeek / Gemini）使用 cl100k_base 近似
            enc = tiktoken.get_encoding("cl100k_base")
        _ENCODING_CACHE[model] = enc
    return _ENCODING_CACHE[model]


def estimate_tokens(text: str, model: str = "") -> int:
    """估算一段文本的 token 数量。"""
    enc = _get_encoding(model or settings.LLM_MODEL)
    return len(enc.encode(text))


def estimate_comment_tokens(comment: Dict[str, Any], model: str = "") -> int:
    """估算单条评论的 token 数。"""
    text = f"[score:{comment.get('score', 0)}] {comment.get('body', '')}\n"
    return estimate_tokens(text, model)


def split_into_batches(
    comments: List[Dict[str, Any]],
    system_prompt_tokens: int = 800,
    post_context_tokens: int = 1000,
    output_tokens: int = 4000,
    model: str = "",
) -> List[List[Dict[str, Any]]]:
    """
    将评论列表按 token 预算切分为多个批次。
    每批使用的 token 不超过 MAX_INPUT_TOKENS 中可用于评论的部分。

    Args:
        comments: 已采样的评论列表
        system_prompt_tokens: System Prompt 预计占用 token
        post_context_tokens: 帖子标题+正文预计占用 token
        output_tokens: 输出预留 token（多商机输出比单商机稍大）
        model: LLM 模型名（影响 token 计算）

    Returns:
        批次列表，每个批次是评论子列表
    """
    available = (
        settings.MAX_INPUT_TOKENS
        - system_prompt_tokens
        - post_context_tokens
        - output_tokens
    )
    # 保留 15% 安全余量
    available = int(available * 0.85)

    if available <= 0:
        logger.warning("[token_budget] 可用 token 不足，强制使用单批次")
        return [comments[:settings.MAX_COMMENTS_PER_BATCH]]

    batches: List[List[Dict[str, Any]]] = []
    current_batch: List[Dict[str, Any]] = []
    current_tokens = 0

    for comment in comments:
        ct = estimate_comment_tokens(comment, model)
        if current_tokens + ct > available and current_batch:
            batches.append(current_batch)
            current_batch = [comment]
            current_tokens = ct
        else:
            current_batch.append(comment)
            current_tokens += ct

        # 每批最多 MAX_COMMENTS_PER_BATCH 条
        if len(current_batch) >= settings.MAX_COMMENTS_PER_BATCH:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

    if current_batch:
        batches.append(current_batch)

    logger.info(
        f"[token_budget] {len(comments)} 条评论分为 {len(batches)} 批"
        f"，平均每批 {len(comments) // max(len(batches), 1)} 条"
    )
    return batches
