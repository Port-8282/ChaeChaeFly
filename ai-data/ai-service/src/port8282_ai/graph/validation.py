"""구조 검증 외에 입력·후보·설명 사이의 참조를 검사한다."""

from schemas import EvaluatedCandidate, RunInput
from schemas.agent_io import AnalysisInput, AnalysisResult, EvidenceReference, ReportResult


def validate_candidate(snapshot: RunInput, item: EvaluatedCandidate) -> None:
    call_ids = {call.vessel_call_id for call in snapshot.vessel_calls}
    berth_ids = {berth.berth_id for berth in snapshot.berths}
    if {a.vessel_call_id for a in item.candidate.assignments} != call_ids:
        raise ValueError("후보는 입력의 모든 입항 건을 정확히 한 번 배정해야 합니다.")
    if any(a.berth_id not in berth_ids for a in item.candidate.assignments):
        raise ValueError("후보가 입력에 없는 부두를 참조합니다.")
    for violation in item.constraints.violations:
        if not set(violation.vessel_call_ids) <= call_ids:
            raise ValueError("제약 위반이 입력에 없는 입항 건을 참조합니다.")
        if not set(violation.berth_ids) <= berth_ids:
            raise ValueError("제약 위반이 입력에 없는 부두를 참조합니다.")
    if item.cost is not None:
        contracts = {c.vessel_call_id: c for c in snapshot.contracts}
        if item.cost.currency != snapshot.contracts[0].currency:
            raise ValueError("후보 비용의 통화가 입력 계약과 다릅니다.")
        for cost in item.cost.vessel_costs:
            contract = contracts[cost.vessel_call_id]
            if cost.contract_id != contract.contract_id:
                raise ValueError("비용의 계약 참조가 입력과 다릅니다.")
            if any(
                (line.rule_code, line.rule_version) != (contract.rule_code, contract.rule_version)
                for line in cost.line_items
            ):
                raise ValueError("비용의 계산 규칙이 입력 계약과 다릅니다.")


def validate_evidence(request: AnalysisInput, evidence: tuple[EvidenceReference, ...]) -> None:
    candidates = {
        item.evaluation.candidate.candidate_id: item.evaluation
        for item in request.ranked_candidates
    }
    for ref in evidence:
        if ref.candidate_id not in candidates:
            raise ValueError("근거가 순위에 없는 후보를 참조합니다.")
        if ref.line_item_id is not None:
            cost = candidates[ref.candidate_id].cost
            ids = {line.line_item_id for vessel in cost.vessel_costs for line in vessel.line_items}
            if ref.line_item_id not in ids:
                raise ValueError("근거가 후보에 없는 비용 내역을 참조합니다.")


def validate_analysis_references(request: AnalysisInput, result: AnalysisResult) -> None:
    expected = {item.evaluation.candidate.candidate_id for item in request.ranked_candidates}
    actual = [item.candidate_id for item in result.comparisons]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError("분석은 순위의 모든 후보를 정확히 한 번 설명해야 합니다.")
    for comparison in result.comparisons:
        validate_evidence(request, comparison.evidence)
        if not any(ref.candidate_id == comparison.candidate_id for ref in comparison.evidence):
            raise ValueError("후보 분석에는 해당 후보의 근거가 필요합니다.")


def validate_report_references(request: AnalysisInput, result: ReportResult) -> None:
    expected = {item.evaluation.candidate.candidate_id for item in request.ranked_candidates}
    if len(result.candidate_ids) != len(set(result.candidate_ids)):
        raise ValueError("보고서의 후보 ID가 중복되었습니다.")
    if not set(result.candidate_ids) <= expected:
        raise ValueError("보고서가 순위에 없는 후보를 참조합니다.")
    validate_evidence(request, result.evidence)
    if not {ref.candidate_id for ref in result.evidence} <= set(result.candidate_ids):
        raise ValueError("보고서의 근거와 후보 참조가 일치하지 않습니다.")
