from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional

from app.core.database import get_db
from app.models.models import SolveHistory

router = APIRouter()


@router.get("/history")
async def get_history(
    session_id: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(SolveHistory)
        .where(SolveHistory.session_id == session_id)
        .order_by(SolveHistory.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return {
        "session_id": session_id,
        "count": len(items),
        "history": [
            {
                "id": h.id,
                "problem": h.problem,
                "topic": h.topic,
                "difficulty": h.difficulty,
                "answer": h.result.get("answer") if h.result else None,
                "created_at": str(h.created_at),
            }
            for h in items
        ],
    }


@router.delete("/history/{history_id}")
async def delete_history_item(history_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(SolveHistory, history_id)
    if item:
        await db.delete(item)
    return {"deleted": True}


@router.delete("/history")
async def clear_history(session_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    await db.execute(delete(SolveHistory).where(SolveHistory.session_id == session_id))
    return {"cleared": True, "session_id": session_id}
