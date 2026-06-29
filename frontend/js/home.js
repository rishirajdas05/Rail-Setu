// RailSetu homepage hub: popular routes + per-user recently viewed / searches.
// Hidden automatically when a search is active (from/to in the URL).
(function () {
  "use strict";

  const hub = document.getElementById("home-hub");
  if (!hub) return;

  const qp = new URLSearchParams(location.search);
  if (qp.get("from") && qp.get("to")) { hub.hidden = true; return; }

  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const ROUTES = [
    { from: "NDLS", to: "CSTM", label: "New Delhi → Mumbai" },
    { from: "NDLS", to: "GWL", label: "New Delhi → Gwalior" },
    { from: "NDLS", to: "BPL", label: "New Delhi → Bhopal" },
    { from: "HWH", to: "NDLS", label: "Howrah → New Delhi" },
    { from: "BCT", to: "ADI", label: "Mumbai → Ahmedabad" },
    { from: "MAS", to: "SBC", label: "Chennai → Bengaluru" },
  ];

  const chip = (href, text) => `<a class="hub-chip" href="${href}">${text}</a>`;

  function popularBlock() {
    const chips = ROUTES.map((r) =>
      chip(`/?from=${encodeURIComponent(r.from)}&to=${encodeURIComponent(r.to)}`, esc(r.label))
    ).join("");
    return `<div class="hub-block"><h3 class="hub-h" data-i18n="hub.popular">Popular routes</h3><div class="hub-chips">${chips}</div></div>`;
  }

  function guestRecentBlock() {
    let views = [];
    try { views = JSON.parse(localStorage.getItem("railsetu_recent_views") || "[]"); } catch (_) {}
    if (!views.length) return "";
    const chips = views
      .map((v) => chip(`/train/${encodeURIComponent(v.num)}/`,
        `${esc(v.num)}${v.name ? ` &middot; ${esc(v.name)}` : ""}`))
      .join("");
    return `<div class="hub-block"><h3 class="hub-h" data-i18n="hub.recent_trains">Recently viewed</h3><div class="hub-chips">${chips}</div></div>`;
  }

  function render(blocks) {
    hub.innerHTML = blocks.filter(Boolean).join("");
    hub.hidden = false;
    if (window.RailI18n) RailI18n.refresh();
  }

  // baseline (works for guests and as a fast first paint)
  render([popularBlock(), guestRecentBlock()]);

  // signed-in: replace the local "recently viewed" with server-backed history
  if (window.RailHistory && RailHistory.authed()) {
    RailHistory.list().then((items) => {
      const trains = items.filter((i) => i.kind === "train");
      const routes = items.filter((i) => i.kind === "route");
      const blocks = [popularBlock()];
      if (trains.length) {
        blocks.push(`<div class="hub-block"><h3 class="hub-h" data-i18n="hub.recent_trains">Recently viewed</h3>
          <div class="hub-chips">${trains.map((t) => chip(esc(t.url), esc(t.label))).join("")}</div></div>`);
      }
      if (routes.length) {
        blocks.push(`<div class="hub-block"><h3 class="hub-h" data-i18n="hub.recent_searches">Recent searches</h3>
          <div class="hub-chips">${routes.map((r) => chip(esc(r.url), esc(r.label))).join("")}</div></div>`);
      }
      if (trains.length || routes.length) {
        blocks.push(`<div class="hub-foot"><button type="button" class="hub-clear" id="hub-clear" data-i18n="hub.clear">Clear history</button></div>`);
      }
      render(blocks);
      const cl = document.getElementById("hub-clear");
      if (cl) cl.addEventListener("click", async () => {
        cl.disabled = true;
        await RailHistory.clear();
        render([popularBlock()]);
      });
    });
  }
})();