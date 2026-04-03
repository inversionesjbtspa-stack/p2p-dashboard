from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.config import settings
from app.parser import extract_contact_data, normalize_phone, normalize_rut

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


@dataclass(slots=True)
class ExtractionResult:
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    rut: str | None = None
    address: str | None = None
    business_line: str | None = None
    second_alias: str | None = None
    summary: str | None = None
    confidence: Decimal = Decimal("0.30")
    source: str = "regex"

    def as_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "rut": self.rut,
            "address": self.address,
            "business_line": self.business_line,
            "second_alias": self.second_alias,
            "summary": self.summary,
            "confidence": str(self.confidence),
            "source": self.source,
        }


class ContactExtractionService:
    def __init__(self) -> None:
        self.enabled = bool(settings.openai_enabled and settings.openai_api_key and OpenAI is not None)
        self.client = OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds) if self.enabled else None

    def extract(self, text: str | None) -> ExtractionResult:
        base = self._fallback(text)
        if not text or not self.enabled or self.client is None:
            return base
        try:
            response = self.client.responses.create(
                model=settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "Extrae datos de contacto y facturación desde texto de órdenes P2P. "
                                    "Devuelve JSON válido con llaves: full_name, email, phone, rut, address, business_line, second_alias, summary, confidence. "
                                    "No inventes datos. confidence debe ir entre 0 y 1."
                                ),
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": text}],
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "contact_extraction",
                        "schema": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "full_name": {"type": ["string", "null"]},
                                "email": {"type": ["string", "null"]},
                                "phone": {"type": ["string", "null"]},
                                "rut": {"type": ["string", "null"]},
                                "address": {"type": ["string", "null"]},
                                "business_line": {"type": ["string", "null"]},
                                "second_alias": {"type": ["string", "null"]},
                                "summary": {"type": ["string", "null"]},
                                "confidence": {"type": ["number", "null"]},
                            },
                            "required": [
                                "full_name",
                                "email",
                                "phone",
                                "rut",
                                "address",
                                "business_line",
                                "second_alias",
                                "summary",
                                "confidence",
                            ],
                        },
                    }
                },
            )
            payload = json.loads(response.output_text)
            return ExtractionResult(
                full_name=(payload.get("full_name") or base.full_name or None),
                email=(payload.get("email") or base.email or None),
                phone=normalize_phone(payload.get("phone") or base.phone),
                rut=normalize_rut(payload.get("rut") or base.rut),
                address=payload.get("address") or None,
                business_line=payload.get("business_line") or None,
                second_alias=payload.get("second_alias") or None,
                summary=payload.get("summary") or None,
                confidence=Decimal(str(payload.get("confidence") or "0.80")),
                source="openai",
            )
        except Exception:
            return base

    def _fallback(self, text: str | None) -> ExtractionResult:
        parsed = extract_contact_data(text)
        return ExtractionResult(
            full_name=parsed.get("full_name"),
            email=parsed.get("email"),
            phone=parsed.get("phone"),
            rut=parsed.get("rut"),
            summary="Extracción por reglas locales." if text else None,
            confidence=Decimal("0.30"),
            source="regex",
        )
