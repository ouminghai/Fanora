import pytest

from app.agents.fan_profile import FanProfileAgent, build_fan_profile_graph
from app.schemas.fan_profile import FanProfileRequest


@pytest.mark.asyncio
async def test_fan_profile_graph_scores_and_classifies_a_core_fan() -> None:
    graph = build_fan_profile_graph()

    result = await graph.ainvoke(
        {
            "wallet_address": "0x0000000000000000000000000000000000000001",
            "community_id": "fanora",
            "fan_token_balance": 900,
            "completed_tasks": 12,
            "active_days": 20,
            "referrals": 4,
            "onchain_actions": 8,
        }
    )

    assert result["scores"]["total"] >= 80
    assert result["fan_type"] == "core_contributor"
    assert result["analysis_source"] == "rules"
    assert result["badge_eligible"] is True
    assert result["badge_draft"] is not None


@pytest.mark.asyncio
async def test_agent_returns_structured_rule_fallback_without_model() -> None:
    agent = FanProfileAgent()
    result = await agent.analyze(
        FanProfileRequest(
            wallet_address="0x0000000000000000000000000000000000000002",
            community_id="fanora",
            fan_token_balance=120,
            completed_tasks=3,
            active_days=4,
        )
    )

    assert result.analysis_source == "rules"
    assert result.badge_eligible is False
    assert result.badge_draft is None
