from collections.abc import Callable

from schemas.agent_io import ReportInput, ReportResult
from schemas.execution import RunContext


class ReportAgent:
    def __init__(self, model: Callable[[RunContext, ReportInput], ReportResult | dict]):
        self._model = model

    def run(self, context: RunContext, report_input: ReportInput) -> ReportResult:
        return ReportResult.model_validate(self._model(context, report_input))
