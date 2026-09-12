from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import SolveHistory

router = APIRouter()


def history_owner(session_id, current_user):
    if current_user is not None:
        return str(current_user.id)
    # Account IDs must never be accepted as anonymous session credentials.
    if not session_id or not session_id.startswith('sess_') or len(session_id) > 64:
        raise HTTPException(status_code=400, detail='A valid guest session is required.')
    return session_id


@router.get("/history")
async def get_history(
    session_id: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    session_id = history_owner(session_id, current_user)
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
async def delete_history_item(history_id: int, session_id: str = Query(...), db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    owner = history_owner(session_id, current_user)
    item = await db.get(SolveHistory, history_id)
    if item is None or item.session_id != owner:
        raise HTTPException(status_code=404, detail='History item not found.')
    await db.delete(item)
    return {"deleted": True}


@router.delete("/history")
async def clear_history(session_id: str = Query(...), db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    session_id = history_owner(session_id, current_user)
    await db.execute(delete(SolveHistory).where(SolveHistory.session_id == session_id))
    return {"cleared": True, "session_id": session_id}
