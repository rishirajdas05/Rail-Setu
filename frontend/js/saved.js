// RailSaved: tiny client for /api/saved/ (saved trains & routes).
// Requires auth.js (RailAuth) to be loaded first.
(function () {
  const BASE = "/api/saved/";

  function authed() {
    return !!(window.RailAuth && RailAuth.isAuthed());
  }

  async function list() {
    if (!authed()) return [];
    try {
      const res = await fetch(BASE, { headers: { ...RailAuth.authHeader() } });
      if (!res.ok) return [];
      return await res.json();
    } catch (e) {
      return [];
    }
  }

  async function add(item) {
    const res = await fetch(BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...RailAuth.authHeader() },
      body: JSON.stringify(item),
    });
    if (!res.ok) throw new Error("save failed");
    return await res.json();
  }

  async function remove(id) {
    const res = await fetch(BASE + id + "/", {
      method: "DELETE",
      headers: { ...RailAuth.authHeader() },
    });
    if (!res.ok && res.status !== 204) throw new Error("remove failed");
  }

  // small internal cache so toggles know current state without refetching
  let cache = null;
  async function ensureCache() {
    if (cache === null) cache = await list();
    return cache;
  }
  function findSaved(kind, key) {
    return (cache || []).find((x) => x.kind === kind && x.key === key);
  }

  // Wire a button to toggle saving `item` ({kind,key,label,subtitle,url}).
  // opts: { labelOn, labelOff } to set button text by state.
  async function wireToggle(btn, item, opts) {
    opts = opts || {};
    if (!btn) return;
    if (!authed()) {
      btn.hidden = true;
      return;
    }
    btn.hidden = false;
    await ensureCache();

    function paint() {
      const s = findSaved(item.kind, item.key);
      btn.classList.toggle("is-saved", !!s);
      btn.setAttribute("aria-pressed", s ? "true" : "false");
      if (opts.labelOn || opts.labelOff) {
        btn.textContent = s ? (opts.labelOn || "Saved") : (opts.labelOff || "Save");
      }
    }
    paint();

    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        const existing = findSaved(item.kind, item.key);
        if (existing) {
          await remove(existing.id);
          cache = cache.filter((x) => x.id !== existing.id);
        } else {
          const created = await add(item);
          cache.push(created);
        }
        paint();
      } catch (e) {
        /* leave state as-is on failure */
      }
      btn.disabled = false;
    });
  }

  window.RailSaved = { list, add, remove, wireToggle, ensureCache };
})();