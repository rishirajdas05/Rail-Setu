// RailSetu station board: pick a station, list the trains scheduled through it.
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const input = $("station-input");
  const suggestEl = $("station-suggest");
  const form = $("board-form");
  const errEl = $("board-error");
  const wrap = $("board-result");
  const loading = $("bd-loading");
  const empty = $("bd-empty");
  const card = $("bd-card");

  let selectedCode = "";
  let items = [];
  let activeIndex = -1;

  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  const show = (el) => el && (el.hidden = false);
  const hide = (el) => el && (el.hidden = true);

  function debounce(fn, ms) {
    let t;
    return (...a) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...a), ms);
    };
  }

  // ---- autocomplete ----
  function close() {
    suggestEl.classList.remove("open");
    suggestEl.innerHTML = "";
    activeIndex = -1;
  }

  function renderSuggest(stations) {
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
  }

  function pick(i) {
    const s = items[i];
    if (!s) return;
    input.value = `${s.name} (${s.code})`;
    selectedCode = s.code;
    close();
  }

  const fetchSuggest = debounce(async (q) => {
    try {
      const res = await fetch(`/api/stations/?q=${encodeURIComponent(q)}`);
      if (!res.ok) return close();
      renderSuggest(await res.json());
    } catch (_) {
      close();
    }
  }, 180);

  input.addEventListener("input", () => {
    selectedCode = "";
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
    if (li) pick(Number(li.dataset.i));
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest("#board-form")) close();
  });

  // ---- board ----
  function typeBadge(t) {
    if (!t) return "";
    return `<span class="bd-type">${esc(t)}</span>`;
  }

  function dayTag(d) {
    return d && d > 0 ? `<span class="day-tag">+${d}d</span>` : "";
  }

  function row(t) {
    const time = t.departure || t.arrival || "--:--";
    const kind = t.departure ? "dep" : "arr";
    return `
      <li class="bd-row">
        <div class="bd-time">
          <span class="bd-time-main">${esc(time)} ${dayTag(t.day_offset)}</span>
          <span class="bd-time-kind">${kind === "dep" ? "departs" : "arrives"}</span>
        </div>
        <div class="bd-mid">
          <div class="bd-train">
            <a href="/train/${encodeURIComponent(t.number)}/">${esc(t.number)} &middot; ${esc(t.name)}</a>
            ${typeBadge(t.type)}
          </div>
          <div class="bd-route">${esc(t.source_name || t.source_code)} <span class="arrow">&rarr;</span> ${esc(t.dest_name || t.dest_code)}</div>
        </div>
        <div class="bd-meta">
          ${t.platform ? `<span class="bd-pf">PF ${esc(t.platform)}</span>` : ""}
          ${t.arrival && t.departure ? `<span class="bd-times">${esc(t.arrival)} / ${esc(t.departure)}</span>` : ""}
          <a class="bd-live" href="/status/?train=${encodeURIComponent(t.number)}&start_day=0">Live</a>
        </div>
      </li>`;
  }

  let lastTrains = [];
  let bdFilter = "";
  let bdType = "ALL";

  function applyBdFilter() {
    let rows = lastTrains;
    if (bdType !== "ALL") rows = rows.filter((t) => (t.type || "") === bdType);
    if (bdFilter) {
      rows = rows.filter((t) => {
        const hay = `${t.number} ${t.name} ${t.dest_name || t.dest_code || ""} ${t.source_name || t.source_code || ""}`.toLowerCase();
        return hay.includes(bdFilter);
      });
    }
    const list = $("bd-list");
    if (list) {
      list.innerHTML = rows.length
        ? rows.map(row).join("")
        : `<li class="bd-none">No trains match your filter.</li>`;
    }
    const count = $("bd-count");
    if (count) {
      count.textContent =
        rows.length === lastTrains.length
          ? `${lastTrains.length} trains call here · next departures first`
          : `${rows.length} of ${lastTrains.length} trains shown`;
    }
  }

  function renderBoard(d) {
    const trains = d.trains || [];
    if (!trains.length) {
      hide(card);
      empty.textContent = "No trains found calling at this station.";
      show(empty);
      return;
    }
    lastTrains = trains;
    bdFilter = "";
    bdType = "ALL";
    const types = [...new Set(trains.map((t) => t.type).filter(Boolean))].sort();
    const chips = ["ALL", ...types]
      .map(
        (ty) =>
          `<button type="button" class="bd-chip${ty === "ALL" ? " is-on" : ""}" data-type="${esc(ty)}">${
            ty === "ALL" ? "All" : esc(ty)
          }</button>`
      )
      .join("");
    card.innerHTML = `
      <div class="bd-head">
        <div>
          <h2 class="bd-station">${esc(d.station.name)} <span class="bd-code">${esc(d.station.code)}</span></h2>
          <p class="bd-count" id="bd-count">${d.count} trains call here &middot; next departures first</p>
        </div>
      </div>
      <div class="bd-filter">
        <input type="text" id="bd-search" class="bd-search" placeholder="Filter by train name, number, or destination" autocomplete="off">
        <div class="bd-chips">${chips}</div>
      </div>
      <ul class="bd-list" id="bd-list">${trains.map(row).join("")}</ul>`;
    hide(empty);
    show(card);

    const search = $("bd-search");
    if (search) {
      search.addEventListener("input", () => {
        bdFilter = search.value.trim().toLowerCase();
        applyBdFilter();
      });
    }
    card.querySelectorAll(".bd-chip").forEach((c) =>
      c.addEventListener("click", () => {
        bdType = c.dataset.type;
        card.querySelectorAll(".bd-chip").forEach((x) => x.classList.toggle("is-on", x === c));
        applyBdFilter();
      })
    );
  }

  async function loadBoard() {
    const code = selectedCode || guessCode();
    if (!code) {
      errEl.textContent = "Pick a station from the list.";
      return;
    }
    errEl.textContent = "";
    show(wrap);
    hide(card);
    hide(empty);
    show(loading);
    history.replaceState(null, "", `/board/?code=${encodeURIComponent(code)}`);
    try {
      const res = await fetch(`/api/station-board/?code=${encodeURIComponent(code)}&limit=100`);
      hide(loading);
      if (!res.ok) {
        empty.textContent =
          res.status === 404 ? "Station not found." : "Could not load the board.";
        show(empty);
        return;
      }
      renderBoard(await res.json());
    } catch (_) {
      hide(loading);
      empty.textContent = "Could not load the board.";
      show(empty);
    }
  }

  // If the user typed a bare code like "GWL", use it directly.
  function guessCode() {
    const v = input.value.trim().toUpperCase();
    const m = v.match(/\(([A-Z]{2,8})\)\s*$/);
    if (m) return m[1];
    if (/^[A-Z]{2,8}$/.test(v)) return v;
    return "";
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    loadBoard();
  });

  // Deep link: /board/?code=GWL
  const params = new URLSearchParams(location.search);
  const initial = params.get("code");
  if (initial) {
    selectedCode = initial.toUpperCase();
    input.value = selectedCode;
    loadBoard();
  }
})();