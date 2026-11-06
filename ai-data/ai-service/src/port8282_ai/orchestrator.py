"""입력 검증과 실행 상태 초기화, 그래프 호출, 최종 결과 변환."""

from datetime import datetime, timezone
from uuid import uuid4

from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from schemas import RunInput
from schemas.execution import RunContext, RunResult, RunStage, RunStatus, StepError

from .graph.state import create_initial_state


class Orchestrator:
    def __init__(self, graph: CompiledStateGraph):
        self._graph = graph

    def run(self, payload: RunInput | dict) -> RunResult:
        context = RunContext(run_id=str(uuid4()), started_at=datetime.now(timezone.utc))
        try:
            snapshot = RunInput.model_validate(payload)
        except ValidationError as exc:
            return RunResult(
                context=context,
                stage=RunStage.INPUT,
                status=RunStatus.FAILED,
                errors=(StepError(stage=RunStage.INPUT, code="INVALID_INPUT", message=str(exc)),),
            )
        state = self._graph.invoke(create_initial_state(context, snapshot))
        return RunResult.model_validate(
            {key: value for key, value in state.items() if key != "snapshot"}
        )
