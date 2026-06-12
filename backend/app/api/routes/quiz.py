from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import QuizAttempt
from app.services.llm_service import generate_quiz_questions

router = APIRouter()


class QuizRequest(BaseModel):
    topic: str
    difficulty: Optional[str] = "intermediate"
    count: Optional[int] = 5
    session_id: Optional[str] = "anonymous"


class QuizSubmission(BaseModel):
    session_id: str
    topic: str
    difficulty: str
    questions: List[dict]
    user_answers: List[str]


@router.post("/quiz/generate")
async def generate_quiz(req: QuizRequest):
    if req.count < 1 or req.count > 20:
        raise HTTPException(status_code=400, detail="count must be between 1 and 20.")
    questions = await generate_quiz_questions(req.topic, req.difficulty, req.count)
    # Strip answers for client
    for q in questions:
        q.pop("answer", None)
        q.pop("explanation", None)
    return {"topic": req.topic, "difficulty": req.difficulty, "questions": questions}


@router.post("/quiz/submit")
async def submit_quiz(submission: QuizSubmission, db: AsyncSession = Depends(get_db)):
    # Regenerate with answers for grading
    questions_with_answers = await generate_quiz_questions(
        submission.topic, submission.difficulty, len(submission.questions)
    )
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
        topic=submission.topic,
        difficulty=submission.difficulty,
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
