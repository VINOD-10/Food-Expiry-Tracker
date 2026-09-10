import tkinter as tk
import threading
from tkinter import messagebox, ttk
from datetime import datetime

import database
from expiry import DISPLAY_FORMAT, fetch_current_time, format_datetime, format_remaining, get_expiry_details, parse_datetime, to_storage


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
        self.current_time = datetime.now()
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
        workspace.columnconfigure(0, weight=1, minsize=260)
        workspace.columnconfigure(1, weight=2, minsize=420)
        workspace.rowconfigure(0, weight=1)
        self._build_overview_add_panel(workspace).grid(row=0, column=0, sticky="nsew", padx=(0, 18))
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
            self._label(list_frame, "Your inventory is empty\nAdd a food item from the Inventory page to start tracking it.", 10, COLORS["muted"], justify="left").pack(anchor="w", pady=24)
            return panel
        for row in rows:
            details = self._row_details(row)
            item = tk.Frame(list_frame, bg=COLORS["white"])
            item.pack(fill="x", pady=7)
            self._label(item, row[1], 10, COLORS["ink"], "bold").pack(side="left")
            self._label(item, format_remaining(details["remaining"]), 9, COLORS["muted"]).pack(side="right")
            tk.Frame(list_frame, bg=COLORS["line"], height=1).pack(fill="x", pady=(2, 0))
        return panel

    def _build_overview_add_panel(self, parent):
        panel = tk.Frame(parent, bg=COLORS["white"], highlightbackground=COLORS["line"], highlightthickness=1)
        self._label(panel, "ADD TO PANTRY", 9, COLORS["teal"], "bold").pack(anchor="w", padx=24, pady=(24, 5))
        self._label(panel, "Track a food item", 17, COLORS["ink"], "bold").pack(anchor="w", padx=24)
        self._label(panel, "Add food and expiry details from the Overview page.", 9, COLORS["muted"], wraplength=250, justify="left").pack(anchor="w", padx=24, pady=(6, 22))
        tk.Frame(panel, bg=COLORS["line"], height=1).pack(fill="x", padx=24)
        self._label(panel, "Keep your pantry up to date and see the item appear in Recent items after saving.", 10, COLORS["muted"], wraplength=250, justify="left").pack(anchor="w", padx=24, pady=(22, 18))
        self._button(panel, "Add food item", self._open_food_form, COLORS["teal"], COLORS["teal_dark"]).pack(fill="x", padx=24)
        return panel

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
        canvas = tk.Canvas(table_wrap, bg=COLORS["white"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(table_wrap, orient="vertical", command=canvas.yview, style="Food.Vertical.TScrollbar")
        self.food_list = tk.Frame(canvas, bg=COLORS["white"])
        canvas_window = canvas.create_window((0, 0), window=self.food_list, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        self.food_list.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(canvas_window, width=event.width))
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.food_canvas = canvas
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
        self._button(controls, "Add food item", self._open_food_form, COLORS["teal"], COLORS["teal_dark"]).pack(side="right")
        self.filter_var.trace_add("write", lambda *_args: self._refresh_table(False))
        self._build_table_panel(body).pack(fill="both", expand=True)

    def _build_expiring(self):
        body = self._body()
        self._build_table_panel(body, only_expiring=True).pack(fill="both", expand=True)

    def _row_details(self, row):
        purchased = row[4] or row[2]
        expires = row[5] or row[3]
        return get_expiry_details(purchased, expires, now=self.current_time)

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
        if not hasattr(self, "food_list"):
            return
        rows = self._visible_rows(only_expiring)
        for child in self.food_list.winfo_children():
            child.destroy()
        headings = ("FOOD ITEM", "PURCHASED / MADE", "EXPIRY DATE / TIME", "TIME LEFT", "STATUS")
        if not only_expiring:
            headings += ("ACTIONS",)
        for column, heading in enumerate(headings):
            self._label(self.food_list, heading, 8, COLORS["muted"], "bold").grid(row=0, column=column, sticky="w", padx=8, pady=(4, 10))
        self.food_list.columnconfigure(0, weight=2)
        for column in range(1, len(headings)):
            self.food_list.columnconfigure(column, weight=1)
        for row_number, row in enumerate(rows, start=1):
            details = self._row_details(row)
            item_row = tk.Frame(self.food_list, bg=COLORS["white"])
            item_row.grid(row=row_number * 2 - 1, column=0, columnspan=len(headings), sticky="ew")
            item_row.columnconfigure(0, weight=2)
            for column in range(1, len(headings)):
                item_row.columnconfigure(column, weight=1)
            values = (row[1], format_datetime(details["purchased_at"]), format_datetime(details["expires_at"]), format_remaining(details["remaining"]), details["status"])
            status_color = COLORS["red"] if details["alert_level"] in ("urgent", "expired") else (COLORS["amber"] if details["alert_level"] == "soon" else COLORS["green"])
            for column, value in enumerate(values):
                self._label(item_row, value, 9, status_color if column == 4 else COLORS["ink"], "bold" if column in (0, 4) else "normal").grid(row=0, column=column, sticky="w", padx=8, pady=12)
            if not only_expiring:
                actions = tk.Frame(item_row, bg=COLORS["white"])
                actions.grid(row=0, column=5, sticky="e", padx=8)
                self._button(actions, "Edit", lambda food_row=row: self._open_food_form(food_row), "#2F80ED", "#2169C7").pack(side="left", padx=(0, 5), pady=2)
                self._button(actions, "Delete", lambda food_id=row[0]: self._delete_item(food_id), COLORS["red"], "#A93E37").pack(side="left", pady=2)
            tk.Frame(self.food_list, bg=COLORS["line"], height=1).grid(row=row_number * 2, column=0, columnspan=len(headings), sticky="ew")
        if not rows:
            message = "Nothing is expiring soon\nItems approaching their expiry date will appear here." if only_expiring else "Your inventory is empty\nAdd a food item from the Inventory page to start tracking it."
            self._label(self.food_list, message, 11, COLORS["muted"], "bold", justify="center").grid(row=1, column=0, columnspan=len(headings), pady=40)
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
        if hasattr(self, "food_list"):
            self._refresh_table(self.current_route == "expiring")
        elif self.current_route == "overview" and hasattr(self, "metric_values"):
            for title, value in (("TOTAL ITEMS", "total"), ("FRESH", "fresh"), ("EXPIRING SOON", "soon"), ("EXPIRED", "expired")):
                self.metric_values[title].config(text=str(self._counts()[value]))
        self._sync_current_time()
        self.root.after(60000, self._schedule_refresh)

    def _sync_current_time(self):
        def fetch_time():
            current_time = fetch_current_time()
            if current_time is not None:
                self.root.after(0, lambda: self._set_current_time(current_time))

        threading.Thread(target=fetch_time, daemon=True).start()

    def _set_current_time(self, current_time):
        self.current_time = current_time
        if hasattr(self, "food_list"):
            self._refresh_table(self.current_route == "expiring")
        elif self.current_route == "overview" and hasattr(self, "metric_values"):
            for title, value in (("TOTAL ITEMS", "total"), ("FRESH", "fresh"), ("EXPIRING SOON", "soon"), ("EXPIRED", "expired")):
                self.metric_values[title].config(text=str(self._counts()[value]))

    def _value(self, entry):
        value = entry.get().strip()
        return "" if value in ("e.g. Greek yogurt", DATE_HINT, "Search inventory") else value

    def _open_food_form(self, row=None):
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit food item" if row else "Add food item")
        dialog.geometry("390x330")
        dialog.resizable(False, False)
        dialog.configure(bg=COLORS["white"])
        dialog.transient(self.root)
        dialog.grab_set()
        self._label(dialog, "EDIT FOOD ITEM" if row else "ADD FOOD ITEM", 9, COLORS["teal"], "bold").pack(anchor="w", padx=26, pady=(24, 5))
        self._label(dialog, "Update the details below.", 16, COLORS["ink"], "bold").pack(anchor="w", padx=26, pady=(0, 18))
        form = tk.Frame(dialog, bg=COLORS["white"])
        form.pack(fill="x", padx=26)
        self._label(form, "FOOD NAME", 8, COLORS["muted"], "bold").pack(anchor="w")
        name_entry = tk.Entry(form, font=(FONT, 10), fg=COLORS["ink"], bg="#FBFCFD", relief="flat", highlightthickness=1, highlightbackground=COLORS["line"])
        name_entry.pack(fill="x", ipady=8, pady=(6, 12))
        self._label(form, "PURCHASED / MADE", 8, COLORS["muted"], "bold").pack(anchor="w")
        purchased_entry = tk.Entry(form, font=(FONT, 10), fg=COLORS["ink"], bg="#FBFCFD", relief="flat", highlightthickness=1, highlightbackground=COLORS["line"])
        purchased_entry.pack(fill="x", ipady=8, pady=(6, 12))
        self._label(form, "EXPIRY DATE", 8, COLORS["muted"], "bold").pack(anchor="w")
        expiry_entry = tk.Entry(form, font=(FONT, 10), fg=COLORS["ink"], bg="#FBFCFD", relief="flat", highlightthickness=1, highlightbackground=COLORS["line"])
        expiry_entry.pack(fill="x", ipady=8, pady=(6, 12))
        if row:
            purchased_entry.insert(0, format_datetime(row[4] or row[2]))
            purchased_entry.config(state="disabled")
            name_entry.insert(0, row[1])
            expiry_entry.insert(0, format_datetime(row[5] or row[3]))
        actions = tk.Frame(dialog, bg=COLORS["white"])
        actions.pack(fill="x", padx=26, pady=(4, 20))
        self._button(actions, "Save changes" if row else "Add item", lambda: self._save_food_form(dialog, row, name_entry, purchased_entry, expiry_entry), COLORS["teal"], COLORS["teal_dark"]).pack(side="left", fill="x", expand=True)
        self._button(actions, "Cancel", dialog.destroy, "#EEF3F5", "#DDE7EB", fg=COLORS["ink"]).pack(side="left", padx=(8, 0))

    def _save_food_form(self, dialog, row, name_entry, purchased_entry, expiry_entry):
        name = name_entry.get().strip()
        purchased_value = purchased_entry.get().strip()
        expiry_value = expiry_entry.get().strip()
        try:
            purchased = parse_datetime(purchased_value)
            expires = parse_datetime(expiry_value, default_time=(23, 59))
            if not name or expires <= purchased:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Check the dates", "Use DD-MM-YYYY or DD-MM-YYYY HH:MM, with expiry after purchase.", parent=dialog)
            return
        if row:
            database.update(row[0], name, to_storage(purchased), to_storage(expires))
            message = "Food item updated successfully."
        else:
            database.insert(name, to_storage(purchased), to_storage(expires))
            message = "Food item added successfully."
        dialog.destroy()
        self.show_page("inventory")
        messagebox.showinfo("Success", message)

    def _delete_item(self, food_id):
        if not messagebox.askyesno("Remove item", "Are you sure you want to delete this food item?"):
            return
        database.delete(food_id)
        self._refresh_table(self.current_route == "expiring")
        messagebox.showinfo("Deleted", "Food item deleted successfully.")

if __name__ == "__main__":
    root = tk.Tk()
    FoodExpiryApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        root.destroy()
