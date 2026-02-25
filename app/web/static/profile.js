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
      help_1: "Открой вкладку Инструменты",
      help_2: "Вставь ссылку на контент",
      help_3: "Нажми Скачать или MP3",
      help_4: "Дождись завершения обработки",
      help_5: "Скачай результат из истории",
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
      help_1: "Open Tools tab",
      help_2: "Paste a link",
      help_3: "Click Download or MP3",
      help_4: "Wait for processing",
      help_5: "Download from Recent",
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

  function setAvatar(elOrId, url, fallbackText = "👤") {
    const el = typeof elOrId === "string" ? document.getElementById(elOrId) : elOrId;
    if (!el) return;

    const u = (url || "").trim();
    if (!u) {
      el.classList.remove("has-photo");
      el.style.backgroundImage = "";
      el.textContent = fallbackText;
      return;
    }

    el.textContent = "";
    el.classList.add("has-photo");
    el.style.backgroundImage = `url("${u}")`;
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
    setAvatar("profileAvatar", p.user_photo_url || "");
    setAvatar("headerAvatar", p.user_photo_url || "");

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