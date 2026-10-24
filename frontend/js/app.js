// Hash router and app shell behaviour.
import { api } from "./api.js";
import { dataChanged, loadBootData, onDataChanged, state } from "./state.js";
import { errorState, hideTooltip, hydrateIcons, plural } from "./ui.js";
import * as overview from "./pages/overview.js";
import * as inventory from "./pages/inventory.js";
import * as addFood from "./pages/add.js";
import * as alerts from "./pages/alerts.js";
import * as shopping from "./pages/shopping.js";
import * as analytics from "./pages/analytics.js";
import * as settings from "./pages/settings.js";

const ROUTES = {
  overview: { page: overview, title: "Overview" },
  inventory: { page: inventory, title: "Inventory" },
  add: { page: addFood, title: "Add Food" },
  alerts: { page: alerts, title: "Expiry Alerts" },
  shopping: { page: shopping, title: "Shopping List" },
  analytics: { page: analytics, title: "Analytics" },
  settings: { page: settings, title: "Settings" },
};

const app = document.getElementById("app");
const view = document.getElementById("view");
let cleanup = null;
let renderToken = 0;

function parseHash() {
  const [path, query = ""] = location.hash.replace(/^#\/?/, "").split("?");
  const name = ROUTES[path] ? path : "overview";
  return { name, params: Object.fromEntries(new URLSearchParams(query)) };
}

async function render() {
  const { name, params } = parseHash();
  const token = ++renderToken;
  hideTooltip();
  cleanup?.();
  cleanup = null;
  closeMenu();
  document.querySelectorAll("#nav a").forEach((link) => {
    if (link.dataset.route === name) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  document.title = `${ROUTES[name].title} · Food Expiry Tracker`;
  view.innerHTML = "";
  const result = await ROUTES[name].page.render(view, params);
  if (token !== renderToken) { result?.(); return; }
  cleanup = result || null;
  view.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}

// ---------- navigation chrome ----------
const menuButton = document.getElementById("menu-btn");
function closeMenu() {
  app.classList.remove("menu-open");
  menuButton.setAttribute("aria-expanded", "false");
}
menuButton.addEventListener("click", () => {
  const open = !app.classList.contains("menu-open");
  app.classList.toggle("menu-open", open);
  menuButton.setAttribute("aria-expanded", String(open));
  if (open) document.querySelector("#nav a[aria-current]")?.focus();
});
document.getElementById("backdrop").addEventListener("click", closeMenu);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && app.classList.contains("menu-open")) { closeMenu(); menuButton.focus(); }
});

const collapseButton = document.getElementById("collapse-btn");
function setCollapsed(collapsed) {
  app.classList.toggle("collapsed", collapsed);
  collapseButton.setAttribute("aria-expanded", String(!collapsed));
  collapseButton.querySelector(".label").textContent = collapsed ? "Expand sidebar" : "Collapse sidebar";
  collapseButton.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
  document.querySelectorAll("#nav a").forEach((link) => {
    if (collapsed) link.setAttribute("title", link.querySelector(".label").textContent);
    else link.removeAttribute("title");
  });
  try { localStorage.setItem("fet-sidebar", collapsed ? "collapsed" : "expanded"); } catch { /* storage unavailable */ }
}
collapseButton.addEventListener("click", () => setCollapsed(!app.classList.contains("collapsed")));

// ---------- alert badge + optional browser notifications ----------
async function refreshAlerts() {
  let data;
  try { data = await api.get("/api/alerts"); } catch { return; }
  const badge = document.getElementById("alert-badge");
  badge.hidden = data.active === 0;
  badge.textContent = data.active > 99 ? "99+" : String(data.active);
  badge.setAttribute("aria-label", `${plural(data.active, "active alert")}`);
  maybeNotify(data);
}

/** One summary notification per day while the app is open, only with explicit opt-in and permission. */
function maybeNotify(data) {
  if (!state.settings?.browser_notifications || !("Notification" in window) || Notification.permission !== "granted") return;
  if (!data.active) return;
  const key = `${data.today}:${data.counts.expired}-${data.counts.today}-${data.counts.soon}`;
  try {
    if (localStorage.getItem("fet-notified") === key) return;
    localStorage.setItem("fet-notified", key);
  } catch { return; }
  const parts = [];
  if (data.counts.expired) parts.push(`${data.counts.expired} expired`);
  if (data.counts.today) parts.push(`${data.counts.today} expiring today`);
  if (data.counts.soon) parts.push(`${data.counts.soon} expiring soon`);
  const notification = new Notification("Food Expiry Tracker", { body: `${parts.join(", ")}. Open the alerts page to review.`, tag: "fet-alerts" });
  notification.onclick = () => { window.focus(); location.hash = "#/alerts"; };
}

async function refreshMeta() {
  try {
    const meta = await api.get("/api/meta");
    const dayChanged = state.meta && meta.today !== state.meta.today;
    state.meta = meta;
    if (dayChanged) dataChanged();
  } catch { /* keep the last known values */ }
}

// ---------- boot ----------
async function boot() {
  hydrateIcons();
  let collapsed = false;
  try { collapsed = localStorage.getItem("fet-sidebar") === "collapsed"; } catch { /* storage unavailable */ }
  setCollapsed(collapsed);
  try {
    await loadBootData();
  } catch (error) {
    view.innerHTML = errorState(error, "boot-retry").value;
    view.querySelector("#boot-retry").addEventListener("click", () => location.reload());
    return;
  }
  window.addEventListener("hashchange", render);
  onDataChanged(refreshAlerts);
  await render();
  refreshAlerts();
  // Status depends on the calendar date, so re-check when the tab returns and periodically.
  document.addEventListener("visibilitychange", () => { if (!document.hidden) { refreshMeta(); refreshAlerts(); } });
  setInterval(refreshMeta, 10 * 60 * 1000);
}

boot();
