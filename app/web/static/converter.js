/* ============================================================
   EagleTools — Smart File Converter
   Умный детект типа файла + матрица доступных действий
   ============================================================ */
(function () {
  "use strict";

  /* ── Матрица: тип файла → доступные действия ── */
  const ACTION_MAP = {
    video: [
      { id: "video_to_mp3",  icon: '<img src="/static/icons/fmt-mp3.svg" style="width:20px;height:20px;display:block;" />',      name: "→ MP3",  desc_ru: "Извлечь аудио",       desc_en: "Extract audio",        color: "#7c3aed" },
      { id: "video_to_mp4",  icon: '<img src="/static/icons/fmt-mp4.svg" style="width:20px;height:20px;display:block;" />',      name: "→ MP4",  desc_ru: "Конвертировать",       desc_en: "Convert video",        color: "#e8195a" },
      { id: "video_to_gif",  icon: '<img src="/static/icons/fmt-gif.svg" style="width:20px;height:20px;display:block;" />',      name: "→ GIF",  desc_ru: "Сделать гифку",        desc_en: "Make GIF",             color: "#059669" },
      { id: "video_compress",icon: '<img src="/static/icons/fmt-compress.svg" style="width:20px;height:20px;display:block;" />', name: "Сжать",  desc_ru: "Уменьшить размер",     desc_en: "Compress size",        color: "#d97706" },
      { id: "video_to_m4a",  icon: '<img src="/static/icons/fmt-mp3.svg" style="width:20px;height:20px;display:block;" />',      name: "→ M4A",  desc_ru: "Аудио M4A",            desc_en: "Audio M4A",            color: "#7c3aed" },
      { id: "video_stt",     icon: '<img src="/static/icons/fmt-text.svg" style="width:20px;height:20px;display:block;" />',     name: "→ Текст",desc_ru: "Распознать речь",      desc_en: "Speech to text",       color: "#0891b2" },
    ],
    audio: [
      { id: "audio_to_mp3",  icon: '<img src="/static/icons/fmt-mp3.svg" style="width:20px;height:20px;display:block;" />',      name: "→ MP3",  desc_ru: "Конвертировать",       desc_en: "Convert",              color: "#e8195a" },
      { id: "audio_to_wav",  icon: '<img src="/static/icons/fmt-wav.svg" style="width:20px;height:20px;display:block;" />',      name: "→ WAV",  desc_ru: "Несжатый формат",      desc_en: "Lossless format",      color: "#7c3aed" },
      { id: "audio_to_ogg",  icon: '<img src="/static/icons/fmt-wav.svg" style="width:20px;height:20px;display:block;" />',      name: "→ OGG",  desc_ru: "Открытый формат",      desc_en: "Open format",          color: "#059669" },
      { id: "audio_to_m4a",  icon: '<img src="/static/icons/fmt-mp3.svg" style="width:20px;height:20px;display:block;" />',      name: "→ M4A",  desc_ru: "Для Apple устройств",  desc_en: "For Apple devices",    color: "#6366f1" },
      { id: "audio_compress",icon: '<img src="/static/icons/fmt-compress.svg" style="width:20px;height:20px;display:block;" />', name: "Сжать",  desc_ru: "Уменьшить размер",     desc_en: "Compress size",        color: "#d97706" },
      { id: "audio_stt",     icon: '<img src="/static/icons/fmt-text.svg" style="width:20px;height:20px;display:block;" />',     name: "→ Текст",desc_ru: "Распознать речь",      desc_en: "Speech to text",       color: "#0891b2" },
    ],
    image: [
      { id: "img_to_jpg",    icon: '<img src="/static/icons/fmt-jpg.svg" style="width:20px;height:20px;display:block;" />',      name: "→ JPG",  desc_ru: "Универсальный формат", desc_en: "Universal format",     color: "#e8195a" },
      { id: "img_to_png",    icon: '<img src="/static/icons/fmt-png.svg" style="width:20px;height:20px;display:block;" />',      name: "→ PNG",  desc_ru: "С прозрачностью",      desc_en: "With transparency",    color: "#7c3aed" },
      { id: "img_to_webp",   icon: '<img src="/static/icons/fmt-webp.svg" style="width:20px;height:20px;display:block;" />',     name: "→ WebP", desc_ru: "Для веба",             desc_en: "For web",              color: "#059669" },
      { id: "img_compress",  icon: '<img src="/static/icons/fmt-compress.svg" style="width:20px;height:20px;display:block;" />', name: "Сжать",  desc_ru: "Уменьшить файл",       desc_en: "Reduce size",          color: "#d97706" },
    ],
    pdf: [
      { id: "pdf_to_txt",    icon: '<img src="/static/icons/fmt-text.svg" style="width:20px;height:20px;display:block;" />',     name: "→ Текст",desc_ru: "Извлечь текст",        desc_en: "Extract text",         color: "#e8195a" },
      { id: "pdf_to_img",    icon: '<img src="/static/icons/fmt-png.svg" style="width:20px;height:20px;display:block;" />',      name: "→ Фото", desc_ru: "Страницы как картинки",desc_en: "Pages as images",      color: "#7c3aed" },
      { id: "pdf_compress",  icon: '<img src="/static/icons/fmt-compress.svg" style="width:20px;height:20px;display:block;" />', name: "Сжать",  desc_ru: "Уменьшить файл",       desc_en: "Reduce size",          color: "#d97706" },
    ],
    document: [
      { id: "doc_to_pdf",    icon: '<img src="/static/icons/fmt-pdf.svg" style="width:20px;height:20px;display:block;" />',      name: "→ PDF",  desc_ru: "Конвертировать в PDF", desc_en: "Convert to PDF",       color: "#e8195a" },
      { id: "doc_to_txt",    icon: '<img src="/static/icons/fmt-text.svg" style="width:20px;height:20px;display:block;" />',     name: "→ Текст",desc_ru: "Извлечь текст",        desc_en: "Extract text",         color: "#059669" },
    ],
  };

  /* ── Определение типа файла по MIME и расширению ── */
  const VIDEO_EXT  = ["mp4","mkv","mov","avi","webm","flv","wmv","m4v","3gp","ts"];
  const AUDIO_EXT  = ["mp3","wav","flac","ogg","opus","m4a","aac","wma","aiff"];
  const IMAGE_EXT  = ["jpg","jpeg","png","gif","webp","heic","heif","bmp","tiff","tif","svg","avif"];
  const PDF_EXT    = ["pdf"];
  const DOC_EXT    = ["doc","docx","xls","xlsx","ppt","pptx","odt","ods","odp","rtf","txt","csv"];

  function detectType(file) {
    const mime = (file.type || "").toLowerCase();
    const ext  = (file.name || "").split(".").pop().toLowerCase();

    if (mime.startsWith("video/")  || VIDEO_EXT.includes(ext))  return "video";
    if (mime.startsWith("audio/")  || AUDIO_EXT.includes(ext))  return "audio";
    if (mime.startsWith("image/")  || IMAGE_EXT.includes(ext))  return "image";
    if (mime === "application/pdf" || PDF_EXT.includes(ext))    return "pdf";
    if (DOC_EXT.includes(ext))                                   return "document";
    /* Fallback: если mime содержит image — считаем картинкой */
    if (mime.includes("image"))  return "image";
    if (mime.includes("video"))  return "video";
    if (mime.includes("audio"))  return "audio";
    return null;
  }

  /* ── Эмодзи по типу ── */
  const TYPE_EMOJI = { video: "🎬", audio: "🎵", image: "🖼", pdf: "📑", document: "📄" };
  const TYPE_COLOR = {
    video:    "rgba(232,25,90,.12)",
    audio:    "rgba(124,58,237,.12)",
    image:    "rgba(5,150,105,.12)",
    pdf:      "rgba(217,119,6,.12)",
    document: "rgba(99,102,241,.12)",
  };

  /* ── Форматирование размера файла ── */
  function fmtSize(bytes) {
    if (!bytes) return "";
    if (bytes < 1024)        return bytes + " B";
    if (bytes < 1024*1024)   return (bytes/1024).toFixed(1) + " KB";
    return (bytes/1024/1024).toFixed(1) + " MB";
  }

  /* ── Язык ── */
  function getLang() {
    try {
      const l = document.documentElement.lang;
      if (l === "en") return "en";
    } catch {}
    return "ru";
  }

  function tx(key) {
    return window.EagleProfile?.t?.(key) || FALLBACK[key] || key;
  }

  const FALLBACK = {
    conv_choose_action: "Что сделать с файлом",
    conv_btn_run:       "Конвертировать",
    conv_processing:    "Обрабатываю…",
    conv_done:          "Готово",
    conv_error:         "Ошибка конвертации",
    conv_unsupported:   "Формат не поддерживается",
    conv_too_big:       "Файл слишком большой (макс. 100 МБ)",
    conv_select_action: "Выбери действие",
  };

  const MAX_SYNC_FREE    = 15  * 1024 * 1024;  // 15 MB
  const MAX_SYNC_PREMIUM = 50  * 1024 * 1024;  // 50 MB
  const MAX_SIZE_FREE    = 100 * 1024 * 1024;  // 100 MB
  const MAX_SIZE_PREMIUM = 500 * 1024 * 1024;  // 500 MB

  /* ── State ── */
  let selectedFile   = null;
  let selectedAction = null;
  let fileType       = null;

  /* ── DOM refs ── */
  const $ = (id) => document.getElementById(id);

  /* ── Инициализация ── */
  function init() {
    const drop      = $("convDrop");
    const fileInput = $("convFileInput");
    const fileClear = $("convFileClear");
    const runBtn    = $("convRunBtn");

    if (!drop) return;

    /* Клик на дроп-зону */
    drop.addEventListener("click", (e) => {
      if (e.target !== fileInput) fileInput.click();
    });

    /* Выбор файла */
    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files[0]) handleFile(fileInput.files[0]);
    });

    /* Drag & Drop */
    drop.addEventListener("dragover",  (e) => { e.preventDefault(); drop.classList.add("drag-over"); });
    drop.addEventListener("dragleave", ()  => { drop.classList.remove("drag-over"); });
    drop.addEventListener("drop",      (e) => {
      e.preventDefault(); drop.classList.remove("drag-over");
      if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
    });

    /* Сброс файла */
    fileClear.addEventListener("click", resetConverter);

    /* Запуск конвертации */
    runBtn.addEventListener("click", runConversion);
  }

  /* ── Обработка выбранного файла ── */
  function handleFile(file) {
    var isPremium = false;
    try { isPremium = !!(window.EagleProfile && window.EagleProfile.isPremium && window.EagleProfile.isPremium()); } catch(e) {}
    const maxSize = isPremium ? MAX_SIZE_PREMIUM : MAX_SIZE_FREE;

    if (file.size > maxSize) {
      showToast(tx("conv_too_big"), "err");
      return;
    }

    selectedFile   = file;
    selectedAction = null;
    fileType       = detectType(file);

    /* Превью файла */
    $("convDrop").style.display     = "none";
    $("convFile").classList.add("visible");
    $("convFileName").textContent   = file.name;
    $("convFileSize").textContent   = fmtSize(file.size);
    /* SVG иконка вместо эмодзи */
    const thumbIcons = {
      video:    "/static/icons/fmt-video.svg",
      audio:    "/static/icons/fmt-mp3.svg",
      image:    "/static/icons/fmt-png.svg",
      pdf:      "/static/icons/fmt-pdf.svg",
      document: "/static/icons/file-doc.svg",
    };
    const thumbSrc = thumbIcons[fileType] || "/static/icons/file-doc.svg";
    const thumbEl  = $("convFileThumb");
    thumbEl.innerHTML = `<img src="${thumbSrc}" style="width:22px;height:22px;display:block;" />`;
    thumbEl.style.background = TYPE_COLOR[fileType] || "var(--surface2)";

    /* Список действий */
    if (!fileType) {
      showUnsupported();
      return;
    }

    try {
      renderActions(fileType);
    } catch(err) {
      showError("Ошибка отображения: " + err.message);
    }
  }

  /* ── Рендер кнопок действий ── */
  function renderActions(type) {
    var rawExt = selectedFile ? selectedFile.name.split(".").pop().toLowerCase() : "";
    /* jpg и jpeg — одно и то же */
    const inputExt  = rawExt === "jpeg" ? "jpg" : rawExt;
    const allActions = ACTION_MAP[type] || [];
    /* Скрываем если выходной формат совпадает со входным */
    const actions = allActions.filter(a => {
      const parts = a.id.split("_to_");
      if (parts.length < 2) return true;
      var outExt = parts[parts.length - 1];
      if (outExt === "jpeg") outExt = "jpg";
      return outExt !== inputExt;
    });
    const lang    = getLang();
    const grid    = $("convActionGrid");

    grid.innerHTML = actions.map(a => `
      <div class="conv-action" data-action-id="${a.id}" style="--ac:${a.color}">
        <div class="conv-action__icon" style="background:${a.color}22;display:flex;align-items:center;justify-content:center;">${a.icon}</div>
        <div class="conv-action__text">
          <div class="conv-action__name">${a.name}</div>
          <div class="conv-action__desc">${lang === "en" ? a.desc_en : a.desc_ru}</div>
        </div>
      </div>
    `).join("");

    /* Клик по действию */
    grid.querySelectorAll(".conv-action").forEach(el => {
      el.addEventListener("click", () => {
        grid.querySelectorAll(".conv-action").forEach(e => e.classList.remove("selected"));
        el.classList.add("selected");
        selectedAction = el.dataset.actionId;
        $("convRunWrap").classList.add("visible");
        /* Обновить текст кнопки */
        const action = actions.find(a => a.id === selectedAction);
        if (action) {
          $("convRunLabel").textContent = (lang === "en" ? "Convert " : "Конвертировать ") + action.name;
        }
      });
    });

    $("convActions").classList.add("visible");
    /* Скрываем кнопку пока не выбрано действие */
    $("convRunWrap").classList.remove("visible");
    /* Если только одно действие — выбираем его автоматически */
    if (actions.length === 1) {
      const onlyAction = grid.querySelector(".conv-action");
      if (onlyAction) {
        onlyAction.classList.add("selected");
        selectedAction = onlyAction.dataset.actionId;
        const a = actions[0];
        $("convRunLabel").textContent = (getLang() === "en" ? "Convert " : "Конвертировать ") + a.name;
        $("convRunWrap").classList.add("visible");
      }
    }
  }

  /* ── Неподдерживаемый формат ── */
  function showUnsupported() {
    $("convActions").classList.remove("visible");
    $("convRunWrap").classList.remove("visible");
    const grid = $("convActionGrid");
    grid.innerHTML = `<div style="grid-column:1/-1;padding:12px 0;text-align:center;font-size:13px;color:var(--text3)">${tx("conv_unsupported")}</div>`;
    $("convActions").classList.add("visible");
  }

  /* ── Запуск конвертации ── */
  async function runConversion() {
    if (!selectedFile || !selectedAction) {
      showToast(tx("conv_select_action"), "warn");
      return;
    }

    /* UI → loading state */
    $("convActions").classList.remove("visible");
    $("convRunWrap").classList.remove("visible");
    $("convResult").innerHTML = "";
    $("convResult").style.display = "none";

    const prog = $("convProgress");
    prog.classList.add("visible", "is-running");
    $("convProgressFill").style.width = "0%";
    $("convProgressText").textContent = tx("conv_processing");

    /* Анимированный прогресс */
    let fakeProgress = 0;
    const progInterval = setInterval(() => {
      fakeProgress = Math.min(fakeProgress + Math.random() * 8, 88);
      $("convProgressFill").style.width = fakeProgress + "%";
    }, 400);

    try {
      /* Читаем файл как base64 */
      $("convProgressText").textContent = (getLang() === "en" ? "Reading " : "Читаю ") + fmtSize(selectedFile.size) + "…";

      const base64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload  = () => resolve(reader.result.split(",")[1]);
        reader.onerror = () => reject(new Error("file_read_failed"));
        reader.readAsDataURL(selectedFile);
      });

      $("convProgressText").textContent = (getLang() === "en" ? "Uploading " : "Загружаю ") + fmtSize(selectedFile.size) + "…";

      const initData = window.Telegram?.WebApp?.initData || "";
      const headers  = { "Content-Type": "application/json" };
      if (initData) headers["X-TG-INITDATA"] = initData;

      const bodyObj = {
        action:   selectedAction,
        filename: selectedFile.name,
        mimetype: selectedFile.type || "application/octet-stream",
        data:     base64,
      };
      const body = JSON.stringify(bodyObj);

      let resp;
      try {
        resp = await fetch("/api/convert", { method: "POST", headers, body });
      } catch(fetchErr) {
        throw new Error("fetch failed: " + fetchErr.message + " (body size: " + body.length + ")");
      }

      clearInterval(progInterval);
      $("convProgressFill").style.width = "100%";
      prog.classList.remove("is-running");

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        const detail = err.detail || tx("conv_error");
        throw new Error(detail);
      }

      const data = await resp.json();
      setTimeout(() => {
        prog.classList.remove("visible");
        showResult(data);
      }, 400);

    } catch (e) {
      clearInterval(progInterval);
      prog.classList.remove("visible", "is-running");
      /* Показываем детальную ошибку для диагностики */
      var errType = e ? e.constructor.name : "unknown";
      var errMsg  = (e && e.message) ? e.message : "no message";
      var msg = errType + ": " + errMsg;
      showError(msg);
    }
  }

  /* ── Показать результат ── */
  function showResult(data) {
    const lang       = getLang();
    const result     = $("convResult");
    const dlLabel    = lang === "en" ? "Download" : "Скачать";
    const shareLabel = lang === "en" ? "Share"    : "Поделиться";
    const url        = data.download_url || "";
    const fname      = data.filename || "file";

    result.style.display = "block";
    result.innerHTML = `
      <div class="result-file" style="animation: resultIn .28s cubic-bezier(.34,1.56,.64,1) both">
        <div class="result-file__top">
          <div class="result-file__icon">
            <div class="conv-check-anim">
              <svg viewBox="0 0 48 48" width="44" height="44" fill="none">
                <circle class="cca-circle" cx="24" cy="24" r="20" stroke="#34d399" stroke-width="2.5" stroke-linecap="round"/>
                <polyline class="cca-tick" points="14,24 21,31 34,16" stroke="#34d399" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
          </div>
          <div class="result-file__name">${escHtml(fname)}</div>
        </div>
        <div class="result-file__actions">
          <button class="btn btn--primary" id="convDlBtn" style="flex:1">
            <img src="/static/icons/dl.svg" class="icon" style="width:16px;height:16px;filter:brightness(10);" />
            ${dlLabel}
          </button>
          <button class="btn btn--secondary" id="convShareBtn">
            <img src="/static/icons/share-2.svg" class="icon" style="width:16px;height:16px" />
            ${shareLabel}
          </button>
        </div>
      </div>
    `;

    /* Скачивание — открываем полный URL через Telegram или напрямую */
    /* Добавляем имя файла как query param для красивого скачивания */
    const baseUrl  = url.startsWith("http") ? url : (window.location.origin + url);
    const fullUrl  = baseUrl + (baseUrl.includes("?") ? "&" : "?") + "name=" + encodeURIComponent(fname);
    document.getElementById("convDlBtn").onclick = function() {
      /* Используем ту же функцию что и recent — openFile из app.js */
      if (typeof window.__eagleOpenFile === "function") {
        window.__eagleOpenFile(fullUrl);
      } else {
        var full = fullUrl.startsWith("http") ? fullUrl : window.location.origin + fullUrl;
        try { if (window.Telegram?.WebApp?.openLink) { window.Telegram.WebApp.openLink(full); return; } } catch {}
        try { window.open(full, "_blank", "noopener"); } catch {}
      }
    };
    document.getElementById("convShareBtn").onclick = function() {
      window.__eagleShare(fullUrl, fname);
    };

    /* Кнопка сбросить */
    const resetBtn = document.createElement("button");
    resetBtn.className = "btn btn--secondary";
    resetBtn.style.cssText = "width:100%;margin-top:8px;";
    resetBtn.textContent = lang === "en" ? "Convert another file" : "Конвертировать ещё";
    resetBtn.onclick = resetConverter;
    result.appendChild(resetBtn);
  }

  /* ── Показать ошибку — красивый автотост ── */
  function showError(msg) {
    /* Убираем старый тост если есть */
    var old = document.getElementById("convErrToast");
    if (old) old.remove();

    var toast = document.createElement("div");
    toast.id = "convErrToast";
    toast.style.cssText = [
      "position:fixed",
      "bottom:24px",
      "left:50%",
      "transform:translateX(-50%) translateY(0)",
      "background:var(--bg3,#16131f)",
      "border:1px solid rgba(248,113,113,.3)",
      "border-radius:14px",
      "padding:12px 18px",
      "font-size:13px",
      "color:var(--err,#f87171)",
      "z-index:9999",
      "max-width:calc(100vw - 32px)",
      "text-align:center",
      "box-shadow:0 8px 28px rgba(0,0,0,.44)",
      "transition:opacity .4s ease, transform .4s ease",
      "pointer-events:none",
    ].join(";");
    toast.textContent = "⚠️ " + msg;

    document.body.appendChild(toast);

    /* Анимация появления */
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        toast.style.opacity = "1";
      });
    });

    /* Автоисчезновение через 3.5 сек */
    setTimeout(function() {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(-50%) translateY(12px)";
      setTimeout(function() { toast.remove(); }, 420);
    }, 3500);

    /* Восстанавливаем кнопки */
    $("convActions").classList.add("visible");
    $("convRunWrap").classList.add("visible");
  }

  /* ── Сброс состояния ── */
  function resetConverter() {
    selectedFile   = null;
    selectedAction = null;
    fileType       = null;

    $("convFileInput").value       = "";
    $("convDrop").style.display    = "";
    $("convFile").classList.remove("visible");
    $("convActions").classList.remove("visible");
    $("convRunWrap").classList.remove("visible");
    $("convProgress").classList.remove("visible", "is-running");
    $("convProgressFill").style.width = "0%";
    $("convResult").innerHTML      = "";
    $("convResult").style.display  = "none";
    $("convActionGrid").innerHTML  = "";
  }

  /* ── Helpers ── */
  function escHtml(s) {
    return String(s || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  }

  function showToast(msg, type) {
    if (typeof window.__eagleToast === "function") { window.__eagleToast(msg, type); return; }
    /* fallback — не используем alert, просто показываем в UI */
    if (type === "err" || type === "warn") showError(msg);
  }

  /* Share helper */
  window.__eagleShare = async function(url, title) {
    const full = url.startsWith("http") ? url : window.location.origin + url;
    /* Сначала пробуем нативный share sheet */
    if (navigator.share) {
      try { await navigator.share({ url: full, title: title || "EagleTools" }); return; } catch(e) {
        /* Если отменили — не делаем ничего, если ошибка — копируем */
        if (e.name === "AbortError") return;
      }
    }
    /* Fallback — копируем ссылку */
    try {
      await navigator.clipboard.writeText(full);
      if (typeof window.__eagleToast === "function") window.__eagleToast("Ссылка скопирована", "ok");
    } catch {
      /* последний fallback */
      const inp = document.createElement("input");
      inp.value = full; document.body.appendChild(inp);
      inp.select(); document.execCommand("copy"); inp.remove();
      if (typeof window.__eagleToast === "function") window.__eagleToast("Ссылка скопирована", "ok");
    }
  };

  /* ── Запуск после DOMContentLoaded ── */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();