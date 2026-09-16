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


class LifetimeFreeLimitTests(unittest.IsolatedAsyncioTestCase):
    """
    The free-tier solve limit is a one-time lifetime allowance, not a
    daily-refreshing quota -- a signed-in free account that has used its
    full allowance must be blocked even if daily_solves was just reset to
    0 a moment ago, and an anonymous session gets the same lifetime
    allowance tied to its session_id instead of an account. Uses the real
    FREE_LIFETIME_LIMIT constant rather than a hardcoded number so this
    doesn't need updating every time that limit is adjusted.
    """

    async def asyncSetUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from app.core.database import Base, get_db
        from app.core.auth import get_current_user
        from app.api.routes import solve

        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async def db():
            async with self.sessions() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        self.app = FastAPI()
        self.app.include_router(solve.router, prefix="/api/v1")
        self.app.dependency_overrides[get_db] = db
        self.get_current_user_key = get_current_user
        self.client = TestClient(self.app)

    async def asyncTearDown(self):
        self.client.close()
        await self.engine.dispose()

    async def _solve(self, problem="2 + 2", session_id="sess_test"):
        with patch("app.api.routes.solve.get_explanation", return_value=None):
            return self.client.post(
                "/api/v1/solve", json={"problem": problem, "session_id": session_id}
            )

    async def test_signed_in_free_user_blocked_at_lifetime_limit_even_right_after_daily_reset(self):
        from app.models.models import User
        from app.api.routes.solve import FREE_LIFETIME_LIMIT
        user = User(
            google_id="g-limit", email="limit@example.com", subscription_plan="free",
            total_solves=FREE_LIFETIME_LIMIT, daily_solves=0, daily_solves_reset_at=None,
        )
        self.app.dependency_overrides[self.get_current_user_key] = lambda: user
        resp = await self._solve()
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Upgrade", resp.json()["detail"])

    async def test_signed_in_free_user_allowed_just_under_the_limit(self):
        from app.models.models import User
        from app.api.routes.solve import FREE_LIFETIME_LIMIT
        user = User(
            google_id="g-ok", email="ok@example.com", subscription_plan="free",
            total_solves=FREE_LIFETIME_LIMIT - 1, daily_solves=0,
        )
        self.app.dependency_overrides[self.get_current_user_key] = lambda: user
        resp = await self._solve()
        self.assertEqual(resp.status_code, 200)

    async def test_paid_plan_is_never_blocked_by_the_lifetime_limit(self):
        from app.models.models import User
        user = User(
            google_id="g-pro", email="pro@example.com", subscription_plan="pro",
            total_solves=5000,
        )
        self.app.dependency_overrides[self.get_current_user_key] = lambda: user
        resp = await self._solve()
        self.assertEqual(resp.status_code, 200)

    async def test_anonymous_session_blocked_after_lifetime_limit_solves(self):
        from app.models.models import SolveHistory
        from app.core.auth import get_current_user
        from app.api.routes.solve import FREE_LIFETIME_LIMIT
        self.app.dependency_overrides[get_current_user] = lambda: None
        async with self.sessions() as session:
            for i in range(FREE_LIFETIME_LIMIT):
                session.add(SolveHistory(session_id="sess_full", problem=f"p{i}", result={}))
            await session.commit()
        resp = await self._solve(session_id="sess_full")
        self.assertEqual(resp.status_code, 429)
        self.assertIn("upgrade", resp.json()["detail"].lower())

    async def test_anonymous_session_allowed_just_under_the_limit(self):
        from app.models.models import SolveHistory
        from app.core.auth import get_current_user
        from app.api.routes.solve import FREE_LIFETIME_LIMIT
        self.app.dependency_overrides[get_current_user] = lambda: None
        async with self.sessions() as session:
            for i in range(FREE_LIFETIME_LIMIT - 1):
                session.add(SolveHistory(session_id="sess_almost_full", problem=f"p{i}", result={}))
            await session.commit()
        resp = await self._solve(session_id="sess_almost_full")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
