// Shopping list with optional transfer of purchased items into inventory.
import { api, ApiError, newRequestKey } from "../api.js";
import { options } from "../foodForm.js";
import { dataChanged, state, today } from "../state.js";
import {
  confirmDialog, emptyState, errorState, formatQty, html, icon, openDialog, pageHead, plural, setBusy, skeletonRows, toast,
} from "../ui.js";

function validateItem(data) {
  const errors = {};
  if (!data.name) errors.name = "Enter an item name";
  else if (data.name.length > 100) errors.name = "Use 100 characters or fewer";
  if (data.quantity !== null && (!Number.isFinite(data.quantity) || data.quantity <= 0)) errors.quantity = "Quantity must be greater than 0";
  return errors;
}

function readItem(form) {
  const values = Object.fromEntries(new FormData(form));
  const quantity = (values.quantity || "").trim();
  return {
    name: (values.name || "").trim().replace(/\s+/g, " "),
    quantity: quantity === "" ? null : Number(quantity),
    unit: quantity === "" ? null : values.unit || null,
    category: values.category || "Other",
    notes: (values.notes || "").trim() || null,
  };
}

function fieldErrors(form, errors) {
  form.querySelectorAll(".error").forEach((el) => { el.hidden = true; });
  form.querySelectorAll("[aria-invalid]").forEach((el) => el.removeAttribute("aria-invalid"));
  let first = null;
  for (const [field, message] of Object.entries(errors)) {
    const input = form.elements[field];
    const el = form.querySelector(`[data-error="${field}"]`);
    if (!input || !el) continue;
    el.textContent = message;
    el.hidden = false;
    input.setAttribute("aria-invalid", "true");
    first ??= input;
  }
  first?.focus();
  return Boolean(first);
}

function itemFields(item = {}, prefix) {
  const meta = state.meta;
  return html`
    <div class="field name-field"><label for="${prefix}-name">Item <span class="req" aria-hidden="true">*</span></label>
      <input class="input" id="${prefix}-name" name="name" maxlength="100" required autocomplete="off" placeholder="e.g. Eggs" value="${item.name || ""}">
      <p class="error" data-error="name" hidden></p></div>
    <div class="field"><label for="${prefix}-qty">Quantity</label>
      <input class="input" id="${prefix}-qty" name="quantity" type="number" min="0.01" step="any" inputmode="decimal" value="${item.quantity ?? ""}" placeholder="Optional">
      <p class="error" data-error="quantity" hidden></p></div>
    <div class="field"><label for="${prefix}-unit">Unit</label>
      <select class="select" id="${prefix}-unit" name="unit">${options(meta.units, item.unit || "pcs")}</select></div>
    <div class="field"><label for="${prefix}-cat">Category</label>
      <select class="select" id="${prefix}-cat" name="category">${options(meta.categories, item.category || "Other")}</select></div>`;
}

function itemRow(item) {
  return html`<li class="${item.purchased ? "is-purchased" : ""}" data-id="${item.id}">
    <button class="check" type="button" role="checkbox" aria-checked="${item.purchased}" data-action="toggle"
      aria-label="${item.purchased ? "Mark as pending" : "Mark as purchased"}: ${item.name}"><span class="box">${item.purchased ? icon("check", "sm") : ""}</span></button>
    <div class="grow"><div class="item-name">${item.name}</div>
      <div class="item-sub">${item.quantity !== null ? formatQty(item.quantity, item.unit) + " · " : ""}${item.category}${item.notes ? ` · ${item.notes}` : ""}</div></div>
    <div class="shop-actions">
      ${item.inventory_food_id ? html`<span class="chip">${icon("check", "sm")}In inventory</span>` : ""}
      ${item.purchased && !item.inventory_food_id
        ? html`<button class="btn btn-secondary" type="button" data-action="move">${icon("box", "sm")}Add to inventory</button>` : ""}
      <button class="btn btn-ghost btn-icon" type="button" data-action="edit" aria-label="Edit ${item.name}">${icon("edit", "sm")}</button>
      <button class="btn btn-danger-ghost btn-icon" type="button" data-action="delete" aria-label="Delete ${item.name}">${icon("trash", "sm")}</button>
    </div>
  </li>`;
}

export async function render(view) {
  let alive = true;
  let filter = "all";
  let items = [];
  let counts = { all: 0, pending: 0, purchased: 0 };
  let addKey = newRequestKey();
  let seq = 0;

  view.innerHTML = html`
    ${pageHead({ eyebrow: "Shopping list", title: "Shopping list", subtitle: "Plan your groceries, tick items off as you buy them, then add them to your inventory." })}
    <section class="card card-pad" style="margin-bottom:16px" aria-labelledby="add-title">
      <h2 id="add-title" class="sr-only">Add a shopping item</h2>
      <form class="add-row" id="add-form" novalidate>${itemFields({}, "new")}
        <button class="btn btn-primary btn-lg add-btn" type="submit">${icon("plus")}Add item</button></form>
    </section>
    <section class="card" aria-label="Shopping items">
      <div class="card-head" style="align-items:center">
        <div class="segmented" role="group" aria-label="Filter items" id="filter"></div>
        <button class="btn btn-ghost" type="button" id="clear-completed">${icon("trash", "sm")}Clear purchased</button>
      </div>
      <div id="list" aria-live="polite" aria-busy="true">${skeletonRows(4)}</div>
    </section>`.value;

  const list = view.querySelector("#list");
  const addForm = view.querySelector("#add-form");

  function renderFilter() {
    view.querySelector("#filter").innerHTML = [["all", "All"], ["pending", "Pending"], ["purchased", "Purchased"]].map(([key, label]) =>
      html`<button type="button" data-filter="${key}" aria-pressed="${filter === key}">${label}<span class="count">${counts[key]}</span></button>`.value).join("");
    view.querySelector("#clear-completed").disabled = counts.purchased === 0;
  }

  async function load() {
    const token = ++seq;
    try {
      const data = await api.get("/api/shopping", { status: filter });
      if (!alive || token !== seq) return;
      items = data.items;
      counts = data.counts;
      renderFilter();
      list.innerHTML = (items.length
        ? html`<ul class="item-list shop-list">${items.map(itemRow)}</ul>`
        : emptyState({
            iconName: "cart",
            title: filter === "all" ? "Your shopping list is empty" : filter === "pending" ? "Nothing left to buy" : "No purchased items",
            text: filter === "all" ? "Add the groceries you need above. Tick them off as you shop." : "Switch the filter to see other items.",
            compact: true,
          })).value;
    } catch (error) {
      if (!alive || token !== seq) return;
      list.innerHTML = errorState(error).value;
      list.querySelector("#retry").addEventListener("click", load);
    } finally {
      if (alive && token === seq) list.setAttribute("aria-busy", "false");
    }
  }

  addForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = addForm.querySelector('[type="submit"]');
    if (button.disabled) return;
    const data = readItem(addForm);
    if (fieldErrors(addForm, validateItem(data))) return;
    setBusy(button, true, "Adding…");
    try {
      const saved = await api.post("/api/shopping", data, { "Idempotency-Key": addKey });
      addKey = newRequestKey();
      toast(`Added ${saved.name} to your shopping list.`);
      addForm.elements.name.value = "";
      addForm.elements.quantity.value = "";
      addForm.elements.name.focus();
      if (filter === "purchased") filter = "all";
      await load();
    } catch (error) {
      if (!(error instanceof ApiError && fieldErrors(addForm, error.fields))) toast(error.message, "error");
    } finally {
      setBusy(button, false);
    }
  });

  view.querySelector("#filter").addEventListener("click", (event) => {
    const button = event.target.closest("[data-filter]");
    if (!button) return;
    filter = button.dataset.filter;
    renderFilter();
    load();
  });

  view.querySelector("#clear-completed").addEventListener("click", async () => {
    const ok = await confirmDialog({
      title: "Clear purchased items?",
      message: `This removes ${plural(counts.purchased, "purchased item")} from your shopping list. Food you already added to your inventory stays there.`,
      confirmLabel: "Clear purchased", danger: true,
    });
    if (!ok) return;
    try {
      const { removed } = await api.post("/api/shopping/clear-completed");
      toast(`Removed ${plural(removed, "purchased item")}.`);
      await load();
    } catch (error) {
      toast(error.message, "error");
    }
  });

  list.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action]");
    const li = button?.closest("li[data-id]");
    if (!li) return;
    const item = items.find((entry) => entry.id === Number(li.dataset.id));
    if (!item) return;
    const action = button.dataset.action;
    if (action === "toggle") {
      button.disabled = true;
      try {
        await api.patch(`/api/shopping/${item.id}/status`, { purchased: !item.purchased });
        await load();
      } catch (error) {
        toast(error.message, "error");
        if (document.contains(button)) button.disabled = false;
        if (error.status === 404) load();
      }
    } else if (action === "edit") {
      openEdit(item);
    } else if (action === "delete") {
      const ok = await confirmDialog({ title: "Delete shopping item?", message: html`Remove <strong>${item.name}</strong> from your shopping list?`, confirmLabel: "Delete", danger: true });
      if (!ok) return;
      try {
        await api.del(`/api/shopping/${item.id}`);
        toast(`Deleted ${item.name}.`);
      } catch (error) {
        toast(error.status === 404 ? `${item.name} was already deleted.` : error.message, error.status === 404 ? "info" : "error");
      }
      load();
    } else if (action === "move") {
      openMove(item);
    }
  });

  function openEdit(item) {
    const { body, close } = openDialog({
      title: "Edit shopping item",
      content: html`<form novalidate><div class="form-grid">${itemFields(item, "edit")}
        <div class="field span-2"><label for="edit-notes">Notes</label><textarea class="textarea" id="edit-notes" name="notes" maxlength="500">${item.notes || ""}</textarea></div></div>
        <div class="form-actions"><button class="btn btn-secondary" type="button" data-close>Cancel</button>
        <button class="btn btn-primary" type="submit">Save changes</button></div></form>`,
    });
    const form = body.querySelector("form");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector('[type="submit"]');
      if (button.disabled) return;
      const data = readItem(form);
      if (fieldErrors(form, validateItem(data))) return;
      setBusy(button, true);
      try {
        await api.put(`/api/shopping/${item.id}`, data);
        close();
        toast(`Saved ${data.name}.`);
        load();
      } catch (error) {
        if (!(error instanceof ApiError && fieldErrors(form, error.fields))) toast(error.message, "error");
        setBusy(button, false);
      }
    });
  }

  function openMove(item) {
    const meta = state.meta;
    const { body, close } = openDialog({
      title: "Add to inventory",
      subtitle: `Enter the expiry date printed on ${item.name}. It is never guessed for you.`,
      content: html`<form novalidate><div class="form-grid">
        <div class="field"><label for="mv-exp">Expiry date <span class="req" aria-hidden="true">*</span></label>
          <input class="input" id="mv-exp" name="expiry_date" type="date" required min="2000-01-01" max="2099-12-31" autofocus>
          <p class="error" data-error="expiry_date" hidden></p></div>
        <div class="field"><label for="mv-mfg">Manufacturing / purchase date</label>
          <input class="input" id="mv-mfg" name="mfg_date" type="date" max="${today()}" value="${today()}">
          <p class="error" data-error="mfg_date" hidden></p></div>
        <div class="field"><label for="mv-cat">Category</label><select class="select" id="mv-cat" name="category">${options(meta.categories, item.category)}</select></div>
        <div class="field"><label for="mv-store">Storage location</label><select class="select" id="mv-store" name="storage_location">${options(meta.storage_locations, null, "Not specified")}</select></div>
        <div class="field"><label for="mv-qty">Quantity</label><input class="input" id="mv-qty" name="quantity" type="number" min="0.01" step="any" value="${item.quantity ?? 1}">
          <p class="error" data-error="quantity" hidden></p></div>
        <div class="field"><label for="mv-unit">Unit</label><select class="select" id="mv-unit" name="unit">${options(meta.units, item.unit || "pcs")}</select></div>
      </div>
      <div class="banner banner-danger form-error" role="alert" hidden></div>
      <div class="form-actions"><button class="btn btn-secondary" type="button" data-close>Cancel</button>
        <button class="btn btn-primary" type="submit">${icon("box")}Add to inventory</button></div></form>`,
    });
    const form = body.querySelector("form");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector('[type="submit"]');
      if (button.disabled) return;
      const v = Object.fromEntries(new FormData(form));
      const payload = {
        expiry_date: v.expiry_date, mfg_date: v.mfg_date || null, category: v.category, storage_location: v.storage_location || null,
        quantity: v.quantity === "" ? null : Number(v.quantity), unit: v.unit,
      };
      const errors = {};
      if (!payload.expiry_date) errors.expiry_date = "Enter the expiry date";
      if (payload.mfg_date && payload.mfg_date > today()) errors.mfg_date = "This date cannot be in the future";
      else if (payload.mfg_date && payload.expiry_date && payload.mfg_date > payload.expiry_date) errors.mfg_date = "Must be on or before the expiry date";
      if (payload.quantity !== null && !(payload.quantity > 0)) errors.quantity = "Quantity must be greater than 0";
      if (fieldErrors(form, errors)) return;
      setBusy(button, true, "Adding…");
      const banner = form.querySelector(".form-error");
      banner.hidden = true;
      try {
        const result = await api.post(`/api/shopping/${item.id}/move-to-inventory`, payload);
        close();
        toast(`${result.food.food_name} is now in your inventory (${result.food.status_label.toLowerCase()}).`);
        dataChanged();
        load();
      } catch (error) {
        if (!(error instanceof ApiError && fieldErrors(form, error.fields))) {
          banner.textContent = error.message;
          banner.hidden = false;
        }
        setBusy(button, false);
        if (error.status === 409) load();
      }
    });
  }

  await load();
  return () => { alive = false; };
}
