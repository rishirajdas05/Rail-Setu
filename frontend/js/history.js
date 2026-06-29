// RailHistory: per-user recently viewed trains & recent searches. Needs auth.js.
(function () {
  const BASE = "/api/recent/";
  function authed() { return !!(window.RailAuth && RailAuth.isAuthed()); }

  async function record(item) {
    if (!authed()) return;
    try {
      await fetch(BASE, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...RailAuth.authHeader() },
        body: JSON.stringify(item),
      });
    } catch (e) { /* best-effort */ }
  }

  async function list() {
    if (!authed()) return [];
    try {
      const res = await fetch(BASE, { headers: { ...RailAuth.authHeader() } });
      if (!res.ok) return [];
      return await res.json();
    } catch (e) { return []; }
  }

  async function clear() {
    if (!authed()) return;
    try { await fetch(BASE, { method: "DELETE", headers: { ...RailAuth.authHeader() } }); } catch (e) {}
  }

  window.RailHistory = { record, list, clear, authed };
})();