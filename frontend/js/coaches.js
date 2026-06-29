// RailSetu Coaches page: find a train, see its coaches and platform, and tap a
// coach to view the berth/seat layout inside (generated from the coach's class).
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  const input = $("cz-input");
  const suggest = $("cz-suggest");
  const errorEl = $("cz-error");
  const loading = $("cz-loading");
  const result = $("cz-result");

  const CLASS_FULL = {
    SL: "Sleeper", "3A": "AC 3 Tier", "2A": "AC 2 Tier", "1A": "AC First",
    CC: "Chair Car", EC: "Executive Chair", "2S": "Second Sitting",
  };

  // ---- search autocomplete ----
  let timer = null;
  function closeSuggest() { suggest.hidden = true; suggest.innerHTML = ""; }

  async function search(q) {
    try {
      const res = await fetch(`/api/train-search/?q=${encodeURIComponent(q)}`);
      if (!res.ok) return closeSuggest();
      const rows = await res.json();
      if (!rows.length) {
        suggest.innerHTML = `<li class="tf-none">No trains match "${esc(q)}"</li>`;
        suggest.hidden = false;
        return;
      }
      suggest.innerHTML = rows
        .map(
          (t) =>
            `<li class="tf-item" data-num="${esc(t.number)}" role="option">
               <span class="tf-num">${esc(t.number)}</span>
               <span class="tf-name">${esc(t.name)}</span>
               <span class="tf-route">${esc(t.source_code)} → ${esc(t.destination_code)}</span>
             </li>`
        )
        .join("");
      suggest.hidden = false;
      suggest.querySelectorAll(".tf-item").forEach((li) =>
        li.addEventListener("click", () => {
          input.value = `${li.dataset.num}`;
          closeSuggest();
          loadTrain(li.dataset.num);
        })
      );
    } catch (_) {
      closeSuggest();
    }
  }

  input.addEventListener("input", () => {
    const q = input.value.trim();
    clearTimeout(timer);
    if (q.length < 2) return closeSuggest();
    timer = setTimeout(() => search(q), 180);
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const first = suggest.querySelector(".tf-item");
      if (first) { input.value = first.dataset.num; closeSuggest(); loadTrain(first.dataset.num); }
      else if (/^\d{4,6}$/.test(input.value.trim())) loadTrain(input.value.trim());
    } else if (e.key === "Escape") closeSuggest();
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".cz-find")) closeSuggest();
  });

  // ---- load + render a train ----
  async function loadTrain(number) {
    errorEl.textContent = "";
    result.hidden = true;
    loading.hidden = false;
    try {
      const res = await fetch(`/api/trains/${encodeURIComponent(number)}/`);
      if (!res.ok) throw new Error("not found");
      const d = await res.json();
      renderTrain(d);
    } catch (e) {
      loading.hidden = true;
      errorEl.textContent = "Could not load that train. Check the number and that the server is running.";
    }
  }

  function renderTrain(d) {
    loading.hidden = true;
    const stops = d.stops || [];
    const board = stops[0];
    const plat = board ? board.platform : "—";
    const boardName = board ? board.station_name : "";

    const coaches = [{ code: "ENG", cls: null, name: "Engine", engine: true }]
      .concat(d.coach_layout || []);

    const strip = coaches
      .map((c, i) => {
        const cl = c.engine ? "cz-engine" : c.cls ? `cz-${esc(c.cls)}` : "cz-util";
        const clickable = c.cls ? "is-tap" : "";
        return `<button type="button" class="cz-coach ${cl} ${clickable}" data-i="${i}" title="${esc(c.name)}">${esc(c.code)}</button>`;
      })
      .join("");

    const present = [...new Set((d.coach_layout || []).filter((c) => c.cls).map((c) => c.cls))];
    const legend = present
      .map((cl) => `<span class="cz-leg"><i class="cz-sw cz-${esc(cl)}"></i>${esc(CLASS_FULL[cl] || cl)}</span>`)
      .join("");

    result.innerHTML = `
      <div class="cz-card">
        <div class="cz-train-head">
          <div>
            <h2 class="cz-train-title">${esc(d.number)} &middot; ${esc(d.name)}</h2>
            <p class="cz-train-route">${esc(d.source_name)} (${esc(d.source_code)}) → ${esc(d.destination_name)} (${esc(d.destination_code)})</p>
          </div>
          <a class="cz-open" href="/train/${encodeURIComponent(d.number)}/">Open train page &rsaquo;</a>
        </div>

        <p class="cz-board">Boarding at <strong>${esc(boardName)}</strong> &middot; Platform <strong>${esc(plat)}</strong> <span class="cz-ind">indicative</span></p>

        <div class="cz-strip">${strip}</div>
        <div class="cz-legend">${legend}</div>
        <p class="cz-hint" id="cz-hint">Tap a coloured coach above to see the layout inside.</p>

        <div class="cz-inside" id="cz-inside" hidden></div>
      </div>`;
    result.hidden = false;

    const stripEl = result.querySelector(".cz-strip");
    stripEl.querySelectorAll(".cz-coach").forEach((btn) => {
      const c = coaches[+btn.dataset.i];
      btn.addEventListener("click", () => {
        if (!c.cls) return;
        stripEl.querySelectorAll(".cz-coach").forEach((x) => x.classList.remove("is-sel"));
        btn.classList.add("is-sel");
        renderInside(c);
      });
    });
  }

  // ---- interior layout generators ----
  const SLEEPER_SPEC = {
    SL: { total: 72, pattern: ["LB", "MB", "UB", "LB", "MB", "UB", "SL", "SU"] },
    "3A": { total: 64, pattern: ["LB", "MB", "UB", "LB", "MB", "UB", "SL", "SU"] },
    "2A": { total: 46, pattern: ["LB", "UB", "LB", "UB", "SL", "SU"] },
    "1A": { total: 24, pattern: ["LB", "UB", "LB", "UB"] },
  };
  const SEAT_SPEC = {
    CC: { total: 78, perRow: 5, split: 3 },
    EC: { total: 56, perRow: 4, split: 2 },
    "2S": { total: 108, perRow: 6, split: 3 },
  };

  function berthClass(t) {
    if (t === "LB" || t === "SL") return "b-low";
    if (t === "MB") return "b-mid";
    if (t === "UB" || t === "SU") return "b-up";
    return "";
  }

  function renderInside(coach) {
    const host = $("cz-inside");
    const hint = $("cz-hint");
    if (hint) hint.hidden = true;
    const cls = coach.cls;
    const title = `${esc(coach.code)} &middot; ${esc(CLASS_FULL[cls] || cls)}`;

    if (SLEEPER_SPEC[cls]) {
      const s = SLEEPER_SPEC[cls];
      const bays = [];
      let no = 1;
      while (no <= s.total) {
        const bay = [];
        for (let k = 0; k < s.pattern.length && no <= s.total; k++) {
          bay.push({ no, type: s.pattern[k] });
          no++;
        }
        bays.push(bay);
      }
      const cell = (b) =>
        `<span class="berth ${berthClass(b.type)}"><b>${b.no}</b><i>${b.type}</i></span>`;
      const col = (arr) => `<div class="berth-col">${arr.slice().reverse().map(cell).join("")}</div>`;

      const bayHtml = bays
        .map((bay, idx) => {
          const main = bay.filter((b) => b.type !== "SL" && b.type !== "SU");
          const side = bay.filter((b) => b.type === "SL" || b.type === "SU");
          const half = Math.ceil(main.length / 2) || 1;
          const colA = main.slice(0, half);
          const colB = main.slice(half);
          const sideCol = side.length
            ? `<div class="bay-aisle"></div><div class="berth-col side">${side.slice().reverse().map(cell).join("")}</div>`
            : "";
          return `<div class="bay">
              <span class="bay-no">Bay ${idx + 1}</span>
              <div class="bay-body"><div class="bay-main">${col(colA)}${col(colB)}</div>${sideCol}</div>
            </div>`;
        })
        .join("");

      host.innerHTML = `
        <div class="cz-inside-head">${title} <span class="cz-inside-sub">${s.total} berths</span></div>
        <div class="cz-shell">
          <span class="cz-cap"></span>
          <div class="bays">${bayHtml}</div>
          <span class="cz-cap"></span>
        </div>
        <div class="cz-berth-legend">
          <span><i class="bsw b-low"></i>Lower (LB &middot; SL)</span>
          <span><i class="bsw b-mid"></i>Middle (MB)</span>
          <span><i class="bsw b-up"></i>Upper (UB &middot; SU)</span>
          <span class="cz-aisle-key"><i class="bsw aisle-key"></i>Aisle</span>
        </div>`;
      host.hidden = false;
      return;
    }

    if (SEAT_SPEC[cls]) {
      const s = SEAT_SPEC[cls];
      const rows = [];
      let no = 1;
      while (no <= s.total) {
        const row = [];
        for (let k = 0; k < s.perRow && no <= s.total; k++) {
          row.push({ no, aisle: k === s.split - 1 });
          no++;
        }
        rows.push(row);
      }
      const rowHtml = rows
        .map(
          (row, i) =>
            `<div class="seat-row"><span class="row-no">${i + 1}</span>${row
              .map((st) => `<span class="seat">${st.no}</span>${st.aisle ? '<span class="aisle"></span>' : ""}`)
              .join("")}</div>`
        )
        .join("");
      host.innerHTML = `
        <div class="cz-inside-head">${title} <span class="cz-inside-sub">${s.total} seats &middot; ${s.split}+${s.perRow - s.split} seating</span></div>
        <div class="cz-shell seating">
          <span class="cz-cap"></span>
          <div class="seat-grid">${rowHtml}</div>
          <span class="cz-cap"></span>
        </div>
        <p class="cz-seatnote">Window seats are at the ends of each row; the gap is the aisle.</p>`;
      host.hidden = false;
      return;
    }

    host.innerHTML = `<div class="cz-inside-head">${title}</div><p class="cz-note">No reserved layout for this coach type.</p>`;
    host.hidden = false;
  }

  // deep link: /coaches/?train=12626
  const qp = new URLSearchParams(location.search);
  const pre = qp.get("train");
  if (pre) { input.value = pre; loadTrain(pre); }
})();