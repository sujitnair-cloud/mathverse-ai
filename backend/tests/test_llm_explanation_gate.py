"""
Regression test: get_explanation() previously returned the structured
template immediately for any non-paid plan, before even checking whether
an LLM provider/key was configured -- meaning "AI Explanation" was never
actually AI for free/anonymous users regardless of setup. This is now a
deliberate product decision: attempt a real LLM explanation for every
plan, falling back to the template only on a genuine failure (no
provider, quota exhausted, request error).
"""
import unittest
from unittest.mock import patch

from app.services import llm_service


class FreeUsersGetRealLLMExplanationTests(unittest.IsolatedAsyncioTestCase):
    async def test_free_plan_attempts_gemini_instead_of_going_straight_to_template(self):
        with patch.object(llm_service.settings, "LLM_PROVIDER", "gemini"), \
             patch.object(llm_service.settings, "GEMINI_API_KEY", "AIzaSy" + "x" * 33), \
             patch.object(llm_service, "_call_gemini", return_value="a real gemini explanation") as mock_call:
            result = await llm_service.get_explanation(
                "unique_probe_problem_free_plan_gate_test",
                {"answer": "4"}, "intermediate", plan="free",
            )
        mock_call.assert_called_once()
        self.assertEqual(result, "a real gemini explanation")

    async def test_anonymous_plan_also_attempts_gemini(self):
        with patch.object(llm_service.settings, "LLM_PROVIDER", "gemini"), \
             patch.object(llm_service.settings, "GEMINI_API_KEY", "AIzaSy" + "x" * 33), \
             patch.object(llm_service, "_call_gemini", return_value="another real explanation") as mock_call:
            result = await llm_service.get_explanation(
                "unique_probe_problem_anonymous_gate_test",
                {"answer": "4"}, "intermediate", plan=None,
            )
        mock_call.assert_called_once()
        self.assertEqual(result, "another real explanation")

    async def test_still_falls_back_to_template_when_no_provider_configured(self):
        with patch.object(llm_service.settings, "LLM_PROVIDER", "none"):
            result = await llm_service.get_explanation(
                "unique_probe_problem_no_provider_test",
                {"answer": "4"}, "intermediate", plan="free",
            )
        # The rich fallback is a real, complete explanation, not empty/an error.
        self.assertTrue(len(result) > 20)

    async def test_a_genuine_call_failure_is_not_cached(self):
        """
        A transient/genuine LLM call failure was previously cached for 72h
        just like a real success -- confirmed directly in production: after
        fixing a real underlying bug (Gemini's model list going stale), a
        previously-asked problem kept serving the old cached failure while a
        brand-new problem text picked up the fix immediately. The failure
        path must never populate the cache.
        """
        problem = "unique_probe_problem_failure_not_cached_test"
        with patch.object(llm_service.settings, "LLM_PROVIDER", "gemini"), \
             patch.object(llm_service.settings, "GEMINI_API_KEY", "AIzaSy" + "x" * 33), \
             patch.object(llm_service, "_call_gemini", side_effect=RuntimeError("transient failure")):
            first = await llm_service.get_explanation(problem, {"answer": "4"}, "intermediate", plan="free")
        self.assertIn("*LLM error:", first)

        with patch.object(llm_service.settings, "LLM_PROVIDER", "gemini"), \
             patch.object(llm_service.settings, "GEMINI_API_KEY", "AIzaSy" + "x" * 33), \
             patch.object(llm_service, "_call_gemini", return_value="the fix landed") as mock_call:
            second = await llm_service.get_explanation(problem, {"answer": "4"}, "intermediate", plan="free")
        mock_call.assert_called_once()  # proves the second call wasn't served from a stale cache
        self.assertEqual(second, "the fix landed")


if __name__ == "__main__":
    unittest.main()
