// RailSetu theme: applies saved/system theme before paint, wires the toggle.
(function () {
  var KEY = "railsetu_theme";
  function apply(t) {
    if (t === "dark") document.documentElement.setAttribute("data-theme", "dark");
    else document.documentElement.removeAttribute("data-theme");
  }
  function current() {
    var saved = null;
    try { saved = localStorage.getItem(KEY); } catch (e) {}
    if (saved === "dark" || saved === "light") return saved;
    return (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
  }
  apply(current()); // runs in <head>, before the body paints

  function wire() {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      apply(next);
      try { localStorage.setItem(KEY, next); } catch (e) {}
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();
})();