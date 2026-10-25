// Login and sign-up pages, shown outside the app shell.
import { api, ApiError } from "../api.js";
import { state } from "../state.js";
import { html, icon, setBusy, toast } from "../ui.js";

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const FEATURES = [
  ["bell", "Expiry alerts", "See what to use up today, before it goes to waste."],
  ["cart", "Shopping list", "Plan groceries and move purchases straight into your inventory."],
  ["chart", "Waste insights", "Learn how much food you use up and how much you throw away."],
];

function passwordField(id, label, autocomplete, hint) {
  return html`<div class="field">
    <label for="${id}">${label}</label>
    <div class="password-wrap">
      <input class="input" id="${id}" name="${id}" type="password" autocomplete="${autocomplete}" required maxlength="128"
        aria-describedby="${hint ? `${id}-hint ` : ""}${id}-error">
      <button class="btn btn-ghost btn-icon reveal" type="button" aria-label="Show password" aria-pressed="false" aria-controls="${id}">${icon("eye", "sm")}</button>
    </div>
    ${hint ? html`<p class="hint" id="${id}-hint">${hint}</p>` : ""}
    <p class="error" id="${id}-error" hidden></p>
  </div>`;
}

function textField(id, label, type, autocomplete, extra = "") {
  return html`<div class="field">
    <label for="${id}">${label}</label>
    <input class="input" id="${id}" name="${id}" type="${type}" autocomplete="${autocomplete}" required ${extra} aria-describedby="${id}-error">
    <p class="error" id="${id}-error" hidden></p>
  </div>`;
}

function loginForm(notice) {
  return html`<form class="auth-form" novalidate>
    <h1 id="auth-title">Welcome back</h1>
    <p class="muted">Log in to see your kitchen.</p>
    ${notice ? html`<div class="banner banner-info" role="status">${icon("info")}<div class="banner-text">${notice}</div></div>` : ""}
    ${textField("email", "Email", "email", "email", 'maxlength="254" inputmode="email" autofocus')}
    ${passwordField("password", "Password", "current-password")}
    <p class="forgot-link"><a href="#/forgot">Forgot password?</a></p>
    <label class="check-row"><input type="checkbox" name="remember"> Keep me logged in for 30 days</label>
    <div class="banner banner-danger form-error" role="alert" hidden></div>
    <button class="btn btn-primary btn-lg btn-block" type="submit">Log in</button>
    ${state.meta?.allow_signup ? html`<p class="auth-switch">New here? <a href="#/signup">Create an account</a></p>` : ""}
  </form>`;
}

function signupForm() {
  return html`<form class="auth-form" novalidate>
    <h1 id="auth-title">Create your account</h1>
    <p class="muted">Your inventory, shopping list and settings stay private to you.</p>
    ${textField("display_name", "Your name", "text", "name", 'maxlength="50" autofocus')}
    ${textField("email", "Email", "email", "email", 'maxlength="254" inputmode="email"')}
    ${passwordField("password", "Password", "new-password", "At least 8 characters. A short phrase is easy to remember.")}
    ${passwordField("confirm", "Confirm password", "new-password")}
    <div class="banner banner-danger form-error" role="alert" hidden></div>
    <button class="btn btn-primary btn-lg btn-block" type="submit">Create account</button>
    <p class="auth-switch">Already have an account? <a href="#/login">Log in</a></p>
  </form>`;
}

function forgotForm() {
  return html`<form class="auth-form" novalidate>
    <h1 id="auth-title">Reset your password</h1>
    <p class="muted">Enter your email and the recovery code you saved when you created your account.</p>
    ${textField("email", "Email", "email", "email", 'maxlength="254" inputmode="email" autofocus')}
    <div class="field">
      <label for="recovery_code">Recovery code</label>
      <input class="input mono" id="recovery_code" name="recovery_code" type="text" autocomplete="off" autocapitalize="characters" spellcheck="false" required maxlength="64"
        placeholder="XXXXX-XXXXX-XXXXX-XXXXX" aria-describedby="recovery_code-hint recovery_code-error">
      <p class="hint" id="recovery_code-hint">Dashes and capital letters are optional.</p>
      <p class="error" id="recovery_code-error" hidden></p>
    </div>
    ${passwordField("new_password", "New password", "new-password", "At least 8 characters. Resetting signs you out on every other device.")}
    ${passwordField("confirm", "Confirm new password", "new-password")}
    <div class="banner banner-danger form-error" role="alert" hidden></div>
    <button class="btn btn-primary btn-lg btn-block" type="submit">Reset password</button>
    <p class="auth-switch">Lost your recovery code too? Ask whoever runs this server to reset your password.</p>
    <p class="auth-switch"><a href="#/login">Back to log in</a></p>
  </form>`;
}

/** Shows a one-time recovery code. Resolves when the user confirms they've saved it. */
export function recoveryCodePanel(container, code, { title, intro, button, headingTag = "h1" }) {
  container.innerHTML = html`<div class="recovery-panel stack">
    <${headingTag} id="recovery-title" tabindex="-1">${title}</${headingTag}>
    <p class="muted">${intro}</p>
    <div class="recovery-code"><code>${code}</code></div>
    <div class="banner banner-warn">${icon("alert")}<div class="banner-text">This code is shown only once. Without it, a forgotten password can only be reset by whoever runs this server.</div></div>
    <div class="page-actions">
      <button class="btn btn-secondary" type="button" data-copy>${icon("copy", "sm")}Copy code</button>
      <button class="btn btn-secondary" type="button" data-download>${icon("download", "sm")}Download as file</button>
    </div>
    <label class="check-row"><input type="checkbox" data-saved> I've saved my recovery code somewhere safe</label>
    <button class="btn btn-primary btn-lg btn-block" type="button" data-continue disabled>${button}</button>
  </div>`.value;
  container.querySelector("[data-copy]").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(code);
      toast("Recovery code copied.", "info");
    } catch {
      toast("Couldn't copy automatically. Select the code and copy it yourself.", "info");
    }
  });
  container.querySelector("[data-download]").addEventListener("click", () => {
    const text = `Food Expiry Tracker recovery code\n\n${code}\n\nUse it on the "Forgot password?" page. It works once; you get a new one after using it.\n`;
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    link.download = "food-expiry-tracker-recovery-code.txt";
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  });
  const saved = container.querySelector("[data-saved]");
  const next = container.querySelector("[data-continue]");
  saved.addEventListener("change", () => { next.disabled = !saved.checked; });
  container.querySelector("#recovery-title").focus();
  return new Promise((resolve) => next.addEventListener("click", resolve, { once: true }));
}

function closedNotice() {
  return html`<div class="auth-form">
    <h1 id="auth-title">Sign-up is closed</h1>
    <p class="muted">New accounts are turned off on this server. Ask the owner to create an account for you.</p>
    <a class="btn btn-primary btn-lg btn-block" href="#/login">Back to log in</a>
  </div>`;
}

export function showErrors(form, errors, message) {
  form.querySelectorAll(".error").forEach((el) => { el.hidden = true; el.textContent = ""; });
  form.querySelectorAll("[aria-invalid]").forEach((el) => el.removeAttribute("aria-invalid"));
  let first = null;
  for (const [field, text] of Object.entries(errors)) {
    const input = form.elements[field];
    const el = form.querySelector(`#${field}-error`);
    if (!input || !el) continue;
    el.textContent = text;
    el.hidden = false;
    input.setAttribute("aria-invalid", "true");
    first ??= input;
  }
  const banner = form.querySelector(".form-error");
  banner.hidden = !message;
  banner.textContent = message || "";
  (first || (message ? banner : null))?.focus?.();
}

export function bindPasswordToggles(root) {
  root.querySelectorAll(".reveal").forEach((button) => {
    button.addEventListener("click", () => {
      const input = root.querySelector(`#${button.getAttribute("aria-controls")}`);
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.setAttribute("aria-pressed", String(show));
      button.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  });
}

export function passwordProblem(value) {
  if (!value) return "Enter a password";
  if (value.length < 8) return "Use at least 8 characters";
  if (value.length > 128) return "Use 128 characters or fewer";
  if (!value.trim()) return "Password cannot be only spaces";
  return null;
}

/** Renders the login or sign-up page. Calls onAuthenticated(user) after success. */
export function renderAuth(container, mode, { notice, onAuthenticated }) {
  const signup = mode === "signup";
  const forgot = mode === "forgot";
  const content = signup ? (state.meta?.allow_signup ? signupForm() : closedNotice()) : forgot ? forgotForm() : loginForm(notice);
  container.innerHTML = html`<div class="auth-shell">
    <section class="auth-intro" aria-hidden="true">
      <div class="brand"><span class="brand-mark">${icon("leaf")}</span><span class="brand-name">Food Expiry Tracker</span></div>
      <p class="auth-tagline">Waste less food. Spend less money. Always know what's in your kitchen.</p>
      <ul class="auth-features">${FEATURES.map(([name, title, text]) => html`<li><span class="stat-icon">${icon(name)}</span><span><strong>${title}</strong><br>${text}</span></li>`)}</ul>
    </section>
    <main class="auth-card card" aria-labelledby="auth-title">
      <div class="brand auth-brand-mobile"><span class="brand-mark">${icon("leaf")}</span><span class="brand-name">Food Expiry Tracker</span></div>
      ${content}
    </main>
  </div>`.value;
  document.title = `${signup ? "Create account" : forgot ? "Reset password" : "Log in"} · Food Expiry Tracker`;
  const form = container.querySelector("form");
  if (!form) return;
  bindPasswordToggles(form);
  form.querySelector("[autofocus]")?.focus();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector('[type="submit"]');
    if (button.disabled) return;
    const values = Object.fromEntries(new FormData(form));
    const email = (values.email || "").trim().toLowerCase();
    const errors = {};
    if (!email) errors.email = "Enter your email address";
    else if (!EMAIL.test(email)) errors.email = "Enter a valid email address, like name@example.com";
    if (forgot) {
      if (!values.recovery_code.trim()) errors.recovery_code = "Enter your recovery code";
      const problem = passwordProblem(values.new_password);
      if (problem) errors.new_password = problem;
      else if (values.confirm !== values.new_password) errors.confirm = "Passwords don't match";
    } else if (signup) {
      if (!values.display_name.trim()) errors.display_name = "Enter your name";
      const problem = passwordProblem(values.password);
      if (problem) errors.password = problem;
      else if (values.confirm !== values.password) errors.confirm = "Passwords don't match";
    } else if (!values.password) {
      errors.password = "Enter your password";
    }
    if (Object.keys(errors).length) { showErrors(form, errors); return; }
    showErrors(form, {});
    setBusy(button, true, signup ? "Creating account…" : forgot ? "Resetting…" : "Logging in…");
    try {
      let user;
      if (forgot) {
        user = await api.post("/api/auth/reset-password", { email, recovery_code: values.recovery_code.trim(), new_password: values.new_password });
      } else if (signup) {
        user = await api.post("/api/auth/register", { display_name: values.display_name.trim(), email, password: values.password });
      } else {
        user = await api.post("/api/auth/login", { email, password: values.password, remember: values.remember === "on" });
      }
      if (user.recovery_code) {
        const { recovery_code: code, ...account } = user;
        user = account;
        const holder = document.createElement("div");
        form.replaceWith(holder);
        document.title = `Recovery code · Food Expiry Tracker`;
        await recoveryCodePanel(holder, code, forgot
          ? { title: "Password reset", intro: "Your old recovery code no longer works. Here is your new one:", button: "Continue to my kitchen" }
          : { title: "Save your recovery code", intro: "If you ever forget your password, this code lets you set a new one.", button: "Continue to my kitchen" });
      }
      await onAuthenticated(user, signup, forgot);
    } catch (error) {
      const fields = error instanceof ApiError ? { ...error.fields } : {};
      delete fields._;
      const placed = Object.keys(fields).some((f) => form.querySelector(`#${f}-error`));
      showErrors(form, fields, placed ? "" : error.message);
      if (!signup && !forgot && error.status === 401) {
        form.elements.password.value = "";
        form.elements.password.focus();
      }
      setBusy(button, false);
    }
  });
}
