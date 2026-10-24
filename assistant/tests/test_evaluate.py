import unittest

from pydantic_ai import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from home_ai.agent import DELEGATE_TOOL, HOME_TOOL, SEARCH_TOOL
from home_ai.config import Settings
from home_ai.evaluate import (
    build_synthetic_dataset,
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
        self.assertIsNone(report["passed"], "A partial sample should leave unmeasured gates incomplete.")
        self.assertNotIn("prompt", report)
        self.assertNotIn("answer", report["cases"][0])

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

if __name__ == "__main__":
    unittest.main()
