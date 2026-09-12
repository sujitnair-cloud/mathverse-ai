import secrets
from datetime import datetime, timezone, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from app.core.database import get_db
from app.models.models import QuizAttempt, QuizSession
from app.services.llm_service import generate_quiz_questions, _valid_quiz_question

router = APIRouter()

class QuizRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=100)
    difficulty: Literal['basic', 'intermediate', 'advanced'] = 'intermediate'
    # Independent of `difficulty` (how advanced the topic/formulas are): how
    # much reasoning a routine application takes at that same level. A
    # single flattened "difficulty" was collapsing two different things a
    # learner (or a teacher building an assignment) may want to vary
    # separately — a routine question and an unfamiliar one at the same
    # level are not interchangeable.
    demand: Literal['routine', 'multi_step', 'unfamiliar'] = 'routine'
    count: int = Field(default=5, ge=1, le=20)
    session_id: str = Field(min_length=1, max_length=64)

class QuizSubmission(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    quiz_id: str = Field(min_length=1, max_length=64)
    user_answers: list[str] = Field(min_length=1, max_length=20)

@router.post('/quiz/generate')
async def generate_quiz(req: QuizRequest, db: AsyncSession = Depends(get_db)):
    questions = await generate_quiz_questions(req.topic, req.difficulty, req.demand, req.count)
    # generate_quiz_questions() already validates every question before
    # returning it — this is a defense-in-depth check at the API boundary,
    # not the primary line of defense.
    if not questions or len(questions) > 20 or any(not _valid_quiz_question(q) for q in questions):
        raise HTTPException(status_code=502, detail='Unable to prepare a valid quiz. Please try again.')
    quiz = QuizSession(id=secrets.token_urlsafe(32), session_id=req.session_id,
                       topic=req.topic, difficulty=req.difficulty, questions=questions)
    db.add(quiz)
    await db.flush()
    return {'quiz_id': quiz.id, 'topic': quiz.topic, 'difficulty': quiz.difficulty,
            'questions': [{'question': q['question'], 'options': q['options']} for q in questions]}

@router.post('/quiz/submit')
async def submit_quiz(submission: QuizSubmission, db: AsyncSession = Depends(get_db)):
    quiz = await db.get(QuizSession, submission.quiz_id)
    if quiz is None or quiz.session_id != submission.session_id:
        raise HTTPException(status_code=404, detail='Quiz not found. Please start a new quiz.')
    created = quiz.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > timedelta(days=1):
        raise HTTPException(status_code=410, detail='This quiz expired. Please start a new quiz.')
    if len(submission.user_answers) != len(quiz.questions):
        raise HTTPException(status_code=400, detail='Please answer every question.')
    graded = []
    for q, answer in zip(quiz.questions, submission.user_answers):
        answer = answer.strip().upper()
        if answer not in {o[0].upper() for o in q['options']}:
            raise HTTPException(status_code=400, detail='Please select a valid answer for every question.')
        graded.append({'question': q['question'], 'user_answer': answer,
                       'correct_answer': q['answer'], 'explanation': q.get('explanation', ''),
                       'is_correct': answer == q['answer'].strip().upper()})
    # Atomically consume this quiz; concurrent submissions cannot create duplicate scores.
    consumed = await db.execute(delete(QuizSession).where(QuizSession.id == quiz.id))
    if consumed.rowcount != 1:
        raise HTTPException(status_code=409, detail='This quiz has already been submitted.')
    correct = sum(q['is_correct'] for q in graded)
    score = round(correct / len(graded) * 100, 1)
    db.add(QuizAttempt(session_id=quiz.session_id, topic=quiz.topic, difficulty=quiz.difficulty,
                       score=score, total_questions=len(graded), answers=graded))
    return {'score': score, 'correct': correct, 'total': len(graded),
            'grade': 'A' if score >= 90 else 'B' if score >= 75 else 'C' if score >= 60 else 'D',
            'graded_questions': graded}
