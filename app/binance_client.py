from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings


class BinanceClient:
    def __init__(self) -> None:
        self.base_url = settings.binance_base_url.rstrip("/")
        self.api_key = settings.binance_api_key
        self.secret_key = settings.binance_secret_key

    def is_configured(self) -> bool:
        return bool(self.api_key and self.secret_key)

    def _sign(self, params: dict[str, Any]) -> str:
        query_string = urlencode(params)
        signature = hmac.new(
            self.secret_key.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def get_c2c_history(
        self,
        *,
        trade_type: str,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
        page: int = 1,
        rows: int = 100,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("Binance API keys are not configured.")

        params: dict[str, Any] = {
            "tradeType": trade_type,
            "page": page,
            "rows": rows,
            "timestamp": int(time.time() * 1000),
        }

        if start_timestamp is not None:
            params["startTimestamp"] = start_timestamp

        if end_timestamp is not None:
            params["endTimestamp"] = end_timestamp

        params["signature"] = self._sign(params)
        headers = {"X-MBX-APIKEY": self.api_key}

        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{self.base_url}/sapi/v1/c2c/orderMatch/listUserOrderHistory",
                params=params,
                headers=headers,
            )

            try:
                response.raise_for_status()
            except Exception as e:
                print("Binance error:", e)
                return {"data": []}

            return response.json()
