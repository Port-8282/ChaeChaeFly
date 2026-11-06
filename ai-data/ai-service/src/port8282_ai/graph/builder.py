"""주입된 Agent를 고정 분기로 연결하고 재사용 가능한 그래프를 컴파일한다."""

from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from port8282_ai.ranking import rank_candidates
from schemas.execution import RunStatus

from .nodes import (
    AnalysisRunner,
    ReportRunner,
    SchedulingRunner,
    analysis_node,
    finalize_node,
    ranking_node,
    report_node,
    scheduling_node,
)
from .state import GraphState


def build_graph(
    scheduling: SchedulingRunner,
    analysis: AnalysisRunner,
    report: ReportRunner,
    *,
    ranker: Callable = rank_candidates,
):
    graph = StateGraph(GraphState)
    graph.add_node("scheduling", scheduling_node(scheduling))
    graph.add_node("ranking", ranking_node(ranker))
    graph.add_node("analysis", analysis_node(analysis))
    graph.add_node("report", report_node(report))
    graph.add_node("finalize", finalize_node)
    graph.add_edge(START, "scheduling")
    graph.add_conditional_edges(
        "scheduling",
        lambda state: "ranking" if state["status"] == RunStatus.RUNNING else "finalize",
        {"ranking": "ranking", "finalize": "finalize"},
    )
    graph.add_conditional_edges(
        "ranking",
        lambda state: (
            "analysis"
            if state["status"] == RunStatus.RUNNING and state["ranked_candidates"]
            else "finalize"
        ),
        {"analysis": "analysis", "finalize": "finalize"},
    )
    graph.add_conditional_edges(
        "analysis",
        lambda state: "report" if state["status"] == RunStatus.RUNNING else "finalize",
        {"report": "report", "finalize": "finalize"},
    )
    graph.add_edge("report", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()
