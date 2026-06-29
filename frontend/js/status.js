// RailSetu live status page. Talks to the Django API on the same origin.
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const form = $("status-form");
  const trainInput = $("train-input");
  const startDay = $("startday-select");
  const errorEl = $("status-error");

  const resultWrap = $("status-result");
  const loading = $("st-loading");
  const empty = $("st-empty");
  const card = $("st-card");

  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  // Prefill from ?train= so the page is shareable.
  const qs = new URLSearchParams(location.search);
  if (qs.get("train")) {
    trainInput.value = qs.get("train").replace(/\D/g, "").slice(0, 6);
    if (qs.get("start_day")) startDay.value = qs.get("start_day");
  }

  function show(el) { el.hidden = false; }
  function hide(el) { el.hidden = true; }

  function setError(msg) {
    errorEl.textContent = msg || "";
    errorEl.style.display = msg ? "block" : "none";
  }

  function delayClass(mins) {
    if (mins > 0) return "is-late";
    if (mins < 0) return "is-early";
    return "is-ontime";
  }

  function dayTag(day) {
    return day && day > 0 ? `<span class="day-tag">+${day}d</span>` : "";
  }

  function stopRow(s, kind) {
    // kind: "crossed" | "upcoming"
    const timeMain = kind === "crossed" ? s.exp_arr : s.exp_arr;
    const sched = s.sched_arr;
    const delayed = s.delay > 0;
    return `
      <li class="tl-stop ${kind}">
        <span class="tl-dot" aria-hidden="true"></span>
        <div class="tl-body">
          <div class="tl-line1">
            <span class="tl-name">${esc(s.name)} <span class="tl-code">${esc(s.code)}</span></span>
            <span class="tl-km">${s.km} km</span>
          </div>
          <div class="tl-line2">
            <span class="tl-time ${delayed ? "is-late" : ""}">${esc(timeMain)} ${dayTag(s.day)}</span>
            ${sched && sched !== timeMain ? `<span class="tl-sched">sched ${esc(sched)}</span>` : ""}
            ${s.platform ? `<span class="tl-pf">PF ${s.platform}</span>` : ""}
            ${s.delay ? `<span class="tl-delay">${s.delay > 0 ? "+" + s.delay : s.delay} min</span>` : ""}
          </div>
        </div>
      </li>`;
  }

  function render(d) {
    const dc = delayClass(d.delay_min);
    const pct = d.total_km ? Math.min(100, Math.round((d.covered_km / d.total_km) * 100)) : 0;

    const positionLines = (d.position_lines || [])
      .map((l) => `<li>${esc(l)}</li>`)
      .join("");

    const crossed = (d.crossed || []).map((s) => stopRow(s, "crossed")).join("");
    const upcoming = (d.upcoming || []).map((s) => stopRow(s, "upcoming")).join("");

    card.innerHTML = `
      <div class="st-head">
        <div>
          <h2 class="st-train">${esc(d.train_number)} &middot; ${esc(d.train_name)}</h2>
          <p class="st-route">${esc(d.source_name)} <span class="arrow">&rarr;</span> ${esc(d.dest_name)}</p>
        </div>
        <div class="st-startdate">Started ${esc(d.start_date || "")}</div>
      </div>

      <div class="st-banner ${dc}">
        <div class="st-banner-main">
          <span class="st-delay">${esc(d.delay_text)}</span>
          <span class="st-asof">${esc(d.as_of || "")}</span>
          <span class="st-live"><span class="st-live-dot" aria-hidden="true"></span>LIVE</span>
        </div>
        ${positionLines ? `<ul class="st-pos">${positionLines}</ul>` : ""}
        ${
          d.next_station
            ? `<div class="st-next">Next stop: <strong>${esc(d.next_station)}</strong> ${esc(d.next_in || "")}</div>`
            : ""
        }
      </div>

      <div class="st-progress">
        <div class="st-bar"><span style="width:${pct}%"></span></div>
        <div class="st-bar-labels">
          <span>${d.covered_km} km covered</span>
          <span>${d.total_km} km total</span>
        </div>
      </div>

      ${!d.gps_live ? `<p class="st-note">Position estimated from schedule data (no live GPS for this train).</p>` : ""}

      <ol class="tl">
        ${crossed}
        <li class="tl-now"><span class="tl-dot" aria-hidden="true"></span>
          <div class="tl-body"><strong>${
            d.terminated
              ? `Train has reached ${esc(d.current_station || "destination")}`
              : d.next_station && d.current_station
              ? `Train is between ${esc(d.current_station)} and ${esc(d.next_station)}`
              : `Train is around ${esc(d.current_station || "here")}`
          }</strong></div>
        </li>
        ${upcoming}
      </ol>
    `;
    hide(loading);
    hide(empty);
    show(card);
  }

  async function track() {
    const num = trainInput.value.replace(/\D/g, "").slice(0, 6);
    if (num.length < 4) {
      setError("Enter a valid train number (4–5 digits).");
      return;
    }
    setError("");
    show(resultWrap);
    hide(card);
    hide(empty);
    show(loading);

    // keep the URL shareable
    history.replaceState(null, "", `/status/?train=${num}&start_day=${startDay.value}`);

    try {
      const res = await fetch(
        `/api/running-status/${num}/?start_day=${encodeURIComponent(startDay.value)}`
      );
      const data = await res.json();

      if (res.status === 503) {
        hide(loading);
        empty.textContent =
          "Live status is not configured yet. Add your provider API key to enable it.";
        show(empty);
        return;
      }
      if (!data.ok) {
        hide(loading);
        empty.textContent =
          data.detail ||
          "Could not fetch status. Try a different ‘departed origin’ day, or check the train number.";
        show(empty);
        return;
      }
      render(data);
    } catch (e) {
      hide(loading);
      empty.textContent = "Network error reaching the server.";
      show(empty);
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    track();
  });

  // Auto-run if a train was passed in the URL.
  if (trainInput.value.length >= 4) track();
})();