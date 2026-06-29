// RailSetu Check PNR page.
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  const form = $("pnr-form");
  const input = $("pnr-input");
  const errorEl = $("pnr-error");
  const wrap = $("pnr-result");
  const loading = $("pnr-loading");
  const empty = $("pnr-empty");
  const card = $("pnr-card");

  // prefill from ?pnr= so results are shareable
  const q = new URLSearchParams(location.search);
  if (q.get("pnr")) input.value = q.get("pnr").replace(/\D/g, "").slice(0, 10);

  const show = (el) => (el.hidden = false);
  const hide = (el) => (el.hidden = true);

  function statusPill(s, label) {
    const cls = s === "CNF" ? "ok" : s === "RAC" ? "warn" : s === "WL" ? "wait" : "cancel";
    return `<span class="pill ${cls}">${esc(label || s)}</span>`;
  }

  function render(b) {
    const rows = (b.passengers || []).map((p) => `
      <tr>
        <td>Passenger ${p.passenger}</td>
        <td>${esc(p.coach || "—")}</td>
        <td>${esc(p.berth || "—")}</td>
        <td>${statusPill(p.status, p.status_display)}</td>
      </tr>`).join("");

    card.innerHTML = `
      <div class="bk-confirm">
        <div class="bk-confirm-top">
          <div>
            <span class="bk-pnr-label">PNR</span>
            <span class="bk-pnr">${esc(b.pnr)}</span>
          </div>
          ${statusPill(b.status, b.status_display)}
        </div>
        <p class="bk-confirm-route">
          ${esc(b.train_number)} · ${esc(b.train_name)}<br>
          ${esc(b.from_code)} → ${esc(b.to_code)} · ${esc(b.journey_date)} · ${esc(b.travel_class)}
        </p>
        <table class="bk-pax-table">
          <thead><tr><th>Passenger</th><th>Coach</th><th>Berth</th><th>Status</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
        <div class="bk-confirm-actions">
          <a class="bk-link" href="/status/?train=${encodeURIComponent(b.train_number)}&start_day=1">Live status</a>
        </div>
      </div>`;
    hide(loading);
    hide(empty);
    show(card);
  }

  function wlPosition(b) {
    let mx = 0;
    (b.passengers || []).forEach((p) => {
      const m = /WL\/(\d+)/.exec(p.booked_status || "");
      if (m) mx = Math.max(mx, parseInt(m[1], 10));
    });
    return mx;
  }

  function gaugeHTML(r) {
    const band = r.band;
    const color = band === "High" ? "var(--green)" : band === "Moderate" ? "var(--amber-ink)" : "var(--red)";
    return `
      <div class="pr-gauge">
        <div class="pr-num"><span class="pr-pct">${r.percent}<small>%</small></span>
          <span class="pr-band">${esc(band)} chance</span></div>
        <div class="pr-track"><span style="width:${r.percent}%;background:${color}"></span></div>
        <p class="pr-verdict">Predicted: <strong>${esc(r.prediction)}</strong></p>
        <p class="pr-note">${esc(r.disclaimer || "")}</p>
      </div>`;
  }

  async function maybePredict(b) {
    const host = card.querySelector(".bk-confirm");
    if (!host) return;

    if (b.status === "RAC") {
      const div = document.createElement("div");
      div.className = "bk-predict";
      div.innerHTML = `<h3 class="bk-predict-h">Confirmation chance</h3>
        <p class="pr-note">RAC tickets are past the waitlist and usually get a berth before departure.</p>`;
      host.appendChild(div);
      return;
    }
    if (b.status !== "WL") return;
    const wl = wlPosition(b);
    if (!wl) return;

    try {
      const res = await fetch("/api/predict/confirmation/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          travel_class: b.travel_class,
          quota: b.quota || "GN",
          waitlist_position: wl,
          journey_date: b.journey_date,
        }),
      });
      const data = await res.json();
      if (!res.ok) return; // ML service offline -> skip quietly
      const div = document.createElement("div");
      div.className = "bk-predict";
      div.innerHTML = `<h3 class="bk-predict-h">Confirmation chance · WL ${wl}</h3>${gaugeHTML(data)}`;
      host.appendChild(div);
    } catch (e) { /* skip on error */ }
  }

  async function check() {
    const pnr = input.value.replace(/\D/g, "").slice(0, 10);
    if (pnr.length !== 10) {
      errorEl.textContent = "A PNR is 10 digits.";
      errorEl.style.display = "block";
      return;
    }
    errorEl.textContent = "";
    show(wrap);
    hide(card);
    hide(empty);
    show(loading);
    history.replaceState(null, "", `/pnr/?pnr=${pnr}`);

    try {
      const res = await fetch(`/api/pnr/${pnr}/`);
      if (res.status === 404) {
        hide(loading);
        empty.textContent = "No booking found for that PNR.";
        show(empty);
        return;
      }
      const data = await res.json();
      render(data);
      maybePredict(data);
    } catch (e) {
      hide(loading);
      empty.textContent = "Network error reaching the server.";
      show(empty);
    }
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); check(); });

  if (input.value.length === 10) check();
})();