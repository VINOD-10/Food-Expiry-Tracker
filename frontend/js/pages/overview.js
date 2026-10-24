// Overview: a read-only summary. Inventory changes happen on the Inventory page.
import { api } from "../api.js";
import { onDataChanged } from "../state.js";
import { bindTooltips, emptyState, errorState, formatDate, formatDays, formatQty, formatTimestamp, html, icon, pageHead, plural, statusBadge } from "../ui.js";

const DIST = [
  ["expired", "Expired"], ["today", "Expires today"], ["soon", "Expiring soon"], ["safe", "Safe"], ["unknown", "Unknown date"],
];
const TIPS = [
  "Keep the oldest items at the front of the fridge so they get used first.",
  "Plan two or three meals around anything that expires in the next few days.",
  "Freeze bread, cooked rice and ripe fruit before their date to make them last.",
  "Check the list before shopping. The Shopping List page helps you avoid buying duplicates.",
  "\"Best before\" is about quality; \"use by\" is about safety. Never eat \"use by\" food after its date.",
];

function greeting() {
  const hour = new Date().getHours();
  return hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
}

function banner(data) {
  const { expired, today, soon } = data.counts;
  if (!expired && !today && !soon) {
    return data.counts.total
      ? html`<div class="banner banner-ok">${icon("check-circle")}<div class="banner-text"><strong>All clear.</strong> Nothing expires in the next ${plural(data.threshold, "day")}.</div></div>`
      : "";
  }
  const parts = [];
  if (expired) parts.push(`${plural(expired, "item")} expired`);
  if (today) parts.push(`${today} expiring today`);
  if (soon) parts.push(`${soon} expiring within ${plural(data.threshold, "day")}`);
  const tone = expired || today ? "banner-danger" : "banner-warn";
  return html`<div class="banner ${tone}" role="alert">${icon("alert")}
    <div class="banner-text"><strong>Needs attention:</strong> ${parts.join(" · ")}.</div>
    <a class="btn" href="#/alerts">Review alerts ${icon("arrow-right", "sm")}</a></div>`;
}

function stat(tone, label, value, sub, href, iconName) {
  return html`<a class="card stat tone-${tone}" href="${href}">
    <div class="stat-top"><span class="stat-label">${label}</span><span class="stat-icon">${icon(iconName)}</span></div>
    <span class="stat-value">${value}</span><span class="stat-sub">${sub}</span></a>`;
}

function itemRow(item) {
  return html`<li>
    <span class="cat-dot" aria-hidden="true">${item.category.slice(0, 1)}</span>
    <div class="grow"><div class="item-name">${item.food_name}</div>
      <div class="item-sub">${item.category} · ${formatQty(item.quantity, item.unit)} · Exp. ${formatDate(item.expiry_date)}</div></div>
    <div class="trail">${statusBadge(item.status, item.status_label)}<span class="small muted days">${formatDays(item.days_remaining)}</span></div>
  </li>`;
}

function distribution(counts) {
  const total = counts.total;
  if (!total) return emptyState({ iconName: "chart", title: "No data yet", text: "Add food to see how your inventory is spread across expiry statuses.", compact: true });
  const rows = DIST.filter(([key]) => counts[key] > 0);
  return html`
    <div class="dist-bar" role="img" aria-label="${rows.map(([key, label]) => `${label}: ${counts[key]}`).join(", ")}">
      ${rows.map(([key, label]) => html`<span class="fill-${key}" style="flex:${counts[key]}" tabindex="0"
        data-tip="${label}: ${plural(counts[key], "item")} (${Math.round((counts[key] / total) * 100)}%)"></span>`)}
    </div>
    <ul class="legend">${DIST.filter(([key]) => key !== "unknown" || counts.unknown).map(([key, label]) =>
      html`<li><span class="swatch fill-${key}"></span>${label}<span class="val">${counts[key]}</span></li>`)}</ul>
    <details class="table-view"><summary>View as table</summary>
      <table><thead><tr><th>Status</th><th>Items</th></tr></thead>
      <tbody>${rows.map(([key, label]) => html`<tr><td>${label}</td><td>${counts[key]}</td></tr>`)}</tbody></table></details>`;
}

function template(data) {
  const c = data.counts;
  return html`
    ${pageHead({
      eyebrow: greeting(), title: "Your kitchen at a glance",
      subtitle: `Today is ${formatDate(data.today)}. Here is what needs your attention.`,
      actions: html`<a class="btn btn-secondary" href="#/shopping">${icon("cart")}Shopping list</a>
        <a class="btn btn-primary" href="#/add">${icon("plus")}Add food</a>`,
    })}
    ${banner(data)}
    <section class="stats" aria-label="Inventory summary">
      ${stat("total", "Total items", c.total, "Tracked in your inventory", "#/inventory", "box")}
      ${stat("safe", "Safe", c.safe, `More than ${plural(data.threshold, "day")} left`, "#/inventory?status=safe", "shield")}
      ${stat("soon", "Expiring soon", c.expiring, c.today ? `${c.today} of them today` : `Within ${plural(data.threshold, "day")}`, "#/alerts", "hourglass")}
      ${stat("expired", "Expired", c.expired, "Past the printed date", "#/inventory?status=expired", "x-circle")}
    </section>
    <div class="grid grid-3-2">
      <section class="card" aria-labelledby="attention-title">
        <div class="card-head"><div><h2 id="attention-title">Needs attention</h2><p>Expired and soon-to-expire food, most urgent first</p></div>
          ${data.attention_total ? html`<a class="btn btn-ghost" href="#/alerts">View all ${data.attention_total} ${icon("arrow-right", "sm")}</a>` : ""}</div>
        <div class="card-body">${data.attention.length
          ? html`<ul class="item-list">${data.attention.map(itemRow)}</ul>`
          : emptyState({ iconName: "check-circle", title: "Nothing urgent", text: c.total ? "No food is expired or close to expiring." : "Once you add food, anything close to its expiry date shows up here.", compact: true })}</div>
      </section>
      <section class="card" aria-labelledby="dist-title">
        <div class="card-head"><div><h2 id="dist-title">Expiry distribution</h2><p>${plural(c.total, "item")} by status</p></div></div>
        <div class="card-body">${distribution(c)}</div>
      </section>
      <section class="card" aria-labelledby="recent-title">
        <div class="card-head"><div><h2 id="recent-title">Recently added</h2><p>The latest food added to your inventory</p></div>
          ${c.total ? html`<a class="btn btn-ghost" href="#/inventory?sort=newest">Open inventory ${icon("arrow-right", "sm")}</a>` : ""}</div>
        <div class="card-body">${data.recent.length
          ? html`<ul class="item-list">${data.recent.map((item) => html`<li>
              <span class="cat-dot" aria-hidden="true">${item.category.slice(0, 1)}</span>
              <div class="grow"><div class="item-name">${item.food_name}</div>
                <div class="item-sub">${item.category}${item.created_at ? ` · Added ${formatTimestamp(item.created_at)}` : ""}</div></div>
              <div class="trail">${statusBadge(item.status, item.status_label)}</div></li>`)}</ul>`
          : emptyState({ iconName: "box", title: "Your inventory is empty", text: "Add your first food item to start tracking expiry dates.",
              action: html`<a class="btn btn-primary" href="#/add">${icon("plus")}Add food</a>`, compact: true })}</div>
      </section>
      <section class="card" aria-labelledby="tips-title">
        <div class="card-head"><div><h2 id="tips-title">Waste less food</h2><p>Small habits that make a difference</p></div></div>
        <div class="card-body"><ul class="tips">${TIPS.map((tip) => html`<li>${icon("bulb")}<span>${tip}</span></li>`)}</ul>
          <div class="note">${icon("info")}<span>Statuses come from the printed date only. They can't tell you whether food is safe, so check how it looks and smells and how it was stored.</span></div></div>
      </section>
    </div>`;
}

const skeleton = html`<div class="stats">${[0, 1, 2, 3].map(() => html`<div class="skeleton sk-block"></div>`)}</div>
  <div class="grid grid-3-2"><div class="skeleton sk-block" style="height:280px"></div><div class="skeleton sk-block" style="height:280px"></div></div>`;

export async function render(view) {
  let alive = true;
  async function load(initial) {
    if (initial) view.innerHTML = html`${pageHead({ eyebrow: greeting(), title: "Your kitchen at a glance" })}<div aria-busy="true">${skeleton}</div>`.value;
    try {
      const data = await api.get("/api/dashboard");
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
