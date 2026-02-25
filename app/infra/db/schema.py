# app/infra/db/schema.py
from __future__ import annotations

"""
DB facade.

Правила:
- Модели (User/Job/UsageDaily/Referral/SubscriptionEvent и Base) объявляются ТОЛЬКО в app.infra.db.models.
- Этот файл НЕ создает declarative_base() и НЕ объявляет ORM классы.
- Этот файл экспортит:
  1) Enum'ы/типы (PlanEnum/JobKind/JobStatus)
  2) ORM модели (ре-экспортом из models.py)
  3) Алиасы для legacy-имен моделей (DailyUsage -> UsageDaily, etc.)
"""

from enum import StrEnum


# -------------------------
# Enum'ы домена / БД контракта
# -------------------------

class PlanEnum(StrEnum):
    free = "free"
    premium = "premium"


class JobKind(StrEnum):
    save = "save"
    stt = "stt"


class JobStatus(StrEnum):
    queued = "queued"
    running = "running"
    done = "done"
    error = "error"


# -------------------------
# Ре-экспорт ORM моделей (единый registry)
# -------------------------
from app.infra.db.models import *  # noqa: F401,F403


# -------------------------
# Legacy aliases (совместимость со старым кодом)
# -------------------------

# в проекте актуальное имя: UsageDaily
# но некоторые сервисы могут импортировать DailyUsage
try:
    DailyUsage = UsageDaily  # type: ignore[name-defined]
except Exception:
    pass

# иногда встречается SubscriptionEvent(s) в разных вариантах
try:
    SubscriptionEvents = SubscriptionEvent  # type: ignore[name-defined]
except Exception:
    pass