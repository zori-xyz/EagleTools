// smart-input.js — unified Smart Input for EagleTools Home tab
(() => {
  "use strict";

  const URL_PATTERNS = {
    youtube:    /(?:youtube\.com\/(?:watch|shorts|embed)|youtu\.be\/)/i,
    soundcloud: /soundcloud\.com\//i,
  };

  const URL_ACTIONS = {
    youtube: [
      { tool: "save",  icon: "🎬", label_ru: "Видео",  label_en: "Video",  badge: "MP4", color: "#e8195a" },
      { tool: "audio", icon: "🎵", label_ru: "Аудио",  label_en: "Audio",  badge: "MP3", color: "#7c3aed" },
    ],
    soundcloud: [
      { tool: "audio", icon: "🎵", label_ru: "MP3",    label_en: "MP3",    badge: "MP3", color: "#7c3aed" },
    ],
    generic: [
      { tool: "save",  icon: "⬇️", label_ru: "Скачать", label_en: "Download", badge: "", color: "#059669" },
    ],
  };

  const FILE_ACTIONS = {
    video:    [
      { id: "video_to_mp3",  icon: "🎵", name: "→ MP3",  desc_ru: "Извлечь аудио",    desc_en: "Extract audio",  color: "#7c3aed" },
      { id: "video_to_mp4",  icon: "🎬", name: "→ MP4",  desc_ru: "Конвертировать",   desc_en: "Convert video",  color: "#e8195a" },
      { id: "video_to_gif",  icon: "🖼",  name: "→ GIF",  desc_ru: "Сделать гифку",    desc_en: "Make GIF",       color: "#059669" },
      { id: "video_compress",icon: "🗜",  name: "Сжать",  desc_ru: "Уменьшить размер", desc_en: "Compress size",  color: "#d97706" },
    ],
    audio:    [
      { id: "audio_to_mp3",  icon: "🎵", name: "→ MP3",  desc_ru: "Конвертировать",   desc_en: "Convert",        color: "#e8195a" },
      { id: "audio_to_wav",  icon: "🎼", name: "→ WAV",  desc_ru: "Несжатый формат",  desc_en: "Lossless",       color: "#7c3aed" },
      { id: "audio_to_ogg",  icon: "🎵", name: "→ OGG",  desc_ru: "Открытый формат",  desc_en: "Open format",    color: "#059669" },
      { id: "audio_compress",icon: "🗜",  name: "Сжать",  desc_ru: "Уменьшить размер", desc_en: "Compress size",  color: "#d97706" },
    ],
    image:    [
      { id: "img_to_jpg",    icon: "🖼",  name: "→ JPG",  desc_ru: "Универсальный",    desc_en: "Universal",      color: "#e8195a" },
      { id: "img_to_png",    icon: "🖼",  name: "→ PNG",  desc_ru: "С прозрачностью",  desc_en: "Transparent",    color: "#7c3aed" },
      { id: "img_to_webp",   icon: "🖼",  name: "→ WebP", desc_ru: "Для веба",         desc_en: "For web",        color: "#059669" },
      { id: "img_compress",  icon: "🗜",  name: "Сжать",  desc_ru: "Уменьшить файл",   desc_en: "Reduce size",    color: "#d97706" },
    ],
    pdf:      [
      { id: "pdf_to_txt",    icon: "📝", name: "→ Текст",desc_ru: "Извлечь текст",    desc_en: "Extract text",   color: "#e8195a" },
      { id: "pdf_compress",  icon: "🗜",  name: "Сжать",  desc_ru: "Уменьшить файл",   desc_en: "Reduce size",    color: "#d97706" },
    ],
    document: [
      { id: "doc_to_pdf",    icon: "📄", name: "→ PDF",  desc_ru: "Конвертировать",   desc_en: "Convert to PDF", color: "#e8195a" },
      { id: "doc_to_txt",    icon: "📝", name: "→ Текст",desc_ru: "Извлечь текст",    desc_en: "Extract text",   color: "#059669" },
    ],
  };

  const VIDEO_EXT  = ["mp4","mkv","mov","avi","webm","flv","wmv","m4v","3gp"];
  const AUDIO_EXT  = ["mp3","wav","flac","ogg","opus","m4a","aac","wma","aiff"];
  const IMAGE_EXT  = ["jpg","jpeg","png","gif","webp","heic","bmp","tiff","avif"];
  const PDF_EXT    = ["pdf"];
  const DOC_EXT    = ["doc","docx","xls","xlsx","ppt","pptx","odt","txt","csv","rtf"];

  const URL_CHIP_ICONS = { youtube: "▶️", soundcloud: "🎵", generic: "🌐" };
  const URL_CHIP_NAMES = {
    youtube: "YouTube",
    soundcloud: "SoundCloud",
    generic_ru: "Ссылка",
    generic_en: "URL",
  };

  const $ = id => document.getElementById(id);

  let mode = null;        // "url" | "file"
  let currentUrl = "";
  let urlType = null;
  let currentFile = null;
  let fileType = null;
  let selectedTool = null;   // for URL mode
  let selectedAction = null; // for file mode
  let running = false;

  function tx(key) { return window.EagleProfile?.t?.(key) || key; }
  function getLang() { try { return document.documentElement.lang === "en" ? "en" : "ru"; } catch { return "ru"; } }
  function esc(s) { return String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }

  function fmtSize(b) {
    if (!b) return "";
    if (b < 1048576) return (b / 1024).toFixed(1) + " KB";
    return (b / 1048576).toFixed(1) + " MB";
  }

  function checkQuota() {
    const q = window.__eagleQuota;
    if (!q) return true;
    if (q.isPremium) return true;
    return (q.used || 0) < (q.limit || 10);
  }

  function detectUrlType(url) {
    if (URL_PATTERNS.youtube.test(url)) return "youtube";
    if (URL_PATTERNS.soundcloud.test(url)) return "soundcloud";
    if (/^https?:\/\//i.test(url)) return "generic";
    return null;
  }

  function detectFileType(file) {
    const mime = (file.type || "").toLowerCase();
    const ext  = (file.name || "").split(".").pop().toLowerCase();
    if (mime.startsWith("video/")  || VIDEO_EXT.includes(ext))  return "video";
    if (mime.startsWith("audio/")  || AUDIO_EXT.includes(ext))  return "audio";
    if (mime.startsWith("image/")  || IMAGE_EXT.includes(ext))  return "image";
    if (mime === "application/pdf" || PDF_EXT.includes(ext))    return "pdf";
    if (DOC_EXT.includes(ext))                                   return "document";
    return null;
  }

  // ── UI helpers ──

  function showChip(icon, type, sub) {
    $("smartDropzone").style.display = "none";
    $("smartUrlRow") && ($("smartUrlRow").style.display = "none");
    const chip = $("smartChip"); chip.style.display = "";
    $("smartChipIcon").textContent = icon;
    $("smartChipType").textContent = type;
    $("smartChipSub").textContent = sub;
  }

  function showActions(html) {
    const el = $("smartActions"); el.style.display = "";
    $("smartActionsRow").innerHTML = html;
    $("smartQuotaWarn").style.display = "none";
    if (!checkQuota()) {
      el.style.display = "none";
      $("smartQuotaWarn").style.display = "";
    }
  }

  function setProgress(pct, text) {
    $("smartProgress").style.display = "";
    $("smartProgress").classList.toggle("is-running", pct < 100);
    $("smartProgressFill").style.width = pct + "%";
    if (text != null) $("smartProgressText").textContent = text;
  }

  function hideProgress() { $("smartProgress").style.display = "none"; }

  function showResult(html) {
    hideProgress();
    const el = $("smartResult"); el.innerHTML = html;
  }

  function reset() {
    mode = null; currentUrl = ""; urlType = null;
    currentFile = null; fileType = null;
    selectedTool = null; selectedAction = null; running = false;
    $("smartDropzone").style.display = "";
    $("smartChip").style.display = "none";
    $("smartActions").style.display = "none";
    $("smartQuotaWarn").style.display = "none";
    hideProgress();
    $("smartResult").innerHTML = "";
    $("smartUrlRow").style.display = "none";
    const inp = $("smartUrlInput"); if (inp) inp.value = "";
    const fi = $("smartFileInput"); if (fi) fi.value = "";
  }

  // ── Handle URL ──

  function handleUrl(url) {
    const u = (url || "").trim();
    if (!u) return;
    const t = detectUrlType(u);
    if (!t) { window.__eagleToast?.(tx("err_bad_url") || "Неверная ссылка", "warn", "⚠️"); return; }
    currentUrl = u; urlType = t; mode = "url";
    const lang = getLang();
    const chipName = t === "youtube" ? "YouTube" : t === "soundcloud" ? "SoundCloud" : (lang === "en" ? "URL" : "Ссылка");
    const sub = u.replace(/^https?:\/\//, "").slice(0, 52) + (u.length > 56 ? "…" : "");
    showChip(URL_CHIP_ICONS[t], chipName, sub);
    const actions = URL_ACTIONS[t] || URL_ACTIONS.generic;
    const btns = actions.map(a => {
      const label = lang === "en" ? a.label_en : a.label_ru;
      return `<button class="smart-action" data-tool="${esc(a.tool)}" type="button" style="border-color:${a.color}33">
        <span class="smart-action__icon">${a.icon}</span>
        <span class="smart-action__label">${esc(label)}</span>
        ${a.badge ? `<span class="smart-action__badge">${esc(a.badge)}</span>` : ""}
      </button>`;
    }).join("");
    showActions(btns);
    $("smartActionsRow").querySelectorAll(".smart-action").forEach(btn => {
      btn.addEventListener("click", () => { if (!running) runUrl(btn.dataset.tool); });
    });
  }

  // ── Handle file ──

  function handleFile(file) {
    if (!file) return;
    const MAX = 100 * 1024 * 1024;
    if (file.size > MAX) { window.__eagleToast?.(tx("conv_too_big") || "Файл слишком большой (макс. 100 МБ)", "warn", "⚠️"); return; }
    currentFile = file; fileType = detectFileType(file); mode = "file";
    const typeEmoji = { video:"🎬", audio:"🎵", image:"🖼", pdf:"📑", document:"📄" };
    showChip(typeEmoji[fileType] || "📄", file.name, fmtSize(file.size));
    if (!fileType) { showActions(`<div style="font-size:13px;color:var(--text3);padding:4px 0">${tx("conv_unsupported") || "Формат не поддерживается"}</div>`); return; }
    const lang = getLang();
    const rawExt = file.name.split(".").pop().toLowerCase();
    const inputExt = rawExt === "jpeg" ? "jpg" : rawExt;
    const all = FILE_ACTIONS[fileType] || [];
    const actions = all.filter(a => { const p = a.id.split("_to_"); return p.length < 2 || p[p.length - 1] !== inputExt; });
    const grid = `<div class="smart-actions__grid">${actions.map(a => `
      <div class="smart-action--grid" data-action-id="${esc(a.id)}" style="--ac:${a.color}">
        <div class="conv-action__icon" style="background:${a.color}22">${a.icon}</div>
        <div class="conv-action__text">
          <div class="conv-action__name">${esc(a.name)}</div>
          <div class="conv-action__desc">${esc(lang === "en" ? a.desc_en : a.desc_ru)}</div>
        </div>
      </div>`).join("")}</div>`;
    showActions(grid);
    $("smartActionsRow").querySelectorAll(".smart-action--grid").forEach(el => {
      el.addEventListener("click", () => {
        if (running) return;
        $("smartActionsRow").querySelectorAll(".smart-action--grid").forEach(e => e.classList.remove("selected"));
        el.classList.add("selected");
        selectedAction = el.dataset.actionId;
        runFile();
      });
    });
  }

  // ── Run URL job ──

  async function runUrl(tool) {
    if (running || !currentUrl || !tool) return;
    if (!checkQuota()) { $("smartQuotaWarn").style.display = ""; return; }
    running = true;
    $("smartActions").style.display = "none";
    let pct = 5; setProgress(pct, tx("starting") || "Загружаю…");
    const timer = setInterval(() => { pct = Math.min(pct + Math.random() * 6, 88); setProgress(pct); }, 600);
    const r = await window.EagleAPI?.postJson?.(`/api/save_job?tool=${encodeURIComponent(tool)}`, { url: currentUrl });
    clearInterval(timer);
    if (!r?.ok) {
      running = false; hideProgress();
      showResult(errHtml(r, true, () => { $("smartResult").innerHTML = ""; showActions($("smartActionsRow").outerHTML); runUrl(tool); }));
      return;
    }
    setProgress(100, ""); setTimeout(() => { hideProgress(); renderResult(r.data, tool); window.__eagleLastHash = ""; window.__eagleLoadRecents?.(true); }, 300);
  }

  // ── Run file conversion ──

  async function runFile() {
    if (running || !currentFile || !selectedAction) return;
    if (!checkQuota()) { $("smartQuotaWarn").style.display = ""; return; }
    running = true;
    $("smartActions").style.display = "none";
    const lang = getLang();
    let pct = 5; setProgress(pct, lang === "en" ? "Reading…" : "Читаю файл…");
    const timer = setInterval(() => { pct = Math.min(pct + Math.random() * 7, 88); setProgress(pct); }, 400);
    try {
      const base64 = await new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res(r.result.split(",")[1]);
        r.onerror = () => rej(new Error("file_read_failed"));
        r.readAsDataURL(currentFile);
      });
      setProgress(pct, lang === "en" ? `Uploading ${fmtSize(currentFile.size)}…` : `Загружаю ${fmtSize(currentFile.size)}…`);
      const initData = window.Telegram?.WebApp?.initData || "";
      const headers = { "Content-Type": "application/json" };
      if (initData) headers["X-TG-INITDATA"] = initData;
      const resp = await fetch("/api/convert", { method: "POST", headers, body: JSON.stringify({ action: selectedAction, filename: currentFile.name, mimetype: currentFile.type || "application/octet-stream", data: base64 }) });
      clearInterval(timer);
      if (!resp.ok) { const e = await resp.json().catch(() => ({})); throw new Error(e.detail || tx("conv_error") || "Ошибка конвертации"); }
      const data = await resp.json();
      setProgress(100, "");
      setTimeout(() => { hideProgress(); renderConvResult(data); window.__eagleLastHash = ""; window.__eagleLoadRecents?.(true); }, 300);
    } catch (e) {
      clearInterval(timer);
      running = false;
      hideProgress();
      showResult(errHtml({ error: e?.message || String(e) }, true));
    }
  }

  // ── Render helpers ──

  function renderResult(data, tool) {
    const lang = getLang();
    const ext = tool === "audio" ? ".mp3" : ".mp4";
    const url = data?.download_url || (data?.file_id ? `/api/file/${encodeURIComponent(data.file_id)}` : "");
    const name = (data?.title || data?.filename || data?.file_id || "file").replace(/\.[^.]+$/, "") + ext;
    if (!url) { showResult(errHtml({ error: tx("err_unknown") })); return; }
    showResult(resultHtml(url, name, lang));
    window.__eagleToast?.(tx("done") || "Готово!", "ok", "✅");
  }

  function renderConvResult(data) {
    const lang = getLang();
    const url = data?.download_url || "";
    const name = data?.filename || "file";
    if (!url) { showResult(errHtml({ error: tx("conv_error") || "Ошибка конвертации" })); return; }
    showResult(resultHtml(url, name, lang));
    window.__eagleToast?.(tx("done") || "Готово!", "ok", "✅");
  }

  function resultHtml(url, name, lang) {
    const dlLabel = lang === "en" ? "Download" : "Скачать";
    const shareLabel = lang === "en" ? "Share" : "Поделиться";
    return `<div class="result-file" style="animation:resultIn .28s cubic-bezier(.34,1.56,.64,1) both">
      <div class="result-file__top">
        <div class="result-file__icon"><div class="conv-check-anim">
          <svg viewBox="0 0 48 48" width="36" height="36" fill="none">
            <circle class="cca-circle" cx="24" cy="24" r="20" stroke="#34d399" stroke-width="2.5" stroke-linecap="round"/>
            <polyline class="cca-tick" points="14,24 21,31 34,16" stroke="#34d399" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg></div></div>
        <span class="result-file__name">${esc(name)}</span>
      </div>
      <div class="result-file__actions">
        <button class="btn btn--primary btn--sm" type="button" data-action="open-file" data-url="${esc(url)}" style="flex:1">
          <img src="/static/icons/dl.svg" style="width:14px;height:14px;filter:brightness(10);" /> ${dlLabel}
        </button>
        <button class="btn btn--secondary btn--sm" type="button" data-action="share-file"
          data-url="${esc(url)}" data-title="${esc(name)}">${shareLabel}</button>
      </div>
      <button class="btn btn--secondary" type="button" id="smartResetBtn"
        style="width:100%;margin-top:8px;height:38px;font-size:13px">
        ${lang === "en" ? "Process another" : "Обработать ещё"}
      </button>
    </div>`;
  }

  let _retryFn = null;

  function errHtml(r, showRetry, retryFn) {
    const msg = r?.error || r?.data?.detail || "Ошибка";
    if (showRetry && retryFn) _retryFn = retryFn;
    const retryBtn = showRetry
      ? `<button class="btn btn--secondary btn--sm" id="smartRetryBtn" type="button"
           style="margin-top:8px;width:100%">${getLang() === "en" ? "↺ Retry" : "↺ Повторить"}</button>`
      : "";
    return `<div class="result-file">
      <div class="result-file__top">
        <span class="result-file__icon">⛔</span>
        <span class="result-file__name muted">${esc(msg)}</span>
      </div>${retryBtn}</div>`;
  }

  // ── Init ──

  function init() {
    const drop = $("smartDropzone");
    const fileInput = $("smartFileInput");
    const pasteBtn = $("smartPasteBtn");
    const chipClear = $("smartChipClear");
    const urlInput = $("smartUrlInput");
    const urlClear = $("smartUrlClear");
    if (!drop) return;

    // Click on drop zone → open file picker
    drop.addEventListener("click", e => { if (e.target !== fileInput) fileInput.click(); });

    // File selected
    fileInput.addEventListener("change", () => { if (fileInput.files?.[0]) handleFile(fileInput.files[0]); });

    // Drag & drop
    drop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("drag-over"); });
    drop.addEventListener("dragleave", () => drop.classList.remove("drag-over"));
    drop.addEventListener("drop", e => { e.preventDefault(); drop.classList.remove("drag-over"); if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); });

    // Paste from clipboard
    pasteBtn.addEventListener("click", async () => {
      try {
        const text = await navigator.clipboard.readText();
        if (text && /^https?:\/\//i.test(text.trim())) { handleUrl(text.trim()); return; }
      } catch {}
      // Fallback: show URL input
      $("smartDropzone").style.display = "none";
      $("smartUrlRow").style.display = "";
      urlInput.focus();
    });

    // URL input — detect on paste/input
    urlInput.addEventListener("input", () => {
      const v = urlInput.value.trim();
      if (v && detectUrlType(v)) handleUrl(v);
    });
    urlInput.addEventListener("paste", e => {
      setTimeout(() => {
        const v = urlInput.value.trim();
        if (v && detectUrlType(v)) handleUrl(v);
      }, 50);
    });

    // URL clear
    urlClear.addEventListener("click", () => {
      urlInput.value = "";
      $("smartUrlRow").style.display = "none";
      $("smartDropzone").style.display = "";
    });

    // Chip clear → full reset
    chipClear.addEventListener("click", reset);

    // Delegate reset/retry buttons in result
    document.addEventListener("click", e => {
      if (e.target.closest("#smartResetBtn")) reset();
      if (e.target.closest("#smartRetryBtn")) {
        $("smartResult").innerHTML = "";
        running = false;
        if (_retryFn) { const fn = _retryFn; _retryFn = null; fn(); return; }
        if (mode === "file" && currentFile) handleFile(currentFile);
      }
    });

    // Global paste (when on Home tab)
    document.addEventListener("paste", e => {
      const active = document.querySelector("[data-panel='home'].is-active");
      if (!active) return;
      if (mode !== null) return;
      const text = e.clipboardData?.getData("text") || "";
      if (text && /^https?:\/\//i.test(text.trim())) handleUrl(text.trim());
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.__smartInputReset = reset;
})();
