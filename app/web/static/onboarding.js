/* ============================================================
   EagleTools — Onboarding Tour v6
   Step 4: demo row → long-press glow → FAKE action sheet slides up
           (spotlight follows) → auto-dismiss → swipe-left → vanish
   ============================================================ */
(function () {
  "use strict";

  var STORAGE_KEY = "et_onboarded_v1";
  var PROFILE_KEY = "eagle_profile_settings";

  function getLang() {
    try { var l = document.documentElement.lang; if (l === "en") return "en"; if (l === "ru") return "ru"; } catch {}
    try { var r = localStorage.getItem(PROFILE_KEY); if (r) { var o = JSON.parse(r); if (o && o.lang === "en") return "en"; } } catch {}
    return "ru";
  }

  /* ── Demo row ────────────────────────────────────────────── */
  var DEMO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><rect x="2" y="2" width="20" height="20" rx="4"/><path d="M10 8l6 4-6 4V8z" fill="currentColor" stroke="none"/></svg>';

  function buildDemoRow(lang) {
    var name  = lang === "en" ? "EagleTools_demo.mp4" : "EagleTools_демо.mp4";
    var label = lang === "en" ? "DONE" : "ГОТОВО";
    var delLbl = lang === "en" ? "Delete" : "Удалить";
    var trashSvg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>';
    return (
      '<div class="recentitem ri ri--video" id="et-demo-file" data-id="demo" style="overflow:hidden;">' +
        '<div class="ri-swipe-bg">' + trashSvg + '<span>' + delLbl + '</span></div>' +
        '<div class="ri-inner">' +
          '<div class="ri-icon">' + DEMO_ICON + '</div>' +
          '<div class="ri-info">' +
            '<div class="ri-name">' + name + '</div>' +
            '<div class="ri-meta">' +
              '<span class="ri-badge ri-badge--done">' + label + '</span>' +
              '<span class="ri-size">14.2 MB</span>' +
              '<span class="ri-when">1 ' + (lang === "en" ? "min ago" : "мин назад") + '</span>' +
            '</div>' +
          '</div>' +
          '<div class="ri-actions__hint">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" width="14" height="14" style="opacity:.3"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  var _demoRow = null;

  function injectDemoFile(lang) {
    removeDemoFile();
    var list = document.getElementById("recentList");
    if (!list) return;
    var tmp = document.createElement("div");
    tmp.innerHTML = buildDemoRow(lang);
    _demoRow = tmp.firstElementChild;
    list.insertBefore(_demoRow, list.firstChild);
  }

  function removeDemoFile() {
    if (_demoRow) { try { _demoRow.remove(); } catch {} _demoRow = null; }
    var old = document.getElementById("et-demo-file");
    if (old) old.remove();
  }

  /* ── Fake action sheet ───────────────────────────────────── */
  function buildFakeSheet(lang) {
    var isEn = lang === "en";
    var items = [
      { icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><path d="M14.5 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V9.5L14.5 3z"/><polyline points="14 3 14 9 20 9"/></svg>', label: isEn ? "Open" : "Открыть" },
      { icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><path d="M12 15V3m0 12-4-4m4 4 4-4M2 17l.621 2.485A2 2 0 004.561 21h14.878a2 2 0 001.94-1.515L22 17"/></svg>', label: isEn ? "Download" : "Скачать" },
      { icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>', label: isEn ? "Share" : "Поделиться" },
      { icon: '<svg viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>', label: isEn ? "Delete" : "Удалить", danger: true },
    ];

    var rowsHtml = items.map(function(it) {
      return (
        '<div class="et-fs-item' + (it.danger ? ' et-fs-danger' : '') + '">' +
          '<div class="et-fs-icon">' + it.icon + '</div>' +
          '<span class="et-fs-label">' + it.label + '</span>' +
        '</div>'
      );
    }).join('');

    var el = document.createElement("div");
    el.id = "et-fake-sheet";
    el.innerHTML =
      '<div class="et-fs-handle"></div>' +
      '<div class="et-fs-title">EagleTools_демо.mp4</div>' +
      rowsHtml;
    return el;
  }

  function showFakeSheet(lang, cb) {
    var old = document.getElementById("et-fake-sheet");
    if (old) old.remove();
    var el = buildFakeSheet(lang);
    document.body.appendChild(el);
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        el.classList.add("is-open");
        setTimeout(function() { cb(el); }, 360);
      });
    });
  }

  function hideFakeSheet(el, cb) {
    if (!el || !el.parentNode) { if (cb) cb(); return; }
    el.classList.remove("is-open");
    setTimeout(function() {
      el.remove();
      if (cb) cb();
    }, 360);
  }

  /* ── Demo sequence ───────────────────────────────────────── */
  function runDemoSequence(lang, doneCb) {
    var row = document.getElementById("et-demo-file");
    if (!row) { doneCb(); return; }

    /* 1. Fade out tip, let overlay stay */
    tip.classList.remove("et-visible");

    /* 2. Move spotlight to demo row */
    function spotRow() {
      var er = row.getBoundingClientRect();
      if (!er.width) return;
      var PAD = 8;
      applyRect({ top: er.top - PAD, left: er.left - PAD, width: er.width + PAD * 2, height: er.height + PAD * 2 });
    }

    var isEn = lang === "en";

    /* ─── timing constants (ms) ─────────────────────────── */
    var T_BEFORE_HINT   = 300;   /* settle before first hint       */
    var T_HINT_READ     = 1200;  /* user reads "Зажми и держи…"    */
    var T_GLOW          = 1000;  /* long-press glow duration        */
    var T_SHEET_ANIMATE = 420;   /* fake sheet slide-in             */
    var T_SHEET_RECT    = 100;   /* extra wait for getBCR to settle */
    var T_SHEET_READ    = 3500;  /* user reads action sheet options */
    var T_SWIPE_HINT    = 1200;  /* user reads swipe hint           */
    var T_SWIPE_ANIM    = 700;   /* translateX animation            */
    var T_VANISH        = 600;   /* collapse animation              */

    setTimeout(function() {
      spotRow();

      /* ── Phase 1: long-press hint + glow ── */
      showHint(isEn ? "Hold to open actions…" : "Зажми для меню действий…");

      setTimeout(function() {
        row.classList.add("is-pressing");

        setTimeout(function() {
          row.classList.remove("is-pressing");
          hideHint();

          /* ── Phase 2: fake sheet slides up ── */
          showFakeSheet(lang, function(sheetEl) {
            /* spotlight moves to cover the sheet */
            setTimeout(function() {
              var sr = sheetEl.getBoundingClientRect();
              applyRect({ top: Math.max(4, sr.top - 12), left: 0,
                          width: window.innerWidth, height: sr.height + 20 });
              showHint(isEn ? "Tap any action from the menu" : "Любое действие из меню");
            }, T_SHEET_RECT);

            /* ── Phase 3: dismiss sheet ── */
            setTimeout(function() {
              hideHint();
              hideFakeSheet(sheetEl, function() {

                /* spotlight back on row */
                spotRow();

                /* ── Phase 4: swipe-to-delete ── */
                showHint(isEn ? "← Swipe left to delete" : "← Потяни влево — удалить");

                setTimeout(function() {
                  row.classList.add("is-swiping");

                  setTimeout(function() {
                    hideHint();
                    row.classList.add("is-vanishing");

                    setTimeout(function() {
                      removeDemoFile();
                      doneCb();
                    }, T_VANISH);
                  }, T_SWIPE_ANIM);
                }, T_SWIPE_HINT);
              });
            }, T_SHEET_READ);
          });
        }, T_GLOW);
      }, T_HINT_READ);
    }, T_BEFORE_HINT);
  }

  /* ── Steps ───────────────────────────────────────────────── */
  var STEPS = {
    ru: [
      {
        tab: "tools", target: "#converterCard", badge: "NEW ✦",
        title: "🧠 SMART конвертер",
        text: "Брось любой файл — видео, аудио, фото, PDF или документ. Конвертер сам определит тип и предложит только нужные действия.",
      },
      {
        tab: "tools", target: "[data-tool='save']",
        title: "⬇️ Скачать видео",
        text: "Вставь ссылку с YouTube, TikTok, Vimeo или любой другой платформы — получишь готовый MP4 без рекламы.",
      },
      {
        tab: "tools", target: "[data-tool='audio']",
        title: "🎵 Музыка с SoundCloud",
        text: "Ссылка на трек или плейлист — и у тебя готовый MP3. Работает со всеми публичными треками.",
      },
      {
        tab: "recent", target: "#et-demo-file",
        title: "🗂 История загрузок",
        text: "Файлы хранятся 24 часа. Нажми <b>Далее</b> — покажу как работает меню и свайп-удаление.",
        onEnter: function(lang) { injectDemoFile(lang); },
        onLeave: function() { removeDemoFile(); },
        onNext: function(cb) { runDemoSequence(getLang(), cb); },
      },
      {
        tab: "profile", target: "[data-tab='profile']",
        title: "👤 Твой профиль",
        text: "Следи за дневным лимитом. Приглашай друзей по реферальной ссылке — за каждого +5 загрузок в день навсегда.",
      },
    ],
    en: [
      {
        tab: "tools", target: "#converterCard", badge: "NEW ✦",
        title: "🧠 SMART Converter",
        text: "Drop any file — video, audio, photo, PDF or document. The converter detects the type and suggests the right actions automatically.",
      },
      {
        tab: "tools", target: "[data-tool='save']",
        title: "⬇️ Download video",
        text: "Paste a link from YouTube, TikTok, Vimeo or any platform — get a clean MP4 without ads.",
      },
      {
        tab: "tools", target: "[data-tool='audio']",
        title: "🎵 Music from SoundCloud",
        text: "Drop a track or playlist link and get a ready MP3. Works with all public SoundCloud tracks.",
      },
      {
        tab: "recent", target: "#et-demo-file",
        title: "🗂 Download history",
        text: "Files are stored for 24 hours. Tap <b>Next</b> — I'll show how the action menu and swipe-to-delete work.",
        onEnter: function(lang) { injectDemoFile(lang); },
        onLeave: function() { removeDemoFile(); },
        onNext: function(cb) { runDemoSequence(getLang(), cb); },
      },
      {
        tab: "profile", target: "[data-tab='profile']",
        title: "👤 Your profile",
        text: "Track your daily limit. Invite friends via referral link — each one gives you +5 downloads per day forever.",
      },
    ],
  };

  /* ── CSS ─────────────────────────────────────────────────── */
  var CSS = [
    "#et-overlay{position:fixed;inset:0;z-index:9000;pointer-events:none;}",
    "#et-overlay.et-active{pointer-events:all;}",
    "#et-svg{position:fixed;inset:0;width:100%;height:100%;pointer-events:none;}",
    "#et-ring{",
    "  position:fixed;border:2px solid #e8195a;border-radius:14px;",
    "  box-shadow:0 0 0 3px rgba(232,25,90,.18),0 0 24px rgba(232,25,90,.25);",
    "  pointer-events:none;z-index:9100;",
    "  transition:top .38s cubic-bezier(.4,0,.2,1),left .38s cubic-bezier(.4,0,.2,1),",
    "             width .38s cubic-bezier(.4,0,.2,1),height .38s cubic-bezier(.4,0,.2,1);",
    "}",
    "#et-tip{",
    "  position:fixed;z-index:9200;width:min(292px,calc(100vw - 24px));",
    "  background:var(--bg3,#16131f);border:1px solid rgba(232,25,90,.25);",
    "  border-radius:18px;padding:18px 18px 14px;",
    "  box-shadow:0 18px 50px rgba(0,0,0,.6);",
    "  opacity:0;transform:translateY(8px);",
    "  transition:opacity .22s ease,transform .22s ease;",
    "  pointer-events:all;",
    "}",
    "#et-tip.et-visible{opacity:1;transform:translateY(0);}",
    "#et-tip::before{content:'';position:absolute;width:10px;height:10px;background:var(--bg3,#16131f);border-left:1px solid rgba(232,25,90,.25);border-top:1px solid rgba(232,25,90,.25);border-radius:2px 0 0 0;left:var(--et-ax,22px);}",
    "#et-tip.et-arrow-top::before{top:-6px;transform:rotate(45deg);}",
    "#et-tip.et-arrow-bottom::before{bottom:-6px;transform:rotate(225deg);}",
    ".et-badge{display:inline-block;font-size:9px;font-weight:700;letter-spacing:.8px;padding:2px 8px;border-radius:999px;margin-bottom:6px;background:linear-gradient(135deg,rgba(232,25,90,.18),rgba(124,58,237,.18));border:1px solid rgba(232,25,90,.28);color:#e8195a;}",
    ".et-step{font-size:10px;font-weight:600;color:#e8195a;letter-spacing:.8px;text-transform:uppercase;margin-bottom:5px;}",
    ".et-title{font-size:15px;font-weight:600;color:var(--text,rgba(255,255,255,.92));margin-bottom:5px;line-height:1.3;}",
    ".et-text{font-size:13px;color:var(--text2,rgba(255,255,255,.50));line-height:1.55;margin-bottom:14px;}",
    ".et-text b{color:var(--text,rgba(255,255,255,.78));}",
    ".et-footer{display:flex;align-items:center;justify-content:space-between;}",
    ".et-dots{display:flex;gap:5px;align-items:center;}",
    ".et-dot{width:5px;height:5px;border-radius:50%;background:rgba(255,255,255,.15);transition:all .25s ease;}",
    ".et-dot.et-on{background:#e8195a;width:14px;border-radius:3px;}",
    ".et-btns{display:flex;gap:8px;align-items:center;}",
    ".et-skip{font-size:12px;color:var(--text3,rgba(255,255,255,.28));background:none;border:none;padding:6px 2px;cursor:pointer;font-family:var(--font,'DM Sans',sans-serif);transition:color .2s;}",
    ".et-skip:hover{color:var(--text2,rgba(255,255,255,.50));}",
    ".et-next{font-size:13px;font-weight:500;color:#fff;background:#e8195a;border:none;border-radius:10px;padding:7px 16px;cursor:pointer;font-family:var(--font,'DM Sans',sans-serif);transition:background .18s,transform .1s;}",
    ".et-next:hover{background:#ff2d6b;}",
    ".et-next:active{transform:scale(0.96);}",
    ".et-next:disabled{opacity:.45;pointer-events:none;}",
    "html[data-theme='light'] #et-tip{background:#fff;border-color:rgba(208,20,83,.18);box-shadow:0 12px 40px rgba(80,40,140,.13);}",
    "html[data-theme='light'] #et-tip::before{background:#fff;border-color:rgba(208,20,83,.18);}",
    "html[data-theme='light'] .et-dot{background:rgba(0,0,0,.12);}",
    /* ── Fake action sheet ── */
    "#et-fake-sheet{",
    "  position:fixed;left:0;right:0;bottom:0;z-index:9150;",
    "  background:var(--bg2,#1e1b2e);border-radius:20px 20px 0 0;",
    "  padding:0 0 max(16px,env(safe-area-inset-bottom));",
    "  transform:translateY(100%);",
    "  transition:transform .36s cubic-bezier(.32,1,.6,1);",
    "  box-shadow:0 -8px 48px rgba(0,0,0,.55);",
    "  pointer-events:none;",
    "}",
    "#et-fake-sheet.is-open{transform:translateY(0);pointer-events:all;}",
    "html[data-theme='light'] #et-fake-sheet{background:#f2f2f7;}",
    ".et-fs-handle{width:36px;height:4px;background:rgba(128,128,128,.25);border-radius:2px;margin:10px auto 6px;}",
    ".et-fs-title{font-size:13px;color:var(--text3,rgba(255,255,255,.35));text-align:center;padding:4px 20px 12px;",
    "  border-bottom:1px solid rgba(255,255,255,.06);margin-bottom:4px;",
    "  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}",
    "html[data-theme='light'] .et-fs-title{color:rgba(0,0,0,.35);border-color:rgba(0,0,0,.06);}",
    ".et-fs-item{display:flex;align-items:center;gap:14px;padding:13px 20px;",
    "  font-size:15px;font-weight:400;color:var(--text,rgba(255,255,255,.88));}",
    "html[data-theme='light'] .et-fs-item{color:rgba(0,0,0,.85);}",
    ".et-fs-danger{color:#ef4444 !important;}",
    ".et-fs-icon{width:36px;height:36px;border-radius:10px;background:rgba(255,255,255,.07);",
    "  display:flex;align-items:center;justify-content:center;flex-shrink:0;}",
    "html[data-theme='light'] .et-fs-icon{background:rgba(0,0,0,.06);}",
    ".et-fs-danger .et-fs-icon{background:rgba(239,68,68,.12);}",
    ".et-fs-label{font-family:var(--font,'DM Sans',sans-serif);}",
    /* ── Hint label (shown during demo) ── */
    "#et-hint{",
    "  position:fixed;left:50%;top:72px;",
    "  transform:translateX(-50%) translateY(-10px);",
    "  z-index:9210;",
    "  background:rgba(232,25,90,.95);color:#fff;",
    "  font-size:14px;font-weight:600;font-family:var(--font,'DM Sans',sans-serif);",
    "  padding:9px 22px;border-radius:20px;",
    "  white-space:nowrap;pointer-events:none;",
    "  box-shadow:0 4px 20px rgba(232,25,90,.4);",
    "  opacity:0;transition:opacity .3s ease,transform .3s ease;",
    "}",
    "#et-hint.et-hint--visible{opacity:1;transform:translateX(-50%) translateY(0);}",
  ].join("\n");

  var current = 0, steps = [], overlay, ring, tip, cutout, styleEl, resizeHandler, rafId;

  function lockScroll() {
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";
  }
  function unlockScroll() {
    document.body.style.overflow = "";
    document.documentElement.style.overflow = "";
  }

  /* ── Hint label ──────────────────────────────────────────── */
  function showHint(text) {
    var h = document.getElementById("et-hint");
    if (!h) return;
    h.textContent = text;
    h.classList.add("et-hint--visible");
  }
  function hideHint() {
    var h = document.getElementById("et-hint");
    if (h) h.classList.remove("et-hint--visible");
  }

  function cleanup() {
    document.body.classList.remove("et-onboarding");
    removeDemoFile();
    hideHint();
    var fs = document.getElementById("et-fake-sheet");
    if (fs) fs.remove();
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    if (resizeHandler) { window.removeEventListener("resize", resizeHandler); resizeHandler = null; }
    if (overlay) { overlay.remove(); overlay = null; }
    if (styleEl) { styleEl.remove(); styleEl = null; }
    ring = tip = cutout = null;
    unlockScroll();
  }

  function switchTab(tabName) {
    var btn = document.querySelector('[data-tab="' + tabName + '"]');
    if (btn) btn.click();
  }

  function scrollToEl(el, cb) {
    var rect = el.getBoundingClientRect();
    var vh   = window.innerHeight;
    var pad  = 80;

    if (rect.top >= pad && rect.bottom <= vh - pad) { cb(); return; }

    el.scrollIntoView({ behavior: "smooth", block: "center" });

    var prevTop = null, stableCount = 0;
    function poll() {
      var top = el.getBoundingClientRect().top;
      if (top === prevTop) {
        stableCount++;
        if (stableCount >= 3) { cb(); return; }
      } else {
        stableCount = 0;
        prevTop = top;
      }
      rafId = requestAnimationFrame(poll);
    }
    rafId = requestAnimationFrame(poll);
  }

  function applyRect(r) {
    if (!cutout || !ring) return;
    cutout.setAttribute("x", r.left);
    cutout.setAttribute("y", r.top);
    cutout.setAttribute("width", r.width);
    cutout.setAttribute("height", r.height);

    var W = window.innerWidth, H = window.innerHeight;
    var svg = document.getElementById("et-svg");
    if (svg) {
      svg.setAttribute("viewBox", "0 0 " + W + " " + H);
      svg.querySelectorAll("rect:not(#et-cutout)").forEach(function(rc) {
        rc.setAttribute("width", W); rc.setAttribute("height", H);
      });
    }

    ring.style.top    = r.top    + "px";
    ring.style.left   = r.left   + "px";
    ring.style.width  = r.width  + "px";
    ring.style.height = r.height + "px";
  }

  function positionTip(r) {
    var tipW = tip.offsetWidth  || 292;
    var tipH = tip.offsetHeight || 170;
    var vw   = window.innerWidth;
    var vh   = window.innerHeight;
    var M = 12, ARROW = 14;

    var belowTop = r.top + r.height + ARROW;
    var aboveTop = r.top - tipH - ARROW;
    var top, arrowCls;

    if (belowTop + tipH < vh - M)  { top = belowTop; arrowCls = "et-arrow-top"; }
    else if (aboveTop > M)          { top = aboveTop; arrowCls = "et-arrow-bottom"; }
    else                            { top = Math.max(M, vh - tipH - M); arrowCls = "et-arrow-top"; }

    var left = r.left;
    if (left + tipW > vw - M) left = vw - tipW - M;
    if (left < M) left = M;

    var ax = Math.max(12, Math.min(tipW - 22, (r.left + r.width / 2) - left - 5));

    tip.style.top  = top  + "px";
    tip.style.left = left + "px";
    tip.style.setProperty("--et-ax", ax + "px");
    tip.className  = arrowCls;
  }

  function renderStep(idx) {
    var step = steps[idx];
    if (!step) return;
    var lang = getLang();

    tip.classList.remove("et-visible");
    switchTab(step.tab);

    /* onEnter: delay to let loadRecents() re-render before injecting demo */
    var hasEnter = typeof step.onEnter === "function";
    if (hasEnter) setTimeout(function() { step.onEnter(lang); }, 700);

    var pollMax = hasEnter ? 25 : 6;
    var pollMs  = hasEnter ? 120 : 60;
    var tries = 0;

    setTimeout(function() {
      function tryFind() {
        var el = document.querySelector(step.target);
        if (!el && tries++ < pollMax) { setTimeout(tryFind, pollMs); return; }
        if (!el) { doNext(); return; }

        scrollToEl(el, function() {
          var er  = el.getBoundingClientRect();
          var PAD = 6;
          var r   = { top: er.top - PAD, left: er.left - PAD, width: er.width + PAD * 2, height: er.height + PAD * 2 };

          applyRect(r);

          var isLast = idx === steps.length - 1;
          var dots   = steps.map(function(_, i) {
            return '<span class="et-dot' + (i === idx ? " et-on" : "") + '"></span>';
          }).join("");

          var skipLbl = lang === "en" ? "Skip" : "Пропустить";
          var nextLbl = isLast ? (lang === "en" ? "Let\u2019s go!" : "Поехали!") : (lang === "en" ? "Next" : "Далее");
          var stepLbl = lang === "en" ? "Step" : "Шаг";
          var badgeHtml = step.badge ? '<div class="et-badge">' + step.badge + '</div>' : "";

          tip.innerHTML =
            '<div class="et-step">' + stepLbl + " " + (idx + 1) + " / " + steps.length + "</div>" +
            badgeHtml +
            '<div class="et-title">' + step.title + "</div>" +
            '<div class="et-text">'  + step.text  + "</div>" +
            '<div class="et-footer">' +
              '<div class="et-dots">' + dots + "</div>" +
              '<div class="et-btns">' +
                '<button class="et-skip">' + skipLbl + "</button>" +
                '<button class="et-next">' + nextLbl + "</button>" +
              "</div>" +
            "</div>";

          tip.querySelector(".et-skip").onclick = finish;

          var nextBtn = tip.querySelector(".et-next");
          if (isLast) {
            nextBtn.onclick = finish;
          } else if (typeof step.onNext === "function") {
            nextBtn.onclick = function() {
              nextBtn.disabled = true;
              tip.querySelector(".et-skip").style.opacity = "0";
              tip.querySelector(".et-skip").style.pointerEvents = "none";
              step.onNext(function() {
                /* After demo: slide tip out, advance */
                setTimeout(function() { current++; renderStep(current); }, 180);
              });
            };
          } else {
            nextBtn.onclick = doNext;
          }

          requestAnimationFrame(function() {
            positionTip(r);
            requestAnimationFrame(function() { tip.classList.add("et-visible"); });
          });
        });
      }
      tryFind();
    }, 80);
  }

  function doNext() {
    var step = steps[current];
    if (step && typeof step.onLeave === "function") step.onLeave();
    tip.classList.remove("et-visible");
    setTimeout(function() { current++; renderStep(current); }, 180);
  }

  function finish() {
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch {}
    var step = steps[current];
    if (step && typeof step.onLeave === "function") step.onLeave();
    tip.classList.remove("et-visible");
    var fs = document.getElementById("et-fake-sheet");
    if (fs) fs.remove();
    setTimeout(function() {
      if (!overlay) return;
      overlay.style.transition = "opacity .28s ease";
      overlay.style.opacity = "0";
      setTimeout(cleanup, 300);
    }, 100);
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
      '<svg id="et-svg" viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">' +
        '<defs><mask id="et-mask">' +
          '<rect width="' + W + '" height="' + H + '" fill="white"/>' +
          '<rect id="et-cutout" x="0" y="0" width="0" height="0" rx="14" ry="14" fill="black"/>' +
        "</mask></defs>" +
        '<rect width="' + W + '" height="' + H + '" fill="rgba(0,0,0,0.72)" mask="url(#et-mask)"/>' +
      "</svg>" +
      '<div id="et-ring"></div>' +
      '<div id="et-hint"></div>' +
      '<div id="et-tip"></div>';

    document.body.appendChild(overlay);
    document.body.classList.add("et-onboarding");
    ring   = document.getElementById("et-ring");
    tip    = document.getElementById("et-tip");
    cutout = document.getElementById("et-cutout");

    /* Tap outside tooltip → next step (skip during demo) */
    overlay.addEventListener("click", function(e) {
      if (tip.contains(e.target)) return;
      var fs = document.getElementById("et-fake-sheet");
      if (fs && fs.contains(e.target)) return;
      if (steps[current] && typeof steps[current].onNext === "function") return; /* demo step — ignore taps */
      doNext();
    });

    resizeHandler = function() {
      var step = steps[current];
      if (!step) return;
      var el = document.querySelector(step.target);
      if (!el) return;
      var er = el.getBoundingClientRect();
      var PAD = 6;
      applyRect({ top: er.top - PAD, left: er.left - PAD, width: er.width + PAD * 2, height: er.height + PAD * 2 });
      positionTip({ top: er.top - PAD, left: er.left - PAD, width: er.width + PAD * 2, height: er.height + PAD * 2 });
    };
    window.addEventListener("resize", resizeHandler);

    lockScroll();
    requestAnimationFrame(function() { overlay.classList.add("et-active"); });
  }

  function start() {
    var lang = getLang();
    steps   = STEPS[lang] || STEPS.ru;
    current = 0;
    buildDOM();
    window.scrollTo({ top: 0, behavior: "instant" });
    switchTab("tools");
    setTimeout(function() { renderStep(0); }, 100);
  }

  function tryStart() {
    try { if (localStorage.getItem(STORAGE_KEY)) return; } catch {}
    setTimeout(start, window.__EAGLE_APP_READY__ ? 500 : 1200);
  }

  if (document.readyState === "complete") { tryStart(); }
  else { window.addEventListener("load", tryStart, { once: true }); }

  window.eagleTourStart = function() {
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
    start();
  };

})();
