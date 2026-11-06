"""LangGraph State 없이 Agent를 호출하기 위한 데이터 계약."""

from enum import StrEnum

from pydantic import Field, model_validator

from .candidates import EvaluatedCandidate, RankedCandidate
from .common import EntityId, SchemaModel, UtcDateTime
from .execution import CallRecord, StepError


class SearchTermination(StrEnum):
    COMPLETED = "COMPLETED"
    MAX_ITERATIONS = "MAX_ITERATIONS"
    TIME_LIMIT = "TIME_LIMIT"
    FAILED = "FAILED"


class SchedulingResult(SchemaModel):
    evaluated_candidates: tuple[EvaluatedCandidate, ...] = ()
    termination_reason: SearchTermination = SearchTermination.COMPLETED
    errors: tuple[StepError, ...] = ()
    warnings: tuple[str, ...] = ()
    calls: tuple[CallRecord, ...] = ()

    @model_validator(mode="after")
    def validate_failure(self):
        if (self.termination_reason == SearchTermination.FAILED) != bool(self.errors):
            raise ValueError("FAILED 종료에는 오류가 필요하며 정상 종료에는 오류가 없어야 합니다.")
        ids = [item.candidate.candidate_id for item in self.evaluated_candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("후보 ID가 중복되었습니다.")
        return self


class EvidenceReference(SchemaModel):
    candidate_id: EntityId
    # None이면 후보 전체 계산 결과, 값이 있으면 해당 비용 내역을 참조한다.
    line_item_id: EntityId | None = None


class CandidateAnalysis(SchemaModel):
    candidate_id: EntityId
    explanation: str = Field(min_length=1)
    evidence: tuple[EvidenceReference, ...] = Field(min_length=1)


class AnalysisInput(SchemaModel):
    ranked_candidates: tuple[RankedCandidate, ...] = Field(min_length=1)
    input_as_of: UtcDateTime


class AnalysisResult(SchemaModel):
    comparisons: tuple[CandidateAnalysis, ...] = Field(min_length=1)


class ReportInput(AnalysisInput):
    analysis: AnalysisResult


class ReportResult(SchemaModel):
    content: str = Field(min_length=1)
    candidate_ids: tuple[EntityId, ...] = Field(min_length=1)
    evidence: tuple[EvidenceReference, ...] = Field(min_length=1)
