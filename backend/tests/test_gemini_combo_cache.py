"""
Regression test: _gemini_generate() previously re-searched every
model x api_version x auth_style combination on every single call, even
after finding a working one. That's wasteful in both latency and quota --
confirmed directly live in production: the tool-calling loop making
several Gemini calls per solve burned through the free-tier daily quota
fast. The last-known-working combo is now cached and tried first.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import llm_service


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        self.text = str(self._payload)

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class GeminiComboCacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        llm_service._LAST_GOOD_GEMINI_COMBO = None

    async def asyncTearDown(self):
        llm_service._LAST_GOOD_GEMINI_COMBO = None

    async def test_second_call_reuses_the_cached_combo_with_a_single_request(self):
        with patch.object(llm_service.settings, "GEMINI_API_KEY", "AIzaSy" + "x" * 33), \
             patch.object(llm_service, "_list_gemini_models", return_value=[]):
            mock_post = AsyncMock(return_value=FakeResponse(200))
            with patch("httpx.AsyncClient.post", mock_post):
                await llm_service._gemini_generate([{"parts": [{"text": "first"}]}])
            first_call_count = mock_post.call_count
            self.assertIsNotNone(llm_service._LAST_GOOD_GEMINI_COMBO)

            mock_post2 = AsyncMock(return_value=FakeResponse(200))
            with patch("httpx.AsyncClient.post", mock_post2):
                await llm_service._gemini_generate([{"parts": [{"text": "second"}]}])
            # Exactly one request -- the cached combo, no re-search.
            self.assertEqual(mock_post2.call_count, 1)

    async def test_falls_back_to_full_search_when_cached_combo_stops_working(self):
        llm_service._LAST_GOOD_GEMINI_COMBO = ("AIzaSy" + "x" * 33, "gemini-2.5-flash", "v1beta", "header")
        responses = [FakeResponse(404)] + [FakeResponse(200)] * 20  # cached combo dead, then search succeeds
        with patch.object(llm_service.settings, "GEMINI_API_KEY", "AIzaSy" + "x" * 33), \
             patch.object(llm_service, "_list_gemini_models", return_value=[]), \
             patch("httpx.AsyncClient.post", AsyncMock(side_effect=responses)):
            body = await llm_service._gemini_generate([{"parts": [{"text": "hi"}]}])
        self.assertIn("candidates", body)
        # A fresh, real combo was found and re-cached (not the dead one).
        self.assertIsNotNone(llm_service._LAST_GOOD_GEMINI_COMBO)


if __name__ == "__main__":
    unittest.main()
