// app/web/static/app.js
(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function escapeHtml(s) {
    return String(s ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  const t = (k) => window.EagleProfile?.t?.(k) || "";

  // ---------- Toast ----------
  let toastEl = null;
  let toastTimer = null;

  function ensureToast() {
    if (toastEl) return toastEl;
    toastEl = document.createElement("div");
    toastEl.className = "toast";
    toastEl.innerHTML = `
      <div class="toast__inner">
        <div class="toast__icon" id="toastIcon">ℹ️</div>
        <div class="toast__msg" id="toastMsg"></div>
      </div>
    `;
    document.body.appendChild(toastEl);
    return toastEl;
  }

  function toast(msg, kind = "ok", icon = "ℹ️") {
    const el = ensureToast();
    const m = $("#toastMsg", el);
    const ic = $("#toastIcon", el);
    if (m) m.textContent = String(msg ?? "");
    if (ic) ic.textContent = icon;
    el.dataset.kind = kind || "ok";
    el.classList.add("is-on");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("is-on"), 2200);
  }

  // ---------- API ----------
  async function apiGet(path) {
    try {
      const r = await window.EagleAPI?.getJson?.(path);
      if (r && typeof r === "object" && "ok" in r && "data" in r) return r;
      return { ok: true, data: r };
    } catch (e) {
      return { ok: false, error: String(e?.message || e) };
    }
  }

  async function apiPost(path, body) {
    try {
      const r = await window.EagleAPI?.postJson?.(path, body);
      if (r && typeof r === "object" && "ok" in r && "data" in r) return r;
      return { ok: true, data: r };
    } catch (e) {
      return { ok: false, error: String(e?.message || e) };
    }
  }

  async function apiDelete(path) {
    try {
      const r = await window.EagleAPI?.delJson?.(path);
      if (r && typeof r === "object" && "ok" in r && "data" in r) return r;
      return { ok: true, data: r };
    } catch (e) {
      return { ok: false, error: String(e?.message || e) };
    }
  }

  function prettyErr(r) {
    if (!r) return "Unknown error";
    if (r.error) return String(r.error);
    if (r.data && typeof r.data === "object") {
      const d = r.data;
      return d.detail || d.message || JSON.stringify(d);
    }
    return "Request failed";
  }

  // ---------- Indicator math ----------
  function syncIndicator(container, indicator, activeBtn) {
    if (!container || !indicator || !activeBtn) return;
    const cRect = container.getBoundingClientRect();
    const bRect = activeBtn.getBoundingClientRect();
    const left = bRect.left - cRect.left;
    const top = bRect.top - cRect.top;

    indicator.style.left = "0px";
    indicator.style.top = "0px";
    indicator.style.width = `${Math.round(bRect.width)}px`;
    indicator.style.height = `${Math.round(bRect.height)}px`;
    indicator.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`;
  }

  // ---------- Tabs ----------
  const tabsEl = $("#tabs");
  const indEl = $("#tabsIndicator");

  function setTab(name) {
    const btns = $$("[data-tab]");
    const panels = $$("[data-panel]");
    btns.forEach((b) => b.classList.toggle("is-active", b.dataset.tab === name));
    panels.forEach((p) => p.classList.toggle("is-active", p.dataset.panel === name));

    const activeBtn = btns.find((b) => b.dataset.tab === name) || btns[0];
    if (tabsEl && indEl && activeBtn) syncIndicator(tabsEl, indEl, activeBtn);

    if (name === "profile") {
      window.EagleProfile?.renderProfile?.();
      syncAllSegmini();
    }
    if (name === "recent") loadRecents(false);
  }
  window.setTab = setTab;

  function bindTabs() {
    document.addEventListener(
      "click",
      (e) => {
        const btn = e.target.closest("[data-tab]");
        if (!btn) return;
        const name = btn.dataset.tab;
        if (!name) return;
        setTab(name);
      },
      true
    );

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
  function syncAllSegmini() {
    $$(".segmini").forEach(syncSegmini);
  }
  function setSegActive(seg, value) {
    if (!seg) return;
    const btns = $$(".segmini__btn", seg);
    btns.forEach((b) => b.classList.toggle("is-active", b.dataset.value === value));
    syncSegmini(seg);
  }

  // ---------- Settings modal ----------
  const modalEl = () => $("#settingsModal");
  function isModalOpen() {
    return modalEl()?.classList.contains("is-open");
  }

  function openSettings() {
    const m = modalEl();
    if (!m) return;

    const s = window.EagleProfile?.settings || { lang: "ru", theme: "dark" };
    setSegActive($("#langSeg"), s.lang);
    setSegActive($("#themeSeg"), s.theme);

    m.classList.add("is-open");
    m.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");

    requestAnimationFrame(() => syncAllSegmini());
  }

  function closeSettings() {
    const m = modalEl();
    if (!m) return;
    m.classList.remove("is-open");
    m.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
  }

  function getBotUsername() {
    return window.BOT_USERNAME || "EagleToolsBot";
  }

  function openTgLink(url) {
    try {
      if (window.Telegram?.WebApp?.openTelegramLink && url.startsWith("https://t.me/")) {
        window.Telegram.WebApp.openTelegramLink(url);
        return;
      }
      if (window.Telegram?.WebApp?.openLink) {
        window.Telegram.WebApp.openLink(url);
        return;
      }
    } catch {}
    try { window.open(url, "_blank", "noopener"); } catch {}
  }

  // ---------- Tool card helpers ----------
  function getRole(card, role) {
    return card?.querySelector?.(`[data-role="${role}"]`) || null;
  }

  function setProgress(card, v) {
    const bar = getRole(card, "bar");
    const val = Math.max(0, Math.min(100, Number(v || 0)));
    if (bar) bar.style.width = `${val}%`;
    if (card) card.classList.toggle("is-progress", val > 0);
  }

  function setProgressText(card, html) {
    const el = getRole(card, "progress");
    if (el) el.innerHTML = html || "";
  }

  function setResult(card, html) {
    const el = getRole(card, "result");
    if (el) el.innerHTML = html || "";
  }

  function resetCardUi(card) {
    setProgress(card, 0);
    setProgressText(card, "");
    setResult(card, "");
  }

  // ---------- Filename / title helpers (FIX) ----------
  function pickFirstString(...vals) {
    for (const v of vals) {
      if (typeof v === "string" && v.trim()) return v.trim();
    }
    return "";
  }

  function extFromTool(tool) {
    if (tool === "audio") return ".mp3";
    return ".mp4";
  }

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

    const fileId = pickFirstString(data.file_id, out.file_id, data.fileId, out.fileId) || "";

    const downloadUrl =
      pickFirstString(data.download_url, out.download_url, data.url, out.url) ||
      (fileId ? `/api/file/${encodeURIComponent(fileId)}` : "");

    const title = pickFirstString(
      data.title,
      out.title,
      data.filename,
      out.filename,
      meta.title,
      meta.filename
    );

    const displayName = normalizeDisplayName(title || fileId, tool);
    if (!downloadUrl) return null;
    return { fileId, downloadUrl, displayName };
  }

  function safeAutoDownload(url, filename = "") {
    try {
      const a = document.createElement("a");
      a.href = url;
      if (filename) a.download = filename;
      a.rel = "noopener";
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      a.remove();
      return true;
    } catch {
      return false;
    }
  }

  // ---------- Tools run ----------
  let lastHash = "";

  async function runTool(card) {
    const tool = card?.dataset?.tool || "";
    const urlEl = getRole(card, "url");
    const url = (urlEl?.value || "").trim();

    if (!url) {
      toast(t("err_empty_url") || "Paste a link", "warn", "⚠️");
      return;
    }

    resetCardUi(card);
    setProgress(card, 18);
    setProgressText(card, `<span class="muted">${escapeHtml(t("starting") || "Starting…")}</span>`);

    const t0 = performance.now();
    const r = await apiPost(`/api/save_job?tool=${encodeURIComponent(tool)}`, { url });

    if (!r.ok) {
      resetCardUi(card);
      setResult(card, `<span class="muted">${escapeHtml(prettyErr(r))}</span>`);
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
      setProgressText(card, `${escapeHtml(t("done_in") || "Done in")} • ${escapeHtml(secs)}s`);

      setResult(
        card,
        `<a href="${escapeHtml(out.downloadUrl)}" target="_blank" rel="noopener">${escapeHtml(out.displayName)}</a>`
      );

      const ok = safeAutoDownload(out.downloadUrl, out.displayName);
      if (!ok) {
        try { window.open(out.downloadUrl, "_blank", "noopener"); } catch {}
      }

      toast(t("job_created") || "Job created", "ok", "✅");
      return;
    }

    setProgress(card, 0);
    setProgressText(card, "");
    setResult(card, `<span class="muted">${escapeHtml(t("queued") || "Queued")}</span>`);
    toast(t("job_created") || "Job created", "ok", "✅");
  }

  function bindToolRuns() {
    document.addEventListener(
      "click",
      (e) => {
        const btn = e.target.closest("[data-role='run']");
        if (!btn) return;
        const card = btn.closest("[data-tool]");
        if (!card) return;
        runTool(card).catch((err) => toast(String(err?.message || err), "err", "⛔"));
      },
      true
    );
  }

  // ---------- Recents ----------
  function fmtBytes(n) {
    const v = Number(n);
    if (!Number.isFinite(v) || v <= 0) return "";
    const u = ["B", "KB", "MB", "GB", "TB"];
    let i = 0;
    let x = v;
    while (x >= 1024 && i < u.length - 1) { x /= 1024; i++; }
    return `${x.toFixed(i === 0 ? 0 : 1)} ${u[i]}`;
  }

  function fmtWhen(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return "";
      return d.toLocaleString();
    } catch { return ""; }
  }

  function itemTitle(item) {
    const meta = item?.metadata || item?.meta || {};
    return pickFirstString(item?.title, item?.filename, meta?.title, meta?.filename);
  }

  function recentRow(item) {
    const id = item?.id ?? "";
    const kind = String(item?.kind || "SAVE").toUpperCase();
    const status = String(item?.status || "queued").toLowerCase();

    const title = itemTitle(item) || item?.file_id || `#${id}`;
    const when = fmtWhen(item?.created_at);
    const size = fmtBytes(item?.size_bytes);

    const downloadUrl =
      item?.download_url || (item?.file_id ? `/api/file/${encodeURIComponent(item.file_id)}` : "");
    const canDl = !!downloadUrl;

    const badge =
      status === "done" ? "done" :
      status === "failed" || status === "error" ? "err" :
      status === "running" ? "run" : "q";

    return `
      <div class="recentitem" data-id="${escapeHtml(id)}">
        <div class="recentitem__main">
          <div class="recentitem__title">${escapeHtml(title)}</div>
          <div class="recentitem__sub muted">
            <span class="pill pill--${badge}">${escapeHtml(kind)} • ${escapeHtml(status)}</span>
            ${when ? `<span class="dot">•</span><span>${escapeHtml(when)}</span>` : ""}
            ${size ? `<span class="dot">•</span><span>${escapeHtml(size)}</span>` : ""}
          </div>
        </div>

        <div class="recentitem__actions">
          <button class="iconbtn" type="button" data-action="recent-dl" ${canDl ? "" : "disabled"}
            data-url="${escapeHtml(downloadUrl)}" aria-label="Download">⬇️</button>
          <button class="iconbtn" type="button" data-action="recent-copy" ${canDl ? "" : "disabled"}
            data-url="${escapeHtml(downloadUrl)}" aria-label="Copy">📋</button>
          <button class="iconbtn iconbtn--danger" type="button" data-action="recent-del"
            aria-label="Delete">🗑️</button>
        </div>
      </div>
    `;
  }

  function hash(items) {
    try {
      return JSON.stringify(items.map((x) => [x?.id, x?.status, x?.updated_at, x?.file_id, x?.download_url, x?.title]));
    } catch {
      return String(items?.length || 0);
    }
  }

  function renderRecents(items) {
    const list = $("#recentList");
    if (!list) return;
    if (!items || !items.length) {
      list.innerHTML = `<div class="muted small">${escapeHtml(t("recent_empty") || "No jobs yet")}</div>`;
      return;
    }
    list.innerHTML = items.map(recentRow).join("");
  }

  async function loadRecents(silent = true) {
    const r = await apiGet("/api/recent");
    if (!r || !r.ok) {
      if (!silent) toast(prettyErr(r), "err", "⛔");
      return;
    }

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

    if (action === "open-settings") {
      openSettings();
      return;
    }
    if (action === "close-settings") {
      closeSettings();
      return;
    }

    if (action === "open-upgrade") {
      const bot = getBotUsername();
      openTgLink(`https://t.me/${encodeURIComponent(bot)}?start=premium`);
      return;
    }

    if (action === "open-support") {
      const bot = getBotUsername();
      openTgLink(`https://t.me/${encodeURIComponent(bot)}?start=support`);
      return;
    }

    if (action === "open-privacy") {
      const bot = getBotUsername();
      openTgLink(`https://t.me/${encodeURIComponent(bot)}?start=privacy`);
      return;
    }

    if (action === "clear-all") {
      $$("[data-tool]").forEach((card) => {
        const url = getRole(card, "url");
        if (url) url.value = "";
        resetCardUi(card);
      });
      toast(t("cleared") || "Cleared", "ok", "✅");
      return;
    }

    if (action === "lang") {
      const v = el.dataset.value;
      if (v === "ru" || v === "en") {
        window.EagleProfile?.setLang?.(v);
        setSegActive($("#langSeg"), v);
        const a = $("[data-tab].is-active");
        if (a) syncIndicator(tabsEl, indEl, a);
      }
      return;
    }

    if (action === "theme") {
      const v = el.dataset.value;
      if (v === "dark" || v === "light") {
        window.EagleProfile?.setTheme?.(v);
        setSegActive($("#themeSeg"), v);
      }
      return;
    }

    if (action === "copy-ref") {
      const link = window.EagleProfile?.refLink || "";
      if (!link) return toast("—", "warn", "⚠️");
      try { await navigator.clipboard.writeText(link); toast(t("copied") || "Copied", "ok", "✅"); }
      catch { toast("Copy failed", "err", "⛔"); }
      return;
    }

    if (action === "share-ref") {
      const link = window.EagleProfile?.refLink || "";
      if (!link) return toast("—", "warn", "⚠️");
      try {
        if (navigator.share) await navigator.share({ text: link, url: link });
        else await navigator.clipboard.writeText(link);
        toast("OK", "ok", "✅");
      } catch {}
      return;
    }

    if (action === "recent-dl") {
      const url = el.dataset.url || "";
      if (!url) return;
      const ok = safeAutoDownload(url, "");
      if (!ok) {
        try { window.open(url, "_blank", "noopener"); } catch {}
      }
      return;
    }

    if (action === "recent-copy") {
      const url = el.dataset.url || "";
      if (!url) return;
      try { await navigator.clipboard.writeText(url); toast(t("copied") || "Copied", "ok", "✅"); }
      catch { toast("Copy failed", "err", "⛔"); }
      return;
    }

    if (action === "recent-del") {
      const row = el.closest(".recentitem");
      const id = row?.dataset?.id;
      if (!id) return;

      const ok = confirm(t("confirm_delete") || "Delete this item?");
      if (!ok) return;

      row.remove();
      const r = await apiDelete(`/api/recent/${encodeURIComponent(id)}`);
      if (!r.ok) {
        toast(prettyErr(r), "err", "⛔");
        lastHash = "";
        loadRecents(false);
        return;
      }

      toast(t("deleted") || "Deleted", "ok", "✅");
      lastHash = "";
      loadRecents(true);
    }
  }

  function bindGlobalClick() {
    document.addEventListener(
      "click",
      async (e) => {
        const btn = e.target.closest("[data-action]");
        if (!btn) return;
        const action = btn.dataset.action;
        if (!action) return;
        try { await onAction(action, btn); }
        catch (err) { toast(String(err?.message || err), "err", "⛔"); }
      },
      true
    );
  }

  // ---------- Init ----------
  function init() {
    $$("[data-tool]").forEach(resetCardUi);

    bindTabs();
    bindToolRuns();
    bindGlobalClick();

    // close modal on ESC
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && isModalOpen()) closeSettings();
    });

    syncAllSegmini();
    loadRecents(true).catch(() => {});
    window.__EAGLE_APP_READY__ = true;

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