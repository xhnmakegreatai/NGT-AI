"""
数据库会话管理
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import settings


connect_args = {}
if settings.database_url.startswith("sqlite"):
    # SQLite 在多线程访问下需要关闭同线程检查
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    future=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    future=True,
)


def get_db() -> Session:
    """FastAPI 依赖：提供数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
