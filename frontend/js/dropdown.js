// RailSetu shared dropdown. Progressively enhances every <select> into a styled
// menu while keeping the real <select> in the DOM, so the page's own scripts keep
// reading and setting select.value exactly as before. The option list is built
// from the live <select> on open, so selects filled dynamically by other scripts
// (class, quota) just work.
(function () {
  "use strict";

  function enhance(select) {
    if (select.dataset.ddReady) return;
    select.dataset.ddReady = "1";

    const wrap = document.createElement("div");
    wrap.className = "rs-select";
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);
    select.style.display = "none";
    select.tabIndex = -1;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "rs-select-btn";
    wrap.appendChild(btn);

    const pop = document.createElement("div");
    pop.className = "rs-select-pop";
    pop.hidden = true;
    wrap.appendChild(pop);

    function syncLabel() {
      const o = select.options[select.selectedIndex];
      btn.textContent = o ? o.textContent : "";
    }

    function buildList() {
      pop.innerHTML = "";
      Array.from(select.options).forEach((opt, i) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "rs-option" + (i === select.selectedIndex ? " is-sel" : "");
        item.textContent = opt.textContent;
        item.addEventListener("click", () => {
          select.selectedIndex = i;
          select.dispatchEvent(new Event("change", { bubbles: true }));
          syncLabel();
          close();
        });
        pop.appendChild(item);
      });
    }

    function open() {
      buildList();
      pop.hidden = false;
      wrap.classList.add("open");
    }
    function close() {
      pop.hidden = true;
      wrap.classList.remove("open");
    }

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      pop.hidden ? open() : close();
    });
    document.addEventListener("click", (e) => { if (!wrap.contains(e.target)) close(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });

    // keep the label in sync when other scripts fill options or change value
    select.addEventListener("change", syncLabel);
    new MutationObserver(syncLabel).observe(select, { childList: true });

    syncLabel();
  }

  function enhanceAll() {
    document.querySelectorAll("select").forEach(enhance);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhanceAll);
  } else {
    enhanceAll();
  }
  // expose in case a script adds selects later
  window.RailDropdown = { enhanceAll, enhance };
})();