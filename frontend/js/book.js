// RailSetu booking page.
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
  const GENDERS = [["M", "Male"], ["F", "Female"], ["O", "Other"]];

  const loading = $("bk-loading");
  const errorEl = $("bk-error");
  const formWrap = $("bk-form-wrap");
  const summaryEl = $("bk-summary");
  const paxEl = $("bk-pax");
  const formError = $("bk-form-error");
  const submit = $("bk-submit");
  const resultEl = $("bk-result");

  // ---- read journey context from the URL ----
  const q = new URLSearchParams(location.search);
  const ctx = {
    train: (q.get("train") || "").trim(),
    from: (q.get("from") || "").trim().toUpperCase(),
    to: (q.get("to") || "").trim().toUpperCase(),
    date: q.get("date") || "",
  };

  // ---- must be signed in ----
  if (!window.RailAuth || !RailAuth.isAuthed()) {
    location.href = "/login/?next=" + encodeURIComponent(location.pathname + location.search);
    return;
  }

  function fail(msg) {
    loading.hidden = true;
    errorEl.textContent = msg;
    errorEl.hidden = false;
  }

  function fillSelect(sel, pairs) {
    sel.innerHTML = pairs.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join("");
  }

  function paxRow(i) {
    const wrap = document.createElement("div");
    wrap.className = "bk-pax-row";
    wrap.innerHTML = `
      <input type="text" class="px-name" placeholder="Full name" maxlength="80" aria-label="Passenger name">
      <input type="number" class="px-age" placeholder="Age" min="1" max="120" aria-label="Age">
      <select class="px-gender" aria-label="Gender">
        ${GENDERS.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join("")}
      </select>
      <button type="button" class="px-del" aria-label="Remove passenger">&times;</button>
    `;
    wrap.querySelector(".px-del").addEventListener("click", () => {
      if (paxEl.children.length > 1) wrap.remove();
    });
    return wrap;
  }

  function addPax() {
    if (paxEl.children.length >= 6) {
      formError.textContent = "A booking can have at most 6 passengers.";
      return;
    }
    formError.textContent = "";
    paxEl.appendChild(paxRow());
  }

  function collectPassengers() {
    const rows = [...paxEl.querySelectorAll(".bk-pax-row")];
    const out = [];
    for (const r of rows) {
      const name = r.querySelector(".px-name").value.trim();
      const age = parseInt(r.querySelector(".px-age").value, 10);
      const gender = r.querySelector(".px-gender").value;
      if (!name || !age) return { error: "Fill in every passenger's name and age." };
      if (age < 1 || age > 120) return { error: "Passenger age must be between 1 and 120." };
      out.push({ name, age, gender });
    }
    if (!out.length) return { error: "Add at least one passenger." };
    return { passengers: out };
  }

  function statusPill(s, label) {
    const cls = s === "CNF" ? "ok" : s === "RAC" ? "warn" : s === "WL" ? "wait" : "cancel";
    return `<span class="pill ${cls}">${esc(label || s)}</span>`;
  }

  function renderResult(b) {
    formWrap.hidden = true;
    const pax = (b.passengers || []).map((p, i) => `
      <tr>
        <td>${i + 1}. ${esc(p.name)}</td>
        <td>${esc(p.coach || "—")}</td>
        <td>${esc(p.berth || "—")}</td>
        <td>${statusPill(p.status, p.status_display)}</td>
      </tr>`).join("");

    resultEl.innerHTML = `
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
          ${esc(b.from_code)} → ${esc(b.to_code)} · ${esc(b.journey_date)} · ${esc(b.travel_class)} · ₹${esc(b.total_fare)}
        </p>
        <table class="bk-pax-table">
          <thead><tr><th>Passenger</th><th>Coach</th><th>Berth</th><th>Status</th></tr></thead>
          <tbody>${pax}</tbody>
        </table>
        ${b.email_sent_to ? `<p class="bk-emailed">A confirmation has been emailed to ${esc(b.email_sent_to)}.</p>` : ""}
        <div class="bk-confirm-actions">
          <button type="button" class="bk-ticket" data-pnr="${esc(b.pnr)}">Download e-ticket</button>
          <a class="bk-link" href="/status/?train=${encodeURIComponent(b.train_number)}&start_day=1">Live status</a>
          <a class="bk-link" href="/">Book another</a>
        </div>
      </div>`;
    resultEl.hidden = false;
    const tbtn = resultEl.querySelector(".bk-ticket");
    if (tbtn) tbtn.addEventListener("click", () => downloadTicket(tbtn.dataset.pnr, tbtn));
    maybePredict(b);
    resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
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

  async function downloadTicket(pnr, btn) {
    const original = btn ? btn.textContent : "";
    if (btn) { btn.disabled = true; btn.textContent = "Preparing..."; }
    try {
      const res = await fetch(`/api/bookings/${encodeURIComponent(pnr)}/ticket/`, {
        headers: authHeader(),
      });
      if (!res.ok) throw new Error("ticket");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `RailSetu-${pnr}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      if (btn) btn.textContent = "Could not download";
    } finally {
      if (btn) { btn.disabled = false; setTimeout(() => { btn.textContent = original; }, 1500); }
    }
  }

  async function maybePredict(b) {
    const host = resultEl.querySelector(".bk-confirm");
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
          travel_class: b.travel_class, quota: b.quota,
          waitlist_position: wl, journey_date: b.journey_date,
        }),
      });
      const data = await res.json();
      if (!res.ok) return; // service offline -> just skip quietly
      const div = document.createElement("div");
      div.className = "bk-predict";
      div.innerHTML = `<h3 class="bk-predict-h">Confirmation chance · WL ${wl}</h3>${gaugeHTML(data)}`;
      host.appendChild(div);
    } catch (e) { /* skip on error */ }
  }

  function firstError(data, fallback) {
    if (!data || typeof data !== "object") return fallback;
    if (typeof data.detail === "string") return data.detail;
    for (const k of Object.keys(data)) {
      const v = data[k];
      if (Array.isArray(v) && v.length) return typeof v[0] === "string" ? v[0] : `${k}: invalid`;
      if (typeof v === "string") return v;
    }
    return fallback;
  }

  async function submitBooking(e) {
    e.preventDefault();
    formError.textContent = "";
    const got = collectPassengers();
    if (got.error) { formError.textContent = got.error; return; }

    const body = {
      train: ctx.train,
      from_station: ctx.from,
      to_station: ctx.to,
      journey_date: $("bk-date").value,
      travel_class: $("bk-class").value,
      quota: $("bk-quota").value,
      passengers: got.passengers,
    };

    submit.disabled = true;
    submit.textContent = "Booking…";
    try {
      const res = await fetch("/api/bookings/", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...RailAuth.authHeader() },
        body: JSON.stringify(body),
      });
      if (res.status === 401) {
        location.href = "/login/?next=" + encodeURIComponent(location.pathname + location.search);
        return;
      }
      const data = await res.json();
      if (!res.ok) {
        formError.textContent = firstError(data, "Could not complete the booking.");
        submit.disabled = false;
        submit.textContent = "Confirm booking";
        return;
      }
      renderResult(data);
    } catch (err) {
      formError.textContent = "Network error. Is the server running?";
      submit.disabled = false;
      submit.textContent = "Confirm booking";
    }
  }

  // ---- compact station autocomplete for the manual entry form ----
  function attachAuto(input, list) {
    let items = [], code = "", t;
    const close = () => { list.classList.remove("open"); list.innerHTML = ""; };
    const pick = (i) => {
      const s = items[i];
      if (!s) return;
      input.value = `${s.name} (${s.code})`;
      code = s.code;
      close();
    };
    input.addEventListener("input", () => {
      code = "";
      const query = input.value.trim();
      clearTimeout(t);
      if (query.length < 2) return close();
      t = setTimeout(async () => {
        try {
          const res = await fetch(`/api/stations/?q=${encodeURIComponent(query)}`);
          if (!res.ok) return close();
          items = await res.json();
          if (!items.length) return close();
          list.innerHTML = items.map((s, i) =>
            `<li role="option" data-i="${i}"><span><span class="s-name">${esc(s.name)}</span>` +
            `<span class="s-sub"> ${esc(s.state || "")}</span></span>` +
            `<span class="s-code">${esc(s.code)}</span></li>`).join("");
          list.classList.add("open");
        } catch (e) { close(); }
      }, 180);
    });
    list.addEventListener("mousedown", (e) => {
      const li = e.target.closest("li[data-i]");
      if (li) pick(parseInt(li.dataset.i, 10));
    });
    return { code: () => code || input.value.trim().toUpperCase() };
  }

  function showEntry() {
    loading.hidden = true;
    $("bk-entry").hidden = false;
    const trainIn = $("en-train");
    if (ctx.train) trainIn.value = ctx.train;
    const fromA = attachAuto($("en-from"), $("en-from-suggest"));
    const toA = attachAuto($("en-to"), $("en-to-suggest"));
    if (ctx.from) $("en-from").value = ctx.from;
    if (ctx.to) $("en-to").value = ctx.to;
    $("bk-entry-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const err = $("bk-entry-error");
      const train = trainIn.value.replace(/\D/g, "").slice(0, 6);
      const from = fromA.code();
      const to = toA.code();
      if (train.length < 4) { err.textContent = "Enter a valid train number."; return; }
      if (!from || !to) { err.textContent = "Choose both the from and to stations."; return; }
      if (from === to) { err.textContent = "From and to stations must be different."; return; }
      const qp = new URLSearchParams({ train, from, to });
      if (ctx.date) qp.set("date", ctx.date);
      location.href = "/book/?" + qp.toString();
    });
  }

  async function init() {
    if (!ctx.train || !ctx.from || !ctx.to) {
      return showEntry();
    }
    // fetch the train for its name and to validate the stations are on the route
    let train;
    try {
      const res = await fetch(`/api/trains/${encodeURIComponent(ctx.train)}/`);
      if (!res.ok) return fail(`Train ${ctx.train} was not found.`);
      train = await res.json();
    } catch (e) {
      return fail("Could not load the train. Is the server running?");
    }

    const stops = train.stops || [];
    const findStop = (c) => stops.find((s) => s.station_code === c);
    const fromStop = findStop(ctx.from);
    const toStop = findStop(ctx.to);

    summaryEl.innerHTML = `
      <h1 class="bk-title">${esc(train.number)} · ${esc(train.name)}</h1>
      <p class="bk-route">
        <strong>${esc((fromStop && fromStop.station_name) || ctx.from)}</strong> (${esc(ctx.from)})
        <span class="arrow">→</span>
        <strong>${esc((toStop && toStop.station_name) || ctx.to)}</strong> (${esc(ctx.to)})
      </p>`;

    // Populate the class dropdown with only the classes this train actually
    // offers (a Shatabdi has CC/EC, not SL/3A). Availability is the source of truth.
    let classPairs = CLASSES;
    try {
      const ar = await fetch(
        `/api/availability/?train=${encodeURIComponent(ctx.train)}` +
        `&from=${encodeURIComponent(ctx.from)}&to=${encodeURIComponent(ctx.to)}`
      );
      if (ar.ok) {
        const ad = await ar.json();
        const valid = (ad.classes || []).map((c) => [c.travel_class, c.class_name]);
        if (valid.length) classPairs = valid;
      }
    } catch (e) { /* fall back to the full list */ }

    fillSelect($("bk-class"), classPairs);
    fillSelect($("bk-quota"), QUOTAS);

    const today = new Date().toISOString().slice(0, 10);
    const dateInput = $("bk-date");
    dateInput.min = today;
    dateInput.value = ctx.date && ctx.date >= today ? ctx.date : today;

    addPax(); // start with one passenger
    $("bk-add").addEventListener("click", addPax);
    $("bk-form").addEventListener("submit", submitBooking);

    loading.hidden = true;
    formWrap.hidden = false;
  }

  init();
})();