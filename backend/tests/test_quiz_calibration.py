"""Offline integration tests: real SQLite persistence, simulated model transport."""
import json
import unittest
from copy import deepcopy
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.database import Base
from app.services import llm_service
from app.services.quiz_policy import QuizUnavailableError, quiz_prompt, validate_questions
from app.api.routes.quiz import QuizRequest, QuizSubmission, generate_quiz, submit_quiz


QUESTION = {
    'question': 'For which real p does the integral from 1 to infinity of x^(-p) converge?',
    'options': ['A) p > 1', 'B) p >= 1', 'C) p < 1', 'D) Every real p'],
    'answer': 'A',
    'explanation': 'For p != 1, the antiderivative is x^(1-p)/(1-p). Its upper limit is finite precisely when p > 1. At p = 1, log(x) diverges.',
    'skill': 'improper integral convergence',
    'difficulty_reason': 'Evaluate a parameter-dependent limit and handle the exceptional logarithmic case.',
}


class CalibrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_generates_then_reviews(self):
        caller = AsyncMock(side_effect=[json.dumps([QUESTION]), '{"accepted": true}'])
        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'openai'), patch.object(
            llm_service.settings, 'OPENAI_API_KEY', 'test-' * 8
        ), patch.object(llm_service, '_call_openai', caller):
            result = await llm_service.generate_quiz_questions('calculus', 'advanced', 1)
        self.assertEqual(result[0]['answer'], 'A')
        self.assertEqual(caller.await_count, 2)
        self.assertIn('improper-integral convergence', caller.await_args_list[0].args[0])
        self.assertIn('Solve each item independently', caller.await_args_list[1].args[0])

    async def test_rejected_or_broken_generation_never_falls_back(self):
        for responses in ([json.dumps([QUESTION]), '{"accepted": false}'], ['not json']):
            with self.subTest(responses=responses), patch.object(llm_service.settings, 'LLM_PROVIDER', 'openai'), patch.object(
                llm_service.settings, 'OPENAI_API_KEY', 'test-' * 8
            ), patch.object(llm_service, '_call_openai', AsyncMock(side_effect=responses)):
                with self.assertRaises(QuizUnavailableError):
                    await llm_service.generate_quiz_questions('calculus', 'advanced', 1)

    async def test_no_provider_is_explicitly_unavailable(self):
        with patch.object(llm_service.settings, 'LLM_PROVIDER', 'none'):
            with self.assertRaises(QuizUnavailableError):
                await llm_service.generate_quiz_questions('calculus', 'advanced', 5)

    def test_level_contracts_are_distinct(self):
        self.assertIn('one direct application', quiz_prompt('calculus', 'basic', 3))
        self.assertIn('at least two steps', quiz_prompt('calculus', 'intermediate', 3))
        self.assertIn('Taylor remainder', quiz_prompt('calculus', 'advanced', 3))
        with self.assertRaises(ValueError):
            quiz_prompt('unknown', 'advanced', 3)

    def test_malformed_and_duplicate_items_are_rejected(self):
        bad = deepcopy(QUESTION)
        bad['options'][1] = 'B) p > 1'
        for questions, count in [([QUESTION], 2), ([QUESTION, QUESTION], 2), ([bad], 1), ([{}], 1)]:
            with self.subTest(questions=questions), self.assertRaises(QuizUnavailableError):
                validate_questions(questions, count)


class QuizPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def create_quiz(self):
        with patch('app.api.routes.quiz.generate_quiz_questions', AsyncMock(return_value=[deepcopy(QUESTION)])):
            async with self.sessions() as db:
                response = await generate_quiz(QuizRequest(topic='calculus', difficulty='advanced', count=1, session_id='learner'), db)
                await db.commit()
        return response

    async def test_grades_original_saved_questions_without_regeneration(self):
        quiz = await self.create_quiz()
        self.assertEqual(set(quiz['questions'][0]), {'question', 'options'})
        with patch('app.api.routes.quiz.generate_quiz_questions', AsyncMock(side_effect=AssertionError('must not regenerate'))):
            async with self.sessions() as db:
                result = await submit_quiz(QuizSubmission(quiz_id=quiz['quiz_id'], session_id='learner', user_answers=['A']), db)
        self.assertEqual(result['score'], 100)
        self.assertEqual(result['graded_questions'][0]['question'], QUESTION['question'])

    async def test_wrong_session_and_incomplete_answers_rejected(self):
        quiz = await self.create_quiz()
        for session, answers, status in [('other', ['A'], 404), ('learner', [], 400), ('learner', ['E'], 400)]:
            async with self.sessions() as db:
                with self.assertRaises(HTTPException) as error:
                    await submit_quiz(QuizSubmission(quiz_id=quiz['quiz_id'], session_id=session, user_answers=answers), db)
                self.assertEqual(error.exception.status_code, status)


if __name__ == '__main__':
    unittest.main()
