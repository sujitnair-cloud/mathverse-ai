import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.auth import get_current_user
from app.api.routes.history import history_owner
from app.core.limiter import limiter
from app.models.models import SolveHistory, User
from app.services.math_engine import (
    solve_expression, is_llm_first_problem, detect_difficulty as auto_detect_difficulty,
    looks_like_prose, preprocess_problem,
)
from app.services.llm_service import get_explanation, llm_full_solve, solve_with_gemini_tools

router = APIRouter()

# Product decision: a daily-refreshing quota (resets on a rolling 24h
# window, not at a fixed clock time), lower for anonymous visitors than for
# signed-in free accounts -- signing in is itself the upsell step before
# the payment recommendation, so it gets a real allowance bump. Once the
# day's allowance is used, the paywall prompt shows.
ANON_DAILY_LIMIT = 15
FREE_DAILY_LIMIT = 20

PLAN_LIMITS = {
    "free":    FREE_DAILY_LIMIT,
    "student": 9999,
    "pro":     9999,
    "school":  9999,
}


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
@limiter.limit("30/minute")
async def solve_problem(
    request: Request,
    req: SolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    if not req.problem.strip():
        raise HTTPException(status_code=400, detail="Problem cannot be empty.")
    owner = history_owner(req.session_id, current_user)

    # ── Usage limit check ─────────────────────────────────────────────────────
    if current_user:
        # Authenticated user — daily quota via daily_solves, rolling 24h
        # window (reset whenever at least a full day has elapsed since the
        # last reset, not at a fixed clock time).
        plan = current_user.subscription_plan or "free"
        limit = PLAN_LIMITS.get(plan, FREE_DAILY_LIMIT)

        now = datetime.now(timezone.utc)
        reset_at = current_user.daily_solves_reset_at
        if reset_at is not None and reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)
        if reset_at is None or (now - reset_at).days >= 1:
            current_user.daily_solves = 0
            current_user.daily_solves_reset_at = now

        used_today = current_user.daily_solves or 0
        if plan == "free" and used_today >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"You've used all {limit} free solves for today. Upgrade to Pro for unlimited access.",
            )

        current_user.daily_solves = used_today + 1
        current_user.total_solves = (current_user.total_solves or 0) + 1  # lifetime stat only, not a gate
        db.add(current_user)
        solves_used = current_user.daily_solves
        solves_limit = limit

    else:
        # Anonymous user — limit by session_id, same rolling 24h window,
        # counted from actual solve history rather than a stored counter
        # (there's no account to store one on).
        session_id = req.session_id or "anonymous"
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        count_result = await db.execute(
            select(func.count()).select_from(SolveHistory).where(
                SolveHistory.session_id == session_id,
                SolveHistory.created_at >= cutoff,
            )
        )
        anon_count = count_result.scalar() or 0

        if anon_count >= ANON_DAILY_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"You've used all {ANON_DAILY_LIMIT} free solves for today. "
                    f"Sign in with Google for {FREE_DAILY_LIMIT} free solves a day, "
                    "or upgrade to Pro for unlimited access."
                ),
            )

        solves_used = anon_count + 1
        solves_limit = ANON_DAILY_LIMIT

    # ── Solve ─────────────────────────────────────────────────────────────────
    detected_difficulty = auto_detect_difficulty(req.problem)
    explanation_level = req.difficulty or detected_difficulty

    user_plan = (current_user.subscription_plan if current_user else None) or "free"

    explanation = None
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

    # Primary path: Gemini reads the problem directly -- any phrasing or
    # notation, no regex-based topic routing to go stale or miss a case --
    # and calls the structured solver as a verified-computation tool
    # whenever it needs one, so the final answer is exact rather than
    # hallucinated. This replaces needing a new hand-written pattern for
    # every new phrasing someone happens to type. Falls back to the older
    # SymPy-first / word-problem flow below when this path is unavailable
    # (no LLM configured) or the whole round trip fails outright (network
    # error, response never resolved to valid JSON) -- "never leave the
    # user with nothing" applies here same as everywhere else.
    #
    # Fast-path exception: an "obviously simple" input -- short, and with
    # no natural-language ambiguity at all (looks_like_prose() is the same
    # signal this app already relies on elsewhere to catch exactly that
    # ambiguity) -- skips the multi-second LLM round trip entirely and goes
    # straight to the free, instant structured solver below instead, which
    # still gets a real LLM fallback if it turns out to fail. This can't
    # reintroduce the misrouting bugs fixed earlier this session: it only
    # ever fires for input that was already unambiguous before any topic
    # detection ran, never for a word problem or unusual phrasing.
    is_simple_and_unambiguous = (
        len(req.problem) < 80 and not looks_like_prose(preprocess_problem(req.problem))
    )
    tool_result = None
    if not is_simple_and_unambiguous:
        tool_result = await solve_with_gemini_tools(req.problem, explanation_level)

    if tool_result and tool_result.get("_quota_exceeded"):
        loop = asyncio.get_running_loop()
        result.update(await loop.run_in_executor(None, solve_expression, req.problem))
        result["error"] = (
            "Daily AI quota reached — answered via the structured solver instead. "
            "Quota resets at midnight UTC."
        )
    elif tool_result:
        explanation = tool_result.pop("explanation", None)
        result.update(tool_result)

    elif is_llm_first_problem(req.problem):
        # Word problem / proof / advanced request -- for everyone now, not
        # just paid plans. Previously free/anonymous users only ever got the
        # structured (SymPy) solver here, which has no real handling for this
        # category (word problems, proofs) by design, then bolted on a
        # "requires Student or Pro" error whenever that predictably failed --
        # confusingly, this could still show a real, correct answer alongside
        # that same paywall error, because get_explanation() (unrestricted by
        # plan since an earlier fix) sometimes yielded an answer via the
        # separate "extract Final Answer from the explanation" fallback below
        # even while this block was independently reporting failure. The
        # monetization lever is the solve-count limit above, not gating
        # which categories of problem get a real attempt.
        llm_result = await llm_full_solve(req.problem, explanation_level)
        if llm_result and llm_result.get("_quota_exceeded"):
            loop = asyncio.get_running_loop()
            result.update(await loop.run_in_executor(None, solve_expression, req.problem))
            result["error"] = (
                "Daily AI quota reached — answered via the structured solver instead. "
                "Quota resets at midnight UTC."
            )
        elif llm_result:
            explanation = llm_result.pop("explanation", None)
            result.update(llm_result)
        else:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, solve_expression, req.problem)
    else:
        # Standard path: SymPy first, LLM fallback for everyone when it fails.
        # A structured-solver gap (misrouted topic, unhandled notation, etc.)
        # previously meant a dead-end error with no answer for free/anon
        # users, even for problems well within SymPy's real capability that
        # just hit a pipeline bug -- paywalling that fallback made every such
        # bug user-facing for the majority of users instead of invisible.
        # Existing per-request/per-day solve-count limits above still cap
        # usage; this only changes which backend answers an already-allowed
        # request.
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
                result["error"] = "Daily AI quota reached. Quota resets at midnight UTC."
            elif llm_result:
                explanation = llm_result.pop("explanation", None)
                result.update(llm_result)
                result["error"] = None

    if not result.get("difficulty"):
        result["difficulty"] = detected_difficulty

    if explanation is None and req.include_explanation:
        explanation = await get_explanation(req.problem, result, explanation_level, plan=user_plan)

    # For word problems: if SymPy returned "See steps" but the LLM explanation
    # starts with "**Final Answer:** ...", extract that as the concise answer.
    if explanation and result.get("answer") in (None, "See steps", ""):
        import re as _re
        m = _re.search(r'\*{0,2}Final Answer:?\*{0,2}\s*([^\n]+)', explanation, _re.IGNORECASE)
        if m:
            result["answer"] = m.group(1).strip().strip("*").strip()

    # Persist to history
    history = SolveHistory(
        session_id=owner,
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
