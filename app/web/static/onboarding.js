// EagleTools Onboarding Tour
// Запускается один раз при первом открытии Mini App
(() => {
  const STORAGE_KEY = "eagle_onboarded_v1";

  // ── Шаги тура ──────────────────────────────────────────────────────────────
  const STEPS = [
    {
      id: "welcome",
      target: null, // fullscreen welcome — без привязки к элементу
      titleRu: "Добро пожаловать в EagleTools 🦅",
      titleEn: "Welcome to EagleTools 🦅",
      textRu: "Твой карманный медиакомбайн прямо в Telegram. Скачивай видео, музыку и распознавай речь за секунды.",
      textEn: "Your pocket media toolkit right inside Telegram. Download videos, music and transcribe speech in seconds.",
      emoji: "🦅",
    },
    {
      id: "tools",
      target: "[data-panel='tools']",
      titleRu: "Инструменты",
      titleEn: "Tools",
      textRu: "Вставь ссылку на YouTube или SoundCloud — и получи файл. Всё работает прямо здесь, без сторонних приложений.",
      textEn: "Paste a YouTube or SoundCloud link and get your file. Everything works right here, no third-party apps needed.",
      emoji: "🧰",
      tab: "tools",
      highlight: ".toolgrid",
    },
    {
      id: "recent",
      target: "[data-panel='recent']",
      titleRu: "История загрузок",
      titleEn: "Download history",
      textRu: "Все твои файлы сохраняются здесь. Можно воспроизвести, скачать или поделиться в любой момент.",
      textEn: "All your files are saved here. Play, download or share them anytime.",
      emoji: "🕐",
      tab: "recent",
      highlight: ".card",
    },
    {
      id: "profile",
      target: "[data-panel='profile']",
      titleRu: "Профиль и лимиты",
      titleEn: "Profile & limits",
      textRu: "Следи за использованием. Бесплатно — 10 загрузок в день. Приглашай друзей и получай +5 за каждого.",
      textEn: "Track your usage. Free plan — 10 downloads per day. Invite friends and get +5 for each one.",
      emoji: "👤",
      tab: "profile",
      highlight: ".usage-card",
    },
    {
      id: "bot",
      target: null,
      titleRu: "Работает и в боте",
      titleEn: "Works in the bot too",
      textRu: "Отправь голосовое сообщение или аудио прямо в @EagleToolsBot — бот распознает речь или конвертирует файл.",
      textEn: "Send a voice message or audio directly to @EagleToolsBot — it will transcribe speech or convert your file.",
      emoji: "🤖",
    },
  ];

  // ── State ──────────────────────────────────────────────────────────────────
  let step = 0;
  let overlay = null;
  let lang = "ru";

  function getLang() {
    try {
      return window.EagleProfile?.settings?.lang || localStorage.getItem("eagle_lang") || "ru";
    } catch { return "ru"; }
  }

  function s(ru, en) {
    return lang === "en" ? en : ru;
  }

  // ── DOM helpers ────────────────────────────────────────────────────────────
  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  // ── Highlight box ──────────────────────────────────────────────────────────
  function getHighlightRect(selector) {
    if (!selector) return null;
    const target = document.querySelector(selector);
    if (!target) return null;
    const r = target.getBoundingClientRect();
    return { top: r.top, left: r.left, width: r.width, height: r.height };
  }

  // ── Build overlay ──────────────────────────────────────────────────────────
  function buildOverlay() {
    const wrap = el("div", "onb-overlay");
    wrap.setAttribute("role", "dialog");
    wrap.setAttribute("aria-modal", "true");

    // SVG spotlight backdrop
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.classList.add("onb-backdrop");
    svg.setAttribute("aria-hidden", "true");
    wrap.appendChild(svg);

    // Card
    const card = el("div", "onb-card");

    const top = el("div", "onb-card__top");
    const emojiEl = el("div", "onb-card__emoji");
    const progress = el("div", "onb-card__progress");
    top.appendChild(emojiEl);
    top.appendChild(progress);

    const title = el("div", "onb-card__title");
    const text = el("div", "onb-card__text");

    const footer = el("div", "onb-card__footer");
    const dots = el("div", "onb-dots");
    const nextBtn = el("button", "onb-btn onb-btn--next");
    nextBtn.type = "button";
    footer.appendChild(dots);
    footer.appendChild(nextBtn);

    const skip = el("button", "onb-skip");
    skip.type = "button";

    card.appendChild(top);
    card.appendChild(title);
    card.appendChild(text);
    card.appendChild(footer);
    card.appendChild(skip);
    wrap.appendChild(card);

    document.body.appendChild(wrap);
    return wrap;
  }

  // ── Render step ────────────────────────────────────────────────────────────
  function renderStep(idx) {
    const data = STEPS[idx];
    if (!data) { finish(); return; }

    // Switch tab if needed
    if (data.tab && window.setTab) {
      window.setTab(data.tab);
    }

    const card = overlay.querySelector(".onb-card");
    const emojiEl = overlay.querySelector(".onb-card__emoji");
    const progressEl = overlay.querySelector(".onb-card__progress");
    const titleEl = overlay.querySelector(".onb-card__title");
    const textEl = overlay.querySelector(".onb-card__text");
    const nextBtn = overlay.querySelector(".onb-btn--next");
    const skipBtn = overlay.querySelector(".onb-skip");
    const dotsEl = overlay.querySelector(".onb-dots");
    const svg = overlay.querySelector(".onb-backdrop");

    // Animate card out → update → in
    card.classList.add("is-exiting");

    setTimeout(() => {
      // Emoji
      emojiEl.textContent = data.emoji;

      // Progress text
      progressEl.textContent = `${idx + 1} / ${STEPS.length}`;

      // Title + text
      titleEl.textContent = s(data.titleRu, data.titleEn);
      textEl.textContent = s(data.textRu, data.textEn);

      // Next button
      const isLast = idx === STEPS.length - 1;
      nextBtn.textContent = isLast
        ? s("Начать работу →", "Get started →")
        : s("Далее →", "Next →");

      // Skip
      skipBtn.textContent = s("Пропустить", "Skip");

      // Dots
      dotsEl.innerHTML = STEPS.map((_, i) =>
        `<div class="onb-dot ${i === idx ? "is-active" : ""}" aria-hidden="true"></div>`
      ).join("");

      // Spotlight
      updateSpotlight(svg, data.highlight || null);

      // Position card
      positionCard(card, data.highlight || null);

      card.classList.remove("is-exiting");
      card.classList.add("is-entering");
      setTimeout(() => card.classList.remove("is-entering"), 380);
    }, 160);
  }

  function updateSpotlight(svg, highlightSel) {
    const W = window.innerWidth, H = window.innerHeight;
    svg.setAttribute("width", W);
    svg.setAttribute("height", H);
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);

    if (!highlightSel) {
      // Full dark overlay — no spotlight
      svg.innerHTML = `
        <defs>
          <radialGradient id="onbGrad" cx="50%" cy="40%" r="55%">
            <stop offset="0%" stop-color="rgba(232,25,90,0.06)"/>
            <stop offset="100%" stop-color="rgba(8,6,14,0)"/>
          </radialGradient>
        </defs>
        <rect width="${W}" height="${H}" fill="rgba(8,6,14,0.88)"/>
        <rect width="${W}" height="${H}" fill="url(#onbGrad)"/>
      `;
      return;
    }

    const r = getHighlightRect(highlightSel);
    if (!r) {
      updateSpotlight(svg, null);
      return;
    }

    const pad = 10;
    const rx = 16;
    const x = r.left - pad, y = r.top - pad;
    const w = r.width + pad * 2, h = r.height + pad * 2;

    svg.innerHTML = `
      <defs>
        <mask id="onbMask">
          <rect width="${W}" height="${H}" fill="white"/>
          <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="black"/>
        </mask>
        <filter id="onbBlur">
          <feGaussianBlur stdDeviation="1.5"/>
        </filter>
      </defs>
      <rect width="${W}" height="${H}" fill="rgba(8,6,14,0.82)" mask="url(#onbMask)"/>
      <rect x="${x - 1}" y="${y - 1}" width="${w + 2}" height="${h + 2}" rx="${rx + 1}"
            fill="none" stroke="rgba(232,25,90,0.55)" stroke-width="1.5"/>
      <rect x="${x - 3}" y="${y - 3}" width="${w + 6}" height="${h + 6}" rx="${rx + 3}"
            fill="none" stroke="rgba(232,25,90,0.15)" stroke-width="1"/>
    `;
  }

  function positionCard(card, highlightSel) {
    // Default: bottom center
    card.style.bottom = "24px";
    card.style.top = "";
    card.style.left = "50%";
    card.style.transform = "translateX(-50%)";

    if (!highlightSel) return;

    const r = getHighlightRect(highlightSel);
    if (!r) return;

    const cardH = 280;
    const viewH = window.innerHeight;
    const spaceBelow = viewH - r.top - r.height;
    const spaceAbove = r.top;

    if (spaceBelow >= cardH + 20) {
      card.style.top = `${r.top + r.height + 16}px`;
      card.style.bottom = "";
    } else if (spaceAbove >= cardH + 20) {
      card.style.top = `${r.top - cardH - 16}px`;
      card.style.bottom = "";
    } else {
      card.style.bottom = "24px";
      card.style.top = "";
    }
  }

  // ── Navigation ─────────────────────────────────────────────────────────────
  function next() {
    if (step < STEPS.length - 1) {
      step++;
      renderStep(step);
    } else {
      finish();
    }
  }

  function finish() {
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch {}

    const card = overlay?.querySelector(".onb-card");
    if (card) {
      card.classList.add("is-exiting");
    }
    overlay?.classList.add("is-hiding");
    setTimeout(() => {
      overlay?.remove();
      overlay = null;
      // Switch back to tools tab
      if (window.setTab) window.setTab("tools");
    }, 350);
  }

  // ── Public API ─────────────────────────────────────────────────────────────
  function start(force = false) {
    try {
      if (!force && localStorage.getItem(STORAGE_KEY)) return;
    } catch {}

    lang = getLang();
    step = 0;

    overlay = buildOverlay();

    // Bind events
    overlay.querySelector(".onb-btn--next").addEventListener("click", next);
    overlay.querySelector(".onb-skip").addEventListener("click", finish);

    // Keyboard
    function onKey(e) {
      if (e.key === "ArrowRight" || e.key === "Enter") next();
      if (e.key === "Escape") finish();
    }
    document.addEventListener("keydown", onKey);
    overlay.addEventListener("remove", () => document.removeEventListener("keydown", onKey));

    // Swipe support
    let touchStartX = 0;
    overlay.addEventListener("touchstart", e => { touchStartX = e.touches[0].clientX; }, { passive: true });
    overlay.addEventListener("touchend", e => {
      const dx = e.changedTouches[0].clientX - touchStartX;
      if (dx < -50) next();
      if (dx > 50) { if (step > 0) { step--; renderStep(step); } }
    }, { passive: true });

    // Show
    requestAnimationFrame(() => {
      overlay.classList.add("is-visible");
      renderStep(0);
    });
  }

  // ── Auto-start ─────────────────────────────────────────────────────────────
  function maybeStart() {
    // Ждём пока приложение инициализируется
    if (!window.__EAGLE_APP_READY__) {
      let attempts = 0;
      const poll = setInterval(() => {
        attempts++;
        if (window.__EAGLE_APP_READY__ || attempts > 30) {
          clearInterval(poll);
          if (window.__EAGLE_APP_READY__) start();
        }
      }, 200);
    } else {
      setTimeout(start, 400);
    }
  }

  window.EagleOnboarding = { start, reset: () => { try { localStorage.removeItem(STORAGE_KEY); } catch {} } };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", maybeStart, { once: true });
  } else {
    maybeStart();
  }
})();