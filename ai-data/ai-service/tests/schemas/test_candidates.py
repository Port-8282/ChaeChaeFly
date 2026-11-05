"""후보 배정, 시간표, 제약·비용 및 단계 간 일관성 검증."""

from copy import deepcopy
from decimal import Decimal

import pytest
from pydantic import ValidationError

from schemas import (
    ConstraintResult,
    ConstraintViolation,
    CostLineItem,
    CostResult,
    EvaluatedCandidate,
    PlanCandidate,
    RankedCandidate,
    SimulationResult,
    VesselCost,
    VesselTimeline,
)


def test_candidate_allows_same_sequence_at_different_berths(evaluation_payload):
    candidate = PlanCandidate.model_validate(evaluation_payload["candidate"])
    assert [item.sequence for item in candidate.assignments] == [1, 1]


def test_candidate_allows_nonconsecutive_sequence(evaluation_payload):
    payload = evaluation_payload["candidate"]
    payload["assignments"][1].update(berth_id="berth-1", sequence=3)
    assert PlanCandidate.model_validate(payload).assignments[1].sequence == 3


def test_candidate_rejects_duplicate_call(evaluation_payload):
    payload = evaluation_payload["candidate"]
    payload["assignments"][1]["vessel_call_id"] = "call-1"
    with pytest.raises(ValidationError, match="같은 입항 건을 중복"):
        PlanCandidate.model_validate(payload)


def test_candidate_rejects_duplicate_berth_sequence(evaluation_payload):
    payload = evaluation_payload["candidate"]
    payload["assignments"][1]["berth_id"] = "berth-1"
    with pytest.raises(ValidationError, match="접안 순서는 중복"):
        PlanCandidate.model_validate(payload)


@pytest.mark.parametrize(
    "section,field,model",
    [
        ("candidate", "assignments", PlanCandidate),
        ("simulation", "timelines", SimulationResult),
        ("cost", "vessel_costs", CostResult),
    ],
)
def test_results_require_nonempty_collections(evaluation_payload, section, field, model):
    payload = evaluation_payload[section]
    payload[field] = []
    with pytest.raises(ValidationError) as error:
        model.model_validate(payload)
    assert error.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize(
    "field,value",
    [
        ("berthing_at", "2026-11-05T11:00:00+09:00"),
        ("work_started_at", "2026-11-05T13:00:00+09:00"),
        ("work_completed_at", "2026-11-05T14:00:00+09:00"),
    ],
)
def test_timeline_rejects_each_reversed_boundary(timeline_payload, field, value):
    timeline_payload[field] = value
    with pytest.raises(ValidationError, match="시각의 순서"):
        VesselTimeline.model_validate(timeline_payload)


def test_timeline_allows_all_equal_times(timeline_payload):
    for field in ("work_started_at", "work_completed_at", "departed_at"):
        timeline_payload[field] = timeline_payload["berthing_at"]
    assert VesselTimeline.model_validate(timeline_payload).interruptions == ()


@pytest.mark.parametrize(
    "bounds,allowed,message",
    [
        ([(10, 11), (11, 12)], True, None),
        ([(11, 12), (10, 11)], True, None),
        ([(9, 11)], False, "작업 시간 안"),
        ([(11, 13)], False, "작업 시간 안"),
        ([(10, 12), (11, 12)], False, "겹칩니다"),
    ],
)
def test_timeline_interruptions(timeline_payload, bounds, allowed, message):
    timeline_payload["interruptions"] = [
        {
            "start_at": f"2026-11-05T{start:02d}:00:00+09:00",
            "end_at": f"2026-11-05T{end:02d}:00:00+09:00",
        }
        for start, end in bounds
    ]
    if allowed:
        value = VesselTimeline.model_validate(timeline_payload)
        # 정렬은 겹침 확인용이며 저장되는 구간의 순서를 바꾸지 않아야 한다.
        assert [w.start_at.hour + 9 for w in value.interruptions] == [s for s, _ in bounds]
    else:
        with pytest.raises(ValidationError, match=message):
            VesselTimeline.model_validate(timeline_payload)


def test_timeline_rejects_negative_waiting_time(timeline_payload):
    timeline_payload["waiting_seconds"] = -1
    with pytest.raises(ValidationError) as error:
        VesselTimeline.model_validate(timeline_payload)
    assert error.value.errors()[0]["loc"] == ("waiting_seconds",)


@pytest.mark.parametrize("feasible,has_violation", [(True, False), (False, True)])
def test_constraint_result_accepts_consistent_status(feasible, has_violation):
    violations = [{"code": "LIMIT", "message": "한도 초과"}] if has_violation else []
    result = ConstraintResult(
        candidate_id="candidate-1", feasible=feasible, violations=violations
    )
    assert result.feasible is feasible
    assert bool(result.violations) is has_violation


@pytest.mark.parametrize("feasible,has_violation", [(True, True), (False, False)])
def test_constraint_result_rejects_inconsistent_status(feasible, has_violation):
    violations = [{"code": "LIMIT", "message": "한도 초과"}] if has_violation else []
    with pytest.raises(ValidationError, match="위반 목록이 일치"):
        ConstraintResult(candidate_id="candidate-1", feasible=feasible, violations=violations)


@pytest.mark.parametrize("value", [1, 0, "true", "false"])
def test_constraint_status_requires_boolean(value):
    with pytest.raises(ValidationError) as error:
        ConstraintResult(candidate_id="candidate-1", feasible=value)
    assert error.value.errors()[0]["loc"] == ("feasible",)


def test_violation_defaults_and_nonempty_message():
    value = ConstraintViolation(code="LIMIT", message="한도 초과")
    assert value.vessel_call_ids == value.berth_ids == ()
    with pytest.raises(ValidationError):
        ConstraintViolation(code="LIMIT", message="")


def test_cost_line_requires_description(evaluation_payload):
    payload = evaluation_payload["cost"]["vessel_costs"][0]["line_items"][0]
    payload["description"] = ""
    with pytest.raises(ValidationError):
        CostLineItem.model_validate(payload)


def test_vessel_cost_rejects_duplicate_line_ids(evaluation_payload):
    payload = evaluation_payload["cost"]["vessel_costs"][0]
    payload["line_items"].append(deepcopy(payload["line_items"][0]))
    payload["total_amount"] = "0.20"
    with pytest.raises(ValidationError, match="계산 내역 ID가 중복"):
        VesselCost.model_validate(payload)


def test_vessel_cost_sums_decimal_line_items(evaluation_payload):
    payload = evaluation_payload["cost"]["vessel_costs"][0]
    second = deepcopy(payload["line_items"][0])
    second.update(line_item_id="another-line", amount="0.20")
    payload["line_items"].append(second)
    payload["total_amount"] = "0.30"
    assert VesselCost.model_validate(payload).total_amount == Decimal("0.30")


@pytest.mark.parametrize("total,allowed", [("0", True), ("0.01", False)])
def test_empty_cost_lines_require_zero_total(evaluation_payload, total, allowed):
    payload = evaluation_payload["cost"]["vessel_costs"][0]
    payload.update(line_items=[], total_amount=total)
    if allowed:
        value = VesselCost.model_validate(payload)
        assert value.total_amount == 0
        assert value.line_items == ()
    else:
        with pytest.raises(ValidationError, match="계산 내역의 합계"):
            VesselCost.model_validate(payload)


@pytest.mark.parametrize(
    "section,message", [("vessel", "계산 내역의 합계"), ("candidate", "선박별 비용의 합계")]
)
def test_cost_rejects_incorrect_total(evaluation_payload, section, message):
    payload = evaluation_payload["cost"]
    model = CostResult
    if section == "vessel":
        payload = payload["vessel_costs"][0]
        model = VesselCost
    payload["total_amount"] = "999"
    with pytest.raises(ValidationError, match=message):
        model.model_validate(payload)


def test_cost_rejects_duplicate_calls(evaluation_payload):
    payload = evaluation_payload["cost"]
    payload["vessel_costs"][1]["vessel_call_id"] = "call-1"
    with pytest.raises(ValidationError, match="입항 건별 비용이 중복"):
        CostResult.model_validate(payload)


@pytest.mark.parametrize("section", ["simulation", "constraints", "cost"])
def test_evaluation_rejects_mismatched_candidate_id(evaluation_payload, section):
    evaluation_payload[section]["candidate_id"] = "another-candidate"
    with pytest.raises(ValidationError, match="후보 ID가 일치"):
        EvaluatedCandidate.model_validate(evaluation_payload)


def test_feasible_evaluation_requires_cost(evaluation_payload):
    evaluation_payload["cost"] = None
    with pytest.raises(ValidationError, match="실행 가능한 후보에만 비용"):
        EvaluatedCandidate.model_validate(evaluation_payload)


def test_infeasible_evaluation_rejects_cost(infeasible_payload, evaluation_payload):
    infeasible_payload["cost"] = evaluation_payload["cost"]
    with pytest.raises(ValidationError, match="실행 가능한 후보에만 비용"):
        EvaluatedCandidate.model_validate(infeasible_payload)


def test_none_cost_must_be_explicit(infeasible_payload):
    assert EvaluatedCandidate.model_validate(infeasible_payload).cost is None
    del infeasible_payload["cost"]
    with pytest.raises(ValidationError) as error:
        EvaluatedCandidate.model_validate(infeasible_payload)
    assert error.value.errors()[0]["loc"] == ("cost",)
    assert error.value.errors()[0]["type"] == "missing"


@pytest.mark.parametrize("case", ["missing", "extra", "duplicate", "wrong_berth"])
def test_evaluation_requires_exact_planned_timelines(evaluation_payload, case):
    timelines = evaluation_payload["simulation"]["timelines"]
    if case == "missing":
        timelines.pop()
    elif case == "extra":
        extra = deepcopy(timelines[0])
        extra["vessel_call_id"] = "extra-call"
        timelines.append(extra)
    elif case == "duplicate":
        timelines.append(deepcopy(timelines[0]))
    else:
        timelines[0]["berth_id"] = "berth-2"
    with pytest.raises(ValidationError, match="계획과 시뮬레이션의 배정"):
        EvaluatedCandidate.model_validate(evaluation_payload)


@pytest.mark.parametrize("case", ["missing", "extra"])
def test_evaluation_requires_exact_planned_cost_calls(evaluation_payload, case):
    cost = evaluation_payload["cost"]
    if case == "missing":
        cost["vessel_costs"].pop()
        cost["total_amount"] = "0.10"
    else:
        extra = deepcopy(cost["vessel_costs"][0])
        extra["vessel_call_id"] = "extra-call"
        cost["vessel_costs"].append(extra)
        cost["total_amount"] = "0.40"
    # 하위 비용 모델의 합계는 정상으로 유지하여 배정 대응 검증만 실패하게 한다.
    with pytest.raises(ValidationError, match="계획과 비용의 입항 건"):
        EvaluatedCandidate.model_validate(evaluation_payload)


def test_evaluation_accepts_reordered_results(evaluation_payload):
    evaluation_payload["simulation"]["timelines"].reverse()
    evaluation_payload["cost"]["vessel_costs"].reverse()
    value = EvaluatedCandidate.model_validate(evaluation_payload)
    assert value.simulation.timelines[0].vessel_call_id == "call-2"
    assert value.cost.total_amount == Decimal("0.30")


def test_ranking_rejects_infeasible_candidate(infeasible_payload):
    with pytest.raises(ValidationError, match="실행 불가능한 후보"):
        RankedCandidate(rank=1, evaluation=infeasible_payload)


@pytest.mark.parametrize("rank", [0, -1, True, "1"])
def test_ranking_requires_positive_integer(evaluation_payload, rank):
    with pytest.raises(ValidationError) as error:
        RankedCandidate(rank=rank, evaluation=evaluation_payload)
    assert error.value.errors()[0]["loc"] == ("rank",)
