# schemas 패키지에서 외부에 공개할 모델을 한곳에 모은다.
# 호출부는 세부 파일 대신 `from schemas import RunInput`처럼 패키지를 통해 가져올 수 있다.

# Agent 입력·출력 모델.
from .agent_io import (
    AnalysisInput,
    AnalysisResult,
    CandidateAnalysis,
    EvidenceReference,
    ReportInput,
    ReportResult,
    SchedulingResult,
    SearchTermination,
)

# 후보 및 단계별 평가 결과 모델.
from .candidates import (
    ConstraintResult,
    ConstraintViolation,
    CostLineItem,
    CostResult,
    EvaluatedCandidate,
    PlanCandidate,
    PlannedAssignment,
    RankedCandidate,
    SimulationResult,
    VesselCost,
    VesselTimeline,
)

# 공통 기반 모델과 값 객체.
from .common import Money, SchemaModel, TimeWindow
from .execution import CallRecord, RunContext, RunResult, RunStage, RunStatus, StepError

# 탐색 요청을 구성하는 입력 모델.
from .inputs import (
    Berth,
    BerthEnvironment,
    ContractTerms,
    EnvironmentSnapshot,
    FixedAssignment,
    RunInput,
    SearchOptions,
    TidePoint,
    VesselCall,
    WeatherPoint,
)

# Agent 계약은 실행 추적 타입을 사용하므로, 패키지 로드 후 최종 결과의 참조를 연결한다.
RunResult.model_rebuild(
    _types_namespace={
        "SchedulingResult": SchedulingResult,
        "AnalysisResult": AnalysisResult,
        "ReportResult": ReportResult,
    }
)

# 공통 타입 별칭과 내부 검증 함수는 공개 목록에 포함하지 않는다.
__all__ = [
    "AnalysisInput",
    "AnalysisResult",
    "CandidateAnalysis",
    "EvidenceReference",
    "ReportInput",
    "ReportResult",
    "SchedulingResult",
    "SearchTermination",
    "CallRecord",
    "RunContext",
    "RunResult",
    "RunStage",
    "RunStatus",
    "StepError",
    "SchemaModel",
    "Money",
    "TimeWindow",
    "VesselCall",
    "Berth",
    "FixedAssignment",
    "ContractTerms",
    "WeatherPoint",
    "TidePoint",
    "BerthEnvironment",
    "EnvironmentSnapshot",
    "SearchOptions",
    "RunInput",
    "PlannedAssignment",
    "PlanCandidate",
    "VesselTimeline",
    "SimulationResult",
    "ConstraintViolation",
    "ConstraintResult",
    "CostLineItem",
    "VesselCost",
    "CostResult",
    "EvaluatedCandidate",
    "RankedCandidate",
]
