"""SQLAlchemy models: runs + the 3-layer agent memory."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


class Run(Base):
    """One protocol review run (the persisted Blackboard)."""
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default="webhook")
    submitter: Mapped[str] = mapped_column(String(200), default="")
    pdf_path: Mapped[str] = mapped_column(Text, default="")
    nct_id: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(20), default="queued")   # queued|running|done|failed
    decision: Mapped[str] = mapped_column(String(30), default="")
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RunMessage(Base):
    """Short-term memory: agent-to-agent conversation on the blackboard, per run."""
    __tablename__ = "run_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    agent: Mapped[str] = mapped_column(String(40))
    role: Mapped[str] = mapped_column(String(20), default="agent")   # agent|system|human
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentMemory(Base):
    """Long-term memory: learned facts/rules. HITL: proposed -> approved by a human."""
    __tablename__ = "agent_memories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent: Mapped[str] = mapped_column(String(40), index=True)
    scope: Mapped[str] = mapped_column(String(20), default="global")   # global|sponsor|submitter
    scope_ref: Mapped[str] = mapped_column(String(200), default="")
    fact: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="proposed")  # proposed|approved|rejected|inactive
    proposed_by: Mapped[str] = mapped_column(String(60), default="")
    run_id: Mapped[str] = mapped_column(String(36), default="")
    decided_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Interaction(Base):
    """Historical memory: every LLM exchange (audit, evals, cost)."""
    __tablename__ = "agent_interactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True, default="")
    agent: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(60), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_s: Mapped[float] = mapped_column(Float, default=0.0)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    prompt_excerpt: Mapped[str] = mapped_column(Text, default="")
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


_engine = None
_SessionLocal: sessionmaker | None = None


def get_engine(url: str | None = None):
    global _engine, _SessionLocal
    if _engine is None or url:
        _engine = create_engine(url or settings.resolved_database_url, future=True)
        Base.metadata.create_all(_engine)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def get_session() -> Session:
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


def reset_engine_for_tests(url: str):
    """Point the module at a fresh database (tests)."""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
    return get_engine(url)
