from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.models import Formula

router = APIRouter()


class FormulaOut(BaseModel):
    id: int
    name: str
    topic: str
    subtopic: Optional[str]
    formula: str
    description: Optional[str]
    variables: Optional[dict]
    example: Optional[str]
    difficulty: str
    tags: Optional[list]

    class Config:
        from_attributes = True


@router.get("/formula/search", response_model=List[FormulaOut])
async def search_formulas(
    q: Optional[str] = Query(None, description="Search query"),
    topic: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Formula)
    conditions = []
    if q:
        conditions.append(or_(
            Formula.name.ilike(f"%{q}%"),
            Formula.description.ilike(f"%{q}%"),
            Formula.topic.ilike(f"%{q}%"),
        ))
    if topic:
        conditions.append(Formula.topic.ilike(f"%{topic}%"))
    if difficulty:
        conditions.append(Formula.difficulty == difficulty)
    if conditions:
        from sqlalchemy import and_
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/formula/{formula_id}", response_model=FormulaOut)
async def get_formula(formula_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.get(Formula, formula_id)
    if not result:
        raise HTTPException(status_code=404, detail="Formula not found.")
    return result


@router.get("/formula/topics/list")
async def list_formula_topics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Formula.topic).distinct())
    topics = [row[0] for row in result.fetchall() if row[0]]
    return {"topics": sorted(topics)}
