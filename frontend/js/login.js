// RailSetu login + signup logic.
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const form = $("auth-form");
  const card = $("auth-card");
  const tabLogin = $("tab-login");
  const tabSignup = $("tab-signup");
  const emailField = $("email-field");
  const nameField = $("name-field");
  const confirmField = $("confirm-field");
  const pwHint = $("pw-hint");
  const titleEl = $("auth-title");
  const subEl = $("auth-subtitle");
  const submit = $("auth-submit");
  const errorEl = $("auth-error");
  const switchEl = $("auth-switch");

  let mode = "login"; // or "signup"

  // If already signed in, no reason to be here.
  if (window.RailAuth && RailAuth.isAuthed()) {
    location.href = "/";
    return;
  }

  // allow ?next=/somewhere to redirect after auth
  const nextUrl = new URLSearchParams(location.search).get("next") || "/";

  const LAST_USER_KEY = "railsetu_last_user";

  const COPY = {
    login: {
      title: "Welcome back",
      sub: "Sign in to manage your bookings and trips.",
      button: "Sign in",
      switch: 'New here? <a href="#" id="go-signup">Create an account</a>',
    },
    signup: {
      title: "Create your account",
      sub: "Join RailSetu to book, track delays, and predict confirmations.",
      button: "Create account",
      switch: 'Already have an account? <a href="#" id="go-login">Sign in</a>',
    },
  };

  function rememberUser(name) {
    try { if (name) localStorage.setItem(LAST_USER_KEY, name); } catch (e) {}
  }
  // Prefill the username from the last successful sign-in.
  try {
    const last = localStorage.getItem(LAST_USER_KEY);
    if (last) $("username").value = last;
  } catch (e) {}

  function setMode(m) {
    mode = m;
    const signup = m === "signup";
    const c = COPY[m];

    tabLogin.classList.toggle("is-active", !signup);
    tabSignup.classList.toggle("is-active", signup);
    if (card) card.classList.toggle("is-signup", signup);

    emailField.hidden = !signup;
    if (nameField) nameField.hidden = !signup;
    if (confirmField) confirmField.hidden = !signup;
    pwHint.hidden = !signup;

    if (titleEl) titleEl.textContent = c.title;
    if (subEl) subEl.textContent = c.sub;
    submit.textContent = c.button;

    const pw = $("password");
    if (pw) pw.setAttribute("autocomplete", signup ? "new-password" : "current-password");

    errorEl.textContent = "";
    switchEl.innerHTML = c.switch;
    const go = $(signup ? "go-login" : "go-signup");
    if (go) go.addEventListener("click", (e) => { e.preventDefault(); setMode(signup ? "login" : "signup"); });
  }

  tabLogin.addEventListener("click", () => setMode("login"));
  tabSignup.addEventListener("click", () => setMode("signup"));

  function setError(msg) { errorEl.textContent = msg || ""; }

  async function postJSON(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    let data = {};
    try { data = await res.json(); } catch (e) {}
    return { res, data };
  }

  // Turn DRF error payloads into a readable line.
  function firstError(data, fallback) {
    if (!data || typeof data !== "object") return fallback;
    if (data.detail) return data.detail;
    for (const k of Object.keys(data)) {
      const v = data[k];
      if (Array.isArray(v) && v.length) return `${k}: ${v[0]}`;
      if (typeof v === "string") return `${k}: ${v}`;
    }
    return fallback;
  }

  async function login(username, password) {
    const { res, data } = await postJSON("/api/auth/login/", { username, password });
    if (!res.ok) {
      setError(firstError(data, "Invalid username or password."));
      return false;
    }
    RailAuth.setSession(data.access, data.refresh, username);
    rememberUser(username);
    return true;
  }

  async function signup(username, email, password, fullName) {
    const body = { username, email, password };
    const name = (fullName || "").trim();
    if (name) {
      const sp = name.indexOf(" ");
      body.first_name = sp === -1 ? name : name.slice(0, sp);
      body.last_name = sp === -1 ? "" : name.slice(sp + 1).trim();
    }
    const { res, data } = await postJSON("/api/auth/register/", body);
    if (!res.ok) {
      setError(firstError(data, "Could not create the account."));
      return false;
    }
    // registration succeeds but returns no token; log in to get one
    return login(username, password);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError("");
    const username = $("username").value.trim();
    const password = $("password").value;
    const email = $("email").value.trim();
    const fullName = $("fullname") ? $("fullname").value.trim() : "";

    if (!username || !password) { setError("Enter a username and password."); return; }
    if (mode === "signup") {
      if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
      const confirm = $("password2") ? $("password2").value : password;
      if (password !== confirm) { setError("The two passwords do not match."); return; }
    }

    submit.disabled = true;
    submit.textContent = mode === "signup" ? "Creating…" : "Signing in…";
    try {
      const ok = mode === "signup"
        ? await signup(username, email, password, fullName)
        : await login(username, password);
      if (ok) { location.href = nextUrl; return; }
    } catch (err) {
      setError("Network error. Is the server running?");
    }
    submit.disabled = false;
    submit.textContent = COPY[mode].button;
  });

  // start in the mode named by ?mode=signup, else login
  setMode(new URLSearchParams(location.search).get("mode") === "signup" ? "signup" : "login");

  // ---- Sign in with Google (classic redirect flow) ----
  // The button is a normal link to the backend, which redirects to Google and back.
  const gLink = $("google-link");
  if (gLink && nextUrl && nextUrl !== "/") {
    gLink.href = "/auth/google/login/?next=" + encodeURIComponent(nextUrl);
  }
})();