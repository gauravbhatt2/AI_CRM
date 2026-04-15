"""
SQLAlchemy ORM models for CRM persistence.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    pass


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Account(Base):
    """CRM account (company)."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)

    contacts: Mapped[list["Contact"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    deals: Mapped[list["Deal"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    crm_records: Mapped[list["CrmRecord"]] = relationship(back_populates="account")


class Contact(Base):
    """Person linked to an account."""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    email: Mapped[str] = mapped_column(String(512), default="", server_default="")
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    account: Mapped["Account"] = relationship(back_populates="contacts")
    crm_records: Mapped[list["CrmRecord"]] = relationship(back_populates="contact")


class Deal(Base):
    """Opportunity linked to an account (FRD: stage, value, intent signal)."""

    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    value: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    stage: Mapped[str] = mapped_column(String(128), default="Open", server_default="Open")
    intent_snapshot: Mapped[str] = mapped_column(String(512), default="", server_default="")

    account: Mapped["Account"] = relationship(back_populates="deals")
    crm_records: Mapped[list["CrmRecord"]] = relationship(back_populates="deal")


class CrmRecord(Base):
    """
    Persisted transcript + extracted CRM fields from the ingestion pipeline.
    """

    __tablename__ = "crm_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    budget: Mapped[str] = mapped_column(String(1024), default="", server_default="")
    intent: Mapped[str] = mapped_column(String(1024), default="", server_default="")
    competitors: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    product: Mapped[str] = mapped_column(String(1024), default="", server_default="")
    timeline: Mapped[str] = mapped_column(String(1024), default="", server_default="")
    industry: Mapped[str] = mapped_column(String(1024), default="", server_default="")
    custom_fields: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    source_type: Mapped[str] = mapped_column(String(64), default="call", server_default="call")
    external_interaction_id: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    participants: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    source_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    structured_transcript: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mapping_method: Mapped[str] = mapped_column(String(32), default="rules", server_default="rules")

    # AI Intelligence Layer fields
    interaction_type: Mapped[str] = mapped_column(String(64), default="", server_default="")
    deal_score: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    risk_level: Mapped[str] = mapped_column(String(32), default="", server_default="")
    risk_reason: Mapped[str] = mapped_column(Text, default="", server_default="")
    summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    tags: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    next_action: Mapped[str] = mapped_column(Text, default="", server_default="")
    product_version: Mapped[str] = mapped_column(String(256), default="", server_default="")
    pain_points: Mapped[str] = mapped_column(Text, default="", server_default="")
    next_step: Mapped[str] = mapped_column(Text, default="", server_default="")
    urgency_reason: Mapped[str] = mapped_column(Text, default="", server_default="")
    stakeholders: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    mentioned_company: Mapped[str] = mapped_column(String(512), default="", server_default="")
    procurement_stage: Mapped[str] = mapped_column(String(128), default="", server_default="")
    use_case: Mapped[str] = mapped_column(Text, default="", server_default="")
    decision_criteria: Mapped[str] = mapped_column(Text, default="", server_default="")
    budget_owner: Mapped[str] = mapped_column(String(256), default="", server_default="")
    implementation_scope: Mapped[str] = mapped_column(String(256), default="", server_default="")

    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    account: Mapped["Account | None"] = relationship(back_populates="crm_records")
    contact: Mapped["Contact | None"] = relationship(back_populates="crm_records")
    deal: Mapped["Deal | None"] = relationship(back_populates="crm_records")


class AuditLog(Base):
    """DRD §3.5 — audit trail for ingestion and key CRM events (append-only)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_table: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
