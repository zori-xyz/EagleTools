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

  function openPlayer(url, title, isAudio) {
    playerUrl = url; playerTitle = title || ""; playerIsAudio = isAudio;
    const modal = $("#playerModal");
    const video = $("#playerVideo"), audio = $("#playerAudio");
    const videoWrap = $("#playerVideoWrap"), audioWrap = $("#playerAudioWrap");
    const controls = $("#playerControls");
    const titleEl = $("#playerAudioTitle");

    // stop previous
    if (video) { video.pause(); video.src = ""; }
    if (audio) { audio.pause(); audio.src = ""; }

    if (isAudio) {
      videoWrap && (videoWrap.style.display = "none");
      audioWrap && (audioWrap.style.display = "");
      controls && (controls.style.display = "");
      if (titleEl) titleEl.textContent = title || "Аудио";
      if (audio) {
        audio.src = url.startsWith("http") ? url : window.location.origin + url;
        audio.load();
        bindAudioControls(audio);
      }
    } else {
      audioWrap && (audioWrap.style.display = "none");
      videoWrap && (videoWrap.style.display = "");
      controls && (controls.style.display = "none");
      if (video) {
        video.src = url.startsWith("http") ? url : window.location.origin + url;
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
    setProgress(card, 20);
    setProgressText(card, `<span>${t("starting") || "Загружаем…"}</span>`);

    const t0 = performance.now();
    const r = await apiPost(`/api/save_job?tool=${encodeURIComponent(tool)}`, { url });

    if (!r.ok) {
      resetCardUi(card);
      setResult(card, `<div class="result-file"><div class="result-file__top"><span class="result-file__icon">⛔</span><span class="result-file__name muted">${escapeHtml(prettyErr(r))}</span></div></div>`);
      toast(prettyErr(r), "err", "⛔");
      return;
    }

    lastHash = "";
    loadRecents(true);

    const data = r.data;
    const secs = ((performance.now() - t0) / 1000).toFixed(1);
    const out = extractOut(data, tool);

    if (out) {
      setProgress(card, 0);
      setProgressText(card, `✓ Готово за ${escapeHtml(secs)}s`);

      const isAudio = tool === "audio" || out.displayName.endsWith(".mp3");
      const icon = isAudio ? "🎵" : "🎬";

      setResult(card, `
        <div class="result-file">
          <div class="result-file__top">
            <span class="result-file__icon">${icon}</span>
            <span class="result-file__name">${escapeHtml(out.displayName)}</span>
          </div>
          <div class="result-file__actions">
            <button class="btn btn--secondary btn--sm" type="button"
              data-action="open-file" data-url="${escapeHtml(out.downloadUrl)}">
              🌐 Открыть
            </button>
            <button class="btn btn--primary btn--sm" type="button"
              data-action="share-file" data-url="${escapeHtml(out.downloadUrl)}"
              data-title="${escapeHtml(out.displayName)}">
              📤 Поделиться
            </button>
          </div>
        </div>
      `);

      toast(t("done") || "Готово!", "ok", "✅");
      return;
    }

    setProgress(card, 0);
    setProgressText(card, "");
    setResult(card, `<div class="result-file"><div class="result-file__top"><span class="result-file__icon">⏳</span><span class="result-file__name muted">${escapeHtml(t("queued") || "В очереди")}</span></div></div>`);
    toast(t("job_created") || "Задание создано", "ok", "✅");
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
    const statusLabel = status === "done" ? (t("done") || "ГОТОВО")
      : status === "expired" ? "ИСТЁК"
      : status === "failed" || status === "error" ? (t("err_unknown") || "ОШИБКА")
      : status === "running" ? "ОБРАБАТЫВАЮ"
      : "В ОЧЕРЕДИ";

    const dlBtn = `<button class="ri-btn ri-btn--dl" type="button" data-action="recent-dl"
      data-url="${escapeHtml(downloadUrl)}" ${canDl ? "" : "disabled"} aria-label="Download">
      <svg class="ri-btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><path d="M12 15V3m0 12-4-4m4 4 4-4M2 17l.621 2.485A2 2 0 004.561 21h14.878a2 2 0 001.94-1.515L22 17"/></svg>
    </button>`;

    const delBtn = `<button class="ri-btn ri-btn--del" type="button" data-action="recent-del" aria-label="Delete">
      <svg class="ri-btn-icon ri-btn-icon--del" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>
    </button>`;

    const playBtn = canDl ? `<button class="ri-btn ri-btn--play" type="button" data-action="recent-play"
      data-url="${escapeHtml(downloadUrl)}" data-title="${escapeHtml(title)}"
      data-audio="${isAudio}" data-image="${isImage}" aria-label="Play">
      <svg viewBox="0 0 24 24" fill="#ffffff" width="14" height="14"><path d="M8 5v14l11-7z"/></svg>
    </button>` : "";

    return `
      <div class="recentitem ri ${typeClass}" data-id="${escapeHtml(id)}">
        <div class="ri-inner">
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
          <div class="ri-actions">
            ${playBtn}${dlBtn}${delBtn}
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

  function renderRecents(items) {
    const list = $("#recentList"); if (!list) return;
    _recentItems = items || [];
    if (!_recentItems.length) {
      list.innerHTML = `<div class="muted small" style="text-align:center;padding:32px 0">${escapeHtml(t("recent_empty") || "Нет загрузок")}</div>`;
      return;
    }
    const sortSel = document.getElementById("recentSort");
    const sortVal = sortSel ? sortSel.value : "date_desc";
    const sorted  = sortItems(_recentItems, sortVal);
    list.innerHTML = sorted.map(recentRow).join("");
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

    if (action === "open-file") { openFile(el.dataset.url || ""); return; }
    if (action === "share-file") { await shareFile(el.dataset.url || "", el.dataset.title || ""); return; }

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
        /* Показываем фото в лайтбоксе */
        const url = el.dataset.url || "";
        const title = el.dataset.title || "";
        showImageViewer(url, title);
        return;
      }
      const url = el.dataset.url || "";
      const title = el.dataset.title || "";
      const isAudio = el.dataset.audio === "true";
      if (!url) return;
      openPlayer(url, title, isAudio);
      return;
    }

    if (action === "recent-dl") { openFile(el.dataset.url || ""); return; }
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

  // ---------- Init ----------
  function init() {
    $$("[data-tool]").forEach(resetCardUi);
    bindTabs();
    bindToolRuns();
    bindGlobalClick();
    initPlayer();
    document.addEventListener("keydown", e => { if (e.key === "Escape") { if (isModalOpen()) closeSettings(); else closePlayer(); } });
    syncAllSegmini();
    loadRecents(true).catch(() => {});
    /* Сортировка recent */
    const sortSel = document.getElementById("recentSort");
    if (sortSel) sortSel.addEventListener("change", () => renderRecents(_recentItems));

    window.__EAGLE_APP_READY__ = true;
    window.__eagleOpenFile = openFile;
    window.__eagleToast = toast;
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