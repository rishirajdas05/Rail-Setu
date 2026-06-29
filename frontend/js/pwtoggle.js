// RailSetu: reusable show/hide toggle for password inputs.
// Any <button class="pw-toggle" data-pw-toggle="INPUT_ID"> is wired automatically.
//
// Reveal works by switching the input between type="password" and type="text".
// We track the shown state on a local variable (instead of reading input.type)
// and we do NOT call input.focus() after toggling: focusing a managed
// current-password field pops the browser's saved-password dropdown over the
// box, which made the reveal look like it had failed.
(function () {
  "use strict";

  function wire(btn) {
    if (btn.dataset.pwReady) return;
    btn.dataset.pwReady = "1";
    const input = document.getElementById(btn.dataset.pwToggle);
    if (!input) return;

    let shown = false;

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      shown = !shown;
      // Clear any stale masking style a previous build may have set inline.
      input.style.removeProperty("-webkit-text-security");
      input.style.removeProperty("text-security");
      input.type = shown ? "text" : "password";
      btn.classList.toggle("is-shown", shown);
      btn.setAttribute("aria-label", shown ? "Hide password" : "Show password");
      btn.setAttribute("aria-pressed", shown ? "true" : "false");
    });
  }

  function init(root) {
    (root || document).querySelectorAll("[data-pw-toggle]").forEach(wire);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => init());
  } else {
    init();
  }
  window.RailPwToggle = { init };
})();