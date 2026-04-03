from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    binance_counterparty_key: Mapped[str | None] = mapped_column(String(255), index=True)
    rut: Mapped[str | None] = mapped_column(String(32), index=True)
    first_name: Mapped[str | None] = mapped_column(String(120))
    last_name: Mapped[str | None] = mapped_column(String(120))
    full_name: Mapped[str | None] = mapped_column(String(255), index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(64), index=True)
    address: Mapped[str | None] = mapped_column(String(255))
    business_line: Mapped[str | None] = mapped_column(String(255))
    second_alias: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    data_quality_status: Mapped[str | None] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    orders: Mapped[list[Order]] = relationship(back_populates="client")
    metrics: Mapped[ClientMetric6M | None] = relationship(back_populates="client", uselist=False)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("order_number", name="uq_order_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    adv_no: Mapped[str | None] = mapped_column(String(64))
    trade_type: Mapped[str | None] = mapped_column(String(16), index=True)
    asset: Mapped[str | None] = mapped_column(String(32))
    fiat: Mapped[str | None] = mapped_column(String(16), index=True)
    fiat_symbol: Mapped[str | None] = mapped_column(String(16))
    amount_crypto: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    order_status: Mapped[str | None] = mapped_column(String(32), index=True)
    order_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    commission: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    counterparty_nickname: Mapped[str | None] = mapped_column(String(255), index=True)
    advertisement_role: Mapped[str | None] = mapped_column(String(32))
    raw_message: Mapped[str | None] = mapped_column(Text)
    extracted_email: Mapped[str | None] = mapped_column(String(255))
    extracted_phone: Mapped[str | None] = mapped_column(String(64))
    extracted_rut: Mapped[str | None] = mapped_column(String(32))
    extracted_full_name: Mapped[str | None] = mapped_column(String(255))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    extraction_source: Mapped[str | None] = mapped_column(String(32), default="regex")
    source: Mapped[str | None] = mapped_column(String(32), default="binance_api")
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    client: Mapped[Client | None] = relationship(back_populates="orders")


class ClientMetric6M(Base):
    __tablename__ = "client_metrics_6m"
    __table_args__ = (UniqueConstraint("client_id", name="uq_client_metrics_client"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    tx_count_6m: Mapped[int] = mapped_column(Integer, default=0)
    total_amount_6m: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=0)
    first_tx_6m: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_tx_6m: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    client: Mapped[Client] = relationship(back_populates="metrics")


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    pulled_orders: Mapped[int] = mapped_column(Integer, default=0)
