// RailSetu i18n powered by Groq translation (any language), with caching.
// English is the source: every element tagged data-i18n / data-i18n-html /
// data-i18n-ph / data-i18n-aria holds its English text. Switching language sends
// the unique English strings to /api/translate/ once, caches the result in
// localStorage, and applies it. Switching back to English restores the originals.
// The navbar <select id="lang-select"> is progressively enhanced into a custom
// dropdown; if JS is off the native select still works.
(function () {
  "use strict";
  var KEY = "railsetu_lang";
  var cachePrefix = "railsetu_tr_"; // + lang -> JSON map {src: translated}

  var LANGS = [
    ["en", "English"], ["hi", "\u0939\u093f\u0928\u094d\u0926\u0940"],
    ["bn", "\u09ac\u09be\u0982\u09b2\u09be"], ["ta", "\u0ba4\u0bae\u0bbf\u0bb4\u0bcd"],
    ["te", "\u0c24\u0c46\u0c32\u0c41\u0c17\u0c41"], ["mr", "\u092e\u0930\u093e\u0920\u0940"],
    ["gu", "\u0a97\u0ac1\u0a9c\u0ab0\u0abe\u0aa4\u0ac0"], ["kn", "\u0c95\u0ca8\u0ccd\u0ca8\u0ca1"],
    ["pa", "\u0a2a\u0a70\u0a1c\u0a3e\u0a2c\u0a40"],
  ];

  var originals = [];
  var tracked = (window.WeakSet ? new WeakSet() : null);
  var ddWrap, ddBtn, ddMenu, ddCur;

  function lang() {
    var v = null;
    try { v = localStorage.getItem(KEY); } catch (e) {}
    return v || "en";
  }
  function langName(code) {
    for (var i = 0; i < LANGS.length; i++) { if (LANGS[i][0] === code) return LANGS[i][1]; }
    return code;
  }

  function collect() {
    function add(el, kind, src) {
      if (tracked && tracked.has(el)) return;
      if (tracked) tracked.add(el);
      originals.push({ el: el, kind: kind, src: src });
    }
    document.querySelectorAll("[data-i18n]").forEach(function (el) { add(el, "text", el.textContent.trim()); });
    document.querySelectorAll("[data-i18n-html]").forEach(function (el) { add(el, "html", el.innerHTML.trim()); });
    document.querySelectorAll("[data-i18n-ph]").forEach(function (el) { add(el, "ph", el.getAttribute("placeholder") || ""); });
    document.querySelectorAll("[data-i18n-aria]").forEach(function (el) { add(el, "aria", el.getAttribute("aria-label") || ""); });
  }

  function setEl(item, value) {
    if (item.kind === "text") item.el.textContent = value;
    else if (item.kind === "html") item.el.innerHTML = value;
    else if (item.kind === "ph") item.el.setAttribute("placeholder", value);
    else if (item.kind === "aria") item.el.setAttribute("aria-label", value);
  }

  function restoreEnglish() {
    originals.forEach(function (it) { setEl(it, it.src); });
    document.documentElement.setAttribute("lang", "en");
  }

  function loadCache(l) {
    try { return JSON.parse(localStorage.getItem(cachePrefix + l) || "{}"); } catch (e) { return {}; }
  }
  function saveCache(l, map) {
    try { localStorage.setItem(cachePrefix + l, JSON.stringify(map)); } catch (e) {}
  }

  function applyMap(map) {
    originals.forEach(function (it) {
      var v = map[it.src];
      setEl(it, v != null ? v : it.src);
    });
  }

  function setBusy(on) {
    if (ddBtn) ddBtn.disabled = on;
    if (ddWrap) ddWrap.classList.toggle("is-busy", on);
    document.documentElement.style.cursor = on ? "progress" : "";
  }

  async function applyLang(l) {
    document.documentElement.setAttribute("lang", l);
    if (l === "en") { restoreEnglish(); return; }

    var cache = loadCache(l);
    var unique = [], seen = {};
    originals.forEach(function (it) {
      if (it.src && cache[it.src] == null && !seen[it.src]) { seen[it.src] = 1; unique.push(it.src); }
    });
    if (unique.length === 0) { applyMap(cache); return; }

    setBusy(true);
    try {
      var res = await fetch("/api/translate/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_lang: l, texts: unique }),
      });
      if (res.ok) {
        var data = await res.json();
        var tr = data.translations || [];
        unique.forEach(function (src, i) { cache[src] = tr[i] != null ? tr[i] : src; });
        saveCache(l, cache);
        applyMap(cache);
      } else {
        restoreEnglish();
        try { localStorage.setItem(KEY, "en"); } catch (e) {}
        setCurrent("en");
      }
    } catch (e) {
      restoreEnglish();
    } finally {
      setBusy(false);
    }
  }

  // ---- custom dropdown ----
  var GLOBE = "<svg class='lang-dd-globe' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.7'><circle cx='12' cy='12' r='9'/><path d='M3 12h18' stroke-linecap='round'/><path d='M12 3c2.6 2.7 2.6 15.3 0 18M12 3c-2.6 2.7-2.6 15.3 0 18'/></svg>";
  var CHEV = "<svg class='lang-dd-chev' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'><path d='m6 9 6 6 6-6'/></svg>";
  var CHECK = "<svg class='lang-dd-check' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.8' stroke-linecap='round' stroke-linejoin='round'><path d='M20 6 9 17l-5-5'/></svg>";

  function closeMenu() {
    if (!ddWrap) return;
    ddWrap.classList.remove("open");
    ddBtn.setAttribute("aria-expanded", "false");
  }
  function openMenu() {
    if (!ddWrap || ddBtn.disabled) return;
    ddWrap.classList.add("open");
    ddBtn.setAttribute("aria-expanded", "true");
  }
  function toggleMenu() { ddWrap.classList.contains("open") ? closeMenu() : openMenu(); }

  function setCurrent(l) {
    if (ddCur) ddCur.textContent = langName(l);
    if (ddMenu) {
      ddMenu.querySelectorAll(".lang-dd-opt").forEach(function (o) {
        var on = o.getAttribute("data-val") === l;
        o.classList.toggle("is-active", on);
        o.setAttribute("aria-selected", on ? "true" : "false");
      });
    }
  }

  function buildDropdown() {
    var sel = document.getElementById("lang-select");
    if (!sel) return;
    var cur = lang();
    ddWrap = document.createElement("div");
    ddWrap.className = "lang-dd";
    ddWrap.id = "lang-dd";
    ddWrap.innerHTML =
      "<button type='button' class='lang-dd-btn' id='lang-dd-btn' aria-haspopup='listbox' aria-expanded='false' aria-label='Language'>" +
        GLOBE + "<span class='lang-dd-cur'>" + langName(cur) + "</span>" + CHEV +
      "</button>" +
      "<ul class='lang-dd-menu' role='listbox' tabindex='-1'>" +
        LANGS.map(function (p) {
          return "<li class='lang-dd-opt' role='option' data-val='" + p[0] + "' aria-selected='false'>" +
                 "<span class='lang-dd-lbl'>" + p[1] + "</span>" + CHECK + "</li>";
        }).join("") +
      "</ul>";
    sel.replaceWith(ddWrap);
    ddBtn = ddWrap.querySelector(".lang-dd-btn");
    ddMenu = ddWrap.querySelector(".lang-dd-menu");
    ddCur = ddWrap.querySelector(".lang-dd-cur");

    ddBtn.addEventListener("click", function (e) { e.stopPropagation(); toggleMenu(); });
    ddMenu.addEventListener("click", function (e) {
      var opt = e.target.closest(".lang-dd-opt");
      if (!opt) return;
      var l = opt.getAttribute("data-val");
      try { localStorage.setItem(KEY, l); } catch (err) {}
      setCurrent(l);
      closeMenu();
      applyLang(l);
    });
    document.addEventListener("click", function (e) { if (ddWrap && !ddWrap.contains(e.target)) closeMenu(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeMenu(); });

    setCurrent(cur);
  }

  window.RailI18n = {
    lang: lang,
    apply: function () { applyLang(lang()); },
    refresh: function () { collect(); applyLang(lang()); },
  };

  function init() {
    collect();
    buildDropdown();
    if (lang() !== "en") applyLang(lang());
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();