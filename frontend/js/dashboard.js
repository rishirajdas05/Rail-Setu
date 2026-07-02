// RailSetu shared dropdown.
// Converts normal form <select> fields into styled dropdowns.
// The navbar language selector is skipped completely because i18n.js handles it.

(function () {
  "use strict";

  function shouldSkip(select) {
    return (
      !select ||
      select.hidden ||
      select.id === "lang-select" ||
      select.classList.contains("lang-select") ||
      select.closest(".rs-lang")
    );
  }

  function closeOthers(currentWrap) {
    document.querySelectorAll(".rs-select.open").forEach(function (wrap) {
      if (wrap !== currentWrap) {
        wrap.classList.remove("open");

        var pop = wrap.querySelector(".rs-select-pop");

        if (pop) {
          pop.hidden = true;
        }
      }
    });
  }

  function enhance(select) {
    if (shouldSkip(select) || select.dataset.ddReady === "1") return;

    select.dataset.ddReady = "1";

    var wrap = document.createElement("div");
    wrap.className = "rs-select";

    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);

    select.style.display = "none";
    select.tabIndex = -1;

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "rs-select-btn";

    var pop = document.createElement("div");
    pop.className = "rs-select-pop";
    pop.hidden = true;

    wrap.appendChild(btn);
    wrap.appendChild(pop);

    function syncLabel() {
      var selected = select.options[select.selectedIndex];
      btn.textContent = selected ? selected.textContent : "";
      btn.disabled = select.disabled;
    }

    function buildOptions() {
      pop.innerHTML = "";

      Array.from(select.options).forEach(function (option, index) {
        var item = document.createElement("button");
        item.type = "button";
        item.className = "rs-option" + (index === select.selectedIndex ? " is-sel" : "");
        item.textContent = option.textContent;

        item.addEventListener("click", function () {
          select.selectedIndex = index;
          select.dispatchEvent(new Event("change", { bubbles: true }));
          syncLabel();
          close();
        });

        pop.appendChild(item);
      });
    }

    function open() {
      if (select.disabled) return;

      closeOthers(wrap);
      buildOptions();

      wrap.classList.add("open");
      pop.hidden = false;
    }

    function close() {
      wrap.classList.remove("open");
      pop.hidden = true;
    }

    btn.addEventListener("click", function (event) {
      event.stopPropagation();

      if (pop.hidden) {
        open();
      } else {
        close();
      }
    });

    document.addEventListener("click", function (event) {
      if (!wrap.contains(event.target)) {
        close();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        close();
      }
    });

    select.addEventListener("change", syncLabel);

    new MutationObserver(syncLabel).observe(select, {
      childList: true,
      attributes: true,
      attributeFilter: ["disabled"],
    });

    syncLabel();
  }

  function enhanceAll() {
    document
      .querySelectorAll("select:not(#lang-select):not(.lang-select):not([hidden])")
      .forEach(enhance);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhanceAll);
  } else {
    enhanceAll();
  }

  window.RailDropdown = {
    enhanceAll: enhanceAll,
    enhance: enhance,
  };
})();