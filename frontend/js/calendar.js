// RailSetu shared date picker. Progressively enhances every <input type="date">
// on the page into a styled calendar, preserving the input's id and value so the
// page's own scripts keep reading input.value exactly as before.
(function () {
  "use strict";

  const MONTHS = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];
  const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  const localISO = (d) => {
    const x = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
    return x.toISOString().slice(0, 10);
  };
  const todayISO = localISO(new Date());
  const fmt = (iso) => { const [y, m, d] = iso.split("-").map(Number); return `${d} ${MON[m - 1]} ${y}`; };

  function enhance(input) {
    if (input.dataset.calReady) return;
    input.dataset.calReady = "1";

    const wrap = document.createElement("div");
    wrap.className = "rs-datefield";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    input.type = "hidden";

    const display = document.createElement("button");
    display.type = "button";
    display.className = "date-display";
    wrap.appendChild(display);

    const pop = document.createElement("div");
    pop.className = "cal-pop";
    pop.hidden = true;
    pop.innerHTML =
      '<div class="cal-head">' +
      '<button type="button" class="cal-nav cal-prev" aria-label="Previous month">&lsaquo;</button>' +
      '<span class="cal-title"></span>' +
      '<button type="button" class="cal-nav cal-next" aria-label="Next month">&rsaquo;</button>' +
      '</div>' +
      '<div class="cal-dow"><span>Mo</span><span>Tu</span><span>We</span><span>Th</span><span>Fr</span><span>Sa</span><span>Su</span></div>' +
      '<div class="cal-grid"></div>';
    wrap.appendChild(pop);

    const title = pop.querySelector(".cal-title");
    const grid = pop.querySelector(".cal-grid");

    const valid = input.value && /^\d{4}-\d{2}-\d{2}$/.test(input.value);
    let sel = valid ? input.value : todayISO;
    let view = new Date(sel + "T00:00:00");
    view = new Date(view.getFullYear(), view.getMonth(), 1);

    function setDate(iso) {
      sel = iso;
      input.value = iso;
      display.textContent = fmt(iso);
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function render() {
      title.textContent = `${MONTHS[view.getMonth()]} ${view.getFullYear()}`;
      const start = (new Date(view.getFullYear(), view.getMonth(), 1).getDay() + 6) % 7;
      const days = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();
      let cells = "";
      for (let i = 0; i < start; i++) cells += '<span class="cal-cell empty"></span>';
      for (let d = 1; d <= days; d++) {
        const iso = localISO(new Date(view.getFullYear(), view.getMonth(), d));
        const past = iso < todayISO;
        const cls = ["cal-cell"];
        if (past) cls.push("disabled");
        if (iso === sel) cls.push("selected");
        else if (iso === todayISO) cls.push("today");
        cells += `<button type="button" class="${cls.join(" ")}" data-iso="${iso}" ${past ? "disabled" : ""}>${d}</button>`;
      }
      grid.innerHTML = cells;
    }

    display.addEventListener("click", (e) => {
      e.stopPropagation();
      pop.hidden = !pop.hidden;
      if (!pop.hidden) render();
    });
    pop.querySelector(".cal-prev").addEventListener("click", (e) => { e.stopPropagation(); view.setMonth(view.getMonth() - 1); render(); });
    pop.querySelector(".cal-next").addEventListener("click", (e) => { e.stopPropagation(); view.setMonth(view.getMonth() + 1); render(); });
    grid.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-iso]");
      if (!b || b.disabled) return;
      setDate(b.dataset.iso);
      pop.hidden = true;
    });
    document.addEventListener("click", (e) => { if (!wrap.contains(e.target)) pop.hidden = true; });

    setDate(sel);
  }

  function init() {
    document.querySelectorAll('input[type="date"]').forEach(enhance);
  }
  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);
})();