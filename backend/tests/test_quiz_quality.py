"""
Regression tests for the Phase 3 quiz-quality work: a verified question
generator (answers computed by SymPy, not hand-written or LLM-guessed), a
topic/level/demand split instead of one flattened "difficulty", and
structural validation that rejects ambiguous questions before they're
ever shown to a student.
"""
import os
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'

import random
import unittest
from unittest.mock import AsyncMock, patch

from app.services.quiz_generator import generate_verified_questions
from app.services import llm_service
from app.services.llm_service import generate_quiz_questions, _valid_quiz_question


class VerifiedGeneratorTests(unittest.TestCase):
    """Every answer is computed by SymPy, so these check the generator's
    own bookkeeping (structure, uniqueness, count) rather than re-deriving
    the math — the math correctness was verified by hand against printed
    output for every topic during development."""

    TOPICS = ["algebra", "algebra_quadratic", "calculus", "calculus_integration",
              "trigonometry", "probability", "statistics", "geometry", "linear-algebra"]

    def test_always_returns_exactly_the_requested_count(self):
        # Some (level, demand) combinations have a narrow parameter space —
        # e.g. only a few distinct routine derivatives — and used to return
        # fewer than requested once that space was exhausted.
        random.seed(0)
        for topic in self.TOPICS:
            for level in ("basic", "intermediate", "advanced", "expert"):
                for demand in ("routine", "multi_step", "unfamiliar"):
                    with self.subTest(topic=topic, level=level, demand=demand):
                        qs = generate_verified_questions(topic, level, demand, 8)
                        self.assertEqual(len(qs), 8)

    def test_no_duplicate_option_values(self):
        random.seed(1)
        for topic in self.TOPICS:
            qs = generate_verified_questions(topic, "intermediate", "routine", 15)
            for q in qs:
                values = [o[3:] for o in q["options"]]
                with self.subTest(question=q["question"]):
                    self.assertEqual(len(set(values)), len(values))

    def test_every_question_structurally_valid(self):
        random.seed(2)
        for topic in self.TOPICS:
            for demand in ("routine", "multi_step", "unfamiliar"):
                qs = generate_verified_questions(topic, "intermediate", demand, 5)
                for q in qs:
                    with self.subTest(topic=topic, demand=demand, question=q["question"]):
                        self.assertTrue(_valid_quiz_question(q))

    def test_unknown_topic_falls_back_instead_of_crashing(self):
        qs = generate_verified_questions("underwater basket weaving", "intermediate", "routine", 3)
        self.assertEqual(len(qs), 3)

    def test_question_text_has_no_double_sign_artifacts(self):
        # "8x + -13" / "x^2 - 1x - 72" / "(x - -8)" were real bugs found by
        # hand-inspecting generator output — assert they can't come back.
        random.seed(3)
        for _ in range(100):
            for topic, demand in [("algebra", "unfamiliar"), ("algebra_quadratic", "unfamiliar")]:
                q = generate_verified_questions(topic, "intermediate", demand, 1)[0]
                text = q["question"] + " " + q["explanation"]
                self.assertNotRegex(text, r"[+\-]\s*-\s*\d", f"double-sign artifact in: {text!r}")
                self.assertNotRegex(text, r"\b1x\b", f"'1x' instead of 'x' in: {text!r}")


class QuestionValidationTests(unittest.TestCase):
    """_valid_quiz_question() is the shared gate both the LLM path and the
    API route rely on — it has to catch what a naive structural check
    (does the answer letter exist among the options?) misses."""

    def _q(self, **overrides):
        base = {"question": "2 + 2 = ?", "options": ["A) 3", "B) 4", "C) 5", "D) 6"],
                "answer": "B", "explanation": "2+2=4"}
        base.update(overrides)
        return base

    def test_valid_question_passes(self):
        self.assertTrue(_valid_quiz_question(self._q()))

    def test_rejects_duplicate_option_values(self):
        q = self._q(options=["A) 4", "B) 4", "C) 5", "D) 6"])
        self.assertFalse(_valid_quiz_question(q))

    def test_rejects_answer_not_matching_any_option(self):
        q = self._q(answer="Z")
        self.assertFalse(_valid_quiz_question(q))

    def test_rejects_missing_fields(self):
        self.assertFalse(_valid_quiz_question({"question": "x"}))
        self.assertFalse(_valid_quiz_question("not even a dict"))

    def test_rejects_too_few_options(self):
        q = self._q(options=["A) 4"])
        self.assertFalse(_valid_quiz_question(q))


class LLMPathFallbackTests(unittest.IsolatedAsyncioTestCase):
    """The LLM path must never hand a student an unvalidated question —
    invalid ones are dropped and backfilled with verified generated ones
    rather than shown or causing the request to fail."""

    async def test_invalid_llm_questions_are_filtered_and_backfilled(self):
        bad = {"question": "dup", "options": ["A) 1", "B) 1"], "answer": "A", "explanation": ""}
        good = {"question": "2+2", "options": ["A) 3", "B) 4", "C) 5", "D) 6"], "answer": "B", "explanation": "x"}
        import json as _json
        raw = _json.dumps([bad, good])
        with patch.object(llm_service.settings, "LLM_PROVIDER", "anthropic"), \
             patch.object(llm_service.settings, "ANTHROPIC_API_KEY", "sk-ant-" + "x" * 20), \
             patch.object(llm_service, "_key_looks_real", return_value=True), \
             patch.object(llm_service, "_call_anthropic", AsyncMock(return_value=raw)):
            questions = await generate_quiz_questions("algebra", "intermediate", "routine", 5)
        self.assertEqual(len(questions), 5)
        for q in questions:
            self.assertTrue(_valid_quiz_question(q))
        # The one valid LLM question should have been kept, not discarded.
        self.assertTrue(any(q["question"] == "2+2" for q in questions))

    async def test_no_llm_configured_uses_verified_generator(self):
        with patch.object(llm_service.settings, "LLM_PROVIDER", "none"):
            questions = await generate_quiz_questions("trigonometry", "intermediate", "routine", 5)
        self.assertEqual(len(questions), 5)
        for q in questions:
            self.assertTrue(_valid_quiz_question(q))


class QuizRouteTests(unittest.IsolatedAsyncioTestCase):
    """End-to-end: the demand field actually reaches question generation,
    and a generated quiz is gradeable via the existing session flow."""

    async def asyncSetUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from app.core.database import Base, get_db
        from app.api.routes import quiz

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
        self.app.include_router(quiz.router)
        self.app.dependency_overrides[get_db] = db
        self.client = TestClient(self.app)

    async def asyncTearDown(self):
        self.client.close()
        await self.engine.dispose()

    async def test_demand_reaches_generation_and_quiz_is_gradeable(self):
        captured = {}
        real_generate = generate_verified_questions

        def spy(topic, level, demand, count):
            captured["demand"] = demand
            return real_generate(topic, level, demand, count)

        with patch("app.api.routes.quiz.generate_quiz_questions", AsyncMock(side_effect=lambda t, l, d, c: spy(t, l, d, c))):
            resp = self.client.post("/quiz/generate", json={
                "topic": "algebra", "difficulty": "intermediate", "demand": "multi_step",
                "count": 3, "session_id": "sess_test",
            })
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(captured["demand"], "multi_step")
        data = resp.json()
        self.assertEqual(len(data["questions"]), 3)
        for q in data["questions"]:
            self.assertNotIn("answer", q)  # answers must never reach the client at generation time

        submission = {"quiz_id": data["quiz_id"], "session_id": "sess_test",
                      "user_answers": ["A", "A", "A"]}
        result = self.client.post("/quiz/submit", json=submission)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertIn("score", result.json())


if __name__ == "__main__":
    unittest.main()
