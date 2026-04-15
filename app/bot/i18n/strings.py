# app/bot/i18n/strings.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Strings:
    lang: str

    # ── /start welcome ────────────────────────────────────────────────────────
    @property
    def welcome_text(self) -> str:
        if self.lang == "en":
            return (
                "🦅 <b>EagleTools</b>\n\n"
                "Just send me a link or a file — I'll figure out the rest.\n\n"
                "<b>Links:</b> YouTube · TikTok · Instagram · Twitter · VK · and more\n"
                "<b>Files:</b> convert audio, extract audio from video, transcribe speech\n\n"
                "Everything else is in the mini app 👇"
            )
        return (
            "🦅 <b>EagleTools</b>\n\n"
            "Просто отправь мне ссылку или файл — я разберусь сам.\n\n"
            "<b>Ссылки:</b> YouTube · TikTok · Instagram · Twitter · VK · и другие\n"
            "<b>Файлы:</b> конвертировать аудио, извлечь звук из видео, расшифровать речь\n\n"
            "Всё остальное — в мини-приложении 👇"
        )

    @property
    def settings_text(self) -> str:
        if self.lang == "en":
            return "⚙️ <b>Settings</b>"
        return "⚙️ <b>Настройки</b>"

    # ── Link detection / processing ───────────────────────────────────────────
    def link_detected(self, platform_label: str) -> str:
        if self.lang == "en":
            return f"{platform_label}\n\nWhat should I do with this link?"
        return f"{platform_label}\n\nЧто делаем со ссылкой?"

    @property
    def link_processing(self) -> str:
        return "⏳ Downloading…" if self.lang == "en" else "⏳ Скачиваю…"

    @property
    def link_processing_audio(self) -> str:
        return "⏳ Extracting audio…" if self.lang == "en" else "⏳ Извлекаю аудио…"

    @property
    def link_processing_stt(self) -> str:
        return "⏳ Downloading and transcribing…" if self.lang == "en" else "⏳ Скачиваю и распознаю…"

    @property
    def link_done(self) -> str:
        return "✅ Done" if self.lang == "en" else "✅ Готово"

    @property
    def link_error(self) -> str:
        if self.lang == "en":
            return (
                "😔 <b>Couldn't download this.</b>\n\n"
                "The link might be private, geo-blocked or unsupported.\n"
                "Try the mini app — it has more options."
            )
        return (
            "😔 <b>Не удалось скачать.</b>\n\n"
            "Ссылка может быть приватной, заблокированной по региону или неподдерживаемой.\n"
            "Попробуй через мини-приложение — там больше возможностей."
        )

    @property
    def link_error_too_large(self) -> str:
        if self.lang == "en":
            return (
                "⚠️ <b>File too large for Telegram</b>\n\n"
                "Telegram limits file uploads to ~50 MB.\n"
                "Try the mini app to download directly."
            )
        return (
            "⚠️ <b>Файл слишком большой для Telegram</b>\n\n"
            "Telegram ограничивает загрузку файлов примерно 50 МБ.\n"
            "Скачай напрямую через мини-приложение."
        )

    @property
    def link_error_timeout(self) -> str:
        if self.lang == "en":
            return "⏳ Download timed out. The server took too long."
        return "⏳ Загрузка заняла слишком много времени. Попробуй ещё раз."

    # ── File detection / processing ───────────────────────────────────────────
    def file_detected(self, type_label: str) -> str:
        if self.lang == "en":
            return f"{type_label}\n\nWhat should I do with it?"
        return f"{type_label}\n\nЧто делаем?"

    @property
    def file_processing(self) -> str:
        return "⏳ Processing…" if self.lang == "en" else "⏳ Обрабатываю…"

    @property
    def file_done(self) -> str:
        return "✅ Done" if self.lang == "en" else "✅ Готово"

    @property
    def file_error(self) -> str:
        if self.lang == "en":
            return "😔 Couldn't process the file. It might be corrupted or unsupported."
        return "😔 Не удалось обработать файл. Он может быть повреждён или не поддерживается."

    @property
    def file_too_big(self) -> str:
        if self.lang == "en":
            return (
                "⚠️ <b>File too large</b>\n\n"
                "Maximum size for bot processing is 19 MB.\n"
                "Use the mini app for larger files."
            )
        return (
            "⚠️ <b>Файл слишком большой</b>\n\n"
            "Максимальный размер для обработки в боте — 19 МБ.\n"
            "Для больших файлов используй мини-приложение."
        )

    # ── STT ───────────────────────────────────────────────────────────────────
    @property
    def stt_preparing(self) -> str:
        return "🧠 Preparing speech recognition…" if self.lang == "en" else "🧠 Подготавливаю распознавание…"

    @property
    def stt_recognizing(self) -> str:
        return "🧠 Recognizing speech…" if self.lang == "en" else "🧠 Распознаю речь…"

    @property
    def stt_done(self) -> str:
        return "📝 Transcript:" if self.lang == "en" else "📝 Расшифровка:"

    @property
    def stt_busy(self) -> str:
        if self.lang == "en":
            return "🧠 Speech recognition is busy. Try again in a minute."
        return "🧠 Распознавание занято. Попробуй через минуту."

    @property
    def stt_timeout(self) -> str:
        if self.lang == "en":
            return "⏳ Recognition took too long. Try a shorter file."
        return "⏳ Распознавание заняло слишком долго. Попробуй файл покороче."

    @property
    def stt_empty(self) -> str:
        if self.lang == "en":
            return "🤔 Couldn't recognize any speech in this file."
        return "🤔 Не удалось распознать речь в этом файле."

    # ── Audio conversion ──────────────────────────────────────────────────────
    @property
    def convert_done(self) -> str:
        return "✅ Converted" if self.lang == "en" else "✅ Конвертировано"

    @property
    def convert_error(self) -> str:
        if self.lang == "en":
            return "😔 Conversion failed. Check the file format."
        return "😔 Не удалось конвертировать. Проверь формат файла."

    # ── Quota ─────────────────────────────────────────────────────────────────
    def quota_exceeded(self, used: int, limit: int) -> str:
        if self.lang == "en":
            return (
                f"⛔ <b>Daily limit reached</b> ({used}/{limit})\n\n"
                "Get <b>Premium</b> for unlimited access\n"
                "or invite a friend — get <b>+5 downloads</b>."
            )
        return (
            f"⛔ <b>Дневной лимит исчерпан</b> ({used}/{limit})\n\n"
            "Оформи <b>Premium</b> для безлимитного доступа\n"
            "или пригласи друга — получи <b>+5 загрузок</b>."
        )

    def quota_exceeded_short(self) -> str:
        if self.lang == "en":
            return "⛔ <b>Daily limit reached.</b> Get <b>Premium</b> for unlimited access."
        return "⛔ <b>Дневной лимит исчерпан.</b> Оформи <b>Premium</b> для безлимита."

    # ── Keyboards ─────────────────────────────────────────────────────────────

    # Link action buttons
    @property
    def btn_download_video(self) -> str:
        return "🎬 Download video" if self.lang == "en" else "🎬 Скачать видео"

    @property
    def btn_extract_audio(self) -> str:
        return "🎵 Audio (MP3)" if self.lang == "en" else "🎵 Аудио (MP3)"

    @property
    def btn_transcribe(self) -> str:
        return "📝 Transcribe" if self.lang == "en" else "📝 Расшифровать"

    @property
    def btn_open_app(self) -> str:
        return "🔗 Open in app" if self.lang == "en" else "🔗 Открыть в приложении"

    @property
    def btn_download_file(self) -> str:
        return "💾 Download" if self.lang == "en" else "💾 Скачать"

    # File action buttons
    @property
    def btn_convert_format(self) -> str:
        return "🔄 Convert format" if self.lang == "en" else "🔄 Конвертировать"

    @property
    def btn_extract_audio_from_video(self) -> str:
        return "🎵 Extract audio" if self.lang == "en" else "🎵 Извлечь аудио"

    @property
    def btn_done(self) -> str:
        return "✓ Done" if self.lang == "en" else "✓ Готово"

    @property
    def btn_cancel(self) -> str:
        return "✕ Cancel" if self.lang == "en" else "✕ Отмена"

    # Format picker
    @property
    def btn_pick_format(self) -> str:
        return "Pick format:" if self.lang == "en" else "Выбери формат:"

    # Common navigation
    @property
    def btn_back(self) -> str:
        return "⬅️ Back" if self.lang == "en" else "⬅️ Назад"

    @property
    def btn_settings(self) -> str:
        return "⚙️ Settings" if self.lang == "en" else "⚙️ Настройки"

    @property
    def btn_lang_toggle(self) -> str:
        return "🇷🇺 Switch to Russian" if self.lang == "en" else "🇬🇧 Switch to English"

    @property
    def btn_privacy(self) -> str:
        return "📄 Privacy Policy" if self.lang == "en" else "📄 Политика конфиденциальности"

    @property
    def btn_get_premium(self) -> str:
        return "⚡️ Get Premium" if self.lang == "en" else "⚡️ Получить Premium"

    @property
    def btn_invite_friend(self) -> str:
        return "🎁 Invite friend (+5 downloads)" if self.lang == "en" else "🎁 Пригласить друга (+5 загрузок)"

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
                f"Send exactly <b>{ton} TON</b> to:\n"
                f"<code>{wallet}</code>\n\n"
                f"Comment:\n"
                f"<code>{comment}</code>\n\n"
                "After payment, press the button below."
            )
        return (
            f"💎 <b>Оплата TON — {label}</b>\n\n"
            f"Отправь ровно <b>{ton} TON</b> на адрес:\n"
            f"<code>{wallet}</code>\n\n"
            f"В комментарии укажи:\n"
            f"<code>{comment}</code>\n\n"
            "После оплаты нажми кнопку ниже."
        )

    def premium_ton_sent_text(self, ton: float, comment: str) -> str:
        if self.lang == "en":
            return (
                f"⏳ <b>Request received</b>\n\n"
                f"Waiting for {ton} TON confirmation.\n"
                f"Comment: <code>{comment}</code>\n\n"
                "Usually up to 10 minutes. You'll be notified."
            )
        return (
            f"⏳ <b>Заявка принята</b>\n\n"
            f"Ожидаем подтверждение перевода {ton} TON.\n"
            f"Комментарий: <code>{comment}</code>\n\n"
            "Обычно до 10 минут. Придёт уведомление."
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

    @property
    def cryptobot_pay_label(self) -> str:
        return "💎 Pay in CryptoBot" if self.lang == "en" else "💎 Оплатить в CryptoBot"

    @property
    def cryptobot_check_label(self) -> str:
        return "🔍 Check payment" if self.lang == "en" else "🔍 Проверить оплату"

    @property
    def cryptobot_not_paid(self) -> str:
        if self.lang == "en":
            return "⏳ Payment not found yet. Try in a few seconds."
        return "⏳ Оплата ещё не найдена. Попробуй через пару секунд."

    @property
    def btn_back_premium(self) -> str:
        return "◀️ Back" if self.lang == "en" else "◀️ Назад"

    # ── Referral ──────────────────────────────────────────────────────────────
    def referral_text(self, link: str) -> str:
        if self.lang == "en":
            return (
                f"🎁 <b>Referral Program</b>\n\n"
                f"For each friend you invite — <b>+5 downloads</b> per day.\n\n"
                f"Your link:\n<code>{link}</code>"
            )
        return (
            f"🎁 <b>Реферальная программа</b>\n\n"
            f"За каждого приглашённого друга — <b>+5 загрузок</b> в день.\n\n"
            f"Твоя ссылка:\n<code>{link}</code>"
        )

    # ── Audio format (keep for backward compat in premium flow) ───────────────
    @property
    def audiofmt_unknown(self) -> str:
        return "Unknown format" if self.lang == "en" else "Неизвестный формат"

    def audiofmt_text(self, fmt: str) -> str:
        fmt_name = _fmt_name(fmt)
        if self.lang == "en":
            return f"✅ Format selected: {fmt_name}\n\nSend a file."
        return f"✅ Формат выбран: {fmt_name}\n\nОтправь файл."

    # ── Progress / misc ───────────────────────────────────────────────────────
    def mode_title(self, mode: str) -> str:
        if self.lang == "en":
            return {"audio": "Converting", "stt": "Recognizing"}.get(mode, "Processing")
        return {"audio": "Конвертирую", "stt": "Распознаю"}.get(mode, "Обрабатываю")

    # ── Profile (kept for referral screen reachable via inline button) ────────
    @property
    def profile_plan_free(self) -> str:
        return "📋 Plan: Free" if self.lang == "en" else "📋 Тариф: Free"

    def profile_premium_until(self, until: str) -> str:
        if self.lang == "en":
            return f"⚡️ Premium until {until}"
        return f"⚡️ Premium до {until}"

    def profile_downloads_today(self, used: int, limit: str) -> str:
        if self.lang == "en":
            return f"📊 Today: {used} / {limit}"
        return f"📊 Сегодня: {used} / {limit}"

    def profile_downloads_left(self, used: int, limit: int, left: int) -> str:
        if self.lang == "en":
            return f"📊 Today: {used} / {limit}  ({left} left)"
        return f"📊 Сегодня: {used} / {limit}  (осталось {left})"

    def profile_referrals(self, count: int) -> str:
        return f"👥 Referrals: {count}" if self.lang == "en" else f"👥 Рефералов: {count}"

    @property
    def profile_premium_bonus_ready(self) -> str:
        if self.lang == "en":
            return "✅ Every 3 referrals = +3 days Premium"
        return "✅ Каждые 3 реферала = +3 дня Premium"

    def profile_premium_bonus_need(self, need: int) -> str:
        if self.lang == "en":
            return f"🎁 {need} more referral(s) → +3 days Premium"
        return f"🎁 Ещё {need} реферал(а) → +3 дня Premium"

    @property
    def profile_ref_hint(self) -> str:
        if self.lang == "en":
            return "🎁 Per friend — <b>+5 downloads</b> per day"
        return "🎁 За каждого друга — <b>+5 загрузок</b> в день"

    @property
    def profile_ref_link_label(self) -> str:
        return "🔗 Your link:" if self.lang == "en" else "🔗 Твоя ссылка:"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmt_name(fmt: str | None) -> str:
    f = (fmt or "mp3").lower()
    return {"mp3": "MP3", "m4a": "M4A", "wav": "WAV", "opus": "OPUS"}.get(f, f.upper())


def get_strings(lang: str | None) -> Strings:
    return Strings(lang="en" if (lang or "").startswith("en") else "ru")


def t(lang: str | None) -> Strings:
    return get_strings(lang)
