# app/bot/routers/public/audio_format.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError

from app.bot.i18n import t
from app.bot.keyboards.audio_format import audio_format_kb
from app.domain.services.user_repo import UserRepo
from app.infra.db.session import get_sessionmaker

router = Router()
repo = UserRepo()


async def _get_lang(uid: int) -> str:
    sm = get_sessionmaker()
    async with sm() as session:
        user = await repo.get_or_create(session, uid)
        return user.language_code or "ru"


@router.callback_query(F.data.startswith("audiofmt:"))
async def cb_audio_format(cb: CallbackQuery):
    uid = cb.from_user.id
    fmt = cb.data.split(":", 1)[1].strip().lower()
    lang = await _get_lang(uid)
    s = t(lang)

    if fmt not in {"mp3", "m4a", "wav", "opus"}:
        await cb.answer(s.audiofmt_unknown, show_alert=False)
        return

    sm = get_sessionmaker()
    async with sm() as session:
        cur = await repo.get_audio_format(session, uid)
        await repo.set_audio_format(session, uid, fmt)

    await cb.answer("OK" if lang == "en" else "Ок")

    try:
        if (cur or "").lower() != fmt:
            await cb.message.edit_text(s.audiofmt_text(fmt), reply_markup=audio_format_kb(lang))
        else:
            await cb.message.edit_reply_markup(reply_markup=audio_format_kb(lang))
    except TelegramBadRequest:
        pass
    except TelegramAPIError:
        pass