/**
 * main.js
 * -------
 * Shared helpers used across every page: authenticated fetch wrapper,
 * toast notifications, session storage helpers, and navbar auth-state
 * rendering. Loaded on every HTML page BEFORE the page-specific script.
 */

/* ---------------------------------------------------------------------
   Session helpers
   --------------------------------------------------------------------- */
const Session = {
  saveToken(token) {
    localStorage.setItem(CONFIG.TOKEN_STORAGE_KEY, token);
  },
  getToken() {
    return localStorage.getItem(CONFIG.TOKEN_STORAGE_KEY);
  },
  saveUser(user) {
    localStorage.setItem(CONFIG.USER_STORAGE_KEY, JSON.stringify(user));
  },
  getUser() {
    const raw = localStorage.getItem(CONFIG.USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  },
  isLoggedIn() {
    return !!this.getToken();
  },
  clear() {
    localStorage.removeItem(CONFIG.TOKEN_STORAGE_KEY);
    localStorage.removeItem(CONFIG.USER_STORAGE_KEY);
  },
  logout() {
    this.clear();
    window.location.href = "login.html";
  },
};

/* ---------------------------------------------------------------------
   Authenticated fetch wrapper
   --------------------------------------------------------------------- */
async function apiRequest(path, { method = "GET", body = null, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && Session.getToken()) {
    headers["Authorization"] = `Bearer ${Session.getToken()}`;
  }

  let response;
  try {
    response = await fetch(`${CONFIG.API_BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    });
  } catch (networkErr) {
    throw new Error("Cannot reach the LifeLine AI server. Is the backend running?");
  }

  let data = {};
  try {
    data = await response.json();
  } catch (_) {
    data = {};
  }

  if (response.status === 401) {
    // Token invalid/expired -> force re-login
    Session.clear();
    if (!location.pathname.endsWith("login.html")) {
      window.location.href = "login.html";
    }
  }

  if (!response.ok) {
    const error = new Error(data.message || `Request failed (${response.status})`);
    // Attach any extra fields the backend sent (e.g. requires_verification,
    // email) so callers can branch on them without re-parsing the response.
    Object.keys(data).forEach((key) => {
      if (key !== "message") {
        const camelKey = key.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
        error[camelKey] = data[key];
      }
    });
    throw error;
  }
  return data;
}

/* ---------------------------------------------------------------------
   Toast notifications
   --------------------------------------------------------------------- */
function ensureToastContainer() {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }
  return container;
}

function showToast(message, type = "info", duration = 4000) {
  const container = ensureToastContainer();
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerText = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("hide");
    setTimeout(() => toast.remove(), 200);
  }, duration);
}

/* ---------------------------------------------------------------------
   Route guards (called at top of protected pages)
   --------------------------------------------------------------------- */
function requireAuth() {
  if (!Session.isLoggedIn()) {
    window.location.href = "login.html";
  }
}

function requireAdmin() {
  requireAuth();
  const user = Session.getUser();
  if (!user || user.role !== "admin") {
    window.location.href = "user_dashboard.html";
  }
}

function redirectIfLoggedIn() {
  if (Session.isLoggedIn()) {
    const user = Session.getUser();
    window.location.href = user && user.role === "admin" ? "admin_dashboard.html" : "user_dashboard.html";
  }
}

/* ---------------------------------------------------------------------
   Small utilities
   --------------------------------------------------------------------- */
function setButtonLoading(button, isLoading, loadingText = "Please wait") {
  if (isLoading) {
    button.dataset.originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span class="spinner"></span> ${loadingText}`;
  } else {
    button.disabled = false;
    button.innerHTML = button.dataset.originalText || button.innerHTML;
  }
}

function formatDateTime(isoString) {
  if (!isoString) return "—";
  const d = new Date(isoString);
  return d.toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}
