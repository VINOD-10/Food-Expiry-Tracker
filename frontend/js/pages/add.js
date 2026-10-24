// Add Food: a quick form that resets after each successful save.
import { bindFoodForm, foodFormHTML } from "../foodForm.js";
import { dataChanged, state } from "../state.js";
import { formatDays, html, icon, pageHead, toast } from "../ui.js";

export async function render(view) {
  view.innerHTML = html`
    ${pageHead({ eyebrow: "Add food", title: "Add a food item", subtitle: "Only the name and expiry date are required. Everything else is optional." })}
    <div class="grid grid-3-2">
      <section class="card card-pad" aria-label="New food item">${foodFormHTML({}, { submitLabel: "Add to inventory" })}</section>
      <aside class="stack">
        <div class="card card-pad" id="last-added" hidden></div>
        <div class="card card-pad">
          <h2>Tips for accurate tracking</h2>
          <ul class="tips" style="margin-top:12px">
            <li>${icon("calendar")}<span>Enter the date printed on the pack. Opened items often last less, so you can set an earlier date.</span></li>
            <li>${icon("bell")}<span>Items within ${state.settings.expiry_threshold} days of expiry appear in Expiry Alerts. You can change this in Settings.</span></li>
            <li>${icon("info")}<span>You can record food that has already expired, for example to log it before throwing it away.</span></li>
          </ul>
        </div>
      </aside>
    </div>`.value;

  const form = view.querySelector("form");
  form.elements.food_name.focus();
  bindFoodForm(form, {
    onSaved: (saved) => {
      toast(`Added ${saved.food_name} to your inventory.`);
      form.reset();
      form.elements.food_name.focus();
      const panel = view.querySelector("#last-added");
      panel.hidden = false;
      panel.innerHTML = html`<h2>Saved</h2>
        <p class="muted" style="margin-top:4px"><strong>${saved.food_name}</strong> · ${saved.status_label} · ${formatDays(saved.days_remaining)}</p>
        <div class="page-actions" style="margin-top:12px">
          <a class="btn btn-secondary" href="#/inventory?item=${saved.id}&search=${encodeURIComponent(saved.food_name)}">View in inventory</a>
        </div>`.value;
      dataChanged();
    },
  });
}
