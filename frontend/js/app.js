// Hash router, sign-in gate and app shell behaviour.
import { api } from "./api.js";
import { clearUserData, dataChanged, loadMeta, loadUserData, onDataChanged, state } from "./state.js";
import { errorState, hideTooltip, hydrateIcons, plural, toast } from "./ui.js";
import { renderAuth } from "./pages/auth.js";
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
const AUTH_ROUTES = new Set(["login", "signup", "forgot"]);

const app = document.getElementById("app");
const authRoot = document.getElementById("auth-root");
const view = document.getElementById("view");
let cleanup = null;
let renderToken = 0;
let returnTo = null;
let authNotice = null;

function parseHash() {
  const [path, query = ""] = location.hash.replace(/^#\/?/, "").split("?");
  const name = ROUTES[path] || AUTH_ROUTES.has(path) ? path : "overview";
  return { name, params: Object.fromEntries(new URLSearchParams(query)) };
}

function stopPage() {
  hideTooltip();
  cleanup?.();
  cleanup = null;
}

async function render() {
  const { name, params } = parseHash();
  if (!state.user) {
    showAuth(name);
    return;
  }
  if (AUTH_ROUTES.has(name)) {
    location.replace("#/overview");
    return;
  }
  authRoot.hidden = true;
  authRoot.innerHTML = "";
  app.hidden = false;
  const token = ++renderToken;
  stopPage();
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

// ---------- sign-in gate ----------
function showAuth(name) {
  stopPage();
  renderToken++;
  if (!AUTH_ROUTES.has(name)) {
    // Remember where the visitor was going, then show the login page at #/login.
    if (location.hash && location.hash !== "#/") returnTo = location.hash;
    history.replaceState(null, "", "#/login");
    name = "login";
  }
  app.hidden = true;
  view.innerHTML = "";
  authRoot.hidden = false;
  renderAuth(authRoot, name, { notice: authNotice, onAuthenticated });
  authNotice = null;
  window.scrollTo(0, 0);
}

async function onAuthenticated(user, isNew, wasReset) {
  state.user = user;
  await loadUserData();
  showUser();
  toast(isNew ? `Welcome, ${user.display_name}! Your account is ready.`
    : wasReset ? "Password reset. Your other devices have been signed out." : `Welcome back, ${user.display_name}.`);
  const target = returnTo && !AUTH_ROUTES.has(returnTo.replace(/^#\/?/, "").split("?")[0]) ? returnTo : "#/overview";
  returnTo = null;
  if (location.hash === target) render();
  else location.hash = target;
  refreshAlerts();
}

function showUser() {
  const user = state.user;
  document.getElementById("user-name").textContent = user.display_name;
  document.getElementById("user-email").textContent = user.email;
  document.getElementById("user-initial").textContent = user.display_name.trim().charAt(0).toUpperCase();
}

async function logout() {
  try { await api.post("/api/auth/logout"); } catch { /* the session is dropped locally either way */ }
  clearUserData();
  document.getElementById("alert-badge").hidden = true;
  returnTo = null;
  toast("You've been logged out.", "info");
  if (location.hash === "#/login") render();
  else location.hash = "#/login";
}
document.getElementById("logout-btn").addEventListener("click", logout);
window.addEventListener("fet:logout", logout);

window.addEventListener("fet:unauthorized", () => {
  if (!state.user) return;
  clearUserData();
  document.getElementById("alert-badge").hidden = true;
  authNotice = "Your session has ended. Please log in again.";
  returnTo = location.hash;
  render();
});

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
  if (!state.user) return;
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
  const key = `${state.user.id}:${data.today}:${data.counts.expired}-${data.counts.today}-${data.counts.soon}`;
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
    const before = state.meta?.today;
    await loadMeta();
    if (before && state.meta.today !== before && state.user) dataChanged();
  } catch { /* keep the last known values */ }
}

// ---------- boot ----------
async function boot() {
  hydrateIcons();
  let collapsed = false;
  try { collapsed = localStorage.getItem("fet-sidebar") === "collapsed"; } catch { /* storage unavailable */ }
  setCollapsed(collapsed);
  try {
    await loadMeta();
    try {
      state.user = await api.get("/api/auth/me");
      await loadUserData();
      showUser();
    } catch (error) {
      if (error.status !== 401) throw error;
      state.user = null;
    }
  } catch (error) {
    authRoot.hidden = false;
    authRoot.innerHTML = `<main class="auth-shell">${errorState(error, "boot-retry").value}</main>`;
    authRoot.querySelector("#boot-retry").addEventListener("click", () => location.reload());
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
