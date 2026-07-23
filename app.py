import tkinter as tk
from tkinter import messagebox
import database

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

    food_entry.delete(0, tk.END)
    mfg_entry.delete(0, tk.END)
    exp_entry.delete(0, tk.END)
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

add_btn.pack(pady=20)

root.mainloop()