# 입력과 계산 결과에서 함께 사용하는 Pydantic 모델과 재사용 가능한 타입을 정의한다.
# Annotated는 기본 타입에 검증 규칙을 덧붙이므로, 각 스키마가 같은 규칙을 공유할 수 있다.

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
    model_validator,
)


# 모든 스키마가 상속하는 기반 모델. 아래 설정은 하위 모델에도 적용된다.
class SchemaModel(BaseModel):
    """모든 데이터 계약의 공통 설정."""

    # frozen은 필드 재할당을 막는 설정이며, 임의의 내부 객체까지 재귀적으로 동결하지는 않는다.
    model_config = ConfigDict(
        extra="forbid",                # 정의되지 않은 필드 거부
        frozen=True,                   # 생성 후 필드 변경 금지
        allow_inf_nan=False,           # 무한대·NaN 금지
        validate_default=True,          # 생략되어 기본값을 쓰는 필드에도 검증 적용
        revalidate_instances="always", # 기존 모델 인스턴스를 입력해도 다시 검증
    )


# BeforeValidator: Pydantic이 값을 변환하기 전에 입력 형식을 제한한다.
# 숫자 타임스탬프를 차단하고, 시간대 유무는 이후 AwareDatetime이 검사한다.
def validate_datetime(value):
    if not isinstance(value, (str, datetime)):
        raise ValueError(
            "시각은 시간대가 있는 datetime 또는 ISO 문자열이어야 합니다."
        )
    return value


# bool은 파이썬에서 int의 하위 타입이므로 숫자 검사와 별도로 먼저 거부한다.
# 문자열의 숫자 형식과 유한성·음수 여부는 이후 Decimal 및 Field 검증에 맡긴다.
def validate_amount(value):
    # float 입력에 따른 금액 오차를 방지한다.
    if isinstance(value, bool) or not isinstance(
        value, (str, int, Decimal)
    ):
        raise ValueError(
            "금액은 Decimal, 정수 또는 문자열로 입력하세요."
        )
    return value


# 숫자 문자열과 bool의 자동 변환을 막고 실제 숫자 타입만 허용한다.
# 양수/0 이상 여부는 사용하는 타입 별칭의 Field에서 따로 검사한다.
def validate_number(value):
    if isinstance(value, bool) or not isinstance(
        value, (int, float, Decimal)
    ):
        raise ValueError("수치는 숫자로 입력하세요.")
    return value


# ID 앞뒤 공백을 제거한 뒤 길이를 검사한다. 공백만 있는 ID는 거부한다.
EntityId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]

# 대문자 세 글자라는 형식만 검사하며, 실제 통화 코드 등록 여부는 조회하지 않는다.
CurrencyCode = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z]{3}$"),
]

# 입력 형식 검사 → 시간대 포함 시각으로 해석 → 같은 순간의 UTC 시각으로 변환한다.
UtcDateTime = Annotated[
    AwareDatetime,
    BeforeValidator(validate_datetime),
    AfterValidator(
        lambda value: value.astimezone(timezone.utc)
    ),
]

# StrictInt는 bool·실수·숫자 문자열을 정수로 자동 변환하지 않는다. 초 값은 0 이상이다.
Seconds = Annotated[StrictInt, Field(ge=0)]
# 개수·순서·기간처럼 0을 허용하지 않는 정수에 사용한다.
PositiveInt = Annotated[StrictInt, Field(gt=0)]

# 실제 숫자 입력을 float로 변환하고 0보다 큰지 확인한다.
PositiveNumber = Annotated[
    float,
    BeforeValidator(validate_number),
    Field(gt=0),
]

# 0을 허용하는 측정값에 사용한다. 무한대·NaN은 공통 모델 설정으로 거부한다.
NonNegativeNumber = Annotated[
    float,
    BeforeValidator(validate_number),
    Field(ge=0),
]

# 금액은 Decimal로 보관한다. float 입력과 음수·무한대·NaN을 거부한다.
MoneyAmount = Annotated[
    Decimal,
    BeforeValidator(validate_amount),
    Field(ge=0, allow_inf_nan=False),
]


# 시간 구간은 [start_at, end_at)로 해석한다. 끝과 다음 시작이 같으면 겹치지 않는다.
class TimeWindow(SchemaModel):
    """시작 포함·종료 제외 시간 구간."""

    # 구간의 시작 시각(포함). 시간대가 있는 입력을 UTC로 정규화한다.
    start_at: UtcDateTime
    # 구간의 종료 시각(제외). start_at보다 반드시 늦어야 한다.
    end_at: UtcDateTime

    @model_validator(mode="after")
    def validate_order(self):
        # after 검증이므로 두 필드는 이미 시간대 검증과 UTC 변환을 마친 상태다.
        # 길이가 0인 구간과 역전된 구간을 모두 거부한다.
        if self.start_at >= self.end_at:
            raise ValueError(
                "start_at은 end_at보다 빨라야 합니다."
            )
        return self


# 금액과 통화를 함께 전달하는 값 객체. amount 자체에는 통화 정보가 없다.
class Money(SchemaModel):
    # 0 이상의 Decimal 금액. float 대신 정수·문자열·Decimal로 입력한다.
    amount: MoneyAmount
    # 영문 대문자 세 글자로 된 통화 코드. 예: KRW, USD.
    currency: CurrencyCode
