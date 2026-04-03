from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Iterable

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.ai_extractor import ContactExtractionService
from app.binance_client import BinanceClient
from app.config import settings
from app.models import Client, ClientMetric6M, Order, SyncRun
from app.parser import safe_decimal


class SyncService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.client = BinanceClient()
        self.extractor = ContactExtractionService()

    def sync_orders(self) -> SyncRun:
        sync_run = SyncRun(status="running")
        self.db.add(sync_run)
        self.db.flush()

        if not self.client.is_configured():
            sync_run.status = "error"
            sync_run.detail = "BINANCE_API_KEY/BINANCE_SECRET_KEY no configuradas."
            sync_run.finished_at = datetime.now(UTC)
            self.db.flush()
            return sync_run

        end_dt = datetime.now(UTC)
        start_dt = end_dt - timedelta(days=settings.sync_lookback_days)
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)

        pulled = 0
        for trade_type in ("BUY", "SELL"):
            page = 1
            while True:
                payload = self.client.get_c2c_history(
                    trade_type=trade_type,
                    start_timestamp=start_ms,
                    end_timestamp=end_ms,
                    page=page,
                    rows=settings.sync_rows,
                )
                data = payload.get("data", [])
                if not data:
                    break
                pulled += len(data)
                for row in data:
                    self._upsert_order(row)
                total = int(payload.get("total", 0) or 0)
                if page * settings.sync_rows >= total:
                    break
                page += 1

        self.recalculate_all_metrics()
        sync_run.status = "success"
        sync_run.pulled_orders = pulled
        sync_run.finished_at = datetime.now(UTC)
        sync_run.detail = f"Sincronización completada. Órdenes procesadas: {pulled}."
        self.db.flush()
        return sync_run

    def analyze_order_message(self, order: Order) -> Order:
        result = self.extractor.extract(order.raw_message)
        order.extracted_email = result.email
        order.extracted_phone = result.phone
        order.extracted_rut = result.rut
        order.extracted_full_name = result.full_name
        order.ai_summary = result.summary
        order.ai_confidence = result.confidence
        order.extraction_source = result.source
        if order.client:
            self.apply_result_to_client(order.client, result)
            self.recalculate_client_metrics(order.client.id)
        self.db.flush()
        return order

    def apply_result_to_client(self, client: Client, result) -> Client:
        if result.full_name and not client.full_name:
            client.full_name = result.full_name
        if result.email and not client.email:
            client.email = result.email
        if result.phone and not client.phone:
            client.phone = result.phone
        if result.rut and not client.rut:
            client.rut = result.rut
        if result.address and not client.address:
            client.address = result.address
        if result.business_line and not client.business_line:
            client.business_line = result.business_line
        if result.second_alias and not client.second_alias:
            client.second_alias = result.second_alias
        required = [client.full_name, client.rut, client.email, client.phone]
        client.data_quality_status = "ready" if all(required) else "pending"
        self.db.flush()
        return client

    def _upsert_order(self, row: dict) -> Order:
        order = self.db.scalar(select(Order).where(Order.order_number == str(row.get("orderNumber"))))
        if order is None:
            order = Order(order_number=str(row.get("orderNumber")))
            self.db.add(order)
            self.db.flush()

        order.adv_no = row.get("advNo")
        order.trade_type = row.get("tradeType")
        order.asset = row.get("asset")
        order.fiat = row.get("fiat")
        order.fiat_symbol = row.get("fiatSymbol")
        order.amount_crypto = safe_decimal(row.get("amount"))
        order.total_price = safe_decimal(row.get("totalPrice"))
        order.unit_price = safe_decimal(row.get("unitPrice"))
        order.order_status = row.get("orderStatus")
        create_ms = row.get("createTime")
        order.order_created_at = datetime.fromtimestamp(create_ms / 1000, tz=UTC) if create_ms else None
        order.commission = safe_decimal(row.get("commission"))
        order.counterparty_nickname = row.get("counterPartNickName")
        order.advertisement_role = row.get("advertisementRole")

        if order.raw_message:
            self.analyze_order_message(order)

        order.client = self._resolve_client(order)
        self.db.flush()
        return order

    def _resolve_client(self, order: Order) -> Client:
        key = order.counterparty_nickname or order.order_number
        client = self.db.scalar(select(Client).where(Client.binance_counterparty_key == key))
        if client is None:
            client = Client(
                binance_counterparty_key=key,
                full_name=order.extracted_full_name or order.counterparty_nickname,
                email=order.extracted_email,
                phone=order.extracted_phone,
                rut=order.extracted_rut,
            )
            self.db.add(client)
            self.db.flush()
        else:
            if not client.email and order.extracted_email:
                client.email = order.extracted_email
            if not client.phone and order.extracted_phone:
                client.phone = order.extracted_phone
            if not client.rut and order.extracted_rut:
                client.rut = order.extracted_rut
            if not client.full_name and (order.extracted_full_name or order.counterparty_nickname):
                client.full_name = order.extracted_full_name or order.counterparty_nickname
        required = [client.full_name, client.rut, client.email, client.phone]
        client.data_quality_status = "ready" if all(required) else "pending"
        return client

    def recalculate_all_metrics(self) -> None:
        client_ids = [client_id for (client_id,) in self.db.execute(select(Client.id)).all()]
        for client_id in client_ids:
            self.recalculate_client_metrics(client_id)

    def recalculate_client_metrics(self, client_id: int) -> ClientMetric6M:
        cutoff = datetime.now(UTC) - timedelta(days=183)
        orders = list(
            self.db.scalars(
                select(Order)
                .where(Order.client_id == client_id, Order.order_created_at >= cutoff)
                .order_by(Order.order_created_at.asc())
            )
        )

        total_amount = sum((order.total_price or 0) for order in orders)
        first_tx = orders[0].order_created_at if orders else None
        last_tx = orders[-1].order_created_at if orders else None

        metrics = self.db.scalar(select(ClientMetric6M).where(ClientMetric6M.client_id == client_id))
        if metrics is None:
            metrics = ClientMetric6M(client_id=client_id)
            self.db.add(metrics)
        metrics.tx_count_6m = len(orders)
        metrics.total_amount_6m = total_amount
        metrics.first_tx_6m = first_tx
        metrics.last_tx_6m = last_tx
        metrics.refreshed_at = datetime.now(UTC)
        self.db.flush()
        return metrics


def latest_sync(db: Session) -> SyncRun | None:
    return db.scalar(select(SyncRun).order_by(desc(SyncRun.started_at)).limit(1))


def dashboard_counts(db: Session) -> dict[str, int]:
    return {
        "orders": db.scalar(select(func.count()).select_from(Order)) or 0,
        "clients": db.scalar(select(func.count()).select_from(Client)) or 0,
        "clients_missing_tax": db.scalar(
            select(func.count()).select_from(Client).where((Client.rut.is_(None)) | (Client.business_line.is_(None)))
        ) or 0,
        "clients_ready": db.scalar(select(func.count()).select_from(Client).where(Client.data_quality_status == "ready")) or 0,
    }


def recent_orders(db: Session, limit: int = 20) -> list[Order]:
    return list(db.scalars(select(Order).order_by(desc(Order.order_created_at)).limit(limit)))


def list_orders(db: Session) -> list[Order]:
    return list(db.scalars(select(Order).order_by(desc(Order.order_created_at))))


def list_clients(db: Session) -> list[Client]:
    return list(db.scalars(select(Client).order_by(desc(Client.updated_at))))
