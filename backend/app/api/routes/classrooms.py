"""Authenticated classroom, assignment, and teacher feedback workflows."""
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict, AwareDatetime
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core.auth import require_user
from app.core.database import get_db
from app.models.models import Classroom, ClassMember, Assignment, AssignmentSubmission, User

router = APIRouter(prefix='/classrooms')


class ClassInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)


class JoinInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    code: str = Field(min_length=1, max_length=32)


class AssignmentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(min_length=1, max_length=20000)
    due_at: AwareDatetime | None = None


class WorkInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    work: str = Field(min_length=1, max_length=30000)


class ReviewInput(BaseModel):
    score: float = Field(ge=0, le=100)
    feedback: str = Field(default='', max_length=10000)


async def accessible_class(class_id, user, db, teacher_only=False):
    classroom = await db.get(Classroom, class_id)
    if classroom is None:
        raise HTTPException(404, 'Classroom not found.')
    if classroom.teacher_id == user.id:
        return classroom
    member = await db.scalar(select(ClassMember.id).where(
        ClassMember.classroom_id == class_id, ClassMember.user_id == user.id))
    if teacher_only or member is None:
        raise HTTPException(403, 'You do not have access to this classroom action.')
    return classroom


def class_view(c, user):
    return {'id': c.id, 'name': c.name, 'role': 'teacher' if c.teacher_id == user.id else 'student',
            'join_code': c.join_code if c.teacher_id == user.id else None}


@router.get('')
async def list_classes(user=Depends(require_user), db: AsyncSession = Depends(get_db)):
    membership = select(ClassMember.classroom_id).where(ClassMember.user_id == user.id)
    items = await db.scalars(select(Classroom).where(or_(
        Classroom.teacher_id == user.id, Classroom.id.in_(membership))).order_by(Classroom.id.desc()))
    return [class_view(c, user) for c in items]


@router.post('', status_code=201)
async def create_class(req: ClassInput, user=Depends(require_user), db: AsyncSession = Depends(get_db)):
    classroom = Classroom(name=req.name, teacher_id=user.id, join_code=secrets.token_hex(6).upper())
    db.add(classroom)
    await db.flush()
    return class_view(classroom, user)


@router.post('/join')
async def join_class(req: JoinInput, user=Depends(require_user), db: AsyncSession = Depends(get_db)):
    classroom = await db.scalar(select(Classroom).where(Classroom.join_code == req.code.upper()))
    if classroom is None:
        raise HTTPException(404, 'No classroom matches that code.')
    if classroom.teacher_id != user.id:
        existing = await db.scalar(select(ClassMember.id).where(
            ClassMember.classroom_id == classroom.id, ClassMember.user_id == user.id))
        if existing is None:
            try:
                async with db.begin_nested():
                    db.add(ClassMember(classroom_id=classroom.id, user_id=user.id))
                    await db.flush()
            except IntegrityError:
                pass  # A simultaneous join already created this membership.
    return class_view(classroom, user)


@router.get('/{class_id}')
async def class_detail(class_id: int, user=Depends(require_user), db: AsyncSession = Depends(get_db)):
    classroom = await accessible_class(class_id, user, db)
    assignments = (await db.scalars(select(Assignment).where(
        Assignment.classroom_id == class_id).order_by(Assignment.id.desc()))).all()
    stmt = select(AssignmentSubmission).join(Assignment).where(Assignment.classroom_id == class_id)
    if classroom.teacher_id != user.id:
        stmt = stmt.where(AssignmentSubmission.student_id == user.id)
    submissions = (await db.scalars(stmt)).all()
    members = (await db.execute(select(User.id, User.name).join(
        ClassMember, ClassMember.user_id == User.id).where(ClassMember.classroom_id == class_id))).all()
    names = {m.id: m.name for m in members}
    def stamp(value):
        return value.replace(tzinfo=timezone.utc).isoformat() if value and value.tzinfo is None else value.isoformat() if value else None
    return {**class_view(classroom, user), 'member_count': len(members),
            'assignments': [{'id': a.id, 'title': a.title, 'instructions': a.instructions,
                             'due_at': stamp(a.due_at)} for a in assignments],
            'submissions': [{'id': s.id, 'assignment_id': s.assignment_id, 'student_name': names.get(s.student_id, 'Student'),
                             'work': s.work, 'score': s.score, 'feedback': s.feedback,
                             'submitted_at': stamp(s.submitted_at)} for s in submissions]}


@router.post('/{class_id}/assignments', status_code=201)
async def create_assignment(class_id: int, req: AssignmentInput, user=Depends(require_user), db: AsyncSession = Depends(get_db)):
    await accessible_class(class_id, user, db, teacher_only=True)
    assignment = Assignment(classroom_id=class_id, **req.model_dump())
    db.add(assignment)
    await db.flush()
    return {'id': assignment.id}


@router.post('/{class_id}/assignments/{assignment_id}/submit', status_code=201)
async def submit_assignment(class_id: int, assignment_id: int, req: WorkInput,
                            user=Depends(require_user), db: AsyncSession = Depends(get_db)):
    classroom = await accessible_class(class_id, user, db)
    if classroom.teacher_id == user.id:
        raise HTTPException(403, 'Teachers review work; students submit it.')
    assignment = await db.get(Assignment, assignment_id)
    if assignment is None or assignment.classroom_id != class_id:
        raise HTTPException(404, 'Assignment not found.')
    # Late work is accepted; teachers can compare the timestamp with the due date.
    submission = AssignmentSubmission(assignment_id=assignment_id, student_id=user.id, work=req.work)
    try:
        async with db.begin_nested():
            db.add(submission)
            await db.flush()
    except IntegrityError:
        raise HTTPException(409, 'You have already submitted this assignment.')
    return {'id': submission.id}


@router.patch('/{class_id}/submissions/{submission_id}')
async def review_submission(class_id: int, submission_id: int, req: ReviewInput,
                            user=Depends(require_user), db: AsyncSession = Depends(get_db)):
    await accessible_class(class_id, user, db, teacher_only=True)
    submission = await db.scalar(select(AssignmentSubmission).join(Assignment).where(
        AssignmentSubmission.id == submission_id, Assignment.classroom_id == class_id))
    if submission is None:
        raise HTTPException(404, 'Submission not found.')
    submission.score = req.score
    submission.feedback = req.feedback
    return {'reviewed': True}
