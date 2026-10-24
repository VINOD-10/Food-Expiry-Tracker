// App-wide state: settings and reference data from the backend, plus a
// change event so every view refreshes after inventory or alert mutations.
import { api } from "./api.js";
import { setDateFormat } from "./ui.js";

export const state = {
  user: null,
  settings: null,
  meta: null,
};

const bus = new EventTarget();
export const onDataChanged = (handler) => {
  bus.addEventListener("data-changed", handler);
  return () => bus.removeEventListener("data-changed", handler);
};
export const dataChanged = () => bus.dispatchEvent(new Event("data-changed"));

export const SORT_FROM_SETTING = { "Expiry date": "expiry", Newest: "newest", Name: "name" };

export async function loadMeta() {
  state.meta = await api.get("/api/meta");
}

/** Loads the signed-in user's settings. */
export async function loadUserData() {
  applySettings(await api.get("/api/settings"));
}

export function clearUserData() {
  state.user = null;
  state.settings = null;
  try { localStorage.removeItem("fet-notified"); } catch { /* storage unavailable */ }
}

export function applySettings(settings) {
  state.settings = settings;
  setDateFormat(settings.date_format);
  applyTheme(settings.theme);
}

export function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === "light" || theme === "dark") root.dataset.theme = theme;
  else delete root.dataset.theme;
  try { localStorage.setItem("fet-theme", theme); } catch { /* storage unavailable */ }
}

/** The app's "today" comes from the server so the client never disagrees about status. */
export function today() {
  return state.meta?.today || new Date().toISOString().slice(0, 10);
}
