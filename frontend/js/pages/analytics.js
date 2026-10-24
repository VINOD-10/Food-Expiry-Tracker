// Analytics: charts drawn only from data the backend actually stores.
import { api } from "../api.js";
import { onDataChanged } from "../state.js";
import { bindTooltips, emptyState, errorState, formatMonth, formatTimestamp, html, icon, pageHead, plural } from "../ui.js";

const STATUS_ROWS = [["safe", "Safe"], ["soon", "Expiring soon"], ["today", "Expires today"], ["expired", "Expired"], ["unknown", "Unknown date"]];

function tableView(headers, rows) {
  return html`<details class="table-view"><summary>View as table</summary><table>
    <thead><tr>${headers.map((h) => html`<th>${h}</th>`)}</tr></thead>
    <tbody>${rows.map((r) => html`<tr>${r.map((c) => html`<td>${c}</td>`)}</tr>`)}</tbody></table></details>`;
}

/** Horizontal bars: one value per row, value at the tip. */
function hbars(rows, total) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return html`<ul class="hbars">${rows.map((r) => html`<li class="hbar">
    <span class="name">${r.swatch ? html`<span class="swatch ${r.swatch}" style="width:10px;height:10px;border-radius:3px;display:inline-block"></span>` : ""}${r.label}</span>
    <span class="track"><span class="bar ${r.fill}" style="width:${(r.value / max) * 100}%" tabindex="0"
      data-tip="${r.label}: ${plural(r.value, "item")}${total ? ` (${Math.round((r.value / total) * 100)}%)` : ""}"></span></span>
    <span class="value">${r.value}</span></li>`)}</ul>`;
}

/** Columns over time for a single series. */
function columns(points, noun) {
  const max = Math.max(1, ...points.map((p) => p.value));
  return html`<div class="columns" role="img" aria-label="${points.map((p) => `${formatMonth(p.month)}: ${p.value}`).join(", ")}">
    ${points.map((p) => html`<div class="col">${p.value ? html`<span class="cap">${p.value}</span>` : ""}
      <span class="bar fill-primary" style="height:${(p.value / max) * 100}%" tabindex="0" data-tip="${formatMonth(p.month)}: ${plural(p.value, noun)}"></span></div>`)}
  </div><div class="col-labels" aria-hidden="true">${points.map((p) => html`<span>${formatMonth(p.month)}</span>`)}</div>`;
}

function stat(tone, label, value, sub, iconName) {
  return html`<div class="card stat tone-${tone}"><div class="stat-top"><span class="stat-label">${label}</span><span class="stat-icon">${icon(iconName)}</span></div>
    <span class="stat-value">${value}</span><span class="stat-sub">${sub}</span></div>`;
}

function template(d) {
  const s = d.status;
  const r = d.removals;
  const statusRows = STATUS_ROWS.filter(([key]) => key !== "unknown" || s.unknown)
    .map(([key, label]) => ({ label, value: s[key], fill: `fill-${key}`, swatch: `fill-${key}` }));
  const categoryRows = d.categories.map((c) => ({ label: c.category, value: c.count, fill: "fill-primary" }));
  const additions = d.monthly_additions.map((m) => ({ month: m.month, value: m.count }));
  const decided = r.consumed + r.discarded;
  const removalMonths = r.monthly.map((m) => ({ month: m.month, value: m.discarded }));

  return html`
    ${pageHead({ eyebrow: "Analytics", title: "Insights", subtitle: "A summary of your inventory and how food leaves it, based only on recorded data." })}
    <section class="stats" aria-label="Key figures">
      ${stat("total", "Items tracked", d.total, "Currently in inventory", "box")}
      ${stat("safe", "Safe", s.safe, `More than ${plural(d.threshold, "day")} left`, "shield")}
      ${stat("soon", "Expiring soon", s.soon + s.today, `${s.today} today`, "hourglass")}
      ${stat("expired", "Expired", s.expired, "Still in inventory", "x-circle")}
    </section>
    <div class="grid grid-2">
      <section class="card" aria-labelledby="a-status">
        <div class="card-head"><div><h2 id="a-status">Expiry status breakdown</h2><p>Current inventory by status</p></div></div>
        <div class="card-body">${d.total ? html`${hbars(statusRows, d.total)}${tableView(["Status", "Items"], statusRows.map((x) => [x.label, x.value]))}`
          : emptyState({ iconName: "chart", title: "No items yet", text: "Add food to see the breakdown.", compact: true })}</div>
      </section>
      <section class="card" aria-labelledby="a-cat">
        <div class="card-head"><div><h2 id="a-cat">Items by category</h2><p>Number of items in each category</p></div></div>
        <div class="card-body">${categoryRows.length ? html`${hbars(categoryRows, d.total)}${tableView(["Category", "Items"], categoryRows.map((x) => [x.label, x.value]))}`
          : emptyState({ iconName: "chart", title: "No categories yet", text: "Categories appear once you add food.", compact: true })}</div>
      </section>
      <section class="card" aria-labelledby="a-month">
        <div class="card-head"><div><h2 id="a-month">Food added per month</h2><p>Items added in the last 6 months that are still in inventory</p></div></div>
        <div class="card-body">${columns(additions, "item")}
          ${tableView(["Month", "Items added"], additions.map((p) => [formatMonth(p.month), p.value]))}
          ${d.untracked_additions ? html`<div class="note">${icon("info")}<span>${plural(d.untracked_additions, "older item")} from before date tracking began ${d.untracked_additions === 1 ? "has" : "have"} no "date added", so ${d.untracked_additions === 1 ? "it isn't" : "they aren't"} counted here.</span></div>` : ""}
          <div class="note">${icon("info")}<span>Deleted items no longer count towards their month.</span></div></div>
      </section>
      <section class="card" aria-labelledby="a-waste">
        <div class="card-head"><div><h2 id="a-waste">Waste insights</h2><p>Why items were removed from your inventory</p></div></div>
        <div class="card-body">${r.total ? html`
          ${hbars([
            { label: "Used or eaten", value: r.consumed, fill: "fill-safe", swatch: "fill-safe" },
            { label: "Thrown away", value: r.discarded, fill: "fill-expired", swatch: "fill-expired" },
            { label: "Other", value: r.other, fill: "fill-unknown", swatch: "fill-unknown" },
          ], r.total)}
          <p class="small" style="margin-top:16px">${decided
            ? `${Math.round((r.discarded / decided) * 100)}% of removed food with a known outcome was thrown away. ${plural(r.expired_at_removal, "item")} had already expired when removed.`
            : "No removals have been marked as used or thrown away yet."}</p>
          <h3 style="margin-top:20px">Food thrown away per month</h3>
          <div style="margin-top:8px">${columns(removalMonths, "item thrown away")}</div>
          ${tableView(["Month", "Used", "Thrown away", "Other", "Expired at removal"], r.monthly.map((m) => [formatMonth(m.month), m.consumed, m.discarded, m.other, m.expired]))}`
          : emptyState({ iconName: "leaf", title: "No removals recorded yet", text: "When you delete an item from the inventory, you can say whether it was used or thrown away. Those answers build this chart.", compact: true })}
          <div class="note">${icon("info")}<span>Tracking started ${r.tracked_since ? formatTimestamp(r.tracked_since) : "recently"}. Items deleted before then, or from the desktop app, aren't included. Money saved isn't shown because prices aren't recorded.</span></div>
        </div>
      </section>
    </div>`;
}

export async function render(view) {
  let alive = true;
  async function load(initial) {
    if (initial) view.innerHTML = html`${pageHead({ eyebrow: "Analytics", title: "Insights" })}<div class="stats" aria-busy="true">${[0, 1, 2, 3].map(() => html`<div class="skeleton sk-block"></div>`)}</div>`.value;
    try {
      const data = await api.get("/api/analytics");
      if (!alive) return;
      view.innerHTML = template(data).value;
      bindTooltips(view);
    } catch (error) {
      if (!alive) return;
      view.innerHTML = errorState(error).value;
      view.querySelector("#retry").addEventListener("click", () => load(true));
    }
  }
  await load(true);
  const off = onDataChanged(() => load(false));
  return () => { alive = false; off(); };
}
