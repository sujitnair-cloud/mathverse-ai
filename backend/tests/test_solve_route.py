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
        with patch("app.api.routes.solve.solve_with_gemini_tools", return_value=None), \
             patch("app.api.routes.solve.solve_expression", return_value=failed_sympy_result), \
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

    async def test_anonymous_user_gets_real_llm_answer_for_a_word_problem_not_a_paywall(self):
        """
        "Solve the differential equation dy/dx = 3x^2 given y=2 when x=0"
        matches _EXPERT_KEYWORDS ("differential equation") and routes through
        is_llm_first_problem(). Free/anonymous users previously got the
        SymPy-only path there (no real handling for differential equations)
        and, whenever that predictably failed, a "requires Student or Pro
        plan" error -- even though a real answer could still slip through
        via the separate "extract Final Answer from explanation" fallback,
        showing a correct answer and a paywall error at the same time. Now
        attempts a real LLM answer for everyone, same as the other fallback
        paths.
        """
        llm_result = {
            "answer": "y = x**3 + 2", "latex_answer": "y = x^3 + 2", "steps": [],
            "explanation": "fixture", "formulas_used": [], "common_mistakes": [], "similar_problems": [],
        }
        with patch("app.api.routes.solve.solve_with_gemini_tools", return_value=None), \
             patch("app.api.routes.solve.llm_full_solve", return_value=llm_result) as mock_llm, \
             patch("app.api.routes.solve.get_explanation", return_value=None):
            resp = self.client.post("/api/v1/solve", json={
                "problem": "Solve the differential equation dy/dx = 3x^2 given y=2 when x=0",
                "session_id": "sess_test_anon_diffeq",
            })
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["answer"], "y = x**3 + 2")
        self.assertIsNone(body["error"])
        mock_llm.assert_called_once()


class GeminiToolsIsThePrimaryPathTests(unittest.IsolatedAsyncioTestCase):
    """
    solve_with_gemini_tools() is now tried first for every request, not
    just detected structured-solver failures -- Gemini reads the problem
    directly in any phrasing/notation and calls the structured solver as a
    verified-computation tool, so a new phrasing doesn't need a new
    hand-written pattern to be answered correctly.
    """

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
        self.app.dependency_overrides[get_current_user] = lambda: None
        self.client = TestClient(self.app)

    async def asyncTearDown(self):
        self.client.close()
        await self.engine.dispose()

    async def test_result_from_the_tool_calling_path_is_used_and_sympy_is_never_touched(self):
        tool_result = {
            "answer": "1/sqrt(1 - x**2)", "latex_answer": "1/sqrt(1-x^2)", "steps": [],
            "explanation": "fixture", "formulas_used": [], "common_mistakes": [], "similar_problems": [],
        }
        with patch("app.api.routes.solve.solve_with_gemini_tools", return_value=tool_result) as mock_tools, \
             patch("app.api.routes.solve.solve_expression") as mock_sympy, \
             patch("app.api.routes.solve.get_explanation", return_value=None):
            resp = self.client.post("/api/v1/solve", json={
                "problem": "If y = sin^-1(x), what is dy/dx?",
                "session_id": "sess_test_tools_primary",
            })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["answer"], "1/sqrt(1 - x**2)")
        mock_tools.assert_called_once()
        mock_sympy.assert_not_called()

    async def test_obviously_simple_input_skips_the_llm_round_trip_entirely(self):
        """
        Every solve now costs a multi-second LLM round trip by default --
        acceptable for handling any phrasing, but wasteful for something
        with zero ambiguity to begin with. A short input with no natural-
        language content at all skips solve_with_gemini_tools entirely and
        goes straight to the free, instant structured solver.
        """
        sympy_result = {
            "problem": "2 + 2", "topic": "algebra_general", "difficulty": "basic",
            "steps": [], "answer": "4", "latex_answer": "4", "alternate_method": None,
            "formulas_used": [], "common_mistakes": [], "similar_problems": [], "error": None,
        }
        with patch("app.api.routes.solve.solve_with_gemini_tools") as mock_tools, \
             patch("app.api.routes.solve.solve_expression", return_value=sympy_result) as mock_sympy, \
             patch("app.api.routes.solve.get_explanation", return_value=None):
            resp = self.client.post("/api/v1/solve", json={
                "problem": "2 + 2", "session_id": "sess_test_fast_path",
            })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["answer"], "4")
        mock_tools.assert_not_called()
        mock_sympy.assert_called_once()

    async def test_ambiguous_looking_input_still_uses_the_llm_round_trip(self):
        # Contrast case: anything with real natural-language content still
        # goes through the primary path, even if fairly short.
        with patch("app.api.routes.solve.solve_with_gemini_tools", return_value=None) as mock_tools, \
             patch("app.api.routes.solve.solve_expression", return_value={
                 "problem": "x", "topic": "algebra_general", "difficulty": "basic", "steps": [],
                 "answer": "4", "latex_answer": "4", "alternate_method": None, "formulas_used": [],
                 "common_mistakes": [], "similar_problems": [], "error": None,
             }), \
             patch("app.api.routes.solve.get_explanation", return_value=None):
            self.client.post("/api/v1/solve", json={
                "problem": "What is two plus two?", "session_id": "sess_test_not_fast_path",
            })
        mock_tools.assert_called_once()

    async def test_quota_exceeded_falls_back_to_the_structured_solver_with_a_note(self):
        # Must be non-trivial (contains prose) so the fast-path for "obviously
        # simple" inputs doesn't skip the tool-calling path before this test
        # ever gets to exercise the quota-exceeded sentinel handling.
        problem = "If y = sin^-1(x), what is dy/dx?"
        sympy_result = {
            "problem": problem, "topic": "calculus_differentiation", "difficulty": "basic",
            "steps": [], "answer": "1/sqrt(1 - x**2)", "latex_answer": "1/sqrt(1-x^2)",
            "alternate_method": None, "formulas_used": [], "common_mistakes": [],
            "similar_problems": [], "error": None,
        }
        with patch("app.api.routes.solve.solve_with_gemini_tools", return_value={"_quota_exceeded": True}), \
             patch("app.api.routes.solve.solve_expression", return_value=sympy_result), \
             patch("app.api.routes.solve.get_explanation", return_value=None):
            resp = self.client.post("/api/v1/solve", json={
                "problem": problem, "session_id": "sess_test_tools_quota",
            })
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["answer"], "1/sqrt(1 - x**2)")
        self.assertIn("structured solver", body["error"])


class DailyFreeLimitTests(unittest.IsolatedAsyncioTestCase):
    """
    The free-tier solve limit is a daily quota on a rolling 24h window, not
    a one-time lifetime allowance -- anonymous visitors get ANON_DAILY_LIMIT
    (15), signed-in free accounts get FREE_DAILY_LIMIT (20). Uses the real
    constants rather than hardcoded numbers so this doesn't need updating
    every time a limit is adjusted.
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
        with patch("app.api.routes.solve.solve_with_gemini_tools", return_value=None), \
             patch("app.api.routes.solve.get_explanation", return_value=None):
            return self.client.post(
                "/api/v1/solve", json={"problem": problem, "session_id": session_id}
            )

    async def test_signed_in_free_user_blocked_at_daily_limit(self):
        from datetime import datetime, timezone
        from app.models.models import User
        from app.api.routes.solve import FREE_DAILY_LIMIT
        user = User(
            google_id="g-limit", email="limit@example.com", subscription_plan="free",
            daily_solves=FREE_DAILY_LIMIT, daily_solves_reset_at=datetime.now(timezone.utc),
        )
        self.app.dependency_overrides[self.get_current_user_key] = lambda: user
        resp = await self._solve()
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Upgrade", resp.json()["detail"])

    async def test_signed_in_free_user_allowed_just_under_the_daily_limit(self):
        from datetime import datetime, timezone
        from app.models.models import User
        from app.api.routes.solve import FREE_DAILY_LIMIT
        user = User(
            google_id="g-ok", email="ok@example.com", subscription_plan="free",
            daily_solves=FREE_DAILY_LIMIT - 1, daily_solves_reset_at=datetime.now(timezone.utc),
        )
        self.app.dependency_overrides[self.get_current_user_key] = lambda: user
        resp = await self._solve()
        self.assertEqual(resp.status_code, 200)

    async def test_signed_in_free_user_gets_a_fresh_quota_after_24h(self):
        from datetime import datetime, timedelta, timezone
        from app.models.models import User
        from app.api.routes.solve import FREE_DAILY_LIMIT
        user = User(
            google_id="g-reset", email="reset@example.com", subscription_plan="free",
            daily_solves=FREE_DAILY_LIMIT,  # exhausted, but the reset window has passed
            daily_solves_reset_at=datetime.now(timezone.utc) - timedelta(days=1, minutes=1),
        )
        self.app.dependency_overrides[self.get_current_user_key] = lambda: user
        resp = await self._solve()
        self.assertEqual(resp.status_code, 200)

    async def test_paid_plan_is_never_blocked_by_the_daily_limit(self):
        from app.models.models import User
        user = User(
            google_id="g-pro", email="pro@example.com", subscription_plan="pro",
            daily_solves=5000,
        )
        self.app.dependency_overrides[self.get_current_user_key] = lambda: user
        resp = await self._solve()
        self.assertEqual(resp.status_code, 200)

    async def test_anonymous_session_blocked_after_daily_limit_solves(self):
        from app.models.models import SolveHistory
        from app.core.auth import get_current_user
        from app.api.routes.solve import ANON_DAILY_LIMIT
        self.app.dependency_overrides[get_current_user] = lambda: None
        async with self.sessions() as session:
            for i in range(ANON_DAILY_LIMIT):
                session.add(SolveHistory(session_id="sess_full", problem=f"p{i}", result={}))
            await session.commit()
        resp = await self._solve(session_id="sess_full")
        self.assertEqual(resp.status_code, 429)
        self.assertIn("upgrade", resp.json()["detail"].lower())

    async def test_anonymous_session_allowed_just_under_the_daily_limit(self):
        from app.models.models import SolveHistory
        from app.core.auth import get_current_user
        from app.api.routes.solve import ANON_DAILY_LIMIT
        self.app.dependency_overrides[get_current_user] = lambda: None
        async with self.sessions() as session:
            for i in range(ANON_DAILY_LIMIT - 1):
                session.add(SolveHistory(session_id="sess_almost_full", problem=f"p{i}", result={}))
            await session.commit()
        resp = await self._solve(session_id="sess_almost_full")
        self.assertEqual(resp.status_code, 200)

    async def test_anonymous_session_gets_a_fresh_quota_after_24h(self):
        from datetime import datetime, timedelta, timezone
        from app.models.models import SolveHistory
        from app.core.auth import get_current_user
        from app.api.routes.solve import ANON_DAILY_LIMIT
        self.app.dependency_overrides[get_current_user] = lambda: None
        old = datetime.now(timezone.utc) - timedelta(days=2)
        async with self.sessions() as session:
            for i in range(ANON_DAILY_LIMIT):
                # Exhausted the limit, but every one of these rows is
                # outside the rolling 24h window -- must not count.
                session.add(SolveHistory(session_id="sess_old", problem=f"p{i}", result={}, created_at=old))
            await session.commit()
        resp = await self._solve(session_id="sess_old")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
