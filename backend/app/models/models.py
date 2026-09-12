from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String(128), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(200))
    avatar_url = Column(Text)
    is_active = Column(Boolean, default=True)

    # Stripe subscription
    stripe_customer_id = Column(String(128), unique=True, index=True)
    stripe_subscription_id = Column(String(128))
    subscription_plan = Column(String(20), default="free")   # free | student | pro | school
    subscription_status = Column(String(20), default="active")  # active | canceled | past_due
    subscription_expires_at = Column(DateTime(timezone=True))

    # Usage tracking
    daily_solves = Column(Integer, default=0)
    daily_solves_reset_at = Column(DateTime(timezone=True))
    total_solves = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), onupdate=func.now())


class SolveHistory(Base):
    __tablename__ = "solve_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), index=True)
    problem = Column(Text, nullable=False)
    topic = Column(String(100))
    difficulty = Column(String(20))
    result = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Formula(Base):
    __tablename__ = "formulas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    topic = Column(String(100), index=True)
    subtopic = Column(String(100))
    formula = Column(Text, nullable=False)
    description = Column(Text)
    variables = Column(JSON)
    example = Column(Text)
    difficulty = Column(String(20), default="intermediate")
    tags = Column(JSON)


class MathTopic(Base):
    __tablename__ = "math_topics"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), index=True)
    definition = Column(Text)
    explanation = Column(Text)
    key_formulas = Column(JSON)
    examples = Column(JSON)
    use_cases = Column(Text)
    difficulty = Column(String(20))
    related_topics = Column(JSON)
    prerequisites = Column(JSON)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), index=True)
    topic = Column(String(100))
    difficulty = Column(String(20))
    score = Column(Float)
    total_questions = Column(Integer)
    answers = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(String(64), primary_key=True)
    session_id = Column(String(64), index=True, nullable=False)
    topic = Column(String(100), nullable=False)
    difficulty = Column(String(20), nullable=False)
    questions = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SkillAttempt(Base):
    """
    Permanent evidence log for the learning journey (Phase 5): one row per
    answered practice/diagnostic/review question. This is what "track
    performance across time, not just one quiz" and "repeated
    misconceptions" are computed from — grouped by (session_id, topic) and
    ordered by created_at, not by any single attempt in isolation.
    """
    __tablename__ = "skill_attempts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), index=True, nullable=False)
    topic = Column(String(100), index=True, nullable=False)
    stage = Column(String(20), nullable=False)  # diagnostic | guided | independent | review
    correct = Column(Boolean, nullable=False)
    hints_used = Column(Integer, default=0)
    misconception = Column(String(100))  # tag identifying *which* likely mistake, not just "wrong"
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SkillQuestion(Base):
    """
    Ephemeral single-use holding pen for one served practice question —
    mirrors QuizSession's pattern (server holds the answer key; the client
    only ever sees the question) but scoped to one question at a time so
    the learning journey can give immediate per-question feedback and
    remediation instead of only a batch score at the end.
    """
    __tablename__ = "skill_questions"

    id = Column(String(64), primary_key=True)
    session_id = Column(String(64), index=True, nullable=False)
    topic = Column(String(100), nullable=False)
    stage = Column(String(20), nullable=False)
    question = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True)
    username = Column(String(100))
    user_type = Column(String(50), default="student")
    level = Column(String(20), default="intermediate")
    preferred_language = Column(String(10), default="en")
    dark_mode = Column(Boolean, default=False)
    topics_explored = Column(JSON, default=list)
    total_problems_solved = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
