"""실행 상태와 추적 정보. Agent 결과의 전방 참조는 schemas 패키지에서 연결한다."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import Field

from .candidates import EvaluatedCandidate, RankedCandidate
from .common import EntityId, SchemaModel, UtcDateTime

if TYPE_CHECKING:
    from .agent_io import AnalysisResult, ReportResult, SchedulingResult


class RunStage(StrEnum):
    INPUT = "INPUT"
    SCHEDULING = "SCHEDULING"
    RANKING = "RANKING"
    ANALYSIS = "ANALYSIS"
    REPORT = "REPORT"
    FINALIZE = "FINALIZE"


class RunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class RunContext(SchemaModel):
    run_id: EntityId
    started_at: UtcDateTime


class StepError(SchemaModel):
    stage: RunStage
    code: EntityId
    message: str = Field(min_length=1)


class CallRecord(SchemaModel):
    run_id: EntityId
    stage: RunStage
    name: EntityId
    started_at: UtcDateTime
    finished_at: UtcDateTime
    succeeded: bool = Field(strict=True)


class RunResult(SchemaModel):
    context: RunContext
    stage: RunStage
    status: RunStatus
    evaluated_candidates: tuple[EvaluatedCandidate, ...] = ()
    scheduling_result: SchedulingResult | None = None
    ranked_candidates: tuple[RankedCandidate, ...] = ()
    analysis: AnalysisResult | None = None
    report: ReportResult | None = None
    errors: tuple[StepError, ...] = ()
    warnings: tuple[str, ...] = ()
    calls: tuple[CallRecord, ...] = ()
