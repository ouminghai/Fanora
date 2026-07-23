import pytest

from app.agents.fan_profile import FanProfileAgent, build_fan_profile_graph
from app.schemas.fan_profile import FanProfileRequest


@pytest.mark.asyncio
async def test_fan_profile_graph_scores_and_classifies_a_core_fan() -> None:
    graph = build_fan_profile_graph()

    result = await graph.ainvoke(
        {
            "wallet_address": "0x0000000000000000000000000000000000000001",
            "fan_token_balance": 900,
            "completed_tasks": 12,
            "active_days": 20,
            "referrals": 4,
            "onchain_actions": 8,
        }
    )

    assert result["scores"]["total"] >= 80
    assert result["fan_type"] == "high_value_contributor"
    assert result["analysis_source"] == "rules"
    assert result["badge_eligible"] is True
    assert result["badge_draft"] is not None


@pytest.mark.asyncio
async def test_agent_returns_structured_rule_fallback_without_model() -> None:
    agent = FanProfileAgent()
    result = await agent.analyze(
        FanProfileRequest(
            wallet_address="0x0000000000000000000000000000000000000002",
            fan_token_balance=120,
            completed_tasks=3,
            active_days=4,
        )
    )

    assert result.analysis_source == "rules"
    assert result.badge_eligible is False
    assert result.badge_draft is None


@pytest.mark.asyncio
async def test_graph_prepares_recommends_and_persists_inside_explicit_nodes() -> None:
    persisted: list[dict] = []

    async def prepare(_state):
        return {
            "wallet_address": "0x0000000000000000000000000000000000000004",
            "fan_token_balance": 250,
            "completed_tasks": 5,
            "active_days": 12,
            "referrals": 0,
            "onchain_actions": 2,
            "chain_summary": {},
            "risk_signals": [],
            "task_candidates": [
                {
                    "task_id": "task-1",
                    "title": "粉丝故事任务",
                    "task_type": "content_publish",
                    "reward_fan_tokens": 180,
                    "action_url": "/community/creations?composer=1",
                }
            ],
        }

    async def persist(state):
        persisted.append(dict(state))
        return {}

    graph = build_fan_profile_graph(prepare_data=prepare, persist_result=persist)
    result = await graph.ainvoke(
        {
            "run_id": "profile-run-1",
            "wallet_address": "0x0000000000000000000000000000000000000004",
        }
    )

    assert result["recommended_tasks"][0]["task_id"] == "task-1"
    assert persisted[0]["scores"]["total"] == result["scores"]["total"]
