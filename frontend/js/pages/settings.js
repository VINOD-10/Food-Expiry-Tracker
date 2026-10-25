// Settings: every control here is persisted in the SQLite settings table.
import { api, ApiError } from "../api.js";
import { bindPasswordToggles, passwordProblem, recoveryCodePanel, showErrors } from "./auth.js";
import { applySettings, applyTheme, dataChanged, state } from "../state.js";
import { formatDate, html, icon, pageHead, setBusy, toast } from "../ui.js";

const DATE_LABELS = { "%d-%m-%Y": "DD-MM-YYYY", "%d/%m/%Y": "DD/MM/YYYY", "%m/%d/%Y": "MM/DD/YYYY", "%Y-%m-%d": "YYYY-MM-DD", "%d %b %Y": "DD Mon YYYY" };
const SORT_LABELS = { "Expiry date": "Expiry date (soonest first)", Newest: "Newest added", Name: "Name (A–Z)" };
const THEME_LABELS = { system: "Match device", light: "Light", dark: "Dark" };

function permissionText() {
  if (!("Notification" in window)) return "This browser doesn't support notifications.";
  if (!window.isSecureContext) return "Notifications need a secure (https or localhost) connection.";
  return {
    granted: "Permission granted. You'll get at most one summary a day, and only while this app is open in a browser tab.",
    denied: "Notifications are blocked for this site. You can allow them in your browser's site settings.",
    default: "Your browser will ask for permission when you turn this on.",
  }[Notification.permission];
}

export async function render(view) {
  const s = state.settings;
  const meta = state.meta;
  const sample = meta.today;
  const notifySupported = "Notification" in window && window.isSecureContext;

  view.innerHTML = html`
    ${pageHead({ eyebrow: "Settings", title: "Settings", subtitle: "Your preferences are saved to your account and apply wherever you log in." })}
    <form class="card" id="settings-form" novalidate>
      <section class="settings-section">
        <div><h2>Expiry alerts</h2><p>Food expiring within this many days is marked "Expiring soon" and appears in Expiry Alerts.</p></div>
        <div class="field"><label for="s-threshold">Alert threshold (days)</label>
          <input class="input" id="s-threshold" name="expiry_threshold" type="number" min="0" max="30" step="1" inputmode="numeric" required
            value="${s.expiry_threshold}" style="max-width:140px" aria-describedby="s-threshold-hint s-threshold-error">
          <p class="hint" id="s-threshold-hint">0 to 30 days. Set it to 0 to alert only on the expiry date itself.</p>
          <p class="error" id="s-threshold-error" hidden></p></div>
      </section>
      <section class="settings-section">
        <div><h2>Browser notifications</h2><p>Optional. These are sent only while the app is open in a tab, never when it's closed.</p></div>
        <div class="field">
          <label class="switch"><input type="checkbox" name="browser_notifications" id="s-notify" ${s.browser_notifications ? "checked" : ""}
            ${notifySupported ? "" : "disabled"} aria-describedby="s-notify-status"><span>Show a daily summary notification of active alerts</span></label>
          <p class="hint" id="s-notify-status">${permissionText()}</p></div>
      </section>
      <section class="settings-section">
        <div><h2>Display</h2><p>How dates appear and how the inventory is sorted by default.</p></div>
        <div class="stack">
          <div class="field"><label for="s-date">Date format</label>
            <select class="select" id="s-date" name="date_format">${meta.date_formats.map((f) =>
              html`<option value="${f}" ${f === s.date_format ? "selected" : ""}>${DATE_LABELS[f] || f} (e.g. ${formatDate(sample, f)})</option>`)}</select></div>
          <div class="field"><label for="s-sort">Default inventory sort</label>
            <select class="select" id="s-sort" name="default_sort">${meta.sorts.map((v) =>
              html`<option value="${v}" ${v === s.default_sort ? "selected" : ""}>${SORT_LABELS[v] || v}</option>`)}</select></div>
          <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="label" style="margin-bottom:6px">Theme</legend>
            <div class="theme-options">${meta.themes.map((t) => html`<label class="radio-card"><input type="radio" name="theme" value="${t}" ${t === s.theme ? "checked" : ""}><span>${THEME_LABELS[t] || t}</span></label>`)}</div>
          </fieldset>
        </div>
      </section>
      <section class="settings-section">
        <div><h2>About your data</h2><p>Where your information is kept.</p></div>
        <div class="small muted stack" style="gap:8px">
          <p>${icon("info", "sm")} Everything is stored in a local SQLite database on this computer. Each account's inventory, shopping list and settings are private to that account. Nothing is sent to other services.</p>
          <p>Dates are worked out in the <strong>${meta.timezone}</strong> timezone. Today is ${formatDate(meta.today)}.</p>
        </div>
      </section>
      <div class="list-meta" style="justify-content:flex-end">
        <button class="btn btn-secondary" type="reset">Discard changes</button>
        <button class="btn btn-primary btn-lg" type="submit">${icon("check")}Save settings</button>
      </div>
    </form>
    <section class="card" style="margin-top:16px" aria-labelledby="account-title">
      <div class="settings-section">
        <div><h2 id="account-title">Account</h2><p>You're signed in as <strong>${state.user.display_name}</strong> (${state.user.email}).
          ${state.user.is_owner ? "This is the owner account, so the desktop app shows your inventory." : ""}</p></div>
        <form id="password-form" class="stack" novalidate>
          <h3>Change password</h3>
          <div class="field"><label for="current_password">Current password</label>
            <div class="password-wrap"><input class="input" id="current_password" name="current_password" type="password" autocomplete="current-password" required maxlength="128" aria-describedby="current_password-error">
            <button class="btn btn-ghost btn-icon reveal" type="button" aria-label="Show password" aria-pressed="false" aria-controls="current_password">${icon("eye", "sm")}</button></div>
            <p class="error" id="current_password-error" hidden></p></div>
          <div class="field"><label for="new_password">New password</label>
            <div class="password-wrap"><input class="input" id="new_password" name="new_password" type="password" autocomplete="new-password" required maxlength="128" aria-describedby="new_password-hint new_password-error">
            <button class="btn btn-ghost btn-icon reveal" type="button" aria-label="Show password" aria-pressed="false" aria-controls="new_password">${icon("eye", "sm")}</button></div>
            <p class="hint" id="new_password-hint">At least 8 characters. Changing it signs you out on your other devices.</p>
            <p class="error" id="new_password-error" hidden></p></div>
          <div class="banner banner-danger form-error" role="alert" hidden></div>
          <div class="page-actions">
            <button class="btn btn-primary" type="submit">Change password</button>
            <button class="btn btn-secondary" type="button" id="settings-logout">${icon("logout", "sm")}Log out</button>
          </div>
        </form>
      </div>
      <div class="settings-section">
        <div><h2 id="recovery-heading">Recovery code</h2><p>Lets you set a new password from the "Forgot password?" page if you forget yours.</p></div>
        <div class="stack" id="recovery-area">
          ${state.user.has_recovery_code
            ? html`<p class="muted">You have a recovery code. Making a new one stops the old one from working.</p>`
            : html`<div class="banner banner-warn" role="status">${icon("alert")}<div class="banner-text">Your account doesn't have a recovery code yet. Create one now so you can't get locked out.</div></div>`}
          <form id="recovery-form" class="stack" novalidate>
            <div class="field"><label for="recovery_password">Confirm with your password</label>
              <div class="password-wrap"><input class="input" id="recovery_password" name="password" type="password" autocomplete="current-password" required maxlength="128" aria-describedby="password-error">
              <button class="btn btn-ghost btn-icon reveal" type="button" aria-label="Show password" aria-pressed="false" aria-controls="recovery_password">${icon("eye", "sm")}</button></div>
              <p class="error" id="password-error" hidden></p></div>
            <div class="banner banner-danger form-error" role="alert" hidden></div>
            <div class="page-actions"><button class="btn btn-secondary" type="submit">${icon("key", "sm")}${state.user.has_recovery_code ? "Create a new recovery code" : "Create my recovery code"}</button></div>
          </form>
        </div>
      </div>
    </section>`.value;

  const form = view.querySelector("#settings-form");
  const notify = form.elements.browser_notifications;

  // Preview the theme immediately; it's saved with the form.
  form.addEventListener("change", (event) => { if (event.target.name === "theme") applyTheme(event.target.value); });
  form.addEventListener("reset", () => setTimeout(() => applyTheme(state.settings.theme), 0));

  notify.addEventListener("change", async () => {
    if (!notifySupported || !notify.checked || Notification.permission === "granted") return;
    if (Notification.permission === "denied") {
      notify.checked = false;
      toast("Notifications are blocked in your browser settings for this site.", "error");
      return;
    }
    const result = await Notification.requestPermission();
    view.querySelector("#s-notify-status").textContent = permissionText();
    if (result !== "granted") {
      notify.checked = false;
      toast("Notification permission was not granted, so notifications stay off.", "info");
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const threshold = form.elements.expiry_threshold;
    const errorEl = view.querySelector("#s-threshold-error");
    const value = Number(threshold.value);
    if (threshold.value === "" || !Number.isInteger(value) || value < 0 || value > 30) {
      errorEl.textContent = "Enter a whole number from 0 to 30.";
      errorEl.hidden = false;
      threshold.setAttribute("aria-invalid", "true");
      threshold.focus();
      return;
    }
    errorEl.hidden = true;
    threshold.removeAttribute("aria-invalid");
    const button = form.querySelector('[type="submit"]');
    if (button.disabled) return;
    setBusy(button, true);
    try {
      const saved = await api.put("/api/settings", {
        expiry_threshold: value,
        date_format: form.elements.date_format.value,
        default_sort: form.elements.default_sort.value,
        theme: form.elements.theme.value,
        browser_notifications: notify.checked && notifySupported && Notification.permission === "granted",
      });
      applySettings(saved);
      toast("Settings saved.");
      dataChanged();
      await render(view);
    } catch (error) {
      toast(`Couldn't save settings: ${error.message}`, "error");
      setBusy(button, false);
    }
  });
  const passwordForm = view.querySelector("#password-form");
  bindPasswordToggles(passwordForm);
  view.querySelector("#settings-logout").addEventListener("click", () => window.dispatchEvent(new Event("fet:logout")));
  passwordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = passwordForm.querySelector('[type="submit"]');
    if (button.disabled) return;
    const current = passwordForm.elements.current_password.value;
    const next = passwordForm.elements.new_password.value;
    const errors = {};
    if (!current) errors.current_password = "Enter your current password";
    const problem = passwordProblem(next);
    if (problem) errors.new_password = problem;
    else if (next === current) errors.new_password = "Choose a password different from your current one";
    if (Object.keys(errors).length) { showErrors(passwordForm, errors); return; }
    showErrors(passwordForm, {});
    setBusy(button, true);
    try {
      await api.put("/api/auth/password", { current_password: current, new_password: next });
      passwordForm.reset();
      toast("Password changed. Other devices have been signed out.");
    } catch (error) {
      const fields = error instanceof ApiError ? { ...error.fields } : {};
      delete fields._;
      showErrors(passwordForm, fields, Object.keys(fields).length ? "" : error.message);
    } finally {
      setBusy(button, false);
    }
  });

  const recoveryForm = view.querySelector("#recovery-form");
  bindPasswordToggles(recoveryForm);
  recoveryForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = recoveryForm.querySelector('[type="submit"]');
    if (button.disabled) return;
    const password = recoveryForm.elements.password.value;
    if (!password) { showErrors(recoveryForm, { password: "Enter your password" }); return; }
    showErrors(recoveryForm, {});
    setBusy(button, true, "Creating…");
    try {
      const { recovery_code: code } = await api.post("/api/auth/recovery-code", { password });
      state.user = { ...state.user, has_recovery_code: true };
      const area = view.querySelector("#recovery-area");
      await recoveryCodePanel(area, code, { title: "Your new recovery code", intro: "Your previous code no longer works.", button: "Done", headingTag: "h3" });
      area.innerHTML = html`<p class="muted" tabindex="-1">Recovery code saved. Making a new one stops the old one from working.</p>`.value;
      area.firstElementChild.focus();
    } catch (error) {
      const fields = error instanceof ApiError ? { ...error.fields } : {};
      delete fields._;
      showErrors(recoveryForm, fields, Object.keys(fields).length ? "" : error.message);
      setBusy(button, false);
    }
  });

  // Leaving without saving drops any theme preview.
  return () => applyTheme(state.settings.theme);
}
