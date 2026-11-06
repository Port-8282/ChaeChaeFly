import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from port8282_ai.agents import AnalysisAgent, ReportAgent, SchedulingAgent
from port8282_ai.agents.mocks import (
    mock_analysis_model,
    mock_evaluation_tool,
    mock_report_model,
)
from port8282_ai.graph import build_graph
from port8282_ai.graph.state import create_initial_state
from port8282_ai.orchestrator import Orchestrator
from port8282_ai.ranking import rank_candidates
from schemas import RunInput, RunResult, SchedulingResult
from schemas.agent_io import AnalysisInput, AnalysisResult, ReportInput, ReportResult
from schemas.execution import RunContext, RunStage, RunStatus


def make_workflow(
    evaluation,
    *,
    tools=None,
    analysis_model=mock_analysis_model,
    report_model=mock_report_model,
    **kwargs,
):
    return Orchestrator(
        build_graph(
            SchedulingAgent([mock_evaluation_tool(evaluation)] if tools is None else tools),
            AnalysisAgent(analysis_model),
            ReportAgent(report_model),
            **kwargs,
        )
    )


def fail(*args):
    raise RuntimeError("injected failure")


def test_success_and_serialization(run_input_payload, evaluation_payload):
    result = make_workflow(evaluation_payload).run(run_input_payload)
    assert result.status == RunStatus.SUCCEEDED
    assert result.stage == RunStage.FINALIZE
    assert result.report and result.analysis and result.scheduling_result
    assert len(result.evaluated_candidates) == len(result.ranked_candidates) == 1
    assert not result.errors
    assert [call.name for call in result.calls] == [
        "evaluation_tool_0",
        "scheduling",
        "ranking",
        "analysis",
        "report",
    ]
    assert all(call.run_id == result.context.run_id and call.succeeded for call in result.calls)
    assert RunResult.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("empty", [True, False])
def test_no_feasible_skips_models(run_input_payload, infeasible_payload, empty):
    model = Mock(side_effect=AssertionError("must not run"))
    result = make_workflow(
        infeasible_payload,
        tools=[] if empty else None,
        analysis_model=model,
        report_model=model,
    ).run(run_input_payload)
    assert result.status == RunStatus.SUCCEEDED
    assert result.warnings == ("NO_FEASIBLE_PLAN",)
    assert not result.ranked_candidates
    assert result.analysis is result.report is None
    model.assert_not_called()


def test_invalid_input_never_calls_graph():
    graph = Mock()
    result = Orchestrator(graph).run({})
    assert result.status == RunStatus.FAILED
    assert result.errors[0].stage == RunStage.INPUT
    graph.invoke.assert_not_called()


def test_tool_failure_keeps_completed_candidates(run_input_payload, evaluation_payload):
    result = make_workflow(
        evaluation_payload, tools=[mock_evaluation_tool(evaluation_payload), fail]
    ).run(run_input_payload)
    assert result.status == RunStatus.FAILED
    assert len(result.evaluated_candidates) == 1
    assert result.scheduling_result.termination_reason == "FAILED"
    assert [call.succeeded for call in result.calls] == [True, False, False]
    assert not result.ranked_candidates


@pytest.mark.parametrize("stage", ["scheduling", "ranking", "analysis", "report"])
def test_failures_preserve_previous_results(run_input_payload, evaluation_payload, stage):
    scheduling = SchedulingAgent([mock_evaluation_tool(evaluation_payload)])
    if stage == "scheduling":
        scheduling = Mock(run=Mock(side_effect=RuntimeError("agent failed")))
    report_model = Mock(side_effect=fail) if stage == "report" else Mock(wraps=mock_report_model)
    kwargs = {"ranker": fail} if stage == "ranking" else {}
    workflow = Orchestrator(
        build_graph(
            scheduling,
            AnalysisAgent(fail if stage == "analysis" else mock_analysis_model),
            ReportAgent(report_model),
            **kwargs,
        )
    )
    result = workflow.run(run_input_payload)
    assert result.status == (
        RunStatus.PARTIAL if stage in ("analysis", "report") else RunStatus.FAILED
    )
    assert result.errors[0].stage.value == stage.upper()
    assert bool(result.evaluated_candidates) == (stage != "scheduling")
    assert bool(result.ranked_candidates) == (stage in ("analysis", "report"))
    assert bool(result.analysis) == (stage == "report")
    assert result.report is None
    if stage != "report":
        report_model.assert_not_called()


@pytest.mark.parametrize("bad_reference", ["candidate", "line_item", "duplicate", "missing"])
def test_analysis_references_rejected(run_input_payload, evaluation_payload, bad_reference):
    def model(context, request):
        payload = mock_analysis_model(context, request).model_dump()
        item = payload["comparisons"][0]
        if bad_reference == "candidate":
            item["candidate_id"] = "unknown"
        elif bad_reference == "line_item":
            item["evidence"][0]["line_item_id"] = "unknown"
        elif bad_reference == "duplicate":
            payload["comparisons"] = (item, item)
        else:
            payload["comparisons"] = ()
        return payload

    report = Mock(wraps=mock_report_model)
    result = make_workflow(evaluation_payload, analysis_model=model, report_model=report).run(
        run_input_payload
    )
    assert result.status == RunStatus.PARTIAL
    assert result.ranked_candidates and result.analysis is None
    report.assert_not_called()


def test_report_references_rejected(run_input_payload, evaluation_payload):
    def model(context, request):
        payload = mock_report_model(context, request).model_dump()
        payload["candidate_ids"] = ("unknown",)
        return payload

    result = make_workflow(evaluation_payload, report_model=model).run(run_input_payload)
    assert result.status == RunStatus.PARTIAL
    assert result.analysis and result.report is None


@pytest.mark.parametrize("invalid", ["shape", "berth", "contract", "currency"])
def test_invalid_tool_results_fail(run_input_payload, evaluation_payload, invalid):
    payload = deepcopy(evaluation_payload)
    if invalid == "shape":
        payload["cost"]["total_amount"] = "999"
    elif invalid == "berth":
        payload["candidate"]["assignments"][0]["berth_id"] = "unknown"
        payload["simulation"]["timelines"][0]["berth_id"] = "unknown"
    elif invalid == "contract":
        payload["cost"]["vessel_costs"][0]["contract_id"] = "unknown"
    else:
        payload["cost"]["currency"] = "USD"
    result = make_workflow(evaluation_payload, tools=[lambda *_: payload]).run(run_input_payload)
    assert result.status == RunStatus.FAILED
    assert not result.ranked_candidates


def test_ranking_returns_all_feasible_candidates(run_input_payload, evaluation_payload):
    expensive = deepcopy(evaluation_payload)
    expensive["candidate"]["candidate_id"] = "z"
    for field in ("simulation", "constraints", "cost"):
        expensive[field]["candidate_id"] = "z"
    result = make_workflow(
        evaluation_payload,
        tools=[mock_evaluation_tool(expensive), mock_evaluation_tool(evaluation_payload)],
    ).run(run_input_payload)
    assert result.status == RunStatus.SUCCEEDED
    assert len(result.evaluated_candidates) == 2
    assert [r.evaluation.candidate.candidate_id for r in result.ranked_candidates] == [
        "candidate-1",
        "z",
    ]
    assert len(result.analysis.comparisons) == 2
    assert result.report.candidate_ids == ("candidate-1", "z")


def test_runs_do_not_share_state(run_input_payload, evaluation_payload):
    workflow = make_workflow(evaluation_payload)
    first = workflow.run(run_input_payload)
    invalid = workflow.run({})
    second = workflow.run(run_input_payload)
    assert first.context.run_id != second.context.run_id
    assert invalid.errors and not first.errors and not second.errors
    assert len(first.calls) == len(second.calls) == 5
    assert first.evaluated_candidates == second.evaluated_candidates
    assert first.evaluated_candidates[0] is not second.evaluated_candidates[0]


def test_independent_agents_and_utc(run_input_payload, evaluation_payload):
    context = RunContext(run_id="standalone", started_at=datetime.now(timezone.utc))
    snapshot = RunInput.model_validate(run_input_payload)
    scheduling = SchedulingAgent([mock_evaluation_tool(evaluation_payload)]).run(context, snapshot)
    request = AnalysisInput(
        ranked_candidates=rank_candidates(scheduling.evaluated_candidates),
        input_as_of=snapshot.environment.data_as_of,
    )
    analysis = AnalysisAgent(mock_analysis_model).run(context, request)
    report = ReportAgent(mock_report_model).run(
        context, ReportInput(**request.model_dump(), analysis=analysis)
    )
    assert isinstance(analysis, AnalysisResult)
    assert isinstance(report, ReportResult)
    assert request.input_as_of.utcoffset().total_seconds() == 0
    state = create_initial_state(context, snapshot)
    assert state["analysis"] is None and state["calls"] == ()


def test_cost_then_waiting_ranking(run_input_payload, evaluation_payload):
    tools = []
    for candidate_id, amount, waiting in (
        ("expensive", "2", 0),
        ("slow", "1", 100),
        ("fast", "1", 0),
    ):
        payload = deepcopy(evaluation_payload)
        payload["candidate"]["candidate_id"] = candidate_id
        for field in ("simulation", "constraints", "cost"):
            payload[field]["candidate_id"] = candidate_id
        for vessel in payload["cost"]["vessel_costs"]:
            vessel["line_items"][0]["amount"] = amount
            vessel["total_amount"] = amount
        payload["cost"]["total_amount"] = str(int(amount) * 2)
        for timeline in payload["simulation"]["timelines"]:
            timeline["waiting_seconds"] = waiting
        tools.append(mock_evaluation_tool(payload))
    result = make_workflow(evaluation_payload, tools=tools).run(run_input_payload)
    assert result.status == RunStatus.SUCCEEDED
    assert [r.evaluation.candidate.candidate_id for r in result.ranked_candidates] == [
        "fast",
        "slow",
        "expensive",
    ]


def test_duplicate_candidate_keeps_first_evaluation(run_input_payload, evaluation_payload):
    tool = mock_evaluation_tool(evaluation_payload)
    result = make_workflow(evaluation_payload, tools=[tool, tool]).run(run_input_payload)
    assert result.status == RunStatus.FAILED
    assert len(result.evaluated_candidates) == 1
    assert not result.calls[1].succeeded


def test_invalid_ranking_preserves_calculations(run_input_payload, evaluation_payload):
    def ranker(candidates):
        ranked = rank_candidates(candidates)
        return (ranked[0], ranked[0])

    result = make_workflow(evaluation_payload, ranker=ranker).run(run_input_payload)
    assert result.status == RunStatus.FAILED
    assert result.evaluated_candidates and not result.ranked_candidates
    assert result.errors[0].stage == RunStage.RANKING


@pytest.mark.parametrize("reason", ["MAX_ITERATIONS", "TIME_LIMIT"])
def test_search_limit_is_normal_termination(run_input_payload, evaluation_payload, reason):
    tool = mock_evaluation_tool(evaluation_payload)
    context = RunContext(run_id="test", started_at=datetime.now(timezone.utc))
    evaluation = tool(context, RunInput.model_validate(run_input_payload))
    scheduling = Mock(
        run=Mock(
            return_value=SchedulingResult(
                evaluated_candidates=(evaluation,),
                termination_reason=reason,
            )
        )
    )
    workflow = Orchestrator(
        build_graph(
            scheduling,
            AnalysisAgent(mock_analysis_model),
            ReportAgent(mock_report_model),
        )
    )
    result = workflow.run(run_input_payload)
    assert result.status == RunStatus.SUCCEEDED
    assert result.scheduling_result.termination_reason == reason


def test_graph_failure_does_not_leak_to_next_run(run_input_payload, evaluation_payload):
    report = Mock(
        side_effect=[
            RuntimeError("first run"),
            {
                "content": "second run",
                "candidate_ids": ["candidate-1"],
                "evidence": [{"candidate_id": "candidate-1"}],
            },
        ]
    )
    workflow = make_workflow(evaluation_payload, report_model=report)
    first = workflow.run(run_input_payload)
    second = workflow.run(run_input_payload)
    assert first.status == RunStatus.PARTIAL and first.errors
    assert second.status == RunStatus.SUCCEEDED and not second.errors
    assert second.report.content == "second run"
    assert all(call.run_id == second.context.run_id for call in second.calls)
    assert len(first.calls) == len(second.calls)


def test_example_cli(run_input_payload, evaluation_payload, tmp_path):
    input_path = tmp_path / "input.json"
    evaluation_path = tmp_path / "evaluation.json"
    input_path.write_text(json.dumps(run_input_payload), encoding="utf-8")
    evaluation_path.write_text(json.dumps(evaluation_payload), encoding="utf-8")
    script = Path(__file__).resolve().parents[2] / "examples" / "run_mock_graph.py"
    process = subprocess.run(
        [sys.executable, str(script), str(input_path), str(evaluation_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    result = RunResult.model_validate_json(process.stdout)
    assert result.status == RunStatus.SUCCEEDED and result.report
