from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.models import MathTopic

router = APIRouter()


class TopicOut(BaseModel):
    id: int
    slug: str
    name: str
    category: str
    definition: Optional[str]
    explanation: Optional[str]
    key_formulas: Optional[list]
    examples: Optional[list]
    use_cases: Optional[str]
    difficulty: Optional[str]
    related_topics: Optional[list]
    prerequisites: Optional[list]

    class Config:
        from_attributes = True


@router.get("/topics", response_model=List[TopicOut])
async def list_topics(
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MathTopic)
    if category:
        stmt = stmt.where(MathTopic.category.ilike(f"%{category}%"))
    if difficulty:
        stmt = stmt.where(MathTopic.difficulty == difficulty)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/topics/search")
async def search_topics(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MathTopic).where(
        or_(
            MathTopic.name.ilike(f"%{q}%"),
            MathTopic.definition.ilike(f"%{q}%"),
            MathTopic.category.ilike(f"%{q}%"),
        )
    ).limit(20)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/topics/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MathTopic.category).distinct())
    cats = [row[0] for row in result.fetchall() if row[0]]
    return {"categories": sorted(cats)}


@router.get("/topics/{slug}", response_model=TopicOut)
async def get_topic(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MathTopic).where(MathTopic.slug == slug))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found.")
    return topic
