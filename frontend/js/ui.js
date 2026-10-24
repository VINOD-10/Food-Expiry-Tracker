// Rendering helpers shared by every page: escaping, icons, formatting,
// status badges, dialogs, toasts and chart tooltips.

// ---------- safe HTML ----------
class Raw { constructor(value) { this.value = value; } toString() { return this.value; } }
export const raw = (value) => new Raw(String(value));

export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
}

function interpolate(value) {
  if (value instanceof Raw) return value.value;
  if (Array.isArray(value)) return value.map(interpolate).join("");
  if (value === false || value === null || value === undefined) return "";
  return esc(value);
}

/** Tagged template: every interpolation is escaped unless wrapped in raw() or produced by html``. */
export function html(strings, ...values) {
  return raw(strings.reduce((out, part, i) => out + part + (i < values.length ? interpolate(values[i]) : ""), ""));
}

// ---------- icons ----------
const ICONS = {
  home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/>',
  box: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
  "plus-circle": '<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
  cart: '<circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2 2h3l2.7 12.4a2 2 0 0 0 2 1.6h8.7a2 2 0 0 0 2-1.6L22 7H6"/>',
  chart: '<path d="M3 3v18h18"/><path d="M8 17v-5M13 17V8M18 17v-9"/>',
  settings: '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v6M14 11v6"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  alert: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  leaf: '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10Z"/><path d="M2 21c0-3 1.9-5.4 5.1-6"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  "chevrons-left": '<path d="m11 17-5-5 5-5M18 17l-5-5 5-5"/>',
  "chevron-left": '<path d="m15 18-6-6 6-6"/>',
  "chevron-right": '<path d="m9 18 6-6-6-6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  "check-circle": '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/>',
  "arrow-right": '<path d="M5 12h14M13 6l6 6-6 6"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
  "x-circle": '<circle cx="12" cy="12" r="9"/><path d="m15 9-6 6M9 9l6 6"/>',
  hourglass: '<path d="M6 2h12M6 22h12M7 2v4a5 5 0 0 0 10 0V2M7 22v-4a5 5 0 0 1 10 0v4"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01"/>',
  bulb: '<path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.3h6c0-1 .4-1.8 1-2.3A7 7 0 0 0 12 2z"/>',
  wifi: '<path d="M5 13a10 10 0 0 1 14 0M8.5 16.5a5 5 0 0 1 7 0M2 9.5a15 15 0 0 1 20 0M12 20h.01"/>',
};

export function icon(name, cls = "") {
  return raw(`<svg class="icon ${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONS[name] || ""}</svg>`);
}

export function hydrateIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((el) => {
    el.outerHTML = icon(el.dataset.icon).value;
  });
}

// ---------- formatting ----------
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
let dateFormat = "%d-%m-%Y";
export function setDateFormat(format) { dateFormat = format || dateFormat; }

/** Format an ISO calendar date (YYYY-MM-DD) without timezone shifts. */
export function formatDate(iso, format = dateFormat) {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-");
  if (!d) return "—";
  return format.replace("%d", d).replace("%m", m).replace("%Y", y).replace("%b", MONTHS[Number(m) - 1]);
}

export function formatTimestamp(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  const local = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  return formatDate(local);
}

export function formatMonth(key) {
  const [y, m] = key.split("-");
  return `${MONTHS[Number(m) - 1]} ${y.slice(2)}`;
}

export function formatDays(days) {
  if (days === null || days === undefined) return "No valid date";
  if (days < 0) { const n = -days; return `Expired ${n} day${n === 1 ? "" : "s"} ago`; }
  if (days === 0) return "Expires today";
  return `${days} day${days === 1 ? "" : "s"} left`;
}

export function formatQty(quantity, unit) {
  if (quantity === null || quantity === undefined) return "—";
  const n = Number.isInteger(quantity) ? quantity : Number(quantity.toFixed(2));
  return `${n} ${unit || ""}`.trim();
}

export function plural(n, word) { return `${n} ${word}${n === 1 ? "" : "s"}`; }

// ---------- status ----------
export const STATUS = {
  safe: { label: "Safe", icon: "shield" },
  soon: { label: "Expiring soon", icon: "hourglass" },
  today: { label: "Expires today", icon: "clock" },
  expired: { label: "Expired", icon: "x-circle" },
  unknown: { label: "Unknown date", icon: "help" },
};

export function statusBadge(status, label) {
  const meta = STATUS[status] || STATUS.unknown;
  return html`<span class="badge status-${status}">${icon(meta.icon)}${label || meta.label}</span>`;
}

// ---------- page helpers ----------
export function pageHead({ eyebrow, title, subtitle, actions = "" }) {
  return html`<header class="page-head">
    <div>${eyebrow ? html`<div class="eyebrow">${eyebrow}</div>` : ""}<h1>${title}</h1>${subtitle ? html`<p>${subtitle}</p>` : ""}</div>
    ${actions ? html`<div class="page-actions">${actions}</div>` : ""}
  </header>`;
}

export function emptyState({ iconName = "box", title, text, action = "" , compact = false }) {
  return html`<div class="empty ${compact ? "compact" : ""}">
    <div class="empty-icon">${icon(iconName, "lg")}</div>
    <h3>${title}</h3>${text ? html`<p>${text}</p>` : ""}${action}
  </div>`;
}

export function errorState(error, retryId = "retry") {
  return html`<div class="load-error card">
    ${emptyState({ iconName: error?.network ? "wifi" : "alert", title: "Couldn't load this page", text: error?.message || "Something went wrong.",
      action: html`<button class="btn btn-secondary" type="button" id="${retryId}">${icon("refresh")}Try again</button>` })}
  </div>`;
}

export function skeletonRows(count = 5) {
  return html`<div class="card-pad" aria-hidden="true">${Array.from({ length: count }, (_, i) =>
    html`<div class="skeleton sk-line" style="width:${[92, 78, 85, 70, 88][i % 5]}%"></div>`)}</div>`;
}

export function setBusy(button, busy, busyLabel) {
  if (!button) return;
  if (busy) {
    button.dataset.label = button.innerHTML;
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    button.innerHTML = `<span class="spinner" aria-hidden="true"></span>${esc(busyLabel || "Saving…")}`;
  } else {
    button.disabled = false;
    button.removeAttribute("aria-busy");
    if (button.dataset.label) button.innerHTML = button.dataset.label;
  }
}

// ---------- toasts ----------
export function toast(message, type = "success", timeout = 4500) {
  const region = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.setAttribute("role", type === "error" ? "alert" : "status");
  el.innerHTML = html`${icon(type === "error" ? "alert" : type === "info" ? "info" : "check-circle")}
    <div class="msg">${message}</div>
    <button class="close" type="button" aria-label="Dismiss notification">${icon("x", "sm")}</button>`.value;
  const remove = () => el.remove();
  el.querySelector(".close").addEventListener("click", remove);
  region.append(el);
  if (timeout) setTimeout(remove, type === "error" ? timeout * 1.6 : timeout);
}

// ---------- dialogs ----------
/** Opens a modal dialog. Returns { dialog, body, close }. Focus returns to the opener on close. */
export function openDialog({ title, subtitle = "", content, wide = false, onClose }) {
  const opener = document.activeElement;
  const dialog = document.createElement("dialog");
  dialog.className = `modal ${wide ? "wide" : ""}`;
  const titleId = `dlg-${Math.random().toString(36).slice(2, 8)}`;
  dialog.setAttribute("aria-labelledby", titleId);
  dialog.innerHTML = html`<div class="modal-head">
      <div><h2 id="${titleId}">${title}</h2>${subtitle ? html`<p>${subtitle}</p>` : ""}</div>
      <button class="btn btn-ghost btn-icon" type="button" data-close aria-label="Close dialog">${icon("x")}</button>
    </div>
    <div class="modal-body">${content}</div>`.value;
  document.body.append(dialog);
  const close = () => dialog.open && dialog.close();
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog || event.target.closest("[data-close]")) close();
  });
  dialog.addEventListener("close", () => {
    dialog.remove();
    onClose?.();
    if (opener && document.contains(opener)) opener.focus();
  });
  dialog.showModal();
  const first = dialog.querySelector("[autofocus], .modal-body input, .modal-body select, .modal-body button");
  first?.focus();
  return { dialog, body: dialog.querySelector(".modal-body"), close };
}

/** Confirmation dialog; resolves to the submitted FormData, or null when cancelled. */
export function confirmDialog({ title, message, confirmLabel = "Confirm", danger = false, extra = "" }) {
  return new Promise((resolve) => {
    let result = null;
    const { body, close } = openDialog({
      title,
      content: html`<form method="dialog" novalidate>
        <p>${message}</p>${extra}
        <div class="form-actions">
          <button class="btn btn-secondary" type="button" data-close>Cancel</button>
          <button class="btn ${danger ? "btn-danger" : "btn-primary"}" type="submit" autofocus>${confirmLabel}</button>
        </div></form>`,
      onClose: () => resolve(result),
    });
    body.querySelector("form").addEventListener("submit", (event) => {
      event.preventDefault();
      result = new FormData(event.target);
      close();
    });
  });
}

// ---------- chart tooltips ----------
export function bindTooltips(root) {
  const tip = document.getElementById("tooltip");
  const show = (el) => {
    tip.textContent = el.dataset.tip;
    tip.hidden = false;
    const rect = el.getBoundingClientRect();
    const tipRect = tip.getBoundingClientRect();
    const left = Math.min(window.innerWidth - tipRect.width - 8, Math.max(8, rect.left + rect.width / 2 - tipRect.width / 2));
    const top = rect.top - tipRect.height - 8 < 8 ? rect.bottom + 8 : rect.top - tipRect.height - 8;
    tip.style.left = `${left}px`;
    tip.style.top = `${top}px`;
  };
  const hide = () => { tip.hidden = true; };
  root.querySelectorAll("[data-tip]").forEach((el) => {
    el.addEventListener("pointerenter", () => show(el));
    el.addEventListener("pointerleave", hide);
    el.addEventListener("focus", () => show(el));
    el.addEventListener("blur", hide);
  });
}

export function hideTooltip() {
  const tip = document.getElementById("tooltip");
  if (tip) tip.hidden = true;
}
