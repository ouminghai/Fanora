from app.agents.fan_profile import build_fan_profile_graph


def test_fan_profile_graph_scores_and_classifies_a_fan() -> None:
    graph = build_fan_profile_graph()

    result = graph.invoke(
        {
            "wallet_address": "0x0000000000000000000000000000000000000001",
            "completed_tasks": 5,
            "active_days": 10,
            "referrals": 1,
        }
    )

    assert result["score"] == 85
    assert result["fan_type"] == "core_contributor"

