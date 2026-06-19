from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import SolveHistory, User
from app.services.math_engine import solve_expression
from app.services.llm_service import get_explanation

router = APIRouter()

PLAN_LIMITS = {
    "free":    10,
    "student": 9999,
    "pro":     9999,
    "school":  9999,
}

ANON_DAILY_LIMIT = 5  # anonymous users (no login) get 5/day per session


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
    solves_used: Optional[int] = None
    solves_limit: Optional[int] = None


@router.post("/solve", response_model=SolveResponse)
async def solve_problem(
    req: SolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    if not req.problem.strip():
        raise HTTPException(status_code=400, detail="Problem cannot be empty.")

    # ── Usage limit check ─────────────────────────────────────────────────────
    if current_user:
        plan = current_user.subscription_plan or "free"
        limit = PLAN_LIMITS.get(plan, 10)

        # Reset daily count if it's a new day
        now = datetime.now(timezone.utc)
        reset_at = current_user.daily_solves_reset_at
        if reset_at is None or (now - reset_at).days >= 1:
            current_user.daily_solves = 0
            current_user.daily_solves_reset_at = now

        used = current_user.daily_solves or 0
        if used >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Daily limit of {limit} solves reached. Upgrade your plan for unlimited access."
            )

        current_user.daily_solves = used + 1
        current_user.total_solves = (current_user.total_solves or 0) + 1
        db.add(current_user)
        solves_used = used + 1
        solves_limit = limit
    else:
        # Anonymous — no enforcement for now, just track session
        solves_used = None
        solves_limit = None

    # ── Solve ─────────────────────────────────────────────────────────────────
    result = solve_expression(req.problem)

    explanation = None
    if req.include_explanation:
        explanation = await get_explanation(req.problem, result, req.difficulty)

    # Persist to history
    history = SolveHistory(
        session_id=req.session_id if not current_user else str(current_user.id),
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
        solves_used=solves_used,
        solves_limit=solves_limit,
    )
