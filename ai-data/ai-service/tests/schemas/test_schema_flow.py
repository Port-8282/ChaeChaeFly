"""입력·평가 데이터의 연결 및 JSON 전송 시 계약 보존을 확인한다."""

from datetime import timezone
from decimal import Decimal
import importlib
import json

import pytest

from schemas import EvaluatedCandidate, RankedCandidate, RunInput


def test_feasible_flow_from_input_to_rank(run_input_payload, evaluation_payload):
    run = RunInput.model_validate(run_input_payload)
    evaluation = EvaluatedCandidate.model_validate(evaluation_payload)
    ranked = RankedCandidate(rank=1, evaluation=evaluation)

    calls = {call.vessel_call_id for call in run.vessel_calls}
    assert {item.vessel_call_id for item in evaluation.candidate.assignments} == calls
    assert {item.berth_id for item in evaluation.candidate.assignments} <= {
        berth.berth_id for berth in run.berths
    }
    assert {item.contract_id for item in evaluation.cost.vessel_costs} == {
        contract.contract_id for contract in run.contracts
    }
    assert ranked.rank == 1
    assert ranked.evaluation.cost.total_amount == Decimal("0.30")


def test_infeasible_evaluation_preserves_violation(infeasible_payload):
    value = EvaluatedCandidate.model_validate(infeasible_payload)
    assert value.cost is None
    assert value.constraints.feasible is False
    assert value.constraints.violations[0].vessel_call_ids == ("call-1",)


def test_run_input_json_round_trip(run_input_payload):
    value = RunInput.model_validate(run_input_payload)
    serialized = value.model_dump_json()
    restored = RunInput.model_validate_json(serialized)

    assert restored == value
    assert isinstance(restored.vessel_calls, tuple)
    assert restored.vessel_calls[0].eta_at.tzinfo is timezone.utc
    assert restored.contracts[0].rate_amount == Decimal("0.10")
    assert json.loads(serialized)["contracts"][0]["rate_amount"] == "0.10"


@pytest.mark.parametrize("payload_name", ["evaluation_payload", "infeasible_payload"])
def test_evaluation_json_round_trip(request, payload_name):
    value = EvaluatedCandidate.model_validate(request.getfixturevalue(payload_name))
    restored = EvaluatedCandidate.model_validate_json(value.model_dump_json())

    assert restored == value
    assert restored.simulation.timelines[0].berthing_at.tzinfo is timezone.utc
    if value.cost is not None:
        assert isinstance(restored.cost.total_amount, Decimal)
        assert restored.cost.total_amount == Decimal("0.30")
    else:
        assert restored.cost is None


def test_public_schema_exports_are_importable():
    package = importlib.import_module("schemas")
    expected = {
        "SchemaModel", "Money", "TimeWindow", "VesselCall", "Berth", "FixedAssignment",
        "ContractTerms", "WeatherPoint", "TidePoint", "BerthEnvironment",
        "EnvironmentSnapshot", "SearchOptions", "RunInput", "PlannedAssignment",
        "PlanCandidate", "VesselTimeline", "SimulationResult", "ConstraintViolation",
        "ConstraintResult", "CostLineItem", "VesselCost", "CostResult",
        "EvaluatedCandidate", "RankedCandidate",
    }
    assert set(package.__all__) == expected
    for name in expected:
        assert getattr(package, name).__name__ == name
