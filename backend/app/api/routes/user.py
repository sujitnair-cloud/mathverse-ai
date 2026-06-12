from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import UserProfile

router = APIRouter()


class ProfileUpsert(BaseModel):
    session_id: str
    username: Optional[str] = None
    user_type: Optional[str] = "student"
    level: Optional[str] = "intermediate"
    preferred_language: Optional[str] = "en"
    dark_mode: Optional[bool] = False


@router.get("/user/profile")
async def get_profile(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserProfile).where(UserProfile.session_id == session_id))
    profile = result.scalar_one_or_none()
    if not profile:
        return {"exists": False}
    return {
        "exists": True,
        "session_id": profile.session_id,
        "username": profile.username,
        "user_type": profile.user_type,
        "level": profile.level,
        "preferred_language": profile.preferred_language,
        "dark_mode": profile.dark_mode,
        "topics_explored": profile.topics_explored or [],
        "total_problems_solved": profile.total_problems_solved,
        "streak_days": profile.streak_days,
        "created_at": str(profile.created_at),
    }


@router.post("/user/profile")
async def upsert_profile(data: ProfileUpsert, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserProfile).where(UserProfile.session_id == data.session_id))
    profile = result.scalar_one_or_none()
    if profile:
        profile.username = data.username or profile.username
        profile.user_type = data.user_type
        profile.level = data.level
        profile.preferred_language = data.preferred_language
        profile.dark_mode = data.dark_mode
    else:
        profile = UserProfile(
            session_id=data.session_id,
            username=data.username,
            user_type=data.user_type,
            level=data.level,
            preferred_language=data.preferred_language,
            dark_mode=data.dark_mode,
            topics_explored=[],
            total_problems_solved=0,
        )
        db.add(profile)
    return {"saved": True, "session_id": data.session_id}
