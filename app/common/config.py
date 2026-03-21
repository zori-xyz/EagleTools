from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Single source of truth for:
      - Telegram bot (aiogram)
      - WebApp (FastAPI)
      - DB / Redis
      - Internal Bot → Backend API
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # =========================
    # CORE
    # =========================

    debug: bool = Field(default=False, validation_alias="DEBUG")
    data_dir: str = Field(default="data", validation_alias="DATA_DIR")

    # DEV (local only)
    dev_tg_user_id: Optional[int] = Field(
        default=None,
        validation_alias="DEV_TG_USER_ID",
    )

    # =========================
    # PAYMENTS
    # =========================

    ton_wallet: Optional[str] = Field(default=None, validation_alias="TON_WALLET")
    cryptobot_token: Optional[str] = Field(default=None, validation_alias="CRYPTOBOT_TOKEN")

    # =========================
    # ADMIN
    # =========================

    # Comma-separated Telegram IDs: ADMIN_IDS=123456789,987654321
    admin_ids: Optional[str] = Field(default=None, validation_alias="ADMIN_IDS")

    # Channel for TON payment notifications: ADMIN_CHANNEL_ID=-100xxxxxxxxx
    admin_channel_id: Optional[int] = Field(default=None, validation_alias="ADMIN_CHANNEL_ID")

    # =========================
    # BOT / REFERRALS
    # =========================

    # Used to build referral deep links:
    # https://t.me/<BOT_USERNAME>?start=ref_xxx
    bot_username: Optional[str] = Field(
        default=None,
        validation_alias="BOT_USERNAME",
    )

    # Internal Bot → Backend API
    bot_api_url: Optional[str] = Field(
        default=None,
        validation_alias="BOT_API_URL",
    )

    bot_api_key: Optional[str] = Field(
        default=None,
        validation_alias="BOT_API_KEY",
    )

    # =========================
    # TELEGRAM
    # =========================

    telegram_bot_token: Optional[str] = Field(
        default=None,
        validation_alias="TELEGRAM_BOT_TOKEN",
    )

    bot_token: Optional[str] = Field(
        default=None,
        validation_alias="BOT_TOKEN",
    )

    telegram_webapp_secret: Optional[str] = Field(
        default=None,
        validation_alias="TELEGRAM_WEBAPP_SECRET",
    )

    # =========================
    # DATABASE
    # =========================

    database_url: Optional[str] = Field(
        default=None,
        validation_alias="DATABASE_URL",
    )

    postgres_db: Optional[str] = Field(default=None, validation_alias="POSTGRES_DB")
    postgres_user: Optional[str] = Field(default=None, validation_alias="POSTGRES_USER")
    postgres_password: Optional[str] = Field(default=None, validation_alias="POSTGRES_PASSWORD")

    # =========================
    # WEB
    # =========================

    web_host: str = Field(default="127.0.0.1", validation_alias="WEB_HOST")
    web_port: int = Field(default=8000, validation_alias="WEB_PORT")
    webapp_url: Optional[str] = Field(default=None, validation_alias="WEBAPP_URL")

    # =========================
    # REDIS
    # =========================

    redis_url: Optional[str] = Field(default=None, validation_alias="REDIS_URL")
    redis_host: Optional[str] = Field(default=None, validation_alias="REDIS_HOST")
    redis_port: Optional[int] = Field(default=None, validation_alias="REDIS_PORT")
    redis_db: Optional[int] = Field(default=None, validation_alias="REDIS_DB")

    # ======================================================
    # HELPER PROPERTIES (safe accessors)
    # ======================================================

    @property
    def effective_bot_token(self) -> str:
        """
        Prefer TELEGRAM_BOT_TOKEN, fallback to BOT_TOKEN.
        """
        token = (self.telegram_bot_token or self.bot_token or "").strip()
        if not token:
            raise RuntimeError(
                "Missing Telegram bot token: set TELEGRAM_BOT_TOKEN (or BOT_TOKEN)."
            )
        return token

    @property
    def effective_webapp_secret(self) -> str:
        """
        Prefer TELEGRAM_WEBAPP_SECRET,
        fallback to bot token (safe for initData validation).
        """
        secret = (
            self.telegram_webapp_secret
            or self.telegram_bot_token
            or self.bot_token
            or ""
        ).strip()

        if not secret:
            raise RuntimeError(
                "Missing Telegram webapp secret: set TELEGRAM_WEBAPP_SECRET "
                "(or TELEGRAM_BOT_TOKEN/BOT_TOKEN)."
            )

        return secret

    @property
    def effective_database_url(self) -> str:
        if not (self.database_url or "").strip():
            raise RuntimeError("Missing DATABASE_URL.")
        return self.database_url.strip()

    @property
    def effective_redis_url(self) -> Optional[str]:
        """
        Prefer REDIS_URL.
        Otherwise build from host/port/db if present.
        Return None if redis isn't configured.
        """
        if self.redis_url and self.redis_url.strip():
            return self.redis_url.strip()

        if self.redis_host and self.redis_port is not None:
            db = int(self.redis_db or 0)
            return f"redis://{self.redis_host}:{int(self.redis_port)}/{db}"

        return None


# Singleton settings instance
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()