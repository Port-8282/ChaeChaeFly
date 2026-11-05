# 한 번의 접안 계획 탐색에 필요한 입력 데이터 계약을 정의한다.
# 개별 모델은 값의 형식을 검증하고, RunInput은 모델 사이의 ID 참조와 계약 관계를 검증한다.
# 컬렉션은 tuple로 표현하며, 기본값 ()는 해당 항목이 제공되지 않은 상태를 나타낸다.

from typing import Literal

from pydantic import Field, model_validator

from .common import (
    CurrencyCode,
    EntityId,
    MoneyAmount,
    NonNegativeNumber,
    PositiveInt,
    PositiveNumber,
    SchemaModel,
    Seconds,
    TimeWindow,
    UtcDateTime,
)


# 선박 자체의 정보와 이번 입항의 도착 예정 시각·화물 정보를 묶는다.
class VesselCall(SchemaModel):
    """동일 선박도 입항 건별로 구분한다."""

    # 선박 ID와 별개인 입항 건 식별자. 같은 선박의 재입항을 구분한다.
    vessel_call_id: EntityId
    # 입항 횟수와 무관하게 선박 자체를 식별하는 ID.
    vessel_id: EntityId
    # 예상 도착 시각(ETA). 시간대가 있는 시각을 UTC로 저장한다.
    eta_at: UtcDateTime

    # 선박 길이(m). 0보다 커야 한다.
    length_m: PositiveNumber
    # 선박 폭(m). 0보다 커야 한다.
    beam_m: PositiveNumber
    # 흘수(m): 수면에서 선체 최하단까지의 깊이.
    draft_m: PositiveNumber

    # 이번 입항에서 처리할 화물량(톤). 0보다 커야 한다.
    cargo_tonnes: PositiveNumber
    # 화물 종류 코드. 부두의 취급 가능 화물과 비교할 때 사용한다.
    cargo_type: EntityId


# 부두의 수용 한계, 하역 처리 능력, 취급 화물과 가용 시간을 정의한다.
class Berth(SchemaModel):
    # 배정 또는 환경 정보가 가리키는 부두 식별자.
    berth_id: EntityId

    # 수용 가능한 선박의 최대 길이(m).
    max_length_m: PositiveNumber
    # 수용 가능한 선박의 최대 폭(m).
    max_beam_m: PositiveNumber
    # 지정한 기준면에서 측정한 수심(m).
    water_depth_m: PositiveNumber
    # 수심의 수직 기준면 식별자. 조위 데이터의 기준면과 함께 해석한다.
    vertical_datum: EntityId

    # 시간당 화물 처리량(톤/시간). 작업 소요 시간 산정에 사용한다.
    handling_tonnes_per_hour: PositiveNumber
    # 취급 가능한 화물 종류 코드 목록. 최소 한 개가 필요하다.
    supported_cargo_types: tuple[EntityId, ...] = Field(
        min_length=1
    )
    # 부두를 사용할 수 있는 구간. 시작 시각순으로 정렬되고 서로 겹치지 않아야 한다.
    available_windows: tuple[TimeWindow, ...]

    @model_validator(mode="after")
    def validate_windows(self):
        windows = self.available_windows

        # 정렬한 결과와 원본을 비교한다. 입력 순서를 자동으로 고치지 않고 오류로 알린다.
        ordered = tuple(
            sorted(windows, key=lambda w: w.start_at)
        )
        if windows != ordered:
            raise ValueError(
                "부두 가용 시간은 시간순이어야 합니다."
            )

        # 시간순 목록의 이웃 구간만 비교하면 겹침을 찾을 수 있다.
        # 이전 종료와 다음 시작이 같은 인접 구간은 허용한다.
        for previous, current in zip(windows, windows[1:]):
            if previous.end_at > current.start_at:
                raise ValueError("부두 가용 시간이 겹칩니다.")

        return self


# 탐색 입력으로 주어진 확정 배정과 부두 점유 시간 구간이다.
class FixedAssignment(SchemaModel):
    # 선박 ID와 별개인 입항 건 식별자. 같은 선박의 재입항을 구분한다.
    vessel_call_id: EntityId
    # 배정 또는 환경 정보가 가리키는 부두 식별자.
    berth_id: EntityId
    # 확정 배정이 부두를 점유하는 시작·종료 시간 구간.
    occupancy_window: TimeWindow


# 입항 건에 적용할 비용 규칙과 요율·허용 하역 시간을 보관한다.
class ContractTerms(SchemaModel):
    # 비용 계산에 적용하는 계약의 식별자.
    contract_id: EntityId
    # 선박 ID와 별개인 입항 건 식별자. 같은 선박의 재입항을 구분한다.
    vessel_call_id: EntityId

    # 적용할 계산 규칙을 구분하는 코드. 실제 규칙 실행은 계산 계층에서 수행한다.
    rule_code: EntityId
    # 같은 규칙 코드의 버전을 구분하여 적용한 규칙을 추적한다.
    rule_version: EntityId

    # 계약상 허용된 하역 시간(초). 0을 허용한다.
    allowed_laytime_seconds: Seconds

    # 요율 기간 한 단위에 대응하는 금액. 적용 방식은 지정한 규칙에 따른다.
    rate_amount: MoneyAmount
    # 요율의 기준 기간(초). 예: 시간당 요율이면 3600이며 0은 허용하지 않는다.
    rate_period_seconds: PositiveInt
    # 영문 대문자 세 글자로 된 통화 코드. 예: KRW, USD.
    currency: CurrencyCode

    # 시간 산정에 포함할 구간 목록. 구체적인 반영 방식은 계약 규칙에서 결정한다.
    included_windows: tuple[TimeWindow, ...] = ()
    # 시간 산정에서 제외할 구간 목록. 구체적인 반영 방식은 계약 규칙에서 결정한다.
    excluded_windows: tuple[TimeWindow, ...] = ()


# 특정 시각에 관측되거나 예측된 풍속과 파고 데이터 한 건이다.
class WeatherPoint(SchemaModel):
    # 해당 기상 값의 시각. UTC로 정규화한다.
    at: UtcDateTime
    # 풍속(m/s). 음수는 허용하지 않는다.
    wind_speed_mps: NonNegativeNumber
    # 파고(m). 음수는 허용하지 않는다.
    wave_height_m: NonNegativeNumber


# 특정 시각의 조위와 그 높이를 측정한 기준면을 함께 기록한다.
class TidePoint(SchemaModel):
    # 해당 조위 값의 시각. UTC로 정규화한다.
    at: UtcDateTime

    # 조위는 기준면보다 낮을 수 있으므로 음수를 허용한다.
    height_m: float = Field(
        strict=True,
        allow_inf_nan=False,
    )
    # 조위 높이의 수직 기준면 식별자.
    vertical_datum: EntityId


# 부두 하나에 대응하는 기상·조위 시계열과 작업 가능 시간 구간이다.
class BerthEnvironment(SchemaModel):
    # 배정 또는 환경 정보가 가리키는 부두 식별자.
    berth_id: EntityId

    # 부두의 기상 데이터 목록. 생략하면 빈 튜플이다.
    weather: tuple[WeatherPoint, ...] = ()
    # 부두의 조위 데이터 목록. 생략하면 빈 튜플이다.
    tides: tuple[TidePoint, ...] = ()
    # 환경 조건에 따른 작업 가능 구간. 빈 값의 업무적 해석은 소비하는 계층에서 정한다.
    workable_windows: tuple[TimeWindow, ...] = ()


# 한 실행에서 사용할 환경 데이터 묶음과 데이터 기준·수집 시각이다.
class EnvironmentSnapshot(SchemaModel):
    # 환경 데이터가 기준으로 삼는 시각.
    data_as_of: UtcDateTime
    # 환경 데이터를 수집한 시각. 기준 시각과 별도로 보관한다.
    collected_at: UtcDateTime

    # 부두별 환경 정보. RunInput에서 부두 ID의 중복과 참조 유효성을 검사한다.
    berth_conditions: tuple[BerthEnvironment, ...] = ()


# 후보 탐색에 사용할 반복·시간 한도, 반환 개수와 난수 시드를 정의한다.
class SearchOptions(SchemaModel):
    # 최대 탐색 반복 횟수. 기본값은 100회.
    max_iterations: PositiveInt = 100
    # 탐색 제한 시간(초). 기본값은 30초.
    time_limit_seconds: PositiveInt = 30
    # 반환할 상위 후보 개수. 기본값은 3개.
    top_k: PositiveInt = 3
    # 탐색 재현에 사용할 0 이상의 정수 시드. Seconds 타입의 정수 제약을 재사용한다.
    random_seed: Seconds = 0


# 접안 계획 탐색 한 번에 필요한 전체 입력. 마지막 검증에서 입력 간 연결을 확인한다.
class RunInput(SchemaModel):
    # 지원하는 입력 계약 버전. 현재 문자열 "1"만 허용한다.
    schema_version: Literal["1"] = "1"

    # 이번 계획이 대상으로 삼는 시간 범위.
    planning_window: TimeWindow

    # 계획할 입항 건 목록. 최소 한 건이 필요하며 입항 건 ID는 중복될 수 없다.
    vessel_calls: tuple[VesselCall, ...] = Field(
        min_length=1
    )
    # 배정 대상 부두 목록. 최소 한 개가 필요하며 부두 ID는 고유해야 한다.
    berths: tuple[Berth, ...] = Field(min_length=1)

    # 이미 확정된 배정 목록. 생략하면 확정 배정이 없는 것으로 전달된다.
    fixed_assignments: tuple[FixedAssignment, ...] = ()
    # 이번 실행에서 참조할 환경 데이터 스냅샷.
    environment: EnvironmentSnapshot

    # 입항 건별 계약 목록. 모든 입항 건에 정확히 하나의 계약이 필요하다.
    contracts: tuple[ContractTerms, ...] = Field(
        min_length=1
    )

    # 생략 시 실행별로 기본 SearchOptions 인스턴스를 생성한다.
    search_options: SearchOptions = Field(
        default_factory=SearchOptions
    )

    @model_validator(mode="after")
    def validate_references(self):
        # 리스트와 집합의 길이가 다르면 동일 ID가 둘 이상 들어온 것이다.
        def unique(values, label):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} 중복입니다.")

        call_ids = [
            vessel.vessel_call_id
            for vessel in self.vessel_calls
        ]
        berth_ids = [
            berth.berth_id
            for berth in self.berths
        ]
        contract_calls = [
            contract.vessel_call_id
            for contract in self.contracts
        ]

        # 개별 필드 검증으로는 찾을 수 없는 목록 내 ID 중복을 확인한다.
        unique(call_ids, "vessel_call_id")
        unique(berth_ids, "berth_id")
        unique(
            [contract.contract_id for contract in self.contracts],
            "contract_id",
        )
        unique(contract_calls, "입항 건별 계약")

        # 계약의 입항 건 중복을 먼저 막았으므로 집합 일치까지 확인하면
        # 모든 입항 건에 계약이 정확히 하나 있고, 알 수 없는 입항 건의 계약도 없음을 보장한다.
        if set(contract_calls) != set(call_ids):
            raise ValueError(
                "모든 입항 건에 계약이 정확히 하나씩 필요합니다."
            )

        # 합산 비용을 하나의 통화로 표현할 수 있도록 혼합 통화를 거부한다.
        currencies = {
            contract.currency
            for contract in self.contracts
        }
        if len(currencies) != 1:
            raise ValueError(
                "한 실행에서는 동일 통화만 사용할 수 있습니다."
            )

        unique(
            [
                assignment.vessel_call_id
                for assignment in self.fixed_assignments
            ],
            "확정 배정",
        )

        # 확정 배정이 이번 입력의 입항 건과 부두를 참조하는지 검사한다.
        for assignment in self.fixed_assignments:
            if (
                assignment.vessel_call_id not in call_ids
                or assignment.berth_id not in berth_ids
            ):
                raise ValueError(
                    "확정 배정이 존재하지 않는 "
                    "입항 건·부두를 참조합니다."
                )

        # 환경 정보는 부두당 최대 한 묶음이며, 입력에 없는 부두를 참조할 수 없다.
        # 모든 부두에 환경 정보가 존재하는지까지 요구하지는 않는다.
        conditions = self.environment.berth_conditions

        unique(
            [condition.berth_id for condition in conditions],
            "환경 데이터 부두",
        )

        for condition in conditions:
            if condition.berth_id not in berth_ids:
                raise ValueError(
                    "환경 데이터가 존재하지 않는 부두를 참조합니다."
                )

        return self
