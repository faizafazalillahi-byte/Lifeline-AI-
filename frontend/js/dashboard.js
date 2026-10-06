/**
 * dashboard.js
 * ------------
 * Powers user_dashboard.html: sidebar tab switching, dashboard summary
 * stats, emergency contacts CRUD, emergency history table, notifications
 * list, and profile editing.
 */

document.addEventListener("DOMContentLoaded", () => {
  requireAuth();
  initSidebar();
  loadUserChip();
  loadOverview();
  loadContacts();
  loadHistory();
  loadNotifications();
  loadProfileForm();
  wireContactModal();
  wireProfileForm();
  wireLogout();
});

/* ---------------------------------------------------------------------
   Sidebar tab switching
   --------------------------------------------------------------------- */
function initSidebar() {
  const navItems = document.querySelectorAll(".dash-nav-item[data-panel]");
  navItems.forEach((item) => {
    item.addEventListener("click", () => {
      navItems.forEach((i) => i.classList.remove("active"));
      item.classList.add("active");

      document.querySelectorAll(".dash-panel").forEach((p) => p.classList.remove("active"));
      const target = document.getElementById(`panel-${item.dataset.panel}`);
      if (target) target.classList.add("active");
    });
  });
}

function loadUserChip() {
  const user = Session.getUser();
  if (!user) return;
  const initials = user.full_name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  document.getElementById("sidebar-avatar").innerText = initials;
  document.getElementById("sidebar-name").innerText = user.full_name;
  document.getElementById("sidebar-role").innerText = user.role;
  document.getElementById("overview-name").innerText = user.full_name.split(" ")[0];
}

function wireLogout() {
  document.getElementById("logout-btn").addEventListener("click", () => Session.logout());
}

/* ---------------------------------------------------------------------
   Overview / dashboard summary
   --------------------------------------------------------------------- */
async function loadOverview() {
  try {
    const data = await apiRequest("/user/dashboard-summary");
    const s = data.summary;
    document.getElementById("stat-total").innerText = s.total_emergencies;
    document.getElementById("stat-active").innerText = s.active_emergencies;
    document.getElementById("stat-contacts").innerText = s.contacts_count;
    document.getElementById("stat-last-severity").innerText = s.last_emergency ? s.last_emergency.severity_level : "—";

    const container = document.getElementById("last-emergency-content");
    if (s.last_emergency) {
      const e = s.last_emergency;
      container.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
          <div>
            <div style="font-weight:600;text-transform:capitalize;">${escapeHtml(e.emergency_type)} emergency</div>
            <div style="font-size:13px;color:var(--slate-400);" class="mono">${formatDateTime(e.created_at)}</div>
          </div>
          <div style="display:flex;gap:10px;align-items:center;">
            ${severityBadge(e.severity_level)}
            ${statusBadge(e.status)}
          </div>
        </div>`;
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ---------------------------------------------------------------------
   Emergency contacts
   --------------------------------------------------------------------- */
async function loadContacts() {
  const tbody = document.getElementById("contacts-tbody");
  const empty = document.getElementById("contacts-empty");
  try {
    const data = await apiRequest("/user/contacts");
    if (!data.contacts.length) {
      tbody.innerHTML = "";
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";
    tbody.innerHTML = data.contacts.map((c) => `
      <tr>
        <td>${escapeHtml(c.contact_name)}</td>
        <td class="mono">${escapeHtml(c.contact_phone)}</td>
        <td>${escapeHtml(c.relationship || "—")}</td>
        <td class="row-actions">
          <button class="icon-btn" onclick="openEditContact(${c.contact_id}, '${escapeAttr(c.contact_name)}', '${escapeAttr(c.contact_phone)}', '${escapeAttr(c.relationship || "")}')" title="Edit">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4z"/></svg>
          </button>
          <button class="icon-btn danger" onclick="deleteContactHandler(${c.contact_id})" title="Delete">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>
          </button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function wireContactModal() {
  const modal = document.getElementById("contact-modal");
  const form = document.getElementById("contact-form");

  document.getElementById("open-add-contact").addEventListener("click", () => {
    document.getElementById("contact-modal-title").innerText = "Add Emergency Contact";
    form.reset();
    document.getElementById("contact-id").value = "";
    modal.classList.add("show");
  });

  document.getElementById("cancel-contact-modal").addEventListener("click", () => {
    modal.classList.remove("show");
  });

  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("show");
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const contactId = document.getElementById("contact-id").value;
    const payload = {
      contact_name: document.getElementById("contact-name").value.trim(),
      contact_phone: document.getElementById("contact-phone").value.trim(),
      relationship: document.getElementById("contact-relationship").value.trim(),
    };

    const submitBtn = form.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true, "Saving");
    try {
      if (contactId) {
        await apiRequest(`/user/contacts/${contactId}`, { method: "PUT", body: payload });
        showToast("Contact updated", "success");
      } else {
        await apiRequest("/user/contacts", { method: "POST", body: payload });
        showToast("Contact added", "success");
      }
      modal.classList.remove("show");
      loadContacts();
      loadOverview();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setButtonLoading(submitBtn, false);
    }
  });
}

function openEditContact(id, name, phone, relationship) {
  document.getElementById("contact-modal-title").innerText = "Edit Emergency Contact";
  document.getElementById("contact-id").value = id;
  document.getElementById("contact-name").value = name;
  document.getElementById("contact-phone").value = phone;
  document.getElementById("contact-relationship").value = relationship;
  document.getElementById("contact-modal").classList.add("show");
}

async function deleteContactHandler(id) {
  if (!confirm("Remove this emergency contact?")) return;
  try {
    await apiRequest(`/user/contacts/${id}`, { method: "DELETE" });
    showToast("Contact removed", "success");
    loadContacts();
    loadOverview();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ---------------------------------------------------------------------
   Emergency history
   --------------------------------------------------------------------- */
async function loadHistory() {
  const tbody = document.getElementById("history-tbody");
  const empty = document.getElementById("history-empty");
  try {
    const data = await apiRequest("/user/history");
    if (!data.history.length) {
      tbody.innerHTML = "";
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";
    tbody.innerHTML = data.history.map((h) => `
      <tr>
        <td class="mono">${formatDateTime(h.created_at)}</td>
        <td style="text-transform:capitalize;">${escapeHtml(h.emergency_type)}</td>
        <td>${severityBadge(h.severity_level)}</td>
        <td>${statusBadge(h.status)}</td>
      </tr>
    `).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ---------------------------------------------------------------------
   Notifications
   --------------------------------------------------------------------- */
async function loadNotifications() {
  const list = document.getElementById("notifications-list");
  const empty = document.getElementById("notifications-empty");
  try {
    const data = await apiRequest("/user/notifications");
    if (!data.notifications.length) {
      list.innerHTML = "";
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";
    list.innerHTML = data.notifications.map((n) => `
      <div style="display:flex;gap:14px;padding:14px 0;border-bottom:1px solid var(--paper-dim);${n.is_read ? "opacity:0.6;" : ""}">
        <div style="width:8px;height:8px;border-radius:50%;background:${n.is_read ? "var(--slate-400)" : "var(--accent-red)"};margin-top:6px;flex-shrink:0;"></div>
        <div style="flex:1;">
          <div style="font-size:14px;">${escapeHtml(n.message)}</div>
          <div class="mono" style="font-size:12px;color:var(--slate-400);margin-top:3px;">${formatDateTime(n.created_at)}</div>
        </div>
      </div>
    `).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ---------------------------------------------------------------------
   Profile
   --------------------------------------------------------------------- */
async function loadProfileForm() {
  try {
    const data = await apiRequest("/user/profile");
    const u = data.user;
    document.getElementById("profile-email").value = u.email;
    document.getElementById("profile-full-name").value = u.full_name;
    document.getElementById("profile-phone").value = u.phone;
    document.getElementById("profile-blood-group").value = u.blood_group || "";
    document.getElementById("profile-address").value = u.home_address || "";
  } catch (err) {
    showToast(err.message, "error");
  }
}

function wireProfileForm() {
  const form = document.getElementById("profile-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      full_name: document.getElementById("profile-full-name").value.trim(),
      phone: document.getElementById("profile-phone").value.trim(),
      blood_group: document.getElementById("profile-blood-group").value,
      home_address: document.getElementById("profile-address").value.trim(),
    };
    const submitBtn = form.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true, "Saving");
    try {
      await apiRequest("/user/profile", { method: "PUT", body: payload });
      const user = Session.getUser();
      user.full_name = payload.full_name;
      Session.saveUser(user);
      loadUserChip();
      showToast("Profile updated", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setButtonLoading(submitBtn, false);
    }
  });
}

/* ---------------------------------------------------------------------
   Small render helpers
   --------------------------------------------------------------------- */
function severityBadge(level) {
  if (!level) return `<span class="badge badge-status">Not scored</span>`;
  const cls = { Low: "badge-low", Medium: "badge-medium", High: "badge-high", Critical: "badge-critical" }[level] || "badge-status";
  return `<span class="badge ${cls}">${level}</span>`;
}

function statusBadge(status) {
  const labels = {
    pending: "Pending", acknowledged: "Acknowledged", in_progress: "In Progress",
    resolved: "Resolved", cancelled: "Cancelled",
  };
  return `<span class="badge badge-status">${labels[status] || status}</span>`;
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function escapeAttr(str) {
  return escapeHtml(str).replace(/'/g, "&#39;");
}
