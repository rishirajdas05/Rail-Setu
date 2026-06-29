// RailSetu Assistant: self-injecting floating chat widget backed by /api/chat/.
// Styles are injected here so the widget looks right regardless of styles.css caching.
(function () {
  "use strict";

  if (window.__railsetuChatLoaded) return;
  window.__railsetuChatLoaded = true;

  const CSS = `
  .rs-chat-launch{position:fixed;right:22px;bottom:22px;z-index:2147483000;width:60px;height:60px;
    border-radius:50%;border:none;cursor:pointer;color:#fff;display:flex;align-items:center;justify-content:center;
    background:linear-gradient(150deg,#1d3b6e,#16224a);box-shadow:0 14px 34px -8px rgba(16,35,69,.6);
    transition:transform .15s ease,box-shadow .15s ease}
  .rs-chat-launch:hover{transform:translateY(-2px);box-shadow:0 18px 40px -8px rgba(16,35,69,.7)}
  .rs-chat-launch svg{width:26px;height:26px}
  .rs-chat-launch.is-open{background:linear-gradient(150deg,#2f5fd0,#244db0)}
  .rs-chat-panel{position:fixed;right:22px;bottom:94px;z-index:2147483000;width:374px;max-width:calc(100vw - 28px);
    height:560px;max-height:calc(100vh - 130px);display:flex;flex-direction:column;overflow:hidden;
    background:#fff;border-radius:18px;box-shadow:0 28px 70px -18px rgba(16,35,69,.5);
    font-family:'Inter',system-ui,-apple-system,Segoe UI,Roboto,sans-serif;animation:rsPop .18s ease;
    transition:width .2s ease,height .2s ease}
  @keyframes rsPop{from{opacity:0;transform:translateY(10px) scale(.98)}to{opacity:1;transform:none}}
  .rs-chat-panel.is-max{width:560px;height:calc(100vh - 120px)}
  .rs-chat-panel[hidden]{display:none}
  .rs-chat-head{display:flex;align-items:center;gap:11px;padding:13px 14px;color:#fff;cursor:grab;touch-action:none;
    background:linear-gradient(135deg,#1d3b6e 0%,#16224a 100%)}
  .rs-chat-head:active{cursor:grabbing}
  .rs-chat-ava{width:36px;height:36px;border-radius:50%;flex:0 0 auto;display:flex;align-items:center;justify-content:center;
    background:rgba(255,255,255,.14)}
  .rs-chat-ava svg{width:20px;height:20px}
  .rs-chat-htext{flex:1;min-width:0}
  .rs-chat-htext strong{display:block;font-size:.94rem;font-weight:700;line-height:1.2}
  .rs-chat-sub{display:block;font-size:.71rem;color:#bcc8e4;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .rs-chat-actions{display:flex;align-items:center;gap:4px;flex:0 0 auto;position:relative;z-index:7}
  .rs-act{background:rgba(255,255,255,.12);border:none;color:#fff;width:28px;height:28px;border-radius:7px;
    cursor:pointer;display:flex;align-items:center;justify-content:center;line-height:1;padding:0}
  .rs-act:hover{background:rgba(255,255,255,.24)}
  .rs-act svg{width:15px;height:15px}
  .rs-act-close{font-size:1.2rem}
  .rs-chat-log{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;background:#eef1f7}
  .rs-chat-log::-webkit-scrollbar{width:7px}
  .rs-chat-log::-webkit-scrollbar-thumb{background:#cfd6e6;border-radius:4px}
  .rs-msg{display:flex;flex-direction:column;max-width:86%}
  .rs-user{align-self:flex-end;align-items:flex-end}
  .rs-assistant{align-self:flex-start;align-items:flex-start}
  .rs-bubble{padding:10px 13px;border-radius:14px;font-size:.875rem;line-height:1.5;word-wrap:break-word;
    box-shadow:0 1px 2px rgba(16,35,69,.06)}
  .rs-user .rs-bubble{background:linear-gradient(135deg,#2f5fd0,#244db0);color:#fff;border-bottom-right-radius:5px}
  .rs-assistant .rs-bubble{background:#fff;color:#18202e;border:1px solid #e3e8f1;border-bottom-left-radius:5px}
  .rs-src{font-size:.68rem;color:#6b7691;margin-top:5px;padding-left:2px}
  .rs-typing .rs-bubble{display:inline-flex;gap:5px;align-items:center}
  .rs-typing i{width:7px;height:7px;border-radius:50%;background:#9aa6c0;display:inline-block;animation:rsBlink 1s infinite both}
  .rs-typing i:nth-child(2){animation-delay:.2s}.rs-typing i:nth-child(3){animation-delay:.4s}
  @keyframes rsBlink{0%,80%,100%{opacity:.3;transform:scale(.85)}40%{opacity:1;transform:scale(1)}}
  .rs-chips{display:flex;flex-wrap:wrap;gap:7px;padding:0 16px 14px;background:#eef1f7}
  .rs-chip{font:inherit;font-size:.74rem;color:#244db0;background:#fff;border:1px solid #d4def3;border-radius:999px;
    padding:6px 11px;cursor:pointer;transition:background .12s}
  .rs-chip:hover{background:#eaf0fd}
  .rs-chat-form{display:flex;gap:9px;padding:12px;border-top:1px solid #e3e8f1;background:#fff}
  .rs-chat-form input{flex:1;padding:11px 13px;border:1px solid #d9e0ec;border-radius:11px;font:inherit;font-size:.875rem;color:#18202e}
  .rs-chat-form input:focus{outline:none;border-color:#2f5fd0;box-shadow:0 0 0 3px rgba(47,95,208,.14)}
  .rs-chat-form button{width:44px;flex:0 0 auto;border:none;border-radius:11px;color:#fff;cursor:pointer;
    display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1d3b6e,#16224a)}
  .rs-chat-form button:hover{background:linear-gradient(135deg,#2f5fd0,#244db0)}
  .rs-chat-form button:disabled{opacity:.5;cursor:default}
  @media (max-width:520px){
    .rs-chat-panel,.rs-chat-panel.is-max{right:10px;left:10px;bottom:88px;width:auto;height:calc(100vh - 120px)}
    .rs-chat-launch{right:16px;bottom:16px}
    .rs-rsz{display:none}
  }
  .rs-rsz{position:absolute;width:18px;height:18px;z-index:6;touch-action:none}
  .rs-nw{top:0;left:0;cursor:nwse-resize}
  .rs-ne{top:0;right:0;cursor:nesw-resize}
  .rs-sw{bottom:0;left:0;cursor:nesw-resize}
  .rs-se{bottom:0;right:0;cursor:nwse-resize}
  .rs-se::after{content:"";position:absolute;right:4px;bottom:4px;width:7px;height:7px;
    border-right:2px solid #b9c2d4;border-bottom:2px solid #b9c2d4}
  .rs-chat-panel.is-max .rs-rsz{display:none}
  [data-theme="dark"] .rs-chat-panel{background:#19212f}
  [data-theme="dark"] .rs-chat-log,[data-theme="dark"] .rs-chips{background:#10161f}
  [data-theme="dark"] .rs-assistant .rs-bubble{background:#222c3c;color:#e7ecf4;border-color:#2c3647}
  [data-theme="dark"] .rs-chat-form{background:#19212f;border-top-color:#2c3647}
  [data-theme="dark"] .rs-chat-form input{background:#222c3c;color:#e7ecf4;border-color:#2c3647}
  [data-theme="dark"] .rs-chat-form input::placeholder{color:#8c97a8}
  [data-theme="dark"] .rs-chip{background:#222c3c;color:#9fc0ff;border-color:#2c3647}
  [data-theme="dark"] .rs-chip:hover{background:#2a3547}
  [data-theme="dark"] .rs-src{color:#9aa6b8}
  [data-theme="dark"] .rs-chat-log::-webkit-scrollbar-thumb{background:#2c3647}`;

  const style = document.createElement("style");
  style.textContent = CSS;
  document.head.appendChild(style);

  const BOT_ICON =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="8" width="18" height="11" rx="3"/><path d="M12 8V5M9 3h6"/><circle cx="9" cy="13" r="1"/><circle cx="15" cy="13" r="1"/><path d="M3 12H1M23 12h-2"/></svg>';
  const MAX_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M21 16v3a2 2 0 0 1-2 2h-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>';

  const history = [];

  const launcher = document.createElement("button");
  launcher.className = "rs-chat-launch";
  launcher.type = "button";
  launcher.setAttribute("aria-label", "Open RailSetu Assistant");
  launcher.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.5 8.5 0 0 1-12.2 7.6L3 21l1.9-5.8A8.5 8.5 0 1 1 21 11.5Z"/><path d="M8 11h8M8 14h5"/></svg>';

  const panel = document.createElement("div");
  panel.className = "rs-chat-panel";
  panel.hidden = true;
  panel.innerHTML =
    '<div class="rs-chat-head">' +
    '  <span class="rs-chat-ava">' + BOT_ICON + "</span>" +
    '  <div class="rs-chat-htext"><strong>RailSetu Assistant</strong><span class="rs-chat-sub">Trains, fares, PNR &amp; rules</span></div>' +
    '  <div class="rs-chat-actions">' +
    '    <button type="button" class="rs-act rs-act-max" aria-label="Maximize" title="Maximize">' + MAX_ICON + "</button>" +
    '    <button type="button" class="rs-act rs-act-close" aria-label="Close" title="Close">&times;</button>' +
    "  </div>" +
    "</div>" +
    '<div class="rs-chat-log" id="rs-chat-log"></div>' +
    '<div class="rs-chips" id="rs-chips"></div>' +
    '<form class="rs-chat-form" id="rs-chat-form">' +
    '  <input type="text" id="rs-chat-input" placeholder="Ask anything about trains..." autocomplete="off" aria-label="Message">' +
    '  <button type="submit" id="rs-chat-send" aria-label="Send">' +
    '    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4 20-7Z"/></svg>' +
    "  </button>" +
    "</form>" +
    '<div class="rs-rsz rs-nw" data-c="nw"></div>' +
    '<div class="rs-rsz rs-ne" data-c="ne"></div>' +
    '<div class="rs-rsz rs-sw" data-c="sw"></div>' +
    '<div class="rs-rsz rs-se" data-c="se"></div>';

  document.body.appendChild(launcher);
  document.body.appendChild(panel);

  const head = panel.querySelector(".rs-chat-head");
  const log = panel.querySelector("#rs-chat-log");
  const chips = panel.querySelector("#rs-chips");
  const form = panel.querySelector("#rs-chat-form");
  const input = panel.querySelector("#rs-chat-input");
  const sendBtn = panel.querySelector("#rs-chat-send");
  const btnMax = panel.querySelector(".rs-act-max");
  const btnClose = panel.querySelector(".rs-act-close");

  const SUGGESTIONS = ["Trains Delhi to Gwalior", "What does RAC mean?", "Cancellation refund rules", "Will WL 12 in 3A confirm?"];

  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function addMsg(role, text, sources) {
    const wrap = document.createElement("div");
    wrap.className = "rs-msg rs-" + role;
    let html = '<div class="rs-bubble">' + esc(text).replace(/\n/g, "<br>") + "</div>";
    if (sources && sources.length) {
      const uniq = [...new Set(sources.map((s) => s.title))].slice(0, 3);
      if (uniq.length) html += '<div class="rs-src">Based on: ' + esc(uniq.join(", ")) + "</div>";
    }
    wrap.innerHTML = html;
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
    return wrap;
  }

  function addTyping() {
    const wrap = document.createElement("div");
    wrap.className = "rs-msg rs-assistant rs-typing";
    wrap.innerHTML = '<div class="rs-bubble"><i></i><i></i><i></i></div>';
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
    return wrap;
  }

  function renderChips() {
    chips.innerHTML = "";
    SUGGESTIONS.forEach((s) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "rs-chip";
      b.textContent = s;
      b.addEventListener("click", () => { input.value = s; send(); });
      chips.appendChild(b);
    });
  }

  let greeted = false;
  function openPanel() {
    panel.hidden = false;
    launcher.classList.add("is-open");
    input.focus();
    if (!greeted) {
      greeted = true;
      addMsg("assistant", "Hi! I'm the RailSetu Assistant. Ask me about trains, fares, PNR status, waitlist chances, or booking rules.");
      renderChips();
    }
  }
  function closePanel() {
    panel.hidden = true;
    panel.classList.remove("is-max");
    launcher.classList.remove("is-open");
  }
  launcher.addEventListener("click", () => (panel.hidden ? openPanel() : closePanel()));
  btnClose.addEventListener("click", (e) => { e.stopPropagation(); closePanel(); });

  btnMax.addEventListener("click", (e) => {
    e.stopPropagation();
    // drop any dragged/resized geometry so maximize uses its anchored layout
    panel.style.left = panel.style.top = panel.style.right = panel.style.bottom = panel.style.width = panel.style.height = "";
    panel.classList.toggle("is-max");
  });

  // ---- drag the panel by its header ----
  let drag = null;
  head.addEventListener("pointerdown", (e) => {
    if (e.target.closest("button")) return;        // let buttons work
    if (panel.classList.contains("is-max")) return; // don't drag when maximized
    const rect = panel.getBoundingClientRect();
    drag = { dx: e.clientX - rect.left, dy: e.clientY - rect.top, sx: e.clientX, sy: e.clientY, moved: false };
    // switch from right/bottom anchoring to absolute left/top
    panel.style.left = rect.left + "px";
    panel.style.top = rect.top + "px";
    panel.style.right = "auto";
    panel.style.bottom = "auto";
    try { head.setPointerCapture(e.pointerId); } catch (_) {}
  });
  head.addEventListener("pointermove", (e) => {
    if (!drag) return;
    if (Math.abs(e.clientX - drag.sx) > 3 || Math.abs(e.clientY - drag.sy) > 3) drag.moved = true;
    const w = panel.offsetWidth, h = panel.offsetHeight;
    const x = Math.max(6, Math.min(e.clientX - drag.dx, window.innerWidth - w - 6));
    const y = Math.max(6, Math.min(e.clientY - drag.dy, window.innerHeight - h - 6));
    panel.style.left = x + "px";
    panel.style.top = y + "px";
  });
  function endDrag(e) {
    if (!drag) return;
    try { head.releasePointerCapture(e.pointerId); } catch (_) {}
    drag = null;
  }
  head.addEventListener("pointerup", endDrag);
  head.addEventListener("pointercancel", endDrag);

  // ---- resize from any corner ----
  let rsz = null;
  panel.querySelectorAll(".rs-rsz").forEach((handle) => {
    handle.addEventListener("pointerdown", (e) => {
      if (panel.classList.contains("is-max")) return;
      e.preventDefault();
      e.stopPropagation();
      const r = panel.getBoundingClientRect();
      rsz = {
        c: handle.dataset.c, sx: e.clientX, sy: e.clientY,
        left: r.left, top: r.top, w: r.width, h: r.height,
        right: r.left + r.width, bottom: r.top + r.height,
      };
      panel.style.left = r.left + "px";
      panel.style.top = r.top + "px";
      panel.style.width = r.width + "px";
      panel.style.height = r.height + "px";
      panel.style.right = "auto";
      panel.style.bottom = "auto";
      try { handle.setPointerCapture(e.pointerId); } catch (_) {}
    });
    handle.addEventListener("pointermove", (e) => {
      if (!rsz) return;
      const dx = e.clientX - rsz.sx;
      const dy = e.clientY - rsz.sy;
      const minW = 300, minH = 240;
      const maxW = window.innerWidth - 28;
      const maxH = window.innerHeight - 30;
      let w = rsz.w, h = rsz.h, left = rsz.left, top = rsz.top;
      if (rsz.c.indexOf("e") > -1) w = rsz.w + dx;
      if (rsz.c.indexOf("w") > -1) w = rsz.w - dx;
      if (rsz.c.indexOf("s") > -1) h = rsz.h + dy;
      if (rsz.c.indexOf("n") > -1) h = rsz.h - dy;
      w = Math.max(minW, Math.min(w, maxW));
      h = Math.max(minH, Math.min(h, maxH));
      if (rsz.c.indexOf("w") > -1) left = rsz.right - w;   // anchor right edge
      if (rsz.c.indexOf("n") > -1) top = rsz.bottom - h;   // anchor bottom edge
      left = Math.max(6, Math.min(left, window.innerWidth - w - 6));
      top = Math.max(6, Math.min(top, window.innerHeight - h - 6));
      panel.style.width = w + "px";
      panel.style.height = h + "px";
      panel.style.left = left + "px";
      panel.style.top = top + "px";
    });
    function endRsz(e) {
      if (!rsz) return;
      try { handle.releasePointerCapture(e.pointerId); } catch (_) {}
      rsz = null;
    }
    handle.addEventListener("pointerup", endRsz);
    handle.addEventListener("pointercancel", endRsz);
  });

  let busy = false;
  async function send() {
    const text = input.value.trim();
    if (!text || busy) return;
    input.value = "";
    chips.innerHTML = "";
    addMsg("user", text);
    history.push({ role: "user", content: text });

    busy = true;
    sendBtn.disabled = true;
    const typing = addTyping();
    try {
      const res = await fetch("/api/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history: history.slice(0, -1),
          lang: (window.RailI18n && RailI18n.lang && RailI18n.lang()) || "en",
        }),
      });
      const data = await res.json().catch(() => ({}));
      typing.remove();
      if (!res.ok) {
        addMsg("assistant", data.detail || "Sorry, something went wrong.");
      } else {
        addMsg("assistant", data.answer, data.sources);
        history.push({ role: "assistant", content: data.answer });
      }
    } catch (err) {
      typing.remove();
      addMsg("assistant", "Network error. Is the server running?");
    } finally {
      busy = false;
      sendBtn.disabled = false;
      input.focus();
    }
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); send(); });
})();