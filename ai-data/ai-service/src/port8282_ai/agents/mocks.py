"""외부 API나 실제 계산 없이 연결을 검증하는 모의 어댑터."""

from schemas import EvaluatedCandidate, RunInput
from schemas.agent_io import (
    AnalysisInput,
    AnalysisResult,
    CandidateAnalysis,
    EvidenceReference,
    ReportInput,
    ReportResult,
)
from schemas.execution import RunContext

from .scheduling import EvaluationTool


def mock_evaluation_tool(evaluation: EvaluatedCandidate | dict) -> EvaluationTool:
    # 호출자의 객체와 분리하고, 호출마다 새 검증 결과를 반환한다.
    payload = EvaluatedCandidate.model_validate(evaluation).model_dump()

    def evaluate(context: RunContext, snapshot: RunInput) -> EvaluatedCandidate:
        return EvaluatedCandidate.model_validate(payload)

    return evaluate


def mock_analysis_model(context: RunContext, request: AnalysisInput) -> AnalysisResult:
    return AnalysisResult(
        comparisons=tuple(
            CandidateAnalysis(
                candidate_id=item.evaluation.candidate.candidate_id,
                explanation=(
                    f"모의 분석: {item.rank}위, 총비용 "
                    f"{item.evaluation.cost.total_amount} {item.evaluation.cost.currency}"
                ),
                evidence=(EvidenceReference(candidate_id=item.evaluation.candidate.candidate_id),),
            )
            for item in request.ranked_candidates
        )
    )


def mock_report_model(context: RunContext, request: ReportInput) -> ReportResult:
    ids = tuple(item.evaluation.candidate.candidate_id for item in request.ranked_candidates)
    return ReportResult(
        content="모의 보고서\n"
        + "\n".join(item.explanation for item in request.analysis.comparisons),
        candidate_ids=ids,
        evidence=tuple(EvidenceReference(candidate_id=value) for value in ids),
    )
