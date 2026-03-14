(function () {
  const API = {};

  function getInitData() {
    try {
      return window.Telegram?.WebApp?.initData || "";
    } catch (_) {
      return "";
    }
  }

  async function safeFetch(url, opts = {}) {
    const headers = new Headers(opts.headers || {});
    const initData = getInitData();
    if (initData) headers.set("X-TG-INITDATA", initData);

    if (opts.json === true) {
      headers.set("Accept", "application/json");
      headers.set("Content-Type", "application/json");
    } else {
      headers.set("Accept", headers.get("Accept") || "application/json");
    }

    const resp = await fetch(url, { ...opts, headers });

    const ct = resp.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      const data = await resp.json().catch(() => null);
      if (!resp.ok) {
        const detail = data?.detail || data?.error || `HTTP_${resp.status}`;
        const err = new Error(detail);
        err.status = resp.status;
        err.data = data;
        throw err;
      }
      return data;
    }

    const text = await resp.text().catch(() => "");
    if (!resp.ok) {
      const err = new Error(text || `HTTP_${resp.status}`);
      err.status = resp.status;
      err.data = text;
      throw err;
    }
    return text;
  }

  API.safeFetch = safeFetch;
  API.getJsonRaw = (path) => safeFetch(path, { method: "GET" });
  API.postJsonRaw = (path, body) =>
    safeFetch(path, { method: "POST", body: JSON.stringify(body || {}), json: true });
  API.delJsonRaw = (path) => safeFetch(path, { method: "DELETE" });

  API.getJson = async (path) => {
    try {
      const data = await API.getJsonRaw(path);
      return { ok: true, data };
    } catch (e) {
      return { ok: false, error: String(e?.message || e), status: e?.status || 0, data: e?.data ?? null };
    }
  };

  API.postJson = async (path, body) => {
    try {
      const data = await API.postJsonRaw(path, body);
      return { ok: true, data };
    } catch (e) {
      return { ok: false, error: String(e?.message || e), status: e?.status || 0, data: e?.data ?? null };
    }
  };

  API.delJson = async (path) => {
    try {
      const data = await API.delJsonRaw(path);
      return { ok: true, data };
    } catch (e) {
      return { ok: false, error: String(e?.message || e), status: e?.status || 0, data: e?.data ?? null };
    }
  };

  // Build download URL from file_id + download_url returned by server
  // If server already returned download_url (with token) — use it directly
  // Otherwise fallback to /api/file/{file_id} (old behavior)
  API.fileUrl = (fileIdOrUrl) => {
    if (!fileIdOrUrl) return "";
    if (fileIdOrUrl.startsWith("/") || fileIdOrUrl.startsWith("http")) return fileIdOrUrl;
    return `/api/file/${encodeURIComponent(fileIdOrUrl)}`;
  };

  API.saveJob = (tool, url) => API.postJson(`/api/save_job?tool=${encodeURIComponent(tool)}`, { url });
  API.getRecent = () => API.getJson("/api/recent");
  API.getProfile = () => API.getJson("/api/profile");
  API.getMe = () => API.getJson("/api/me");

  window.EagleAPI = API;
})();