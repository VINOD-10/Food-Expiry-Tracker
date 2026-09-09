import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

import database
from expiry import DISPLAY_FORMAT, format_datetime, format_remaining, get_expiry_details, parse_datetime, to_storage


COLORS = {
    "ink": "#17212B", "muted": "#6D7885", "line": "#E3E8ED",
    "paper": "#F7F8FA", "white": "#FFFFFF", "navy": "#142A3D",
    "navy_soft": "#1D3A52", "teal": "#0F8B8D", "teal_dark": "#0B6E70",
    "amber": "#C47B16", "red": "#C6534B", "green": "#2E8B68",
}
FONT = "Segoe UI"
DATE_HINT = "DD-MM-YYYY HH:MM"


class FoodExpiryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pantry | Food expiry tracker")
        self.root.geometry("1180x760")
        self.root.minsize(760, 600)
        self.root.configure(bg=COLORS["paper"])
        self.selected_id = None
        self.sidebar_compact = False
        database.connect()
        self._configure_styles()
        self._build_shell()
        self.show_page("overview")
        self._schedule_refresh()

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Food.Treeview", background=COLORS["white"], fieldbackground=COLORS["white"], foreground=COLORS["ink"], rowheight=48, borderwidth=0, font=(FONT, 10))
        style.configure("Food.Treeview.Heading", background=COLORS["white"], foreground=COLORS["muted"], font=(FONT, 9, "bold"), padding=(12, 10), relief="flat")
        style.map("Food.Treeview", background=[("selected", "#E3F2F2")], foreground=[("selected", COLORS["ink"])])
        style.configure("Food.Vertical.TScrollbar", troughcolor=COLORS["white"], background="#CBD5DD", borderwidth=0, arrowsize=12)
        style.configure("Food.TCombobox", padding=7, font=(FONT, 10))

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
        self.nav_buttons = {}
        self.nav_labels = {}
        for icon, label, route in (("⌂", "Overview", "overview"), ("□", "Inventory", "inventory"), ("◷", "Expiring soon", "expiring")):
            self._nav_item(icon, label, route).pack(fill="x", padx=12, pady=2)
        self.content = tk.Frame(self.root, bg=COLORS["paper"])
        self.content.pack(side="left", fill="both", expand=True)
        self.root.bind("<Configure>", self._responsive_sidebar)

    def _nav_item(self, icon, text, route):
        button = tk.Button(self.sidebar, text=f"  {icon}    {text}", command=lambda: self.show_page(route), anchor="w", font=(FONT, 10), fg="#B6C5D0", bg=COLORS["navy"], activebackground=COLORS["navy_soft"], activeforeground=COLORS["white"], relief="flat", bd=0, cursor="hand2", padx=12, pady=11)
        self.nav_buttons[route] = button
        self.nav_labels[route] = (icon, text)
        return button

    def _responsive_sidebar(self, _event=None):
        compact = self.root.winfo_width() < 900
        if compact == self.sidebar_compact:
            return
        self.sidebar_compact = compact
        self.sidebar.configure(width=72 if compact else 224)
        for route, button in self.nav_buttons.items():
            icon, text = self.nav_labels[route]
            button.configure(text=f"  {icon}" if compact else f"  {icon}    {text}", anchor="center" if compact else "w")

    def show_page(self, route):
        for child in self.content.winfo_children():
            child.destroy()
        for name, button in self.nav_buttons.items():
            active = name == route
            button.configure(bg=COLORS["navy_soft"] if active else COLORS["navy"], fg=COLORS["white"] if active else "#B6C5D0", font=(FONT, 10, "bold" if active else "normal"))
        self.current_route = route
        self._build_header(route)
        pages = {"overview": self._build_overview, "inventory": self._build_inventory, "expiring": self._build_expiring}
        pages[route]()

    def _build_header(self, route):
        titles = {
            "overview": ("GOOD MORNING", "Your pantry, at a glance.", "Keep food fresh and waste less."),
            "inventory": ("PANTRY", "Inventory", "Everything you are currently keeping track of."),
            "expiring": ("ATTENTION", "Expiring soon", "Dynamic alerts based on each item's total shelf life."),
        }
        eyebrow, title, subtitle = titles[route]
        header = tk.Frame(self.content, bg=COLORS["paper"])
        header.pack(fill="x", padx=42, pady=(30, 0))
        left = tk.Frame(header, bg=COLORS["paper"])
        left.pack(side="left")
        self._label(left, eyebrow, 9, COLORS["teal"], "bold").pack(anchor="w")
        self._label(left, title, 25 if route == "overview" else 22, COLORS["ink"], "bold").pack(anchor="w", pady=(5, 0))
        self._label(left, subtitle, 10, COLORS["muted"]).pack(anchor="w", pady=(5, 0))
        profile = tk.Frame(header, bg=COLORS["paper"])
        profile.pack(side="right", anchor="n")
        tk.Label(profile, text="JD", font=(FONT, 10, "bold"), fg=COLORS["navy"], bg="#D8EEEB", width=4, height=2).pack(side="left")
        tk.Label(profile, text="Jordan's pantry\nPersonal workspace", justify="left", font=(FONT, 9), fg=COLORS["muted"], bg=COLORS["paper"]).pack(side="left", padx=(10, 0))

    def _body(self):
        body = tk.Frame(self.content, bg=COLORS["paper"])
        body.pack(fill="both", expand=True, padx=42, pady=(26, 32))
        return body

    def _button(self, parent, text, command, bg, active, fg="white"):
        return tk.Button(parent, text=text, command=command, font=(FONT, 9, "bold"), fg=fg, bg=bg, activebackground=active, activeforeground=fg, relief="flat", bd=0, cursor="hand2", padx=13, pady=9)

    def _build_overview(self):
        body = self._body()
        metrics = tk.Frame(body, bg=COLORS["paper"])
        metrics.pack(fill="x", pady=(0, 24))
        self.metric_values = {}
        counts = self._counts()
        self._metric(metrics, "TOTAL ITEMS", "in your pantry", COLORS["teal"], counts["total"], lambda: self.show_page("inventory"))
        self._metric(metrics, "FRESH", "outside alert windows", COLORS["green"], counts["fresh"])
        self._metric(metrics, "EXPIRING SOON", "inside dynamic alert windows", COLORS["amber"], counts["soon"], lambda: self.show_page("expiring"))
        self._metric(metrics, "EXPIRED", "past the expiry deadline", COLORS["red"], counts["expired"], lambda: self.show_page("inventory"))
        workspace = tk.Frame(body, bg=COLORS["paper"])
        workspace.pack(fill="both", expand=True)
        workspace.columnconfigure(0, weight=1, minsize=300)
        workspace.columnconfigure(1, weight=2, minsize=420)
        workspace.rowconfigure(0, weight=1)
        self._build_editor(workspace).grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        self._build_recent_items(workspace).grid(row=0, column=1, sticky="nsew")

    def _metric(self, parent, title, subtitle, color, value, command=None):
        card = tk.Frame(parent, bg=COLORS["white"], highlightbackground=COLORS["line"], highlightthickness=1)
        card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Frame(card, bg=color, width=4).pack(side="left", fill="y")
        inner = tk.Frame(card, bg=COLORS["white"])
        inner.pack(fill="both", expand=True, padx=16, pady=14)
        self._label(inner, title, 8, COLORS["muted"], "bold").pack(anchor="w")
        value_label = tk.Label(inner, text=str(value), font=(FONT, 22, "bold"), fg=COLORS["ink"], bg=COLORS["white"])
        value_label.pack(anchor="w", pady=(5, 0))
        self.metric_values[title] = value_label
        self._label(inner, subtitle, 8, COLORS["muted"]).pack(anchor="w")
        if command:
            for widget in (card, inner, *inner.winfo_children()):
                widget.bind("<Button-1>", lambda _event: command())

    def _build_recent_items(self, parent):
        panel = tk.Frame(parent, bg=COLORS["white"], highlightbackground=COLORS["line"], highlightthickness=1)
        toolbar = tk.Frame(panel, bg=COLORS["white"])
        toolbar.pack(fill="x", padx=22, pady=(22, 16))
        title = tk.Frame(toolbar, bg=COLORS["white"])
        title.pack(side="left")
        tk.Label(title, text="Recent items", font=(FONT, 15, "bold"), fg=COLORS["ink"], bg=COLORS["white"]).pack(anchor="w")
        self._label(title, "Latest additions from your inventory", 8, COLORS["muted"]).pack(anchor="w", pady=(3, 0))
        self._button(toolbar, "View all inventory", lambda: self.show_page("inventory"), "#EEF3F5", "#DDE7EB", fg=COLORS["ink"]).pack(side="right")
        list_frame = tk.Frame(panel, bg=COLORS["white"])
        list_frame.pack(fill="both", expand=True, padx=22, pady=(0, 22))
        rows = sorted(database.fetch(), key=lambda row: row[0], reverse=True)[:5]
        if not rows:
            self._label(list_frame, "Your inventory is empty\nAdd a food item from the Overview page to start tracking it.", 10, COLORS["muted"], justify="left").pack(anchor="w", pady=24)
            return panel
        for row in rows:
            details = self._row_details(row)
            item = tk.Frame(list_frame, bg=COLORS["white"])
            item.pack(fill="x", pady=7)
            self._label(item, row[1], 10, COLORS["ink"], "bold").pack(side="left")
            self._label(item, format_remaining(details["remaining"]), 9, COLORS["muted"]).pack(side="right")
            tk.Frame(list_frame, bg=COLORS["line"], height=1).pack(fill="x", pady=(2, 0))
        return panel

    def _build_editor(self, parent):
        panel = tk.Frame(parent, bg=COLORS["white"], highlightbackground=COLORS["line"], highlightthickness=1)
        self._label(panel, "ADD TO PANTRY", 9, COLORS["teal"], "bold").pack(anchor="w", padx=24, pady=(24, 5))
        self.editor_title = self._label(panel, "Track a food item", 17, COLORS["ink"], "bold")
        self.editor_title.pack(anchor="w", padx=24)
        self._label(panel, "Dates accept DD-MM-YYYY or DD-MM-YYYY HH:MM.", 9, COLORS["muted"]).pack(anchor="w", padx=24, pady=(5, 22))
        form = tk.Frame(panel, bg=COLORS["white"])
        form.pack(fill="x", padx=24)
        self.food_entry = self._field(form, "FOOD NAME", "e.g. Greek yogurt")
        self.mfg_entry = self._field(form, "PURCHASED / MADE", DATE_HINT)
        self.exp_entry = self._field(form, "EXPIRY DATE", DATE_HINT)
        actions = tk.Frame(panel, bg=COLORS["white"])
        actions.pack(fill="x", padx=24, pady=(10, 0))
        self._button(actions, "Add item", self.add_food, COLORS["teal"], COLORS["teal_dark"]).pack(side="left", fill="x", expand=True)
        self._button(actions, "Update", self.update_food, "#EEF3F5", "#DDE7EB", fg=COLORS["ink"]).pack(side="left", padx=(8, 0))
        self._button(actions, "Clear", self.clear_form, COLORS["white"], "#EEF3F5", fg=COLORS["muted"]).pack(side="left", padx=(8, 0))
        return panel

    def _field(self, parent, label, placeholder):
        self._label(parent, label, 8, COLORS["muted"], "bold").pack(anchor="w", pady=(0, 6))
        entry = tk.Entry(parent, font=(FONT, 10), fg=COLORS["ink"], bg="#FBFCFD", relief="flat", highlightthickness=1, highlightbackground=COLORS["line"], highlightcolor=COLORS["teal"])
        entry.pack(fill="x", ipady=8, pady=(0, 14))
        entry.insert(0, placeholder)
        entry.config(fg="#A0AAB3")
        entry.bind("<FocusIn>", lambda _event: self._clear_placeholder(entry, placeholder))
        entry.bind("<FocusOut>", lambda _event: self._restore_placeholder(entry, placeholder))
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

    def _build_table_panel(self, parent, compact=False, only_expiring=False):
        panel = tk.Frame(parent, bg=COLORS["white"], highlightbackground=COLORS["line"], highlightthickness=1)
        toolbar = tk.Frame(panel, bg=COLORS["white"])
        toolbar.pack(fill="x", padx=22, pady=(20, 16))
        title = tk.Frame(toolbar, bg=COLORS["white"])
        title.pack(side="left")
        title_text = "Your inventory" if compact else ("Expiring alerts" if only_expiring else "Inventory list")
        tk.Label(title, text=title_text, font=(FONT, 15, "bold"), fg=COLORS["ink"], bg=COLORS["white"]).pack(anchor="w")
        self.inventory_count = tk.Label(title, text="", font=(FONT, 8), fg=COLORS["muted"], bg=COLORS["white"])
        self.inventory_count.pack(anchor="w", pady=(3, 0))
        search = tk.Entry(toolbar, width=20, font=(FONT, 9), relief="flat", bg="#F5F7F8", fg=COLORS["ink"], highlightthickness=1, highlightbackground=COLORS["line"])
        search.pack(side="right", ipady=7, padx=(8, 0))
        search.insert(0, "Search inventory")
        search.config(fg="#A0AAB3")
        search.bind("<FocusIn>", lambda _event: self._clear_placeholder(search, "Search inventory"))
        search.bind("<FocusOut>", lambda _event: self._restore_placeholder(search, "Search inventory"))
        self.search_entry = search
        table_wrap = tk.Frame(panel, bg=COLORS["white"])
        table_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        columns = ("name", "purchased", "expiry", "remaining", "alert", "status") if only_expiring else ("name", "purchased", "expiry", "remaining", "status")
        self.food_table = ttk.Treeview(table_wrap, columns=columns, show="headings", style="Food.Treeview", selectmode="browse")
        headings = {"name": "FOOD ITEM", "purchased": "PURCHASED / MADE", "expiry": "EXPIRY DATE / TIME", "remaining": "TIME LEFT", "alert": "ALERT LEVEL", "status": "STATUS"}
        widths = {"name": 140, "purchased": 125, "expiry": 140, "remaining": 125, "alert": 100, "status": 105}
        for column in columns:
            self.food_table.heading(column, text=headings[column], anchor="w")
            self.food_table.column(column, width=widths[column], anchor="w", stretch=column == "name")
        scrollbar = ttk.Scrollbar(table_wrap, orient="vertical", command=self.food_table.yview, style="Food.Vertical.TScrollbar")
        self.food_table.configure(yscrollcommand=scrollbar.set)
        self.food_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.empty_state = tk.Label(table_wrap, text="", font=(FONT, 11, "bold"), fg=COLORS["muted"], bg=COLORS["white"], justify="center")
        self.empty_state.place(relx=0.5, rely=0.5, anchor="center")
        for tag, color in (("fresh", COLORS["green"]), ("soon", COLORS["amber"]), ("urgent", COLORS["red"]), ("expired", COLORS["red"])):
            self.food_table.tag_configure(tag, foreground=color)
        self.food_table.bind("<<TreeviewSelect>>", self.select_item)
        self._button(panel, "Edit selected", self.edit_selected, "#EEF3F5", "#DDE7EB", fg=COLORS["ink"]).pack(side="left", padx=22, pady=(0, 18))
        self._button(panel, "Delete selected", self.delete_food, COLORS["white"], "#FDEDEC", fg=COLORS["red"]).pack(side="right", padx=22, pady=(0, 18))
        search.bind("<KeyRelease>", lambda _event: self._refresh_table(only_expiring))
        self._refresh_table(only_expiring)
        return panel

    def _build_inventory(self):
        body = self._body()
        controls = tk.Frame(body, bg=COLORS["paper"])
        controls.pack(fill="x", pady=(0, 14))
        self.filter_var = tk.StringVar(value="All statuses")
        self._label(controls, "FILTER BY STATUS", 8, COLORS["muted"], "bold").pack(side="left", padx=(0, 8))
        ttk.Combobox(controls, textvariable=self.filter_var, values=("All statuses", "Fresh", "Expiring Soon", "Urgent", "Expired"), state="readonly", width=16, style="Food.TCombobox").pack(side="left")
        self._button(controls, "Add food item", lambda: self.show_page("overview"), COLORS["teal"], COLORS["teal_dark"]).pack(side="right")
        self.filter_var.trace_add("write", lambda *_args: self._refresh_table(False))
        self._build_table_panel(body)

    def _build_expiring(self):
        body = self._body()
        self._build_table_panel(body, only_expiring=True)

    def _row_details(self, row):
        purchased = row[4] or row[2]
        expires = row[5] or row[3]
        return get_expiry_details(purchased, expires)

    def _visible_rows(self, only_expiring=False):
        rows = database.fetch()
        query = self.search_entry.get().strip().lower()
        if query and query != "search inventory":
            rows = [row for row in rows if query in row[1].lower()]
        if only_expiring:
            rows = [row for row in rows if self._row_details(row)["status"] == "Expiring Soon"]
        if hasattr(self, "filter_var") and self.current_route == "inventory" and self.filter_var.get() != "All statuses":
            target = self.filter_var.get()
            rows = [row for row in rows if self._row_details(row)["status"] == target]
        return rows

    def _refresh_table(self, only_expiring=False):
        if not hasattr(self, "food_table"):
            return
        rows = self._visible_rows(only_expiring)
        self.food_table.delete(*self.food_table.get_children())
        for row in rows:
            details = self._row_details(row)
            alert = "URGENT" if details["alert_level"] == "urgent" else ("EXPIRING SOON" if details["alert_level"] == "soon" else "")
            values = (row[1], format_datetime(details["purchased_at"]), format_datetime(details["expires_at"]), format_remaining(details["remaining"]), alert, details["status"]) if only_expiring else (row[1], format_datetime(details["purchased_at"]), format_datetime(details["expires_at"]), format_remaining(details["remaining"]), details["status"])
            self.food_table.insert("", "end", iid=str(row[0]), values=values, tags=(details["alert_level"],))
        if not rows:
            message = "Nothing is expiring soon\nItems approaching their expiry date will appear here." if only_expiring else "Your inventory is empty\nAdd a food item from the Overview page to start tracking it."
            self.empty_state.config(text=message)
            self.empty_state.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.empty_state.place_forget()
        self.inventory_count.config(text=f"{len(rows)} item" + ("s" if len(rows) != 1 else ""))

    def _counts(self):
        counts = {"total": 0, "fresh": 0, "soon": 0, "expired": 0}
        for row in database.fetch():
            counts["total"] += 1
            status = self._row_details(row)["status"]
            if status == "Fresh":
                counts["fresh"] += 1
            elif status == "Expired":
                counts["expired"] += 1
            else:
                counts["soon"] += 1
        return counts

    def _schedule_refresh(self):
        if hasattr(self, "food_table"):
            self._refresh_table(self.current_route == "expiring")
        elif self.current_route == "overview" and hasattr(self, "metric_values"):
            for title, value in (("TOTAL ITEMS", "total"), ("FRESH", "fresh"), ("EXPIRING SOON", "soon"), ("EXPIRED", "expired")):
                self.metric_values[title].config(text=str(self._counts()[value]))
        self.root.after(60000, self._schedule_refresh)

    def _value(self, entry):
        value = entry.get().strip()
        return "" if value in ("e.g. Greek yogurt", DATE_HINT, "Search inventory") else value

    def add_food(self):
        values = [self._value(field) for field in (self.food_entry, self.mfg_entry, self.exp_entry)]
        if not all(values):
            messagebox.showwarning("Missing details", "Add a food name and both dates to continue.")
            return
        try:
            purchased = parse_datetime(values[1])
            expires = parse_datetime(values[2], default_time=(23, 59))
            if expires <= purchased:
                raise ValueError("Expiry must be later")
        except ValueError:
            messagebox.showwarning("Check the dates", "Use DD-MM-YYYY or DD-MM-YYYY HH:MM, with expiry after purchase.")
            return
        database.insert(values[0], to_storage(purchased), to_storage(expires))
        self.clear_form()
        self.show_page("inventory")

    def update_food(self):
        if self.selected_id is None:
            messagebox.showwarning("No item selected", "Select an inventory item before updating it.")
            return
        values = [self._value(field) for field in (self.food_entry, self.mfg_entry, self.exp_entry)]
        try:
            purchased = parse_datetime(values[1])
            expires = parse_datetime(values[2], default_time=(23, 59))
            if not values[0] or expires <= purchased:
                raise ValueError
        except (ValueError, IndexError):
            messagebox.showwarning("Check the dates", "Use DD-MM-YYYY or DD-MM-YYYY HH:MM, with expiry after purchase.")
            return
        database.update(self.selected_id, values[0], to_storage(purchased), to_storage(expires))
        self.clear_form()
        self.show_page(self.current_route)

    def select_item(self, _event=None):
        selected = self.food_table.selection() if hasattr(self, "food_table") else ()
        self.selected_id = int(selected[0]) if selected else None

    def edit_selected(self):
        selected = self.food_table.selection() if hasattr(self, "food_table") else ()
        if not selected:
            messagebox.showwarning("No item selected", "Select an inventory item to edit it.")
            return
        row = next((item for item in database.fetch() if str(item[0]) == selected[0]), None)
        if row:
            self.selected_id = row[0]
            self.show_page("overview")
            self._set_entry(self.food_entry, row[1])
            self._set_entry(self.mfg_entry, row[4] or row[2])
            self._set_entry(self.exp_entry, row[5] or row[3])
            self.editor_title.config(text=f"Editing {row[1]}")

    def delete_food(self):
        selected = self.food_table.selection() if hasattr(self, "food_table") else ()
        if not selected:
            messagebox.showwarning("No item selected", "Select an inventory item to remove it.")
            return
        if messagebox.askyesno("Remove item", "Remove this item from your pantry?"):
            database.delete(selected[0])
            self.selected_id = None
            self.show_page(self.current_route)

    @staticmethod
    def _set_entry(entry, value):
        entry.delete(0, tk.END)
        entry.insert(0, value)
        entry.config(fg=COLORS["ink"])

    def clear_form(self):
        self.selected_id = None
        for entry, placeholder in ((self.food_entry, "e.g. Greek yogurt"), (self.mfg_entry, DATE_HINT), (self.exp_entry, DATE_HINT)):
            entry.delete(0, tk.END)
            entry.insert(0, placeholder)
            entry.config(fg="#A0AAB3")


if __name__ == "__main__":
    root = tk.Tk()
    FoodExpiryApp(root)
    root.mainloop()
