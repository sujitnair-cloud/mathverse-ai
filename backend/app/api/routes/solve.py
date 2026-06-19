import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import SolveHistory, User
from app.services.math_engine import solve_expression, is_llm_first_problem, detect_difficulty as auto_detect_difficulty
from app.services.llm_service import get_explanation, llm_full_solve

router = APIRouter()

PLAN_LIMITS = {
    "free":    10,
    "student": 9999,
    "pro":     9999,
    "school":  9999,
}

ANON_LIMIT = 3  # anonymous users get 3 solves ever, then must sign in


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
        # Authenticated user — check daily plan limit
        plan = current_user.subscription_plan or "free"
        limit = PLAN_LIMITS.get(plan, 10)

        now = datetime.now(timezone.utc)
        reset_at = current_user.daily_solves_reset_at
        if reset_at is None or (now - reset_at).days >= 1:
            current_user.daily_solves = 0
            current_user.daily_solves_reset_at = now

        used = current_user.daily_solves or 0
        if used >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"You have used all {limit} free solves for today. Upgrade to Pro for unlimited access.",
            )

        current_user.daily_solves = used + 1
        current_user.total_solves = (current_user.total_solves or 0) + 1
        db.add(current_user)
        solves_used = used + 1
        solves_limit = limit

    else:
        # Anonymous user — limit by session_id
        session_id = req.session_id or "anonymous"
        count_result = await db.execute(
            select(func.count()).select_from(SolveHistory).where(
                SolveHistory.session_id == session_id
            )
        )
        anon_count = count_result.scalar() or 0

        if anon_count >= ANON_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=f"You have used {ANON_LIMIT} free solves. Sign in with Google for 10 free solves per day — it's free!",
            )

        solves_used = anon_count + 1
        solves_limit = ANON_LIMIT

    # ── Solve ─────────────────────────────────────────────────────────────────
    # Auto-detect difficulty from the problem text; use it when user hasn't overridden
    detected_difficulty = auto_detect_difficulty(req.problem)
    explanation_level = req.difficulty or detected_difficulty

    explanation = None
    # Default skeleton — always defined so the return block is safe
    result: dict = {
        "problem": req.problem,
        "topic": "algebra_general",
        "difficulty": detected_difficulty,
        "steps": [],
        "answer": None,
        "latex_answer": None,
        "alternate_method": None,
        "formulas_used": [],
        "common_mistakes": [],
        "similar_problems": [],
        "error": None,
    }

    if is_llm_first_problem(req.problem):
        # Word problem / proof / aptitude → skip SymPy, go straight to LLM
        llm_result = await llm_full_solve(req.problem, explanation_level)
        if llm_result and llm_result.get("_quota_exceeded"):
            result["error"] = (
                "Daily AI quota reached. Your question will be answered via the structured solver. "
                "Quota resets at midnight UTC."
            )
        elif llm_result:
            explanation = llm_result.pop("explanation", None)
            result.update(llm_result)
        else:
            # No LLM configured — try SymPy anyway
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, solve_expression, req.problem)
    else:
        # Standard path: SymPy first (non-blocking thread), LLM fallback if it fails
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, solve_expression, req.problem)

        answer_str = str(result.get("answer") or "")
        sympy_failed = (
            bool(result.get("error")) or
            not result.get("answer") or
            answer_str.startswith("Please ") or
            answer_str.startswith("See steps")
        )
        if sympy_failed:
            llm_result = await llm_full_solve(req.problem, explanation_level)
            if llm_result and llm_result.get("_quota_exceeded"):
                result["error"] = (
                    "Daily AI quota reached. Quota resets at midnight UTC."
                )
            elif llm_result:
                explanation = llm_result.pop("explanation", None)
                result.update(llm_result)
                result["error"] = None

    # Propagate auto-detected difficulty onto result so frontend can highlight it
    if not result.get("difficulty"):
        result["difficulty"] = detected_difficulty

    if explanation is None and req.include_explanation:
        explanation = await get_explanation(req.problem, result, explanation_level)

    # For word problems: if SymPy returned "See steps" but the LLM explanation
    # starts with "**Final Answer:** ...", extract that as the concise answer.
    if explanation and result.get("answer") in (None, "See steps", ""):
        import re as _re
        m = _re.search(r'\*{0,2}Final Answer:?\*{0,2}\s*([^\n]+)', explanation, _re.IGNORECASE)
        if m:
            result["answer"] = m.group(1).strip().strip("*").strip()

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
