// RailAlerts: client for /api/alerts/ (price & seat alerts). Needs auth.js first.
(function () {
  const BASE = "/api/alerts/";
  function authed() { return !!(window.RailAuth && RailAuth.isAuthed()); }

  async function list() {
    if (!authed()) return [];
    try {
      const res = await fetch(BASE, { headers: { ...RailAuth.authHeader() } });
      if (!res.ok) return [];
      return await res.json();
    } catch (e) { return []; }
  }

  async function create(payload) {
    const res = await fetch(BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...RailAuth.authHeader() },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Could not create the alert.");
    return data;
  }

  async function remove(id) {
    const res = await fetch(BASE + id + "/", { method: "DELETE", headers: { ...RailAuth.authHeader() } });
    if (!res.ok && res.status !== 204) throw new Error("remove failed");
  }

  window.RailAlerts = { list, create, remove, authed };
})();