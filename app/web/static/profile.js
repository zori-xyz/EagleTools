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
      recent_empty: "Нет загрузок",
      profile_title: "Профиль",
      plan: "Тариф",
      usage_title: "Использование",
      requests_today: "запросов сегодня",
      remaining: "Осталось",
      upgrade_premium: "Получить Premium",
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
      tour_btn: "Повторить тур по приложению",
      sort_date_new: "Сначала новые",
      sort_date_old: "Сначала старые",
      sort_name_az: "По имени А–Я",
      sort_name_za: "По имени Я–А",
      sort_size_big: "По размеру ↓",
      sort_size_small: "По размеру ↑",
      conv_title: "Конвертер файлов",
      conv_desc: "Видео, аудио, фото, PDF, документы",
      conv_badge: "SMART",
      conv_drop_label: "Выбери файл",
      conv_drop_sub: "или перетащи сюда · до 100 МБ",
      conv_choose_action: "Что сделать с файлом",
      conv_btn_run: "Конвертировать",
      conv_processing: "Обрабатываю…",
      conv_done: "Готово",
      conv_error: "Ошибка конвертации",
      conv_unsupported: "Формат не поддерживается",
      conv_too_big: "Файл слишком большой (макс. 100 МБ)",
      conv_select_action: "Выбери действие",
      language: "Язык",
      theme: "Тема",
      help_title: "Помощь",
      tab_tools: "Инструменты",
      tab_recent: "История",
      tab_profile: "Профиль",
      tab_help: "Помощь",
      links: "Видео",
      // Help - Mini App
      help_miniapp_title: "Как пользоваться Mini App",
      help_ma_1: "Открой вкладку Инструменты — вставь ссылку на видео или аудио",
      help_ma_2: "Поддерживаются YouTube, SoundCloud и другие публичные сайты",
      help_ma_3: "Нажми Скачать для видео (mp4) или MP3 для аудио",
      help_ma_4: "После загрузки нажми Открыть или Поделиться",
      help_ma_5: "Все файлы видны во вкладке История",
      // Help - Bot
      help_bot_title: "Функции бота в Telegram",
      help_bot_audio_title: "Конвертер аудио",
      help_bot_audio_desc: "Отправь аудио, видео или голосовое — бот конвертирует в mp3, wav или другой формат",
      help_bot_stt_title: "Распознавание речи",
      help_bot_stt_desc: "Отправь голосовое или аудио — бот расшифрует текст с помощью Whisper AI",
      // Help - Premium
      help_premium_title: "Преимущества Premium",
      help_prem_1: "Безлимитные загрузки — без суточного лимита",
      help_prem_2: "Приоритетная обработка заданий",
      help_prem_3: "Доступ ко всем будущим функциям",
      help_prem_4: "Поддержка развития проекта",
      // Help - Referral
      help_ref_title: "Реферальная система",
      // Help - Privacy
      help_privacy_title: "Конфиденциальность",
      // Player
      player_open: "🌐 Открыть",
      player_share: "📤 Поделиться",
      // Tools
      tool_video_desc: "YouTube и другие платформы",
      tool_audio_desc: "Треки и плейлисты",
      // Actions
      limit_reached: "Дневной лимит исчерпан",
      err_empty_url: "Вставь ссылку",
      job_created: "Задание создано",
      done: "Готово!",
      done_in: "Готово за",
      cleared: "Очищено",
      copied: "Скопировано!",
      deleted: "Удалено",
      confirm_delete: "Удалить эту задачу?",
      queued: "В очереди",
      expired: "Истёк",
      file_expired: "Файл удалён с сервера",
      starting: "Загружаю…",
      processing: "Обрабатываю",
      conv_reading: "Читаю файл…",
      conv_uploading: "Загружаю…",
      link_copied: "Ссылка скопирована",
      err_save_failed: "Не удалось загрузить файл",
      err_soundcloud: "Ошибка SoundCloud",
      err_ip_blocked: "Платформа заблокировала сервер",
      err_timeout: "Превышено время ожидания",
      err_bad_url: "Неверная ссылка",
      err_unknown: "Неизвестная ошибка",
      copy_failed: "Ошибка копирования",
      // Help steps (HTML allowed)
      help_ma_1_html: "Открой вкладку <b>Инструменты</b> — вставь ссылку на видео или аудио",
      help_ma_2_html: "Поддерживаются <b>YouTube</b>, <b>SoundCloud</b> и другие публичные сайты",
      help_ma_3_html: "Нажми <b>Скачать</b> для видео (mp4) или <b>MP3</b> для аудио",
      help_ma_4_html: "После загрузки нажми <b>Открыть</b> или <b>Поделиться</b>",
      help_ma_5_html: "Все файлы видны во вкладке <b>История</b>",
      help_ref_1_html: "Скопируй реферальную ссылку во вкладке Профиль",
      help_ref_2_html: "Поделись с друзьями — пусть запустят бота по ней",
      help_ref_3_html: "За каждого друга получишь <b>+5 загрузок</b> в день",
      help_ref_4_html: "Каждые <b>3 приглашённых</b> дают Premium +3 дня",
      help_privacy_text: "Мы не храним твои файлы. Все загруженные файлы автоматически удаляются после скачивания.",
      player_sub: "EagleTools",
    },
    en: {
      subtitle: "Links → files",
      btn_download: "Download",
      btn_make_mp3: "MP3",
      recent_title: "Recent Downloads",
      recent_empty: "No downloads yet",
      profile_title: "Profile",
      plan: "Plan",
      usage_title: "Usage",
      requests_today: "requests today",
      remaining: "Remaining",
      upgrade_premium: "Get Premium",
      valid_until: "Valid until",
      referrals_title: "Referral Program",
      refs_subtitle: "Invite friends and get bonuses",
      friends_invited: "friends invited",
      until_reward: "until reward",
      ref_copy_btn: "Copy",
      ref_share_btn: "Share",
      settings: "Settings",
      support: "Support",
      privacy_policy: "Privacy Policy",
      tour_btn: "Repeat app tour",
      sort_date_new: "Newest first",
      sort_date_old: "Oldest first",
      sort_name_az: "Name A–Z",
      sort_name_za: "Name Z–A",
      sort_size_big: "Size ↓",
      sort_size_small: "Size ↑",
      conv_title: "File Converter",
      conv_desc: "Video, audio, photo, PDF, documents",
      conv_badge: "SMART",
      conv_drop_label: "Choose a file",
      conv_drop_sub: "or drag it here · up to 100 MB",
      conv_choose_action: "What to do with the file",
      conv_btn_run: "Convert",
      conv_processing: "Processing…",
      conv_done: "Done",
      conv_error: "Conversion error",
      conv_unsupported: "Format not supported",
      conv_too_big: "File is too large (max 100 MB)",
      conv_select_action: "Choose an action",
      expired: "Expired",
      file_expired: "File deleted from server",
      starting: "Downloading…",
      processing: "Processing",
      conv_reading: "Reading file…",
      conv_uploading: "Uploading…",
      language: "Language",
      theme: "Theme",
      help_title: "Help",
      tab_tools: "Tools",
      tab_recent: "Recent",
      tab_profile: "Profile",
      tab_help: "Help",
      links: "Video",
      // Help - Mini App
      help_miniapp_title: "How to use Mini App",
      help_ma_1: "Open the Tools tab — paste a link to video or audio",
      help_ma_2: "Supports YouTube, SoundCloud and other public sites",
      help_ma_3: "Click Download for video (mp4) or MP3 for audio",
      help_ma_4: "After download click Open or Share",
      help_ma_5: "All files are visible in the Recent tab",
      // Help - Bot
      help_bot_title: "Bot functions in Telegram",
      help_bot_audio_title: "Audio converter",
      help_bot_audio_desc: "Send audio, video or voice — bot converts to mp3, wav or other formats",
      help_bot_stt_title: "Speech recognition",
      help_bot_stt_desc: "Send voice or audio — bot transcribes text using Whisper AI",
      // Help - Premium
      help_premium_title: "Premium benefits",
      help_prem_1: "Unlimited downloads — no daily limit",
      help_prem_2: "Priority job processing",
      help_prem_3: "Access to all upcoming features",
      help_prem_4: "Support the project's development",
      // Help - Referral
      help_ref_title: "Referral system",
      // Help - Privacy
      help_privacy_title: "Privacy",
      // Player
      player_open: "🌐 Open",
      player_share: "📤 Share",
      // Tools
      tool_video_desc: "YouTube and other platforms",
      tool_audio_desc: "Tracks and playlists",
      // Actions
      limit_reached: "Daily limit reached",
      err_empty_url: "Paste a link first",
      job_created: "Job created",
      done: "Done!",
      done_in: "Done in",
      cleared: "Cleared",
      copied: "Copied!",
      deleted: "Deleted",
      confirm_delete: "Delete this item?",
      queued: "Queued",
      link_copied: "Link copied",
      err_save_failed: "Failed to download file",
      err_soundcloud: "SoundCloud error",
      err_ip_blocked: "Platform blocked the server IP",
      err_timeout: "Request timed out",
      err_bad_url: "Invalid link",
      err_unknown: "Unknown error",
      copy_failed: "Failed to copy",
      help_ma_1_html: "Open the <b>Tools</b> tab — paste a link to video or audio",
      help_ma_2_html: "Supports <b>YouTube</b>, <b>SoundCloud</b> and other public sites",
      help_ma_3_html: "Click <b>Download</b> for video (mp4) or <b>MP3</b> for audio",
      help_ma_4_html: "After download click <b>Open</b> or <b>Share</b>",
      help_ma_5_html: "All files are visible in the <b>Recent</b> tab",
      help_ref_1_html: "Copy your referral link from the Profile tab",
      help_ref_2_html: "Share it with friends — have them start the bot via your link",
      help_ref_3_html: "Each friend gives you <b>+5 downloads</b> per day",
      help_ref_4_html: "Every <b>3 invited</b> friends give Premium +3 days",
      help_privacy_text: "We don't store your files. All uploaded files are automatically deleted after downloading.",
      player_sub: "EagleTools",
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

  function setHtml(id, html) {
    const el = document.getElementById(id);
    if (el && html) el.innerHTML = html;
  }
  function setText2(id, txt) {
    const el = document.getElementById(id);
    if (el && txt) el.textContent = txt;
  }

  function applyI18n() {
    const s = getSettings();
    const L = s.lang;
    document.documentElement.lang = L;

    // Standard data-i18n
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const k = el.getAttribute("data-i18n");
      const txt = dict?.[L]?.[k] ?? dict?.en?.[k];
      if (typeof txt === "string" && txt.length) el.textContent = txt;
    });

    // Help - Mini App steps
    setHtml("hma1", dict?.[L]?.help_ma_1_html ?? dict?.en?.help_ma_1_html);
    setHtml("hma2", dict?.[L]?.help_ma_2_html ?? dict?.en?.help_ma_2_html);
    setHtml("hma3", dict?.[L]?.help_ma_3_html ?? dict?.en?.help_ma_3_html);
    setHtml("hma4", dict?.[L]?.help_ma_4_html ?? dict?.en?.help_ma_4_html);
    setHtml("hma5", dict?.[L]?.help_ma_5_html ?? dict?.en?.help_ma_5_html);

    // Help - Referral steps
    setHtml("hrf1", dict?.[L]?.help_ref_1_html ?? dict?.en?.help_ref_1_html);
    setHtml("hrf2", dict?.[L]?.help_ref_2_html ?? dict?.en?.help_ref_2_html);
    setHtml("hrf3", dict?.[L]?.help_ref_3_html ?? dict?.en?.help_ref_3_html);
    setHtml("hrf4", dict?.[L]?.help_ref_4_html ?? dict?.en?.help_ref_4_html);

    // Help - Privacy
    setHtml("hpriv", dict?.[L]?.help_privacy_text ?? dict?.en?.help_privacy_text);

    // Player labels
    setText2("playerOpenLabel", dict?.[L]?.player_open ?? dict?.en?.player_open);
    setText2("playerShareLabel", dict?.[L]?.player_share ?? dict?.en?.player_share);

    // Premium button (has icon + text span)
    const upgBtn = document.getElementById("upgradePlanBtn");
    if (upgBtn) {
      const upgSpan = upgBtn.querySelector("span[data-i18n]") || upgBtn;
      const upgTxt = dict?.[L]?.upgrade_premium ?? dict?.en?.upgrade_premium;
      if (upgTxt) upgSpan.textContent = upgTxt;
    }

    // Help upgrade button
    const helpUpgBtns = document.querySelectorAll("button[data-action='open-upgrade']");
    helpUpgBtns.forEach(btn => {
      const txt = dict?.[L]?.upgrade_premium ?? dict?.en?.upgrade_premium;
      if (txt) btn.textContent = "⚡️ " + txt;
    });
  }

  async function fetchProfile() {
    try {
      const resp = await window.EagleAPI?.getJson?.("/api/profile");
      if (resp && typeof resp === "object" && "ok" in resp && "data" in resp) return resp.ok ? resp.data : null;
      return resp || null;
    } catch { return null; }
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
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit"
      });
    } catch { return String(iso); }
  }

  function getBotUsername() { return window.BOT_USERNAME || "EagleToolsBot"; }

  const AVATAR_COLORS = [
    ["#e8195a","#c2185b"],
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
    const isLarge = el.classList.contains("profile-hero__avatar");
    const size = isLarge ? 140 : 52;
    const fontSize = isLarge ? 56 : 22;
    const canvas = document.createElement("canvas");
    canvas.width = size; canvas.height = size;
    const ctx = canvas.getContext("2d");
    const grad = ctx.createLinearGradient(0, 0, size, size);
    grad.addColorStop(0, c1); grad.addColorStop(1, c2);
    ctx.fillStyle = grad;
    const r = isLarge ? 28 : 12;
    ctx.beginPath();
    ctx.moveTo(r, 0); ctx.lineTo(size - r, 0);
    ctx.quadraticCurveTo(size, 0, size, r);
    ctx.lineTo(size, size - r);
    ctx.quadraticCurveTo(size, size, size - r, size);
    ctx.lineTo(r, size);
    ctx.quadraticCurveTo(0, size, 0, size - r);
    ctx.lineTo(0, r);
    ctx.quadraticCurveTo(0, 0, r, 0);
    ctx.closePath(); ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.92)";
    ctx.font = `700 ${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
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
      el.textContent = ""; el.classList.add("has-photo");
      el.style.backgroundImage = `url("${u}")`; return;
    }
    if (name && name.trim()) { _makeInitialsAvatar(el, name.trim()); return; }
    el.classList.remove("has-photo"); el.style.backgroundImage = ""; el.textContent = "👤";
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
    setWidth("profileBarFill", p.is_unlimited ? 0 : Math.round((used / Math.max(1, limit)) * 100));

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

  function setLang(lang) { saveSettings({ lang }); init(); }
  function setTheme(theme) { saveSettings({ theme }); init(); }

  function init() {
    applyTheme();
    applyI18n();
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