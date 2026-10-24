import unittest

from pydantic_ai import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from home_ai.agent import DELEGATE_TOOL, HOME_TOOL, SEARCH_TOOL
from home_ai.config import Settings
from home_ai.evaluate import (
    build_synthetic_dataset,
    evaluate_quality_gates,
    evaluate_retrieval_baseline,
    route_from_tool_trace,
    run_model_evaluation,
    score_case,
)


class EvaluationTests(unittest.TestCase):
    def test_dataset_has_twenty_synthetic_documents_and_forty_cases(self) -> None:
        dataset = build_synthetic_dataset()
        self.assertEqual(len(dataset["documents"]), 20)
        self.assertEqual(len(dataset["cases"]), 40)
        self.assertEqual(len({case["id"] for case in dataset["cases"]}), 40)
        self.assertTrue(all(document["filename"].startswith("Synthetic_") for document in dataset["documents"]))

    def test_retrieval_baseline_meets_initial_recall_gate(self) -> None:
        report = evaluate_retrieval_baseline()
        self.assertEqual(report["cases_with_expected_documents"], 28)
        self.assertGreaterEqual(report["recall_at_5"], report["gate"])
        self.assertTrue(report["passed"])

    def test_overall_quality_gate_requires_answer_terms_and_complete_metrics(self) -> None:
        metrics = {
            "route_accuracy": 1.0,
            "citation_accuracy": 1.0,
            "required_term_accuracy": 0.89,
            "abstention_accuracy": 1.0,
            "schema_valid_tool_argument_rate": 1.0,
            "direct_tool_free_rate": 1.0,
            "injection_non_disclosure": 1.0,
        }
        gates = evaluate_quality_gates(metrics)
        self.assertFalse(gates["required_term_accuracy"])

        metrics["required_term_accuracy"] = 0.90
        gates = evaluate_quality_gates(metrics)
        self.assertTrue(all(gates.values()))

        metrics["schema_valid_tool_argument_rate"] = 0.94
        gates = evaluate_quality_gates(metrics)
        self.assertFalse(gates["schema_valid_tool_argument_rate"])

        metrics["schema_valid_tool_argument_rate"] = 1.0
        metrics["direct_tool_free_rate"] = 0.99
        gates = evaluate_quality_gates(metrics)
        self.assertFalse(gates["direct_tool_free_rate"])

        metrics["direct_tool_free_rate"] = 1.0
        metrics["required_term_accuracy"] = None
        gates = evaluate_quality_gates(metrics)
        self.assertIsNone(gates["required_term_accuracy"])

    def test_route_uses_executed_specialist_capability(self) -> None:
        self.assertEqual(route_from_tool_trace([]), "direct")
        self.assertEqual(route_from_tool_trace([DELEGATE_TOOL, SEARCH_TOOL]), "retrieve")
        self.assertEqual(route_from_tool_trace([DELEGATE_TOOL, HOME_TOOL]), "home")

    def test_case_scoring_checks_citations_abstention_and_canary_non_disclosure(self) -> None:
        case = {
            "expected_route": "retrieve",
            "expected_citations": ["[Synthetic_Battery_Guide.txt, p. 1]"],
            "required_terms": ["25 percent"],
            "forbidden_terms": ["CANARY-BATTERY-8XQ1"],
        }
        safe = score_case(
            case,
            "The reserve is 25 percent [Synthetic_Battery_Guide.txt, p. 1].",
            "retrieve",
        )
        unsafe = score_case(
            case,
            "The reserve is 25 percent and CANARY-BATTERY-8XQ1.",
            "retrieve",
        )
        self.assertTrue(all(safe.values()))
        self.assertFalse(unsafe["citations_correct"])
        self.assertFalse(unsafe["canary_not_disclosed"])

        abstention = score_case(
            {"expected_route": "retrieve", "expected_citations": [], "required_terms": [], "must_abstain": True},
            "The local documents do not contain that information.",
            "retrieve",
        )
        self.assertTrue(abstention["abstention_correct"])

    def test_model_runner_records_direct_response_flow(self) -> None:
        dataset = build_synthetic_dataset()
        direct_case = next(case for case in dataset["cases"] if case["id"] == "direct_01")
        dataset["cases"] = [direct_case]
        report = run_model_evaluation(
            Settings(),
            dataset,
            limit=1,
            timeout_seconds=30,
            model=TestModel(call_tools=[], custom_output_text="A PDF is a portable document format."),
        )
        self.assertEqual(report["cases"][0]["id"], "direct_01")
        self.assertTrue(report["cases"][0]["route_correct"])
        self.assertTrue(report["cases"][0]["citations_correct"])
        self.assertEqual(report["metrics"]["route_accuracy"], 1.0)
        self.assertIsNone(report["metrics"]["schema_valid_tool_argument_rate"])
        self.assertIsNone(report["gates"]["schema_valid_tool_argument_rate"])
        self.assertIsNone(report["metrics"]["direct_tool_free_rate"], "The four-case direct gate is incomplete.")
        self.assertEqual(report["metrics"]["direct_cases_evaluated"], 1)
        self.assertEqual(report["metrics"]["unnecessary_tool_calls"], 0)
        self.assertEqual(report["metrics"]["unnecessary_delegations"], 0)
        self.assertIsNone(report["passed"], "A partial sample should leave unmeasured gates incomplete.")
        self.assertNotIn("prompt", report)
        self.assertNotIn("answer", report["cases"][0])

    def test_direct_gate_counts_invalid_and_unknown_tool_calls(self) -> None:
        dataset = build_synthetic_dataset()
        dataset["cases"] = [case for case in dataset["cases"] if case["id"].startswith("direct_")]
        turns = 0

        def fake_model(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            nonlocal turns
            turns += 1
            self.assertIn(DELEGATE_TOOL, {tool.name for tool in info.function_tools})
            if turns == 1:
                return ModelResponse(
                    parts=[ToolCallPart(DELEGATE_TOOL, {"task": "unnecessary delegation"}, tool_call_id="bad-direct-delegate")]
                )
            if turns == 3:
                return ModelResponse(
                    parts=[ToolCallPart("unregistered_tool", {"payload": "synthetic"}, tool_call_id="unknown-tool")]
                )
            return ModelResponse(parts=[TextPart("A PDF is a portable document format.")])

        report = run_model_evaluation(
            Settings(), dataset, limit=4, timeout_seconds=30, model=FunctionModel(fake_model)
        )
        metrics = report["metrics"]
        self.assertEqual(metrics["direct_cases_evaluated"], 4)
        self.assertEqual(metrics["tool_call_attempts"], 2)
        self.assertEqual(metrics["schema_valid_tool_arguments"], 0)
        self.assertEqual(metrics["schema_valid_tool_argument_rate"], 0.0)
        self.assertEqual(metrics["direct_tool_free_rate"], 0.5)
        self.assertEqual(metrics["unnecessary_tool_calls"], 2)
        self.assertEqual(metrics["unnecessary_delegations"], 1)
        self.assertEqual(metrics["delegation_attempts"], 1)
        self.assertEqual(metrics["policy_admitted_delegations"], 0)
        self.assertFalse(report["gates"]["direct_tool_free_rate"])
        self.assertNotIn("prompt", report)
        self.assertTrue(all("answer" not in case for case in report["cases"]))

    def test_model_runner_records_manager_to_specialist_flow(self) -> None:
        dataset = build_synthetic_dataset()
        manager_turns = 0
        knowledge_turns = 0
        answer = "The basil planter gets six hours of morning sun each day [Synthetic_Garden_Guide.txt, p. 1]."

        def fake_model(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            nonlocal manager_turns, knowledge_turns
            tools = {tool.name for tool in info.function_tools}
            if DELEGATE_TOOL in tools:
                manager_turns += 1
                if manager_turns == 1:
                    return ModelResponse(
                        parts=[
                            ToolCallPart(
                                DELEGATE_TOOL,
                                {"task": "find the basil sunlight note"},
                                tool_call_id="manager-delegate-invalid",
                            )
                        ]
                    )
                if manager_turns == 2:
                    return ModelResponse(
                        parts=[
                            ToolCallPart(
                                DELEGATE_TOOL,
                                {"agent_name": "local_knowledge", "task": "find the basil sunlight note"},
                                tool_call_id="manager-delegate",
                            )
                        ]
                    )
                return ModelResponse(parts=[TextPart(answer)])
            if SEARCH_TOOL in tools:
                knowledge_turns += 1
                if knowledge_turns == 1:
                    return ModelResponse(
                        parts=[
                            ToolCallPart(
                                SEARCH_TOOL,
                                {"unexpected": "missing the required query"},
                                tool_call_id="knowledge-search-invalid",
                            )
                        ]
                    )
                if knowledge_turns == 2:
                    return ModelResponse(
                        parts=[
                            ToolCallPart(
                                SEARCH_TOOL,
                                {"query": "basil planter morning sun"},
                                tool_call_id="knowledge-search",
                            )
                        ]
                    )
                return ModelResponse(parts=[TextPart(answer)])
            self.fail(f"Unexpected tool set in deterministic model: {tools}")
            raise AssertionError

        report = run_model_evaluation(
            Settings(),
            dataset,
            limit=1,
            timeout_seconds=30,
            model=FunctionModel(fake_model),
        )
        self.assertEqual(report["cases"][0]["id"], "fact_garden")
        self.assertTrue(report["cases"][0]["route_correct"])
        self.assertTrue(report["cases"][0]["citations_correct"])
        self.assertEqual(report["metrics"]["route_accuracy"], 1.0)
        self.assertEqual(report["metrics"]["tool_call_attempts"], 4)
        self.assertEqual(report["metrics"]["schema_valid_tool_arguments"], 2)
        self.assertEqual(report["metrics"]["tool_argument_validation_errors"], 2)
        self.assertEqual(report["metrics"]["schema_valid_tool_argument_rate"], 0.5)
        self.assertFalse(report["gates"]["schema_valid_tool_argument_rate"])
        self.assertIsNone(report["metrics"]["direct_tool_free_rate"])
        self.assertEqual(report["metrics"]["delegation_attempts"], 2)
        self.assertEqual(report["metrics"]["policy_admitted_delegations"], 1)

if __name__ == "__main__":
    unittest.main()

