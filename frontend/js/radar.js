(function () {
  "use strict";
  var el = document.getElementById("rail-map");
  if (!el || typeof L === "undefined") return;
  var KEY = "K0JQ1nE0ekRlTQStkWth";

  var streets = L.tileLayer("https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=" + KEY, { maxZoom: 19, attribution: "&copy; MapTiler &copy; OpenStreetMap" });
  var hybrid = L.tileLayer("https://api.maptiler.com/maps/hybrid/{z}/{x}/{y}.jpg?key=" + KEY, { maxZoom: 19, attribution: "&copy; MapTiler &copy; OpenStreetMap" });

  var map = L.map(el, { preferCanvas: true, layers: [streets] }).setView([22.6, 79.0], 5);
  L.control.layers({ "Map": streets, "Satellite": hybrid }).addTo(map);
  setTimeout(function () { map.invalidateSize(); }, 300);

  var layer = L.layerGroup().addTo(map);
  var routeLayer = L.layerGroup().addTo(map);

  var panel = document.createElement("div");
  panel.id = "radar-panel";
  panel.style.cssText = "position:absolute;top:14px;left:14px;z-index:1200;width:320px;max-width:86vw;max-height:84%;overflow:auto;background:var(--card,#161f2d);color:var(--ink,#e6ebf4);border:1px solid var(--line,#2a3446);border-radius:14px;box-shadow:0 18px 44px rgba(0,0,0,.5);padding:16px;display:none;font-family:Inter,system-ui,sans-serif";
  el.appendChild(panel);
  function closePanel() { panel.style.display = "none"; routeLayer.clearLayers(); }

  function arrowIcon(bearing) {
    return L.divIcon({ className: "rail-arrow", html: "<div style=\"transform:rotate(" + bearing + "deg);width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-bottom:13px solid #f2b134;filter:drop-shadow(0 0 1px #7a5200)\"></div>", iconSize: [12, 13], iconAnchor: [6, 7] });
  }
  function fmtMin(m) { var h = Math.floor(m / 60), mm = m % 60; return (h ? h + "h " : "") + mm + "m"; }

  function openTrain(number, name) {
    panel.style.display = "block";
    panel.innerHTML = "<div style=\"display:flex;justify-content:space-between;gap:10px\"><h3 style=\"margin:0;font-size:1.05rem\">" + number + " " + (name || "") + "</h3><button id=\"rp-x\" style=\"background:none;border:none;color:inherit;font-size:1.3rem;cursor:pointer\">&times;</button></div><p style=\"margin:8px 0 0;color:var(--muted,#98a3b6)\">Loading route&hellip;</p>";
    document.getElementById("rp-x").onclick = closePanel;
    fetch("/api/trains/" + encodeURIComponent(number) + "/route/?started=today")
      .then(function (r) { if (!r.ok) throw new Error("bad"); return r.json(); })
      .then(function (d) {
        routeLayer.clearLayers(); if (d.polyline && d.polyline.length > 1) { var rl = L.polyline(d.polyline, { color: "#4f7fff", weight: 3, opacity: 0.9 }).addTo(routeLayer); map.fitBounds(rl.getBounds(), { padding: [40, 40], maxZoom: 7 }); }
        var s = d.stats || {};
        var html = "<div style=\"display:flex;justify-content:space-between;gap:10px\"><div><h3 style=\"margin:0;font-size:1.05rem\">" + d.number + " " + (d.name || "") + "</h3><p style=\"margin:2px 0 0;color:var(--muted,#98a3b6);font-size:.85rem\">" + (d.source || "") + " &rarr; " + (d.destination || "") + "</p></div><button id=\"rp-x\" style=\"background:none;border:none;color:inherit;font-size:1.3rem;cursor:pointer\">&times;</button></div>";
        html += "<p style=\"margin:10px 0 0;color:var(--amber,#f2b134);font-weight:600\">" + (d.status_text || "") + "</p>";
        html += "<div style=\"display:flex;gap:14px;margin:10px 0;font-size:.8rem;color:var(--muted,#98a3b6)\"><span><strong style=\"color:var(--ink,#e6ebf4)\">" + (s.total_km || 0) + "</strong> km</span><span><strong style=\"color:var(--ink,#e6ebf4)\">" + (s.avg_speed_kmph || 0) + "</strong> km/h</span><span><strong style=\"color:var(--ink,#e6ebf4)\">" + (s.halts || 0) + "</strong> stops</span><span>" + (s.journey_minutes ? fmtMin(s.journey_minutes) : "") + "</span></div>";
        var cur = d.current || {};
        html += "<div style=\"border-top:1px solid var(--line,#2a3446);margin-top:6px;padding-top:8px\">";
        (d.stops || []).forEach(function (st) {
          var next = cur.next && st.code === cur.next;
          var dot = next ? "#f2b134" : "#4f7fff";
          html += "<div style=\"display:flex;justify-content:space-between;gap:10px;padding:3px 0;font-size:.82rem;" + (next ? "font-weight:600" : "") + "\"><span><span style=\"display:inline-block;width:8px;height:8px;border-radius:50%;background:" + dot + ";margin-right:7px\"></span>" + st.name + " <span style=\"color:var(--muted,#98a3b6)\">" + st.code + "</span></span><span style=\"color:var(--muted,#98a3b6);white-space:nowrap\">" + (st.departure || st.arrival || "") + " &middot; " + st.km + "km</span></div>";
        });
        html += "</div>";
        panel.innerHTML = html;
        document.getElementById("rp-x").onclick = closePanel;
      })
      .catch(function () {
        panel.innerHTML = "<div style=\"display:flex;justify-content:space-between\"><h3 style=\"margin:0\">" + number + "</h3><button id=\"rp-x\" style=\"background:none;border:none;color:inherit;font-size:1.3rem;cursor:pointer\">&times;</button></div><p style=\"color:var(--muted,#98a3b6)\">Route not available.</p>";
        document.getElementById("rp-x").onclick = closePanel;
      });
  }

  function draw(trains) {
    layer.clearLayers();
    trains.forEach(function (t) {
      var mk = L.marker([t.lat, t.lon], { icon: arrowIcon(t.bearing || 0) });
      mk.on("click", function () { openTrain(t.number, t.name); });
      layer.addLayer(mk);
    });
  }
  function setCount(n) { var c = document.getElementById("radar-count"); if (c) c.textContent = n + " trains running now (indicative)"; }
  function load() {
    fetch("/api/radar/?started=today").then(function (r) { if (!r.ok) throw new Error("bad"); return r.json(); })
      .then(function (data) { draw(data.trains || []); setCount(data.count || 0); }).catch(function () { setCount(0); });
  }
  load();
  setInterval(load, 60000);
})();

