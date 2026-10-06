/**
 * auth.js
 * -------
 * Handles both the login form and the register form. Each page only has
 * one of the two forms in the DOM, so we check for existence before
 * attaching listeners.
 */

document.addEventListener("DOMContentLoaded", () => {
  redirectIfLoggedIn(); // bounce straight to dashboard if already logged in

  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");

  if (loginForm) initLoginForm(loginForm);
  if (registerForm) initRegisterForm(registerForm);
});

/* ---------------------------------------------------------------------
   LOGIN
   --------------------------------------------------------------------- */
function initLoginForm(form) {
  const alertBox = document.getElementById("form-alert");
  const submitBtn = form.querySelector('button[type="submit"]');

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert(alertBox);

    const email = form.email.value.trim();
    const password = form.password.value;

    if (!email || !password) {
      showAlert(alertBox, "Please enter both email and password.");
      return;
    }

    setButtonLoading(submitBtn, true, "Signing in");
    try {
      const data = await apiRequest("/auth/login", {
        method: "POST",
        auth: false,
        body: { email, password },
      });

      Session.saveToken(data.token);
      Session.saveUser(data.user);
      showToast(`Welcome back, ${data.user.full_name.split(" ")[0]}!`, "success");

      setTimeout(() => {
        window.location.href = data.user.role === "admin" ? "admin_dashboard.html" : "user_dashboard.html";
      }, 500);
    } catch (err) {
      // Special case: account exists and password was correct, but the
      // email hasn't been verified yet — send them to finish that instead
      // of just showing a dead-end error.
      if (err.requiresVerification) {
        showToast("Please verify your email to continue.", "warning");
        setTimeout(() => {
          window.location.href = `verify_email.html?email=${encodeURIComponent(err.email || email)}`;
        }, 800);
        return;
      }
      showAlert(alertBox, err.message);
    } finally {
      setButtonLoading(submitBtn, false);
    }
  });
}

/* ---------------------------------------------------------------------
   REGISTER
   --------------------------------------------------------------------- */
function initRegisterForm(form) {
  const alertBox = document.getElementById("form-alert");
  const submitBtn = form.querySelector('button[type="submit"]');
  const passwordInput = form.password;
  const strengthBar = document.getElementById("password-strength-bar");

  if (passwordInput && strengthBar) {
    passwordInput.addEventListener("input", () => {
      updatePasswordStrength(passwordInput.value, strengthBar);
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert(alertBox);

    const payload = {
      full_name: form.full_name.value.trim(),
      email: form.email.value.trim(),
      phone: form.phone.value.trim(),
      password: form.password.value,
      blood_group: form.blood_group ? form.blood_group.value : null,
      home_address: form.home_address ? form.home_address.value.trim() : null,
    };

    const confirmPassword = form.confirm_password.value;
    if (payload.password !== confirmPassword) {
      showAlert(alertBox, "Passwords do not match.");
      return;
    }
    const PASSWORD_PATTERN = /^(?=.*[A-Z])(?=.*\d).{8,}$/;
    if (!PASSWORD_PATTERN.test(payload.password)) {
      showAlert(alertBox, "Password must be at least 8 characters and include one uppercase letter and one number.");
      return;
    }

    setButtonLoading(submitBtn, true, "Creating account");
    try {
      const data = await apiRequest("/auth/register", {
        method: "POST",
        auth: false,
        body: payload,
      });

      showToast("Account created! Please verify your email to continue.", "success");
      setTimeout(() => {
        window.location.href = `verify_email.html?email=${encodeURIComponent(data.email || payload.email)}`;
      }, 700);
    } catch (err) {
      showAlert(alertBox, err.message);
    } finally {
      setButtonLoading(submitBtn, false);
    }
  });
}

/* ---------------------------------------------------------------------
   Helpers
   --------------------------------------------------------------------- */
function showAlert(box, message) {
  if (!box) return;
  box.innerText = message;
  box.classList.add("show");
}

function hideAlert(box) {
  if (!box) return;
  box.classList.remove("show");
  box.innerText = "";
}

function updatePasswordStrength(password, bar) {
  let score = 0;
  if (password.length >= 6) score++;
  if (password.length >= 10) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  const percent = (score / 5) * 100;
  bar.style.width = `${percent}%`;

  if (score <= 2) bar.style.background = "var(--accent-red)";
  else if (score <= 3) bar.style.background = "var(--accent-amber)";
  else bar.style.background = "var(--accent-teal)";
}
