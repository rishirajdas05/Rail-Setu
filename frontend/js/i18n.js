// RailSetu i18n powered by Groq translation (any language), with caching.
// English is the source: every element tagged data-i18n / data-i18n-html /
// data-i18n-ph / data-i18n-aria holds its English text. Switching language sends
// the unique English strings to /api/translate/ once, caches the result in
// localStorage, and applies it. Switching back to English restores the originals.
(function () {
  "use strict";
  var KEY = "railsetu_lang";
  var cachePrefix = "railsetu_tr_"; // + lang  -> JSON map {src: translated}

  // language options shown in the navbar selector
  var LANGS = [
    ["en", "English"], ["hi", "\u0939\u093f\u0928\u094d\u0926\u0940"],
    ["bn", "\u09ac\u09be\u0982\u09b2\u09be"], ["ta", "\u0ba4\u0bae\u0bbf\u0bb4\u0bcd"],
    ["te", "\u0c24\u0c46\u0c32\u0c41\u0c17\u0c41"], ["mr", "\u092e\u0930\u093e\u0920\u0940"],
    ["gu", "\u0a97\u0ac1\u0a9c\u0ab0\u0abe\u0aa4\u0c40".slice(0, 7)], ["kn", "\u0c95\u0ca8\u0ccd\u0ca8\u0ca1"],
    ["pa", "\u0a2a\u0a70\u0a1c\u0a3e\u0a2c\u0a40"],
  ];

  var originals = []; // [{el, kind, src}]
  var tracked = (window.WeakSet ? new WeakSet() : null);

  function lang() {
    var v = null;
    try { v = localStorage.getItem(KEY); } catch (e) {}
    return v || "en";
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
    var sel = document.getElementById("lang-select");
    if (sel) sel.disabled = on;
    document.documentElement.style.cursor = on ? "progress" : "";
  }

  async function applyLang(l) {
    document.documentElement.setAttribute("lang", l);
    if (l === "en") { restoreEnglish(); return; }

    var cache = loadCache(l);
    var unique = [];
    var seen = {};
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
        // not configured / failed: stay English
        restoreEnglish();
        try { localStorage.setItem(KEY, "en"); } catch (e) {}
        syncSelect("en");
      }
    } catch (e) {
      restoreEnglish();
    } finally {
      setBusy(false);
    }
  }

  function syncSelect(l) {
    var sel = document.getElementById("lang-select");
    if (sel) sel.value = l;
  }

  function buildSelect() {
    var sel = document.getElementById("lang-select");
    if (!sel) return;
    sel.innerHTML = LANGS.map(function (p) {
      return '<option value="' + p[0] + '">' + p[1] + "</option>";
    }).join("");
    sel.value = lang();
    sel.addEventListener("change", function () {
      var l = sel.value;
      try { localStorage.setItem(KEY, l); } catch (e) {}
      applyLang(l);
    });
  }

  window.RailI18n = {
    lang: lang,
    apply: function () { applyLang(lang()); },
    refresh: function () { collect(); applyLang(lang()); },
  };

  function init() {
    collect();
    buildSelect();
    if (lang() !== "en") applyLang(lang());
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();