/**
 * admin.js
 * --------
 * Powers admin_dashboard.html: sidebar tabs, live emergency monitoring
 * with status updates, user activation toggles, facility directory CRUD,
 * and the audit log.
 */

document.addEventListener("DOMContentLoaded", () => {
  requireAdmin();
  initSidebar();
  loadUserChip();
  loadOverview();
  loadEmergencies();
  loadUsers();
  loadFacilities();
  loadLogs();
  loadHotspots();
  wireFilters();
  wireFacilityModals();
  wireHeatmapFilters();
  wireEmergencyDetailModal();
  wireLogout();
  startLivePolling();
});

/* ---------------------------------------------------------------------
   Live polling — keeps Overview stats + the Live Emergencies table
   refreshing automatically, and pings a toast when a brand-new
   emergency arrives (so this actually feels "live", not static).
   --------------------------------------------------------------------- */
let _knownEmergencyIds = new Set();
let _firstPollDone = false;

function startLivePolling() {
  setInterval(async () => {
    await loadOverview();
    await pollForNewEmergencies();
  }, 8000); // every 8 seconds
}

async function pollForNewEmergencies() {
  try {
    const data = await apiRequest("/admin/emergencies");
    const currentIds = new Set(data.emergencies.map((e) => e.emergency_id));
    let newOnes = [];

    if (_firstPollDone) {
      newOnes = data.emergencies.filter((e) => !_knownEmergencyIds.has(e.emergency_id));
      newOnes.forEach((e) => {
        playAlertSound();
        showToast(
          `🚨 New ${e.severity_level || ""} ${e.emergency_type} SOS from ${e.full_name}${e.is_fake_suspected ? " (flagged for review)" : ""}`,
          e.severity_level === "Critical" ? "error" : "warning",
          7000
        );
      });
    }

    _knownEmergencyIds = currentIds;
    _firstPollDone = true;

    // Only re-render the table if the Live Emergencies panel is the active tab,
    // otherwise leave it (loadEmergencies() re-fetches with current filters
    // whenever the user switches to that tab anyway).
    if (document.getElementById("panel-emergencies").classList.contains("active")) {
      loadEmergencies();
    }
    if (document.getElementById("panel-hotspots").classList.contains("active") && newOnes.length > 0) {
      loadHeatmap();
    }
  } catch (err) {
    // Silent fail on polling — don't spam toasts if the network hiccups.
  }
}

function playAlertSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.25);
  } catch (e) {
    // Audio not available/blocked — non-critical, ignore.
  }
}

/* ---------------------------------------------------------------------
   Sidebar
   --------------------------------------------------------------------- */
function initSidebar() {
  const navItems = document.querySelectorAll(".dash-nav-item[data-panel]");
  navItems.forEach((item) => {
    item.addEventListener("click", () => {
      navItems.forEach((i) => i.classList.remove("active"));
      item.classList.add("active");
      document.querySelectorAll(".dash-panel").forEach((p) => p.classList.remove("active"));
      document.getElementById(`panel-${item.dataset.panel}`).classList.add("active");

      if (item.dataset.panel === "hotspots") loadHotspots();
    });
  });
}

function loadUserChip() {
  const user = Session.getUser();
  if (!user) return;
  const initials = user.full_name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  document.getElementById("sidebar-avatar").innerText = initials;
  document.getElementById("sidebar-name").innerText = user.full_name;
}

function wireLogout() {
  document.getElementById("logout-btn").addEventListener("click", () => Session.logout());
}

/* ---------------------------------------------------------------------
   Overview
   --------------------------------------------------------------------- */
async function loadOverview() {
  try {
    const data = await apiRequest("/admin/dashboard-summary");
    const s = data.summary;

    document.getElementById("stat-active").innerText = s.total_active;
    document.getElementById("stat-resolved").innerText = s.by_status.resolved || 0;
    document.getElementById("stat-fake").innerText = s.total_flagged_fake;
    document.getElementById("stat-users").innerText = s.total_users;

    renderBreakdown("severity-breakdown", s.by_severity, {
      Low: "var(--accent-teal)", Medium: "var(--accent-amber)", High: "#E67C87", Critical: "var(--accent-red)",
    });
    renderBreakdown("type-breakdown", s.by_type, {
      medical: "var(--accent-blue)", fire: "var(--accent-red)", accident: "var(--accent-amber)",
      crime: "#8B5CF6", other: "var(--slate-400)",
    });
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderBreakdown(elId, counts, colors) {
  const el = document.getElementById(elId);
  const entries = Object.entries(counts);
  const max = Math.max(...entries.map(([, v]) => v), 1);

  if (!entries.length) {
    el.innerHTML = `<div class="empty-state">No data yet</div>`;
    return;
  }

  el.innerHTML = entries.map(([label, value]) => `
    <div class="breakdown-row">
      <span style="text-transform:capitalize;width:80px;">${label}</span>
      <div class="breakdown-bar"><div class="breakdown-bar-fill" style="width:${(value / max) * 100}%;background:${colors[label] || "var(--slate-400)"};"></div></div>
      <span class="mono" style="font-weight:600;">${value}</span>
    </div>
  `).join("");
}

/* ---------------------------------------------------------------------
   Emergencies
   --------------------------------------------------------------------- */
function wireFilters() {
  ["filter-status", "filter-severity", "filter-fake-only"].forEach((id) => {
    document.getElementById(id).addEventListener("change", loadEmergencies);
  });
}

async function loadEmergencies() {
  const status = document.getElementById("filter-status").value;
  const severity = document.getElementById("filter-severity").value;
  const fakeOnly = document.getElementById("filter-fake-only").checked;

  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (severity) params.set("severity", severity);
  if (fakeOnly) params.set("fake_only", "true");

  const tbody = document.getElementById("emergencies-tbody");
  const empty = document.getElementById("emergencies-empty");

  try {
    const data = await apiRequest(`/admin/emergencies?${params.toString()}`);
    if (!data.emergencies.length) {
      tbody.innerHTML = "";
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";
    tbody.innerHTML = data.emergencies.map((e) => `
      <tr>
        <td class="mono">#${e.emergency_id}</td>
        <td>${escapeHtml(e.full_name)}${e.is_fake_suspected ? ' <span class="badge badge-high" style="margin-left:4px;">⚠ flagged</span>' : ""}</td>
        <td style="text-transform:capitalize;">${escapeHtml(e.emergency_type)}</td>
        <td>${severityBadge(e.severity_level)}</td>
        <td>
          <select class="filter-select status-select" data-id="${e.emergency_id}" style="padding:5px 8px;font-size:12.5px;">
            ${["pending", "acknowledged", "in_progress", "resolved", "cancelled"].map(
              (s) => `<option value="${s}" ${s === e.status ? "selected" : ""}>${s.replace("_", " ")}</option>`
            ).join("")}
          </select>
        </td>
        <td class="mono" style="font-size:12.5px;">${formatDateTime(e.created_at)}</td>
        <td class="row-actions">
          <button class="icon-btn view-emergency-btn" data-id="${e.emergency_id}" title="View details & emergency contacts">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
          <a href="https://www.google.com/maps?q=${e.latitude},${e.longitude}" target="_blank" class="icon-btn" title="View location">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
          </a>
        </td>
      </tr>
    `).join("");

    document.querySelectorAll(".view-emergency-btn").forEach((btn) => {
      btn.addEventListener("click", () => openEmergencyDetail(btn.dataset.id));
    });

    document.querySelectorAll(".status-select").forEach((select) => {
      select.addEventListener("change", async (e) => {
        const id = e.target.dataset.id;
        try {
          await apiRequest(`/admin/emergencies/${id}/status`, { method: "PUT", body: { status: e.target.value } });
          showToast(`Emergency #${id} updated to ${e.target.value.replace("_", " ")}`, "success");
          loadOverview();
        } catch (err) {
          showToast(err.message, "error");
        }
      });
    });
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ---------------------------------------------------------------------
   Users
   --------------------------------------------------------------------- */
async function loadUsers() {
  try {
    const data = await apiRequest("/admin/users");
    document.getElementById("users-tbody").innerHTML = data.users.map((u) => `
      <tr>
        <td>${escapeHtml(u.full_name)}</td>
        <td>${escapeHtml(u.email)}</td>
        <td class="mono">${escapeHtml(u.phone)}</td>
        <td style="text-transform:capitalize;">${u.role}</td>
        <td><span class="badge ${u.is_active ? "badge-low" : "badge-high"}">${u.is_active ? "Active" : "Inactive"}</span></td>
        <td>
          <button class="btn btn-outline toggle-user-btn" data-id="${u.user_id}" data-active="${u.is_active ? 1 : 0}" style="padding:6px 12px;font-size:12.5px;">
            ${u.is_active ? "Deactivate" : "Activate"}
          </button>
        </td>
      </tr>
    `).join("");

    document.querySelectorAll(".toggle-user-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.id;
        const nextActive = btn.dataset.active === "0";
        try {
          await apiRequest(`/admin/users/${id}/status`, { method: "PUT", body: { is_active: nextActive } });
          showToast("User status updated", "success");
          loadUsers();
        } catch (err) {
          showToast(err.message, "error");
        }
      });
    });
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ---------------------------------------------------------------------
   Facilities
   --------------------------------------------------------------------- */
async function loadFacilities() {
  try {
    const [hData, pData] = await Promise.all([
      apiRequest("/admin/facilities/hospitals"),
      apiRequest("/admin/facilities/police-stations"),
    ]);

    document.getElementById("hospitals-tbody").innerHTML = hData.hospitals.map((h) => `
      <tr>
        <td>${escapeHtml(h.name)}</td><td>${escapeHtml(h.address || "—")}</td><td class="mono">${escapeHtml(h.phone || "—")}</td>
        <td><button class="icon-btn danger delete-hospital-btn" data-id="${h.hospital_id}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>
        </button></td>
      </tr>
    `).join("");

    document.getElementById("police-tbody").innerHTML = pData.police_stations.map((p) => `
      <tr>
        <td>${escapeHtml(p.name)}</td><td>${escapeHtml(p.address || "—")}</td><td class="mono">${escapeHtml(p.phone || "—")}</td>
        <td><button class="icon-btn danger delete-police-btn" data-id="${p.station_id}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>
        </button></td>
      </tr>
    `).join("");

    document.querySelectorAll(".delete-hospital-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Remove this hospital?")) return;
        await apiRequest(`/admin/facilities/hospitals/${btn.dataset.id}`, { method: "DELETE" });
        loadFacilities();
      });
    });
    document.querySelectorAll(".delete-police-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Remove this police station?")) return;
        await apiRequest(`/admin/facilities/police-stations/${btn.dataset.id}`, { method: "DELETE" });
        loadFacilities();
      });
    });
  } catch (err) {
    showToast(err.message, "error");
  }
}

function wireFacilityModals() {
  const hModal = document.getElementById("hospital-modal");
  const pModal = document.getElementById("police-modal");

  document.getElementById("open-add-hospital").addEventListener("click", () => hModal.classList.add("show"));
  document.getElementById("cancel-hospital-modal").addEventListener("click", () => hModal.classList.remove("show"));
  document.getElementById("open-add-police").addEventListener("click", () => pModal.classList.add("show"));
  document.getElementById("cancel-police-modal").addEventListener("click", () => pModal.classList.remove("show"));

  document.getElementById("hospital-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await apiRequest("/admin/facilities/hospitals", {
        method: "POST",
        body: {
          name: document.getElementById("hospital-name").value.trim(),
          latitude: document.getElementById("hospital-lat").value,
          longitude: document.getElementById("hospital-lng").value,
          phone: document.getElementById("hospital-phone").value.trim(),
          address: document.getElementById("hospital-address").value.trim(),
        },
      });
      hModal.classList.remove("show");
      e.target.reset();
      showToast("Hospital added", "success");
      loadFacilities();
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  document.getElementById("police-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await apiRequest("/admin/facilities/police-stations", {
        method: "POST",
        body: {
          name: document.getElementById("police-name").value.trim(),
          latitude: document.getElementById("police-lat").value,
          longitude: document.getElementById("police-lng").value,
          phone: document.getElementById("police-phone").value.trim(),
          address: document.getElementById("police-address").value.trim(),
        },
      });
      pModal.classList.remove("show");
      e.target.reset();
      showToast("Police station added", "success");
      loadFacilities();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

/* ---------------------------------------------------------------------
   Audit logs
   --------------------------------------------------------------------- */
async function loadLogs() {
  try {
    const data = await apiRequest("/admin/logs");
    document.getElementById("logs-tbody").innerHTML = data.logs.map((l) => `
      <tr>
        <td>${escapeHtml(l.admin_name)}</td>
        <td>${escapeHtml(l.action)}</td>
        <td>${l.target_type ? `${escapeHtml(l.target_type)} #${l.target_id}` : "—"}</td>
        <td class="mono" style="font-size:12.5px;">${formatDateTime(l.created_at)}</td>
      </tr>
    `).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ---------------------------------------------------------------------
   AI Hotspot Detection (K-Means clustering)
   --------------------------------------------------------------------- */
async function loadHotspots() {
  const container = document.getElementById("hotspots-container");
  try {
    const data = await apiRequest("/admin/hotspots");

    if (!data.hotspots.length) {
      container.innerHTML = `<div class="empty-state">Not enough emergency history yet to detect meaningful clusters (need at least a handful of alerts across different locations). Raise a few test SOS alerts from different coordinates and check back.</div>`;
    } else {
      const riskColors = {
        "Critical Zone": { bg: "var(--accent-red)", fg: "#fff" },
        "High Risk Zone": { bg: "rgba(230,57,74,0.12)", fg: "#C22B3B" },
        "Moderate Zone": { bg: "var(--accent-amber-dim)", fg: "#B67614" },
        "Low Risk Zone": { bg: "var(--accent-teal-dim)", fg: "#0A8A7C" },
      };

      container.innerHTML = `
        <table class="data-table">
          <thead>
            <tr><th>Zone Center (lat, lng)</th><th>Alerts in Zone</th><th>Dominant Severity</th><th>Risk Score</th><th>Classification</th><th></th></tr>
          </thead>
          <tbody>
            ${data.hotspots.map((h) => {
              const c = riskColors[h.risk_level] || { bg: "var(--paper-dim)", fg: "var(--slate-600)" };
              return `
                <tr>
                  <td class="mono">${h.center_lat}, ${h.center_lng}</td>
                  <td>${h.emergency_count}</td>
                  <td>${severityBadge(h.dominant_severity)}</td>
                  <td class="mono">${h.risk_score}</td>
                  <td><span class="badge" style="background:${c.bg};color:${c.fg};">${h.risk_level}</span></td>
                  <td><a href="https://www.google.com/maps?q=${h.center_lat},${h.center_lng}" target="_blank" class="icon-btn" title="View on map">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                  </a></td>
                </tr>
              `;
            }).join("")}
          </tbody>
        </table>
        <p style="margin-top:16px;font-size:13px;color:var(--slate-400);">
          Risk score = 50% alert volume in the zone + 50% average severity of alerts in that zone. Recomputed live from current emergency data using K-Means clustering — not manually configured.
        </p>
      `;
    }

    // Live heatmap — driven by its own type/range filters, independent
    // of the "Live Emergencies" tab filters.
    await loadHeatmap();
  } catch (err) {
    container.innerHTML = `<div class="empty-state">Could not load hotspot data: ${err.message}</div>`;
  }
}

/* ---------------------------------------------------------------------
   Filterable live heatmap (type + time range)
   --------------------------------------------------------------------- */
async function loadHeatmap() {
  const type = document.getElementById("heatmap-type-filter").value;
  const range = document.getElementById("heatmap-range-filter").value;

  try {
    const data = await apiRequest(`/admin/heatmap-points?type=${type}&range=${range}`);
    document.getElementById("heatmap-point-count").innerText = `${data.count} alert(s) in view`;
    renderHeatmap("hotspot-heatmap", data.points);
  } catch (err) {
    document.getElementById("hotspot-heatmap").innerHTML = `<div class="map-fallback" style="color:var(--slate-600);">Could not load heatmap: ${err.message}</div>`;
  }
}

function wireHeatmapFilters() {
  document.getElementById("heatmap-type-filter").addEventListener("change", loadHeatmap);
  document.getElementById("heatmap-range-filter").addEventListener("change", loadHeatmap);
}

/* ---------------------------------------------------------------------
   Emergency detail modal (with the alert-raiser's emergency contacts)
   --------------------------------------------------------------------- */
async function openEmergencyDetail(emergencyId) {
  const modal = document.getElementById("emergency-detail-modal");
  const content = document.getElementById("emergency-detail-content");
  content.innerHTML = `<div class="empty-state">Loading...</div>`;
  modal.classList.add("show");

  try {
    const data = await apiRequest(`/admin/emergencies/${emergencyId}`);
    const e = data.emergency;

    const contactsHtml = e.emergency_contacts.length
      ? e.emergency_contacts.map((c) => `
          <div class="contact-chip">
            <div>
              <div style="font-weight:600;">${escapeHtml(c.contact_name)}</div>
              <div style="font-size:12px;color:var(--slate-400);">${escapeHtml(c.relationship || "Contact")}</div>
            </div>
            <a href="tel:${escapeHtml(c.contact_phone)}">${escapeHtml(c.contact_phone)}</a>
          </div>
        `).join("")
      : `<div class="empty-state" style="padding:16px;">This user has no emergency contacts on file.</div>`;

    content.innerHTML = `
      <div class="detail-row"><span class="detail-label">Raised by</span><span>${escapeHtml(e.full_name)} (${escapeHtml(e.phone)})</span></div>
      <div class="detail-row"><span class="detail-label">Blood group</span><span>${escapeHtml(e.blood_group || "Not on file")}</span></div>
      <div class="detail-row"><span class="detail-label">Type</span><span style="text-transform:capitalize;">${escapeHtml(e.emergency_type)}</span></div>
      <div class="detail-row"><span class="detail-label">Severity</span><span>${severityBadge(e.severity_level)}</span></div>
      <div class="detail-row"><span class="detail-label">Fake-alert score</span><span class="mono">${e.fake_score ?? "—"} ${e.is_fake_suspected ? "⚠️ flagged" : ""}</span></div>
      <div class="detail-row"><span class="detail-label">Description</span><span style="text-align:right;max-width:60%;">${escapeHtml(e.description || "—")}</span></div>
      <div class="detail-row"><span class="detail-label">Raised at</span><span class="mono">${formatDateTime(e.created_at)}</span></div>

      <h4 style="margin:18px 0 10px;font-size:14px;">Emergency Contacts (${e.emergency_contacts.length})</h4>
      ${contactsHtml}
    `;
  } catch (err) {
    content.innerHTML = `<div class="empty-state">Could not load details: ${err.message}</div>`;
  }
}

function wireEmergencyDetailModal() {
  const modal = document.getElementById("emergency-detail-modal");
  document.getElementById("close-emergency-detail").addEventListener("click", () => modal.classList.remove("show"));
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.remove("show"); });
}

/* ---------------------------------------------------------------------
   Helpers
   --------------------------------------------------------------------- */
function severityBadge(level) {
  if (!level) return `<span class="badge badge-status">Not scored</span>`;
  const cls = { Low: "badge-low", Medium: "badge-medium", High: "badge-high", Critical: "badge-critical" }[level] || "badge-status";
  return `<span class="badge ${cls}">${level}</span>`;
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
