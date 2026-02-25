from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main import main_menu_kb
from app.bot.keyboards.tools import tools_kb
from app.domain.services.panel import safe_edit_or_send
from app.domain.services.user_repo import UserRepo
from app.infra.db.session import get_sessionmaker

router = Router()
repo = UserRepo()


def text_tools(lang: str) -> str:
    if lang == "en":
        return "🧰 Tools:\n\n• 🎧 Convert to audio\n• 📝 Speech to text\n\n🌐 Links open in Mini App."
    return "🧰 Инструменты:\n\n• 🎧 Конвертировать в аудио\n• 📝 Распознать речь в текст\n\n🌐 Ссылки открывай в Mini App."


def text_settings(lang: str) -> str:
    if lang == "en":
        return "⚙️ Settings:\n\n• Language"
    return "⚙️ Настройки:\n\n• Язык"


def text_profile(lang: str) -> str:
    if lang == "en":
        return "👤 Profile (soon)"
    return "👤 Профиль (скоро)"


def welcome_text(lang: str) -> str:
    if lang == "en":
        return (
            "EagleTools is a helper bot.\n\n"
            "🧰 Tools:\n"
            "• 🎧 Convert to audio\n"
            "• 📝 Speech to text\n\n"
            "🌐 Links open in Mini App.\n\n"
            "Use the buttons below."
        )
    return (
        "EagleTools — бот-инструментарий.\n\n"
        "🧰 Инструменты:\n"
        "• 🎧 Конвертировать в аудио\n"
        "• 📝 Распознать речь в текст\n\n"
        "🌐 Ссылки открывай в Mini App.\n\n"
        "Пользуйся кнопками ниже."
    )


async def get_user(uid: int):
    sm = get_sessionmaker()
    async with sm() as session:
        return await repo.get_or_create(session, uid)


async def get_panel(uid: int):
    user = await get_user(uid)
    if user.panel_chat_id and user.panel_message_id:
        return int(user.panel_chat_id), int(user.panel_message_id)
    return None


async def save_panel(uid: int, chat_id: int, message_id: int):
    sm = get_sessionmaker()
    async with sm() as session:
        await repo.set_panel(session, uid, chat_id=chat_id, message_id=message_id)


async def edit_panel(cb: CallbackQuery, text: str, markup):
    uid = cb.from_user.id
    user = await get_user(uid)
    panel = await get_panel(uid)

    current = None
    if panel:
        from app.domain.services.panel import PanelRef
        current = PanelRef(chat_id=panel[0], message_id=panel[1])

    panel_ref = await safe_edit_or_send(
        bot=cb.bot,
        chat_id=cb.message.chat.id,
        text=text,
        reply_markup=markup,
        current=current,
    )
    await save_panel(uid, panel_ref.chat_id, panel_ref.message_id)


@router.callback_query(F.data == "main:tools")
async def go_tools(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    await edit_panel(cb, text_tools(user.language or "ru"), tools_kb())
    await cb.answer()


@router.callback_query(F.data == "main:settings")
async def go_settings(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    await edit_panel(cb, text_settings(user.language or "ru"), main_menu_kb())
    await cb.answer()


@router.callback_query(F.data == "main:profile")
async def go_profile(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    await edit_panel(cb, text_profile(user.language or "ru"), main_menu_kb())
    await cb.answer()


@router.callback_query(F.data == "nav:home")
async def go_home(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    await edit_panel(cb, welcome_text(user.language or "ru"), main_menu_kb())
    await cb.answer()


# Заглушки инструментов (пока)
@router.callback_query(F.data.startswith("tool:"))
async def tool_stub(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    lang = user.language or "ru"
    which = cb.data.split(":", 1)[1]

    if lang == "en":
        msg = "Selected tool: "
        names = {"audio": "Convert to audio", "stt": "Speech to text"}
    else:
        msg = "Выбран инструмент: "
        names = {"audio": "Конвертировать в аудио", "stt": "Распознать речь в текст"}

    await edit_panel(cb, f"{msg}{names.get(which, which)}\n\nОтправь ссылку или файл.", tools_kb())
    await cb.answer()