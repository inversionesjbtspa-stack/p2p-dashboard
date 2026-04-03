from __future__ import annotations

import re
from typing import Any

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:(?:\+?56)?\s?)?(?:9\s?\d{4}\s?\d{4}|\d{2}\s?\d{4}\s?\d{4}|\d{8,11})")
RUT_RE = re.compile(r"\b\d{1,2}\.?(?:\d{3})\.?(?:\d{3})[-‐‑‒–—―]?([0-9Kk])\b")
NAME_HINT_RE = re.compile(
    r"(?:nombre(?:\s+completo)?|cliente|facturar a|raz[oó]n social|autorizad[oa])\s*[:\-]\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ' ]{4,80})",
    re.IGNORECASE,
)
STOP_WORDS = re.compile(r"\b(correo|email|mail|tel[eé]fono|fono|rut|direcci[oó]n|giro)\b.*$", re.IGNORECASE)


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D+", "", value)
    if not digits:
        return None
    if digits.startswith("56") and len(digits) >= 11:
        return f"+{digits}"
    if len(digits) == 9 and digits.startswith("9"):
        return f"+56{digits}"
    return digits


def normalize_rut(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"[^0-9Kk]", "", value)
    if len(cleaned) < 2:
        return None
    body, dv = cleaned[:-1], cleaned[-1].upper()
    return f"{int(body)}-{dv}"


def guess_name(text: str | None) -> str | None:
    if not text:
        return None
    match = NAME_HINT_RE.search(text)
    if not match:
        return None
    name = " ".join(match.group(1).split())
    name = STOP_WORDS.sub("", name).strip(' :-,;')
    return name.title() if name else None


def extract_contact_data(text: str | None) -> dict[str, str | None]:
    if not text:
        return {"email": None, "phone": None, "rut": None, "full_name": None}

    email_match = EMAIL_RE.search(text)
    phone_match = PHONE_RE.search(text)
    rut_match = RUT_RE.search(text)

    email = email_match.group(0).strip() if email_match else None
    phone = normalize_phone(phone_match.group(0)) if phone_match else None
    rut = normalize_rut(rut_match.group(0)) if rut_match else None
    full_name = guess_name(text)
    return {"email": email, "phone": phone, "rut": rut, "full_name": full_name}


def safe_decimal(value: Any):
    if value in (None, ""):
        return None
    from decimal import Decimal, InvalidOperation

    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None
