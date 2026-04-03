from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import Base, engine, get_db
from app.excel_export import export_workbook
from app.models import Client, Order
from app.services import SyncService, dashboard_counts, latest_sync, recent_orders

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Binance P2P Dashboard")
security = HTTPBasic()
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def require_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    correct_username = secrets.compare_digest(credentials.username, settings.dashboard_username)
    correct_password = secrets.compare_digest(credentials.password, settings.dashboard_password)
    if not (correct_username and correct_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas", headers={"WWW-Authenticate": "Basic"})
    return credentials.username


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db), _: str = Depends(require_auth)):
    context = {
        "request": request,
        "counts": dashboard_counts(db),
        "sync": latest_sync(db),
        "orders": recent_orders(db),
        "openai_enabled": bool(settings.openai_enabled and settings.openai_api_key),
    }
    return templates.TemplateResponse("dashboard.html", context)


@app.get("/orders", response_class=HTMLResponse)
def orders_page(request: Request, db: Session = Depends(get_db), _: str = Depends(require_auth)):
    orders = list(
        db.scalars(select(Order).options(selectinload(Order.client)).order_by(Order.order_created_at.desc()))
    )
    return templates.TemplateResponse("orders.html", {"request": request, "orders": orders, "openai_enabled": bool(settings.openai_enabled and settings.openai_api_key)})


@app.post("/orders/{order_id}/message")
def update_order_message(
    order_id: int,
    message: str = Form(""),
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    order.raw_message = message.strip() or None
    SyncService(db).analyze_order_message(order)
    db.commit()
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/orders/{order_id}/analyze")
def analyze_order(order_id: int, db: Session = Depends(get_db), _: str = Depends(require_auth)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    SyncService(db).analyze_order_message(order)
    db.commit()
    return RedirectResponse(url="/orders", status_code=303)


@app.get("/clients", response_class=HTMLResponse)
def clients_page(request: Request, db: Session = Depends(get_db), _: str = Depends(require_auth)):
    clients = list(
        db.scalars(select(Client).options(selectinload(Client.metrics)).order_by(Client.updated_at.desc()))
    )
    return templates.TemplateResponse("clients.html", {"request": request, "clients": clients})


@app.get("/clients/{client_id}", response_class=HTMLResponse)
def client_edit_page(client_id: int, request: Request, db: Session = Depends(get_db), _: str = Depends(require_auth)):
    client = db.scalar(select(Client).options(selectinload(Client.metrics)).where(Client.id == client_id))
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return templates.TemplateResponse("client_edit.html", {"request": request, "client": client})


@app.post("/clients/{client_id}")
def update_client(
    client_id: int,
    full_name: str = Form(""),
    rut: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    business_line: str = Form(""),
    second_alias: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    client.full_name = full_name.strip() or None
    client.rut = rut.strip() or None
    client.email = email.strip() or None
    client.phone = phone.strip() or None
    client.address = address.strip() or None
    client.business_line = business_line.strip() or None
    client.second_alias = second_alias.strip() or None
    client.notes = notes.strip() or None
    required = [client.full_name, client.rut, client.email, client.phone]
    client.data_quality_status = "ready" if all(required) else "pending"
    db.commit()
    return RedirectResponse(url=f"/clients/{client_id}", status_code=303)


@app.post("/sync/run")
def run_sync(db: Session = Depends(get_db), _: str = Depends(require_auth)):
    SyncService(db).sync_orders()
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.get("/export.xlsx")
def export_xlsx(db: Session = Depends(get_db), _: str = Depends(require_auth)):
    orders = list(db.scalars(select(Order).options(selectinload(Order.client)).order_by(Order.order_created_at.desc())))
    clients = list(db.scalars(select(Client).options(selectinload(Client.metrics)).order_by(Client.updated_at.desc())))
    content = export_workbook(orders, clients)
    headers = {"Content-Disposition": 'attachment; filename="binance_p2p_dashboard.xlsx"'}
    return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
