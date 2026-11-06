"""주입한 평가 Tool을 순차 호출한다. 실제 탐색 알고리즘은 Tool로 교체한다."""

from collections.abc import Callable, Sequence
from datetime import datetime, timezone

from schemas import EvaluatedCandidate, RunInput
from schemas.agent_io import SchedulingResult, SearchTermination
from schemas.execution import CallRecord, RunContext, RunStage, StepError

EvaluationTool = Callable[[RunContext, RunInput], EvaluatedCandidate | dict]


class SchedulingAgent:
    def __init__(self, tools: Sequence[EvaluationTool]):
        self._tools = tuple(tools)

    def run(self, context: RunContext, snapshot: RunInput) -> SchedulingResult:
        candidates = []
        calls = []
        for index, tool in enumerate(self._tools):
            started = datetime.now(timezone.utc)
            error = None
            try:
                candidate = EvaluatedCandidate.model_validate(tool(context, snapshot))
                if any(
                    item.candidate.candidate_id == candidate.candidate.candidate_id
                    for item in candidates
                ):
                    raise ValueError("후보 ID가 중복되었습니다.")
                candidates.append(candidate)
            except Exception as exc:
                error = StepError(
                    stage=RunStage.SCHEDULING,
                    code="TOOL_FAILED",
                    message=f"{type(exc).__name__}: {exc}",
                )
            calls.append(
                CallRecord(
                    run_id=context.run_id,
                    stage=RunStage.SCHEDULING,
                    name=f"evaluation_tool_{index}",
                    started_at=started,
                    finished_at=datetime.now(timezone.utc),
                    succeeded=error is None,
                )
            )
            if error is not None:
                return SchedulingResult(
                    evaluated_candidates=tuple(candidates),
                    termination_reason=SearchTermination.FAILED,
                    errors=(error,),
                    calls=tuple(calls),
                )
        return SchedulingResult(evaluated_candidates=tuple(candidates), calls=tuple(calls))
