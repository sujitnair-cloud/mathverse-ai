"""Regression checks using an isolated database; no live AI or account access."""
import os
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.database import Base, get_db
from app.core.auth import get_current_user
from app.api.routes import quiz, history, classrooms
from app.models.models import SolveHistory


class LearningFlows(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
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
        self.app.include_router(quiz.router)
        self.app.include_router(history.router)
        self.app.include_router(classrooms.router)
        self.app.dependency_overrides[get_db] = db
        self.app.dependency_overrides[get_current_user] = lambda: None
        self.client = TestClient(self.app)

    async def asyncTearDown(self):
        self.client.close()
        await self.engine.dispose()

    async def test_quiz_grades_original_questions_and_hides_answers(self):
        questions = [{'question': '2 + 2?', 'options': ['A) 4', 'B) 5'],
                      'answer': 'A', 'explanation': 'Two pairs make four.'}]
        generator = AsyncMock(return_value=questions)
        with patch.object(quiz, 'generate_quiz_questions', generator):
            response = self.client.post('/quiz/generate', json={
                'topic': 'algebra', 'count': 1, 'session_id': 'sess_test'})
            self.assertEqual(response.status_code, 200, response.text)
            data = response.json()
            self.assertNotIn('answer', data['questions'][0])
            self.assertNotIn('explanation', data['questions'][0])
            submission = {'quiz_id': data['quiz_id'], 'session_id': 'sess_test', 'user_answers': ['A']}
            wrong_owner = self.client.post('/quiz/submit', json={**submission, 'session_id': 'sess_other'})
            self.assertEqual(wrong_owner.status_code, 404)
            invalid = self.client.post('/quiz/submit', json={**submission, 'user_answers': ['Z']})
            self.assertEqual(invalid.status_code, 400)
            response = self.client.post('/quiz/submit', json=submission)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['score'], 100)
            self.assertEqual(generator.await_count, 1)
            self.assertEqual(self.client.post('/quiz/submit', json=submission).status_code, 404)

    async def test_invalid_generation_count(self):
        response = self.client.post('/quiz/generate', json={
            'topic': 'algebra', 'count': 0, 'session_id': 'sess_test'})
        self.assertEqual(response.status_code, 422)

    async def test_classroom_assignment_and_feedback_permissions(self):
        self.assertEqual(self.client.get('/classrooms').status_code, 401)
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
        response = self.client.post('/classrooms', json={'name': 'Year 9 Algebra'})
        self.assertEqual(response.status_code, 201, response.text)
        classroom = response.json()
        base = f"/classrooms/{classroom['id']}"
        assignment = self.client.post(base + '/assignments', json={
            'title': 'Equations', 'instructions': 'Solve 2x = 10 and show your working.'})
        self.assertEqual(assignment.status_code, 201, assignment.text)
        assignment_id = assignment.json()['id']
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2)
        self.assertEqual(self.client.get(base).status_code, 403)
        joined = self.client.post('/classrooms/join', json={'code': classroom['join_code']})
        self.assertEqual(joined.status_code, 200)
        self.assertIsNone(joined.json()['join_code'])
        self.assertEqual(self.client.post(base + '/assignments', json={
            'title': 'Unauthorized', 'instructions': 'No'}).status_code, 403)
        submitted = self.client.post(f'{base}/assignments/{assignment_id}/submit', json={'work': 'Divide both sides by 2. x = 5.'})
        self.assertEqual(submitted.status_code, 201, submitted.text)
        self.assertEqual(self.client.post(f'{base}/assignments/{assignment_id}/submit', json={'work': 'Duplicate'}).status_code, 409)
        review_url = f"{base}/submissions/{submitted.json()['id']}"
        self.assertEqual(self.client.patch(review_url, json={'score': 100}).status_code, 403)
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=3)
        self.client.post('/classrooms/join', json={'code': classroom['join_code']})
        self.assertEqual(self.client.get(base).json()['submissions'], [])
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
        self.assertEqual(self.client.patch(review_url, json={'score': 101}).status_code, 422)
        self.assertEqual(self.client.patch(review_url, json={'score': 100, 'feedback': 'Clear working.'}).status_code, 200)
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2)
        work = self.client.get(base).json()['submissions'][0]
        self.assertEqual(work['score'], 100)
        self.assertEqual(work['feedback'], 'Clear working.')

    async def test_account_history_cannot_be_read_or_deleted_by_guest(self):
        async with self.sessions() as db:
            item = SolveHistory(session_id='42', problem='2+2', result={'answer': '4'})
            db.add(item)
            await db.commit()
            item_id = item.id
        self.assertEqual(self.client.get('/history?session_id=42').status_code, 400)
        self.assertEqual(self.client.delete(f'/history/{item_id}?session_id=sess_other').status_code, 404)
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=42)
        response = self.client.get('/history?session_id=sess_browser')
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['history'][0]['answer'], '4')
        self.assertEqual(self.client.delete('/history?session_id=sess_browser').status_code, 200)
        self.assertEqual(self.client.get('/history?session_id=sess_browser').json()['count'], 0)


if __name__ == '__main__':
    unittest.main()
