"""입력 계약의 고유 제약과 모델 간 참조 관계를 검증한다."""

from copy import deepcopy
from decimal import Decimal

import pytest
from pydantic import ValidationError

from schemas import (
    Berth,
    BerthEnvironment,
    ContractTerms,
    EnvironmentSnapshot,
    RunInput,
    SearchOptions,
    TidePoint,
    WeatherPoint,
)


def test_run_input_accepts_two_calls_of_same_vessel(run_input_payload):
    value = RunInput.model_validate(run_input_payload)
    assert value.vessel_calls[0].vessel_id == value.vessel_calls[1].vessel_id
    assert value.vessel_calls[0].vessel_call_id != value.vessel_calls[1].vessel_call_id
    assert isinstance(value.vessel_calls, tuple)
    assert value.contracts[0].rate_amount == Decimal("0.10")
    assert value.schema_version == "1"


def test_search_defaults_and_independent_instances(run_input_payload):
    first = RunInput.model_validate(run_input_payload)
    second = RunInput.model_validate(run_input_payload)
    assert first.search_options.model_dump() == {
        "max_iterations": 100,
        "time_limit_seconds": 30,
        "top_k": 3,
        "random_seed": 0,
    }
    assert first.search_options is not second.search_options


@pytest.mark.parametrize("field", ["max_iterations", "time_limit_seconds", "top_k"])
@pytest.mark.parametrize("value", [0, -1])
def test_search_options_reject_nonpositive_limits(field, value):
    with pytest.raises(ValidationError):
        SearchOptions(**{field: value})


@pytest.mark.parametrize("value", [-1, True, "0"])
def test_search_options_reject_invalid_seed(value):
    with pytest.raises(ValidationError):
        SearchOptions(random_seed=value)


@pytest.mark.parametrize(
    "bounds,allowed,message",
    [
        ([(8, 9), (10, 11)], True, None),
        ([(8, 9), (9, 10)], True, None),
        ([], True, None),
        ([(10, 11), (8, 9)], False, "시간순"),
        ([(8, 10), (9, 11)], False, "겹칩니다"),
    ],
)
def test_berth_windows(berth_payload, bounds, allowed, message):
    berth_payload["available_windows"] = [
        {
            "start_at": f"2026-11-05T{start:02d}:00:00Z",
            "end_at": f"2026-11-05T{end:02d}:00:00Z",
        }
        for start, end in bounds
    ]
    if allowed:
        assert len(Berth.model_validate(berth_payload).available_windows) == len(bounds)
    else:
        with pytest.raises(ValidationError, match=message):
            Berth.model_validate(berth_payload)


def test_berth_requires_supported_cargo(berth_payload):
    berth_payload["supported_cargo_types"] = []
    with pytest.raises(ValidationError) as error:
        Berth.model_validate(berth_payload)
    assert error.value.errors()[0]["loc"] == ("supported_cargo_types",)


def test_contract_defaults_and_zero_allowed_laytime(run_input_payload):
    payload = run_input_payload["contracts"][0]
    payload["allowed_laytime_seconds"] = 0
    contract = ContractTerms.model_validate(payload)
    assert contract.allowed_laytime_seconds == 0
    assert contract.included_windows == contract.excluded_windows == ()


def test_contract_rejects_zero_rate_period(run_input_payload):
    payload = run_input_payload["contracts"][0]
    payload["rate_period_seconds"] = 0
    with pytest.raises(ValidationError):
        ContractTerms.model_validate(payload)


def test_environment_defaults_and_zero_weather():
    at = "2026-11-05T00:00:00Z"
    weather = WeatherPoint(at=at, wind_speed_mps=0, wave_height_m=0)
    assert weather.wind_speed_mps == weather.wave_height_m == 0
    berth = BerthEnvironment(berth_id="berth-1")
    assert berth.weather == berth.tides == berth.workable_windows == ()
    assert EnvironmentSnapshot(data_as_of=at, collected_at=at).berth_conditions == ()


def test_tide_accepts_negative_height():
    assert TidePoint(
        at="2026-11-05T00:00:00Z", height_m=-0.5, vertical_datum="datum"
    ).height_m == -0.5


@pytest.mark.parametrize("height", [float("inf"), float("nan"), "-0.5", True])
def test_tide_rejects_nonfinite_or_coerced_input(height):
    with pytest.raises(ValidationError):
        TidePoint(at="2026-11-05T00:00:00Z", height_m=height, vertical_datum="datum")


@pytest.mark.parametrize("field", ["vessel_calls", "berths", "contracts"])
def test_run_input_requires_nonempty_collections(run_input_payload, field):
    run_input_payload[field] = []
    with pytest.raises(ValidationError) as error:
        RunInput.model_validate(run_input_payload)
    assert error.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize(
    "collection,field,message",
    [
        ("vessel_calls", "vessel_call_id", "vessel_call_id 중복"),
        ("berths", "berth_id", "berth_id 중복"),
        ("contracts", "contract_id", "contract_id 중복"),
        ("contracts", "vessel_call_id", "입항 건별 계약 중복"),
    ],
)
def test_run_input_rejects_duplicate_ids(run_input_payload, collection, field, message):
    run_input_payload[collection][1][field] = run_input_payload[collection][0][field]
    with pytest.raises(ValidationError, match=message):
        RunInput.model_validate(run_input_payload)


@pytest.mark.parametrize("case", ["missing", "unknown"])
def test_every_call_requires_exactly_one_contract(run_input_payload, case):
    if case == "missing":
        run_input_payload["contracts"].pop()
    else:
        run_input_payload["contracts"][1]["vessel_call_id"] = "unknown"
    with pytest.raises(ValidationError, match="계약이 정확히 하나씩"):
        RunInput.model_validate(run_input_payload)


def test_run_input_rejects_mixed_currencies(run_input_payload):
    run_input_payload["contracts"][1]["currency"] = "USD"
    with pytest.raises(ValidationError, match="동일 통화"):
        RunInput.model_validate(run_input_payload)


def test_run_input_rejects_duplicate_fixed_assignment(run_input_payload):
    run_input_payload["fixed_assignments"] *= 2
    with pytest.raises(ValidationError, match="확정 배정 중복"):
        RunInput.model_validate(run_input_payload)


@pytest.mark.parametrize("field", ["vessel_call_id", "berth_id"])
def test_fixed_assignment_requires_known_references(run_input_payload, field):
    run_input_payload["fixed_assignments"][0][field] = "unknown"
    with pytest.raises(ValidationError, match="존재하지 않는.*입항 건·부두"):
        RunInput.model_validate(run_input_payload)


def test_run_input_rejects_duplicate_environment_berth(run_input_payload):
    conditions = run_input_payload["environment"]["berth_conditions"]
    conditions.append(deepcopy(conditions[0]))
    with pytest.raises(ValidationError, match="환경 데이터 부두 중복"):
        RunInput.model_validate(run_input_payload)


def test_environment_requires_known_berth(run_input_payload):
    run_input_payload["environment"]["berth_conditions"][0]["berth_id"] = "unknown"
    with pytest.raises(ValidationError, match="환경 데이터가 존재하지 않는 부두"):
        RunInput.model_validate(run_input_payload)


@pytest.mark.parametrize("count", [0, 1])
def test_partial_or_empty_environment_is_allowed(run_input_payload, count):
    run_input_payload["environment"]["berth_conditions"] = (
        run_input_payload["environment"]["berth_conditions"][:count]
    )
    del run_input_payload["fixed_assignments"]
    value = RunInput.model_validate(run_input_payload)
    assert len(value.environment.berth_conditions) == count
    assert value.fixed_assignments == ()


@pytest.mark.parametrize("version", ["2", 1])
def test_run_input_rejects_unsupported_version(run_input_payload, version):
    run_input_payload["schema_version"] = version
    with pytest.raises(ValidationError) as error:
        RunInput.model_validate(run_input_payload)
    assert error.value.errors()[0]["loc"] == ("schema_version",)
