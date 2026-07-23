import tkinter as tk
from tkinter import messagebox
import database
from datetime import datetime

# Create main window
root = tk.Tk()
database.connect()
root.title("Food Expiry Tracker")
root.geometry("500x400")
root.configure(bg="#F5F5F5")

# Heading
heading = tk.Label(
    root,
    text="Food Expiry Tracker",
    font=("Arial", 18, "bold"),
    bg="#F5F5F5",
    fg="#2E4053"
)
heading.pack(pady=20)

# Frame
frame = tk.Frame(root, bg="#F5F5F5")
frame.pack()

# Food Name
tk.Label(frame, text="Food Name", bg="#F5F5F5").grid(row=0, column=0, padx=10, pady=10, sticky="w")
food_entry = tk.Entry(frame, width=30)
food_entry.grid(row=0, column=1)

# Manufacturing Date
tk.Label(frame, text="Manufacturing Date", bg="#F5F5F5").grid(row=1, column=0, padx=10, pady=10, sticky="w")
mfg_entry = tk.Entry(frame, width=30)
mfg_entry.grid(row=1, column=1)

# Expiry Date
tk.Label(frame, text="Expiry Date", bg="#F5F5F5").grid(row=2, column=0, padx=10, pady=10, sticky="w")
exp_entry = tk.Entry(frame, width=30)
exp_entry.grid(row=2, column=1)
def add_food():

    food_name = food_entry.get()
    mfg_date = mfg_entry.get()
    exp_date = exp_entry.get()

    if food_name == "" or mfg_date == "" or exp_date == "":
        messagebox.showwarning("Warning", "Please fill all fields")
        return
    database.insert(
    food_name,
    mfg_date,
    exp_date
)
    messagebox.showinfo("Success", "Food Added Successfully!")
tk.Label(root, text="Search Food", bg="#F5F5F5").pack(pady=5)

search_entry = tk.Entry(root, width=30)
search_entry.pack()
def show_food():

    food_list.delete(0, tk.END)

    rows = database.fetch()

    today = datetime.today()

    for row in rows:

        expiry = datetime.strptime(row[3], "%d-%m-%Y")

        days_left = (expiry - today).days

        if days_left < 0:
            status = "❌ Expired"

        elif days_left <= 3:
            status = "🟡 Expiring Soon"

        else:
            status = "🟢 Safe"

        food_list.insert(
            tk.END,
            f"{row[1]} | Exp: {row[3]} | {days_left} Days | {status}"
        )

    food_entry.delete(0, tk.END)
    mfg_entry.delete(0, tk.END)
    exp_entry.delete(0, tk.END)
def search_food():

    food_list.delete(0, tk.END)

    rows = database.search(search_entry.get())

    for row in rows:

        food_list.insert(
            tk.END,
            f"ID:{row[0]} | {row[1]} | EXP:{row[3]}"
        )
def delete_food():

    selected = food_list.curselection()

    if not selected:
        messagebox.showwarning(
            "Warning",
            "Please select a food item."
        )
        return

    item = food_list.get(selected[0])

    food_id = int(
        item.split("|")[0]
            .replace("ID:", "")
            .strip()
    )

    database.delete(food_id)

    show_food()

    messagebox.showinfo(
        "Deleted",
        "Food deleted successfully!"
    )
# Button
add_btn = tk.Button(
    root,
    text="Add Food",
    command=add_food,
    width=15,
    bg="#4CAF50",
    fg="white",
    font=("Arial", 10, "bold")
)
search_btn = tk.Button(
    root,
    text="Search",
    command=search_food,
    width=15,
    bg="#2196F3",
    fg="white",
    font=("Arial", 10, "bold")
)

search_btn.pack(pady=5)
delete_btn = tk.Button(
    root,
    text="Delete Selected",
    command=delete_food,
    width=18,
    bg="red",
    fg="white",
    font=("Arial", 10, "bold")
)

delete_btn.pack(pady=5)
add_btn.pack(pady=20)
# -----------------------------
# Food List Label
# -----------------------------
tk.Label(
    root,
    text="Saved Food Items",
    bg="#F5F5F5",
    font=("Arial", 12, "bold")
).pack()

# -----------------------------
# Listbox
# -----------------------------
food_list = tk.Listbox(
    root,
    width=60,
    height=8,
    font=("Arial",10)
)

food_list.pack(pady=10)
show_food()
root.mainloop()