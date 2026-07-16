from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class FanProfileState(TypedDict, total=False):
    wallet_address: str
    completed_tasks: int
    active_days: int
    referrals: int
    score: int
    fan_type: str


def calculate_score(state: FanProfileState) -> FanProfileState:
    score = (
        state.get("completed_tasks", 0) * 10
        + state.get("active_days", 0) * 2
        + state.get("referrals", 0) * 15
    )
    return {"score": min(score, 100)}


def classify_fan(state: FanProfileState) -> FanProfileState:
    score = state.get("score", 0)
    if score >= 80:
        fan_type = "core_contributor"
    elif state.get("referrals", 0) >= 3:
        fan_type = "advocate"
    elif state.get("active_days", 0) >= 10:
        fan_type = "loyal_fan"
    else:
        fan_type = "emerging_fan"
    return {"fan_type": fan_type}


def build_fan_profile_graph():
    """Build the internal workflow behind the fan-profile interface."""
    graph = StateGraph(FanProfileState)
    graph.add_node("calculate_score", calculate_score)
    graph.add_node("classify_fan", classify_fan)
    graph.add_edge(START, "calculate_score")
    graph.add_edge("calculate_score", "classify_fan")
    graph.add_edge("classify_fan", END)
    return graph.compile()

