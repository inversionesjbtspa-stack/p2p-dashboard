from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook


def export_workbook(orders, clients) -> bytes:
    wb = Workbook()
    ws_orders = wb.active
    ws_orders.title = "Ordenes"
    ws_orders.append([
        "Número de orden",
        "Fecha",
        "Nombre del comprador",
        "Par",
        "Mensaje",
        "Monto",
        "Correo detectado",
        "Teléfono detectado",
        "RUT detectado",
        "Fuente extracción",
    ])
    for order in orders:
        ws_orders.append([
            order.order_number,
            str(order.order_created_at or ""),
            (order.client.full_name if order.client and order.client.full_name else order.counterparty_nickname),
            order.fiat,
            order.raw_message,
            float(order.total_price) if order.total_price is not None else None,
            order.extracted_email,
            order.extracted_phone,
            order.extracted_rut,
            order.extraction_source,
        ])

    ws_clients = wb.create_sheet("Clientes")
    ws_clients.append([
        "RUT",
        "Nombres apellidos",
        "Correo",
        "Teléfono",
        "Dirección",
        "Giro",
        "Segundo alias",
        "Estado ficha",
        "Tx 6M",
        "Monto 6M",
    ])
    for client in clients:
        ws_clients.append([
            client.rut,
            client.full_name,
            client.email,
            client.phone,
            client.address,
            client.business_line,
            client.second_alias,
            client.data_quality_status,
            client.metrics.tx_count_6m if client.metrics else 0,
            float(client.metrics.total_amount_6m) if client.metrics and client.metrics.total_amount_6m is not None else 0,
        ])

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
