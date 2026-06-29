// RailSetu admin analytics dashboard. Staff only.
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const loading = $("dash-loading");
  const errorEl = $("dash-error");
  const body = $("dash-body");

  const C = { blue: "#2f5fd0", amber: "#e08a1e", green: "#1f9d57", grey: "#9aa4b8", violet: "#7b61ff" };

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function inr(n) { return "\u20b9" + Number(n || 0).toLocaleString("en-IN"); }

  function showError(msg) {
    loading.hidden = true;
    body.hidden = true;
    errorEl.textContent = msg;
    errorEl.hidden = false;
  }

  // ---- bar chart with gridlines, gradient bars, value labels ----
  function barChart(items, color) {
    const w = 760, h = 240, padL = 34, padR = 12, padT = 18, padB = 34;
    const innerW = w - padL - padR, innerH = h - padT - padB;
    const max = Math.max.apply(null, items.map((i) => i.value).concat([1]));
    const niceMax = niceCeil(max);
    const n = items.length || 1;
    const slot = innerW / n, bw = Math.min(54, slot * 0.5);
    const gid = "g" + Math.random().toString(36).slice(2, 7);

    let grid = "";
    const lines = 4;
    for (let i = 0; i <= lines; i++) {
      const y = padT + (innerH * i) / lines;
      const val = Math.round(niceMax * (1 - i / lines));
      grid += `<line x1="${padL}" y1="${y.toFixed(1)}" x2="${w - padR}" y2="${y.toFixed(1)}" class="bc-grid"/>`;
      grid += `<text x="${padL - 8}" y="${(y + 3).toFixed(1)}" class="bc-axis" text-anchor="end">${val}</text>`;
    }
    let bars = "";
    items.forEach((it, i) => {
      const bh = (it.value / niceMax) * innerH;
      const x = padL + i * slot + (slot - bw) / 2;
      const y = padT + innerH - bh;
      bars += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(0, bh).toFixed(1)}" rx="5" fill="url(#${gid})"/>`;
      if (it.value > 0)
        bars += `<text x="${(x + bw / 2).toFixed(1)}" y="${(y - 6).toFixed(1)}" class="bc-val" text-anchor="middle">${esc(it.display != null ? it.display : it.value)}</text>`;
      bars += `<text x="${(x + bw / 2).toFixed(1)}" y="${h - 12}" class="bc-x" text-anchor="middle">${esc(it.label)}</text>`;
    });
    return `<svg viewBox="0 0 ${w} ${h}" class="bc2" preserveAspectRatio="xMidYMid meet">
      <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="${color}" stop-opacity="0.95"/>
        <stop offset="1" stop-color="${color}" stop-opacity="0.55"/>
      </linearGradient></defs>${grid}${bars}</svg>`;
  }

  function niceCeil(v) {
    if (v <= 5) return 5;
    const mag = Math.pow(10, Math.floor(Math.log10(v)));
    return Math.ceil(v / mag) * mag;
  }

  // ---- donut chart with legend ----
  function donut(segments) {
    const total = segments.reduce((s, x) => s + x.value, 0);
    const cx = 80, cy = 80, r = 58, sw = 24, circ = 2 * Math.PI * r;
    let arcs = "", offset = 0;
    if (total > 0) {
      segments.forEach((s) => {
        if (s.value <= 0) return;
        const len = (s.value / total) * circ;
        arcs += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${s.color}" stroke-width="${sw}"
          stroke-dasharray="${len.toFixed(2)} ${(circ - len).toFixed(2)}" stroke-dashoffset="${(-offset).toFixed(2)}"
          transform="rotate(-90 ${cx} ${cy})"/>`;
        offset += len;
      });
    } else {
      arcs = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#eef1f6" stroke-width="${sw}"/>`;
    }
    const legend = segments
      .map((s) => {
        const pct = total ? Math.round((s.value / total) * 100) : 0;
        return `<div class="dn-leg"><span class="dn-dot" style="background:${s.color}"></span>
          <span class="dn-lbl">${esc(s.label)}</span>
          <span class="dn-val">${esc(s.value)} <small>${pct}%</small></span></div>`;
      })
      .join("");
    return `<div class="dn-wrap">
      <svg viewBox="0 0 160 160" class="dn-svg">${arcs}
        <text x="80" y="74" text-anchor="middle" class="dn-total">${total}</text>
        <text x="80" y="94" text-anchor="middle" class="dn-cap">bookings</text>
      </svg>
      <div class="dn-legend">${legend}</div>
    </div>`;
  }

  function rankList(host, rows, valueFmt) {
    if (!rows || !rows.length) { host.innerHTML = `<p class="dash-empty">No data yet.</p>`; return; }
    const max = Math.max.apply(null, rows.map((r) => r.count).concat([1]));
    host.innerHTML = rows
      .map((r, i) => {
        const pct = Math.round((r.count / max) * 100);
        return `<div class="dl-row">
          <span class="dl-rank">${i + 1}</span>
          <span class="dl-label">${esc(r.label)}</span>
          <span class="dl-bar"><span style="width:${pct}%"></span></span>
          <span class="dl-val">${esc(valueFmt ? valueFmt(r.count) : r.count)}</span>
        </div>`;
      })
      .join("");
  }

  const ICONS = {
    book: '<path d="M4 5a2 2 0 0 1 2-2h9l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z"/><path d="M15 3v5h5"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    rupee: '<path d="M6 4h12M6 8h12M16 4c0 4-3 6-7 6h-1l7 8"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  };

  function statCard(c) {
    return `<div class="dash-stat" style="--accent:${c.color}">
      <span class="dash-stat-ico"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${c.icon}</svg></span>
      <span class="dash-stat-num">${esc(c.n)}</span>
      <span class="dash-stat-lbl">${esc(c.l)}</span>
    </div>`;
  }

  function render(d) {
    const b = d.bookings;
    $("dash-cards").innerHTML = [
      { n: b.total, l: "Total bookings", color: C.blue, icon: ICONS.book },
      { n: b.confirmed, l: "Confirmed", color: C.green, icon: ICONS.check },
      { n: inr(b.revenue), l: "Revenue (excl. cancelled)", color: C.amber, icon: ICONS.rupee },
      { n: d.searches.total, l: "Searches", color: C.violet, icon: ICONS.search },
    ].map(statCard).join("");

    $("dash-last7").innerHTML = barChart(
      b.last7.map((x) => ({ label: x.day.split(" ")[0], value: x.count })), C.blue);

    $("dash-status").innerHTML = donut([
      { label: "Confirmed", value: b.confirmed, color: C.green },
      { label: "RAC", value: b.rac, color: C.blue },
      { label: "Waitlisted", value: b.waitlisted, color: C.amber },
      { label: "Cancelled", value: b.cancelled, color: C.grey },
    ]);

    $("dash-byclass").innerHTML = b.by_class.length
      ? barChart(b.by_class.map((x) => ({ label: x.travel_class, value: x.count })), C.amber)
      : `<p class="dash-empty">No bookings yet.</p>`;

    rankList($("dash-routes"), b.top_routes.map((r) => ({ label: r.route, count: r.count })));
    rankList($("dash-searches"), d.searches.top.map((r) => ({ label: r.route, count: r.count })));

    const mu = d.model_usage;
    const muMax = Math.max.apply(null, mu.map((m) => m.count).concat([1]));
    $("dash-models").innerHTML = mu
      .map((m) => `<div class="mu-card">
        <div class="mu-top"><span class="mu-name">${esc(m.model)}</span><span class="mu-count">${esc(m.count)}</span></div>
        <div class="mu-bar"><span style="width:${Math.round((m.count / muMax) * 100)}%"></span></div>
      </div>`)
      .join("");

    $("dash-sub").textContent = `Updated ${new Date().toLocaleString("en-IN", { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" })}`;
    loading.hidden = true;
    errorEl.hidden = true;
    body.hidden = false;
    $("dash-refresh").hidden = false;
  }

  async function load() {
    const res = await fetch("/api/analytics/", { headers: { ...RailAuth.authHeader() } });
    if (res.status === 403) return showError("This dashboard is for staff accounts only.");
    if (!res.ok) return showError("Could not load analytics. Is the server running?");
    render(await res.json());
  }

  async function init() {
    if (!window.RailAuth || !RailAuth.isAuthed()) {
      location.href = "/login/?next=" + encodeURIComponent("/dashboard/");
      return;
    }
    try {
      const meRes = await fetch("/api/auth/me/", { headers: { ...RailAuth.authHeader() } });
      if (meRes.status === 401) {
        location.href = "/login/?next=" + encodeURIComponent("/dashboard/");
        return;
      }
      const me = await meRes.json();
      if (!me.is_staff) {
        showError("This dashboard is for staff accounts only. Sign in with a staff or superuser account to view analytics.");
        return;
      }
      await load();
    } catch (e) {
      showError("Could not load analytics. Is the server running?");
    }
  }

  const rb = $("dash-refresh");
  if (rb) rb.addEventListener("click", async () => {
    rb.disabled = true;
    try { await load(); } catch (e) {}
    rb.disabled = false;
  });

  init();
})();