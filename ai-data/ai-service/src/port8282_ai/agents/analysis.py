from collections.abc import Callable

from schemas.agent_io import AnalysisInput, AnalysisResult
from schemas.execution import RunContext


class AnalysisAgent:
    def __init__(self, model: Callable[[RunContext, AnalysisInput], AnalysisResult | dict]):
        self._model = model

    def run(self, context: RunContext, analysis_input: AnalysisInput) -> AnalysisResult:
        return AnalysisResult.model_validate(self._model(context, analysis_input))
