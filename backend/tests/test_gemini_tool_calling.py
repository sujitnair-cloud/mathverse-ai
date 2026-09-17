"""
Tests for the Gemini tool-calling solve path (solve_with_gemini_tools):
Gemini reads the original problem directly in any phrasing/notation and
calls the solve_math tool for the actual computation, so the final answer
is guaranteed correct rather than hallucinated, without needing a new
regex-based topic pattern for every new phrasing.
"""
import unittest
from unittest.mock import patch

from app.services import llm_service
from app.services.llm_service import _run_solve_tool, solve_with_gemini_tools, QuotaExhaustedError


def _text_response(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def _function_call_response(name: str, args: dict) -> dict:
    return {"candidates": [{"content": {"parts": [{"functionCall": {"name": name, "args": args}}]}}]}


class RunSolveToolTests(unittest.TestCase):
    """The tool must reuse solve_expression() unchanged -- same hardened
    entry point (reject_unsafe_expression etc.) every direct request
    already goes through, since this argument is still just a string that
    traces back to user-influenced input, same RCE surface as any other
    path."""

    def test_valid_expression_returns_ok_with_answer(self):
        result = _run_solve_tool("d/dx of x^3")
        self.assertTrue(result["ok"])
        self.assertEqual(result["answer"], "3*x**2")

    def test_unparseable_expression_returns_ok_false_not_a_raised_exception(self):
        result = _run_solve_tool("this is not math at all")
        self.assertFalse(result["ok"])
        self.assertIn("error", result)

    def test_rce_payload_is_rejected_not_executed(self):
        result = _run_solve_tool('__import__("os").system("echo pwned")')
        self.assertFalse(result["ok"])
        self.assertIn("error", result)


class SolveWithGeminiToolsTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_none_when_provider_is_not_gemini(self):
        with patch.object(llm_service.settings, "LLM_PROVIDER", "none"):
            result = await solve_with_gemini_tools("2 + 2")
        self.assertIsNone(result)

    async def test_single_tool_call_round_trip_then_final_json(self):
        final_json = '{"answer": "3*x**2", "steps": [], "explanation": "fixture"}'
        responses = [
            _function_call_response("solve_math", {"expression": "d/dx of x^3"}),
            _text_response(final_json),
        ]
        with patch.object(llm_service.settings, "LLM_PROVIDER", "gemini"), \
             patch.object(llm_service.settings, "GEMINI_API_KEY", "AIzaSy" + "x" * 33), \
             patch.object(llm_service, "_gemini_generate", side_effect=responses) as mock_gen:
            result = await solve_with_gemini_tools("What is the derivative of x cubed?")
        self.assertEqual(result["answer"], "3*x**2")
        self.assertEqual(mock_gen.call_count, 2)
        # Second call must carry the tool's real result back to Gemini.
        second_call_contents = mock_gen.call_args_list[1].args[0]
        function_response_parts = [
            p for turn in second_call_contents for p in turn["parts"] if "functionResponse" in p
        ]
        self.assertEqual(len(function_response_parts), 1)
        self.assertTrue(function_response_parts[0]["functionResponse"]["response"]["ok"])

    async def test_no_tool_call_needed_still_returns_final_json(self):
        final_json = '{"answer": "4", "steps": [], "explanation": "fixture"}'
        with patch.object(llm_service.settings, "LLM_PROVIDER", "gemini"), \
             patch.object(llm_service.settings, "GEMINI_API_KEY", "AIzaSy" + "x" * 33), \
             patch.object(llm_service, "_gemini_generate", return_value=_text_response(final_json)):
            result = await solve_with_gemini_tools("2 + 2")
        self.assertEqual(result["answer"], "4")

    async def test_quota_exhaustion_returns_sentinel(self):
        with patch.object(llm_service.settings, "LLM_PROVIDER", "gemini"), \
             patch.object(llm_service.settings, "GEMINI_API_KEY", "AIzaSy" + "x" * 33), \
             patch.object(llm_service, "_gemini_generate", side_effect=QuotaExhaustedError("exhausted")):
            result = await solve_with_gemini_tools("2 + 2")
        self.assertEqual(result, {"_quota_exceeded": True})

    async def test_gives_up_after_round_trip_limit_instead_of_looping_forever(self):
        # Gemini keeps calling the tool and never finishes -- must give up,
        # not hang indefinitely.
        always_calling = _function_call_response("solve_math", {"expression": "2+2"})
        with patch.object(llm_service.settings, "LLM_PROVIDER", "gemini"), \
             patch.object(llm_service.settings, "GEMINI_API_KEY", "AIzaSy" + "x" * 33), \
             patch.object(llm_service, "_gemini_generate", return_value=always_calling) as mock_gen:
            result = await solve_with_gemini_tools("2 + 2")
        self.assertIsNone(result)
        self.assertEqual(mock_gen.call_count, 4)


if __name__ == "__main__":
    unittest.main()
