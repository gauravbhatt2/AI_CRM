"""
SQLAlchemy ORM models for CRM persistence.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func, text
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
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    account: Mapped["Account"] = relationship(back_populates="contacts")
    crm_records: Mapped[list["CrmRecord"]] = relationship(back_populates="contact")


class Deal(Base):
    """Opportunity linked to an account."""

    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    value: Mapped[str | None] = mapped_column(String(1024), nullable=True)

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
    source_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    structured_transcript: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mapping_method: Mapped[str] = mapped_column(String(32), default="rules", server_default="rules")

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
