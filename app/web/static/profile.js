// app/web/static/profile.js
(() => {
  const LS_KEY = "eagle_profile_settings";
  const DEFAULTS = { lang: "ru", theme: "dark" };

  function safeJsonParse(s) {
    try { return JSON.parse(s); } catch { return null; }
  }

  function readSettingsRaw() {
    try { return localStorage.getItem(LS_KEY); } catch { return null; }
  }

  function writeSettingsRaw(v) {
    try { localStorage.setItem(LS_KEY, v); return true; } catch { return false; }
  }

  function normalizeSettings(obj) {
    const out = { ...DEFAULTS };
    if (obj && typeof obj === "object") {
      if (obj.lang === "ru" || obj.lang === "en") out.lang = obj.lang;
      if (obj.theme === "dark" || obj.theme === "light") out.theme = obj.theme;
    }
    return out;
  }

  function getSettings() {
    const raw = readSettingsRaw();
    const parsed = raw ? safeJsonParse(raw) : null;
    return normalizeSettings(parsed);
  }

  function saveSettings(patch) {
    const cur = getSettings();
    const next = normalizeSettings({ ...cur, ...(patch || {}) });
    writeSettingsRaw(JSON.stringify(next));
    return next;
  }

  const dict = {
    ru: {
      subtitle: "Links → files",
      btn_download: "Скачать",
      btn_make_mp3: "MP3",
      recent_title: "История загрузок",
      recent_empty: "Пока нет задач",
      profile_title: "Профиль",
      plan: "Тариф",
      usage_title: "Использование",
      requests_today: "запросов сегодня",
      remaining: "Осталось",
      upgrade_premium: "⚡️ Получить Premium",
      valid_until: "Активен до",
      referrals_title: "Реферальная программа",
      refs_subtitle: "Приглашай друзей и получай бонусы",
      friends_invited: "друзей приглашено",
      until_reward: "до награды",
      ref_copy_btn: "Копировать",
      ref_share_btn: "Поделиться",
      settings: "Настройки",
      support: "Поддержка",
      privacy_policy: "Политика конфиденциальности",
      language: "Язык",
      theme: "Тема",
      help_title: "Помощь",
      how_to_use: "Как пользоваться",
      tab_tools: "Инструменты",
      tab_recent: "История",
      tab_profile: "Профиль",
      tab_help: "Помощь",
      links: "Ссылки",
      help_1: "Открой вкладку Инструменты",
      help_2: "Вставь ссылку на контент",
      help_3: "Нажми Скачать или MP3",
      help_4: "Дождись завершения обработки",
      help_5: "Скачай результат из истории",
      help_miniapp_title: "Как пользоваться Mini App",
      help_ma_1: "Открой вкладку Инструменты — вставь ссылку на видео или аудио",
      help_ma_2: "Поддерживаются YouTube, TikTok, Instagram, SoundCloud и другие",
      help_ma_3: "Нажми Скачать для видео (mp4) или MP3 для аудио",
      help_ma_4: "Файл скачается автоматически или появится ссылка в результате",
      help_ma_5: "Все файлы видны во вкладке История",
      help_bot_title: "Функции бота в Telegram",
      help_bot_audio_title: "Конвертер аудио",
      help_bot_audio_desc: "Отправь аудио, видео или голосовое — бот конвертирует в mp3, wav или другой формат",
      help_bot_stt_title: "Распознавание речи",
      help_bot_stt_desc: "Отправь голосовое или аудио — бот расшифрует текст с помощью Whisper AI",
      help_bot_1: "В боте выбери режим через меню Инструменты",
      help_bot_2: "Отправь файл — бот автоматически обработает его",
      help_premium_title: "Преимущества Premium",
      help_prem_1: "Безлимитные загрузки — без суточного лимита",
      help_prem_2: "Приоритетная обработка заданий",
      help_prem_3: "Доступ ко всем будущим функциям",
      help_prem_4: "Поддержка развития проекта",
      help_ref_title: "Реферальная система",
      help_ref_1: "Скопируй свою реферальную ссылку во вкладке Профиль",
      help_ref_2: "Поделись ссылкой с друзьями — пусть запустят бота по ней",
      help_ref_3: "За каждого друга ты получишь +5 загрузок в день",
      help_ref_4: "Каждые 3 приглашённых дают Premium-пользователям +3 дня премиума",
      help_privacy_title: "Конфиденциальность",
      help_privacy_note: "Мы не храним твои файлы. Все загруженные и обработанные файлы автоматически удаляются с сервера после скачивания. Мы не передаём данные третьим лицам.",
      limit_reached: "Дневной лимит исчерпан",
      err_empty_url: "Введите ссылку",
      starting: "Запуск…",
      job_created: "Задача создана",
      status: "Статус",
      done: "Готово",
      done_in: "Готово за",
      cleared: "Очищено",
      copied: "Скопировано!",
      deleted: "Удалено",
      confirm_delete: "Удалить эту задачу?",
      queued: "В очереди",
    },
    en: {
      subtitle: "Links → files",
      tab_tools: "Tools",
      tab_recent: "Recent",
      tab_profile: "Profile",
      tab_help: "Help",
      btn_clear: "Clear",
      btn_download: "Download",
      btn_make_mp3: "Make MP3",
      recent_title: "Recent Downloads",
      recent_empty: "No jobs yet",
      profile_title: "Profile",
      plan: "Plan",
      usage_title: "Usage",
      requests_today: "requests today",
      remaining: "Remaining",
      upgrade_premium: "⚡️ Get Premium",
      valid_until: "Valid until",
      referrals_title: "Referral Program",
      refs_subtitle: "Invite friends and get bonuses",
      friends_invited: "friends invited",
      until_reward: "until reward",
      ref_copy_btn: "Copy",
      ref_share_btn: "Share",
      settings: "Settings",
      support: "Support",
      privacy_policy: "Privacy policy",
      language: "Language",
      theme: "Theme",
      help_title: "Help",
      how_to_use: "How to use",
      tab_tools: "Tools",
      tab_recent: "Recent",
      tab_profile: "Profile",
      tab_help: "Help",
      links: "Links",
      help_1: "Open Tools tab",
      help_2: "Paste a link",
      help_3: "Click Download or MP3",
      help_4: "Wait for processing",
      help_5: "Download from Recent",
      help_miniapp_title: "How to use Mini App",
      help_ma_1: "Open Tools tab — paste a link to video or audio",
      help_ma_2: "Supports YouTube, TikTok, Instagram, SoundCloud and more",
      help_ma_3: "Click Download for video (mp4) or MP3 for audio",
      help_ma_4: "File will download automatically or a link will appear",
      help_ma_5: "All downloaded files are visible in the Recent tab",
      help_bot_title: "Bot functions in Telegram",
      help_bot_audio_title: "Audio converter",
      help_bot_audio_desc: "Send audio, video or voice — bot converts to mp3, wav or other formats",
      help_bot_stt_title: "Speech recognition",
      help_bot_stt_desc: "Send voice or audio — bot transcribes text using Whisper AI",
      help_bot_1: "In the bot, select a mode via the Tools menu",
      help_bot_2: "Send a file — the bot will process it automatically",
      help_premium_title: "Premium benefits",
      help_prem_1: "Unlimited downloads — no daily limit",
      help_prem_2: "Priority job processing",
      help_prem_3: "Access to all upcoming features",
      help_prem_4: "Support the project's development",
      help_ref_title: "Referral system",
      help_ref_1: "Copy your referral link from the Profile tab",
      help_ref_2: "Share it with friends — have them start the bot via your link",
      help_ref_3: "Each friend gives you +5 downloads per day",
      help_ref_4: "Every 3 invited friends give Premium users +3 days of premium",
      help_privacy_title: "Privacy",
      help_privacy_note: "We don't store your files. All uploaded and processed files are automatically deleted from our servers after download. We don't share your data with third parties.",
      limit_reached: "Daily limit reached",
      err_empty_url: "Paste a link first",
      starting: "Starting…",
      job_created: "Job created",
      status: "Status",
      done: "Done",
      done_in: "Done in",
      cleared: "Cleared",
      copied: "Copied!",
      deleted: "Deleted",
      confirm_delete: "Delete this item?",
      queued: "Queued",
    },
  };

  const resolveKey = (k) => k;

  function t(key) {
    const k = resolveKey(key);
    const s = getSettings();
    return dict?.[s.lang]?.[k] ?? dict?.en?.[k] ?? "";
  }

  function applyTheme() {
    const s = getSettings();
    document.documentElement.setAttribute("data-theme", s.theme);
  }

  function applyI18n() {
    const s = getSettings();
    document.documentElement.lang = s.lang;

    const nodes = document.querySelectorAll("[data-i18n]");
    nodes.forEach((el) => {
      const k = el.getAttribute("data-i18n");
      const txt = dict?.[s.lang]?.[resolveKey(k)] ?? dict?.en?.[resolveKey(k)];
      if (typeof txt === "string" && txt.length) el.textContent = txt;
    });
  }

  async function fetchProfile() {
    try {
      const resp = await window.EagleAPI?.getJson?.("/api/profile");
      if (resp && typeof resp === "object" && "ok" in resp && "data" in resp) return resp.ok ? resp.data : null;
      return resp || null;
    } catch {
      return null;
    }
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function setWidth(id, pct) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.width = `${Math.max(0, Math.min(100, pct))}%`;
  }

  function fmtDate(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return String(iso);
      const s = getSettings();
      return d.toLocaleDateString(s.lang === "ru" ? "ru-RU" : "en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      });
    } catch {
      return String(iso);
    }
  }

  function getBotUsername() {
    return window.BOT_USERNAME || "EagleToolsBot";
  }

  const AVATAR_COLORS = [
    ["#2ea6ff","#0066cc"],
    ["#a855f7","#7c3aed"],
    ["#f59e0b","#d97706"],
    ["#10b981","#059669"],
    ["#ef4444","#dc2626"],
    ["#ec4899","#db2777"],
    ["#14b8a6","#0d9488"],
    ["#f97316","#ea580c"],
  ];

  function _avatarColorForName(name) {
    let hash = 0;
    for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
    return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
  }

  function _makeInitialsAvatar(el, name) {
    const initial = (name || "?").trim().charAt(0).toUpperCase();
    const [c1, c2] = _avatarColorForName(name || "?");

    // profile hero avatar — larger canvas
    const isLarge = el.classList.contains("profile-hero__avatar");
    const size = isLarge ? 140 : 52;
    const fontSize = isLarge ? 56 : 22;

    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");

    const grad = ctx.createLinearGradient(0, 0, size, size);
    grad.addColorStop(0, c1);
    grad.addColorStop(1, c2);
    ctx.fillStyle = grad;

    const r = isLarge ? 28 : 12;
    ctx.beginPath();
    ctx.moveTo(r, 0);
    ctx.lineTo(size - r, 0);
    ctx.quadraticCurveTo(size, 0, size, r);
    ctx.lineTo(size, size - r);
    ctx.quadraticCurveTo(size, size, size - r, size);
    ctx.lineTo(r, size);
    ctx.quadraticCurveTo(0, size, 0, size - r);
    ctx.lineTo(0, r);
    ctx.quadraticCurveTo(0, 0, r, 0);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = "rgba(255,255,255,0.92)";
    ctx.font = `700 ${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(initial, size / 2, size / 2 + 1);

    el.textContent = "";
    el.classList.add("has-photo");
    el.style.backgroundImage = `url("${canvas.toDataURL()}")`;
  }

  function setAvatar(elOrId, url, name = "") {
    const el = typeof elOrId === "string" ? document.getElementById(elOrId) : elOrId;
    if (!el) return;

    const u = (url || "").trim();
    if (u) {
      el.textContent = "";
      el.classList.add("has-photo");
      el.style.backgroundImage = `url("${u}")`;
      return;
    }

    if (name && name.trim()) {
      _makeInitialsAvatar(el, name.trim());
      return;
    }

    el.classList.remove("has-photo");
    el.style.backgroundImage = "";
    el.textContent = "👤";
  }

  async function renderProfile() {
    const p = await fetchProfile();
    if (!p) return;

    const isPremium = p.plan === "premium" || p.is_unlimited;
    const used = Number(p.used_today || 0);
    const limit = Number(p.daily_limit || 10);
    const left = p.is_unlimited ? "∞" : String(p.left_today != null ? p.left_today : limit - used);
    const refs = Number(p.referrals || 0);

    setText("profileName", p.user_name || "User");
    setText("profileUsername", p.user_username ? `@${p.user_username}` : "");

    // avatar in profile panel + header button (if exists in DOM)
    setAvatar("profileAvatar", p.user_photo_url || "", p.user_name || "");
    setAvatar("headerAvatar", p.user_photo_url || "", p.user_name || "");

    const badge = document.getElementById("profilePlanBadge");
    if (badge) {
      badge.textContent = isPremium ? "PREMIUM" : "FREE";
      badge.classList.toggle("is-premium", isPremium);
    }

    setText("profileUsed", String(used));
    setText("profileLimit", p.is_unlimited ? "∞" : String(limit));
    setText("profileLeft", left);

    const pct = p.is_unlimited ? 0 : Math.round((used / Math.max(1, limit)) * 100);
    setWidth("profileBarFill", pct);

    const premiumCard = document.getElementById("premiumCard");
    if (premiumCard) {
      premiumCard.style.display = isPremium ? "" : "none";
      if (isPremium && p.premium_until) setText("profilePremiumUntil", fmtDate(p.premium_until));
    }

    const upgradeBtn = document.getElementById("upgradePlanBtn");
    if (upgradeBtn) upgradeBtn.style.display = isPremium ? "none" : "";

    setText("profileRefs", String(refs));
    setText("profileRefLink", p.ref_link || "—");

    const rewardStat = document.getElementById("rewardStat");
    if (rewardStat) {
      if (isPremium && p.reward_need != null && p.reward_need > 0) {
        setText("profileRewardNeed", String(p.reward_need));
        rewardStat.style.display = "";
      } else {
        rewardStat.style.display = "none";
      }
    }
  }

  function setupUpgradeButton() {
    const btn = document.getElementById("upgradePlanBtn");
    if (!btn) return;

    btn.addEventListener("click", () => {
      const botUsername = getBotUsername();
      const url = `https://t.me/${botUsername}`;
      if (window.Telegram?.WebApp) window.Telegram.WebApp.openTelegramLink(url);
      else window.open(url, "_blank");
    });
  }

  function setLang(lang) { saveSettings({ lang }); init(); }
  function setTheme(theme) { saveSettings({ theme }); init(); }

  function init() {
    applyTheme();
    applyI18n();
    setupUpgradeButton();
  }

  window.EagleProfile = {
    t,
    get settings() { return getSettings(); },
    saveSettings,
    setLang,
    setTheme,
    init,
    renderProfile,
    get refLink() {
      const el = document.getElementById("profileRefLink");
      const v = el?.textContent?.trim() || "";
      return v === "—" ? "" : v;
    },
  };

  init();
})();