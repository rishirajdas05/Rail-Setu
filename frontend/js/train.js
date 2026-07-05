// RailSetu train detail page. Reads the train number from the URL path.
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const loading = $("td-loading");
  const errorEl = $("td-error");
  const card = $("td-card");

  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  const hhmm = (t) => (t ? String(t).slice(0, 5) : "—");

  const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  let stopProgress = []; // 0..1 fraction along the route per stop, by time

  // Pull the train number out of /train/<number>/
  function trainNumber() {
    const m = location.pathname.match(/\/train\/([^/]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function renderDays(runsOn) {
    // runs_on is a 7-char string like "1111111" for Mon..Sun
    const bits = (runsOn || "").padEnd(7, "0").slice(0, 7);
    return DAYS.map((d, i) => {
      const on = bits[i] === "1";
      return `<span class="day-chip ${on ? "on" : "off"}">${d}</span>`;
    }).join("");
  }

  function stopRow(s, i, isFirst, isLast) {
    const kind = isFirst ? "is-src" : isLast ? "is-dst" : "";
    return `
      <li class="td-stop ${kind}">
        <span class="td-dot" aria-hidden="true"></span>
        <div class="td-stn">
          <span class="td-stn-name">${esc(s.station_name)}</span>
          <span class="td-stn-code">${esc(s.station_code)}${s.platform ? ` &middot; PF ${esc(s.platform)}` : ""}</span>
        </div>
        <span class="num td-arr">${hhmm(s.arrival)}</span>
        <span class="num td-dep">${hhmm(s.departure)}</span>
        <span class="num td-day">${s.day || 1}</span>
        <span class="num td-edelay" data-i="${i}">·</span>
      </li>`;
  }

  function renderCoach(d, bFrom) {
    const host = $("td-coach");
    if (!host || !Array.isArray(d.coach_layout) || !d.coach_layout.length) return;
    const stops = d.stops || [];
    const board = stops.find((s) => s.station_code === bFrom) || stops[0];
    const plat = board ? board.platform : "—";
    const boardName = board ? board.station_name : "";

    const boxes = [`<div class="cz-coach cz-engine" title="Engine">ENG</div>`]
      .concat(
        d.coach_layout.map((c) => {
          const cl = c.cls ? `cz-${esc(c.cls)}` : "cz-util";
          return `<div class="cz-coach ${cl}" title="${esc(c.name)}">${esc(c.code)}</div>`;
        })
      )
      .join("");

    const present = [...new Set(d.coach_layout.filter((c) => c.cls).map((c) => c.cls))];
    const legend = present
      .map((cl) => `<span class="cz-leg"><i class="cz-sw cz-${esc(cl)}"></i>${esc(cl)}</span>`)
      .join("");

    host.innerHTML = `
      <div class="td-sec-head">Coach position</div>
      <p class="cz-board">Boarding at <strong>${esc(boardName)}</strong> &middot; Platform <strong>${esc(plat)}</strong> <span class="cz-ind">indicative</span></p>
      <div class="cz-strip">${boxes}</div>
      <div class="cz-legend">${legend}</div>
      <p class="cz-note">Indicative platform and coach order from a demonstration model; actual position may vary on the day.</p>`;
    host.hidden = false;
  }

  function render(d) {
    $("td-number").textContent = d.number;
    $("td-name").textContent = d.name;
    $("td-route").textContent =
      `${d.source_name} (${d.source_code}) → ${d.destination_name} (${d.destination_code})`;
    document.title = `${d.number} ${d.name} · RailSetu`;

    // remember this train for the homepage "recently viewed" strip
    try {
      const KEY = "railsetu_recent_views";
      let r = JSON.parse(localStorage.getItem(KEY) || "[]").filter((x) => x.num !== d.number);
      r.unshift({ num: d.number, name: d.name });
      localStorage.setItem(KEY, JSON.stringify(r.slice(0, 6)));
    } catch (_) {}

    if (d.train_type) {
      const tt = $("td-type");
      tt.textContent = d.train_type;
      tt.hidden = false;
    }

    $("td-days").innerHTML = renderDays(d.runs_on);

    const stops = d.stops || [];
    $("td-stops").innerHTML = stops
      .map((s, i) => stopRow(s, i, i === 0, i === stops.length - 1))
      .join("");

    // fraction along the route for each stop, by scheduled time
    const toMin = (s) => {
      const t = s.arrival || s.departure;
      if (!t) return null;
      const [h, m] = String(t).split(":");
      return ((s.day || 1) - 1) * 1440 + (+h) * 60 + (+m);
    };
    const mins = stops.map(toMin);
    const t0 = mins.find((x) => x != null);
    let tN = null;
    for (let i = mins.length - 1; i >= 0; i--) { if (mins[i] != null) { tN = mins[i]; break; } }
    let span = (tN != null && t0 != null) ? tN - t0 : 0;
    if (span <= 0) span = 1;
    stopProgress = mins.map((x) => (x == null ? null : Math.min(1, Math.max(0, (x - t0) / span))));

    // wire the "Live status" button to the status page for this train
    $("td-live").addEventListener("click", () => {
      location.href = `/status/?train=${encodeURIComponent(d.number)}&start_day=1`;
    });

    const pdfBtn = $("td-pdf");
    if (pdfBtn) {
      pdfBtn.addEventListener("click", () => {
        window.location.href = `/api/trains/${encodeURIComponent(d.number)}/schedule/`;
      });
    }

    // wire the "Book" button, carrying journey context if we have it
    const params = new URLSearchParams(location.search);
    const bFrom = params.get("from") || d.source_code;
    const bTo = params.get("to") || d.destination_code;
    const bDate = params.get("date") || "";
    const bookBtn = $("td-book");
    bookBtn.hidden = false;
    bookBtn.addEventListener("click", () => {
      const qp = new URLSearchParams({ train: d.number, from: bFrom, to: bTo });
      if (bDate) qp.set("date", bDate);
      location.href = "/book/?" + qp.toString();
    });

    loading.hidden = true;
    errorEl.hidden = true;
    card.hidden = false;

    renderCoach(d, bFrom);
    loadDelay(d.number, bDate);
    loadDelayTrend(d.number);
    loadAvail(d.number, bDate, bFrom, bTo, "GN");
    loadWeek(d.number, bDate, bFrom, bTo);

    if (window.RailSaved) {
      RailSaved.wireToggle(
        $("td-save"),
        {
          kind: "train",
          key: String(d.number),
          label: `${d.number} · ${d.name}`,
          subtitle: `${d.source_code} → ${d.destination_code}`,
          url: location.pathname + location.search,
        },
        { labelOn: "★ Saved", labelOff: "☆ Save" }
      );
    }

    setupAlertPanel(d, bFrom, bTo, bDate);

    if (window.RailHistory) {
      RailHistory.record({
        kind: "train",
        key: String(d.number),
        label: `${d.number} · ${d.name}`,
        subtitle: `${d.source_code} → ${d.destination_code}`,
        url: `/train/${encodeURIComponent(d.number)}/`,
      });
    }

    const qbox = $("td-quota");
    if (qbox) {
      qbox.querySelectorAll(".td-quota-btn").forEach((b) =>
        b.addEventListener("click", () => {
          qbox.querySelectorAll(".td-quota-btn").forEach((x) => x.classList.toggle("is-on", x === b));
          loadAvail(d.number, bDate, bFrom, bTo, b.dataset.q);
        })
      );
    }
  }

  async function loadDelay(number, date) {
    const host = $("td-delay");
    if (!host) return;
    try {
      const url = `/api/predict/delay/?train=${encodeURIComponent(number)}` +
        (date ? `&date=${encodeURIComponent(date)}` : "");
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok) return; // ML service offline / no estimate -> skip quietly
      const band = data.band || "";
      const cls = band === "Likely on time" ? "is-ontime" : band === "Minor delay" ? "is-late" : "is-major";
      host.className = `td-delay ${cls}`;
      host.innerHTML = `
        <div class="td-delay-label">Predicted arrival delay</div>
        <div class="td-delay-main">
          <span class="td-delay-min">~${data.predicted_delay_min} min</span>
          <span class="td-delay-band">${esc(band)}</span>
        </div>
        <div class="td-delay-sub">likely ${data.range_min[0]}–${data.range_min[1]} min · model trained on synthetic data</div>`;
      host.hidden = false;

      // spread the predicted delay across the route as an estimate per station
      const total = data.predicted_delay_min;
      document.querySelectorAll(".td-edelay").forEach((cell) => {
        const p = stopProgress[+cell.dataset.i];
        if (p == null) { cell.textContent = "·"; return; }
        const est = Math.round((total * Math.pow(p, 0.9)) / 5) * 5;
        cell.textContent = est <= 0 ? "—" : "+" + est;
        cell.classList.remove("mid", "hi");
        if (est >= 45) cell.classList.add("hi");
        else if (est >= 15) cell.classList.add("mid");
      });
    } catch (e) { /* skip */ }
  }

  async function loadAvail(number, date, from, to, quota) {
    const host = $("td-avail");
    if (!host) return;
    try {
      const url = `/api/availability/?train=${encodeURIComponent(number)}` +
        (date ? `&date=${encodeURIComponent(date)}` : "") +
        (from ? `&from=${encodeURIComponent(from)}` : "") +
        (to ? `&to=${encodeURIComponent(to)}` : "") +
        (quota ? `&quota=${encodeURIComponent(quota)}` : "");
      const res = await fetch(url);
      const d = await res.json();
      if (!res.ok || !d.classes || !d.classes.length) return;
      const cards = d.classes.map((c) => {
        const chance = c.chance != null ? `<span class="av-chance">${c.chance}% chance</span>` : "";
        return `
          <div class="av-card is-${esc(c.status_type)}">
            <div class="av-top">
              <span class="av-cls">${esc(c.travel_class)}</span>
              <span class="av-fare">₹${esc(c.fare)}</span>
            </div>
            <div class="av-name">${esc(c.class_name)}</div>
            <div class="av-status">${esc(c.status)}</div>
            ${chance}
          </div>`;
      }).join("");
      host.innerHTML = `
        <div class="av-head">Seat availability <span class="av-date">${esc(d.date)}</span></div>
        <div class="av-grid">${cards}</div>
        <p class="av-note">${esc(d.disclaimer)}</p>`;
      host.hidden = false;
      const qbox = $("td-quota");
      if (qbox) qbox.hidden = false;
      renderFareTrend(d.classes);
      populateAlertClasses(d.classes);
    } catch (e) { /* skip */ }
  }

  // ---- Trends (mini bar charts) ----
  function barChartSVG(items, barClass) {
    const w = 320, h = 130;
    const padB = 24, padT = 16, padX = 6;
    const max = Math.max.apply(null, items.map((i) => i.value).concat([1]));
    const n = items.length || 1;
    const slot = (w - padX * 2) / n;
    const bw = slot * 0.6;
    const chartH = h - padT - padB;
    let svg = "";
    items.forEach((it, i) => {
      const bh = Math.max(2, (it.value / max) * chartH);
      const x = padX + i * slot + (slot - bw) / 2;
      const y = padT + chartH - bh;
      svg += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${bh.toFixed(1)}" rx="3" class="bc-bar ${barClass}"></rect>`;
      svg += `<text x="${(x + bw / 2).toFixed(1)}" y="${h - 8}" class="bc-xlbl" text-anchor="middle">${esc(it.label)}</text>`;
      svg += `<text x="${(x + bw / 2).toFixed(1)}" y="${(y - 3).toFixed(1)}" class="bc-vlbl" text-anchor="middle">${esc(it.display)}</text>`;
    });
    return `<svg viewBox="0 0 ${w} ${h}" class="bc-svg" preserveAspectRatio="xMidYMid meet">${svg}</svg>`;
  }

  function renderFareTrend(classes) {
    const host = $("td-trend-fare");
    if (!host || !classes || !classes.length) return;
    const items = classes.map((c) => ({
      label: c.travel_class,
      value: +c.fare || 0,
      display: "\u20b9" + c.fare,
    }));
    host.innerHTML = `<div class="tr-h">Fare by class</div>` + barChartSVG(items, "is-fare");
    $("td-trends").hidden = false;
  }

  async function loadDelayTrend(number) {
    const host = $("td-trend-delay");
    if (!host) return;
    const dow = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const dates = [];
    const today = new Date();
    for (let i = 0; i < 7; i++) {
      const dt = new Date(today);
      dt.setDate(today.getDate() + i);
      dates.push(dt);
    }
    try {
      const results = await Promise.all(
        dates.map((dt) => {
          const ds = dt.toISOString().slice(0, 10);
          return fetch(`/api/predict/delay/?train=${encodeURIComponent(number)}&date=${ds}`)
            .then((r) => (r.ok ? r.json() : null))
            .catch(() => null);
        })
      );
      const items = results.map((data, i) => ({
        label: dow[dates[i].getDay()],
        value: data ? data.predicted_delay_min : 0,
        display: data ? String(data.predicted_delay_min) : "\u2014",
      }));
      if (items.every((it) => it.value === 0)) return; // ML offline -> skip
      host.innerHTML = `<div class="tr-h">Predicted delay, next 7 days (min)</div>` + barChartSVG(items, "is-delay");
      $("td-trends").hidden = false;
    } catch (e) { /* skip */ }
  }

  // ---- price & seat alerts ----
  let alertCtx = null;
  let alertClassFares = {};

  function setupAlertPanel(d, bFrom, bTo, bDate) {
    if (!window.RailAlerts || !RailAlerts.authed()) return;
    alertCtx = { number: String(d.number), name: d.name || "", from: bFrom, to: bTo, date: bDate };
    $("td-alert").hidden = false;

    const kindSel = $("al-kind");
    const thrWrap = $("al-thr-wrap");
    const classSel = $("al-class");
    const thr = $("al-threshold");

    function prefillThreshold() {
      const f = alertClassFares[classSel.value];
      if (f) thr.value = f;
    }
    function syncKind() {
      thrWrap.hidden = kindSel.value !== "fare";
      if (kindSel.value === "fare" && !thr.value) prefillThreshold();
    }
    kindSel.addEventListener("change", syncKind);
    classSel.addEventListener("change", () => { if (kindSel.value === "fare") prefillThreshold(); });
    syncKind();

    $("al-create").addEventListener("click", onCreateAlert);
    renderMyAlerts();
  }

  function populateAlertClasses(classes) {
    const sel = $("al-class");
    if (!sel || !classes || !classes.length) return;
    alertClassFares = {};
    sel.innerHTML = classes
      .map((c) => {
        alertClassFares[c.travel_class] = +c.fare || 0;
        return `<option value="${esc(c.travel_class)}">${esc(c.travel_class)} · \u20b9${esc(c.fare)}</option>`;
      })
      .join("");
    if ($("al-kind") && $("al-kind").value === "fare" && !$("al-threshold").value) {
      $("al-threshold").value = alertClassFares[sel.value] || "";
    }
  }

  function alertJourneyDate() {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    let d = alertCtx && alertCtx.date ? new Date(alertCtx.date + "T00:00:00") : null;
    if (!d || isNaN(d.getTime()) || d < today) {
      d = new Date(today);
      d.setDate(today.getDate() + 1);
    }
    return d.toISOString().slice(0, 10);
  }

  function showAlertMsg(text, ok) {
    const msg = $("al-msg");
    msg.textContent = text;
    msg.className = "al-msg " + (ok ? "is-ok" : "is-err");
    msg.hidden = false;
  }

  async function onCreateAlert() {
    const kind = $("al-kind").value;
    const payload = {
      kind,
      train_number: alertCtx.number,
      train_name: alertCtx.name,
      from_code: alertCtx.from,
      to_code: alertCtx.to,
      journey_date: alertJourneyDate(),
      travel_class: $("al-class").value,
      quota: "GN",
    };
    if (kind === "fare") payload.threshold = parseInt($("al-threshold").value, 10) || 0;
    const btn = $("al-create");
    btn.disabled = true;
    try {
      await RailAlerts.create(payload);
      showAlertMsg("Alert created. It will be marked when the condition is met.", true);
      await renderMyAlerts();
    } catch (e) {
      showAlertMsg(e.message || "Could not create the alert.", false);
    }
    btn.disabled = false;
  }

  async function renderMyAlerts() {
    const host = $("al-mine");
    if (!host || !alertCtx) return;
    const all = await RailAlerts.list();
    const mine = all.filter((a) => String(a.train_number) === alertCtx.number);
    if (!mine.length) {
      host.innerHTML = "";
      return;
    }
    host.innerHTML =
      `<div class="al-mine-h">Your alerts for this train</div>` +
      mine
        .map((a) => {
          const cond = a.kind === "fare" ? `Fare \u2264 \u20b9${esc(a.threshold)}` : "Seat clears";
          const badge =
            a.status === "triggered"
              ? `<span class="al-badge is-hit">Triggered</span>`
              : a.status === "expired"
              ? `<span class="al-badge is-exp">Expired</span>`
              : `<span class="al-badge is-act">Active</span>`;
          const last = a.last_value ? ` \u00b7 last ${esc(a.last_value)}` : "";
          return `<div class="al-row">
            <span class="al-row-main">${esc(a.travel_class)} \u00b7 ${cond}${last}</span>
            ${badge}
            <button type="button" class="al-del" data-id="${esc(a.id)}" aria-label="Remove">\u2715</button>
          </div>`;
        })
        .join("");
    host.querySelectorAll(".al-del").forEach((b) =>
      b.addEventListener("click", async () => {
        b.disabled = true;
        try {
          await RailAlerts.remove(b.dataset.id);
          await renderMyAlerts();
        } catch (e) {
          b.disabled = false;
        }
      })
    );
  }

  async function loadWeek(number, date, from, to) {
    const host = $("td-week");
    if (!host) return;
    try {
      const url = `/api/availability/week/?train=${encodeURIComponent(number)}` +
        (date ? `&date=${encodeURIComponent(date)}` : "") +
        (from ? `&from=${encodeURIComponent(from)}` : "") +
        (to ? `&to=${encodeURIComponent(to)}` : "");
      const res = await fetch(url);
      const d = await res.json();
      if (!res.ok || !d.classes || !d.classes.length) return;

      const head =
        `<div class="wk-cell wk-corner">Class</div>` +
        d.days
          .map(
            (day) =>
              `<div class="wk-cell wk-dayhead"><span class="wk-wd">${esc(day.weekday)}</span><span class="wk-dt">${esc(day.day)}</span></div>`
          )
          .join("");

      const rows = d.classes
        .map((cls) => {
          const cells = d.days
            .map((day) => {
              const c = day.cells[cls] || { status_type: "", status: "—" };
              return `<div class="wk-cell wk-stat is-${esc(c.status_type)}">${esc(c.status)}</div>`;
            })
            .join("");
          return (
            `<div class="wk-cell wk-cls"><span class="wk-cls-code">${esc(cls)}</span>` +
            `<span class="wk-cls-fare">₹${esc(d.fares[cls])}</span></div>` +
            cells
          );
        })
        .join("");

      host.innerHTML = `
        <div class="wk-head">Availability over the next 7 days</div>
        <div class="wk-scroll">
          <div class="wk-grid">${head}${rows}</div>
        </div>
        <p class="av-note">${esc(d.disclaimer)}</p>`;
      host.hidden = false;
    } catch (e) { /* skip */ }
  }

  async function load() {
    const num = trainNumber();
    if (!num) {
      loading.hidden = true;
      errorEl.textContent = "No train number in the URL.";
      errorEl.hidden = false;
      return;
    }
    try {
      const res = await fetch(`/api/trains/${encodeURIComponent(num)}/`);
      if (res.status === 404) {
        loading.hidden = true;
        errorEl.textContent = `Train ${num} was not found in the dataset.`;
        errorEl.hidden = false;
        return;
      }
      const data = await res.json();
      render(data);
    } catch (e) {
      loading.hidden = true;
      errorEl.textContent = "Could not load the schedule. Is the server running?";
      errorEl.hidden = false;
    }
  }

  load();
})();