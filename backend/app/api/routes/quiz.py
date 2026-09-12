from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Literal
from pydantic import Field
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import QuizAttempt, GeneratedQuiz
from app.services.llm_service import generate_quiz_questions
from app.services.quiz_policy import QuizUnavailableError, validate_request

router = APIRouter()


class QuizRequest(BaseModel):
    topic: str
    difficulty: Literal['basic', 'intermediate', 'advanced'] = "intermediate"
    count: int = Field(default=5, ge=1, le=20)
    session_id: str = Field(default="anonymous", max_length=64)


class QuizSubmission(BaseModel):
    session_id: str
    quiz_id: str
    user_answers: List[str]


@router.post("/quiz/generate")
async def generate_quiz(req: QuizRequest, db: AsyncSession = Depends(get_db)):
    try:
        validate_request(req.topic, req.difficulty, req.count)
        questions = await generate_quiz_questions(req.topic, req.difficulty, req.count)
    except QuizUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    quiz_id = str(uuid4())
    db.add(GeneratedQuiz(id=quiz_id, session_id=req.session_id, topic=req.topic,
                         difficulty=req.difficulty, questions=questions))
    await db.flush()
    public_questions = [{"question": q['question'], "options": q['options']} for q in questions]
    return {"quiz_id": quiz_id, "topic": req.topic, "difficulty": req.difficulty, "questions": public_questions}


@router.post("/quiz/submit")
async def submit_quiz(submission: QuizSubmission, db: AsyncSession = Depends(get_db)):
    quiz = await db.get(GeneratedQuiz, submission.quiz_id)
    if quiz is None or quiz.session_id != submission.session_id:
        raise HTTPException(status_code=404, detail="Quiz not found. Please start a new quiz.")
    questions_with_answers = quiz.questions
    if len(submission.user_answers) != len(questions_with_answers) or any(
        a.strip().upper() not in ('A', 'B', 'C', 'D') for a in submission.user_answers
    ):
        raise HTTPException(status_code=400, detail="Answer every question with A, B, C or D.")
    correct = 0
    graded = []
    for i, (q, user_ans) in enumerate(zip(questions_with_answers, submission.user_answers)):
        is_correct = user_ans.strip().upper() == q.get("answer", "").strip().upper()
        if is_correct:
            correct += 1
        graded.append({
            "question": q["question"],
            "user_answer": user_ans,
            "correct_answer": q.get("answer"),
            "explanation": q.get("explanation", ""),
            "is_correct": is_correct,
        })

    score = round(correct / len(graded) * 100, 1) if graded else 0

    attempt = QuizAttempt(
        session_id=submission.session_id,
        topic=quiz.topic,
        difficulty=quiz.difficulty,
        score=score,
        total_questions=len(graded),
        answers=graded,
    )
    db.add(attempt)

    return {
        "score": score,
        "correct": correct,
        "total": len(graded),
        "grade": "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D",
        "graded_questions": graded,
    }
