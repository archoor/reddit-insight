"""
评论智能采样引擎：四层策略确保在 LLM token 限制内提取最有价值的评论。

采样策略：
  Layer 1: 预过滤（规则引擎，零成本）—— 去除无价值评论
  Layer 2: 多策略采样（算法，零成本）—— 按比例从不同维度选取代表性评论
  Layer 3: 动态分批（Token 预算控制）—— 确保不超出 LLM 上下文
  Layer 4: 结果合并由 analyzer.py 完成
"""
import logging
import random
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# 采样策略权重分配
SAMPLING_WEIGHTS = {
    "top_score": 0.30,      # 高赞评论：社区最认可的共识观点
    "long_text": 0.20,      # 长文评论：有深度的分析和故事
    "top_level": 0.20,      # 一级评论：直接回应帖子主题
    "controversial": 0.15,  # 有回复的评论：引发讨论的内容
    "random": 0.15,         # 随机采样：防止偏见，保证多样性
}

# 预过滤规则常量
MIN_BODY_LENGTH = 15            # 最短有效评论字符数
MIN_SCORE = -2                  # 最低接受评分
DELETED_MARKERS = {"[deleted]", "[removed]", ""}


def _is_valid_comment(comment: Dict[str, Any]) -> bool:
    """Layer 1: 判断评论是否有分析价值。"""
    body = (comment.get("body") or "").strip()
    if body in DELETED_MARKERS:
        return False
    if len(body) < MIN_BODY_LENGTH:
        return False
    if int(comment.get("score", 0)) < MIN_SCORE:
        return False
    return True


def _is_top_level(comment: Dict[str, Any], post_reddit_id: str = "") -> bool:
    """判断是否为一级评论（直接回复帖子）。"""
    parent = comment.get("parent_reddit_id") or ""
    if not parent:
        return comment.get("depth", 0) == 0
    return parent.startswith("t3_") or parent == post_reddit_id


def pre_filter(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Layer 1: 预过滤，去除无价值评论。"""
    filtered = [c for c in comments if _is_valid_comment(c)]
    logger.info(f"[sampler] 预过滤: {len(comments)} → {len(filtered)} 条")
    return filtered


def smart_sample(
    comments: List[Dict[str, Any]],
    target_count: int = 100,
    post_reddit_id: str = "",
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Layer 2: 多策略混合采样，确保覆盖各类有价值的评论。

    Args:
        comments: 预过滤后的评论列表
        target_count: 目标采样数量
        post_reddit_id: 帖子 reddit_id，用于识别一级评论
        seed: 随机种子，保证可重复性

    Returns:
        采样结果，带 sample_reason 标记
    """
    if not comments:
        return []

    if len(comments) <= target_count:
        for c in comments:
            c["sample_reason"] = "all"
        return comments

    random.seed(seed)
    selected_ids: set = set()
    result: List[Dict[str, Any]] = []

    def _add_comments(candidates: List[Dict[str, Any]], quota: int, reason: str) -> int:
        """从候选列表中按配额添加评论，返回实际添加数量。"""
        added = 0
        for c in candidates:
            cid = c.get("reddit_id") or id(c)
            if cid in selected_ids:
                continue
            if added >= quota:
                break
            c["sample_reason"] = reason
            selected_ids.add(cid)
            result.append(c)
            added += 1
        return added

    # 策略 1: 高赞评论（按 score 降序）
    top_score = sorted(comments, key=lambda c: -int(c.get("score", 0)))
    quota_top = int(target_count * SAMPLING_WEIGHTS["top_score"])
    _add_comments(top_score, quota_top, "top_score")

    # 策略 2: 长文评论（按 body 长度降序）
    long_text = sorted(comments, key=lambda c: -len(c.get("body", "")))
    quota_long = int(target_count * SAMPLING_WEIGHTS["long_text"])
    _add_comments(long_text, quota_long, "long_text")

    # 策略 3: 一级评论（直接回复帖子的）
    top_level = [c for c in comments if _is_top_level(c, post_reddit_id)]
    random.shuffle(top_level)
    quota_top_level = int(target_count * SAMPLING_WEIGHTS["top_level"])
    _add_comments(top_level, quota_top_level, "top_level")

    # 策略 4: 有正分的评论（社区认可，引发讨论的内容）
    controversial = [c for c in comments if int(c.get("score", 0)) > 0]
    random.shuffle(controversial)
    quota_controversial = int(target_count * SAMPLING_WEIGHTS["controversial"])
    _add_comments(controversial, quota_controversial, "controversial")

    # 策略 5: 随机补充
    remaining = [c for c in comments if (c.get("reddit_id") or id(c)) not in selected_ids]
    random.shuffle(remaining)
    needed = target_count - len(result)
    _add_comments(remaining, needed, "random")

    logger.info(
        f"[sampler] 多策略采样: {len(comments)} → {len(result)} 条"
        f" (top_score:{quota_top}, long_text:{quota_long},"
        f" top_level:{quota_top_level}, controversial:{quota_controversial})"
    )
    return result


def sample_comments(
    comments: List[Dict[str, Any]],
    post_reddit_id: str = "",
    target_count: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    对外暴露的采样入口，完成 Layer1 + Layer2。

    Args:
        comments: 原始评论列表（字典格式）
        post_reddit_id: 帖子 reddit_id
        target_count: 目标采样数，默认取配置 SAMPLE_TARGET_COUNT

    Returns:
        采样后带 sample_reason 的评论列表
    """
    if target_count is None:
        target_count = settings.SAMPLE_TARGET_COUNT

    filtered = pre_filter(comments)
    sampled = smart_sample(filtered, target_count=target_count, post_reddit_id=post_reddit_id)
    return sampled
