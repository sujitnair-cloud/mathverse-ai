from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.database import get_db
from app.models.models import SolveHistory
from app.services.math_engine import solve_expression
from app.services.llm_service import get_explanation

router = APIRouter()


class SolveRequest(BaseModel):
    problem: str
    difficulty: Optional[str] = "intermediate"
    session_id: Optional[str] = "anonymous"
    include_explanation: Optional[bool] = True


class SolveResponse(BaseModel):
    problem: str
    topic: str
    difficulty: str
    steps: list
    answer: str
    latex_answer: Optional[str] = None
    explanation: Optional[str] = None
    alternate_method: Optional[str] = None
    formulas_used: list
    common_mistakes: list
    similar_problems: list
    error: Optional[str] = None


@router.post("/solve", response_model=SolveResponse)
async def solve_problem(req: SolveRequest, db: AsyncSession = Depends(get_db)):
    if not req.problem.strip():
        raise HTTPException(status_code=400, detail="Problem cannot be empty.")

    # Symbolic solving
    result = solve_expression(req.problem)

    # LLM explanation
    explanation = None
    if req.include_explanation:
        explanation = await get_explanation(req.problem, result, req.difficulty)

    # Persist to history
    history = SolveHistory(
        session_id=req.session_id,
        problem=req.problem,
        topic=result.get("topic"),
        difficulty=result.get("difficulty"),
        result=result,
    )
    db.add(history)

    return SolveResponse(
        problem=result["problem"],
        topic=result.get("topic", "general"),
        difficulty=result.get("difficulty", req.difficulty),
        steps=result.get("steps", []),
        answer=result.get("answer") or "See steps",
        latex_answer=result.get("latex_answer"),
        explanation=explanation,
        alternate_method=result.get("alternate_method"),
        formulas_used=result.get("formulas_used", []),
        common_mistakes=result.get("common_mistakes", []),
        similar_problems=result.get("similar_problems", []),
        error=result.get("error"),
    )
