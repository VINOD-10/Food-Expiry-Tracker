// Inventory: the only place where stored food is edited or deleted.
import { api, ApiError } from "../api.js";
import { bindFoodForm, foodFormHTML, options } from "../foodForm.js";
import { SORT_FROM_SETTING, dataChanged, onDataChanged, state } from "../state.js";
import {
  confirmDialog, emptyState, errorState, formatDate, formatDays, formatQty, formatTimestamp, html, icon,
  openDialog, pageHead, plural, skeletonRows, statusBadge, toast,
} from "../ui.js";

const PAGE_SIZE = 12;
const STATUS_OPTIONS = [
  ["", "All statuses"], ["expired", "Expired"], ["today", "Expires today"], ["soon", "Expiring soon"],
  ["attention", "Needs attention (all of the above)"], ["safe", "Safe"], ["unknown", "Unknown date"],
];
const SORT_OPTIONS = [["expiry", "Expiry date"], ["newest", "Newest added"], ["name", "Name (A–Z)"]];

function selectOptions(pairs, selected) {
  return pairs.map(([value, label]) => html`<option value="${value}" ${value === selected ? "selected" : ""}>${label}</option>`);
}

function row(item, highlight) {
  const cell = (label, content, cls = "") => html`<td class="${cls}"><span class="cell-label">${label}</span><span>${content}</span></td>`;
  return html`<tr data-id="${item.id}" class="${highlight ? "highlight" : ""}">
    <td class="cell-main"><div class="item-name">${item.food_name}</div>
      ${item.notes ? html`<div class="item-sub">${item.notes}</div>` : ""}
      <div class="item-sub show-compact">${item.category}</div></td>
    ${cell("Category", item.category, "hide-mobile hide-tablet")}
    ${cell("Quantity", formatQty(item.quantity, item.unit), "num")}
    ${cell("Mfg. date", formatDate(item.mfg_date), `hide-tablet optional ${item.mfg_date ? "" : "is-empty"}`)}
    ${cell("Expiry date", html`${formatDate(item.expiry_date)}<span class="item-sub only-tablet">${formatDays(item.days_remaining)}</span>`, "nowrap")}
    ${cell("Days left", html`<span class="days">${formatDays(item.days_remaining)}</span>`, "hide-tablet")}
    ${cell("Status", statusBadge(item.status, item.status_label))}
    ${cell("Storage", item.storage_location || "—", `hide-tablet optional ${item.storage_location ? "" : "is-empty"}`)}
    ${cell("Added", formatTimestamp(item.created_at), `hide-tablet optional ${item.created_at ? "" : "is-empty"}`)}
    <td class="cell-actions"><div class="row-actions">
      <button class="btn btn-secondary" type="button" data-action="edit" aria-label="Edit ${item.food_name}">${icon("edit", "sm")}<span class="show-mobile">Edit</span></button>
      <button class="btn btn-danger-ghost" type="button" data-action="delete" aria-label="Delete ${item.food_name}">${icon("trash", "sm")}<span class="show-mobile">Delete</span></button>
    </div></td>
  </tr>`;
}

function table(items, highlightId) {
  return html`<div class="table-scroll"><table class="data-table">
    <caption class="sr-only">Food inventory</caption>
    <thead><tr>
      <th scope="col">Food</th><th scope="col" class="hide-mobile hide-tablet">Category</th><th scope="col">Quantity</th>
      <th scope="col" class="hide-tablet">Mfg. date</th><th scope="col">Expiry date</th><th scope="col" class="hide-tablet">Days left</th>
      <th scope="col">Status</th><th scope="col" class="hide-tablet">Storage</th><th scope="col" class="hide-tablet">Added</th>
      <th scope="col"><span class="sr-only">Actions</span></th>
    </tr></thead>
    <tbody>${items.map((item) => row(item, item.id === highlightId))}</tbody></table></div>`;
}

export async function render(view, params) {
  const defaultSort = SORT_FROM_SETTING[state.settings.default_sort] || "expiry";
  const filters = {
    search: params.search || "",
    category: state.meta.categories.includes(params.category) ? params.category : "",
    status: STATUS_OPTIONS.some(([v]) => v && v === params.status) ? params.status : "",
    sort: SORT_OPTIONS.some(([v]) => v === params.sort) ? params.sort : defaultSort,
    page: 1,
  };
  let alive = true;
  let seq = 0;
  let items = [];
  let highlightId = params.item ? Number(params.item) : null;

  view.innerHTML = html`
    ${pageHead({ eyebrow: "Inventory", title: "Your food inventory", subtitle: "Edit, delete and review everything you are tracking.",
      actions: html`<a class="btn btn-primary" href="#/add">${icon("plus")}Add food</a>` })}
    <section class="card" aria-label="Inventory list">
      <form class="toolbar" role="search" id="filters">
        <div class="field search-field"><label for="f-search">Search by name</label>
          <div class="search">${icon("search")}<input class="input" id="f-search" name="search" type="search" maxlength="100"
            placeholder="e.g. milk" value="${filters.search}" autocomplete="off"></div></div>
        <div class="field"><label for="f-category">Category</label>
          <select class="select" id="f-category" name="category">${options(state.meta.categories, filters.category, "All categories")}</select></div>
        <div class="field"><label for="f-status">Status</label>
          <select class="select" id="f-status" name="status">${selectOptions(STATUS_OPTIONS, filters.status)}</select></div>
        <div class="field"><label for="f-sort">Sort by</label>
          <select class="select" id="f-sort" name="sort">${selectOptions(SORT_OPTIONS, filters.sort)}</select></div>
        <div class="field clear-field"><span class="label" aria-hidden="true">&nbsp;</span>
          <button class="btn btn-ghost" type="button" id="clear-filters">${icon("x", "sm")}Clear filters</button></div>
      </form>
      <div id="list" aria-live="polite" aria-busy="true">${skeletonRows(6)}</div>
      <div class="list-meta"><span id="count" class="num"></span>
        <nav class="pagination" aria-label="Pagination" id="pager"></nav></div>
    </section>`.value;

  const list = view.querySelector("#list");
  const form = view.querySelector("#filters");
  const clearButton = view.querySelector("#clear-filters");

  function syncUrl() {
    const query = new URLSearchParams();
    for (const key of ["search", "category", "status"]) if (filters[key]) query.set(key, filters[key]);
    if (filters.sort !== defaultSort) query.set("sort", filters.sort);
    history.replaceState(null, "", `#/inventory${query.toString() ? `?${query}` : ""}`);
    clearButton.disabled = !filters.search && !filters.category && !filters.status && filters.sort === defaultSort;
  }

  async function load() {
    const token = ++seq;
    list.classList.add("list-loading");
    list.setAttribute("aria-busy", "true");
    syncUrl();
    try {
      const data = await api.get("/api/foods", {
        search: filters.search.trim(), category: filters.category, status: filters.status, sort: filters.sort, page: filters.page, page_size: PAGE_SIZE,
      });
      if (!alive || token !== seq) return;
      items = data.items;
      filters.page = data.page;
      const filtered = filters.search || filters.category || filters.status;
      list.innerHTML = (items.length
        ? table(items, highlightId)
        : filtered
          ? emptyState({ iconName: "search", title: "No matching food", text: "Try a different name, or clear the filters to see everything.",
              action: html`<button class="btn btn-secondary" type="button" data-action="clear">Clear filters</button>` })
          : emptyState({ iconName: "box", title: "Your inventory is empty", text: "Add groceries as you buy them to keep track of their expiry dates.",
              action: html`<a class="btn btn-primary" href="#/add">${icon("plus")}Add your first item</a>` })).value;
      const from = data.total ? (data.page - 1) * data.page_size + 1 : 0;
      view.querySelector("#count").textContent = data.total
        ? `Showing ${from}–${from + items.length - 1} of ${plural(data.total, "item")}` : "0 items";
      view.querySelector("#pager").innerHTML = data.pages > 1 ? html`
        <button class="btn btn-secondary btn-icon" type="button" data-page="${data.page - 1}" ${data.page <= 1 ? "disabled" : ""} aria-label="Previous page">${icon("chevron-left")}</button>
        <span class="num">Page ${data.page} of ${data.pages}</span>
        <button class="btn btn-secondary btn-icon" type="button" data-page="${data.page + 1}" ${data.page >= data.pages ? "disabled" : ""} aria-label="Next page">${icon("chevron-right")}</button>`.value : "";
      list.querySelector("tr.highlight")?.scrollIntoView({ block: "center" });
    } catch (error) {
      if (!alive || token !== seq) return;
      list.innerHTML = errorState(error).value;
      list.querySelector("#retry").addEventListener("click", load);
    } finally {
      if (alive && token === seq) { list.classList.remove("list-loading"); list.setAttribute("aria-busy", "false"); }
    }
  }

  // ----- filters -----
  let debounce;
  form.addEventListener("submit", (event) => event.preventDefault());
  form.addEventListener("input", (event) => {
    const { name, value } = event.target;
    if (!(name in filters)) return;
    filters[name] = value;
    filters.page = 1;
    highlightId = null;
    clearTimeout(debounce);
    debounce = setTimeout(load, name === "search" ? 250 : 0);
  });
  function clearFilters() {
    Object.assign(filters, { search: "", category: "", status: "", sort: defaultSort, page: 1 });
    form.elements.search.value = "";
    form.elements.category.value = "";
    form.elements.status.value = "";
    form.elements.sort.value = defaultSort;
    load();
  }
  clearButton.addEventListener("click", clearFilters);
  view.querySelector("#pager").addEventListener("click", (event) => {
    const button = event.target.closest("[data-page]");
    if (!button || button.disabled) return;
    filters.page = Number(button.dataset.page);
    load();
    view.querySelector("#filters").scrollIntoView({ block: "start" });
  });

  // ----- row actions -----
  list.addEventListener("click", async (event) => {
    if (event.target.closest('[data-action="clear"]')) { clearFilters(); return; }
    const button = event.target.closest("[data-action]");
    const rowEl = button?.closest("tr[data-id]");
    if (!rowEl) return;
    const item = items.find((entry) => entry.id === Number(rowEl.dataset.id));
    if (!item) return;
    if (button.dataset.action === "edit") openEditor(item.id, button);
    if (button.dataset.action === "delete") confirmDelete(item, rowEl);
  });

  async function openEditor(id, trigger) {
    if (trigger) trigger.disabled = true;
    let item;
    try {
      item = await api.get(`/api/foods/${id}`);
    } catch (error) {
      toast(error.status === 404 ? "This item no longer exists. It may have been deleted." : error.message, "error");
      if (error.status === 404) load();
      return;
    } finally {
      if (trigger && document.contains(trigger)) trigger.disabled = false;
    }
    const { body, close } = openDialog({
      title: "Edit food item", subtitle: `Update the details for ${item.food_name}.`, wide: true,
      content: foodFormHTML(item, { submitLabel: "Save changes", cancel: true }),
    });
    bindFoodForm(body.querySelector("form"), {
      itemId: item.id,
      onSaved: (saved) => {
        close();
        highlightId = saved.id;
        toast(`Saved changes to ${saved.food_name}.`);
        dataChanged();
      },
    });
  }

  async function confirmDelete(item, rowEl) {
    const result = await confirmDialog({
      title: "Delete food item?",
      message: html`This permanently removes <strong>${item.food_name}</strong> (${item.category}, expiry ${formatDate(item.expiry_date)}) from your inventory.`,
      confirmLabel: "Delete item", danger: true,
      extra: html`<fieldset class="field" style="border:0;padding:0;margin:16px 0 0">
        <legend class="label" style="margin-bottom:8px">What happened to it? <span class="muted">(used for waste insights)</span></legend>
        <div class="radio-list">
          <label class="radio-card"><input type="radio" name="reason" value="consumed" checked><span>Used or eaten<small>It didn't go to waste</small></span></label>
          <label class="radio-card"><input type="radio" name="reason" value="discarded"><span>Thrown away<small>It went bad or expired</small></span></label>
          <label class="radio-card"><input type="radio" name="reason" value="other"><span>Other<small>For example, it was added by mistake</small></span></label>
        </div></fieldset>`,
    });
    if (!result) return;
    const buttons = rowEl.querySelectorAll("button");
    buttons.forEach((b) => { b.disabled = true; });
    try {
      await api.del(`/api/foods/${item.id}`, { reason: result.get("reason") || "other" });
      toast(`Deleted ${item.food_name}.`);
      dataChanged();
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        toast(`${item.food_name} was already deleted.`, "info");
        dataChanged();
      } else {
        toast(`Couldn't delete ${item.food_name}: ${error.message}`, "error");
        buttons.forEach((b) => { if (document.contains(b)) b.disabled = false; });
      }
    }
  }

  await load();
  const off = onDataChanged(load);
  return () => { alive = false; clearTimeout(debounce); off(); };
}
