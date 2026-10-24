// Expiry Alerts: in-app alert centre with persistent dismissals.
import { api } from "../api.js";
import { applySettings, dataChanged, onDataChanged, state } from "../state.js";
import {
  emptyState, errorState, formatDate, formatDays, formatQty, formatTimestamp, html, icon, openDialog,
  pageHead, plural, setBusy, skeletonRows, statusBadge, toast,
} from "../ui.js";

const GROUPS = [
  ["expired", "Expired", "These are past their printed date. Check them before use, or throw them away."],
  ["today", "Expires today", "Use these today if they are still in good condition."],
  ["soon", "Expiring soon", "Plan to use these in the next few days."],
];

function card(item) {
  return html`<article class="card alert-card tone-${item.status} ${item.dismissed ? "is-dismissed" : ""}" data-id="${item.id}">
    <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start">
      <div style="min-width:0"><h3 class="item-name">${item.food_name}</h3>
        <p class="item-sub">${item.category} · ${formatQty(item.quantity, item.unit)}${item.storage_location ? ` · ${item.storage_location}` : ""}</p></div>
      ${statusBadge(item.status, item.status_label)}
    </div>
    <div class="meta">
      <span class="chip">${icon("calendar", "sm")}Expiry ${formatDate(item.expiry_date)}</span>
      <span class="chip">${icon("clock", "sm")}${formatDays(item.days_remaining)}</span>
      ${item.dismissed ? html`<span class="chip">${icon("check-circle", "sm")}Dismissed</span>` : ""}
    </div>
    <div class="actions">
      <button class="btn btn-secondary" type="button" data-action="view">${icon("eye", "sm")}View</button>
      <a class="btn btn-secondary" href="#/inventory?item=${item.id}&search=${encodeURIComponent(item.food_name)}">${icon("box", "sm")}Open in inventory</a>
      ${item.dismissed
        ? html`<button class="btn btn-ghost" type="button" data-action="restore" aria-label="Restore alert for ${item.food_name}">${icon("undo", "sm")}Restore</button>`
        : html`<button class="btn btn-ghost" type="button" data-action="dismiss" aria-label="Dismiss alert for ${item.food_name}">${icon("check", "sm")}Dismiss</button>`}
    </div>
  </article>`;
}

function details(item) {
  const row = (label, value) => html`<dt>${label}</dt><dd>${value}</dd>`;
  return html`<dl class="detail-list">
    ${row("Status", statusBadge(item.status, item.status_label))}
    ${row("Days remaining", formatDays(item.days_remaining))}
    ${row("Expiry date", formatDate(item.expiry_date))}
    ${row("Manufacturing date", formatDate(item.mfg_date))}
    ${row("Category", item.category)}
    ${row("Quantity", formatQty(item.quantity, item.unit))}
    ${row("Storage", item.storage_location || "—")}
    ${row("Notes", item.notes || "—")}
    ${row("Added", formatTimestamp(item.created_at))}
  </dl>
  <div class="note">${icon("info")}<span>This status is based on the printed date only. Check how the food looks and smells and how it was stored before eating it.</span></div>
  <div class="form-actions"><button class="btn btn-secondary" type="button" data-close>Close</button>
    <a class="btn btn-primary" href="#/inventory?item=${item.id}&search=${encodeURIComponent(item.food_name)}" data-close>Open in inventory</a></div>`;
}

export async function render(view) {
  let alive = true;
  let showDismissed = false;
  let items = [];

  view.innerHTML = html`
    ${pageHead({ eyebrow: "Expiry alerts", title: "Alert centre", subtitle: "Expired food and food expiring soon, most urgent first." })}
    <section class="card card-pad" style="margin-bottom:16px" aria-labelledby="threshold-title">
      <div style="display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;align-items:flex-end">
        <div><h2 id="threshold-title">Alert window</h2>
          <p class="muted small" style="margin-top:4px">Food expiring within this many days counts as "Expiring soon".</p></div>
        <form class="threshold-form" id="threshold-form" novalidate>
          <div class="field"><label for="threshold">Days before expiry</label>
            <input class="input" id="threshold" name="threshold" type="number" min="0" max="30" step="1" inputmode="numeric" required
              value="${state.settings.expiry_threshold}" aria-describedby="threshold-error"></div>
          <button class="btn btn-primary" type="submit">Update</button>
          <p class="error small" id="threshold-error" hidden style="width:100%;color:var(--expired-text)"></p>
        </form>
      </div>
    </section>
    <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px">
      <p id="summary" class="muted" aria-live="polite"></p>
      <label class="switch"><input type="checkbox" id="show-dismissed"><span>Show dismissed alerts</span></label>
    </div>
    <div id="alerts" aria-busy="true"><div class="card">${skeletonRows(4)}</div></div>`.value;

  const container = view.querySelector("#alerts");

  async function load() {
    try {
      const data = await api.get("/api/alerts", { include_dismissed: showDismissed });
      if (!alive) return;
      items = data.items;
      const { expired, today, soon } = data.counts;
      view.querySelector("#summary").textContent = data.active
        ? `${plural(data.active, "active alert")}: ${expired} expired, ${today} today, ${soon} soon${data.dismissed ? ` · ${data.dismissed} dismissed` : ""}`
        : `No active alerts${data.dismissed ? ` · ${data.dismissed} dismissed` : ""}`;
      container.innerHTML = (items.length
        ? html`${GROUPS.map(([status, title, hint]) => {
            const group = items.filter((item) => item.status === status);
            if (!group.length) return "";
            return html`<section class="alert-group" aria-labelledby="g-${status}">
              <div class="alert-group-head">${statusBadge(status, title)}<h2 id="g-${status}" class="sr-only">${title}</h2>
                <span class="muted small">${plural(group.length, "item")} · ${hint}</span></div>
              <div class="alert-cards">${group.map(card)}</div></section>`;
          })}`
        : html`<div class="card">${emptyState({ iconName: "check-circle", title: "You're all caught up",
            text: data.dismissed ? "All current alerts have been dismissed. Turn on \"Show dismissed alerts\" to review them."
              : `Nothing is expired or expiring within ${plural(data.threshold, "day")}.`,
            action: html`<a class="btn btn-secondary" href="#/inventory">View inventory</a>` })}</div>`).value;
    } catch (error) {
      if (!alive) return;
      container.innerHTML = errorState(error).value;
      container.querySelector("#retry").addEventListener("click", load);
    } finally {
      if (alive) container.setAttribute("aria-busy", "false");
    }
  }

  view.querySelector("#show-dismissed").addEventListener("change", (event) => { showDismissed = event.target.checked; load(); });

  container.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action]");
    const cardEl = button?.closest("[data-id]");
    if (!cardEl) return;
    const item = items.find((entry) => entry.id === Number(cardEl.dataset.id));
    if (!item) return;
    if (button.dataset.action === "view") {
      openDialog({ title: item.food_name, subtitle: "Food item details", content: details(item) });
      return;
    }
    const dismiss = button.dataset.action === "dismiss";
    setBusy(button, true, dismiss ? "Dismissing…" : "Restoring…");
    try {
      if (dismiss) await api.post(`/api/alerts/${item.id}/dismiss`);
      else await api.del(`/api/alerts/${item.id}/dismiss`);
      toast(dismiss ? `Dismissed the alert for ${item.food_name}.` : `Restored the alert for ${item.food_name}.`);
      dataChanged();
    } catch (error) {
      toast(error.message, "error");
      if (document.contains(button)) setBusy(button, false);
      if (error.status === 404 || error.status === 409) load();
    }
  });

  view.querySelector("#threshold-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = event.target.elements.threshold;
    const errorEl = view.querySelector("#threshold-error");
    const value = Number(input.value);
    if (input.value === "" || !Number.isInteger(value) || value < 0 || value > 30) {
      errorEl.textContent = "Enter a whole number from 0 to 30.";
      errorEl.hidden = false;
      input.setAttribute("aria-invalid", "true");
      input.focus();
      return;
    }
    errorEl.hidden = true;
    input.removeAttribute("aria-invalid");
    const button = event.target.querySelector("button");
    setBusy(button, true);
    try {
      applySettings(await api.put("/api/settings", { ...state.settings, expiry_threshold: value }));
      toast(`Alert window set to ${plural(value, "day")}.`);
      dataChanged();
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setBusy(button, false);
    }
  });

  await load();
  const off = onDataChanged(load);
  return () => { alive = false; off(); };
}
