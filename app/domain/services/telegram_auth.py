from __future__ import annotations

import hashlib
import hmac
import urllib.parse
from typing import Any

from app.common.config import settings


def verify_init_data(init_data: str) -> dict[str, Any]:
    """
    Telegram WebApp initData validation (HMAC-SHA256)
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    parsed = urllib.parse.parse_qsl(init_data, keep_blank_values=True)
    data = dict(parsed)

    if "hash" not in data:
        raise ValueError("missing_hash")

    received_hash = data.pop("hash")

    # data_check_string
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))

    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key,
        check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("invalid_signature")

    # user comes as JSON string
    if "user" in data:
        import json
        data["user"] = json.loads(data["user"])

    return data