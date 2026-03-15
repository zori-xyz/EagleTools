/* ============================================================
   EagleTools — Onboarding Tour v2
   - Язык берётся из eagle_profile_settings (как в profile.js)
   - Перед каждым шагом переключает на нужный таб
   - Корректный повторный запуск (cleanup перед стартом)
   ============================================================ */
(function () {
  "use strict";

  const STORAGE_KEY = "et_onboarded_v1";
  const PROFILE_KEY = "eagle_profile_settings";

  function getLang() {
    /* profile.js пишет lang в document.documentElement.lang — самый надёжный источник */
    try {
      const docLang = document.documentElement.lang || "";
      if (docLang === "en") return "en";
      if (docLang === "ru") return "ru";
    } catch {}
    /* Fallback: читаем из localStorage напрямую */
    try {
      const raw = localStorage.getItem(PROFILE_KEY);
      if (raw) {
        const obj = JSON.parse(raw);
        if (obj && obj.lang === "en") return "en";
        if (obj && obj.lang === "ru") return "ru";
      }
    } catch {}
    return "ru";
  }

  const STEPS = {
    ru: [
      { tab: "tools",   target: "[data-tool='save']",          title: "Скачать видео",        text: "Вставь ссылку с YouTube или любой другой платформы — получишь готовый MP4 файл." },
      { tab: "tools",   target: "[data-tool='audio']",         title: "Музыка с SoundCloud",  text: "Ссылка на трек или плейлист — и у тебя готовый MP3. Быстро и просто." },
      { tab: "recent",  target: "[data-tab='recent']",         title: "История загрузок",     text: "Все твои файлы здесь. Скачивай, слушай и делись прямо из приложения." },
      { tab: "profile", target: "[data-tab='profile']",        title: "Твой профиль",         text: "Следи за лимитами, приглашай друзей и получай бонусные загрузки." },
      { tab: "tools",   target: "[data-action='open-settings']", title: "Настройки",          text: "Язык, формат аудио и тема оформления — настрой под себя." },
    ],
    en: [
      { tab: "tools",   target: "[data-tool='save']",          title: "Download video",       text: "Paste a YouTube or any other platform link — get a ready MP4 file instantly." },
      { tab: "tools",   target: "[data-tool='audio']",         title: "Music from SoundCloud",text: "Drop a track or playlist link and get a ready MP3. Fast and simple." },
      { tab: "recent",  target: "[data-tab='recent']",         title: "Download history",     text: "All your files are here. Download, listen and share right from the app." },
      { tab: "profile", target: "[data-tab='profile']",        title: "Your profile",         text: "Track your limits, invite friends and earn bonus downloads." },
      { tab: "tools",   target: "[data-action='open-settings']", title: "Settings",           text: "Language, audio format and theme — configure it your way." },
    ],
  };

  const CSS = `
    #et-overlay { position:fixed; inset:0; z-index:9000; pointer-events:none; }
    #et-overlay.et-active { pointer-events:all; }
    #et-svg { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; }
    #et-ring {
      position:absolute; border:2px solid #e8195a; border-radius:14px;
      box-shadow:0 0 0 3px rgba(232,25,90,.18),0 0 22px rgba(232,25,90,.20);
      pointer-events:none; z-index:9100;
      transition:top .32s cubic-bezier(.4,0,.2,1),left .32s cubic-bezier(.4,0,.2,1),
                 width .32s cubic-bezier(.4,0,.2,1),height .32s cubic-bezier(.4,0,.2,1);
    }
    #et-tip {
      position:absolute; z-index:9200; width:min(288px,calc(100vw - 28px));
      background:var(--bg3,#16131f); border:1px solid rgba(232,25,90,.25);
      border-radius:18px; padding:18px 18px 14px;
      box-shadow:0 18px 50px rgba(0,0,0,.55);
      opacity:0; transform:translateY(8px);
      transition:opacity .25s ease,transform .25s ease,
                 top .32s cubic-bezier(.4,0,.2,1),left .32s cubic-bezier(.4,0,.2,1);
      pointer-events:all;
    }
    #et-tip.et-visible { opacity:1; transform:translateY(0); }
    #et-tip::before {
      content:''; position:absolute; width:10px; height:10px;
      background:var(--bg3,#16131f);
      border-left:1px solid rgba(232,25,90,.25); border-top:1px solid rgba(232,25,90,.25);
      border-radius:2px 0 0 0; left:var(--et-ax,22px);
    }
    #et-tip.et-arrow-top::before    { top:-6px;    transform:rotate(45deg); }
    #et-tip.et-arrow-bottom::before { bottom:-6px; transform:rotate(225deg); }
    .et-step  { font-size:10px; font-weight:600; color:#e8195a; letter-spacing:.8px; text-transform:uppercase; margin-bottom:5px; }
    .et-title { font-size:15px; font-weight:600; color:var(--text,rgba(255,255,255,.92)); margin-bottom:5px; line-height:1.3; }
    .et-text  { font-size:13px; color:var(--text2,rgba(255,255,255,.50)); line-height:1.55; margin-bottom:14px; }
    .et-footer{ display:flex; align-items:center; justify-content:space-between; }
    .et-dots  { display:flex; gap:5px; align-items:center; }
    .et-dot   { width:5px; height:5px; border-radius:50%; background:rgba(255,255,255,.15); transition:all .25s ease; }
    .et-dot.et-on { background:#e8195a; width:14px; border-radius:3px; }
    .et-btns  { display:flex; gap:8px; align-items:center; }
    .et-skip  { font-size:12px; color:var(--text3,rgba(255,255,255,.28)); background:none; border:none; padding:6px 2px; cursor:pointer; font-family:var(--font,'DM Sans',sans-serif); transition:color .2s; }
    .et-skip:hover { color:var(--text2,rgba(255,255,255,.50)); }
    .et-next  { font-size:13px; font-weight:500; color:#fff; background:#e8195a; border:none; border-radius:10px; padding:7px 16px; cursor:pointer; font-family:var(--font,'DM Sans',sans-serif); transition:background .18s,transform .1s; }
    .et-next:hover  { background:#ff2d6b; }
    .et-next:active { transform:scale(0.96); }
    html[data-theme="light"] #et-tip { background:#fff; border-color:rgba(208,20,83,.18); box-shadow:0 12px 40px rgba(80,40,140,.13); }
    html[data-theme="light"] #et-tip::before { background:#fff; border-color:rgba(208,20,83,.18); }
    html[data-theme="light"] .et-dot { background:rgba(0,0,0,.12); }
  `;

  let current = 0, steps = [], overlay, ring, tip, cutout, styleEl, resizeHandler;

  function cleanup() {
    if (resizeHandler) { window.removeEventListener("resize", resizeHandler); resizeHandler = null; }
    if (overlay)  { overlay.remove();  overlay  = null; }
    if (styleEl)  { styleEl.remove();  styleEl  = null; }
    ring = tip = cutout = null;
  }

  function switchTab(tabName) {
    const btn = document.querySelector('[data-tab="' + tabName + '"]');
    if (btn) btn.click();
  }

  function updateMask(r) {
    if (!cutout) return;
    cutout.setAttribute("x", r.left);
    cutout.setAttribute("y", r.top);
    cutout.setAttribute("width",  r.width);
    cutout.setAttribute("height", r.height);
    const svgEl = document.getElementById("et-svg");
    if (svgEl) {
      const W = window.innerWidth, H = window.innerHeight;
      svgEl.setAttribute("viewBox", "0 0 " + W + " " + H);
      svgEl.querySelectorAll("rect:not(#et-cutout)").forEach(function(rc) {
        rc.setAttribute("width", W); rc.setAttribute("height", H);
      });
    }
  }

  function renderStep(idx) {
    var step = steps[idx];
    if (!step) return;

    switchTab(step.tab);

    setTimeout(function() {
      var el = document.querySelector(step.target);
      if (!el) { doNext(); return; }

      var er    = el.getBoundingClientRect();
      var PAD   = 6;
      var r     = { top: er.top-PAD, left: er.left-PAD, width: er.width+PAD*2, height: er.height+PAD*2 };
      var isLast = idx === steps.length - 1;
      var lang  = getLang();

      updateMask(r);
      ring.style.top    = r.top    + "px";
      ring.style.left   = r.left   + "px";
      ring.style.width  = r.width  + "px";
      ring.style.height = r.height + "px";

      var dots = steps.map(function(_, i) {
        return '<span class="et-dot' + (i === idx ? " et-on" : "") + '"></span>';
      }).join("");

      var skipLbl = lang === "en" ? "Skip"      : "Пропустить";
      var nextLbl = isLast ? (lang === "en" ? "Let\u2019s go!" : "Поехали!") : (lang === "en" ? "Next" : "Далее");
      var stepLbl = lang === "en" ? "Step" : "Шаг";

      tip.innerHTML =
        '<div class="et-step">' + stepLbl + ' ' + (idx+1) + ' / ' + steps.length + '</div>' +
        '<div class="et-title">' + step.title + '</div>' +
        '<div class="et-text">'  + step.text  + '</div>' +
        '<div class="et-footer">' +
          '<div class="et-dots">' + dots + '</div>' +
          '<div class="et-btns">' +
            '<button class="et-skip">' + skipLbl + '</button>' +
            '<button class="et-next">' + nextLbl + '</button>' +
          '</div>' +
        '</div>';

      tip.querySelector(".et-skip").onclick = finish;
      tip.querySelector(".et-next").onclick = isLast ? finish : doNext;

      tip.classList.remove("et-visible");

      requestAnimationFrame(function() {
        var tipW   = tip.offsetWidth  || 288;
        var tipH   = tip.offsetHeight || 160;
        var vw     = window.innerWidth;
        var vh     = window.innerHeight;
        var MARGIN = 12, ARROW = 14;
        var top, arrowCls;
        var belowTop = r.top + r.height + ARROW;
        var aboveTop = r.top - tipH - ARROW;

        if (belowTop + tipH < vh - MARGIN)    { top = belowTop; arrowCls = "et-arrow-top"; }
        else if (aboveTop > MARGIN)            { top = aboveTop; arrowCls = "et-arrow-bottom"; }
        else                                   { top = belowTop; arrowCls = "et-arrow-top"; }

        var left = r.left;
        if (left + tipW > vw - MARGIN) left = vw - tipW - MARGIN;
        if (left < MARGIN) left = MARGIN;

        var arrowX = Math.max(12, Math.min(tipW - 20, (r.left + r.width/2) - left - 5));

        tip.style.top  = top  + "px";
        tip.style.left = left + "px";
        tip.style.setProperty("--et-ax", arrowX + "px");
        tip.className  = arrowCls;
        requestAnimationFrame(function() { tip.classList.add("et-visible"); });
      });

    }, 80);
  }

  function doNext() {
    tip.classList.remove("et-visible");
    setTimeout(function() { current++; renderStep(current); }, 200);
  }

  function finish() {
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch {}
    tip.classList.remove("et-visible");
    setTimeout(function() {
      if (!overlay) return;
      overlay.style.transition = "opacity .3s ease";
      overlay.style.opacity    = "0";
      setTimeout(cleanup, 320);
    }, 120);
  }

  function buildDOM() {
    cleanup();

    styleEl = document.createElement("style");
    styleEl.textContent = CSS;
    document.head.appendChild(styleEl);

    var W = window.innerWidth, H = window.innerHeight;
    overlay = document.createElement("div");
    overlay.id = "et-overlay";
    overlay.innerHTML =
      '<svg id="et-svg" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">' +
        '<defs><mask id="et-mask">' +
          '<rect width="' + W + '" height="' + H + '" fill="white"/>' +
          '<rect id="et-cutout" x="0" y="0" width="0" height="0" rx="14" ry="14" fill="black"/>' +
        '</mask></defs>' +
        '<rect width="' + W + '" height="' + H + '" fill="rgba(0,0,0,0.72)" mask="url(#et-mask)"/>' +
      '</svg>' +
      '<div id="et-ring"></div>' +
      '<div id="et-tip"></div>';

    document.body.appendChild(overlay);
    ring   = document.getElementById("et-ring");
    tip    = document.getElementById("et-tip");
    cutout = document.getElementById("et-cutout");

    overlay.addEventListener("click", function(e) {
      if (!tip.contains(e.target)) doNext();
    });

    resizeHandler = function() { renderStep(current); };
    window.addEventListener("resize", resizeHandler);

    requestAnimationFrame(function() { overlay.classList.add("et-active"); });
  }

  function start() {
    var lang = getLang();
    steps   = STEPS[lang] || STEPS.ru;
    current = 0;
    buildDOM();
    switchTab("tools");
    setTimeout(function() { renderStep(0); }, 80);
  }

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

  window.eagleTourStart = function() {
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
    start();
  };

})();