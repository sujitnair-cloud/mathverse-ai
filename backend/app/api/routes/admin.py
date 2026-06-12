from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.models import SolveHistory, QuizAttempt, UserProfile, Formula, MathTopic

router = APIRouter()


@router.get("/admin/dashboard")
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    total_solves = (await db.execute(select(func.count()).select_from(SolveHistory))).scalar()
    total_quizzes = (await db.execute(select(func.count()).select_from(QuizAttempt))).scalar()
    total_users = (await db.execute(select(func.count()).select_from(UserProfile))).scalar()
    total_formulas = (await db.execute(select(func.count()).select_from(Formula))).scalar()
    total_topics = (await db.execute(select(func.count()).select_from(MathTopic))).scalar()

    # Recent activity
    recent = await db.execute(
        select(SolveHistory)
        .order_by(SolveHistory.created_at.desc())
        .limit(10)
    )
    recent_items = [
        {"problem": h.problem, "topic": h.topic, "created_at": str(h.created_at)}
        for h in recent.scalars().all()
    ]

    # Top topics
    topic_counts = await db.execute(
        select(SolveHistory.topic, func.count().label("count"))
        .group_by(SolveHistory.topic)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_topics = [{"topic": r[0], "count": r[1]} for r in topic_counts.fetchall()]

    return {
        "stats": {
            "total_solves": total_solves,
            "total_quizzes": total_quizzes,
            "total_users": total_users,
            "total_formulas": total_formulas,
            "total_topics": total_topics,
        },
        "recent_activity": recent_items,
        "top_topics": top_topics,
    }
