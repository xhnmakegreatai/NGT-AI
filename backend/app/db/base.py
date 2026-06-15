"""
SQLAlchemy Declarative Base 定义
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CHAR, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    """跨方言 UUID:PostgreSQL 用原生 UUID,其它(如 SQLite)用 CHAR(36)。"""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        return value if dialect.name == "postgresql" else str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class Base(DeclarativeBase):
    """全局 Declarative Base"""

    pass


class UUIDPrimaryKeyMixin:
    """为模型提供 UUID 主键"""

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )


class TimestampMixin:
    """通用创建/更新时间字段"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
