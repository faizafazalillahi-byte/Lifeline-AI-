/**
 * verify.js
 * ---------
 * Powers verify_email.html: reads the email from the query string
 * (set by register.html on redirect), submits the verification code,
 * and handles "resend code".
 */

function getEmailFromQuery() {
  const params = new URLSearchParams(window.location.search);
  return params.get("email") || "";
}

document.addEventListener("DOMContentLoaded", () => {
  const email = getEmailFromQuery();
  if (!email) {
    // No email context — send them back to register instead of a dead-end page.
    window.location.href = "register.html";
    return;
  }
  document.getElementById("verify-email-display").innerText = email;

  const form = document.getElementById("verify-form");
  const alertBox = document.getElementById("form-alert");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert(alertBox);

    const code = document.getElementById("code").value.trim();
    if (code.length !== 6) {
      showAlert(alertBox, "Please enter the full 6-digit code.");
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true, "Verifying");

    try {
      const data = await apiRequest("/auth/verify-email", {
        method: "POST",
        auth: false,
        body: { email, code },
      });

      Session.saveToken(data.token);
      Session.saveUser(data.user);
      showToast("Email verified! Welcome to LifeLine AI.", "success");
      setTimeout(() => { window.location.href = "user_dashboard.html"; }, 500);
    } catch (err) {
      showAlert(alertBox, err.message);
    } finally {
      setButtonLoading(submitBtn, false);
    }
  });

  document.getElementById("resend-link").addEventListener("click", async (e) => {
    e.preventDefault();
    try {
      const data = await apiRequest("/auth/resend-verification", {
        method: "POST",
        auth: false,
        body: { email },
      });
      showToast(data.message || "A new code has been sent.", "success");
    } catch (err) {
      showToast(err.message, "error");
    }
  });
});

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
