from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError

from app.bot.keyboards.audio_format import audio_format_kb
from app.domain.services.user_repo import UserRepo
from app.infra.db.session import get_sessionmaker

router = Router()
repo = UserRepo()


def _fmt_name(fmt: str) -> str:
    return {
        "mp3": "MP3",
        "m4a": "M4A",
        "wav": "WAV",
        "opus": "OPUS",
    }.get(fmt, fmt.upper())


def _text(fmt: str) -> str:
    return (
        "✅ Режим выбран: 🎧 Конвертировать в аудио\n"
        f"Формат: {_fmt_name(fmt)}\n\n"
        "Отправь файл."
    )


@router.callback_query(F.data.startswith("audiofmt:"))
async def cb_audio_format(cb: CallbackQuery):
    uid = cb.from_user.id
    fmt = cb.data.split(":", 1)[1].strip().lower()

    if fmt not in {"mp3", "m4a", "wav", "opus"}:
        await cb.answer("Неизвестный формат", show_alert=False)
        return

    sm = get_sessionmaker()
    async with sm() as session:
        # если хочешь, можно прочитать текущий и не делать лишний edit
        cur = await repo.get_audio_format(session, uid)
        await repo.set_audio_format(session, uid, fmt)

    await cb.answer("Ок")

    # Главный фикс: редактируем ТО ЖЕ сообщение с меню форматов,
    # сохраняем клавиатуру и не создаём новых сообщений.
    try:
        # если формат не изменился — не дергаем edit (иначе "message is not modified")
        if (cur or "").lower() != fmt:
            await cb.message.edit_text(_text(fmt), reply_markup=audio_format_kb())
        else:
            # но на всякий случай удержим markup (если его кто-то снял)
            await cb.message.edit_reply_markup(reply_markup=audio_format_kb())
    except TelegramBadRequest:
        # например: message is not modified / message to edit not found
        pass
    except TelegramAPIError:
        pass