"""매번 새 딕셔너리를 반환하여 테스트 사이의 변경이 전파되지 않게 한다."""

from copy import deepcopy

import pytest


def at(hour: int) -> str:
    return f"2026-11-05T{hour:02d}:00:00+09:00"


def window(start: int, end: int) -> dict:
    return {"start_at": at(start), "end_at": at(end)}


def make_run_input_payload() -> dict:
    """동일 유조선의 입항 두 건과 원유 취급 부두 두 개를 포함한 정상 입력.

    선박 제원과 처리량은 테스트용 가상 값이다. 원유 20,000톤을 시간당
    10,000톤씩 처리하여 평가 예제의 작업 시간(10~12시)과 맞춘다.
    """
    return {
        "planning_window": window(0, 23),
        "vessel_calls": [
            {
                "vessel_call_id": f"call-{i}",
                "vessel_id": "oil-tanker-1",
                "eta_at": at(8),
                "length_m": 250,
                "beam_m": 44,
                "draft_m": 14,
                "cargo_tonnes": 20000,
                "cargo_type": "crude_oil",
            }
            for i in (1, 2)
        ],
        "berths": [
            {
                "berth_id": f"berth-{i}",
                "max_length_m": 300,
                "max_beam_m": 50,
                "water_depth_m": 18,
                "vertical_datum": "chart-datum",
                "handling_tonnes_per_hour": 10000,
                "supported_cargo_types": ["crude_oil"],
                "available_windows": [window(0, 23)],
            }
            for i in (1, 2)
        ],
        "fixed_assignments": [
            {
                "vessel_call_id": "call-1",
                "berth_id": "berth-1",
                "occupancy_window": window(9, 13),
            }
        ],
        "environment": {
            "data_as_of": at(6),
            "collected_at": at(7),
            "berth_conditions": [
                {
                    "berth_id": f"berth-{i}",
                    "weather": [
                        {"at": at(9), "wind_speed_mps": 3, "wave_height_m": 0.5}
                    ],
                    "tides": [
                        {"at": at(9), "height_m": -0.2, "vertical_datum": "chart-datum"}
                    ],
                    "workable_windows": [window(8, 20)],
                }
                for i in (1, 2)
            ],
        },
        "contracts": [
            {
                "contract_id": f"contract-{i}",
                "vessel_call_id": f"call-{i}",
                "rule_code": "demurrage",
                "rule_version": "1",
                "allowed_laytime_seconds": 3600,
                "rate_amount": "0.10",
                "rate_period_seconds": 3600,
                "currency": "KRW",
            }
            for i in (1, 2)
        ],
    }


def make_evaluation_payload() -> dict:
    """계산 없이 각 단계가 동일한 입항 두 건을 참조하는 정상 평가 데이터를 반환한다."""
    return {
        "candidate": {
            "candidate_id": "candidate-1",
            "assignments": [
                {
                    "vessel_call_id": f"call-{i}",
                    "berth_id": f"berth-{i}",
                    "sequence": 1,
                    "planned_berthing_at": at(9),
                }
                for i in (1, 2)
            ],
        },
        "simulation": {
            "candidate_id": "candidate-1",
            "timelines": [
                {
                    "vessel_call_id": f"call-{i}",
                    "berth_id": f"berth-{i}",
                    "berthing_at": at(9),
                    "work_started_at": at(10),
                    "work_completed_at": at(12),
                    "departed_at": at(13),
                    "waiting_seconds": 3600,
                    "interruptions": [],
                }
                for i in (1, 2)
            ],
        },
        "constraints": {
            "candidate_id": "candidate-1",
            "feasible": True,
            "violations": [],
        },
        "cost": {
            "candidate_id": "candidate-1",
            "vessel_costs": [
                {
                    "vessel_call_id": f"call-{i}",
                    "contract_id": f"contract-{i}",
                    "line_items": [
                        {
                            "line_item_id": f"line-{i}",
                            "rule_code": "demurrage",
                            "rule_version": "1",
                            "description": "초과 시간 비용",
                            "chargeable_seconds": 3600,
                            "amount": amount,
                        }
                    ],
                    "total_amount": amount,
                }
                for i, amount in ((1, "0.10"), (2, "0.20"))
            ],
            "total_amount": "0.30",
            "currency": "KRW",
        },
    }


@pytest.fixture
def run_input_payload():
    return make_run_input_payload()


@pytest.fixture
def evaluation_payload():
    return make_evaluation_payload()


@pytest.fixture
def infeasible_payload(evaluation_payload):
    payload = deepcopy(evaluation_payload)
    payload["constraints"].update(
        feasible=False,
        violations=[
            {
                "code": "BERTH_UNAVAILABLE",
                "message": "부두 사용 불가",
                "vessel_call_ids": ["call-1"],
                "berth_ids": ["berth-1"],
            }
        ],
    )
    payload["cost"] = None
    return payload


@pytest.fixture
def berth_payload(run_input_payload):
    return run_input_payload["berths"][0]


@pytest.fixture
def timeline_payload(evaluation_payload):
    return evaluation_payload["simulation"]["timelines"][0]
