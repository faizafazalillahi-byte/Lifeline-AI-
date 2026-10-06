/**
 * map.js
 * ------
 * Loads the Google Maps JavaScript API dynamically (using the key from
 * config.js) and renders a map with the user's location plus nearest
 * hospital/police markers. If the key is a placeholder, missing, or the
 * script fails to load within a timeout, falls back to a simple text
 * summary + "open in Google Maps" links so the app still works without
 * a configured key.
 */

let _googleMapsLoadPromise = null;

function loadGoogleMaps() {
  if (_googleMapsLoadPromise) return _googleMapsLoadPromise;

  console.log("Google Maps key currently loaded as:", CONFIG.GOOGLE_MAPS_API_KEY);

  _googleMapsLoadPromise = new Promise((resolve, reject) => {
    if (!CONFIG.GOOGLE_MAPS_API_KEY || CONFIG.GOOGLE_MAPS_API_KEY === "YOUR_GOOGLE_MAPS_API_KEY") {
      reject(new Error("Google Maps API key not configured"));
      return;
    }

    if (window.google && window.google.maps) {
      resolve(window.google.maps);
      return;
    }

    const timeout = setTimeout(() => reject(new Error("Google Maps failed to load (timeout)")), 6000);

    window._onGoogleMapsLoaded = () => {
      clearTimeout(timeout);
      resolve(window.google.maps);
    };

    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${CONFIG.GOOGLE_MAPS_API_KEY}&loading=async&callback=_onGoogleMapsLoaded`;
    script.async = true;
    script.onerror = () => {
      clearTimeout(timeout);
      reject(new Error("Google Maps script failed to load"));
    };
    document.head.appendChild(script);
  });

  return _googleMapsLoadPromise;
}

/**
 * Renders the SOS map into #containerId. Falls back to a plain-text
 * summary with "Open in Google Maps" links if the JS API is unavailable.
 * Also exposes drawRouteTo() so facility "Directions" buttons can draw
 * the route INSIDE this map instead of leaving the website.
 */
let _sosMap = null;
let _sosMapsLib = null;
let _directionsRenderer = null;
let _userMarkerPosition = null;

async function renderSosMap(containerId, userLocation, hospital, police) {
  const container = document.getElementById(containerId);
  _userMarkerPosition = userLocation;

  try {
    const maps = await loadGoogleMaps();
    _sosMapsLib = maps;

    const center = { lat: userLocation.lat, lng: userLocation.lng };
    const map = new maps.Map(container, {
      center,
      zoom: 13,
      disableDefaultUI: true,
      zoomControl: true,
      styles: MAP_DARK_STYLE,
    });
    _sosMap = map;

    // Track all marker positions so we can auto-zoom to fit every one of
    // them on screen — otherwise a hospital/police station that's far
    // away (common with sparse seed data) would render off-screen at a
    // fixed close-in zoom level, making the map look "empty" apart from
    // the user's own marker.
    const bounds = new maps.LatLngBounds();
    bounds.extend(center);

    new maps.Marker({
      position: center,
      map,
      title: "Your location",
      icon: { path: maps.SymbolPath.CIRCLE, scale: 9, fillColor: "#E6394A", fillOpacity: 1, strokeColor: "#fff", strokeWeight: 2 },
    });

    if (hospital) {
      const hospitalPos = { lat: parseFloat(hospital.latitude), lng: parseFloat(hospital.longitude) };
      bounds.extend(hospitalPos);
      new maps.Marker({
        position: hospitalPos,
        map,
        title: hospital.name,
        icon: { path: maps.SymbolPath.CIRCLE, scale: 7, fillColor: "#3D7BF5", fillOpacity: 1, strokeColor: "#fff", strokeWeight: 2 },
      });
    }
    if (police) {
      const policePos = { lat: parseFloat(police.latitude), lng: parseFloat(police.longitude) };
      bounds.extend(policePos);
      new maps.Marker({
        position: policePos,
        map,
        title: police.name,
        icon: { path: maps.SymbolPath.CIRCLE, scale: 7, fillColor: "#12B8A6", fillOpacity: 1, strokeColor: "#fff", strokeWeight: 2 },
      });
    }

    // Fit the map to show every marker. If hospital/police are far from
    // the user, this zooms out automatically instead of leaving them
    // invisible off-screen at a fixed close zoom level.
    if (hospital || police) {
      map.fitBounds(bounds, 60); // 60px padding so markers aren't stuck to the edge
    }

    _directionsRenderer = new maps.DirectionsRenderer({
      map,
      suppressMarkers: true,
      polylineOptions: { strokeColor: "#E6394A", strokeWeight: 4 },
    });
  } catch (err) {
    console.error("Google Maps failed to load:", err.message);
    renderMapFallback(containerId, userLocation, hospital, police);
  }
}

/**
 * Draws a route from the user's current location to the given facility
 * directly on the embedded map (no new tab / external app). Falls back
 * to opening Google Maps externally only if the JS API never loaded.
 */
async function drawRouteTo(facility) {
  if (!_sosMap || !_sosMapsLib || !_directionsRenderer) {
    const url = `https://www.google.com/maps/dir/?api=1&origin=${_userMarkerPosition.lat},${_userMarkerPosition.lng}&destination=${facility.latitude},${facility.longitude}`;
    window.open(url, "_blank");
    return;
  }

  const directionsService = new _sosMapsLib.DirectionsService();
  directionsService.route(
    {
      origin: { lat: _userMarkerPosition.lat, lng: _userMarkerPosition.lng },
      destination: { lat: parseFloat(facility.latitude), lng: parseFloat(facility.longitude) },
      travelMode: _sosMapsLib.TravelMode.DRIVING,
    },
    (result, status) => {
      if (status === "OK") {
        _directionsRenderer.setDirections(result);
        document.getElementById("sos-map").scrollIntoView({ behavior: "smooth", block: "center" });
      } else {
        showToast("Could not calculate a route on the map — opening Google Maps instead.", "warning");
        const url = `https://www.google.com/maps/dir/?api=1&origin=${_userMarkerPosition.lat},${_userMarkerPosition.lng}&destination=${facility.latitude},${facility.longitude}`;
        window.open(url, "_blank");
      }
    }
  );
}

function renderMapFallback(containerId, userLocation, hospital, police) {
  const container = document.getElementById(containerId);
  const mapsLink = `https://www.google.com/maps?q=${userLocation.lat},${userLocation.lng}`;
  container.innerHTML = `
    <div class="map-fallback">
      <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
      <div>Live map requires a Google Maps API key.<br>Add yours in <code>js/config.js</code> to enable it here.</div>
      <a href="${mapsLink}" target="_blank" class="btn btn-outline" style="color:#fff;border-color:var(--ink-600);margin-top:8px;">Open Your Location in Google Maps</a>
    </div>
  `;
}

/**
 * Renders a heatmap-style visualization for the admin "AI Hotspot Map" tab.
 *
 * NOTE: Google officially deprecated & removed google.maps.visualization.
 * HeatmapLayer from the Maps JavaScript API (May 2026) with no direct
 * built-in replacement — only a heavy third-party library (deck.gl) is
 * suggested, which needs WebGL setup and is overkill here. Instead, this
 * builds an equivalent "heat glow" effect using plain google.maps.Circle
 * overlays: each point gets 3 concentric, semi-transparent circles
 * (small+intense, medium, large+faint) so overlapping points visually
 * blend into hot zones — same visual result, zero extra dependencies.
 *
 * `points` is an array of {lat, lng, weight} — weight (1-4, mapped from
 * severity) controls how "hot" (red vs yellow) and how intense the glow is.
 */
async function renderHeatmap(containerId, points) {
  const container = document.getElementById(containerId);

  if (!points || !points.length) {
    container.innerHTML = `<div class="map-fallback" style="color:var(--slate-600);">Not enough location data yet to render a heatmap.</div>`;
    return;
  }

  try {
    const maps = await loadGoogleMaps();

    const avgLat = points.reduce((sum, p) => sum + p.lat, 0) / points.length;
    const avgLng = points.reduce((sum, p) => sum + p.lng, 0) / points.length;

    const map = new maps.Map(container, {
      center: { lat: avgLat, lng: avgLng },
      zoom: 12,
      disableDefaultUI: true,
      zoomControl: true,
      styles: MAP_DARK_STYLE,
    });

    // weight 1 (Low) -> cool yellow, weight 4 (Critical) -> hot red
    const weightColor = { 1: "#F5C77E", 2: "#F5A623", 3: "#E67C87", 4: "#E6394A" };

    points.forEach((p) => {
      const color = weightColor[p.weight] || weightColor[1];
      const layers = [
        { radius: 900, opacity: 0.06 },
        { radius: 500, opacity: 0.12 },
        { radius: 200, opacity: 0.22 },
      ];
      layers.forEach((layer) => {
        new maps.Circle({
          map,
          center: { lat: p.lat, lng: p.lng },
          radius: layer.radius * (0.6 + p.weight * 0.2), // more severe = wider glow
          fillColor: color,
          fillOpacity: layer.opacity,
          strokeWeight: 0,
        });
      });
    });
  } catch (err) {
    console.error("Heatmap failed to load:", err.message);
    container.innerHTML = `
      <div class="map-fallback" style="color:var(--slate-600);">
        Live map requires a Google Maps API key. Add yours in <code>frontend/js/config.js</code> —
        the risk-zone table above already works without it.
      </div>
    `;
  }
}

/** A minimal dark map theme so it matches the console aesthetic. */
const MAP_DARK_STYLE = [
  { elementType: "geometry", stylers: [{ color: "#131B2E" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#131B2E" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#8A93A6" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#1B2740" }] },
  { featureType: "water", elementType: "geometry", stylers: [{ color: "#0B1220" }] },
  { featureType: "poi", stylers: [{ visibility: "off" }] },
];
