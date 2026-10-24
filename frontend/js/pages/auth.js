// Login and sign-up pages, shown outside the app shell.
import { api, ApiError } from "../api.js";
import { state } from "../state.js";
import { html, icon, setBusy } from "../ui.js";

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
  const content = signup ? (state.meta?.allow_signup ? signupForm() : closedNotice()) : loginForm(notice);
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
  document.title = `${signup ? "Create account" : "Log in"} · Food Expiry Tracker`;
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
    if (signup) {
      if (!values.display_name.trim()) errors.display_name = "Enter your name";
      const problem = passwordProblem(values.password);
      if (problem) errors.password = problem;
      else if (values.confirm !== values.password) errors.confirm = "Passwords don't match";
    } else if (!values.password) {
      errors.password = "Enter your password";
    }
    if (Object.keys(errors).length) { showErrors(form, errors); return; }
    showErrors(form, {});
    setBusy(button, true, signup ? "Creating account…" : "Logging in…");
    try {
      const user = signup
        ? await api.post("/api/auth/register", { display_name: values.display_name.trim(), email, password: values.password })
        : await api.post("/api/auth/login", { email, password: values.password, remember: values.remember === "on" });
      await onAuthenticated(user, signup);
    } catch (error) {
      const fields = error instanceof ApiError ? { ...error.fields } : {};
      delete fields._;
      const placed = Object.keys(fields).some((f) => form.querySelector(`#${f}-error`));
      showErrors(form, fields, placed ? "" : error.message);
      if (!signup && error.status === 401) {
        form.elements.password.value = "";
        form.elements.password.focus();
      }
      setBusy(button, false);
    }
  });
}
