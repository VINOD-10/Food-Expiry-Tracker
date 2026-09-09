import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

import database


COLORS = {
    "ink": "#17212B", "muted": "#6D7885", "line": "#E3E8ED",
    "paper": "#F7F8FA", "white": "#FFFFFF", "navy": "#142A3D",
    "navy_soft": "#1D3A52", "teal": "#0F8B8D", "teal_dark": "#0B6E70",
    "amber": "#C47B16", "red": "#C6534B", "green": "#2E8B68",
}
FONT = "Segoe UI"


class FoodExpiryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pantry | Food expiry tracker")
        self.root.geometry("1120x720")
        self.root.minsize(880, 620)
        self.root.configure(bg=COLORS["paper"])
        self.selected_id = None
        database.connect()
        self._configure_styles()
        self._build_shell()
        self._refresh()

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Food.Treeview", background=COLORS["white"], fieldbackground=COLORS["white"], foreground=COLORS["ink"], rowheight=48, borderwidth=0, font=(FONT, 10))
        style.configure("Food.Treeview.Heading", background=COLORS["white"], foreground=COLORS["muted"], font=(FONT, 9, "bold"), padding=(12, 10), relief="flat")
        style.map("Food.Treeview", background=[("selected", "#E3F2F2")], foreground=[("selected", COLORS["ink"])])
        style.configure("Food.Vertical.TScrollbar", troughcolor=COLORS["white"], background="#CBD5DD", borderwidth=0, arrowsize=12)

    def _label(self, parent, text, size=10, color=None, weight="normal", **kwargs):
        return tk.Label(parent, text=text, font=(FONT, size, weight), fg=color or COLORS["ink"], bg=parent.cget("bg"), **kwargs)

    def _build_shell(self):
        self.sidebar = tk.Frame(self.root, bg=COLORS["navy"], width=224)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=COLORS["navy"])
        brand.pack(fill="x", padx=24, pady=(28, 38))
        tk.Label(brand, text="P", font=(FONT, 18, "bold"), fg=COLORS["navy"], bg="#8DE0D7", width=2).pack(side="left")
        tk.Label(brand, text="PANTRY", font=(FONT, 13, "bold"), fg=COLORS["white"], bg=COLORS["navy"]).pack(side="left", padx=10)
        self._nav_item("⌂", "Overview", active=True).pack(fill="x", padx=12, pady=2)
        self._nav_item("□", "Inventory").pack(fill="x", padx=12, pady=2)
        self._nav_item("◷", "Expiring soon").pack(fill="x", padx=12, pady=2)
        self._label(self.sidebar, "WORKSPACE", 8, "#8296A7", "bold").pack(anchor="w", padx=28, pady=(34, 12))
        self._nav_item("⚙", "Preferences").pack(fill="x", padx=12, pady=2)
        self._nav_item("?", "Help center").pack(fill="x", padx=12, pady=2)
        bottom = tk.Frame(self.sidebar, bg=COLORS["navy"])
        bottom.pack(side="bottom", fill="x", padx=24, pady=24)
        tk.Frame(bottom, bg="#315069", height=1).pack(fill="x", pady=(0, 18))
        self._label(bottom, "YOUR PANTRY", 8, "#8296A7", "bold").pack(anchor="w")
        self._label(bottom, "A clearer view of what\nyou already have.", 10, "#B6C5D0").pack(anchor="w", pady=(7, 0))
        self.content = tk.Frame(self.root, bg=COLORS["paper"])
        self.content.pack(side="left", fill="both", expand=True)
        self._build_header()
        self._build_dashboard()

    def _nav_item(self, icon, text, active=False):
        frame = tk.Frame(self.sidebar, bg=COLORS["navy_soft"] if active else COLORS["navy"], height=42)
        frame.pack_propagate(False)
        tk.Label(frame, text=icon, font=(FONT, 14), fg="#A8E5DF" if active else "#94A8B7", bg=frame.cget("bg"), width=3).pack(side="left")
        tk.Label(frame, text=text, font=(FONT, 10, "bold" if active else "normal"), fg=COLORS["white"] if active else "#B6C5D0", bg=frame.cget("bg")).pack(side="left")
        return frame

    def _build_header(self):
        header = tk.Frame(self.content, bg=COLORS["paper"])
        header.pack(fill="x", padx=42, pady=(32, 0))
        left = tk.Frame(header, bg=COLORS["paper"])
        left.pack(side="left")
        self._label(left, "GOOD MORNING", 9, COLORS["teal"], "bold").pack(anchor="w")
        self._label(left, "Your pantry, at a glance.", 25, COLORS["ink"], "bold").pack(anchor="w", pady=(5, 0))
        self._label(left, "Keep food fresh and waste less.", 10, COLORS["muted"]).pack(anchor="w", pady=(5, 0))
        profile = tk.Frame(header, bg=COLORS["paper"])
        profile.pack(side="right", anchor="n")
        tk.Label(profile, text="JD", font=(FONT, 10, "bold"), fg=COLORS["navy"], bg="#D8EEEB", width=4, height=2).pack(side="left")
        tk.Label(profile, text="Jordan's pantry\nPersonal workspace", justify="left", font=(FONT, 9), fg=COLORS["muted"], bg=COLORS["paper"]).pack(side="left", padx=(10, 0))

    def _build_dashboard(self):
        self.body = tk.Frame(self.content, bg=COLORS["paper"])
        self.body.pack(fill="both", expand=True, padx=42, pady=(28, 32))
        self.metrics = tk.Frame(self.body, bg=COLORS["paper"])
        self.metrics.pack(fill="x", pady=(0, 24))
        for column in range(4):
            self.metrics.columnconfigure(column, weight=1)
        self.metric_values = {}
        self._metric("TOTAL ITEMS", "0", "in your pantry", COLORS["teal"], 0)
        self._metric("FRESH", "0", "more than 3 days left", COLORS["green"], 1)
        self._metric("EXPIRING SOON", "0", "within the next 3 days", COLORS["amber"], 2)
        self._metric("EXPIRED", "0", "need your attention", COLORS["red"], 3)
        workspace = tk.Frame(self.body, bg=COLORS["paper"])
        workspace.pack(fill="both", expand=True)
        workspace.columnconfigure(0, weight=1, minsize=340)
        workspace.columnconfigure(1, weight=2, minsize=500)
        workspace.rowconfigure(0, weight=1)
        self._build_editor(workspace).grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        self._build_inventory(workspace).grid(row=0, column=1, sticky="nsew")

    def _metric(self, title, value, subtitle, color, column):
        card = tk.Frame(self.metrics, bg=COLORS["white"], highlightbackground=COLORS["line"], highlightthickness=1)
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0))
        tk.Frame(card, bg=color, width=4).pack(side="left", fill="y")
        inner = tk.Frame(card, bg=COLORS["white"])
        inner.pack(fill="both", expand=True, padx=16, pady=14)
        tk.Label(inner, text=title, font=(FONT, 8, "bold"), fg=COLORS["muted"], bg=COLORS["white"]).pack(anchor="w")
        value_label = tk.Label(inner, text=value, font=(FONT, 22, "bold"), fg=COLORS["ink"], bg=COLORS["white"])
        value_label.pack(anchor="w", pady=(5, 0))
        tk.Label(inner, text=subtitle, font=(FONT, 8), fg=COLORS["muted"], bg=COLORS["white"]).pack(anchor="w")
        self.metric_values[title] = value_label

    def _build_editor(self, parent):
        panel = tk.Frame(parent, bg=COLORS["white"], highlightbackground=COLORS["line"], highlightthickness=1)
        self._label(panel, "ADD TO PANTRY", 9, COLORS["teal"], "bold").pack(anchor="w", padx=24, pady=(24, 5))
        self.editor_title = self._label(panel, "Track a food item", 17, COLORS["ink"], "bold")
        self.editor_title.pack(anchor="w", padx=24)
        self._label(panel, "Add dates so Pantry can keep an eye on it.", 9, COLORS["muted"]).pack(anchor="w", padx=24, pady=(5, 22))
        form = tk.Frame(panel, bg=COLORS["white"])
        form.pack(fill="x", padx=24)
        self.food_entry = self._field(form, "FOOD NAME", "e.g. Greek yogurt")
        self.mfg_entry = self._field(form, "PURCHASED / MADE", "DD-MM-YYYY")
        self.exp_entry = self._field(form, "EXPIRY DATE", "DD-MM-YYYY")
        actions = tk.Frame(panel, bg=COLORS["white"])
        actions.pack(fill="x", padx=24, pady=(18, 0))
        self._button(actions, "Add item", self.add_food, COLORS["teal"], COLORS["teal_dark"]).pack(side="left", fill="x", expand=True)
        self._button(actions, "Update", self.update_food, "#EEF3F5", "#DDE7EB", fg=COLORS["ink"]).pack(side="left", padx=(8, 0))
        self._button(actions, "Clear", self.clear_form, COLORS["white"], "#EEF3F5", fg=COLORS["muted"]).pack(side="left", padx=(8, 0))
        tip = tk.Frame(panel, bg="#F0F8F7")
        tip.pack(fill="x", padx=24, pady=(28, 24), side="bottom")
        tk.Label(tip, text="i", font=(FONT, 10, "bold"), fg=COLORS["teal"], bg="#F0F8F7", width=3).pack(side="left", padx=(8, 0), pady=10)
        tk.Label(tip, text="Select an item in the list to edit or remove it.", font=(FONT, 8), fg=COLORS["teal_dark"], bg="#F0F8F7", wraplength=220, justify="left").pack(side="left", padx=2, pady=10)
        return panel

    def _field(self, parent, label, placeholder):
        self._label(parent, label, 8, COLORS["muted"], "bold").pack(anchor="w", pady=(0, 6))
        entry = tk.Entry(parent, font=(FONT, 10), fg=COLORS["ink"], bg="#FBFCFD", relief="flat", highlightthickness=1, highlightbackground=COLORS["line"], highlightcolor=COLORS["teal"], insertwidth=1)
        entry.pack(fill="x", ipady=9, pady=(0, 16))
        entry.insert(0, placeholder)
        entry.config(fg="#A0AAB3")
        entry.bind("<FocusIn>", lambda event: self._clear_placeholder(entry, placeholder))
        entry.bind("<FocusOut>", lambda event: self._restore_placeholder(entry, placeholder))
        return entry

    @staticmethod
    def _clear_placeholder(entry, placeholder):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.config(fg=COLORS["ink"])

    @staticmethod
    def _restore_placeholder(entry, placeholder):
        if not entry.get().strip():
            entry.insert(0, placeholder)
            entry.config(fg="#A0AAB3")

    def _button(self, parent, text, command, bg, active, fg="white"):
        return tk.Button(parent, text=text, command=command, font=(FONT, 9, "bold"), fg=fg, bg=bg, activebackground=active, activeforeground=fg, relief="flat", bd=0, cursor="hand2", padx=13, pady=9)

    def _build_inventory(self, parent):
        panel = tk.Frame(parent, bg=COLORS["white"], highlightbackground=COLORS["line"], highlightthickness=1)
        toolbar = tk.Frame(panel, bg=COLORS["white"])
        toolbar.pack(fill="x", padx=22, pady=(22, 16))
        title = tk.Frame(toolbar, bg=COLORS["white"])
        title.pack(side="left")
        tk.Label(title, text="Your inventory", font=(FONT, 15, "bold"), fg=COLORS["ink"], bg=COLORS["white"]).pack(anchor="w")
        self.inventory_count = tk.Label(title, text="0 items", font=(FONT, 8), fg=COLORS["muted"], bg=COLORS["white"])
        self.inventory_count.pack(anchor="w", pady=(3, 0))
        search_wrap = tk.Frame(toolbar, bg="#F5F7F8", highlightbackground=COLORS["line"], highlightthickness=1)
        search_wrap.pack(side="right")
        tk.Label(search_wrap, text="⌕", font=(FONT, 14), fg=COLORS["muted"], bg="#F5F7F8").pack(side="left", padx=(8, 0))
        self.search_entry = tk.Entry(search_wrap, width=18, font=(FONT, 9), fg=COLORS["ink"], bg="#F5F7F8", relief="flat", bd=0)
        self.search_entry.pack(side="left", ipady=7, padx=6)
        self.search_entry.insert(0, "Search inventory")
        self.search_entry.config(fg="#A0AAB3")
        self.search_entry.bind("<FocusIn>", lambda event: self._clear_placeholder(self.search_entry, "Search inventory"))
        self.search_entry.bind("<FocusOut>", lambda event: self._restore_placeholder(self.search_entry, "Search inventory"))
        self.search_entry.bind("<KeyRelease>", lambda event: self._refresh())
        table_wrap = tk.Frame(panel, bg=COLORS["white"])
        table_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        columns = ("name", "expiry", "days", "status")
        self.food_table = ttk.Treeview(table_wrap, columns=columns, show="headings", style="Food.Treeview", selectmode="browse")
        headings = {"name": "FOOD ITEM", "expiry": "EXPIRY DATE", "days": "DAYS LEFT", "status": "STATUS"}
        widths = {"name": 150, "expiry": 110, "days": 85, "status": 135}
        for column in columns:
            self.food_table.heading(column, text=headings[column], anchor="w")
            self.food_table.column(column, width=widths[column], anchor="w", stretch=column == "name")
        scrollbar = ttk.Scrollbar(table_wrap, orient="vertical", command=self.food_table.yview, style="Food.Vertical.TScrollbar")
        self.food_table.configure(yscrollcommand=scrollbar.set)
        self.food_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.food_table.tag_configure("safe", foreground=COLORS["green"])
        self.food_table.tag_configure("soon", foreground=COLORS["amber"])
        self.food_table.tag_configure("expired", foreground=COLORS["red"])
        self.food_table.bind("<<TreeviewSelect>>", self.select_item)
        self.food_table.bind("<Delete>", lambda event: self.delete_food())
        self._button(panel, "Delete selected item", self.delete_food, COLORS["white"], "#FDEDEC", fg=COLORS["red"]).pack(anchor="e", padx=22, pady=(0, 20))
        return panel

    def _value(self, entry):
        text = entry.get().strip()
        return "" if text in ("e.g. Greek yogurt", "DD-MM-YYYY", "Search inventory") else text

    def _refresh(self):
        rows = database.fetch()
        query = self._value(self.search_entry) if hasattr(self, "search_entry") else ""
        if query:
            rows = [row for row in rows if query.lower() in row[1].lower()]
        if hasattr(self, "food_table"):
            self.food_table.delete(*self.food_table.get_children())
        counts = {"total": len(database.fetch()), "fresh": 0, "soon": 0, "expired": 0}
        for row in rows:
            try:
                days_left = (datetime.strptime(row[3], "%d-%m-%Y") - datetime.now()).days
                if days_left < 0:
                    status, tag = "Expired", "expired"
                    counts["expired"] += 1
                elif days_left <= 3:
                    status, tag = "Expiring soon", "soon"
                    counts["soon"] += 1
                else:
                    status, tag = "Fresh", "safe"
                    counts["fresh"] += 1
                self.food_table.insert("", "end", iid=str(row[0]), values=(row[1], row[3], f"{days_left} days", status), tags=(tag,))
            except (TypeError, ValueError):
                self.food_table.insert("", "end", iid=str(row[0]), values=(row[1], row[3], "-", "Invalid date"), tags=("expired",))
        for key, title in (("total", "TOTAL ITEMS"), ("fresh", "FRESH"), ("soon", "EXPIRING SOON"), ("expired", "EXPIRED")):
            self.metric_values[title].config(text=str(counts[key]))
        self.inventory_count.config(text=f"{counts['total']} item" + ("s" if counts["total"] != 1 else ""))

    def add_food(self):
        values = [self._value(field) for field in (self.food_entry, self.mfg_entry, self.exp_entry)]
        if not all(values):
            messagebox.showwarning("Missing details", "Add a food name and both dates to continue.")
            return
        if not self._valid_dates(values[1], values[2]):
            return
        database.insert(*values)
        self.clear_form()
        self._refresh()

    def update_food(self):
        values = [self._value(field) for field in (self.food_entry, self.mfg_entry, self.exp_entry)]
        if self.selected_id is None:
            messagebox.showwarning("No item selected", "Select an inventory item before updating it.")
            return
        if not all(values) or not self._valid_dates(values[1], values[2]):
            return
        database.update(self.selected_id, *values)
        self.clear_form()
        self._refresh()

    def delete_food(self):
        selected = self.food_table.selection()
        if not selected:
            messagebox.showwarning("No item selected", "Select an inventory item to remove it.")
            return
        if messagebox.askyesno("Remove item", "Remove this item from your pantry?"):
            database.delete(selected[0])
            self.clear_form()
            self._refresh()

    def select_item(self, _event=None):
        selected = self.food_table.selection()
        if not selected:
            return
        item = self.food_table.item(selected[0], "values")
        row = next((row for row in database.fetch() if str(row[0]) == selected[0]), None)
        if row:
            self.selected_id = row[0]
            self._set_entry(self.food_entry, row[1])
            self._set_entry(self.mfg_entry, row[2])
            self._set_entry(self.exp_entry, row[3])
            self.editor_title.config(text=f"Editing {item[0]}")

    @staticmethod
    def _set_entry(entry, value):
        entry.delete(0, tk.END)
        entry.insert(0, value)
        entry.config(fg=COLORS["ink"])

    def clear_form(self):
        self.selected_id = None
        self.editor_title.config(text="Track a food item")
        for entry, placeholder in ((self.food_entry, "e.g. Greek yogurt"), (self.mfg_entry, "DD-MM-YYYY"), (self.exp_entry, "DD-MM-YYYY")):
            entry.delete(0, tk.END)
            entry.insert(0, placeholder)
            entry.config(fg="#A0AAB3")
        self.food_table.selection_remove(self.food_table.selection())

    @staticmethod
    def _valid_dates(mfg_date, expiry_date):
        try:
            datetime.strptime(mfg_date, "%d-%m-%Y")
            datetime.strptime(expiry_date, "%d-%m-%Y")
            return True
        except ValueError:
            messagebox.showwarning("Check the dates", "Use the DD-MM-YYYY format for both dates.")
            return False


if __name__ == "__main__":
    root = tk.Tk()
    FoodExpiryApp(root)
    root.mainloop()
