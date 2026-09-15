"""
Regression test: when the structured (SymPy) solver fails, the AI fallback
in POST /solve previously only ran for paid users (`if sympy_failed and
is_paid`) -- a free or anonymous user hitting any structured-solver gap got
a dead-end error with no answer at all, even for a problem well within the
AI's real capability. This is now a deliberate product decision to extend
the fallback to everyone (existing per-request/per-day solve-count limits
still cap usage); this test locks that in for an anonymous request.
"""
import unittest
from unittest.mock import patch


class LLMFallbackAvailableToFreeUsersTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from app.core.database import Base, get_db
        from app.core.auth import get_current_user
        from app.api.routes import solve

        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async def db():
            async with sessions() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        self.app = FastAPI()
        self.app.include_router(solve.router, prefix="/api/v1")
        self.app.dependency_overrides[get_db] = db
        self.app.dependency_overrides[get_current_user] = lambda: None  # anonymous
        self.client = TestClient(self.app)

    async def asyncTearDown(self):
        self.client.close()
        await self.engine.dispose()

    async def test_anonymous_user_gets_llm_answer_when_sympy_fails(self):
        failed_sympy_result = {
            "problem": "bogus", "topic": "algebra_general", "difficulty": "basic",
            "steps": [], "answer": None, "latex_answer": None, "alternate_method": None,
            "formulas_used": [], "common_mistakes": [], "similar_problems": [],
            "error": "This doesn't look like a solvable expression or equation",
        }
        llm_result = {
            "answer": "42", "latex_answer": "42", "steps": [], "explanation": "fixture",
            "formulas_used": [], "common_mistakes": [], "similar_problems": [],
        }
        with patch("app.api.routes.solve.solve_expression", return_value=failed_sympy_result), \
             patch("app.api.routes.solve.llm_full_solve", return_value=llm_result) as mock_llm, \
             patch("app.api.routes.solve.get_explanation", return_value=None):
            resp = self.client.post("/api/v1/solve", json={
                "problem": "bogus", "session_id": "sess_test_anon_session",
            })
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["answer"], "42")
        self.assertIsNone(body["error"])
        mock_llm.assert_called_once()


if __name__ == "__main__":
    unittest.main()
