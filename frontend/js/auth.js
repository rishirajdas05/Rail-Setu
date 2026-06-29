// Shared auth state for RailSetu. Included on every page.
(function () {
  "use strict";

  const KEY = {
    access: "railsetu_access",
    refresh: "railsetu_refresh",
    user: "railsetu_user",
    staff: "railsetu_is_staff",
  };

  const RailAuth = {
    get access() { return localStorage.getItem(KEY.access) || ""; },
    get refresh() { return localStorage.getItem(KEY.refresh) || ""; },
    get user() { return localStorage.getItem(KEY.user) || ""; },
    get isStaff() { return localStorage.getItem(KEY.staff) === "1"; },
    isAuthed() { return !!this.access; },
    setSession(access, refresh, user) {
      if (access) localStorage.setItem(KEY.access, access);
      if (refresh) localStorage.setItem(KEY.refresh, refresh);
      if (user) localStorage.setItem(KEY.user, user);
      updateHeader();
      refreshStaff();
    },
    clear() {
      localStorage.removeItem(KEY.access);
      localStorage.removeItem(KEY.refresh);
      localStorage.removeItem(KEY.user);
      localStorage.removeItem(KEY.staff);
      updateHeader();
    },
    authHeader() { return this.access ? { Authorization: "Bearer " + this.access } : {}; },
  };
  window.RailAuth = RailAuth;

  function updateHeader() {
    // staff-only Dashboard link (present in every navbar, hidden by default)
    const dash = document.getElementById("nav-dash");
    if (dash) dash.hidden = !(RailAuth.isAuthed() && RailAuth.isStaff);

    const link = document.getElementById("signin-link");
    if (!link) return;
    if (RailAuth.isAuthed()) {
      link.textContent = RailAuth.user || "Account";
      link.href = "/account/";
      link.classList.add("is-user");
      link.onclick = null;
    } else {
      link.textContent = "Sign in";
      link.href = "/login/";
      link.classList.remove("is-user");
      link.onclick = null;
    }
  }

  // Confirm staff status from the server and cache it, so the Dashboard link
  // shows only for staff accounts across all pages.
  async function refreshStaff() {
    if (!RailAuth.isAuthed()) return;
    try {
      const res = await fetch("/api/auth/me/", { headers: { ...RailAuth.authHeader() } });
      if (!res.ok) return;
      const me = await res.json();
      localStorage.setItem(KEY.staff, me.is_staff ? "1" : "0");
      updateHeader();
    } catch (e) {
      /* offline: leave cached value as-is */
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    updateHeader();
    refreshStaff();
  });
})();