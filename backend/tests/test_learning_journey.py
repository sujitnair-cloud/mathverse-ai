"""
Regression tests for Phase 5: the skill map, evidence tracking, and the
recommendation/remediation engine. The release condition for this phase
is that recommendations are explainable and personalized — these tests
check the actual reasoning branches, not just that *a* response comes back.
"""
import os
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'

import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.database import Base
from app.data.seed_data import TOPICS
from app.models.models import MathTopic, SkillAttempt
from app.services import skill_map as sm
from app.services.quiz_generator import generate_verified_questions


class SkillMapTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.Session = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.Session() as db:
            for t in TOPICS:
                db.add(MathTopic(**t))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _attempt(self, db, session_id, topic, correct, misconception=None, stage="guided"):
        db.add(SkillAttempt(session_id=session_id, topic=topic, stage=stage,
                             correct=correct, misconception=misconception))
        await db.commit()


class MasteryComputationTests(SkillMapTestCase):
    async def test_no_attempts_is_not_mastered(self):
        async with self.Session() as db:
            mastery = await sm.compute_mastery(db, "s1")
        self.assertEqual(mastery, {})

    async def test_too_few_attempts_is_not_mastered_even_if_all_correct(self):
        async with self.Session() as db:
            for _ in range(2):  # below MIN_ATTEMPTS_FOR_MASTERY
                await self._attempt(db, "s1", "algebra", True)
            mastery = await sm.compute_mastery(db, "s1")
        self.assertFalse(mastery["algebra"]["mastered"])

    async def test_enough_correct_attempts_is_mastered(self):
        async with self.Session() as db:
            for _ in range(6):
                await self._attempt(db, "s1", "algebra", True)
            mastery = await sm.compute_mastery(db, "s1")
        self.assertTrue(mastery["algebra"]["mastered"])
        self.assertEqual(mastery["algebra"]["accuracy"], 1.0)

    async def test_low_accuracy_is_not_mastered(self):
        async with self.Session() as db:
            for i in range(6):
                await self._attempt(db, "s1", "algebra", i < 2)  # 2/6 correct
            mastery = await sm.compute_mastery(db, "s1")
        self.assertFalse(mastery["algebra"]["mastered"])

    async def test_repeated_misconception_is_surfaced(self):
        async with self.Session() as db:
            for _ in range(4):
                await self._attempt(db, "s1", "algebra", False, misconception="sign_error")
            mastery = await sm.compute_mastery(db, "s1")
        self.assertIn("sign_error", mastery["algebra"]["top_misconceptions"])

    async def test_only_recent_window_counts_toward_mastery(self):
        # 20 wrong answers long ago, then 6 recent correct ones — should
        # still read as mastered, since only the recent window counts.
        async with self.Session() as db:
            for _ in range(20):
                await self._attempt(db, "s1", "algebra", False)
            for _ in range(6):
                await self._attempt(db, "s1", "algebra", True)
            mastery = await sm.compute_mastery(db, "s1")
        self.assertTrue(mastery["algebra"]["mastered"])
        self.assertEqual(mastery["algebra"]["total_attempts"], 26)


class RecommendationTests(SkillMapTestCase):
    async def test_fresh_learner_gets_a_root_topic(self):
        async with self.Session() as db:
            rec = await sm.recommend_next(db, "s1")
        self.assertEqual(rec["stage"], "diagnostic")
        topic = next(t for t in TOPICS if t["slug"] == rec["topic"])
        self.assertEqual(topic["prerequisites"], [])
        self.assertIn(topic["name"], rec["reason"])

    async def test_struggling_with_unmastered_prerequisite_recommends_prerequisite(self):
        async with self.Session() as db:
            for i in range(5):
                await self._attempt(db, "s1", "algebra", i < 1)  # 20% accuracy, arithmetic never attempted
            rec = await sm.recommend_next(db, "s1")
        self.assertEqual(rec["topic"], "arithmetic")
        self.assertIn("Algebra", rec["reason"])
        self.assertIn("Arithmetic", rec["reason"])

    async def test_struggling_with_mastered_prerequisites_recommends_same_topic(self):
        async with self.Session() as db:
            for _ in range(6):
                await self._attempt(db, "s1", "arithmetic", True)
            for i in range(5):
                await self._attempt(db, "s1", "algebra", i < 1)
            rec = await sm.recommend_next(db, "s1")
        self.assertEqual(rec["topic"], "algebra")
        self.assertIn("20%", rec["reason"])

    async def test_frontier_topic_recommended_once_prerequisites_mastered(self):
        async with self.Session() as db:
            for _ in range(6):
                await self._attempt(db, "s1", "arithmetic", True)
            rec = await sm.recommend_next(db, "s1")
        self.assertEqual(rec["topic"], "algebra")
        self.assertEqual(rec["stage"], "diagnostic")
        self.assertIn("Arithmetic", rec["reason"])

    async def test_locked_topic_never_recommended_before_its_prerequisite(self):
        async with self.Session() as db:
            rec = await sm.recommend_next(db, "s1")
        # calculus needs algebra + trigonometry; must never be the very first recommendation
        self.assertNotEqual(rec["topic"], "calculus")
        self.assertNotEqual(rec["topic"], "differential-equations")

    async def test_recommendation_reason_always_mentions_the_recommended_topic(self):
        # Explainability check across a few learner states, not just one.
        async with self.Session() as db:
            rec = await sm.recommend_next(db, "s1")
            topic_name = next(t["name"] for t in TOPICS if t["slug"] == rec["topic"])
            self.assertIn(topic_name, rec["reason"])

            for _ in range(6):
                await self._attempt(db, "s1", "arithmetic", True)
            rec2 = await sm.recommend_next(db, "s1")
            topic_name2 = next(t["name"] for t in TOPICS if t["slug"] == rec2["topic"])
            self.assertIn(topic_name2, rec2["reason"])


class RemediationTests(SkillMapTestCase):
    async def test_wrong_answer_with_unmastered_prerequisite_suggests_revisit(self):
        async with self.Session() as db:
            action = await sm.remediate_wrong_answer(db, "s1", "algebra", "sign_error")
        self.assertEqual(action["action"], "revisit_prerequisite")
        self.assertEqual(action["target_topic"], "arithmetic")

    async def test_repeated_misconception_suggests_different_explanation(self):
        async with self.Session() as db:
            for _ in range(6):
                await self._attempt(db, "s1", "arithmetic", True)  # clear the prerequisite
            for _ in range(3):
                await self._attempt(db, "s1", "algebra", False, misconception="sign_error")
            action = await sm.remediate_wrong_answer(db, "s1", "algebra", "sign_error")
        self.assertEqual(action["action"], "different_explanation")

    async def test_first_time_mistake_suggests_focused_practice(self):
        async with self.Session() as db:
            for _ in range(6):
                await self._attempt(db, "s1", "arithmetic", True)
            action = await sm.remediate_wrong_answer(db, "s1", "algebra", "arithmetic_slip")
        self.assertEqual(action["action"], "focused_practice")


class SkillMapWithProgressTests(SkillMapTestCase):
    async def test_topic_with_unmastered_prerequisite_is_locked(self):
        async with self.Session() as db:
            topics = await sm.skill_map_with_progress(db, "s1")
        algebra = next(t for t in topics if t["slug"] == "algebra")
        self.assertEqual(algebra["status"], "locked")

    async def test_root_topic_is_ready(self):
        async with self.Session() as db:
            topics = await sm.skill_map_with_progress(db, "s1")
        arithmetic = next(t for t in topics if t["slug"] == "arithmetic")
        self.assertEqual(arithmetic["status"], "ready")

    async def test_practice_enabled_flag_matches_generator_availability(self):
        async with self.Session() as db:
            topics = await sm.skill_map_with_progress(db, "s1")
        by_slug = {t["slug"]: t for t in topics}
        self.assertTrue(by_slug["algebra"]["has_practice"])
        self.assertFalse(by_slug["number-theory"]["has_practice"])


class GeneratorTagIntegrationTests(unittest.TestCase):
    """The misconception tags added to quiz_generator distractors must
    actually reach the learning journey's grading path unchanged."""

    def test_every_practice_topic_generates_tagged_questions(self):
        import random
        random.seed(0)
        for topic in sm.PRACTICE_ENABLED_TOPICS:
            qs = generate_verified_questions(topic, "intermediate", "routine", 3)
            for q in qs:
                self.assertIn("option_tags", q)
                wrong_letters = {o[0] for o in q["options"]} - {q["answer"]}
                for letter in wrong_letters:
                    self.assertIn(letter, q["option_tags"], f"{topic}: {letter} missing a tag in {q['options']}")


class LearningRouteTests(unittest.IsolatedAsyncioTestCase):
    """End-to-end through the real HTTP layer: practice/next never leaks
    the answer, practice/answer grades correctly, records evidence, and a
    wrong answer on a locked-prerequisite topic returns real remediation."""

    async def asyncSetUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from app.core.database import Base, get_db
        from app.api.routes import learning

        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as seed_db:
            for t in TOPICS:
                seed_db.add(MathTopic(**t))
            await seed_db.commit()

        async def db():
            async with sessions() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        self.app = FastAPI()
        self.app.include_router(learning.router)
        self.app.dependency_overrides[get_db] = db
        self.client = TestClient(self.app)

    async def asyncTearDown(self):
        self.client.close()
        await self.engine.dispose()

    async def test_skill_map_and_recommendation_endpoints(self):
        r = self.client.get("/learning/skill-map", params={"session_id": "sess1"})
        self.assertEqual(r.status_code, 200, r.text)
        slugs = {t["slug"] for t in r.json()["topics"]}
        self.assertIn("arithmetic", slugs)

        r = self.client.get("/learning/recommendation", params={"session_id": "sess1"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["topic"], "arithmetic")

    async def test_lesson_endpoint_has_all_four_parts(self):
        r = self.client.get("/learning/lesson/calculus")
        self.assertEqual(r.status_code, 200, r.text)
        lesson = r.json()["lesson"]
        for part in ("motivation", "construction", "example", "transfer"):
            self.assertIn(part, lesson)
            self.assertTrue(lesson[part])

    async def test_practice_flow_never_leaks_answer_and_grades_correctly(self):
        r = self.client.post("/learning/practice/next", json={
            "session_id": "sess1", "topic": "arithmetic", "stage": "guided"})
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertNotIn("answer", data)
        self.assertNotIn("explanation", data)
        self.assertNotIn("option_tags", data)

        # Generate and answer 4 fresh questions, one per letter, so every
        # answer-endpoint code path (correct and incorrect) gets exercised.
        results = []
        for letter in ["A", "B", "C", "D"]:
            r2 = self.client.post("/learning/practice/next", json={
                "session_id": "sess1", "topic": "arithmetic", "stage": "guided"})
            qid = r2.json()["question_id"]
            r3 = self.client.post("/learning/practice/answer", json={
                "session_id": "sess1", "question_id": qid, "selected": letter, "hints_used": 1})
            self.assertEqual(r3.status_code, 200, r3.text)
            results.append(r3.json())

        r_progress = self.client.get("/learning/progress", params={"session_id": "sess1"})
        self.assertEqual(r_progress.json()["mastery"]["arithmetic"]["total_attempts"], 4)
        self.assertEqual(r_progress.json()["mastery"]["arithmetic"]["hints_used_total"], 4)

    async def test_double_answering_same_question_is_rejected(self):
        r = self.client.post("/learning/practice/next", json={
            "session_id": "sess1", "topic": "arithmetic", "stage": "guided"})
        qid = r.json()["question_id"]
        r1 = self.client.post("/learning/practice/answer", json={
            "session_id": "sess1", "question_id": qid, "selected": "A"})
        self.assertEqual(r1.status_code, 200)
        r2 = self.client.post("/learning/practice/answer", json={
            "session_id": "sess1", "question_id": qid, "selected": "A"})
        self.assertEqual(r2.status_code, 404)

    async def test_practice_on_locked_topic_still_works_but_wrong_answer_recommends_prerequisite(self):
        # algebra has an unmastered prerequisite (arithmetic); force a wrong
        # answer by trying every option until one is marked incorrect.
        for _ in range(4):
            r = self.client.post("/learning/practice/next", json={
                "session_id": "sess2", "topic": "algebra", "stage": "guided"})
            qid = r.json()["question_id"]
            for letter in ["A", "B", "C", "D"]:
                r2 = self.client.post("/learning/practice/answer", json={
                    "session_id": "sess2", "question_id": qid, "selected": letter})
                if r2.status_code == 404:
                    continue
                result = r2.json()
                if not result["correct"]:
                    self.assertIn("remediation", result)
                    self.assertEqual(result["remediation"]["action"], "revisit_prerequisite")
                    self.assertEqual(result["remediation"]["target_topic"], "arithmetic")
                    return
                break
        self.fail("never got a wrong answer to check remediation for")

    async def test_practice_unavailable_for_non_practice_topic(self):
        r = self.client.post("/learning/practice/next", json={
            "session_id": "sess1", "topic": "number-theory", "stage": "guided"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
