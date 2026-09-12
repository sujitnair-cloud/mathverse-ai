"""
Phase 5: the connected learning journey.
Short diagnostic -> targeted lesson -> guided practice -> independent
practice -> review, backed by a skill map with prerequisites and a
recommendation engine that explains itself from real evidence.
"""
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.data.lesson_content import LESSONS
from app.models.models import MathTopic, SkillAttempt, SkillQuestion
from app.services.quiz_generator import generate_verified_questions
from app.services.skill_map import (
    PRACTICE_ENABLED_TOPICS,
    compute_mastery,
    recommend_next,
    remediate_wrong_answer,
    skill_map_with_progress,
)

router = APIRouter(prefix="/learning")

Stage = Literal["diagnostic", "guided", "independent", "review"]
_STAGE_DEMAND = {"diagnostic": "routine", "guided": "routine", "independent": "multi_step", "review": "unfamiliar"}


@router.get("/skill-map")
async def get_skill_map(session_id: str, db: AsyncSession = Depends(get_db)):
    return {"topics": await skill_map_with_progress(db, session_id)}


@router.get("/recommendation")
async def get_recommendation(session_id: str, db: AsyncSession = Depends(get_db)):
    return await recommend_next(db, session_id)


@router.get("/lesson/{slug}")
async def get_lesson(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MathTopic).where(MathTopic.slug == slug))
    topic = result.scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found.")
    lesson = LESSONS.get(slug)
    return {
        "slug": slug, "name": topic.name, "prerequisites": topic.prerequisites or [],
        "has_practice": slug in PRACTICE_ENABLED_TOPICS,
        "lesson": lesson,  # None for topics without a written lesson yet — frontend shows the topic wiki entry instead
    }


class NextQuestionRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    topic: str = Field(min_length=1, max_length=100)
    stage: Stage = "guided"


@router.post("/practice/next")
async def next_question(req: NextQuestionRequest, db: AsyncSession = Depends(get_db)):
    if req.topic not in PRACTICE_ENABLED_TOPICS:
        raise HTTPException(status_code=400, detail=f"Practice isn't available yet for '{req.topic}'.")
    result = await db.execute(select(MathTopic).where(MathTopic.slug == req.topic))
    topic = result.scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found.")

    demand = _STAGE_DEMAND[req.stage]
    level = topic.difficulty or "intermediate"
    question = generate_verified_questions(req.topic, level, demand, 1)[0]

    record = SkillQuestion(id=secrets.token_urlsafe(24), session_id=req.session_id,
                            topic=req.topic, stage=req.stage, question=question)
    db.add(record)
    await db.flush()
    return {
        "question_id": record.id,
        "question": question["question"],
        "options": question["options"],
        "hint": (LESSONS.get(req.topic) or {}).get("construction"),
    }


class AnswerRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    question_id: str = Field(min_length=1, max_length=64)
    selected: str = Field(min_length=1, max_length=1)
    hints_used: int = Field(default=0, ge=0, le=10)


@router.post("/practice/answer")
async def answer_question(req: AnswerRequest, db: AsyncSession = Depends(get_db)):
    record = await db.get(SkillQuestion, req.question_id)
    if record is None or record.session_id != req.session_id:
        raise HTTPException(status_code=404, detail="Question not found or already answered.")
    q = record.question
    selected = req.selected.strip().upper()
    valid_letters = {o[0].upper() for o in q["options"]}
    if selected not in valid_letters:
        raise HTTPException(status_code=400, detail="Select one of the given options.")

    # Atomically consume this question; a concurrent duplicate answer cannot
    # both succeed and record two attempts (same pattern as quiz.py).
    consumed = await db.execute(delete(SkillQuestion).where(SkillQuestion.id == record.id))
    if consumed.rowcount != 1:
        raise HTTPException(status_code=409, detail="This question has already been answered.")

    correct_letter = q["answer"].strip().upper()
    is_correct = selected == correct_letter
    misconception = None if is_correct else (q.get("option_tags") or {}).get(selected)

    db.add(SkillAttempt(session_id=req.session_id, topic=record.topic, stage=record.stage,
                         correct=is_correct, hints_used=req.hints_used, misconception=misconception))
    await db.flush()

    response = {
        "correct": is_correct, "correct_answer": correct_letter,
        "explanation": q.get("explanation", ""), "misconception": misconception,
    }
    if not is_correct:
        response["remediation"] = await remediate_wrong_answer(db, req.session_id, record.topic, misconception)
    return response


@router.get("/progress")
async def get_progress(session_id: str, db: AsyncSession = Depends(get_db)):
    """Evidence summary across every attempted topic — 'performance across
    time, not just one quiz.'"""
    return {"mastery": await compute_mastery(db, session_id)}
