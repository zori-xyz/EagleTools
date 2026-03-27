/* ============================================================
   EagleTools — Onboarding Tour v5
   - Steps 1-3: Tools tab cards
   - Step 4:    Recent tab — demo file appears, long-press → action sheet,
                then swipe-left → vanish animation
   - Step 5:    Profile tab
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

  /* ── Demo file HTML ──────────────────────────────────────── */
  var DEMO_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><rect x="2" y="2" width="20" height="20" rx="4"/><path d="M10 8l6 4-6 4V8z" fill="currentColor" stroke="none"/></svg>';

  function buildDemoRow(lang) {
    var label = lang === "en" ? "DONE" : "ГОТОВО";
    var name  = lang === "en" ? "EagleTools_demo.mp4" : "EagleTools_демо.mp4";
    var swipeSvg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>';
    var delLbl = lang === "en" ? "Delete" : "Удалить";
    return (
      '<div class="recentitem ri ri--video" id="et-demo-file" data-id="demo" style="overflow:hidden;">' +
        '<div class="ri-swipe-bg">' + swipeSvg + '<span>' + delLbl + '</span></div>' +
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
          '<div class="ri-actions">' +
            '<button class="ri-btn ri-btn--dl" type="button" disabled aria-label="Download">' +
              '<svg class="ri-btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><path d="M12 15V3m0 12-4-4m4 4 4-4M2 17l.621 2.485A2 2 0 004.561 21h14.878a2 2 0 001.94-1.515L22 17"/></svg>' +
            '</button>' +
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
    /* Prepend before existing items so it's always visible */
    list.insertBefore(_demoRow, list.firstChild);
  }

  function removeDemoFile() {
    if (_demoRow) { try { _demoRow.remove(); } catch {} _demoRow = null; }
    var old = document.getElementById("et-demo-file");
    if (old) old.remove();
  }

  /* ── Steps ───────────────────────────────────────────────── */
  var STEPS = {
    ru: [
      {
        tab: "tools", target: "#converterCard", badge: "NEW ✦",
        title: "🧠 SMART конвертер",
        text: "Брось любой файл — видео, аудио, фото, PDF или документ. Конвертер сам определит тип и предложит только нужные действия: конвертация, сжатие, распознавание речи.",
      },
      {
        tab: "tools", target: "[data-tool='save']",
        title: "⬇️ Скачать видео",
        text: "Вставь ссылку с YouTube, TikTok, Vimeo или любой другой платформы — получишь готовый MP4 без рекламы и ограничений.",
      },
      {
        tab: "tools", target: "[data-tool='audio']",
        title: "🎵 Музыка с SoundCloud",
        text: "Ссылка на трек или плейлист — и у тебя готовый MP3. Работает со всеми публичными треками SoundCloud.",
      },
      {
        tab: "recent", target: "#et-demo-file",
        title: "🗂 История загрузок",
        text: "Все твои файлы хранятся здесь 24 часа. Нажми <b>Далее</b> чтобы увидеть, как работает меню действий и свайп для удаления.",
        onEnter: function(lang) { injectDemoFile(lang || "ru"); },
        onLeave: function() { removeDemoFile(); },
        onNext: function(cb) { runDemoSequence("ru", cb); },
      },
      {
        tab: "profile", target: "[data-tab='profile']",
        title: "👤 Твой профиль",
        text: "Следи за дневным лимитом загрузок. Приглашай друзей по реферальной ссылке — за каждого получаешь +5 загрузок в день навсегда.",
      },
    ],
    en: [
      {
        tab: "tools", target: "#converterCard", badge: "NEW ✦",
        title: "🧠 SMART Converter",
        text: "Drop any file — video, audio, photo, PDF or document. The converter detects the type automatically and suggests only relevant actions: convert, compress, transcribe speech.",
      },
      {
        tab: "tools", target: "[data-tool='save']",
        title: "⬇️ Download video",
        text: "Paste a link from YouTube, TikTok, Vimeo or any other platform — get a clean MP4 file without ads or restrictions.",
      },
      {
        tab: "tools", target: "[data-tool='audio']",
        title: "🎵 Music from SoundCloud",
        text: "Drop a track or playlist link and get a ready MP3. Works with all public SoundCloud tracks.",
      },
      {
        tab: "recent", target: "#et-demo-file",
        title: "🗂 Download history",
        text: "All your files are stored here for 24 hours. Tap <b>Next</b> to see the action menu and swipe-to-delete in action.",
        onEnter: function(lang) { injectDemoFile(lang || "en"); },
        onLeave: function() { removeDemoFile(); },
        onNext: function(cb) { runDemoSequence("en", cb); },
      },
      {
        tab: "profile", target: "[data-tab='profile']",
        title: "👤 Your profile",
        text: "Track your daily download limit. Invite friends with your referral link — each one earns you +5 downloads per day, forever.",
      },
    ],
  };

  /* ── Demo animation sequence ─────────────────────────────── */
  function runDemoSequence(lang, doneCb) {
    var row = document.getElementById("et-demo-file");
    if (!row) { doneCb(); return; }

    /* 1. Long-press glow */
    setTimeout(function() {
      row.classList.add("is-pressing");

      /* 2. Open action sheet with demo item */
      setTimeout(function() {
        row.classList.remove("is-pressing");
        var demoItem = { id: "demo", title: "EagleTools_demo.mp4", download_url: "#", file_id: "demo.mp4" };
        if (typeof window.__eagleOpenActionSheet === "function") {
          window.__eagleOpenActionSheet(demoItem);
        }

        /* 3. Close action sheet after a moment */
        setTimeout(function() {
          if (typeof window.__eagleCloseActionSheet === "function") {
            window.__eagleCloseActionSheet();
          }

          /* 4. Swipe animation */
          setTimeout(function() {
            row = document.getElementById("et-demo-file");
            if (!row) { doneCb(); return; }
            row.classList.add("is-swiping");

            /* 5. Vanish */
            setTimeout(function() {
              row = document.getElementById("et-demo-file");
              if (row) row.classList.add("is-vanishing");

              /* 6. Proceed */
              setTimeout(function() {
                removeDemoFile();
                doneCb();
              }, 450);
            }, 420);
          }, 500);
        }, 1400);
      }, 600);
    }, 200);
  }

  /* ── CSS ─────────────────────────────────────────────────── */
  var CSS = [
    "#et-overlay{position:fixed;inset:0;z-index:9000;pointer-events:none;}",
    "#et-overlay.et-active{pointer-events:all;}",
    "#et-svg{position:fixed;inset:0;width:100%;height:100%;pointer-events:none;}",
    "#et-ring{",
    "  position:fixed;border:2px solid #e8195a;border-radius:14px;",
    "  box-shadow:0 0 0 3px rgba(232,25,90,.18),0 0 24px rgba(232,25,90,.25);",
    "  pointer-events:none;z-index:9100;",
    "  transition:top .32s cubic-bezier(.4,0,.2,1),left .32s cubic-bezier(.4,0,.2,1),",
    "             width .32s cubic-bezier(.4,0,.2,1),height .32s cubic-bezier(.4,0,.2,1);",
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

  function cleanup() {
    removeDemoFile();
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

    /* onEnter callback — e.g. inject demo row */
    if (typeof step.onEnter === "function") step.onEnter(lang);

    setTimeout(function() {
      /* If target doesn't exist yet (race with onEnter), poll briefly */
      var tries = 0;
      function tryFind() {
        var el = document.querySelector(step.target);
        if (!el && tries++ < 6) { setTimeout(tryFind, 60); return; }
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
            /* Custom "Next" — run demo sequence, then advance */
            nextBtn.onclick = function() {
              nextBtn.disabled = true;
              tip.querySelector(".et-skip").style.pointerEvents = "none";
              step.onNext(function() {
                tip.classList.remove("et-visible");
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
    /* Clean up demo if present */
    var step = steps[current];
    if (step && typeof step.onLeave === "function") step.onLeave();
    tip.classList.remove("et-visible");
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
      '<div id="et-tip"></div>';

    document.body.appendChild(overlay);
    ring   = document.getElementById("et-ring");
    tip    = document.getElementById("et-tip");
    cutout = document.getElementById("et-cutout");

    overlay.addEventListener("click", function(e) {
      if (!tip.contains(e.target)) doNext();
    });

    resizeHandler = function() {
      var step = steps[current];
      if (!step) return;
      var el = document.querySelector(step.target);
      if (!el) return;
      var er = el.getBoundingClientRect();
      var PAD = 6;
      var r = { top: er.top - PAD, left: er.left - PAD, width: er.width + PAD * 2, height: er.height + PAD * 2 };
      applyRect(r);
      positionTip(r);
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
