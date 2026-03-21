# app/domain/services/cryptobot.py
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

log = logging.getLogger(__name__)

CRYPTOBOT_API = "https://pay.crypt.bot/api"


@dataclass
class CryptoBotInvoice:
    invoice_id: int
    pay_url: str
    status: str
    amount: str
    asset: str
    payload: str


class CryptoBotClient:
    def __init__(self, token: str) -> None:
        self.token = token
        self._headers = {"Crypto-Pay-API-Token": token}

    async def create_invoice(
        self,
        amount: float,
        asset: str = "TON",
        payload: str = "",
        description: str = "",
        expires_in: int = 3600,
    ) -> CryptoBotInvoice:
        async with aiohttp.ClientSession() as session:
            resp = await session.post(
                f"{CRYPTOBOT_API}/createInvoice",
                headers=self._headers,
                json={
                    "asset": asset,
                    "amount": str(amount),
                    "payload": payload,
                    "description": description,
                    "expires_in": expires_in,
                },
            )
            data = await resp.json()

        if not data.get("ok"):
            raise RuntimeError(f"CryptoBot error: {data}")

        inv = data["result"]
        return CryptoBotInvoice(
            invoice_id=inv["invoice_id"],
            pay_url=inv["pay_url"],
            status=inv["status"],
            amount=inv["amount"],
            asset=inv["asset"],
            payload=inv.get("payload", ""),
        )

    async def get_invoice(self, invoice_id: int) -> CryptoBotInvoice | None:
        async with aiohttp.ClientSession() as session:
            resp = await session.get(
                f"{CRYPTOBOT_API}/getInvoices",
                headers=self._headers,
                params={"invoice_ids": str(invoice_id)},
            )
            data = await resp.json()

        if not data.get("ok"):
            return None

        items = data["result"].get("items", [])
        if not items:
            return None

        inv = items[0]
        return CryptoBotInvoice(
            invoice_id=inv["invoice_id"],
            pay_url=inv["pay_url"],
            status=inv["status"],
            amount=inv["amount"],
            asset=inv["asset"],
            payload=inv.get("payload", ""),
        )

    def verify_webhook(self, token: str, body: bytes, signature: str) -> bool:
        """Проверяем подпись вебхука от CryptoBot."""
        secret = hashlib.sha256(token.encode()).digest()
        expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)