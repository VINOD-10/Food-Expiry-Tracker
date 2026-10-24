// The add/edit food form, shared by the Add Food page and the inventory edit dialog.
import { api, ApiError, newRequestKey } from "./api.js";
import { state, today } from "./state.js";
import { html, icon, setBusy } from "./ui.js";

export const options = (values, selected, blank) => html`${blank !== undefined ? html`<option value="">${blank}</option>` : ""}${values.map(
  (value) => html`<option value="${value}" ${value === selected ? "selected" : ""}>${value}</option>`)}`;

export function foodFormHTML(item = {}, { submitLabel = "Save food", cancel = false } = {}) {
  const meta = state.meta;
  const id = (name) => `ff-${name}`;
  const err = (name) => html`<p class="error" id="${id(name)}-error" hidden></p>`;
  return html`<form class="food-form" novalidate>
    <div class="form-grid">
      <div class="field span-2">
        <label for="${id("food_name")}">Food name <span class="req" aria-hidden="true">*</span></label>
        <input class="input" id="${id("food_name")}" name="food_name" maxlength="100" required autocomplete="off"
          placeholder="e.g. Toned milk" value="${item.food_name || ""}" aria-describedby="${id("food_name")}-error">
        ${err("food_name")}
      </div>
      <div class="field">
        <label for="${id("category")}">Category <span class="req" aria-hidden="true">*</span></label>
        <select class="select" id="${id("category")}" name="category" required>${options(meta.categories, item.category || "Other")}</select>
        ${err("category")}
      </div>
      <div class="field">
        <label for="${id("quantity")}">Quantity</label>
        <div class="input-group">
          <input class="input" id="${id("quantity")}" name="quantity" type="number" inputmode="decimal" min="0.01" max="100000" step="any"
            value="${item.quantity ?? (item.id ? "" : "1")}" aria-describedby="${id("quantity")}-error">
          <select class="select" name="unit" aria-label="Quantity unit">${options(meta.units, item.unit || "pcs")}</select>
        </div>
        ${err("quantity")}
      </div>
      <div class="field">
        <label for="${id("mfg_date")}">Manufacturing / purchase date</label>
        <input class="input" id="${id("mfg_date")}" name="mfg_date" type="date" max="${today()}" value="${item.mfg_date || ""}"
          aria-describedby="${id("mfg_date")}-hint ${id("mfg_date")}-error">
        <p class="hint" id="${id("mfg_date")}-hint">Optional</p>
        ${err("mfg_date")}
      </div>
      <div class="field">
        <label for="${id("expiry_date")}">Expiry date <span class="req" aria-hidden="true">*</span></label>
        <input class="input" id="${id("expiry_date")}" name="expiry_date" type="date" required min="2000-01-01" max="2099-12-31"
          value="${item.expiry_date || ""}" aria-describedby="${id("expiry_date")}-hint ${id("expiry_date")}-error">
        <p class="hint" id="${id("expiry_date")}-hint">Use the "best before" or "use by" date on the pack.</p>
        ${err("expiry_date")}
      </div>
      <div class="field">
        <label for="${id("storage_location")}">Storage location</label>
        <select class="select" id="${id("storage_location")}" name="storage_location">${options(meta.storage_locations, item.storage_location, "Not specified")}</select>
      </div>
      <div class="field span-2">
        <label for="${id("notes")}">Notes</label>
        <textarea class="textarea" id="${id("notes")}" name="notes" maxlength="500" placeholder="Optional, e.g. opened on Monday"
          aria-describedby="${id("notes")}-error">${item.notes || ""}</textarea>
        ${err("notes")}
      </div>
    </div>
    <div class="banner banner-danger form-error" role="alert" hidden></div>
    <div class="form-actions">
      ${cancel ? html`<button class="btn btn-secondary" type="button" data-close>Cancel</button>` : ""}
      ${!cancel ? html`<button class="btn btn-secondary" type="reset">Clear form</button>` : ""}
      <button class="btn btn-primary btn-lg" type="submit">${icon("check")}${submitLabel}</button>
    </div>
  </form>`;
}

function readForm(form) {
  const data = Object.fromEntries(new FormData(form));
  const quantity = data.quantity.trim();
  return {
    food_name: data.food_name.trim().replace(/\s+/g, " "),
    category: data.category,
    quantity: quantity === "" ? null : Number(quantity),
    unit: quantity === "" ? null : data.unit,
    mfg_date: data.mfg_date || null,
    expiry_date: data.expiry_date,
    storage_location: data.storage_location || null,
    notes: data.notes.trim() || null,
  };
}

/** Client-side checks that mirror the server rules, for instant feedback. */
export function validateFood(data, form) {
  const errors = {};
  const quantityInput = form?.elements.quantity;
  if (!data.food_name) errors.food_name = "Enter the food name";
  else if (data.food_name.length > 100) errors.food_name = "Use 100 characters or fewer";
  if (quantityInput && quantityInput.validity.badInput) errors.quantity = "Enter a valid number";
  else if (data.quantity !== null && (!Number.isFinite(data.quantity) || data.quantity <= 0)) errors.quantity = "Quantity must be greater than 0";
  else if (data.quantity > 100000) errors.quantity = "Quantity looks too large";
  const expiryInput = form?.elements.expiry_date;
  if (!data.expiry_date) errors.expiry_date = expiryInput?.validity.badInput ? "Enter a complete, valid date" : "Enter the expiry date";
  else if (data.expiry_date < "2000-01-01" || data.expiry_date > "2099-12-31") errors.expiry_date = "Expiry date must be between 2000 and 2099";
  if (data.mfg_date) {
    if (data.mfg_date > today()) errors.mfg_date = "This date cannot be in the future";
    else if (data.expiry_date && data.mfg_date > data.expiry_date) errors.mfg_date = "Must be on or before the expiry date";
  } else if (form?.elements.mfg_date?.validity.badInput) errors.mfg_date = "Enter a complete, valid date";
  if (data.notes && data.notes.length > 500) errors.notes = "Use 500 characters or fewer";
  return errors;
}

function showErrors(form, errors, message) {
  form.querySelectorAll(".error").forEach((el) => { el.hidden = true; el.textContent = ""; });
  form.querySelectorAll("[aria-invalid]").forEach((el) => el.removeAttribute("aria-invalid"));
  const banner = form.querySelector(".form-error");
  let first = null;
  for (const [field, text] of Object.entries(errors)) {
    const el = form.querySelector(`#ff-${field}-error`);
    const input = form.elements[field];
    if (el && input) {
      el.textContent = text;
      el.hidden = false;
      input.setAttribute("aria-invalid", "true");
      first ??= input;
    }
  }
  const unplaced = message && (!first || Object.keys(errors).some((f) => !form.querySelector(`#ff-${f}-error`)));
  banner.hidden = !unplaced;
  banner.textContent = unplaced ? message : "";
  (first || (unplaced ? banner : null))?.focus?.();
  if (!first && unplaced) banner.scrollIntoView({ block: "nearest" });
}

/**
 * Wires validation and submission. `itemId` switches between create and update.
 * Input is never cleared when saving fails.
 */
export function bindFoodForm(form, { itemId = null, onSaved }) {
  let requestKey = newRequestKey();
  let saving = false;
  form.addEventListener("reset", () => setTimeout(() => showErrors(form, {}), 0));
  form.addEventListener("input", (event) => {
    const field = event.target.name;
    const el = form.querySelector(`#ff-${field}-error`);
    if (el && !el.hidden) { el.hidden = true; event.target.removeAttribute("aria-invalid"); }
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (saving) return;
    const data = readForm(form);
    const errors = validateFood(data, form);
    if (Object.keys(errors).length) {
      showErrors(form, errors);
      return;
    }
    showErrors(form, {});
    const button = form.querySelector('[type="submit"]');
    saving = true;
    setBusy(button, true);
    try {
      const saved = itemId
        ? await api.put(`/api/foods/${itemId}`, data)
        : await api.post("/api/foods", data, { "Idempotency-Key": requestKey });
      requestKey = newRequestKey();
      await onSaved(saved, form);
    } catch (error) {
      const fields = error instanceof ApiError ? { ...error.fields } : {};
      delete fields._;
      showErrors(form, fields, error.message);
    } finally {
      saving = false;
      if (document.contains(button)) setBusy(button, false);
    }
  });
}
