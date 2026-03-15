/* ============================================================
   EagleTools — Onboarding Tour
   Показывается один раз при первом запуске Mini App.
   Флаг хранится в localStorage: "et_onboarded_v1"
   ============================================================ */

(function () {
  "use strict";

  const STORAGE_KEY = "et_onboarded_v1";

  /* ── i18n ── */
  function getLang() {
    try {
      const tg = window.Telegram?.WebApp;
      const lang = tg?.initDataUnsafe?.user?.language_code || navigator.language || "ru";
      return lang.startsWith("en") ? "en" : "ru";
    } catch { return "ru"; }
  }

  const STEPS = {
    ru: [
      {
        target: "[data-tool='save']",
        title: "Скачать видео",
        text: "Вставь ссылку с YouTube или любой другой платформы — получишь MP4 файл.",
        anchor: "bottom",
      },
      {
        target: "[data-tool='audio']",
        title: "Музыка с SoundCloud",
        text: "Ссылка на трек или плейлист — и у тебя готовый MP3. Работает мгновенно.",
        anchor: "top",
      },
      {
        target: "[data-tab='recent']",
        title: "История загрузок",
        text: "Все твои файлы здесь. Скачивай, слушай и делись прямо из приложения.",
        anchor: "bottom",
      },
      {
        target: "[data-tab='profile']",
        title: "Твой профиль",
        text: "Следи за лимитами, приглашай друзей и получай бонусные загрузки.",
        anchor: "bottom",
      },
      {
        target: "[data-action='open-settings']",
        title: "Настройки",
        text: "Язык, формат аудио и другие параметры под тебя.",
        anchor: "bottom",
      },
    ],
    en: [
      {
        target: "[data-tool='save']",
        title: "Download video",
        text: "Paste a YouTube or any other platform link — get an MP4 file instantly.",
        anchor: "bottom",
      },
      {
        target: "[data-tool='audio']",
        title: "Music from SoundCloud",
        text: "Drop a track or playlist link and get a ready MP3. Fast and simple.",
        anchor: "top",
      },
      {
        target: "[data-tab='recent']",
        title: "Download history",
        text: "All your files are here. Download, listen and share right from the app.",
        anchor: "bottom",
      },
      {
        target: "[data-tab='profile']",
        title: "Your profile",
        text: "Track your limits, invite friends and earn bonus downloads.",
        anchor: "bottom",
      },
      {
        target: "[data-action='open-settings']",
        title: "Settings",
        text: "Language, audio format and other options — all yours to configure.",
        anchor: "bottom",
      },
    ],
  };

  /* ── CSS ── */
  const CSS = `
    #et-tour-overlay {
      position: fixed; inset: 0; z-index: 9000;
      pointer-events: none;
    }
    #et-tour-overlay.active { pointer-events: all; }

    /* SVG-маска — вырез под spotlight */
    #et-tour-svg {
      position: absolute; inset: 0;
      width: 100%; height: 100%;
      pointer-events: none;
    }
    #et-tour-cutout {
      transition: d 0.38s cubic-bezier(.4,0,.2,1),
                  rx 0.38s cubic-bezier(.4,0,.2,1),
                  ry 0.38s cubic-bezier(.4,0,.2,1);
    }

    /* Подсветка-рамка вокруг элемента */
    #et-tour-ring {
      position: absolute;
      border: 2px solid #e8195a;
      border-radius: 14px;
      box-shadow: 0 0 0 3px rgba(232,25,90,.18), 0 0 22px rgba(232,25,90,.22);
      pointer-events: none;
      z-index: 9100;
      transition: all 0.38s cubic-bezier(.4,0,.2,1);
    }

    /* Тултип */
    #et-tour-tip {
      position: absolute;
      z-index: 9200;
      width: min(300px, calc(100vw - 32px));
      background: var(--bg3, #16131f);
      border: 1px solid rgba(232,25,90,.28);
      border-radius: 18px;
      padding: 18px 18px 14px;
      box-shadow: 0 18px 50px rgba(0,0,0,.58), 0 0 0 1px rgba(255,255,255,.04);
      transition: all 0.38s cubic-bezier(.4,0,.2,1);
      opacity: 0;
      transform: translateY(6px);
    }
    #et-tour-tip.visible {
      opacity: 1;
      transform: translateY(0);
    }

    /* Стрелка тултипа */
    #et-tour-tip::before {
      content: '';
      position: absolute;
      width: 10px; height: 10px;
      background: var(--bg3, #16131f);
      border-left: 1px solid rgba(232,25,90,.28);
      border-top: 1px solid rgba(232,25,90,.28);
      border-radius: 2px 0 0 0;
    }
    #et-tour-tip.arrow-top::before {
      top: -6px; left: 24px;
      transform: rotate(45deg);
    }
    #et-tour-tip.arrow-bottom::before {
      bottom: -6px; left: 24px;
      transform: rotate(225deg);
    }

    .et-tip-step {
      font-size: 10px; font-weight: 600;
      color: #e8195a;
      letter-spacing: .8px;
      text-transform: uppercase;
      margin-bottom: 6px;
    }
    .et-tip-title {
      font-size: 16px; font-weight: 600;
      color: var(--text, rgba(255,255,255,.92));
      margin-bottom: 6px; line-height: 1.3;
    }
    .et-tip-text {
      font-size: 13px;
      color: var(--text2, rgba(255,255,255,.52));
      line-height: 1.55;
      margin-bottom: 14px;
    }

    .et-tip-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .et-dots {
      display: flex; gap: 5px; align-items: center;
    }
    .et-dot {
      width: 5px; height: 5px;
      border-radius: 50%;
      background: rgba(255,255,255,.18);
      transition: all .25s ease;
    }
    .et-dot.active {
      background: #e8195a;
      width: 16px; border-radius: 3px;
    }

    .et-tip-btns {
      display: flex; gap: 8px; align-items: center;
    }
    .et-btn-skip {
      font-size: 12px;
      color: var(--text3, rgba(255,255,255,.28));
      background: none; border: none;
      padding: 6px 2px; cursor: pointer;
      font-family: var(--font, 'DM Sans', sans-serif);
      transition: color .2s;
    }
    .et-btn-skip:hover { color: var(--text2, rgba(255,255,255,.52)); }

    .et-btn-next {
      font-size: 13px; font-weight: 500;
      color: #fff;
      background: #e8195a;
      border: none; border-radius: 10px;
      padding: 7px 16px; cursor: pointer;
      font-family: var(--font, 'DM Sans', sans-serif);
      transition: background .2s, transform .12s;
    }
    .et-btn-next:hover { background: #ff2d6b; }
    .et-btn-next:active { transform: scale(0.96); }

    html[data-theme="light"] #et-tour-tip {
      background: #ffffff;
      border-color: rgba(232,25,90,.22);
      box-shadow: 0 12px 40px rgba(80,40,140,.14), 0 0 0 1px rgba(0,0,0,.04);
    }
    html[data-theme="light"] #et-tour-tip::before {
      background: #ffffff;
    }
    html[data-theme="light"] .et-dot {
      background: rgba(0,0,0,.14);
    }
  `;

  /* ── State ── */
  let current = 0;
  let steps = [];
  let overlay, ring, tip, svg, maskPath;

  /* ── Helpers ── */
  function getRect(el) {
    const r = el.getBoundingClientRect();
    return { top: r.top, left: r.left, width: r.width, height: r.height };
  }

  function pad(r, p) {
    return {
      top: r.top - p,
      left: r.left - p,
      width: r.width + p * 2,
      height: r.height + p * 2,
    };
  }

  /* ── Build DOM ── */
  function buildDOM() {
    const style = document.createElement("style");
    style.textContent = CSS;
    document.head.appendChild(style);

    overlay = document.createElement("div");
    overlay.id = "et-tour-overlay";

    const W = window.innerWidth;
    const H = window.innerHeight;

    overlay.innerHTML = `
      <svg id="et-tour-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <mask id="et-mask">
            <rect width="${W}" height="${H}" fill="white"/>
            <rect id="et-tour-cutout" x="0" y="0" width="0" height="0" rx="14" ry="14" fill="black"/>
          </mask>
        </defs>
        <rect width="${W}" height="${H}" fill="rgba(0,0,0,0.72)" mask="url(#et-mask)"/>
      </svg>
      <div id="et-tour-ring"></div>
      <div id="et-tour-tip"></div>
    `;

    document.body.appendChild(overlay);

    ring = document.getElementById("et-tour-ring");
    tip = document.getElementById("et-tour-tip");
    maskPath = document.getElementById("et-tour-cutout");
    svg = document.getElementById("et-tour-svg");

    /* Клик по затемнению = следующий шаг */
    overlay.addEventListener("click", e => {
      if (!tip.contains(e.target) && !ring.contains(e.target)) next();
    });
  }

  function resizeSVG() {
    if (!svg) return;
    const W = window.innerWidth;
    const H = window.innerHeight;
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.querySelector("rect[mask]").setAttribute("width", W);
    svg.querySelector("rect[mask]").setAttribute("height", H);
    svg.querySelector("mask rect").setAttribute("width", W);
    svg.querySelector("mask rect").setAttribute("height", H);
  }

  /* ── Render step ── */
  function renderStep(idx) {
    const step = steps[idx];
    const el = document.querySelector(step.target);
    if (!el) { next(); return; }

    const r = pad(getRect(el), 6);
    const isLast = idx === steps.length - 1;
    const lang = getLang();

    /* spotlight cutout */
    maskPath.setAttribute("x", r.left);
    maskPath.setAttribute("y", r.top);
    maskPath.setAttribute("width", r.width);
    maskPath.setAttribute("height", r.height);

    /* ring */
    ring.style.top    = r.top + "px";
    ring.style.left   = r.left + "px";
    ring.style.width  = r.width + "px";
    ring.style.height = r.height + "px";

    /* tooltip content */
    const dots = steps.map((_, i) =>
      `<div class="et-dot ${i === idx ? "active" : ""}"></div>`
    ).join("");

    const skipLabel = lang === "en" ? "Skip" : "Пропустить";
    const nextLabel = isLast
      ? (lang === "en" ? "Let's go!" : "Поехали!")
      : (lang === "en" ? "Next" : "Далее");

    tip.innerHTML = `
      <div class="et-tip-step">${lang === "en" ? "Step" : "Шаг"} ${idx + 1} / ${steps.length}</div>
      <div class="et-tip-title">${step.title}</div>
      <div class="et-tip-text">${step.text}</div>
      <div class="et-tip-footer">
        <div class="et-dots">${dots}</div>
        <div class="et-tip-btns">
          <button class="et-btn-skip" id="et-skip">${skipLabel}</button>
          <button class="et-btn-next" id="et-next">${nextLabel}</button>
        </div>
      </div>
    `;

    document.getElementById("et-skip").onclick = finish;
    document.getElementById("et-next").onclick = isLast ? finish : next;

    /* position tooltip */
    requestAnimationFrame(() => {
      const tipW = tip.offsetWidth;
      const tipH = tip.offsetHeight;
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const MARGIN = 12;
      const ARROW = 16;

      let top, arrowClass;

      if (step.anchor === "bottom") {
        /* показываем под элементом */
        top = r.top + r.height + ARROW;
        if (top + tipH > vh - MARGIN) {
          /* нет места снизу — ставим сверху */
          top = r.top - tipH - ARROW;
          arrowClass = "arrow-bottom";
        } else {
          arrowClass = "arrow-top";
        }
      } else {
        /* anchor top — показываем над */
        top = r.top - tipH - ARROW;
        if (top < MARGIN) {
          top = r.top + r.height + ARROW;
          arrowClass = "arrow-top";
        } else {
          arrowClass = "arrow-bottom";
        }
      }

      let left = r.left;
      if (left + tipW > vw - MARGIN) left = vw - tipW - MARGIN;
      if (left < MARGIN) left = MARGIN;

      tip.style.top  = top + "px";
      tip.style.left = left + "px";
      tip.className  = arrowClass;

      /* arrow horizontal offset relative to tooltip */
      const arrowEl = tip; /* ::before псевдоэлемент позиционируем через CSS left */
      const arrowLeft = Math.max(12, (r.left + r.width / 2) - left - 5);
      tip.style.setProperty("--et-arrow-left", arrowLeft + "px");

      /* показываем */
      requestAnimationFrame(() => tip.classList.add("visible"));
    });
  }

  /* CSS для стрелки с кастомным отступом */
  const arrowCSS = `
    #et-tour-tip::before { left: var(--et-arrow-left, 24px); }
  `;

  /* ── Navigation ── */
  function next() {
    tip.classList.remove("visible");
    setTimeout(() => {
      current++;
      if (current >= steps.length) { finish(); return; }
      renderStep(current);
    }, 180);
  }

  function finish() {
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch {}
    tip.classList.remove("visible");
    overlay.classList.remove("active");
    setTimeout(() => {
      overlay.style.opacity = "0";
      overlay.style.transition = "opacity .3s ease";
      setTimeout(() => overlay.remove(), 320);
    }, 120);
  }

  /* ── Start ── */
  function start() {

    const lang = getLang();
    steps = STEPS[lang] || STEPS.ru;

    buildDOM();

    /* доп. CSS для стрелки */
    const s2 = document.createElement("style");
    s2.textContent = arrowCSS;
    document.head.appendChild(s2);

    overlay.classList.add("active");
    renderStep(0);

    window.addEventListener("resize", () => {
      resizeSVG();
      renderStep(current);
    });
  }

  /* ── Entry point ── */
  /* Ждём window.load — к этому моменту app.js точно отработал */
  function tryStart() {
    try { if (localStorage.getItem(STORAGE_KEY)) return; } catch {}
    var delay = window.__EAGLE_APP_READY__ ? 500 : 1200;
    setTimeout(start, delay);
  }

  if (document.readyState === "complete") {
    tryStart();
  } else {
    window.addEventListener("load", tryStart, { once: true });
  }

  /* Экспорт для ручного запуска (например из настроек) */
  window.eagleTourStart = function () {
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
    current = 0;
    start();
  };
})();