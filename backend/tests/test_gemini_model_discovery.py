"""
Regression test: _call_gemini() previously only ever tried a hardcoded list
of model names ("gemini-2.5-flash-lite", "gemini-2.0-flash", ...). Confirmed
directly against Google's own docs that "gemini-2.0-flash" and
"gemini-2.0-flash-lite" -- both in that hardcoded list -- have since been
shut down, which is a very plausible reason every Gemini call was failing
live in production ("No Gemini model responded successfully"). A hardcoded
list will always go stale eventually; _list_gemini_models() asks Gemini's
own ListModels endpoint what's actually available right now instead.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.services.llm_service import _list_gemini_models


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class ListGeminiModelsTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_only_generatecontent_capable_models_without_prefix(self):
        client = MagicMock()
        client.get = AsyncMock(return_value=FakeResponse({
            "models": [
                {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-embedding-001", "supportedGenerationMethods": ["embedContent"]},
                {"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]},
            ]
        }))
        names = await _list_gemini_models(client, "fake-key")
        self.assertIn("gemini-2.5-flash", names)
        self.assertIn("gemini-2.5-pro", names)
        self.assertNotIn("gemini-embedding-001", names)
        self.assertTrue(all(not n.startswith("models/") for n in names))

    async def test_flash_models_are_prioritized_over_pro(self):
        client = MagicMock()
        client.get = AsyncMock(return_value=FakeResponse({
            "models": [
                {"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
            ]
        }))
        names = await _list_gemini_models(client, "fake-key")
        self.assertEqual(names[0], "gemini-2.5-flash")

    async def test_preview_models_are_deprioritized_to_the_end(self):
        client = MagicMock()
        client.get = AsyncMock(return_value=FakeResponse({
            "models": [
                {"name": "models/gemini-3-flash-preview", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
            ]
        }))
        names = await _list_gemini_models(client, "fake-key")
        self.assertEqual(names[0], "gemini-2.5-flash")
        self.assertEqual(names[-1], "gemini-3-flash-preview")

    async def test_returns_empty_list_on_failure_instead_of_raising(self):
        client = MagicMock()
        client.get = AsyncMock(side_effect=RuntimeError("network error"))
        names = await _list_gemini_models(client, "fake-key")
        self.assertEqual(names, [])


if __name__ == "__main__":
    unittest.main()
