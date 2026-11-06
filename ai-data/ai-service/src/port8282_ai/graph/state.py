"""실행마다 새로 생성하는 그래프 내부 상태."""

from typing import TypedDict

from schemas import EvaluatedCandidate, RankedCandidate, RunInput
from schemas.agent_io import AnalysisResult, ReportResult, SchedulingResult
from schemas.execution import CallRecord, RunContext, RunStage, RunStatus, StepError


class GraphState(TypedDict):
    context: RunContext
    snapshot: RunInput
    stage: RunStage
    status: RunStatus
    evaluated_candidates: tuple[EvaluatedCandidate, ...]
    scheduling_result: SchedulingResult | None
    ranked_candidates: tuple[RankedCandidate, ...]
    analysis: AnalysisResult | None
    report: ReportResult | None
    errors: tuple[StepError, ...]
    warnings: tuple[str, ...]
    calls: tuple[CallRecord, ...]


def create_initial_state(context: RunContext, snapshot: RunInput) -> GraphState:
    return GraphState(
        context=context,
        snapshot=snapshot,
        stage=RunStage.INPUT,
        status=RunStatus.RUNNING,
        evaluated_candidates=(),
        scheduling_result=None,
        ranked_candidates=(),
        analysis=None,
        report=None,
        errors=(),
        warnings=(),
        calls=(),
    )
