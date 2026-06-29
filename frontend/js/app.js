// RailSetu search page. Talks to the Django API on the same origin.
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const form = $("search-form");
  const fromInput = $("from-input");
  const toInput = $("to-input");
  const dateInput = $("date-input");
  const searchBtn = $("search-btn");
  const formError = $("form-error");

  const resultsSection = $("results-section");
  const resultsTitle = $("results-title");
  const resultsRoute = $("results-route");
  const board = $("board");
  const stateLoading = $("state-loading");
  const stateEmpty = $("state-empty");
  const stateError = $("state-error");

  // Selected station codes (set when a suggestion is picked).
  const selected = { from: "", to: "" };

  // ---- date defaults (the shared calendar.js enhances this input) ----
  const today = new Date().toISOString().slice(0, 10);
  dateInput.value = today;
  dateInput.min = today;

  // ---- helpers ----
  const hhmm = (t) => (t ? t.slice(0, 5) : "--:--");
  const esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  function debounce(fn, ms) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  function showState(which) {
    resultsSection.hidden = false;
    board.hidden = which !== "board";
    stateLoading.hidden = which !== "loading";
    stateEmpty.hidden = which !== "empty";
    stateError.hidden = which !== "error";
    const ctrls = document.getElementById("res-controls");
    if (ctrls) ctrls.hidden = which !== "board";
  }

  // ---- autocomplete ----
  function setupAutocomplete(input, suggestEl, key) {
    let items = [];
    let activeIndex = -1;

    const close = () => {
      suggestEl.classList.remove("open");
      suggestEl.innerHTML = "";
      activeIndex = -1;
    };

    const render = (stations) => {
      items = stations;
      if (!stations.length) return close();
      suggestEl.innerHTML = stations
        .map(
          (s, i) => `
          <li role="option" data-i="${i}" data-code="${esc(s.code)}">
            <span>
              <span class="s-name">${esc(s.name)}</span>
              <span class="s-sub"> ${esc(s.state || "")}</span>
            </span>
            <span class="s-code">${esc(s.code)}</span>
          </li>`
        )
        .join("");
      suggestEl.classList.add("open");
      activeIndex = -1;
    };

    const pick = (i) => {
      const s = items[i];
      if (!s) return;
      input.value = `${s.name} (${s.code})`;
      selected[key] = s.code;
      close();
    };

    const fetchSuggest = debounce(async (q) => {
      try {
        const res = await fetch(`/api/stations/?q=${encodeURIComponent(q)}`);
        if (!res.ok) return close();
        render(await res.json());
      } catch (_) {
        close();
      }
    }, 180);

    input.addEventListener("input", () => {
      selected[key] = ""; // typing invalidates a previous pick
      const q = input.value.trim();
      if (q.length < 2) return close();
      fetchSuggest(q);
    });

    input.addEventListener("keydown", (e) => {
      if (!suggestEl.classList.contains("open")) return;
      const lis = [...suggestEl.querySelectorAll("li")];
      if (e.key === "ArrowDown") {
        e.preventDefault();
        activeIndex = Math.min(activeIndex + 1, lis.length - 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeIndex = Math.max(activeIndex - 1, 0);
      } else if (e.key === "Enter" && activeIndex >= 0) {
        e.preventDefault();
        pick(activeIndex);
        return;
      } else if (e.key === "Escape") {
        return close();
      } else {
        return;
      }
      lis.forEach((li, i) => li.classList.toggle("active", i === activeIndex));
    });

    suggestEl.addEventListener("mousedown", (e) => {
      const li = e.target.closest("li");
      if (li) {
        e.preventDefault();
        pick(Number(li.dataset.i));
      }
    });

    document.addEventListener("click", (e) => {
      if (!input.contains(e.target) && !suggestEl.contains(e.target)) close();
    });
  }

  setupAutocomplete(fromInput, $("from-suggest"), "from");
  setupAutocomplete(toInput, $("to-suggest"), "to");

  // ---- swap ----
  $("swap-btn").addEventListener("click", () => {
    [fromInput.value, toInput.value] = [toInput.value, fromInput.value];
    [selected.from, selected.to] = [selected.to, selected.from];
  });

  // ---- render results (with sort + filter) ----
  let lastResults = [];
  let sortKey = "dep";
  let typeFilter = "ALL";
  let shownTrains = [];
  const fareByTrain = {};
  const compareSet = new Set();
  const scoreByTrain = {};
  let rankOffline = false;
  let rankLoading = false;

  function _durMin(d) {
    const m = /(\d+)h\s*(\d+)m/.exec(d || "");
    return m ? +m[1] * 60 + +m[2] : 1e9;
  }
  function _timeMin(t, day) {
    const p = (t || "").split(":");
    return (day || 1) * 1440 + (+p[0] || 0) * 60 + (+p[1] || 0);
  }

  function rowHtml(t) {
    const dayDiff = (t.destination.day || 1) - (t.origin.day || 1);
    const dayTag = dayDiff > 0 ? `<span class="t-day">+${dayDiff} day${dayDiff > 1 ? "s" : ""}</span>` : "";
    const typeTag = t.type ? `<span class="t-type">${esc(t.type)}</span>` : "";
    return `
        <a class="train-row" data-num="${esc(t.number)}" href="/train/${esc(t.number)}/?from=${esc(t.origin.code)}&to=${esc(t.destination.code)}&date=${esc(dateInput.value)}">
          <div class="t-info">
            <div class="t-id">${esc(t.number)}</div>
            <div class="t-name">${esc(t.name)}</div>
            ${typeTag}
            <span class="t-badge-slot"></span>
            <button type="button" class="t-compare" data-num="${esc(t.number)}" aria-label="Add to compare">Compare</button>
          </div>
          <div class="t-timeline">
            <div class="t-point from">
              <div class="t-time">${hhmm(t.origin.time)}</div>
              <div class="t-stn">${esc(t.origin.code)}</div>
            </div>
            <div class="t-mid">
              ${dayTag}
              <div class="t-line"></div>
            </div>
            <div class="t-point to">
              <div class="t-time">${hhmm(t.destination.time)}</div>
              <div class="t-stn">${esc(t.destination.code)}</div>
            </div>
          </div>
          <div class="t-dur">${esc(t.duration || "—")}<span>travel time</span></div>
          <span class="t-go" aria-hidden="true">&rsaquo;</span>
          <div class="t-avail" data-train="${esc(t.number)}" data-from="${esc(t.origin.code)}" data-to="${esc(t.destination.code)}"></div>
        </a>`;
  }

  function renderRows(trains) {
    shownTrains = trains;
    board.innerHTML = trains.map(rowHtml).join("");
    board.querySelectorAll(".t-avail").forEach(fillAvail);
    applyBadges();
    syncCompareButtons();
  }

  function syncCompareButtons() {
    board.querySelectorAll(".t-compare").forEach((b) => {
      b.classList.toggle("is-on", compareSet.has(b.dataset.num));
      b.textContent = compareSet.has(b.dataset.num) ? "Added" : "Compare";
    });
  }

  function toggleCompare(num) {
    if (compareSet.has(num)) compareSet.delete(num);
    else {
      if (compareSet.size >= 3) return false;
      compareSet.add(num);
    }
    syncCompareButtons();
    renderCompareBar();
    return true;
  }

  function renderCompareBar() {
    let bar = document.getElementById("cmp-bar");
    if (compareSet.size < 1) {
      if (bar) bar.remove();
      return;
    }
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "cmp-bar";
      bar.className = "cmp-bar";
      document.body.appendChild(bar);
    }
    bar.innerHTML =
      `<span class="cmp-count">${compareSet.size} selected</span>` +
      `<button type="button" class="cmp-go" id="cmp-go"${compareSet.size < 2 ? " disabled" : ""}>Compare ${compareSet.size} trains</button>` +
      `<button type="button" class="cmp-clear" id="cmp-clear">Clear</button>`;
    bar.querySelector("#cmp-go").addEventListener("click", openCompare);
    bar.querySelector("#cmp-clear").addEventListener("click", () => {
      compareSet.clear();
      syncCompareButtons();
      renderCompareBar();
    });
  }

  function openCompare() {
    const trains = lastResults.filter((t) => compareSet.has(t.number));
    if (trains.length < 2) return;

    const durs = trains.map((t) => _durMin(t.duration));
    const minDur = Math.min(...durs);
    const fares = trains.map((t) => fareByTrain[t.number]).filter((f) => f != null);
    const minFare = fares.length ? Math.min(...fares) : null;

    const cols = trains
      .map(
        (t) => `<th>${esc(t.number)}<span>${esc(t.name)}</span></th>`
      )
      .join("");
    const row = (label, fn) =>
      `<tr><td class="cmp-lbl">${label}</td>${trains.map((t) => `<td>${fn(t)}</td>`).join("")}</tr>`;

    const body =
      row("Type", (t) => esc(t.type || "—")) +
      row("Departs", (t) => `${hhmm(t.origin.time)} <span class="cmp-sub">${esc(t.origin.code)}</span>`) +
      row("Arrives", (t) => `${hhmm(t.destination.time)} <span class="cmp-sub">${esc(t.destination.code)}</span>`) +
      row("Duration", (t) => {
        const best = _durMin(t.duration) === minDur;
        return `<span class="${best ? "cmp-best" : ""}">${esc(t.duration || "—")}</span>`;
      }) +
      row("From fare", (t) => {
        const f = fareByTrain[t.number];
        if (f == null) return "—";
        const best = minFare != null && f === minFare;
        return `<span class="${best ? "cmp-best" : ""}">₹${f}</span>`;
      });

    let modal = document.getElementById("cmp-modal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "cmp-modal";
      modal.className = "cmp-modal";
      document.body.appendChild(modal);
    }
    modal.innerHTML = `
      <div class="cmp-card" role="dialog" aria-modal="true">
        <div class="cmp-head">
          <h3>Compare trains</h3>
          <button type="button" class="cmp-x" id="cmp-x" aria-label="Close">&times;</button>
        </div>
        <div class="cmp-scroll">
          <table class="cmp-table">
            <thead><tr><th></th>${cols}</tr></thead>
            <tbody>${body}</tbody>
          </table>
        </div>
        <p class="cmp-note">Fares are estimates; lowest fare and shortest time are highlighted.</p>
      </div>`;
    modal.classList.add("open");
    const close = () => modal.classList.remove("open");
    modal.querySelector("#cmp-x").addEventListener("click", close);
    modal.addEventListener("click", (e) => { if (e.target === modal) close(); });
  }

  function applyBadges() {
    const trains = shownTrains || [];
    let fastest = null, bestDur = Infinity;
    trains.forEach((t) => {
      const d = _durMin(t.duration);
      if (d < bestDur) { bestDur = d; fastest = t.number; }
    });
    let cheapest = null, lowFare = Infinity;
    trains.forEach((t) => {
      const f = fareByTrain[t.number];
      if (f != null && f < lowFare) { lowFare = f; cheapest = t.number; }
    });
    board.querySelectorAll(".train-row").forEach((row) => {
      const slot = row.querySelector(".t-badge-slot");
      if (!slot) return;
      const num = row.dataset.num;
      let html = "";
      if (sortKey === "rec" && !rankOffline && scoreByTrain[num] != null) {
        const sc = scoreByTrain[num];
        const band = sc >= 70 ? "is-great" : sc >= 50 ? "is-good" : "is-fair";
        html += `<span class="t-badge t-match ${band}">Match ${sc}</span>`;
      }
      if (num === fastest) html += `<span class="t-badge is-fast">Fastest</span>`;
      if (num === cheapest) html += `<span class="t-badge is-cheap">Cheapest</span>`;
      slot.innerHTML = html;
    });
  }

  async function ensureRankScores() {
    // already have scores for the current result set?
    if (lastResults.length && lastResults.every((t) => scoreByTrain[t.number] != null)) return;
    if (rankOffline) return;
    rankLoading = true;
    try {
      const items = lastResults.map((t) => ({
        train_number: t.number,
        train_type: t.type || "Exp",
        journey_hours: Math.max(_durMin(t.duration) / 60, 0.1),
        dep_hour: parseInt((t.origin.time || "12:00").split(":")[0], 10) || 12,
        fare: fareByTrain[t.number] != null ? fareByTrain[t.number] : null,
      }));
      const res = await fetch("/api/predict/rank/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items }),
      });
      if (!res.ok) { rankOffline = true; return; }
      const data = await res.json();
      (data.results || []).forEach((r) => { scoreByTrain[r.train_number] = r.score; });
    } catch (e) {
      rankOffline = true;
    } finally {
      rankLoading = false;
    }
  }

  function applyView() {
    let rows = lastResults.slice();
    if (typeFilter !== "ALL") rows = rows.filter((t) => (t.type || "") === typeFilter);
    if (sortKey === "rec" && !rankOffline)
      rows.sort((a, b) => (scoreByTrain[b.number] ?? -1) - (scoreByTrain[a.number] ?? -1));
    else if (sortKey === "dep" || (sortKey === "rec" && rankOffline))
      rows.sort((a, b) => _timeMin(a.origin.time, a.origin.day) - _timeMin(b.origin.time, b.origin.day));
    else if (sortKey === "arr")
      rows.sort((a, b) => _timeMin(a.destination.time, a.destination.day) - _timeMin(b.destination.time, b.destination.day));
    else if (sortKey === "dur")
      rows.sort((a, b) => _durMin(a.duration) - _durMin(b.duration));
    renderRows(rows);
    resultsTitle.textContent = `${rows.length} train${rows.length !== 1 ? "s" : ""}`;
    const note = document.getElementById("rec-note");
    if (note) note.hidden = !(sortKey === "rec" && rankOffline);
  }

  function renderControls() {
    let bar = document.getElementById("res-controls");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "res-controls";
      bar.className = "res-controls";
      board.parentNode.insertBefore(bar, board);
    }
    const types = [...new Set(lastResults.map((t) => t.type).filter(Boolean))].sort();
    const chips = ["ALL", ...types]
      .map(
        (ty) =>
          `<button type="button" class="res-chip${ty === typeFilter ? " is-on" : ""}" data-type="${esc(ty)}">${
            ty === "ALL" ? "All" : esc(ty)
          }</button>`
      )
      .join("");
    const SORTS = { rec: "Recommended", dep: "Departure", arr: "Arrival", dur: "Duration" };
    const opts = Object.entries(SORTS)
      .map(
        ([k, lbl]) =>
          `<li role="option" class="sortdd-opt${k === sortKey ? " is-sel" : ""}" data-k="${k}">${lbl}</li>`
      )
      .join("");
    bar.innerHTML = `
      <div class="res-sort">
        <span class="res-sort-label">Sort by</span>
        <div class="sortdd" id="sortdd">
          <button type="button" class="sortdd-btn" id="sortdd-btn" aria-haspopup="listbox" aria-expanded="false">
            <span id="sortdd-cur">${SORTS[sortKey]}</span>
            <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <ul class="sortdd-pop" id="sortdd-pop" role="listbox">${opts}</ul>
        </div>
      </div>
      <div class="res-chips">${chips}</div>
      <p class="rec-note" id="rec-note" hidden>Recommended ranking needs the ML service (port 8001); showing earliest departures instead.</p>`;

    const dd = bar.querySelector("#sortdd");
    const ddBtn = bar.querySelector("#sortdd-btn");
    const ddPop = bar.querySelector("#sortdd-pop");
    const ddCur = bar.querySelector("#sortdd-cur");
    const closeDD = () => { dd.classList.remove("open"); ddBtn.setAttribute("aria-expanded", "false"); };
    ddBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = dd.classList.toggle("open");
      ddBtn.setAttribute("aria-expanded", open ? "true" : "false");
    });
    ddPop.querySelectorAll(".sortdd-opt").forEach((li) =>
      li.addEventListener("click", async () => {
        sortKey = li.dataset.k;
        ddCur.textContent = SORTS[sortKey];
        ddPop.querySelectorAll(".sortdd-opt").forEach((o) => o.classList.toggle("is-sel", o === li));
        closeDD();
        if (sortKey === "rec") {
          ddCur.textContent = "Ranking…";
          await ensureRankScores();
          ddCur.textContent = SORTS.rec;
        }
        applyView();
      })
    );
    document.addEventListener("click", (e) => { if (!e.target.closest("#sortdd")) closeDD(); });

    bar.querySelectorAll(".res-chip").forEach((c) =>
      c.addEventListener("click", () => { typeFilter = c.dataset.type; renderControls(); applyView(); })
    );
    bar.hidden = false;
  }

  function renderTrains(data) {
    lastResults = data.results || [];
    resultsRoute.textContent = `${data.from} to ${data.to}`;
    if (window.RailSaved) {
      RailSaved.wireToggle(
        document.getElementById("res-save"),
        {
          kind: "route",
          key: `${data.from}-${data.to}`,
          label: `${data.from} to ${data.to}`,
          subtitle: "Saved route",
          url: `/?from=${encodeURIComponent(data.from)}&to=${encodeURIComponent(data.to)}`,
        },
        { labelOn: "★ Saved route", labelOff: "☆ Save route" }
      );
    }
    if (window.RailHistory) {
      RailHistory.record({
        kind: "route",
        key: `${data.from}-${data.to}`,
        label: `${data.from} to ${data.to}`,
        subtitle: "Recent search",
        url: `/?from=${encodeURIComponent(data.from)}&to=${encodeURIComponent(data.to)}`,
      });
    }
    compareSet.clear();
    renderCompareBar();
    Object.keys(scoreByTrain).forEach((k) => delete scoreByTrain[k]);
    rankOffline = false;
    if (!lastResults.length) {
      const ctrls = document.getElementById("res-controls");
      if (ctrls) ctrls.hidden = true;
      return showState("empty");
    }
    sortKey = "dep";
    typeFilter = "ALL";
    renderControls();
    applyView();
    showState("board");
  }

  async function fillAvail(el) {
    const train = el.dataset.train;
    const date = dateInput.value;
    const seg =
      (el.dataset.from ? `&from=${encodeURIComponent(el.dataset.from)}` : "") +
      (el.dataset.to ? `&to=${encodeURIComponent(el.dataset.to)}` : "");
    try {
      const res = await fetch(
        `/api/availability/?train=${encodeURIComponent(train)}` +
        (date ? `&date=${encodeURIComponent(date)}` : "") + seg
      );
      const d = await res.json();
      if (!res.ok || !d.classes || !d.classes.length) return;
      el.innerHTML = d.classes.map((c) => {
        const chance = c.chance != null ? `<span class="rc-chance">${esc(c.chance)}% chance</span>` : "";
        return `<div class="rc-box is-${esc(c.status_type)}">
          <div class="rc-top"><span class="rc-cls">${esc(c.travel_class)}</span><span class="rc-fare">₹${esc(c.fare)}</span></div>
          <div class="rc-status">${esc(c.status)}</div>
          ${chance}
        </div>`;
      }).join("");
      const fares = d.classes.map((c) => +c.fare).filter((n) => !isNaN(n));
      if (fares.length) { fareByTrain[train] = Math.min(...fares); applyBadges(); }
    } catch (e) { /* leave empty on error */ }
  }

  // compare toggle (rows are links, so stop navigation)
  board.addEventListener("click", (e) => {
    const btn = e.target.closest(".t-compare");
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    if (toggleCompare(btn.dataset.num) === false) {
      btn.classList.add("cmp-shake");
      setTimeout(() => btn.classList.remove("cmp-shake"), 400);
    }
  });

  // ---- search submit ----
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    formError.textContent = "";

    const from = selected.from || fromInput.value.trim().toUpperCase();
    const to = selected.to || toInput.value.trim().toUpperCase();

    if (!from || !to) {
      formError.textContent = "Pick both a from and a to station.";
      return;
    }
    if (from === to) {
      formError.textContent = "From and to stations must be different.";
      return;
    }

    searchBtn.disabled = true;
    showState("loading");

    const params = new URLSearchParams({ from, to });
    if (dateInput.value) params.set("date", dateInput.value);

    try {
      const res = await fetch(`/api/trains/search/?${params.toString()}`);
      const data = await res.json();
      if (!res.ok) {
        stateError.textContent = data.detail || "Could not search right now.";
        showState("error");
        return;
      }
      renderTrains(data);
      // keep the search shareable / refreshable
      const shareUrl = "/?" + params.toString();
      history.replaceState(null, "", shareUrl);
    } catch (_) {
      stateError.textContent = "Could not reach the server. Is it running?";
      showState("error");
    } finally {
      searchBtn.disabled = false;
    }
  });

  // Deep link / homepage chips: /?from=NDLS&to=CSTM&date=YYYY-MM-DD runs the search.
  (function prefillFromUrl() {
    const qp = new URLSearchParams(location.search);
    const f = qp.get("from");
    const t = qp.get("to");
    if (!f || !t) return;
    fromInput.value = f.toUpperCase();
    toInput.value = t.toUpperCase();
    selected.from = f.toUpperCase();
    selected.to = t.toUpperCase();
    if (qp.get("date") && dateInput) dateInput.value = qp.get("date");
    if (form.requestSubmit) form.requestSubmit();
    else form.dispatchEvent(new Event("submit", { cancelable: true }));
  })();
})();