(function () {
  "use strict";
  var el = document.getElementById("rail-map");
  if (!el || typeof L === "undefined") return;
  el.style.height = "420px";
  var q = new URLSearchParams(location.search);
  var m = location.pathname.match(/\/train\/([^\/]+)/);
  var number = (window.RAILMAP && window.RAILMAP.number) || q.get("n") || q.get("train") || (m ? m[1] : "") || "";
  var started = (window.RAILMAP && window.RAILMAP.started) || q.get("started") || "today";
  var KEY = "K0JQ1nE0ekRlTQStkWth";

  var streets = L.tileLayer("https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=" + KEY, { maxZoom: 19, attribution: "&copy; MapTiler &copy; OpenStreetMap" });
  var satellite = L.tileLayer("https://api.maptiler.com/maps/hybrid/{z}/{x}/{y}.jpg?key=" + KEY, { maxZoom: 19, attribution: "&copy; MapTiler &copy; OpenStreetMap" });

  var map = L.map(el, { scrollWheelZoom: false, preferCanvas: true, layers: [streets] }).setView([22.9, 79.0], 5);
  L.control.layers({ "Map": streets, "Satellite": satellite }).addTo(map);
  setTimeout(function () { map.invalidateSize(); }, 300);

  function setText(id, v) { var n = document.getElementById(id); if (n) n.textContent = v; }
  if (!number) { setText("rail-status-text", "No train selected."); return; }

  fetch("/api/trains/" + encodeURIComponent(number) + "/route/?started=" + encodeURIComponent(started))
    .then(function (res) { if (!res.ok) throw new Error("bad"); return res.json(); })
    .then(function (data) {
      if (data.polyline && data.polyline.length > 1) {
        var line = L.polyline(data.polyline, { color: "#4f7fff", weight: 4, opacity: 0.85 }).addTo(map);
        map.fitBounds(line.getBounds(), { padding: [30, 30], maxZoom: 7 });
      }
      var stops = data.stops || [];
      stops.forEach(function (s, i) {
        var end = i === 0 || i === stops.length - 1;
        var halt = s.arrival && s.departure && s.arrival !== s.departure;
        if (!end && !halt) return;
        var mk = L.circleMarker([s.lat, s.lon], { radius: end ? 6 : 4, color: end ? "#1d3b6e" : "#4f7fff", fillColor: "#fff", fillOpacity: 1, weight: 2 }).addTo(map);
        mk.bindPopup("<strong>" + s.name + "</strong> (" + s.code + ")<br>" + (s.departure || s.arrival || "") + " &middot; " + s.km + " km");
      });
      if (data.current) {
        L.marker([data.current.lat, data.current.lon], { icon: L.divIcon({ className: "rail-train-icon", html: "<div style=\"background:#f2b134;border:2px solid #7a5200;border-radius:50%;width:16px;height:16px;box-shadow:0 0 0 4px rgba(242,177,52,0.35)\"></div>", iconSize: [16,16], iconAnchor: [8,8] }) }).addTo(map);
      }
      setText("rail-status-text", (data.status_text || "") + " (indicative)");
      map.invalidateSize();
    })
    .catch(function () { setText("rail-status-text", "Route not available."); });
})();

