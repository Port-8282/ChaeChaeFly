"""Agent 호출, 검증, 부분 상태 반환. 실행별 데이터는 클로저에 저장하지 않는다."""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Protocol

from pydantic import TypeAdapter

from schemas import RankedCandidate, RunInput
from schemas.agent_io import (
    AnalysisInput,
    AnalysisResult,
    ReportInput,
    ReportResult,
    SchedulingResult,
)
from schemas.execution import CallRecord, RunContext, RunStage, RunStatus, StepError

from .state import GraphState
from .validation import (
    validate_analysis_references,
    validate_candidate,
    validate_report_references,
)


class SchedulingRunner(Protocol):
    def run(self, context: RunContext, snapshot: RunInput) -> SchedulingResult: ...


class AnalysisRunner(Protocol):
    def run(self, context: RunContext, analysis_input: AnalysisInput) -> AnalysisResult: ...


class ReportRunner(Protocol):
    def run(self, context: RunContext, report_input: ReportInput) -> ReportResult: ...


def failure(state: GraphState, stage: RunStage, exc: Exception) -> dict:
    return {
        "stage": stage,
        "status": (
            RunStatus.PARTIAL if stage in (RunStage.ANALYSIS, RunStage.REPORT) else RunStatus.FAILED
        ),
        "errors": state["errors"]
        + (
            StepError(
                stage=stage, code=f"{stage.value}_FAILED", message=f"{type(exc).__name__}: {exc}"
            ),
        ),
    }


def recorded_node(stage: RunStage, operation: Callable[[GraphState], dict]):
    def node(state: GraphState) -> dict:
        started = datetime.now(timezone.utc)
        try:
            update = operation(state)
        except Exception as exc:
            update = failure(state, stage, exc)
        record = CallRecord(
            run_id=state["context"].run_id,
            stage=stage,
            name=stage.value.lower(),
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            succeeded=update.get("status", RunStatus.RUNNING) == RunStatus.RUNNING,
        )
        return {**update, "calls": update.get("calls", state["calls"]) + (record,)}

    return node


def scheduling_node(agent: SchedulingRunner):
    def execute(state: GraphState) -> dict:
        result = SchedulingResult.model_validate(agent.run(state["context"], state["snapshot"]))
        calls = state["calls"] + result.calls
        if any(call.run_id != state["context"].run_id for call in result.calls):
            raise ValueError("호출 기록의 실행 ID가 다릅니다.")
        accepted = []
        for item in result.evaluated_candidates:
            try:
                validate_candidate(state["snapshot"], item)
            except Exception as exc:
                return {
                    **failure(state, RunStage.SCHEDULING, exc),
                    "evaluated_candidates": tuple(accepted),
                    "calls": calls,
                }
            accepted.append(item)
        return {
            "stage": RunStage.SCHEDULING,
            "status": RunStatus.FAILED if result.errors else RunStatus.RUNNING,
            "scheduling_result": result,
            "evaluated_candidates": tuple(accepted),
            "errors": state["errors"] + result.errors,
            "warnings": state["warnings"] + result.warnings,
            "calls": calls,
        }

    return recorded_node(RunStage.SCHEDULING, execute)


def ranking_node(ranker: Callable):
    def execute(state: GraphState) -> dict:
        # 정렬 함수는 내부 코드이며 Agent/LLM이 순위를 결정하지 않는다.
        ranked = ranker(state["evaluated_candidates"])
        ranked = TypeAdapter(tuple[RankedCandidate, ...]).validate_python(ranked)
        expected = {item.candidate.candidate_id: item for item in state["evaluated_candidates"]}
        ids = [item.evaluation.candidate.candidate_id for item in ranked]
        if len(ids) != len(set(ids)):
            raise ValueError("순위 후보가 중복되었습니다.")
        for index, item in enumerate(ranked, start=1):
            if (
                item.rank != index
                or expected.get(item.evaluation.candidate.candidate_id) != item.evaluation
            ):
                raise ValueError("순위 또는 평가 결과가 원본과 다릅니다.")
        feasible_ids = {key for key, item in expected.items() if item.constraints.feasible}
        if set(ids) != feasible_ids:
            raise ValueError("실행 가능한 후보와 순위 결과가 일치하지 않습니다.")
        return {
            "stage": RunStage.RANKING,
            "ranked_candidates": ranked,
            "warnings": state["warnings"] + (() if ranked else ("NO_FEASIBLE_PLAN",)),
        }

    return recorded_node(RunStage.RANKING, execute)


def analysis_node(agent: AnalysisRunner):
    def execute(state: GraphState) -> dict:
        request = AnalysisInput(
            ranked_candidates=state["ranked_candidates"],
            input_as_of=state["snapshot"].environment.data_as_of,
        )
        result = AnalysisResult.model_validate(agent.run(state["context"], request))
        validate_analysis_references(request, result)
        return {"stage": RunStage.ANALYSIS, "analysis": result}

    return recorded_node(RunStage.ANALYSIS, execute)


def report_node(agent: ReportRunner):
    def execute(state: GraphState) -> dict:
        request = ReportInput(
            ranked_candidates=state["ranked_candidates"],
            input_as_of=state["snapshot"].environment.data_as_of,
            analysis=state["analysis"],
        )
        result = ReportResult.model_validate(agent.run(state["context"], request))
        validate_report_references(request, result)
        return {"stage": RunStage.REPORT, "report": result}

    return recorded_node(RunStage.REPORT, execute)


def finalize_node(state: GraphState) -> dict:
    return {
        "stage": RunStage.FINALIZE,
        "status": RunStatus.SUCCEEDED if state["status"] == RunStatus.RUNNING else state["status"],
    }
