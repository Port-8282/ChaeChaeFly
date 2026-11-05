"""공통 데이터 계약: 입력 제한, 정규화, 불변성과 시간 구간 경계."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError, create_model

from schemas import Money, SchemaModel, TimeWindow
from schemas.common import (
    CurrencyCode,
    EntityId,
    MoneyAmount,
    NonNegativeNumber,
    PositiveInt,
    PositiveNumber,
    Seconds,
    UtcDateTime,
)


# 모델 문맥에서 검사하여 SchemaModel의 유한 수치 정책도 함께 적용한다.
@pytest.fixture(scope="module")
def type_models():
    types = {
        "id": EntityId,
        "currency": CurrencyCode,
        "time": UtcDateTime,
        "seconds": Seconds,
        "integer": PositiveInt,
        "positive": PositiveNumber,
        "nonnegative": NonNegativeNumber,
        "amount": MoneyAmount,
    }
    return {
        name: create_model(f"{name.title()}Value", __base__=SchemaModel, value=(kind, ...))
        for name, kind in types.items()
    }


@pytest.mark.parametrize(
    "kind,value,expected",
    [
        ("id", "  call-1  ", "call-1"),
        ("currency", "KRW", "KRW"),
        ("seconds", 0, 0),
        ("integer", 1, 1),
        ("positive", 1, 1.0),
        ("positive", Decimal("0.5"), 0.5),
        ("nonnegative", 0, 0.0),
        ("amount", "0.10", Decimal("0.10")),
        ("amount", 0, Decimal(0)),
        ("amount", Decimal("12.34"), Decimal("12.34")),
    ],
)
def test_common_types_accept_and_normalize(type_models, kind, value, expected):
    actual = type_models[kind](value=value).value
    assert actual == expected
    assert type(actual) is type(expected)


@pytest.mark.parametrize(
    "kind,values",
    [
        ("id", ["", "   ", 1]),
        ("currency", ["krw", "KR", "KRWW", " KRW", "123"]),
        ("seconds", [-1, 1.0, "1", True, False]),
        ("integer", [0, -1, 1.0, "1", True]),
        ("positive", [0, -1, "1", True, float("inf"), float("nan")]),
        ("nonnegative", [-1, "0", False, float("inf"), float("nan")]),
        ("amount", [0.1, True, -1, "-0.1", "abc", "Infinity", Decimal("NaN")]),
    ],
)
def test_common_types_reject_invalid_values(type_models, kind, values):
    for value in values:
        with pytest.raises(ValidationError) as error:
            type_models[kind](value=value)
        assert error.value.errors()[0]["loc"] == ("value",), repr(value)


@pytest.mark.parametrize(
    "value",
    [
        "2026-11-05T09:00:00+09:00",
        datetime(2026, 11, 5, 9, tzinfo=timezone(timedelta(hours=9))),
    ],
)
def test_datetime_normalizes_to_utc(type_models, value):
    actual = type_models["time"](value=value).value
    assert actual == datetime(2026, 11, 5, tzinfo=timezone.utc)
    assert actual.tzinfo is timezone.utc


@pytest.mark.parametrize(
    "value",
    ["2026-11-05T09:00:00", datetime(2026, 11, 5, 9), 1793836800, True, "bad-time"],
)
def test_datetime_rejects_naive_or_invalid_input(type_models, value):
    with pytest.raises(ValidationError):
        type_models["time"](value=value)


def test_money_rejects_unknown_field():
    with pytest.raises(ValidationError) as error:
        Money(amount="1", currency="KRW", typo=1)
    assert error.value.errors()[0]["type"] == "extra_forbidden"
    assert error.value.errors()[0]["loc"] == ("typo",)


def test_model_is_frozen():
    money = Money(amount="1", currency="KRW")
    with pytest.raises(ValidationError) as error:
        money.amount = Decimal(2)
    assert error.value.errors()[0]["type"] == "frozen_instance"
    assert money.amount == Decimal(1)


def test_defaults_are_validated():
    class InvalidDefault(SchemaModel):
        count: PositiveInt = 0

    with pytest.raises(ValidationError):
        InvalidDefault()


def test_existing_instances_are_revalidated():
    class MutableSource(SchemaModel):
        model_config = {"frozen": False}
        count: PositiveInt

    source = MutableSource(count=1)
    source.count = 0  # assignment 검증이 없는 입력 객체도 재검증 시 거부해야 한다.
    with pytest.raises(ValidationError):
        MutableSource.model_validate(source)


@pytest.mark.parametrize("end", ["09:00:00", "08:00:00"])
def test_time_window_rejects_equal_or_reversed_bounds(end):
    with pytest.raises(ValidationError, match="start_at은 end_at보다"):
        TimeWindow(
            start_at="2026-11-05T09:00:00+09:00",
            end_at=f"2026-11-05T{end}+09:00",
        )


def test_time_window_compares_instants_across_timezones():
    value = TimeWindow(
        start_at="2026-11-05T09:00:00+09:00",
        end_at="2026-11-05T01:00:00Z",
    )
    assert value.end_at - value.start_at == timedelta(hours=1)
