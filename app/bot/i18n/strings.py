# app/bot/i18n/strings.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Strings:
    lang: str

    # ── Menu ──────────────────────────────────────────────────────────────────
    @property
    def menu_text(self) -> str:
        if self.lang == "en":
            return (
                "🦅 <b>EagleTools</b>\n\n"
                "• 🎧 Convert to audio\n"
                "• 📝 Speech to text\n"
                "• 🌐 More tools in our miniapp\n\n"
                "Choose a section:"
            )
        return (
            "🦅 <b>EagleTools</b>\n\n"
            "• 🎧 Конвертировать в аудио\n"
            "• 📝 Распознать речь в текст\n"
            "• 🌐 Полезные инструменты в нашем miniapp\n\n"
            "Выбери раздел:"
        )

    @property
    def tools_text(self) -> str:
        if self.lang == "en":
            return (
                "🧰 <b>Tools</b>\n\n"
                "Choose a mode and send a file.\n\n"
                "🌐 More tools in our miniapp."
            )
        return (
            "🧰 <b>Инструменты</b>\n\n"
            "Выбери режим и отправь файл.\n\n"
            "🌐 Полезные инструменты в нашем miniapp."
        )

    @property
    def settings_text(self) -> str:
        if self.lang == "en":
            return "⚙️ <b>Settings</b>\n\nChoose what to configure:"
        return "⚙️ <b>Настройки</b>\n\nВыбери что настроить:"

    def mode_audio_text(self, fmt: str) -> str:
        fmt_name = _fmt_name(fmt)
        if self.lang == "en":
            return (
                f"🎧 <b>Mode: Convert to audio</b>\n\n"
                f"Format: <b>{fmt_name}</b>\n\n"
                "Send a voice message, video or audio file."
            )
        return (
            f"🎧 <b>Режим: Конвертировать в аудио</b>\n\n"
            f"Формат: <b>{fmt_name}</b>\n\n"
            "Отправь голосовое, видео или аудио файл."
        )

    @property
    def mode_stt_text(self) -> str:
        if self.lang == "en":
            return (
                "📝 <b>Mode: Speech to text</b>\n\n"
                "Send a voice message or audio file."
            )
        return (
            "📝 <b>Режим: Распознать речь в текст</b>\n\n"
            "Отправь голосовое или аудио файл."
        )

    def mode_unknown_text(self, mode: str) -> str:
        if self.lang == "en":
            return f"✅ Mode: {mode}\n\nSend a file."
        return f"✅ Режим: {mode}\n\nОтправь файл."

    # ── Keyboards ─────────────────────────────────────────────────────────────
    @property
    def btn_tools(self) -> str:
        return "🧰 Tools" if self.lang == "en" else "🧰 Инструменты"

    @property
    def btn_settings(self) -> str:
        return "⚙️ Settings" if self.lang == "en" else "⚙️ Настройки"

    @property
    def btn_profile(self) -> str:
        return "👤 Profile" if self.lang == "en" else "👤 Профиль"

    @property
    def btn_back(self) -> str:
        return "⬅️ Back" if self.lang == "en" else "⬅️ Назад"

    @property
    def btn_lang_toggle(self) -> str:
        return "🇷🇺 Switch to Russian" if self.lang == "en" else "🇬🇧 Switch to English"

    @property
    def btn_privacy(self) -> str:
        return "📄 Privacy Policy" if self.lang == "en" else "📄 Политика конфиденциальности"

    @property
    def btn_audio_convert(self) -> str:
        return "🎧 Convert to audio" if self.lang == "en" else "🎧 Конвертировать в аудио"

    @property
    def btn_stt(self) -> str:
        return "📝 Speech to text" if self.lang == "en" else "📝 Распознать речь в текст"

    @property
    def btn_get_premium(self) -> str:
        return "⚡️ Get Premium" if self.lang == "en" else "⚡️ Получить Premium"

    @property
    def btn_invite_friend(self) -> str:
        return "🎁 Invite a friend (+5 downloads)" if self.lang == "en" else "🎁 Пригласить друга (+5 загрузок)"

    # ── Audio format keyboard ─────────────────────────────────────────────────
    @property
    def audiofmt_unknown(self) -> str:
        return "Unknown format" if self.lang == "en" else "Неизвестный формат"

    def audiofmt_text(self, fmt: str) -> str:
        fmt_name = _fmt_name(fmt)
        if self.lang == "en":
            return (
                f"✅ Mode selected: 🎧 Convert to audio\n"
                f"Format: {fmt_name}\n\n"
                "Send a file."
            )
        return (
            f"✅ Режим выбран: 🎧 Конвертировать в аудио\n"
            f"Формат: {fmt_name}\n\n"
            "Отправь файл."
        )

    # ── Smart router ──────────────────────────────────────────────────────────
    @property
    def url_in_miniapp(self) -> str:
        if self.lang == "en":
            return (
                "🌐 Links are processed in the Mini App.\n"
                "Open it via 🧰 Tools → 🌐 Mini App."
            )
        return (
            "🌐 Ссылки обрабатываются в Mini App.\n"
            "Открой её через 🧰 Инструменты → 🌐 Mini App (ссылки)."
        )

    @property
    def no_mode_selected(self) -> str:
        if self.lang == "en":
            return "Choose a mode in 🧰 Tools and send the file again."
        return "Выбери режим в 🧰 Инструментах и отправь файл ещё раз."

    @property
    def file_too_big(self) -> str:
        if self.lang == "en":
            return (
                "⚠️ File is too large to process via Telegram.\n\n"
                "Try sending a smaller file or compressing it."
            )
        return (
            "⚠️ Файл слишком большой для обработки через Telegram.\n\n"
            "Попробуй отправить меньший файл или укоротить/сжать."
        )

    @property
    def stt_busy(self) -> str:
        if self.lang == "en":
            return "Speech recognition is busy right now. Try again in a minute."
        return "Сейчас распознавание занято. Попробуй ещё раз через минуту."

    @property
    def stt_preparing(self) -> str:
        return "🧠 Preparing…" if self.lang == "en" else "🧠 Подготавливаю распознавание…"

    @property
    def stt_recognizing(self) -> str:
        return "🧠 Recognizing…" if self.lang == "en" else "🧠 Распознаю…"

    @property
    def stt_done(self) -> str:
        return "✅ Done" if self.lang == "en" else "✅ Готово"

    @property
    def stt_done_file(self) -> str:
        return "✅ Done (file)" if self.lang == "en" else "✅ Готово (файл)"

    @property
    def stt_timeout(self) -> str:
        if self.lang == "en":
            return "⏳ Recognition took too long."
        return "⏳ Распознавание заняло слишком много времени."

    @property
    def stt_empty(self) -> str:
        if self.lang == "en":
            return "Could not recognize speech."
        return "Не получилось распознать речь."

    @property
    def convert_error(self) -> str:
        if self.lang == "en":
            return "Could not convert the file."
        return "Не получилось преобразовать файл."

    @property
    def convert_done(self) -> str:
        return "✅ Done" if self.lang == "en" else "✅ Готово"

    def quota_exceeded(self, used: int, limit: int) -> str:
        if self.lang == "en":
            return (
                f"⛔ <b>Daily limit reached</b>\n\n"
                f"Used: {used} / {limit}\n\n"
                "Get <b>Premium</b> for unlimited downloads\n"
                "or invite a friend — get +5 downloads."
            )
        return (
            f"⛔ <b>Дневной лимит исчерпан</b>\n\n"
            f"Использовано: {used} / {limit}\n\n"
            "Получи <b>Premium</b> для безлимитных загрузок\n"
            "или пригласи друга — получишь +5 загрузок."
        )

    def quota_exceeded_short(self) -> str:
        if self.lang == "en":
            return "⛔ <b>Daily limit reached</b>\n\nGet <b>Premium</b> for unlimited downloads."
        return "⛔ <b>Дневной лимит исчерпан</b>\n\nПолучи <b>Premium</b> для безлимитных загрузок."

    def mode_title(self, mode: str) -> str:
        if self.lang == "en":
            return {"audio": "Converting", "stt": "Recognizing"}.get(mode, "Processing")
        return {"audio": "Преобразую", "stt": "Распознаю"}.get(mode, "Обрабатываю")

    # ── Premium ───────────────────────────────────────────────────────────────
    @property
    def premium_menu_header(self) -> str:
        if self.lang == "en":
            return "⚡️ <b>EagleTools Premium</b>\n\nChoose a plan:\n"
        return "⚡️ <b>EagleTools Premium</b>\n\nВыбери тариф:\n"

    @property
    def premium_menu_features(self) -> str:
        if self.lang == "en":
            return "\n✅ Unlimited downloads\n✅ Priority processing\n✅ All future features"
        return "\n✅ Безлимитные загрузки\n✅ Приоритетная обработка\n✅ Все будущие функции"

    def premium_tier_text(self, label: str, stars: int, ton: float) -> str:
        if self.lang == "en":
            return (
                f"⚡️ <b>Premium — {label}</b>\n\n"
                f"Price:\n"
                f"• ⭐ {stars} Telegram Stars\n"
                f"• 💎 {ton} TON\n\n"
                "Choose payment method:"
            )
        return (
            f"⚡️ <b>Premium — {label}</b>\n\n"
            f"Стоимость:\n"
            f"• ⭐ {stars} Telegram Stars\n"
            f"• 💎 {ton} TON\n\n"
            "Выбери способ оплаты:"
        )

    def premium_invoice_title(self, label: str) -> str:
        return f"EagleTools Premium — {label}"

    def premium_invoice_desc(self, label: str) -> str:
        if self.lang == "en":
            return f"Unlimited downloads for {label}. Activated immediately after payment."
        return f"Безлимитные загрузки на {label}. Активируется сразу после оплаты."

    @property
    def premium_unknown_tier(self) -> str:
        return "Unknown plan" if self.lang == "en" else "Неизвестный тариф"

    def premium_activated(self, label: str, until: str) -> str:
        if self.lang == "en":
            return (
                f"✅ <b>Premium activated!</b>\n\n"
                f"Plan: {label}\n"
                f"Valid until: {until}\n\n"
                "Thank you for your support! 🦅"
            )
        return (
            f"✅ <b>Premium активирован!</b>\n\n"
            f"Тариф: {label}\n"
            f"Действует до: {until}\n\n"
            "Спасибо за поддержку! 🦅"
        )

    @property
    def premium_activated_forever(self) -> str:
        return "forever" if self.lang == "en" else "навсегда"

    @property
    def premium_payment_error(self) -> str:
        if self.lang == "en":
            return "⚠️ Payment received, but activation failed. Please contact support."
        return "⚠️ Оплата прошла, но возникла ошибка активации. Напиши в поддержку."

    def premium_ton_text(self, label: str, ton: float, wallet: str, comment: str) -> str:
        if self.lang == "en":
            return (
                f"💎 <b>TON Payment — {label}</b>\n\n"
                f"Amount: <b>{ton} TON</b>\n\n"
                "Press <b>Pay in wallet</b> — it will open your TON wallet "
                "with the address and amount already filled in.\n\n"
                f"Or send manually to:\n<code>{wallet}</code>\n"
                f"Comment: <code>{comment}</code>\n\n"
                "After payment press <b>I sent TON</b>."
            )
        return (
            f"💎 <b>Оплата TON — {label}</b>\n\n"
            f"Сумма: <b>{ton} TON</b>\n\n"
            "Нажми <b>Оплатить в кошельке</b> — откроется твой TON кошелёк "
            "с уже заполненным адресом и суммой.\n\n"
            f"Или отправь вручную на:\n<code>{wallet}</code>\n"
            f"Комментарий: <code>{comment}</code>\n\n"
            "После оплаты нажми <b>Я отправил TON</b>."
        )

    def premium_ton_sent_text(self, ton: float, comment: str) -> str:
        if self.lang == "en":
            return (
                f"⏳ <b>Request received</b>\n\n"
                f"Waiting for confirmation of {ton} TON transfer.\n"
                f"Comment: <code>{comment}</code>\n\n"
                "Usually up to 10 minutes. You'll get a notification after confirmation."
            )
        return (
            f"⏳ <b>Заявка принята</b>\n\n"
            f"Ожидаем подтверждение перевода {ton} TON.\n"
            f"Комментарий: <code>{comment}</code>\n\n"
            "Обычно до 10 минут. После подтверждения придёт уведомление."
        )

    @property
    def btn_ton_sent(self) -> str:
        return "✅ I sent TON" if self.lang == "en" else "✅ Я отправил TON"

    @property
    def btn_pay_stars(self) -> str:
        return "⭐ Pay with Stars" if self.lang == "en" else "⭐ Оплатить Stars"

    @property
    def btn_pay_ton(self) -> str:
        return "💎 Pay with TON" if self.lang == "en" else "💎 Оплатить TON"

    # ── Referral ──────────────────────────────────────────────────────────────
    def referral_text(self, link: str) -> str:
        if self.lang == "en":
            return (
                f"🎁 <b>Referral Program</b>\n\n"
                f"For each invited friend — <b>+5 downloads</b> per day.\n\n"
                f"Your link:\n<code>{link}</code>"
            )
        return (
            f"🎁 <b>Реферальная программа</b>\n\n"
            f"За каждого приглашённого друга — <b>+5 загрузок</b> в день.\n\n"
            f"Твоя ссылка:\n<code>{link}</code>"
        )

    @property
    def btn_back_premium(self) -> str:
        return "◀️ Back" if self.lang == "en" else "◀️ Назад"

    # ── Profile ───────────────────────────────────────────────────────────────
    def profile_plan_free(self) -> str:
        return "📋 Plan: Free" if self.lang == "en" else "📋 Тариф: Free"

    def profile_premium_until(self, until: str) -> str:
        return f"⚡️ Premium until {until}"

    def profile_downloads_today(self, used: int, limit: str) -> str:
        if self.lang == "en":
            return f"📊 Downloads today: {used} / {limit}"
        return f"📊 Загрузок сегодня: {used} / {limit}"

    def profile_downloads_left(self, used: int, limit: int, left: int) -> str:
        if self.lang == "en":
            return f"📊 Downloads today: {used} / {limit}  (left: {left})"
        return f"📊 Загрузок сегодня: {used} / {limit}  (осталось {left})"

    def profile_referrals(self, count: int) -> str:
        return f"👥 Referrals: {count}" if self.lang == "en" else f"👥 Рефералов: {count}"

    def profile_premium_bonus_ready(self) -> str:
        if self.lang == "en":
            return "✅ Every 3 referrals = +3 days Premium"
        return "✅ Каждые 3 реферала = +3 дня Premium"

    def profile_premium_bonus_need(self, need: int) -> str:
        if self.lang == "en":
            return f"🎁 Next +3 days Premium: {need} more referral(s)"
        return f"🎁 До +3 дней Premium: ещё {need} реферал(а)"

    def profile_ref_hint(self) -> str:
        if self.lang == "en":
            return "🎁 For each friend — <b>+5 downloads</b> per day"
        return "🎁 За каждого друга — <b>+5 загрузок</b> в день"

    def profile_ref_link_label(self) -> str:
        return "🔗 Your link:" if self.lang == "en" else "🔗 Твоя ссылка:"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmt_name(fmt: str | None) -> str:
    f = (fmt or "mp3").lower()
    return {"mp3": "MP3", "m4a": "M4A", "wav": "WAV", "opus": "OPUS"}.get(f, f.upper())


def get_strings(lang: str | None) -> Strings:
    """Return Strings for the given language code (defaults to Russian)."""
    return Strings(lang="en" if (lang or "").startswith("en") else "ru")


def t(lang: str | None) -> Strings:
    """Shortcut alias for get_strings."""
    return get_strings(lang)