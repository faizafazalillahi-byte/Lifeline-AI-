/**
 * sos.js
 * ------
 * Powers sos.html: emergency type selection, geolocation capture,
 * triggering the SOS API call, and rendering the AI severity result,
 * fake-alert notice, nearest hospital/police cards, and the map.
 */

let selectedType = "other";
let currentPosition = null;
let activeEmergencyId = null;
let locationWatchId = null;

document.addEventListener("DOMContentLoaded", () => {
  requireAuth();

  const user = Session.getUser();
  if (user && user.role === "admin") {
    showToast("Admin accounts don't raise personal SOS alerts. Redirecting to the admin console.", "warning");
    setTimeout(() => { window.location.href = "admin_dashboard.html"; }, 1200);
    return;
  }

  wireTypeChips();
  wireSosButton();
  startGeolocationWatch();
});

/* ---------------------------------------------------------------------
   Emergency type chip selection
   --------------------------------------------------------------------- */
function wireTypeChips() {
  const chips = document.querySelectorAll(".type-chip");
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      chips.forEach((c) => c.classList.remove("selected"));
      chip.classList.add("selected");
      selectedType = chip.dataset.type;
    });
  });
}

/* ---------------------------------------------------------------------
   Geolocation
   --------------------------------------------------------------------- */
function startGeolocationWatch() {
  const statusEl = document.getElementById("gps-status-text");
  const dotEl = document.getElementById("gps-dot");

  if (!("geolocation" in navigator)) {
    statusEl.innerText = "Geolocation not supported by this browser";
    dotEl.classList.add("error");
    return;
  }

  dotEl.classList.add("pending");
  statusEl.innerText = "Acquiring GPS signal...";

  navigator.geolocation.watchPosition(
    (position) => {
      currentPosition = { lat: position.coords.latitude, lng: position.coords.longitude };
      dotEl.classList.remove("pending", "error");
      statusEl.innerText = `Location locked · ${currentPosition.lat.toFixed(5)}, ${currentPosition.lng.toFixed(5)}`;

      // If an emergency is already active, keep reporting live location.
      if (activeEmergencyId) {
        apiRequest(`/emergency/${activeEmergencyId}/location`, {
          method: "POST",
          body: { latitude: currentPosition.lat, longitude: currentPosition.lng },
        }).catch(() => {});
      }
    },
    (err) => {
      dotEl.classList.remove("pending");
      dotEl.classList.add("error");
      statusEl.innerText = "Location permission denied — enable GPS to raise an SOS";
    },
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
  );
}

/* ---------------------------------------------------------------------
   Trigger SOS
   --------------------------------------------------------------------- */
function wireSosButton() {
  document.getElementById("sos-button").addEventListener("click", async () => {
    if (!currentPosition) {
      showToast("Still acquiring your GPS location — try again in a moment.", "warning");
      return;
    }

    const button = document.getElementById("sos-button");
    button.disabled = true;
    button.querySelector(".sos-label").innerText = "Sending...";

    const description = document.getElementById("sos-description").value.trim();

    try {
      const data = await apiRequest("/emergency/sos", {
        method: "POST",
        body: {
          emergency_type: selectedType,
          description,
          latitude: currentPosition.lat,
          longitude: currentPosition.lng,
        },
      });

      activeEmergencyId = data.emergency_id;
      renderResult(data);
    } catch (err) {
      showToast(err.message, "error");
      button.disabled = false;
      button.querySelector(".sos-label").innerText = "SOS";
    }
  });
}

/* ---------------------------------------------------------------------
   Render AI + facility results
   --------------------------------------------------------------------- */
function renderResult(data) {
  document.getElementById("sos-setup").style.display = "none";
  const resultPanel = document.getElementById("sos-result");
  resultPanel.classList.add("show");

  // Severity + status badges
  const badgeWrap = document.getElementById("result-badges");
  badgeWrap.innerHTML = `
    ${severityBadgeDark(data.severity.level)}
    <span class="badge badge-status" style="background:var(--ink-700);color:var(--slate-400);">
      Emergency #${data.emergency_id}
    </span>
    <span class="badge badge-status" style="background:var(--ink-700);color:var(--slate-400);">
      Confidence ${(data.severity.confidence * 100).toFixed(0)}%
    </span>
    <span class="badge badge-status" style="background:var(--accent-teal-dim);color:#0A8A7C;">
      ~${data.estimated_response_minutes} min ETA
    </span>
  `;

  // Fake-alert notice (only shown if flagged — never blocks anything)
  const fakeNotice = document.getElementById("fake-alert-notice");
  if (data.fake_alert_check.is_fake_suspected) {
    fakeNotice.classList.add("show");
    fakeNotice.innerText = "Note: our system flagged this alert for manual review based on recent activity patterns. It has still been dispatched — this is purely for admin visibility.";
  }

  // Facility cards
  renderFacilityCard("hospital-card", data.nearest_hospital, "Nearest Hospital");
  renderFacilityCard("police-card", data.nearest_police_station, "Nearest Police Station");

  // AI first-aid guidance
  renderFirstAidGuidance(data.first_aid_guidance);

  // Map
  renderSosMap("sos-map", currentPosition, data.nearest_hospital, data.nearest_police_station);

  showToast(`SOS raised. ${data.contacts_notified} emergency contact(s) notified.`, "success");
}

function renderFirstAidGuidance(guidance) {
  if (!guidance || !guidance.steps || !guidance.steps.length) return;
  const el = document.getElementById("first-aid-guidance");
  el.innerHTML = `
    <div class="first-aid-header">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"/></svg>
      <span>${escapeHtml(guidance.title)}</span>
    </div>
    <ol class="first-aid-steps">
      ${guidance.steps.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}
    </ol>
    <div class="first-aid-disclaimer">${escapeHtml(guidance.disclaimer)}</div>
  `;
  el.classList.add("show");
}

function renderFacilityCard(elementId, facility, label) {
  const el = document.getElementById(elementId);
  if (!facility) {
    el.innerHTML = `
      <div class="f-label">${label}</div>
      <div class="f-name">No facility on file</div>
      <div class="f-distance">Add facilities via the admin panel</div>
    `;
    return;
  }

  el.innerHTML = `
    <div class="f-label">${label}</div>
    <div class="f-name">${escapeHtml(facility.name)}</div>
    <div class="f-distance mono">${facility.distance_km} km away</div>
    <div class="f-actions">
      <a href="tel:${escapeHtml(facility.phone || "")}" class="call-btn">Call</a>
      <button type="button" class="directions-btn" onclick='drawRouteTo(${JSON.stringify(facility)})'>Directions</button>
    </div>
  `;
}

function severityBadgeDark(level) {
  const colors = {
    Low: { bg: "var(--accent-teal-dim)", fg: "#0A8A7C" },
    Medium: { bg: "var(--accent-amber-dim)", fg: "#B67614" },
    High: { bg: "rgba(230,57,74,0.15)", fg: "#F08B96" },
    Critical: { bg: "var(--accent-red)", fg: "#fff" },
  };
  const c = colors[level] || { bg: "var(--ink-700)", fg: "var(--slate-400)" };
  return `<span class="badge" style="background:${c.bg};color:${c.fg};">${level} Severity</span>`;
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
