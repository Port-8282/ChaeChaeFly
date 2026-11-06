"""입력 JSON과 모의 평가 JSON으로 실제 LangGraph 전체 흐름을 실행한다."""

import argparse
import json
from pathlib import Path

from port8282_ai.agents import AnalysisAgent, ReportAgent, SchedulingAgent
from port8282_ai.agents.mocks import (
    mock_analysis_model,
    mock_evaluation_tool,
    mock_report_model,
)
from port8282_ai.graph import build_graph
from port8282_ai.orchestrator import Orchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="RunInput JSON 파일")
    parser.add_argument("evaluation", type=Path, help="EvaluatedCandidate JSON 파일")
    args = parser.parse_args()
    evaluation = json.loads(args.evaluation.read_text(encoding="utf-8"))
    graph = build_graph(
        scheduling=SchedulingAgent([mock_evaluation_tool(evaluation)]),
        analysis=AnalysisAgent(mock_analysis_model),
        report=ReportAgent(mock_report_model),
    )
    orchestrator = Orchestrator(graph)
    result = orchestrator.run(json.loads(args.input.read_text(encoding="utf-8")))
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
