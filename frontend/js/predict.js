// RailSetu confirmation predictor (standalone page).
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  const CLASSES = [
    ["SL", "Sleeper"], ["3A", "AC 3 Tier"], ["2A", "AC 2 Tier"],
    ["1A", "AC First Class"], ["CC", "AC Chair Car"], ["2S", "Second Sitting"],
  ];
  const QUOTAS = [["GN", "General"], ["TQ", "Tatkal"], ["LD", "Ladies"], ["SS", "Senior Citizen"]];

  const form = $("pr-form");
  const errorEl = $("pr-error");
  const wrap = $("pr-result");
  const loading = $("pr-loading");
  const empty = $("pr-empty");
  const card = $("pr-card");

  const show = (el) => (el.hidden = false);
  const hide = (el) => (el.hidden = true);

  function fill(sel, pairs) {
    sel.innerHTML = pairs.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join("");
  }
  fill($("pr-class"), CLASSES);
  fill($("pr-quota"), QUOTAS);

  // default date ~30 days out
  const d = new Date();
  d.setDate(d.getDate() + 30);
  $("pr-date").value = d.toISOString().slice(0, 10);
  $("pr-date").min = new Date().toISOString().slice(0, 10);

  // shared gauge markup used here and on the booking page
  window.renderConfirmGauge = function (r) {
    const pct = r.percent;
    const bandClass = r.band === "High" ? "is-ontime" : r.band === "Moderate" ? "is-late" : "is-early";
    const barColor = r.band === "High" ? "var(--green)" : r.band === "Moderate" ? "var(--amber-ink)" : "var(--red)";
    return `
      <div class="pr-gauge ${bandClass}">
        <div class="pr-num"><span class="pr-pct">${pct}<small>%</small></span>
          <span class="pr-band">${esc(r.band)} chance</span></div>
        <div class="pr-track"><span style="width:${pct}%;background:${barColor}"></span></div>
        <p class="pr-verdict">Predicted: <strong>${esc(r.prediction)}</strong></p>
        ${r.inputs ? `<p class="pr-inputs">${esc(r.inputs.travel_class)} · ${esc(r.inputs.quota)} · WL ${esc(r.inputs.waitlist_position)} · ${esc(r.inputs.days_to_journey)} days out</p>` : ""}
        <p class="pr-note">${esc(r.disclaimer || "")}</p>
      </div>`;
  };

  async function predict() {
    const wl = parseInt($("pr-wl").value, 10);
    if (!wl || wl < 1) { errorEl.textContent = "Enter a waitlist number."; errorEl.style.display = "block"; return; }
    errorEl.textContent = "";
    show(wrap); hide(card); hide(empty); show(loading);

    const body = {
      travel_class: $("pr-class").value,
      quota: $("pr-quota").value,
      waitlist_position: wl,
      journey_date: $("pr-date").value,
    };
    try {
      const res = await fetch("/api/predict/confirmation/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.status === 503) {
        hide(loading); empty.textContent = data.detail || "Prediction service is offline."; show(empty); return;
      }
      if (!res.ok) {
        hide(loading); empty.textContent = data.detail || "Could not get a prediction."; show(empty); return;
      }
      card.innerHTML = window.renderConfirmGauge(data);
      hide(loading); hide(empty); show(card);
    } catch (e) {
      hide(loading); empty.textContent = "Network error reaching the server."; show(empty);
    }
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); predict(); });
})();