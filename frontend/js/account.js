// RailSetu account page: profile + past bookings.
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  const loading = $("ac-loading");
  const errorEl = $("ac-error");
  const body = $("ac-body");
  const listEl = $("ac-list");
  const emptyEl = $("ac-empty");
  const moreBtn = $("ac-more");

  // must be signed in
  if (!window.RailAuth || !RailAuth.isAuthed()) {
    location.href = "/login/?next=" + encodeURIComponent("/account/");
    return;
  }

  let nextUrl = null;
  let total = 0;

  function statusPill(s, label) {
    const cls = s === "CNF" ? "ok" : s === "RAC" ? "warn" : s === "WL" ? "wait" : "cancel";
    return `<span class="pill ${cls}">${esc(label || s)}</span>`;
  }

  function fmtDate(iso) {
    // booked_at -> readable date
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return iso.slice(0, 10);
    return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  }

  function bookingCard(b) {
    const pax = (b.passengers || []).map((p) =>
      `<li>${esc(p.name)} <span class="ac-seat">${esc(p.coach || "—")} ${esc(p.berth || "")} · ${esc(p.status_display || p.status)}</span></li>`
    ).join("");

    return `
      <article class="ac-booking">
        <div class="ac-booking-top">
          <div>
            <span class="ac-pnr">${esc(b.pnr)}</span>
            <span class="ac-train">${esc(b.train_number)} · ${esc(b.train_name)}</span>
          </div>
          ${statusPill(b.status, b.status_display)}
        </div>
        <p class="ac-booking-meta">
          ${esc(b.from_code)} → ${esc(b.to_code)} · ${esc(b.journey_date)} · ${esc(b.travel_class)} · ₹${esc(b.total_fare)}
          <span class="ac-booked">booked ${esc(fmtDate(b.booked_at))}</span>
        </p>
        <ul class="ac-pax">${pax}</ul>
        <div class="ac-booking-actions">
          <button type="button" class="ac-ticket" data-pnr="${esc(b.pnr)}">Download e-ticket</button>
          <a class="bk-link" href="/pnr/?pnr=${encodeURIComponent(b.pnr)}">PNR status</a>
          <a class="bk-link" href="/status/?train=${encodeURIComponent(b.train_number)}&start_day=1">Live status</a>
          ${b.status !== "CAN" ? `<button type="button" class="ac-cancel" data-pnr="${esc(b.pnr)}">Cancel booking</button>` : ""}
        </div>
      </article>`;
  }

  async function fetchJSON(url) {
    const res = await fetch(url, { headers: { ...RailAuth.authHeader() } });
    if (res.status === 401) {
      RailAuth.clear();
      location.href = "/login/?next=" + encodeURIComponent("/account/");
      throw new Error("unauthorized");
    }
    return res.json();
  }

  let allLoaded = [];

  function todayStr() {
    return new Date().toISOString().slice(0, 10);
  }

  function refreshStats() {
    const t = todayStr();
    const cnf = allLoaded.filter((b) => b.status === "CNF").length;
    const upc = allLoaded.filter(
      (b) => b.status !== "CAN" && String(b.journey_date || "") >= t
    ).length;
    const set = (id, n) => { const el = $(id); if (el) el.textContent = n; };
    set("ac-stat-total", total || allLoaded.length);
    set("ac-stat-cnf", cnf);
    set("ac-stat-upc", upc);
  }

  function renderBookings(page, append) {
    const results = page.results || (Array.isArray(page) ? page : []);
    if (typeof page.count === "number") total = page.count;
    nextUrl = page.next || null;

    if (!append) { listEl.innerHTML = ""; allLoaded = []; }
    allLoaded = allLoaded.concat(results);
    if (!results.length && !append) {
      emptyEl.hidden = false;
    } else {
      listEl.insertAdjacentHTML("beforeend", results.map(bookingCard).join(""));
    }
    $("ac-count").textContent = total ? `${total} total` : "";
    refreshStats();
    moreBtn.hidden = !nextUrl;
    listEl.querySelectorAll(".ac-ticket").forEach((btn) => {
      if (btn.dataset.wired) return;
      btn.dataset.wired = "1";
      btn.addEventListener("click", () => downloadTicket(btn.dataset.pnr, btn));
    });
    listEl.querySelectorAll(".ac-cancel").forEach((btn) => {
      if (btn.dataset.wired) return;
      btn.dataset.wired = "1";
      btn.addEventListener("click", () => cancelBooking(btn.dataset.pnr, btn));
    });
  }

  async function cancelBooking(pnr, btn) {
    if (!window.confirm("Cancel this booking? This cannot be undone.")) return;
    btn.disabled = true;
    const orig = btn.textContent;
    btn.textContent = "Cancelling…";
    try {
      const res = await fetch(`/api/bookings/${encodeURIComponent(pnr)}/cancel/`, {
        method: "POST",
        headers: { ...RailAuth.authHeader() },
      });
      if (res.status === 401) {
        RailAuth.clear();
        location.href = "/login/?next=" + encodeURIComponent("/account/");
        return;
      }
      const d = await res.json();
      if (!res.ok) {
        btn.disabled = false;
        btn.textContent = orig;
        alert(d.detail || "Could not cancel this booking.");
        return;
      }
      const card = btn.closest(".ac-booking");
      if (card) {
        const pill = card.querySelector(".pill");
        if (pill) { pill.className = "pill cancel"; pill.textContent = "Cancelled"; }
        card.querySelectorAll(".ac-pax .ac-seat").forEach((s) => {
          s.textContent = s.textContent.replace(/·.*$/, "· Cancelled");
        });
        const note = document.createElement("p");
        note.className = "ac-refund";
        note.innerHTML =
          `Refund ₹${esc(d.refund)} <span>charge ₹${esc(d.cancellation_charge)} · ${esc(d.rule)}</span>`;
        const actions = card.querySelector(".ac-booking-actions");
        if (actions) card.insertBefore(note, actions);
        else card.appendChild(note);
      }
      const hit = allLoaded.find((b) => b.pnr === pnr);
      if (hit) hit.status = "CAN";
      refreshStats();
      btn.remove();
    } catch (e) {
      btn.disabled = false;
      btn.textContent = orig;
      alert("Could not cancel this booking.");
    }
  }

  async function downloadTicket(pnr, btn) {
    const original = btn.textContent;
    btn.disabled = true; btn.textContent = "Preparing...";
    try {
      const res = await fetch(`/api/bookings/${encodeURIComponent(pnr)}/ticket/`, {
        headers: { ...RailAuth.authHeader() },
      });
      if (!res.ok) throw new Error("ticket");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `RailSetu-${pnr}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      btn.textContent = "Could not download";
    } finally {
      btn.disabled = false;
      setTimeout(() => { btn.textContent = original; }, 1500);
    }
  }

  async function loadSaved() {
    const host = $("ac-saved-list");
    const empty = $("ac-saved-empty");
    const count = $("ac-saved-count");
    if (!host || !window.RailSaved) return;
    const items = await RailSaved.list();
    if (count) count.textContent = items.length ? `${items.length} saved` : "";
    if (!items.length) {
      host.innerHTML = "";
      if (empty) empty.hidden = false;
      return;
    }
    if (empty) empty.hidden = true;
    host.innerHTML = items
      .map((it) => {
        const tag = it.kind === "route" ? "Route" : "Train";
        return `
        <div class="sv-row">
          <a class="sv-main" href="${esc(it.url || "#")}">
            <span class="sv-tag sv-${esc(it.kind)}">${tag}</span>
            <span class="sv-label">${esc(it.label)}</span>
            ${it.subtitle ? `<span class="sv-sub">${esc(it.subtitle)}</span>` : ""}
          </a>
          <button type="button" class="sv-del" data-id="${esc(it.id)}" aria-label="Remove">Remove</button>
        </div>`;
      })
      .join("");
    host.querySelectorAll(".sv-del").forEach((btn) =>
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          await RailSaved.remove(btn.dataset.id);
          await loadSaved();
        } catch (e) {
          btn.disabled = false;
        }
      })
    );
  }

  async function loadAlerts() {
    const host = $("ac-alerts-list");
    const empty = $("ac-alerts-empty");
    const count = $("ac-alerts-count");
    if (!host || !window.RailAlerts) return;
    const items = await RailAlerts.list();
    if (count) count.textContent = items.length ? `${items.length}` : "";
    if (!items.length) {
      host.innerHTML = "";
      if (empty) empty.hidden = false;
      return;
    }
    if (empty) empty.hidden = true;
    host.innerHTML = items
      .map((a) => {
        const cond = a.kind === "fare" ? `Fare \u2264 \u20b9${esc(a.threshold)}` : "Seat clears";
        const badgeCls = a.status === "triggered" ? "is-hit" : a.status === "expired" ? "is-exp" : "is-act";
        const badgeTxt = a.status === "triggered" ? "Triggered" : a.status === "expired" ? "Expired" : "Active";
        const last = a.last_value ? ` · last seen ${esc(a.last_value)}` : "";
        return `
        <div class="sv-row">
          <a class="sv-main" href="/train/${esc(a.train_number)}/?from=${esc(a.from_code)}&to=${esc(a.to_code)}&date=${esc(a.journey_date)}">
            <span class="al-badge ${badgeCls}">${badgeTxt}</span>
            <span class="sv-label">${esc(a.train_number)} · ${esc(a.travel_class)} · ${cond}</span>
            <span class="sv-sub">${esc(a.from_code)} → ${esc(a.to_code)} · ${esc(a.journey_date)}${last}</span>
          </a>
          <button type="button" class="sv-del" data-id="${esc(a.id)}" aria-label="Remove">Remove</button>
        </div>`;
      })
      .join("");
    host.querySelectorAll(".sv-del").forEach((btn) =>
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          await RailAlerts.remove(btn.dataset.id);
          await loadAlerts();
        } catch (e) {
          btn.disabled = false;
        }
      })
    );
  }

  async function init() {
    try {
      const me = await fetchJSON("/api/auth/me/");
      $("ac-username").textContent = me.username || "";
      $("ac-email").textContent = me.email || "No email on file";
      $("ac-avatar").textContent = (me.username || "?").charAt(0).toUpperCase();
      if (me.is_staff) { const dl = $("ac-dash"); if (dl) dl.hidden = false; }

      const page = await fetchJSON("/api/bookings/");
      renderBookings(page, false);

      loadSaved();
      loadAlerts();

      loading.hidden = true;
      body.hidden = false;
    } catch (e) {
      if (e.message === "unauthorized") return;
      loading.hidden = true;
      errorEl.textContent = "Could not load your account. Is the server running?";
      errorEl.hidden = false;
    }
  }

  moreBtn.addEventListener("click", async () => {
    if (!nextUrl) return;
    moreBtn.disabled = true;
    try {
      const page = await fetchJSON(nextUrl);
      renderBookings(page, true);
    } catch (e) { /* handled in fetchJSON */ }
    moreBtn.disabled = false;
  });

  $("ac-signout").addEventListener("click", () => {
    RailAuth.clear();
    location.href = "/";
  });

  const pwForm = $("pw-form");
  if (pwForm) {
    pwForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = $("pw-msg");
      const saveBtn = $("pw-save");
      const cur = $("pw-current").value;
      const nw = $("pw-new").value;
      const show = (text, ok) => {
        msg.textContent = text;
        msg.className = "pw-msg " + (ok ? "is-ok" : "is-err");
        msg.hidden = false;
      };
      if (nw.length < 8) { show("New password must be at least 8 characters.", false); return; }
      saveBtn.disabled = true;
      saveBtn.textContent = "Saving…";
      try {
        const res = await fetch("/api/auth/change-password/", {
          method: "POST",
          headers: { "Content-Type": "application/json", ...RailAuth.authHeader() },
          body: JSON.stringify({ current_password: cur, new_password: nw }),
        });
        if (res.status === 401) {
          RailAuth.clear();
          location.href = "/login/?next=" + encodeURIComponent("/account/");
          return;
        }
        const d = await res.json().catch(() => ({}));
        if (!res.ok) { show(d.detail || "Could not update password.", false); return; }
        show(d.detail || "Password updated successfully.", true);
        pwForm.reset();
      } catch (err) {
        show("Could not reach the server.", false);
      } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "Save password";
      }
    });
  }

  init();
})();