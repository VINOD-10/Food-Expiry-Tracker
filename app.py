import tkinter as tk
from tkinter import ttk, messagebox
import database
from datetime import datetime

# -----------------------
# Setup
# -----------------------
root = tk.Tk()
root.title("Food Expiry Tracker")
root.geometry("800x600")
root.configure(bg="#ECF0F1")

database.connect()
selected_id = None

# -----------------------
# Heading
# -----------------------
tk.Label(
    root,
    text="🍱 Food Expiry Tracker",
    font=("Segoe UI", 22, "bold"),
    bg="#ECF0F1",
    fg="#2C3E50"
).pack(pady=15)

# -----------------------
# Form Section
# -----------------------
form_frame = tk.Frame(root, bg="white", bd=2, relief="groove")
form_frame.pack(padx=20, pady=10, fill="x")

tk.Label(form_frame, text="Food Name", bg="white").grid(row=0, column=0, padx=10, pady=10)
food_entry = tk.Entry(form_frame, width=25)
food_entry.grid(row=0, column=1)

tk.Label(form_frame, text="MFG Date (DD-MM-YYYY)", bg="white").grid(row=1, column=0, padx=10)
mfg_entry = tk.Entry(form_frame)
mfg_entry.grid(row=1, column=1)

tk.Label(form_frame, text="Expiry Date (DD-MM-YYYY)", bg="white").grid(row=2, column=0, padx=10)
exp_entry = tk.Entry(form_frame)
exp_entry.grid(row=2, column=1)

# -----------------------
# Buttons
# -----------------------
btn_frame = tk.Frame(root, bg="#ECF0F1")
btn_frame.pack(pady=10)

# -----------------------
# Search
# -----------------------
search_frame = tk.Frame(root, bg="#ECF0F1")
search_frame.pack(pady=5)

tk.Label(search_frame, text="Search:", bg="#ECF0F1").pack(side="left")
search_entry = tk.Entry(search_frame, width=30)
search_entry.pack(side="left", padx=10)

# -----------------------
# Table Style
# -----------------------
style = ttk.Style()
style.theme_use("default")

style.configure("Treeview",
    background="white",
    foreground="black",
    rowheight=28,
    fieldbackground="white"
)

style.map("Treeview", background=[("selected", "#2980B9")])

# -----------------------
# Table
# -----------------------
food_table = ttk.Treeview(
    root,
    columns=("ID", "Name", "Expiry", "Days", "Status"),
    show="headings"
)

for col in ("ID", "Name", "Expiry", "Days", "Status"):
    food_table.heading(col, text=col)
    food_table.column(col, anchor="center", width=120)

food_table.pack(padx=20, pady=10, fill="both", expand=True)

# Scrollbar
scrollbar = tk.Scrollbar(food_table)
scrollbar.pack(side="right", fill="y")
food_table.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=food_table.yview)

# Status colors
food_table.tag_configure("safe", foreground="#27AE60")
food_table.tag_configure("soon", foreground="#F39C12")
food_table.tag_configure("expired", foreground="#E74C3C")

# -----------------------
# Functions
# -----------------------
def show_food():
    food_table.delete(*food_table.get_children())
    rows = database.fetch()
    today = datetime.now()

    for row in rows:
        try:
            expiry = datetime.strptime(row[3], "%d-%m-%Y")
            days_left = (expiry - today).days

            if days_left < 0:
                status = "❌ Expired"
                tag = "expired"
            elif days_left <= 3:
                status = "🟡 Expiring Soon"
                tag = "soon"
            else:
                status = "🟢 Safe"
                tag = "safe"

            food_table.insert("", "end",
                values=(row[0], row[1], row[3], days_left, status),
                tags=(tag,)
            )

        except:
            food_table.insert("", "end",
                values=(row[0], row[1], row[3], "-", "Invalid")
            )

def add_food():
    if not food_entry.get() or not mfg_entry.get() or not exp_entry.get():
        messagebox.showwarning("Warning", "Fill all fields")
        return

    database.insert(food_entry.get(), mfg_entry.get(), exp_entry.get())
    show_food()

def select_item(event):
    global selected_id
    selected = food_table.focus()

    if selected:
        values = food_table.item(selected, "values")
        selected_id = values[0]

        food_entry.delete(0, tk.END)
        food_entry.insert(0, values[1])

        exp_entry.delete(0, tk.END)
        exp_entry.insert(0, values[2])

def delete_food():
    selected = food_table.focus()
    if not selected:
        messagebox.showwarning("Warning", "Select item")
        return

    values = food_table.item(selected, "values")
    database.delete(values[0])
    show_food()

def update_food():
    global selected_id

    if selected_id is None:
        messagebox.showwarning("Warning", "Select item first")
        return

    database.update(
        selected_id,
        food_entry.get(),
        mfg_entry.get(),
        exp_entry.get()
    )

    show_food()

def search_food():
    food_table.delete(*food_table.get_children())
    rows = database.search(search_entry.get())

    for row in rows:
        food_table.insert("", "end",
            values=(row[0], row[1], row[3], "-", "Search")
        )

# -----------------------
# Bind
# -----------------------
food_table.bind("<<TreeviewSelect>>", select_item)

# -----------------------
# Buttons (after functions)
# -----------------------
tk.Button(btn_frame, text="Add", bg="#27AE60", fg="white", width=12, command=add_food).grid(row=0, column=0, padx=5)
tk.Button(btn_frame, text="Update", bg="#F39C12", fg="white", width=12, command=update_food).grid(row=0, column=1, padx=5)
tk.Button(btn_frame, text="Delete", bg="#E74C3C", fg="white", width=12, command=delete_food).grid(row=0, column=2, padx=5)
tk.Button(btn_frame, text="Search", bg="#3498DB", fg="white", width=12, command=search_food).grid(row=0, column=3, padx=5)

# -----------------------
# Start
# -----------------------
show_food()
root.mainloop()