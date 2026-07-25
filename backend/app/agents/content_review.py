"""LangGraph workflow for Quest participation review."""

import re
from typing import Any, Required, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from app.core.config import settings
from app.core.logging import logger
from app.schemas.content_review import ContentReviewRequest, ContentReviewResult, LlmContentReview
from app.services.llm import LLMService, llm_service
from app.services.llm.service import LLMUnavailable

_MARKDOWN = re.compile(r"!\[[^\]]*]\([^)]+\)|\[([^\]]+)]\([^)]+\)|[`*_>#~-]")
_URL = re.compile(r"https?://\S+", re.IGNORECASE)
_MEANINGFUL = re.compile(r"[A-Za-z0-9\u3400-\u9fff]")
_REPEATED = re.compile(r"(.{1,4})\1{4,}", re.DOTALL)
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'-]{2,}|[\u3400-\u9fff]{2,4}")
_UNSAFE = re.compile(
    r"(色情|博彩|代开发票|仇恨言论|人肉搜索|暴力威胁|porn|casino|doxx|kill\s+yourself)", re.IGNORECASE
)
_PLACEHOLDER = re.compile(r"^(测试|test|111+|666+)[!！.。\s\d]*$", re.IGNORECASE)
_AD_SPAM = re.compile(
    r"(加微|私信我|推广|代购|返利|空投群|点击链接|薅羊毛|刷单|telegram|whatsapp|airdrop|giveaway|promo|discount)",
    re.IGNORECASE,
)
_STOP_WORDS = {
    "任务",
    "完成",
    "参与",
    "分享",
    "内容",
    "粉丝",
    "社区",
    "一个",
    "一次",
    "这个",
    "那个",
    "可以",
    "进行",
    "the",
    "and",
    "with",
    "from",
    "this",
    "that",
    "task",
    "post",
    "fanora",
}


class ContentReviewState(TypedDict, total=False):
    task_id: Required[str]
    task_title: Required[str]
    task_description: Required[str]
    interaction_prompt: Required[str]
    content_type: Required[str]
    source_id: Required[str]
    title: Required[str]
    body: Required[str]
    category: str | None
    required_tag: str | None
    minimum_length: Required[int]
    normalized_text: Required[str]
    meaningful_length: Required[int]
    tag_present: Required[bool]
    relevant: Required[bool]
    spam: Required[bool]
    meaningful: Required[bool]
    policy_safe: Required[bool]
    quality_score: Required[int]
    decision: Required[str]
    reasons: Required[list[str]]
    ai_generated_likelihood: Required[str]
    source: Required[str]
    degraded: Required[bool]


def _normalize_text(value: str) -> str:
    value = _URL.sub(" ", value)
    value = _MARKDOWN.sub(lambda match: match.group(1) or " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_content(state: ContentReviewState) -> dict[str, Any]:
    normalized = _normalize_text(f"{state.get('title', '')}\n{state['body']}")
    return {
        "normalized_text": normalized,
        "meaningful_length": len(_MEANINGFUL.findall(normalized)),
    }


def _keywords(value: str) -> set[str]:
    normalized = _normalize_text(value)
    keywords = {item.casefold() for item in _WORD.findall(normalized) if item.casefold() not in _STOP_WORDS}
    for sequence in re.findall(r"[\u3400-\u9fff]{2,}", normalized):
        keywords.update(sequence[index : index + 2] for index in range(len(sequence) - 1))
    return keywords


def _semantic_topics(value: str) -> set[str]:
    topics = {
        "music": ("歌", "歌曲", "旋律", "音乐", "歌词", "听到", "收听", "live", "music"),
        "concert_memory": ("现场", "演唱会", "全场", "灯光", "舞台", "瞬间", "记忆", "难忘", "散场"),
        "story": ("故事", "陪伴", "入坑", "第一次", "回忆", "经历", "感受"),
        "creation": ("共创", "创作", "设计", "海报", "图片", "视觉", "灵感"),
        "anniversary": ("周年", "祝福", "纪念", "生日"),
        "fan_expression": (
            "粉丝",
            "喜欢",
            "支持",
            "期待",
            "感动",
            "好听",
            "爱了",
            "泪目",
            "太棒",
            "加油",
            "fan",
            "love",
        ),
    }
    lowered = value.casefold()
    return {topic for topic, terms in topics.items() if any(term in lowered for term in terms)}


def deterministic_checks(state: ContentReviewState) -> dict[str, Any]:
    text = state["normalized_text"]
    meaningful_length = state["meaningful_length"]
    required_tag = (state.get("required_tag") or "").strip()
    tag_present = (
        not required_tag or required_tag.casefold() in f"{state.get('title', '')}\n{state['body']}".casefold()
    )
    compact = re.sub(r"\s+", "", text)
    unique_ratio = len(set(compact.casefold())) / max(len(compact), 1)
    spam = bool(_REPEATED.search(compact)) or bool(_PLACEHOLDER.fullmatch(compact)) or bool(_AD_SPAM.search(text))
    if meaningful_length >= 20 and unique_ratio < 0.16:
        spam = True
    minimum = int(state.get("minimum_length", 4))
    lenient_minimum = min(minimum, 4 if state.get("content_type") in {"reply", "page_action"} else 6)
    meaningful = meaningful_length >= lenient_minimum and not spam
    policy_safe = not bool(_UNSAFE.search(text))

    context = "\n".join([state["task_title"], state.get("task_description", ""), state.get("interaction_prompt", "")])
    context_keywords = _keywords(context)
    content_keywords = _keywords(text)
    context_topics = _semantic_topics(context)
    content_topics = _semantic_topics(text)
    related_topic_pairs = {
        frozenset(("story", "concert_memory")),
        frozenset(("music", "concert_memory")),
        frozenset(("story", "anniversary")),
    }
    semantic_relevant = (
        bool(context_topics & content_topics)
        or "fan_expression" in content_topics
        or any(
            frozenset((context_topic, content_topic)) in related_topic_pairs
            for context_topic in context_topics
            for content_topic in content_topics
        )
    )
    relevant = (
        not context_keywords
        or bool(context_keywords & content_keywords)
        or semantic_relevant
    )

    score = 100
    reasons: list[str] = []
    if not tag_present:
        score -= 8
        reasons.append(f"缺少任务建议标签 {required_tag}")
    if not meaningful:
        score -= 45
        reasons.append("内容缺少可识别的真实表达或主要由占位字符组成")
    if spam:
        score -= 35
        reasons.append("检测到明显灌水或低信息量重复内容")
    if not relevant:
        score -= 25
        reasons.append("内容与任务主题缺少可识别的关联")
    if not policy_safe:
        score -= 100
        reasons.append("内容触发基础安全规则")
    if not reasons:
        reasons.append("标签、有效长度、信息量和主题相关性通过基础检查")

    if not policy_safe or not meaningful or spam:
        decision = "rejected"
    elif not relevant:
        decision = "rejected"
    else:
        decision = "approved"
    return {
        "tag_present": tag_present,
        "relevant": relevant,
        "spam": spam,
        "meaningful": meaningful,
        "policy_safe": policy_safe,
        "quality_score": max(0, min(score, 100)),
        "decision": decision,
        "reasons": reasons,
        "ai_generated_likelihood": "low",
        "source": "rules",
        "degraded": False,
    }


def build_content_review_graph(model_service: LLMService = llm_service) -> CompiledStateGraph:
    async def llm_review(state: ContentReviewState) -> dict[str, Any]:
        hard_rejected = not state["meaningful"] or state["spam"] or not state["policy_safe"] or not state["relevant"]
        if hard_rejected or not model_service.available:
            return {"degraded": model_service.available is False}
        messages = [
            SystemMessage(
                content=(
                    "你是 Fanora Quest 真实参与判定 Agent。只判断用户提交是否与任务主题相关，并体现真实参与、"
                    "观点、情绪或粉丝互动；不评价文采、专业程度、原创性或表达丰富度，不发积分、不修改任务、"
                    "不调用链上工具。允许简短、普通、情绪化、常见粉丝表达，允许有轻微 AI 感。"
                    "不要仅因内容简单、与其他用户表达相似、使用常见粉丝话术、语言不丰富而拒绝。"
                    "只有明显无关、大量无意义字符、与任务无关的复制粘贴、广告垃圾信息、明显刷任务空话才拒绝。"
                    "缺少标签只能作为弱信号；如果内容相关且体现参与，应通过。"
                )
            ),
            HumanMessage(
                content=(
                    f"任务：{state['task_title']}\n任务说明：{state.get('task_description', '')}\n"
                    f"互动提示：{state.get('interaction_prompt', '')}\n内容类型：{state['content_type']}\n"
                    f"基础检查：tag={state['tag_present']}, relevant={state['relevant']}, "
                    f"meaningful={state['meaningful']}, spam={state['spam']}\n"
                    f"用户内容：\n{state.get('title', '')}\n{state['body']}"
                )
            ),
        ]
        try:
            review = await model_service.call_structured(messages, LlmContentReview)
            decision = review.decision
            if not review.policy_safe or review.spam or not review.meaningful or not review.relevant:
                decision = "rejected"
            return {
                "decision": decision,
                "quality_score": review.quality_score,
                "relevant": review.relevant,
                "spam": review.spam,
                "meaningful": review.meaningful,
                "policy_safe": review.policy_safe,
                "ai_generated_likelihood": review.ai_generated_likelihood,
                "reasons": review.reasons,
                "source": "llm",
                "degraded": False,
            }
        except (LLMUnavailable, ValidationError, KeyError, TypeError, ValueError):
            logger.exception("content_review_llm_fallback", task_id=state["task_id"], source_id=state["source_id"])
            return {"degraded": True}

    def validate_decision(state: ContentReviewState) -> dict[str, Any]:
        decision = state["decision"]
        reasons = list(state["reasons"])
        if not state["meaningful"] or state["spam"] or not state["policy_safe"]:
            decision = "rejected"
        if decision == "approved" and not state["relevant"]:
            decision = "rejected"
            reasons.append("内容与任务主题明显无关")
        return {"decision": decision, "reasons": list(dict.fromkeys(reasons))[:8]}

    workflow = StateGraph(ContentReviewState)
    workflow.add_node("normalize_content", normalize_content)
    workflow.add_node("deterministic_checks", deterministic_checks)
    workflow.add_node("llm_review", llm_review)
    workflow.add_node("validate_decision", validate_decision)
    workflow.add_edge(START, "normalize_content")
    workflow.add_edge("normalize_content", "deterministic_checks")
    workflow.add_edge("deterministic_checks", "llm_review")
    workflow.add_edge("llm_review", "validate_decision")
    workflow.add_edge("validate_decision", END)
    return workflow.compile()


class ContentReviewAgent:
    def __init__(self, model_service: LLMService = llm_service) -> None:
        self.model_service = model_service
        self._graph = build_content_review_graph(model_service)

    async def review(self, request: ContentReviewRequest) -> ContentReviewResult:
        result = await self._graph.ainvoke(request.model_dump())
        source = result.get("source", "rules")
        return ContentReviewResult(
            decision=result["decision"],
            quality_score=result["quality_score"],
            tag_present=result["tag_present"],
            relevant=result["relevant"],
            spam=result["spam"],
            meaningful=result["meaningful"],
            policy_safe=result["policy_safe"],
            ai_generated_likelihood=result.get("ai_generated_likelihood", "low"),
            reasons=result["reasons"],
            source=source,
            degraded=bool(result.get("degraded")),
            model_id=settings.openai_model if source == "llm" else "rules",
        )


content_review_agent = ContentReviewAgent()
