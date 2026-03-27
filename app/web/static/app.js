// app/web/static/app.js
(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function escapeHtml(s) {
    return String(s ?? "")
      .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  }

  const t = (k) => window.EagleProfile?.t?.(k) || "";

  // ---------- Toast ----------
  let toastEl = null, toastTimer = null;
  function ensureToast() {
    if (toastEl) return toastEl;
    toastEl = document.createElement("div");
    toastEl.className = "toast";
    toastEl.innerHTML = `<div class="toast__inner"><div class="toast__icon" id="toastIcon">ℹ️</div><div class="toast__msg" id="toastMsg"></div></div>`;
    document.body.appendChild(toastEl);
    return toastEl;
  }
  function toast(msg, kind = "ok", icon = "ℹ️") {
    const el = ensureToast();
    const m = $("#toastMsg", el), ic = $("#toastIcon", el);
    if (m) m.textContent = String(msg ?? "");
    if (ic) ic.textContent = icon;
    el.dataset.kind = kind || "ok";
    el.classList.add("is-on");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("is-on"), 2400);
  }

  // ---------- API ----------
  async function apiGet(path) {
    try {
      const r = await window.EagleAPI?.getJson?.(path);
      if (r && typeof r === "object" && "ok" in r && "data" in r) return r;
      return { ok: true, data: r };
    } catch (e) { return { ok: false, error: String(e?.message || e) }; }
  }
  async function apiPost(path, body) {
    try {
      const r = await window.EagleAPI?.postJson?.(path, body);
      if (r && typeof r === "object" && "ok" in r && "data" in r) return r;
      return { ok: true, data: r };
    } catch (e) { return { ok: false, error: String(e?.message || e) }; }
  }
  async function apiDelete(path) {
    try {
      const r = await window.EagleAPI?.delJson?.(path);
      if (r && typeof r === "object" && "ok" in r && "data" in r) return r;
      return { ok: true, data: r };
    } catch (e) { return { ok: false, error: String(e?.message || e) }; }
  }
  const ERROR_MAP = {
    "save_failed": () => t("err_save_failed") || "Не удалось загрузить файл",
    "soundcloud_failed": () => t("err_soundcloud") || "Ошибка SoundCloud",
    "daily_limit_reached": () => t("limit_reached") || "Дневной лимит исчерпан",
    "ip_blocked": () => t("err_ip_blocked") || "Платформа заблокировала сервер",
    "yt_dlp_timeout": () => t("err_timeout") || "Превышено время ожидания",
    "bad_url": () => t("err_bad_url") || "Неверная ссылка",
    "unknown_tool": () => t("err_unknown_tool") || "Неизвестный инструмент",
    "missing_init_data": () => t("err_auth") || "Ошибка авторизации",
    "not_media_url": () => t("err_not_media") || "Ссылка не ведёт на медиафайл",
    "too_large": () => t("err_too_large") || "Файл слишком большой",
    "empty_download": () => t("err_empty") || "Пустой файл",
  };

  function prettyErr(r) {
    if (!r) return t("err_unknown") || "Неизвестная ошибка";
    const raw = r.error ? String(r.error) : (r.data && typeof r.data === "object") ? (r.data.detail || r.data.message || "") : "";
    // Check known error codes
    for (const [code, fn] of Object.entries(ERROR_MAP)) {
      if (raw.startsWith(code) || raw.includes(code)) return fn();
    }
    if (raw) return raw;
    return t("err_unknown") || "Неизвестная ошибка";
  }

  // ---------- Haptic Feedback ----------
  function haptic(type = "light") {
    try { window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.(type); } catch {}
  }
  function hapticNotify(type = "success") {
    try { window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred?.(type); } catch {}
  }

  // ---------- Paste button handler ----------
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-role='paste']");
    if (!btn) return;
    const wrap = btn.closest(".toolcard__input-wrap");
    if (!wrap) return;
    const inp = wrap.querySelector("[data-role='url']");
    if (!inp) return;
    haptic("light");
    try {
      const text = await navigator.clipboard.readText();
      if (text && (text.startsWith("http://") || text.startsWith("https://"))) {
        inp.value = text.trim();
        inp.dispatchEvent(new Event("input", { bubbles: true }));
        hapticNotify("success");
      } else {
        toast(t("err_bad_url") || "Неверная ссылка", "err", "⚠️");
        hapticNotify("error");
      }
    } catch {
      toast(t("copy_failed") || "Ошибка копирования", "err", "⚠️");
    }
  });

  // ---------- Drag-and-drop glow on converter drop zone ----------
  (() => {
    const drop = document.getElementById("convDrop");
    if (!drop) return;
    let dragCount = 0;
    document.addEventListener("dragenter", () => { dragCount++; drop.classList.add("is-dragover"); });
    document.addEventListener("dragleave", () => { dragCount = Math.max(0, dragCount - 1); if (dragCount === 0) drop.classList.remove("is-dragover"); });
    document.addEventListener("drop", () => { dragCount = 0; drop.classList.remove("is-dragover"); });
  })();

  // ---------- Open / Share ----------
  function openFile(url) {
    if (!url) return;
    const full = url.startsWith("http") ? url : window.location.origin + url;
    try { if (window.Telegram?.WebApp?.openLink) { window.Telegram.WebApp.openLink(full); return; } } catch {}
    try { window.open(full, "_blank", "noopener"); } catch {}
  }
  async function shareFile(url, title = "") {
    if (!url) return;
    const full = url.startsWith("http") ? url : window.location.origin + url;
    try { if (navigator.share) { await navigator.share({ title: title || "EagleTools", url: full }); return; } } catch {}
    try { await navigator.clipboard.writeText(full); toast(t("link_copied") || "Ссылка скопирована", "ok", "📋"); } catch { openFile(url); }
  }

  // ---------- Media Player ----------
  let playerUrl = "", playerTitle = "", playerIsAudio = false;
  function fmtTime(sec) {
    if (!isFinite(sec)) return "0:00";
    const m = Math.floor(sec / 60), s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  }

  function updateSeekFill(el, pct) {
    const p = Math.max(0, Math.min(100, Number(pct) || 0));
    el.style.background = `linear-gradient(to right, #e8195a 0%, #e8195a ${p}%, rgba(255,255,255,.10) ${p}%, rgba(255,255,255,.10) 100%)`;
  }

  function openPlayer(url, title, isAudio, isImage) {
    playerUrl = url; playerTitle = title || ""; playerIsAudio = isAudio;
    const modal = $("#playerModal");
    const video = $("#playerVideo"), audio = $("#playerAudio");
    const videoWrap = $("#playerVideoWrap"), audioWrap = $("#playerAudioWrap");
    const controls = $("#playerControls");
    const titleEl = $("#playerAudioTitle");
    const fullUrl = url.startsWith("http") ? url : window.location.origin + url;

    // stop previous
    if (video) { video.pause(); video.src = ""; }
    if (audio) { audio.pause(); audio.src = ""; }

    // Убираем старый image viewer если есть
    const oldImg = document.getElementById("playerImageWrap");
    if (oldImg) oldImg.remove();

    if (isImage) {
      /* GIF и другие изображения — показываем как картинку */
      audioWrap && (audioWrap.style.display = "none");
      videoWrap && (videoWrap.style.display = "none");
      controls && (controls.style.display = "none");

      const imgWrap = document.createElement("div");
      imgWrap.id = "playerImageWrap";
      imgWrap.style.cssText = "text-align:center;padding:8px 0;";
      const img = document.createElement("img");
      img.src = fullUrl;
      img.style.cssText = "max-width:100%;max-height:60vh;border-radius:12px;object-fit:contain;display:block;margin:0 auto;";
      img.alt = title || "";
      imgWrap.appendChild(img);
      const body = document.querySelector(".player-modal__body");
      if (body) body.insertBefore(imgWrap, body.firstChild);

    } else if (isAudio) {
      videoWrap && (videoWrap.style.display = "none");
      audioWrap && (audioWrap.style.display = "");
      controls && (controls.style.display = "");
      if (titleEl) titleEl.textContent = title || (window.__tLang === "en" ? "Audio" : "Аудио");
      if (audio) {
        audio.src = fullUrl;
        audio.load();
        bindAudioControls(audio);
      }
    } else {
      audioWrap && (audioWrap.style.display = "none");
      videoWrap && (videoWrap.style.display = "");
      controls && (controls.style.display = "none");
      if (video) {
        video.src = fullUrl;
        video.load();
      }
    }

    const openBtn = $("#playerOpen"), shareBtn = $("#playerShare");
    const openLabel = $("#playerOpenLabel"), shareLabel = $("#playerShareLabel");
    if (openLabel) openLabel.textContent = t("player_open") || "Открыть";
    if (shareLabel) shareLabel.textContent = t("player_share") || "Поделиться";
    if (openBtn) openBtn.onclick = () => openFile(playerUrl);
    if (shareBtn) shareBtn.onclick = () => shareFile(playerUrl, playerTitle);

    modal && modal.classList.add("is-open");
  }

  function closePlayer() {
    const modal = $("#playerModal");
    const video = $("#playerVideo"), audio = $("#playerAudio");
    if (video) { video.pause(); video.src = ""; }
    if (audio) { audio.pause(); audio.src = ""; }
    const imgWrap = document.getElementById("playerImageWrap");
    if (imgWrap) imgWrap.remove();
    modal && modal.classList.remove("is-open");
  }

  function bindAudioControls(audio) {
    const seek = $("#playerSeek");
    const playBtn = $("#playerPlay");
    const backBtn = $("#playerBack");
    const fwdBtn = $("#playerFwd");
    const curEl = $("#playerCurrent");
    const durEl = $("#playerDuration");

    if (playBtn) {
      playBtn.onclick = () => { if (audio.paused) audio.play(); else audio.pause(); };
    }
    if (backBtn) backBtn.onclick = () => { audio.currentTime = Math.max(0, audio.currentTime - 10); };
    if (fwdBtn) fwdBtn.onclick = () => { audio.currentTime = Math.min(audio.duration || 0, audio.currentTime + 10); };

    audio.ontimeupdate = () => {
      if (seek && isFinite(audio.duration) && audio.duration > 0) {
        const pct = (audio.currentTime / audio.duration) * 100;
        seek.value = pct;
        updateSeekFill(seek, pct);
      }
      if (curEl) curEl.textContent = fmtTime(audio.currentTime);
    };
    audio.ondurationchange = () => { if (durEl) durEl.textContent = fmtTime(audio.duration); };
    audio.onplay = () => { if (playBtn) { playBtn.innerHTML = `<img src="/static/icons/pause.svg" class="icon" style="width:26px;height:26px;filter:brightness(0) invert(1);" />`; } };
    audio.onpause = () => { if (playBtn) { playBtn.innerHTML = `<img src="/static/icons/play.svg" class="icon" style="width:26px;height:26px;filter:brightness(0) invert(1);" />`; } };

    if (seek) {
      updateSeekFill(seek, 0);
      seek.oninput = () => {
        if (isFinite(audio.duration) && audio.duration > 0) {
          audio.currentTime = (seek.value / 100) * audio.duration;
          updateSeekFill(seek, seek.value);
        }
      };
    }
  }

  function initPlayer() {
    $("#playerClose")?.addEventListener("click", closePlayer);
    $("#playerBackdrop")?.addEventListener("click", closePlayer);
  }

  // ---------- Indicator ----------
  function syncIndicator(container, indicator, activeBtn) {
    if (!container || !indicator || !activeBtn) return;
    const cRect = container.getBoundingClientRect(), bRect = activeBtn.getBoundingClientRect();
    indicator.style.left = "0px"; indicator.style.top = "0px";
    indicator.style.width = `${Math.round(bRect.width)}px`;
    indicator.style.height = `${Math.round(bRect.height)}px`;
    indicator.style.transform = `translate(${Math.round(bRect.left - cRect.left)}px, ${Math.round(bRect.top - cRect.top)}px)`;
  }

  // ---------- Tabs ----------
  const tabsEl = $("#tabs"), indEl = $("#tabsIndicator");
  function setTab(name) {
    $$("[data-tab]").forEach(b => b.classList.toggle("is-active", b.dataset.tab === name));
    $$("[data-panel]").forEach(p => p.classList.toggle("is-active", p.dataset.panel === name));
    const activeBtn = $$("[data-tab]").find(b => b.dataset.tab === name);
    if (tabsEl && indEl && activeBtn) syncIndicator(tabsEl, indEl, activeBtn);
    if (name === "profile") { window.EagleProfile?.renderProfile?.(); window.EagleProfile?.init?.(); syncAllSegmini(); }
    if (name === "recent") { lastHash = ""; loadRecents(false); }
    if (name === "help") window.EagleProfile?.init?.();
  }
  window.setTab = setTab;

  function bindTabs() {
    document.addEventListener("click", e => {
      const btn = e.target.closest("[data-tab]");
      if (!btn || !btn.dataset.tab) return;
      setTab(btn.dataset.tab);
    }, true);
    const active = $("[data-tab].is-active");
    if (active) syncIndicator(tabsEl, indEl, active);
    window.addEventListener("resize", () => {
      const a = $("[data-tab].is-active");
      if (a) syncIndicator(tabsEl, indEl, a);
      syncAllSegmini();
    });
  }

  // ---------- Segmini ----------
  function syncSegmini(seg) {
    if (!seg) return;
    const indicator = $(".segmini__indicator", seg);
    const active = $(".segmini__btn.is-active", seg) || $(".segmini__btn", seg);
    if (!indicator || !active) return;
    syncIndicator(seg, indicator, active);
  }
  function syncAllSegmini() { $$(".segmini").forEach(syncSegmini); }
  function setSegActive(seg, value) {
    if (!seg) return;
    $$(".segmini__btn", seg).forEach(b => b.classList.toggle("is-active", b.dataset.value === value));
    syncSegmini(seg);
  }

  // ---------- Settings modal ----------
  const modalEl = () => $("#settingsModal");
  function isModalOpen() { return modalEl()?.classList.contains("is-open"); }
  function openSettings() {
    const m = modalEl(); if (!m) return;
    const s = window.EagleProfile?.settings || { lang: "ru", theme: "dark" };
    setSegActive($("#langSeg"), s.lang);
    setSegActive($("#themeSeg"), s.theme);
    m.classList.add("is-open"); m.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
    requestAnimationFrame(() => syncAllSegmini());
  }
  function closeSettings() {
    const m = modalEl(); if (!m) return;
    m.classList.remove("is-open"); m.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
  }

  function getBotUsername() { return window.BOT_USERNAME || "EagleToolsBot"; }
  function openTgLink(url) {
    try {
      if (window.Telegram?.WebApp?.openTelegramLink && url.startsWith("https://t.me/")) { window.Telegram.WebApp.openTelegramLink(url); return; }
      if (window.Telegram?.WebApp?.openLink) { window.Telegram.WebApp.openLink(url); return; }
    } catch {}
    try { window.open(url, "_blank", "noopener"); } catch {}
  }

  // ---------- Tool card helpers ----------
  function getRole(card, role) { return card?.querySelector?.(`[data-role="${role}"]`) || null; }

  function setProgress(card, v) {
    const bar = getRole(card, "bar");
    const val = Math.max(0, Math.min(100, Number(v || 0)));
    if (bar) bar.style.width = `${val}%`;
    if (card) card.classList.toggle("is-progress", val > 0);
  }
  function setProgressText(card, html) { const el = getRole(card, "progress"); if (el) el.innerHTML = html || ""; }
  function setResult(card, html) {
    const el = getRole(card, "result");
    if (el) { el.innerHTML = html || ""; el.style.display = html ? "" : "none"; }
  }
  function resetCardUi(card) { setProgress(card, 0); setProgressText(card, ""); setResult(card, ""); }

  // ---------- Helpers ----------
  function pickFirstString(...vals) { for (const v of vals) { if (typeof v === "string" && v.trim()) return v.trim(); } return ""; }
  function extFromTool(tool) { return tool === "audio" ? ".mp3" : ".mp4"; }
  function normalizeDisplayName(name, tool) {
    const base = String(name || "").trim();
    if (!base) return "";
    if (/\.[a-z0-9]{2,5}$/i.test(base)) return base;
    return base + extFromTool(tool);
  }
  function extractOut(data, tool) {
    if (!data || typeof data !== "object") return null;
    const meta = data.metadata || data.meta || {};
    const out = data.out || data.result || data.file || {};
    const fileId = pickFirstString(data.file_id, out.file_id) || "";
    const downloadUrl = pickFirstString(data.download_url, out.download_url, data.url, out.url) || (fileId ? `/api/file/${encodeURIComponent(fileId)}` : "");
    const title = pickFirstString(data.title, out.title, data.filename, out.filename, meta.title, meta.filename);
    const displayName = normalizeDisplayName(title || fileId, tool);
    if (!downloadUrl) return null;
    return { fileId, downloadUrl, displayName };
  }

  // ---------- Tools run ----------
  let lastHash = "";

  async function runTool(card) {
    const tool = card?.dataset?.tool || "";
    const urlEl = getRole(card, "url");
    const url = (urlEl?.value || "").trim();
    if (!url) { toast(t("err_empty_url") || "Вставь ссылку", "warn", "⚠️"); return; }

    resetCardUi(card);

    /* Анимированный прогресс */
    let fakePct = 5;
    setProgress(card, fakePct);
    setProgressText(card, `<span>${t("starting") || "Загружаю…"}</span>`);
    const progTimer = setInterval(() => {
      fakePct = Math.min(fakePct + (Math.random() * 6), 88);
      setProgress(card, fakePct);
    }, 600);

    const t0 = performance.now();
    const r = await apiPost(`/api/save_job?tool=${encodeURIComponent(tool)}`, { url });
    clearInterval(progTimer);

    if (!r.ok) {
      setProgress(card, 0);
      setResult(card, `<div class="result-file"><div class="result-file__top"><span class="result-file__icon">⛔</span><span class="result-file__name muted">${escapeHtml(prettyErr(r))}</span></div></div>`);
      toast(prettyErr(r), "err", "⛔");
      hapticNotify("error");
      return;
    }

    setProgress(card, 100);
    lastHash = "";
    loadRecents(true);

    const data = r.data;
    const secs = ((performance.now() - t0) / 1000).toFixed(1);
    const out = extractOut(data, tool);

    if (out) {
      setTimeout(() => {
        setProgress(card, 0);
        const isAudio = tool === "audio" || out.displayName.endsWith(".mp3");
        const dlLabel   = t("btn_download") || "Скачать";
        const shareLabel = t("player_share") || "Поделиться";

        setResult(card, `
          <div class="result-file">
            <div class="result-file__top">
              <div class="result-file__icon">
                <div class="conv-check-anim">
                  <svg viewBox="0 0 48 48" width="36" height="36" fill="none">
                    <circle class="cca-circle" cx="24" cy="24" r="20" stroke="#34d399" stroke-width="2.5" stroke-linecap="round"/>
                    <polyline class="cca-tick" points="14,24 21,31 34,16" stroke="#34d399" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </div>
              </div>
              <span class="result-file__name">${escapeHtml(out.displayName)}</span>
            </div>
            <div class="result-file__actions">
              <button class="btn btn--primary btn--sm" type="button"
                data-action="open-file" data-url="${escapeHtml(out.downloadUrl)}" style="flex:1">
                <img src="/static/icons/dl.svg" class="icon" />
                ${dlLabel}
              </button>
              <button class="btn btn--secondary btn--sm" type="button"
                data-action="share-file" data-url="${escapeHtml(out.downloadUrl)}"
                data-title="${escapeHtml(out.displayName)}">
                <img src="/static/icons/share-2.svg" class="icon" />
                ${shareLabel}
              </button>
            </div>
          </div>
        `);
        toast(t("done") || "Готово!", "ok", "✅");
        hapticNotify("success");
      }, 300);
      return;
    }

    setProgress(card, 0);
    setProgressText(card, "");
    setResult(card, `<div class="result-file"><div class="result-file__top"><span class="result-file__icon">⏳</span><span class="result-file__name muted">${escapeHtml(t("queued") || "В очереди")}</span></div></div>`);
    toast(t("job_created") || "Задание создано", "ok", "✅");
    hapticNotify("success");
  }

  function bindToolRuns() {
    document.addEventListener("click", e => {
      const btn = e.target.closest("[data-role='run']");
      if (!btn) return;
      const card = btn.closest("[data-tool]");
      if (!card) return;
      runTool(card).catch(err => toast(String(err?.message || err), "err", "⛔"));
    }, true);
  }

  // ---------- Recents ----------
  function fmtBytes(n) {
    const v = Number(n);
    if (!Number.isFinite(v) || v <= 0) return "";
    const u = ["B", "KB", "MB", "GB", "TB"]; let i = 0, x = v;
    while (x >= 1024 && i < u.length - 1) { x /= 1024; i++; }
    return `${x.toFixed(i === 0 ? 0 : 1)} ${u[i]}`;
  }
  function fmtWhen(iso) {
    if (!iso) return "";
    try { const d = new Date(iso); if (Number.isNaN(d.getTime())) return ""; return d.toLocaleString(); } catch { return ""; }
  }
  function itemTitle(item) {
    const meta = item?.metadata || item?.meta || {};
    return pickFirstString(item?.title, item?.filename, meta?.title, meta?.filename);
  }

  /* ── SVG иконки для типов файлов ── */
  const FILE_ICONS = {
    audio:    `<img src="/static/icons/fmt-mp3.svg"   style="width:18px;height:18px;display:block;" />`,
    video:    `<img src="/static/icons/fmt-mp4.svg"   style="width:18px;height:18px;display:block;" />`,
    image:    `<img src="/static/icons/fmt-png.svg"   style="width:18px;height:18px;display:block;" />`,
    document: `<img src="/static/icons/file-doc.svg"  style="width:18px;height:18px;display:block;" />`,
    default:  `<img src="/static/icons/file-doc.svg"  style="width:18px;height:18px;display:block;" />`,
  };

  function recentRow(item) {
    const id          = item?.id ?? "";
    const title       = itemTitle(item) || item?.file_id || `#${id}`;
    const when        = fmtWhen(item?.created_at);
    const size        = fmtBytes(item?.size_bytes);
    const downloadUrl = item?.download_url || "";
    const canDl       = !!downloadUrl;
    const ext         = (item?.file_id || "").split(".").pop()?.toLowerCase() || "";
    const isAudio     = ["mp3","wav","ogg","flac","m4a","aac","opus"].includes(ext);
    const isVideo     = ["mp4","webm","mov","avi","mkv"].includes(ext);
    const isImage     = ["jpg","jpeg","png","webp","bmp","tiff","heic","gif"].includes(ext);
    const isTxt       = ["txt","pdf","doc","docx"].includes(ext);

    const fileType  = isAudio ? "audio" : isVideo ? "video" : isImage ? "image" : isTxt ? "document" : "default";
    const icon      = FILE_ICONS[fileType];
    const typeClass = `ri--${fileType === "default" ? "doc" : fileType}`;

    /* Статус */
    const rawStatus   = String(item?.status || "queued").toLowerCase();
    const isExpired   = rawStatus === "expired" || (!canDl && rawStatus === "done");
    const status      = isExpired ? "expired" : (canDl ? "done" : rawStatus);
    const badgeCls    = status === "done" ? "done"
      : status === "expired" ? "exp"
      : status === "failed" || status === "error" ? "err"
      : status === "running" ? "run" : "q";
    const statusLabel = status === "done" ? (t("done") || "ГОТОВО!")
      : status === "expired"  ? (t("expired") || "ИСТЁК")
      : status === "failed" || status === "error" ? (t("err_unknown") || "ОШИБКА")
      : status === "running"  ? (t("processing") || "ОБРАБАТЫВАЮ")
      : (t("queued") || "В ОЧЕРЕДИ");

    /* Tap-to-open datasets on the row inner (long press = action sheet) */
    const tapAttrs = canDl
      ? `data-action="recent-play" data-url="${escapeHtml(downloadUrl)}" data-title="${escapeHtml(title)}" data-audio="${isAudio}" data-image="${isImage}"`
      : "";

    return `
      <div class="recentitem ri ${typeClass}" data-id="${escapeHtml(id)}">
        <div class="ri-inner" ${tapAttrs}>
          <div class="ri-icon">${icon}</div>
          <div class="ri-info">
            <div class="ri-name">${escapeHtml(title)}</div>
            <div class="ri-meta">
              <span class="ri-badge ri-badge--${badgeCls}">${escapeHtml(statusLabel)}</span>
              ${size ? `<span class="ri-size">${escapeHtml(size)}</span>` : ""}
              ${size && when ? `<span class="ri-dot"></span>` : ""}
              ${when ? `<span class="ri-date">${escapeHtml(when)}</span>` : ""}
            </div>
          </div>
          <div class="ri-actions__hint">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" width="14" height="14" style="opacity:.3"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
          </div>
        </div>
      </div>
    `;
  }

  /* ── Анимация удаления — встряска + сворачивание ── */
  function deleteRow(row) {
    /* 1. Встряска */
    row.style.transition = "none";
    row.style.animation  = "riShake .35s cubic-bezier(.36,.07,.19,.97) both";
    /* 2. После встряски — краснеем и сворачиваемся */
    setTimeout(() => {
      row.style.animation  = "";
      row.style.transition = "background .2s ease";
      row.style.background = "rgba(248,113,113,.18)";
      row.style.borderColor = "rgba(248,113,113,.35)";
    }, 350);
    setTimeout(() => {
      row.style.transition = "transform .3s ease, opacity .3s ease, max-height .35s ease, margin .35s ease";
      row.style.transform  = "translateX(100%) scale(.9)";
      row.style.opacity    = "0";
      row.style.overflow   = "hidden";
      row.style.maxHeight  = "0";
      row.style.marginBottom = "0";
    }, 550);
    setTimeout(() => row.remove(), 900);
  }

  /* ── Лайтбокс для просмотра фото ── */
  function showImageViewer(url, title) {
    var old = document.getElementById("et-imgviewer");
    if (old) old.remove();

    const full = url.startsWith("http") ? url : window.location.origin + url;
    const el = document.createElement("div");
    el.id = "et-imgviewer";
    el.style.cssText = "position:fixed;inset:0;z-index:8000;background:rgba(0,0,0,.92);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;";
    el.innerHTML = `
      <div style="position:absolute;top:16px;right:16px;display:flex;gap:8px;">
        <button id="et-img-dl" style="background:var(--rose);border:none;border-radius:10px;padding:8px 14px;color:#fff;font-size:13px;font-weight:500;cursor:pointer;">
          Скачать
        </button>
        <button id="et-img-close" style="background:rgba(255,255,255,.1);border:none;border-radius:10px;padding:8px 14px;color:#fff;font-size:13px;cursor:pointer;">
          ✕
        </button>
      </div>
      <img src="${full}" style="max-width:calc(100vw - 32px);max-height:calc(100vh - 100px);border-radius:12px;object-fit:contain;" />
      ${title ? `<div style="font-size:12px;color:rgba(255,255,255,.5);max-width:80%;text-overflow:ellipsis;overflow:hidden;white-space:nowrap;">${escapeHtml(title)}</div>` : ""}
    `;
    document.body.appendChild(el);

    document.getElementById("et-img-close").onclick = () => el.remove();
    document.getElementById("et-img-dl").onclick = () => openFile(url);
    el.addEventListener("click", (e) => { if (e.target === el) el.remove(); });
  }

  function hash(items) {
    try { return JSON.stringify(items.map(x => [x?.id, x?.status, x?.file_id, x?.download_url, x?.title])); }
    catch { return String(items?.length || 0); }
  }

  let _recentItems = [];

  function sortItems(items, sortVal) {
    const arr = [...items];
    switch (sortVal) {
      case "date_asc":   return arr.sort((a,b) => new Date(a.created_at||0) - new Date(b.created_at||0));
      case "name_asc":   return arr.sort((a,b) => (a.title||"").localeCompare(b.title||""));
      case "name_desc":  return arr.sort((a,b) => (b.title||"").localeCompare(a.title||""));
      case "size_desc":  return arr.sort((a,b) => (b.size_bytes||0) - (a.size_bytes||0));
      case "size_asc":   return arr.sort((a,b) => (a.size_bytes||0) - (b.size_bytes||0));
      default:           return arr.sort((a,b) => new Date(b.created_at||0) - new Date(a.created_at||0));
    }
  }

  function _hideSkeleton() {
    const sk = document.getElementById("recentSkeleton");
    if (sk) sk.style.display = "none";
  }

  function renderRecents(items) {
    const list = $("#recentList"); if (!list) return;
    _hideSkeleton();
    _recentItems = items || [];

    /* Preserve onboarding demo row across re-renders */
    const demoEl = document.getElementById("et-demo-file");

    if (!_recentItems.length) {
      renderEmptyRecent(list);
    } else {
      const sortSel = document.getElementById("recentSort");
      const sortVal = sortSel ? sortSel.value : "date_desc";
      const sorted  = sortItems(_recentItems, sortVal);
      list.innerHTML = sorted.map(recentRow).join("");
    }

    if (demoEl && !list.contains(demoEl)) {
      list.insertBefore(demoEl, list.firstChild);
    }
  }

  async function loadRecents(silent = true) {
    const r = await apiGet("/api/recent");
    if (!r || !r.ok) { if (!silent) toast(prettyErr(r), "err", "⛔"); return; }
    const d = r.data || {};
    const items = Array.isArray(d) ? d : Array.isArray(d.items) ? d.items : [];
    const h = hash(items);
    if (silent && h === lastHash) return;
    lastHash = h;
    renderRecents(items);
  }

  // ---------- Actions ----------
  async function onAction(action, el) {
    if (action === "open-profile") return setTab("profile");
    if (action === "open-settings") { openSettings(); return; }
    if (action === "close-settings") { closeSettings(); return; }
    if (action === "switch-to-tools") { setTab("tools"); return; }
    if (action === "close-action-sheet") { closeActionSheet(); return; }
    if (action.startsWith("as-")) { await handleActionSheetAction(action); return; }

    if (action === "open-upgrade") {
      openTgLink(`https://t.me/${encodeURIComponent(getBotUsername())}?start=premium`);
      setTimeout(() => { try { window.Telegram?.WebApp?.close(); } catch {} }, 300);
      return;
    }
    if (action === "open-support") { openTgLink("https://t.me/zorixyzz"); return; }
    if (action === "open-tour") {
      closeSettings();
      setTimeout(() => { if (typeof window.eagleTourStart === "function") window.eagleTourStart(); }, 320);
      return;
    }
    if (action === "open-privacy") {
      try { if (window.Telegram?.WebApp?.openLink) { window.Telegram.WebApp.openLink("https://telegra.ph/Politika-konfidencialnosti---EagleTools-03-11-2"); return; } } catch {}
      window.open("https://telegra.ph/Politika-konfidencialnosti---EagleTools-03-11-2", "_blank"); return;
    }

    if (action === "open-file") { haptic("medium"); openFile(el.dataset.url || ""); return; }
    if (action === "share-file") { haptic("light"); await shareFile(el.dataset.url || "", el.dataset.title || ""); return; }

    if (action === "lang") {
      const v = el.dataset.value;
      if (v === "ru" || v === "en") {
        window.EagleProfile?.setLang?.(v);
        setSegActive($("#langSeg"), v);
        const a = $("[data-tab].is-active");
        if (a) syncIndicator(tabsEl, indEl, a);
        setTimeout(() => window.EagleProfile?.init?.(), 10);
      }
      return;
    }
    if (action === "theme") {
      const v = el.dataset.value;
      if (v === "dark" || v === "light") { window.EagleProfile?.setTheme?.(v); setSegActive($("#themeSeg"), v); }
      return;
    }

    if (action === "copy-ref") {
      const link = window.EagleProfile?.refLink || "";
      if (!link) return toast("—", "warn", "⚠️");
      try { await navigator.clipboard.writeText(link); toast(t("copied") || "Скопировано", "ok", "✅"); }
      catch { toast(t("copy_failed") || "Ошибка копирования", "err", "⛔"); }
      return;
    }
    if (action === "share-ref") {
      const link = window.EagleProfile?.refLink || "";
      if (!link) return toast("—", "warn", "⚠️");
      try { if (navigator.share) await navigator.share({ text: link, url: link }); else await navigator.clipboard.writeText(link); toast(t("copied") || "Скопировано!", "ok", "✅"); }
      catch {}
      return;
    }

    if (action === "recent-play") {
      const isImage = el.dataset.image === "true";
      if (isImage) {
        /* Показываем фото/GIF в плеере */
        openPlayer(el.dataset.url || "", el.dataset.title || "", false, true);
        return;
      }
      const url = el.dataset.url || "";
      const title = el.dataset.title || "";
      const isAudio = el.dataset.audio === "true";
      if (!url) return;
      openPlayer(url, title, isAudio);
      return;
    }

    if (action === "recent-dl") { haptic("medium"); openFile(el.dataset.url || ""); return; }
    if (action === "recent-share") {
      const shareUrl = el.dataset.url || "";
      const shareTitle = el.dataset.title || "";
      if (shareUrl) {
        const fullUrl = shareUrl.startsWith("http") ? shareUrl : window.location.origin + shareUrl;
        try {
          if (navigator.share) { await navigator.share({ title: shareTitle || "EagleTools", url: fullUrl }); return; }
        } catch {}
        try { await navigator.clipboard.writeText(fullUrl); toast(t("link_copied") || "Ссылка скопирована", "ok", "📋"); } catch {}
      }
      return;
    }
    if (action === "recent-share-old") { await shareFile(el.dataset.url || "", el.dataset.title || ""); return; }

    if (action === "recent-del") {
      const row = el.closest(".recentitem");
      const id = row?.dataset?.id;
      if (!id) return;
      const ok = confirm(t("confirm_delete") || "Удалить файл?");
      if (!ok) return;
      deleteRow(row);
      const r = await apiDelete(`/api/recent/${encodeURIComponent(id)}`);
      if (!r.ok) { toast(prettyErr(r), "err", "⛔"); lastHash = ""; loadRecents(false); return; }
      lastHash = "";
      loadRecents(true);
    }
  }

  function bindGlobalClick() {
    document.addEventListener("click", async e => {
      const btn = e.target.closest("[data-action]");
      if (!btn) return;
      const action = btn.dataset.action;
      if (!action) return;
      try { await onAction(action, btn); }
      catch (err) { toast(String(err?.message || err), "err", "⛔"); }
    }, true);
  }

  // ══════════════════════════════════════════════════════════════
  // ACTION SHEET
  // ══════════════════════════════════════════════════════════════
  let _asItem = null;
  const _asEl  = () => document.getElementById("actionSheet");
  const _asTitle = () => document.getElementById("actionSheetTitle");
  const _asItems = () => document.getElementById("actionSheetItems");

  function _asIcon(path) {
    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;
  }

  function openActionSheet(item) {
    const sheet = _asEl(); if (!sheet) return;
    haptic("light");
    _asItem = item;

    const name  = (item.title || item.file_id || "").split("/").pop();
    const canDl = !!(item.download_url);
    const ext   = (item.file_id || "").split(".").pop()?.toLowerCase() || "";
    const isAudio = ["mp3","wav","ogg","flac","m4a","aac","opus"].includes(ext);
    const isImage = ["jpg","jpeg","png","webp","gif","bmp"].includes(ext);

    _asTitle().textContent = name || t("action_file") || "Файл";

    const rows = [];
    if (canDl) {
      rows.push({ label: t("action_open")  || "Открыть",          icon: _asIcon('<circle cx="12" cy="12" r="10"/><polygon points="10,8 16,12 10,16"/>'), action:"as-play",  danger:false });
      rows.push({ label: t("action_dl")    || "Скачать",          icon: _asIcon('<path d="M12 15V3m0 12-4-4m4 4 4-4M2 17l.621 2.485A2 2 0 004.561 21h14.878a2 2 0 001.94-1.515L22 17"/>'), action:"as-dl", danger:false });
      rows.push({ label: t("action_share") || "Поделиться",       icon: _asIcon('<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>'), action:"as-share", danger:false });
      rows.push({ label: t("action_copy")  || "Копировать ссылку",icon: _asIcon('<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>'), action:"as-copy", danger:false });
      rows.push("sep");
    }
    rows.push({ label: t("action_del") || "Удалить", icon: _asIcon('<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>'), action:"as-del", danger:true });

    _asItems().innerHTML = rows.map(r => {
      if (r === "sep") return `<div class="action-sheet__sep"></div>`;
      return `<button class="action-sheet__item${r.danger ? " action-sheet__item--danger" : ""}" type="button" data-action="${r.action}">
        <span class="action-sheet__item-icon">${r.icon}</span>
        <span class="action-sheet__item-label">${escapeHtml(r.label)}</span>
      </button>`;
    }).join("");

    sheet.setAttribute("aria-hidden","false");
    requestAnimationFrame(() => sheet.classList.add("is-open"));
  }

  function closeActionSheet() {
    const sheet = _asEl(); if (!sheet) return;
    sheet.classList.remove("is-open");
    setTimeout(() => { sheet.setAttribute("aria-hidden","true"); _asItem = null; }, 320);
  }

  async function handleActionSheetAction(action) {
    const item = _asItem;
    closeActionSheet();
    if (!item) return;
    await new Promise(r => setTimeout(r, 60));

    const url   = item.download_url || "";
    const title = item.title || item.file_id || "";
    const ext   = (item.file_id || "").split(".").pop()?.toLowerCase() || "";
    const isAudio = ["mp3","wav","ogg","flac","m4a","aac","opus"].includes(ext);
    const isImage = ["jpg","jpeg","png","webp","gif","bmp"].includes(ext);

    if (action === "as-play") {
      if (isImage) { openPlayer(url, title, false, true); return; }
      if (url) openPlayer(url, title, isAudio);
    } else if (action === "as-dl") {
      haptic("medium"); openFile(url);
    } else if (action === "as-share") {
      if (url) {
        const full = url.startsWith("http") ? url : window.location.origin + url;
        try { if (navigator.share) { await navigator.share({ title, url: full }); return; } } catch {}
        try { await navigator.clipboard.writeText(full); toast(t("link_copied") || "Ссылка скопирована", "ok", "📋"); } catch {}
      }
    } else if (action === "as-copy") {
      if (url) {
        const full = url.startsWith("http") ? url : window.location.origin + url;
        try { await navigator.clipboard.writeText(full); toast(t("copied") || "Скопировано!", "ok", "✅"); haptic("light"); } catch {}
      }
    } else if (action === "as-del") {
      if (item.id === "demo") return; // onboarding demo
      const row = document.querySelector(`.recentitem[data-id="${CSS.escape(String(item.id))}"]`);
      if (!row) return;
      deleteRow(row);
      const r = await apiDelete(`/api/recent/${encodeURIComponent(item.id)}`);
      if (!r.ok) { toast(prettyErr(r), "err", "⛔"); lastHash = ""; loadRecents(false); return; }
      lastHash = ""; loadRecents(true); hapticNotify("success");
    }
  }

  function _initActionSheet() {
    const bd = document.getElementById("actionSheetBackdrop");
    if (bd) bd.addEventListener("click", closeActionSheet);
  }

  // ══════════════════════════════════════════════════════════════
  // LONG PRESS → ACTION SHEET
  // ══════════════════════════════════════════════════════════════
  let _lpFired = false; // blocks click after a long press fires

  function bindLongPress() {
    let _lpTimer = null, _lpRow = null, _lpMoved = false;

    document.addEventListener("touchstart", e => {
      const row = e.target.closest(".recentitem[data-id]");
      if (!row) return;
      _lpRow = row; _lpMoved = false; _lpFired = false;
      _lpTimer = setTimeout(() => {
        if (_lpMoved) return;
        _lpFired = true;
        row.classList.add("is-pressing");
        haptic("medium");
        setTimeout(() => {
          row.classList.remove("is-pressing");
          const id    = row.dataset.id;
          const item  = (id === "demo") ? { id:"demo", title:"EagleTools_demo.mp4", download_url:"#", file_id:"demo.mp4" }
                                        : _recentItems.find(x => String(x.id) === String(id));
          if (item) openActionSheet(item);
        }, 180);
      }, 380);
    }, { passive: true });

    document.addEventListener("touchmove", () => {
      _lpMoved = true;
      clearTimeout(_lpTimer);
      if (_lpRow) { _lpRow.classList.remove("is-pressing"); _lpRow = null; }
    }, { passive: true });

    document.addEventListener("touchend", () => {
      clearTimeout(_lpTimer);
      if (_lpRow) { _lpRow.classList.remove("is-pressing"); _lpRow = null; }
    }, { passive: true });

    /* Suppress click that fires right after a long press */
    document.addEventListener("click", e => {
      if (_lpFired) { _lpFired = false; e.stopImmediatePropagation(); e.preventDefault(); }
    }, true);
  }

  // ══════════════════════════════════════════════════════════════
  // SWIPE TO DELETE
  // ══════════════════════════════════════════════════════════════
  function _addSwipeBg(row) {
    if (row.querySelector(".ri-swipe-bg")) return;
    const bg = document.createElement("div");
    bg.className = "ri-swipe-bg";
    bg.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg><span>${escapeHtml(t("action_del") || "Удалить")}</span>`;
    row.style.position = "relative";
    row.insertBefore(bg, row.firstChild);
  }

  function bindSwipeRow(row) {
    if (row.dataset.swipeBound) return;
    row.dataset.swipeBound = "1";
    _addSwipeBg(row);

    const inner = row.querySelector(".ri-inner");
    const bg    = row.querySelector(".ri-swipe-bg");
    if (!inner) return;

    let startX, startY, curX = 0, tracking = false, axisLocked = false, isH = false;
    const THRESHOLD = 88;

    row.addEventListener("touchstart", e => {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      tracking = true; axisLocked = false; isH = false; curX = 0;
      inner.style.transition = "none";
    }, { passive: true });

    row.addEventListener("touchmove", e => {
      if (!tracking) return;
      const dx = e.touches[0].clientX - startX;
      const dy = e.touches[0].clientY - startY;
      if (!axisLocked) {
        axisLocked = true;
        isH = Math.abs(dx) > Math.abs(dy) + 4;
      }
      if (!isH) return;
      e.preventDefault();
      curX = Math.min(0, dx);
      inner.style.transform = `translateX(${curX}px)`;
      if (bg) bg.style.opacity = Math.min(1, -curX / THRESHOLD);
    }, { passive: false });

    row.addEventListener("touchend", async () => {
      if (!tracking || !isH) { tracking = false; return; }
      tracking = false;
      inner.style.transition = "transform .25s cubic-bezier(.4,0,.2,1)";
      if (bg) bg.style.transition = "opacity .25s";

      if (curX < -THRESHOLD) {
        inner.style.transform = `translateX(-${row.offsetWidth}px)`;
        if (bg) bg.style.opacity = "1";
        const id = row.dataset.id;
        if (id === "demo") { setTimeout(() => row.remove(), 260); return; }
        hapticNotify("success");
        setTimeout(async () => {
          deleteRow(row);
          const r = await apiDelete(`/api/recent/${encodeURIComponent(id)}`);
          if (!r.ok) { toast(prettyErr(r), "err", "⛔"); lastHash = ""; loadRecents(false); }
          else { lastHash = ""; loadRecents(true); }
        }, 250);
      } else {
        inner.style.transform = "translateX(0)";
        if (bg) bg.style.opacity = "0";
        curX = 0;
      }
    }, { passive: true });
  }

  function bindSwipeToDelete() {
    // delegated: bind new rows as they appear
    const observer = new MutationObserver(() => {
      document.querySelectorAll(".recentitem[data-id]").forEach(bindSwipeRow);
    });
    const list = document.getElementById("recentList");
    if (list) observer.observe(list, { childList: true, subtree: false });
    document.querySelectorAll(".recentitem[data-id]").forEach(bindSwipeRow);
  }

  // ══════════════════════════════════════════════════════════════
  // EMPTY STATE
  // ══════════════════════════════════════════════════════════════
  function renderEmptyRecent(list) {
    list.innerHTML = `
      <div class="recent-empty">
        <div class="recent-empty__icon">🦅</div>
        <div class="recent-empty__title">${escapeHtml(t("recent_empty_title") || "Пока пусто")}</div>
        <div class="recent-empty__sub">${escapeHtml(t("recent_empty_sub") || "Скачай видео или конвертируй файл — он появится здесь")}</div>
        <button class="btn btn--primary" type="button" data-action="switch-to-tools">${escapeHtml(t("recent_go_tools") || "Перейти к инструментам")}</button>
      </div>`;
  }

  // ══════════════════════════════════════════════════════════════
  // HELP BADGE
  // ══════════════════════════════════════════════════════════════
  const HELP_BADGE_KEY = "et_help_seen_v1";

  function initHelpBadge() {
    try { if (localStorage.getItem(HELP_BADGE_KEY)) _hideHelpBadge(); } catch {}
    const helpBtn = document.getElementById("helpTabBtn");
    if (helpBtn) helpBtn.addEventListener("click", () => {
      try { localStorage.setItem(HELP_BADGE_KEY, "1"); } catch {}
      _hideHelpBadge();
    }, { once: true });
  }

  function _hideHelpBadge() {
    const dot = document.getElementById("helpNewDot");
    if (dot) dot.remove();
  }

  // ---------- Init ----------
  function init() {
    $$("[data-tool]").forEach(resetCardUi);
    bindTabs();
    bindToolRuns();
    bindGlobalClick();
    initPlayer();
    _initActionSheet();
    bindLongPress();
    bindSwipeToDelete();
    initHelpBadge();
    document.addEventListener("keydown", e => {
      if (e.key === "Escape") {
        const sheet = document.getElementById("actionSheet");
        if (sheet && sheet.classList.contains("is-open")) { closeActionSheet(); return; }
        if (isModalOpen()) closeSettings(); else closePlayer();
      }
    });
    syncAllSegmini();
    loadRecents(true).catch(() => {});
    /* Сортировка recent */
    const sortSel = document.getElementById("recentSort");
    if (sortSel) sortSel.addEventListener("change", () => renderRecents(_recentItems));

    window.__EAGLE_APP_READY__ = true;
    window.__eagleOpenFile = openFile;
    window.__eagleToast = toast;
    window.__eagleOpenActionSheet = openActionSheet;
    window.__eagleCloseActionSheet = closeActionSheet;
    requestAnimationFrame(() => {
      const a = $("[data-tab].is-active");
      if (a) syncIndicator(tabsEl, indEl, a);
      syncAllSegmini();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();