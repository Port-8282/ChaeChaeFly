# 계획 후보 생성 → 시뮬레이션 → 제약 검사 → 비용 계산 → 순위 산정 단계의 데이터 계약이다.
# 각 결과는 candidate_id로 연결하고, EvaluatedCandidate에서 단계 간 일관성을 검증한다.
# 이 파일은 결과의 구조와 정합성을 검증하며, 시뮬레이션이나 비용 계산 자체를 수행하지 않는다.

from pydantic import Field, model_validator

from .common import (
    CurrencyCode,
    EntityId,
    MoneyAmount,
    PositiveInt,
    SchemaModel,
    Seconds,
    TimeWindow,
    UtcDateTime,
)


# 한 입항 건을 어느 부두에, 몇 번째로, 언제 접안시킬지 나타낸다.
class PlannedAssignment(SchemaModel):
    # 선박 ID와 별개인 입항 건 식별자. 같은 선박의 재입항을 구분한다.
    vessel_call_id: EntityId
    # 배정 또는 환경 정보가 가리키는 부두 식별자.
    berth_id: EntityId

    # 같은 부두 안에서의 접안 순서. 1 이상의 정수이며 연속성까지 검사하지는 않는다.
    sequence: PositiveInt
    # 계획상 접안 시각. 실제 계산된 시각은 VesselTimeline에 기록한다.
    planned_berthing_at: UtcDateTime


# 하나 이상의 접안 배정으로 구성된 계획 후보이다.
class PlanCandidate(SchemaModel):
    # 계획 후보와 해당 후보의 계산 결과를 연결하는 식별자.
    candidate_id: EntityId
    # 후보를 구성하는 배정 목록. 최소 한 건이 필요하다.
    assignments: tuple[PlannedAssignment, ...] = Field(
        min_length=1
    )

    @model_validator(mode="after")
    def validate_assignments(self):
        # 하나의 입항 건을 여러 배정에 넣는 중복과, 같은 부두의 순서 충돌을 각각 검사한다.
        calls = [
            assignment.vessel_call_id
            for assignment in self.assignments
        ]
        positions = [
            (assignment.berth_id, assignment.sequence)
            for assignment in self.assignments
        ]

        if len(calls) != len(set(calls)):
            raise ValueError(
                "같은 입항 건을 중복 배정할 수 없습니다."
            )

        # 부두가 다르면 같은 sequence 값을 사용할 수 있으므로 (부두 ID, 순서) 쌍을 비교한다.
        if len(positions) != len(set(positions)):
            raise ValueError(
                "같은 부두의 접안 순서는 중복될 수 없습니다."
            )

        return self


# 시뮬레이션으로 얻은 입항 건 하나의 작업 진행 시각과 중단 구간이다.
class VesselTimeline(SchemaModel):
    # 선박 ID와 별개인 입항 건 식별자. 같은 선박의 재입항을 구분한다.
    vessel_call_id: EntityId
    # 배정 또는 환경 정보가 가리키는 부두 식별자.
    berth_id: EntityId

    # 시뮬레이션에서 계산한 접안 시각.
    berthing_at: UtcDateTime
    # 화물 작업을 시작한 시각. 접안 시각과 같을 수 있다.
    work_started_at: UtcDateTime
    # 화물 작업을 완료한 시각. 작업 시작보다 빠를 수 없다.
    work_completed_at: UtcDateTime
    # 출항 시각. 작업 완료 시각과 같거나 늦어야 한다.
    departed_at: UtcDateTime

    # 계산된 대기 시간(초). 이 모델에서 다른 시각과의 차이로 재계산하지는 않는다.
    waiting_seconds: Seconds
    # 작업 시간 안의 중단 구간 목록. 서로 겹칠 수 없으며 생략 시 빈 튜플이다.
    interruptions: tuple[TimeWindow, ...] = ()

    @model_validator(mode="after")
    def validate_times(self):
        # 각 단계는 같은 시각일 수 있지만, 시간 흐름이 역전되어서는 안 된다.
        if not (
            self.berthing_at
            <= self.work_started_at
            <= self.work_completed_at
            <= self.departed_at
        ):
            raise ValueError(
                "접안·작업 시작·완료·출항 시각의 순서가 "
                "잘못되었습니다."
            )

        # 중단 구간 전체가 작업 시작~완료 사이에 포함되어야 한다.
        for window in self.interruptions:
            if not (
                self.work_started_at
                <= window.start_at
                < window.end_at
                <= self.work_completed_at
            ):
                raise ValueError(
                    "중단 구간은 작업 시간 안에 있어야 합니다."
                )

        # 겹침 검사에만 정렬된 복사본을 사용한다. 저장된 중단 구간의 입력 순서는 바꾸지 않는다.
        windows = sorted(
            self.interruptions,
            key=lambda window: window.start_at,
        )
        for previous, current in zip(windows, windows[1:]):
            # 끝과 시작이 같은 구간은 허용하며, 실제 시간이 겹칠 때만 거부한다.
            if previous.end_at > current.start_at:
                raise ValueError("중단 구간이 겹칩니다.")

        return self


# 한 후보에 대한 입항 건별 시뮬레이션 결과를 모은다.
class SimulationResult(SchemaModel):
    # 계획 후보와 해당 후보의 계산 결과를 연결하는 식별자.
    candidate_id: EntityId
    # 입항 건별 시간표. 최소 한 건이며 계획과의 대응은 EvaluatedCandidate에서 검사한다.
    timelines: tuple[VesselTimeline, ...] = Field(
        min_length=1
    )


# 제약 위반의 종류·설명과 관련 입항 건 및 부두를 기록한다.
class ConstraintViolation(SchemaModel):
    # 제약 위반 유형을 식별하는 코드.
    code: EntityId
    # 제약 위반 설명. 길이가 1 이상인 문자열이어야 한다.
    message: str = Field(min_length=1)

    # 위반에 관련된 입항 건 ID 목록. 대상이 없으면 빈 튜플이다.
    vessel_call_ids: tuple[EntityId, ...] = ()
    # 위반에 관련된 부두 ID 목록. 대상이 없으면 빈 튜플이다.
    berth_ids: tuple[EntityId, ...] = ()


# 후보의 실행 가능 여부와 그 판단 근거인 제약 위반 목록이다.
class ConstraintResult(SchemaModel):
    # 계획 후보와 해당 후보의 계산 결과를 연결하는 식별자.
    candidate_id: EntityId
    # 실제 bool만 허용한다. 위반 목록이 비어 있을 때만 True여야 한다.
    feasible: bool = Field(strict=True)

    # 발견된 제약 위반 목록. 항목이 하나라도 있으면 실행 불가능한 후보이다.
    violations: tuple[ConstraintViolation, ...] = ()

    @model_validator(mode="after")
    def validate_feasibility(self):
        # 위반 없음 ↔ 실행 가능(True)의 양방향 관계를 강제한다.
        if self.feasible != (not self.violations):
            raise ValueError(
                "실행 가능 여부와 위반 목록이 일치하지 않습니다."
            )
        return self


# 어떤 규칙을 적용해 얼마를 계산했는지 추적하기 위한 비용 상세 한 항목이다.
class CostLineItem(SchemaModel):
    # 입항 건별 비용 상세 안에서 고유해야 하는 내역 ID.
    line_item_id: EntityId

    # 적용할 계산 규칙을 구분하는 코드. 실제 규칙 실행은 계산 계층에서 수행한다.
    rule_code: EntityId
    # 같은 규칙 코드의 버전을 구분하여 적용한 규칙을 추적한다.
    rule_version: EntityId
    # 비용 발생 사유 또는 계산 내역 설명. 빈 문자열은 허용하지 않는다.
    description: str = Field(min_length=1)

    # 해당 내역의 과금 대상 시간(초). 금액과의 관계는 계산 규칙에서 결정한다.
    chargeable_seconds: Seconds
    # 0 이상의 Decimal 금액. float 대신 정수·문자열·Decimal로 입력한다.
    amount: MoneyAmount


# 입항 건 하나의 계약별 비용 상세와 합계를 보관한다.
class VesselCost(SchemaModel):
    # 선박 ID와 별개인 입항 건 식별자. 같은 선박의 재입항을 구분한다.
    vessel_call_id: EntityId
    # 비용 계산에 적용하는 계약의 식별자.
    contract_id: EntityId

    # 입항 건의 비용 상세 목록. 각 항목 금액의 합이 total_amount와 같아야 한다.
    line_items: tuple[CostLineItem, ...]
    # 비용 상세 금액의 합계. 빈 내역이면 합계는 0이어야 한다.
    total_amount: MoneyAmount

    @model_validator(mode="after")
    def validate_total(self):
        ids = [
            item.line_item_id
            for item in self.line_items
        ]
        if len(ids) != len(set(ids)):
            raise ValueError("계산 내역 ID가 중복되었습니다.")

        # 전달받은 합계를 신뢰하지 않고 상세 금액을 더해 정확히 일치하는지 검사한다.
        # Decimal 금액을 그대로 합산하며, 여기서 반올림이나 허용 오차는 적용하지 않는다.
        calculated = sum(
            (item.amount for item in self.line_items),
            0,
        )
        if calculated != self.total_amount:
            raise ValueError(
                "선박별 비용과 계산 내역의 합계가 다릅니다."
            )

        return self


# 후보 전체의 입항 건별 비용과 동일 통화 기준 총합이다.
class CostResult(SchemaModel):
    # 계획 후보와 해당 후보의 계산 결과를 연결하는 식별자.
    candidate_id: EntityId
    # 입항 건별 비용 목록. 최소 한 건이며 같은 입항 건을 중복 계산할 수 없다.
    vessel_costs: tuple[VesselCost, ...] = Field(
        min_length=1
    )

    # 입항 건별 total_amount를 모두 더한 후보 전체 비용.
    total_amount: MoneyAmount
    # 영문 대문자 세 글자로 된 통화 코드. 예: KRW, USD.
    currency: CurrencyCode

    @model_validator(mode="after")
    def validate_total(self):
        ids = [
            cost.vessel_call_id
            for cost in self.vessel_costs
        ]
        if len(ids) != len(set(ids)):
            raise ValueError("입항 건별 비용이 중복되었습니다.")

        # 전달받은 합계를 신뢰하지 않고 상세 금액을 더해 정확히 일치하는지 검사한다.
        # Decimal 금액을 그대로 합산하며, 여기서 반올림이나 허용 오차는 적용하지 않는다.
        calculated = sum(
            (cost.total_amount for cost in self.vessel_costs),
            0,
        )
        if calculated != self.total_amount:
            raise ValueError(
                "전체 비용과 선박별 비용의 합계가 다릅니다."
            )

        return self


# 계획과 각 평가 결과를 묶고, 서로 같은 후보·배정을 다루는지 검증한다.
class EvaluatedCandidate(SchemaModel):
    """모든 계산이 끝난 후보."""

    # 평가의 기준이 되는 원본 계획 후보.
    candidate: PlanCandidate
    # 계획에 포함된 모든 배정의 시뮬레이션 결과.
    simulation: SimulationResult
    # 실행 가능 여부와 위반 사유를 담은 제약 검사 결과.
    constraints: ConstraintResult
    # 실행 가능하면 반드시 비용 결과가 필요하고, 실행 불가능하면 None이어야 한다.
    # 기본값이 없으므로 비용이 없는 경우에도 cost=None을 명시해야 한다.
    cost: CostResult | None

    @model_validator(mode="after")
    def validate_consistency(self):
        # 시뮬레이션·제약·비용 결과가 모두 원본 후보에 대한 결과인지 확인한다.
        expected_id = self.candidate.candidate_id

        results = [
            self.simulation,
            self.constraints,
        ]
        if self.cost is not None:
            results.append(self.cost)

        if any(
            result.candidate_id != expected_id
            for result in results
        ):
            raise ValueError("후보 ID가 일치하지 않습니다.")

        # 실행 가능 후보의 비용 누락과 실행 불가능 후보의 비용 포함을 모두 거부한다.
        if self.constraints.feasible != (self.cost is not None):
            raise ValueError(
                "실행 가능한 후보에만 비용 결과가 필요합니다."
            )

        # 시간표는 순서와 무관하게 계획의 (입항 건, 부두) 쌍을 정확히 한 번씩 포함해야 한다.
        planned = {
            (assignment.vessel_call_id, assignment.berth_id)
            for assignment in self.candidate.assignments
        }
        actual = [
            (timeline.vessel_call_id, timeline.berth_id)
            for timeline in self.simulation.timelines
        ]

        if (
            len(actual) != len(set(actual))
            or set(actual) != planned
        ):
            raise ValueError(
                "계획과 시뮬레이션의 배정이 일치하지 않습니다."
            )

        # 비용 결과가 있다면 계획의 모든 입항 건을 빠짐없이, 추가 항목 없이 다뤄야 한다.
        # 입항 건별 비용 중복은 CostResult 자체의 검증에서 이미 검사한다.
        if self.cost is not None:
            planned_calls = {
                assignment.vessel_call_id
                for assignment in self.candidate.assignments
            }
            cost_calls = {
                cost.vessel_call_id
                for cost in self.cost.vessel_costs
            }
            if cost_calls != planned_calls:
                raise ValueError(
                    "계획과 비용의 입항 건이 일치하지 않습니다."
                )

        return self


# 실행 가능한 평가 결과에 1 이상의 순위를 부여한 반환 모델이다.
class RankedCandidate(SchemaModel):
    # 1 이상의 순위 값. 후보 목록 전체의 순위 중복이나 연속성은 여기서 검사하지 않는다.
    rank: PositiveInt
    # 순위에 포함할 평가 결과. 실행 가능한 후보만 허용한다.
    evaluation: EvaluatedCandidate

    @model_validator(mode="after")
    def validate_rankable(self):
        # 순위 모델은 후보의 비용을 비교하거나 순서를 계산하지 않고, 순위 부여 자격만 검사한다.
        if not self.evaluation.constraints.feasible:
            raise ValueError(
                "실행 불가능한 후보는 순위에 포함할 수 없습니다."
            )
        return self
