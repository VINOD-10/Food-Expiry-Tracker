import tkinter as tk
from tkinter import ttk, messagebox
import database
from datetime import datetime

# -----------------------
# Setup
# -----------------------
root = tk.Tk()
root.title("Food Expiry Tracker")
root.geometry("850x720")
root.minsize(700, 620)
root.configure(bg="#F4F7FB")

database.connect()
selected_id = None

# -----------------------
# Heading
# -----------------------
tk.Label(
    root,
    text="Food Expiry Tracker",
    font=("Segoe UI", 22, "bold"),
    bg="#F4F7FB",
    fg="#1F3A5F"
).pack(pady=(18, 12))

# -----------------------
# Form Section
form_frame = tk.Frame(root, bg="white", bd=1, relief="solid")
form_frame.pack(padx=24, pady=8, fill="x")

# Make columns flexible
form_frame.columnconfigure(0, weight=1)
form_frame.columnconfigure(1, weight=2)

# Food Name
tk.Label(
    form_frame,
    text="Food Name",
    bg="white",
    fg="#34495E",
    font=("Segoe UI", 10, "bold")
).grid(row=0, column=0, sticky="e", padx=(18, 10), pady=10)

food_entry = tk.Entry(form_frame, width=30, bg="#F1F4F8", fg="#273746", relief="solid", bd=1)
food_entry.grid(row=0, column=1, sticky="ew", padx=(0, 18), pady=10)

# MFG Date
tk.Label(
    form_frame,
    text="MFG Date (DD-MM-YYYY)",
    bg="white",
    fg="#34495E",
    font=("Segoe UI", 10, "bold")
).grid(row=1, column=0, sticky="e", padx=(18, 10), pady=10)

mfg_entry = tk.Entry(form_frame, width=30, bg="#F1F4F8", fg="#273746", relief="solid", bd=1)
mfg_entry.grid(row=1, column=1, sticky="ew", padx=(0, 18), pady=10)

# Expiry Date
tk.Label(
    form_frame,
    text="Expiry Date (DD-MM-YYYY)",
    bg="white",
    fg="#34495E",
    font=("Segoe UI", 10, "bold")
).grid(row=2, column=0, sticky="e", padx=(18, 10), pady=10)

exp_entry = tk.Entry(form_frame, width=30, bg="#F1F4F8", fg="#273746", relief="solid", bd=1)
exp_entry.grid(row=2, column=1, sticky="ew", padx=(0, 18), pady=10)

# -----------------------
# Buttons
# -----------------------
btn_frame = tk.Frame(root, bg="#F4F7FB")
btn_frame.pack(pady=(12, 8))

# -----------------------
# Search
# -----------------------
search_frame = tk.Frame(root, bg="#F4F7FB")
search_frame.pack(pady=(0, 8))

tk.Label(search_frame, text="Search", bg="#F4F7FB", fg="#34495E", font=("Segoe UI", 10, "bold")).pack(side="left")
search_entry = tk.Entry(search_frame, width=30, bg="white", fg="#273746", relief="solid", bd=1)
search_entry.pack(side="left", padx=10)

# -----------------------
# Table Style
# -----------------------
style = ttk.Style()
style.theme_use("default")

style.configure("Treeview",
    background="white",
    foreground="#273746",
    rowheight=30,
    fieldbackground="white",
    font=("Segoe UI", 10)
)

style.configure("Treeview.Heading",
    background="#1F3A5F",
    foreground="white",
    font=("Segoe UI", 10, "bold"),
    padding=(8, 7)
)
style.map("Treeview", background=[("selected", "#2F7D7A")])
style.map("Treeview.Heading", background=[("active", "#294D73")])

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

food_table.pack(padx=24, pady=(4, 18), fill="both", expand=True)

# Scrollbar
scrollbar = tk.Scrollbar(food_table)
scrollbar.pack(side="right", fill="y")
food_table.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=food_table.yview)

# -----------------------
# Recipe Chatbox
# -----------------------
chat_frame = tk.Frame(root, bg="#102A43", bd=0)
chat_frame.pack(padx=24, pady=(0, 18), fill="x")

chat_header = tk.Frame(chat_frame, bg="#102A43")
chat_header.pack(fill="x", padx=16, pady=(12, 4))

tk.Label(
    chat_header,
    text="Recipe studio",
    bg="#102A43",
    fg="white",
    font=("Segoe UI", 14, "bold")
).pack(side="left")

chat_api_status = tk.Label(
    chat_header,
    text="LOCAL RECIPES",
    bg="#2F7D7A",
    fg="white",
    font=("Segoe UI", 8, "bold"),
    padx=8,
    pady=3
)
chat_api_status.pack(side="left", padx=10)

tk.Button(
    chat_header,
    text="Clear",
    command=lambda: chat_history.delete("1.0", tk.END),
    bg="#294D73",
    fg="white",
    activebackground="#3B6F9E",
    relief="flat",
    bd=0,
    cursor="hand2",
    padx=10,
    pady=3
).pack(side="right")

tk.Label(
    chat_frame,
    text="Use an ingredient, cuisine, or dietary idea. Recipes are matched to food already in your tracker.",
    bg="#102A43",
    fg="#C9D7E6",
    font=("Segoe UI", 9)
).pack(anchor="w", padx=16, pady=(0, 8))

suggestion_frame = tk.Frame(chat_frame, bg="#102A43")
suggestion_frame.pack(fill="x", padx=16, pady=(0, 8))

suggestion_title = tk.Label(
    suggestion_frame,
    text="IN YOUR INVENTORY",
    bg="#102A43",
    fg="#7DD3C7",
    font=("Segoe UI", 8, "bold")
)
suggestion_title.pack(anchor="w")

suggestion_buttons = tk.Frame(suggestion_frame, bg="#102A43")
suggestion_buttons.pack(fill="x", pady=(4, 0))

chat_body = tk.Frame(chat_frame, bg="#F8FAFC")
chat_body.pack(fill="x", padx=12, pady=(0, 8))

chat_history = tk.Text(
    chat_body,
    height=9,
    wrap="word",
    state="normal",
    bg="#F8FAFC",
    fg="#273746",
    relief="flat",
    bd=0,
    padx=10,
    pady=8,
    font=("Segoe UI", 9)
)
chat_history.pack(side="left", fill="both", expand=True)

chat_scrollbar = tk.Scrollbar(chat_body, command=chat_history.yview)
chat_scrollbar.pack(side="right", fill="y")
chat_history.config(yscrollcommand=chat_scrollbar.set)

chat_input_frame = tk.Frame(chat_frame, bg="#102A43")
chat_input_frame.pack(fill="x", padx=16, pady=(0, 12))

chat_entry = tk.Entry(
    chat_input_frame,
    bg="white",
    fg="#273746",
    relief="flat",
    bd=0,
    font=("Segoe UI", 10)
)
chat_entry.pack(side="left", fill="x", expand=True, ipady=8)


def add_chat_message(sender, message):
    chat_history.insert(tk.END, f"{sender}: {message}\n\n")
    chat_history.see(tk.END)


def choose_inventory_food(food_name):
    chat_entry.delete(0, tk.END)
    chat_entry.insert(0, food_name)
    ask_recipe_assistant()


def refresh_inventory_suggestions():
    for button in suggestion_buttons.winfo_children():
        button.destroy()

    names = []
    for row in database.fetch():
        food_name = row[1].strip()
        if food_name and food_name.lower() not in [name.lower() for name in names]:
            names.append(food_name)

    if not names:
        suggestion_title.config(text="IN YOUR INVENTORY • ADD FOOD TO SEE SUGGESTIONS")
        return

    suggestion_title.config(text="IN YOUR INVENTORY • CLICK FOR A RECIPE")
    for index, food_name in enumerate(names):
        tk.Button(
            suggestion_buttons,
            text=food_name,
            command=lambda name=food_name: choose_inventory_food(name),
            bg="#1E4D68",
            fg="white",
            activebackground="#2F7D7A",
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=9,
            pady=3
        ).grid(row=index // 6, column=index % 6, padx=(0, 6), pady=(0, 4), sticky="w")


def recipe_for(food_name):
    name = food_name.lower()
    recipes = {
        "banana": "Banana pancakes (2 servings): mix 2 ripe bananas, 2 eggs, 120 g flour, 120 ml milk, 1 tsp baking powder and a pinch of salt; cook 2 tbsp batter per pancake in a lightly oiled pan for 2 minutes per side.",
        "bread": "Garlic bread (4 servings): mix 60 g softened butter, 2 minced garlic cloves and 1 tbsp chopped herbs; spread on 4 slices and bake at 200 C for 8-10 minutes.",
        "tomato": "Tomato pasta (2 servings): cook 180 g pasta; fry 1 tbsp oil with 1 chopped onion and 2 garlic cloves, add 400 g tomatoes, 1 tsp salt and 1/2 tsp pepper, simmer 15 minutes, then mix with pasta.",
        "potato": "Roasted potatoes (2 servings): toss 500 g cubed potatoes with 2 tbsp oil, 1 tsp salt, 1/2 tsp pepper and 1/2 tsp paprika; roast at 220 C for 30-40 minutes, turning once.",
        "apple": "Apple crumble (4 servings): mix 4 sliced apples with 2 tbsp sugar and 1 tsp cinnamon; cover with 80 g flour, 60 g oats, 60 g butter and 50 g sugar; bake at 180 C for 35 minutes.",
        "milk": "Milk pancakes (2 servings): whisk 1 cup flour, 1 cup milk, 1 egg, 1 tbsp sugar, 1 tsp baking powder and a pinch of salt; cook 60 ml batter per pancake for 2 minutes per side.",
        "rice": "Vegetable fried rice (2 servings): stir-fry 2 tbsp oil, 1 chopped onion and 2 cups cooked rice; add 1 cup chopped vegetables, 1 tbsp soy sauce and 1 beaten egg, then cook 5-7 minutes.",
        "pasta": "Quick pasta (2 servings): boil 180 g pasta; saute 2 tbsp oil, 2 garlic cloves and 250 g chopped vegetables, add 100 ml pasta water and mix with the drained pasta.",
        "carrot": "Carrot soup (4 servings): saute 1 onion in 1 tbsp oil, add 500 g sliced carrots, 750 ml stock, 1/2 tsp salt and 1/4 tsp pepper; simmer 25 minutes and blend.",
        "onion": "Caramelized onion toast (2 servings): cook 2 sliced onions with 1 tbsp oil and a pinch of salt for 20 minutes; add 1 tsp vinegar, then serve on 2 toasted bread slices.",
        "spinach": "Spinach omelette (1 serving): whisk 2 eggs with 1 tbsp milk and a pinch of salt; cook with 1 cup spinach and 1 tsp oil for 3-4 minutes.",
        "cabbage": "Cabbage stir-fry (2 servings): fry 1 tbsp oil, 1 garlic clove and 300 g sliced cabbage; add 1 tbsp soy sauce and cook 6-8 minutes.",
        "broccoli": "Broccoli pasta (2 servings): steam 250 g broccoli; toss with 180 g cooked pasta, 2 tbsp olive oil, 1 garlic clove, 30 g cheese and 1/2 tsp pepper.",
        "beans": "Bean curry (3 servings): fry 1 onion with 1 tbsp oil, add 1 tsp curry powder and 400 g cooked beans, 200 g tomatoes and 150 ml water; simmer 15 minutes.",
        "lentil": "Lentil soup (4 servings): simmer 200 g lentils, 1 chopped onion, 1 carrot, 1 tomato, 1 litre stock, 1 tsp cumin and 1/2 tsp salt for 30 minutes.",
        "chickpea": "Chickpea salad (2 servings): combine 400 g cooked chickpeas, 1 chopped tomato, 1/2 cucumber, 2 tbsp lemon juice, 1 tbsp oil, 1/2 tsp salt and herbs.",
        "chicken": "Chicken stir-fry (2 servings): cook 300 g sliced chicken in 1 tbsp oil for 6-8 minutes; add 2 cups vegetables, 1 tbsp soy sauce and 2 tbsp water, then cook 5 minutes more.",
        "beef": "Beef vegetable stew (4 servings): brown 500 g beef in 1 tbsp oil; add 1 onion, 2 carrots, 500 ml stock, 1 tsp salt and 1/2 tsp pepper; cover and simmer 60 minutes.",
        "fish": "Baked fish (2 servings): place 400 g fish with 1 tbsp oil, 1 tbsp lemon juice, 1/2 tsp salt, 1/4 tsp pepper and herbs; bake at 200 C for 12-15 minutes.",
        "salmon": "Baked salmon (2 servings): season 400 g salmon with 1 tbsp oil, 1 tbsp lemon juice, 1/2 tsp salt and 1/4 tsp pepper; bake at 200 C for 12-15 minutes.",
        "egg": "Vegetable omelette (1 serving): whisk 2 eggs with 1 tbsp milk and 1/4 tsp salt; cook with 1/2 cup chopped vegetables in 1 tsp oil for 3-4 minutes.",
        "cheese": "Cheese toast (2 servings): place 2 cheese slices and 1/2 cup chopped vegetables on 2 bread slices; grill at 200 C for 5-7 minutes until melted.",
        "yogurt": "Yogurt dip (2 servings): mix 200 g yogurt, 1 minced garlic clove, 1 tbsp lemon juice, 1/4 tsp salt and 1 tbsp herbs; chill for 10 minutes.",
        "mushroom": "Mushroom stir-fry (2 servings): cook 300 g sliced mushrooms with 1 tbsp butter, 1 minced garlic clove, 1/2 tsp salt and 1/4 tsp pepper for 8-10 minutes.",
        "corn": "Corn fritters (2 servings): mix 1 cup corn, 1 egg, 60 g flour, 2 tbsp milk, 1/4 tsp salt and pepper; fry 2 tbsp portions in 1 tbsp oil for 2 minutes per side.",
        "cucumber": "Cucumber raita (2 servings): mix 200 g yogurt, 1 grated cucumber, 1/4 tsp salt, 1/4 tsp cumin and 1 tbsp herbs; chill for 15 minutes.",
        "orange": "Orange smoothie (2 servings): blend 2 peeled oranges, 1 banana, 200 ml yogurt or milk and 1 tsp honey until smooth.",
        "mango": "Mango smoothie (2 servings): blend 1 chopped mango, 200 ml milk or yogurt, 1 tsp honey and 4 ice cubes.",
        "strawberry": "Strawberry smoothie (2 servings): blend 250 g strawberries, 200 ml milk or yogurt, 1 banana and 1 tsp honey.",
        "flour": "Simple flatbread (4 pieces): mix 200 g flour, 120 ml water, 1/2 tsp salt and 1 tsp oil; knead 5 minutes, rest 15 minutes, roll and cook 2 minutes per side.",
        "oats": "Overnight oats (1 serving): mix 50 g oats, 150 ml milk, 100 g yogurt, 1 tsp honey and fruit; refrigerate at least 4 hours.",
        "tofu": "Crispy tofu (2 servings): toss 300 g cubed tofu with 1 tbsp oil, 1 tbsp soy sauce and 1 tbsp cornflour; bake at 220 C for 20-25 minutes.",
        "avocado": "Avocado toast (2 servings): mash 1 avocado with 1 tbsp lemon juice, 1/4 tsp salt and pepper; spread on 2 toasted bread slices.",
    }

    if name in {"help", "how", "usage", "api"} or "how to use" in name:
        return "Use the chatbox by typing one food name, for example banana, rice, chicken or tomato, then press Ask or Enter. This app currently uses a local Python recipe catalog, so it needs no API key or internet connection."

    for ingredient, recipe in recipes.items():
        if ingredient in name:
            return recipe

    return f"{food_name.title()} base recipe (2 servings): use 300 g of the food, 1 tbsp oil, 1 chopped onion, 2 garlic cloves, 1/2 tsp salt, 1/4 tsp pepper and 250 ml stock; saute onion and garlic for 3 minutes, add the food and stock, cover and cook until tender. Add water for soup, cooked rice for a bowl, or pasta for a complete meal."


def get_expiring_foods():
    today = datetime.now().date()
    foods = []

    for row in database.fetch():
        try:
            expiry = datetime.strptime(row[3], "%d-%m-%Y").date()
        except ValueError:
            continue

        days_from_today = (expiry - today).days
        if -7 <= days_from_today <= 7:
            foods.append((row[1], days_from_today))

    return foods


def refresh_recipe_suggestions():
    chat_history.delete("1.0", tk.END)
    refresh_inventory_suggestions()

    foods = get_expiring_foods()
    if not foods:
        add_chat_message("Assistant", "No food is expired within the last 7 days or expiring in the next 7 days.")
        return

    add_chat_message("Assistant", "I found these items that need attention:")
    for food_name, days_from_today in foods:
        if days_from_today < 0:
            add_chat_message(
                "Assistant",
                f"{food_name} expired {abs(days_from_today)} day(s) ago. Do not cook with it unless you have confirmed it is safe; when in doubt, discard it."
            )
        elif days_from_today == 0:
            add_chat_message("Assistant", f"{food_name} expires today. If it is fresh and safely stored, {recipe_for(food_name)}")
        else:
            add_chat_message("Assistant", f"{food_name} expires in {days_from_today} day(s). Use it soon: {recipe_for(food_name)}")


def ask_recipe_assistant(event=None):
    food_name = chat_entry.get().strip()
    if not food_name:
        return

    add_chat_message("You", food_name)

    inventory_names = [row[1].strip() for row in database.fetch() if row[1].strip()]
    query = food_name.lower()
    matching_food = any(
        query in inventory_name.lower() or inventory_name.lower() in query
        for inventory_name in inventory_names
    )

    if not matching_food:
        add_chat_message(
            "Assistant",
            f"No food item found in the database for '{food_name}'. Add it to your food tracker first, then ask for a recipe."
        )
        chat_entry.delete(0, tk.END)
        return

    add_chat_message("Assistant", recipe_for(food_name))
    chat_entry.delete(0, tk.END)


tk.Button(
    chat_input_frame,
    text="Ask",
    bg="#2F7D7A",
    activebackground="#256461",
    activeforeground="white",
    fg="white",
    width=12,
    font=("Segoe UI", 10, "bold"),
    relief="flat",
    bd=0,
    cursor="hand2",
    pady=6,
    command=ask_recipe_assistant
).pack(side="left", padx=(8, 0))
chat_entry.bind("<Return>", ask_recipe_assistant)

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
            elif days_left <= 7:
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

    refresh_recipe_suggestions()

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
button_style = {
    "fg": "white",
    "width": 12,
    "font": ("Segoe UI", 10, "bold"),
    "relief": "flat",
    "bd": 0,
    "cursor": "hand2",
    "pady": 6
}

tk.Button(btn_frame, text="Add", bg="#2F7D7A", activebackground="#256461", activeforeground="white", command=add_food, **button_style).grid(row=0, column=0, padx=5)
tk.Button(btn_frame, text="Update", bg="#D28B26", activebackground="#AE711E", activeforeground="white", command=update_food, **button_style).grid(row=0, column=1, padx=5)
tk.Button(btn_frame, text="Delete", bg="#C6534B", activebackground="#A6413A", activeforeground="white", command=delete_food, **button_style).grid(row=0, column=2, padx=5)
tk.Button(btn_frame, text="Search", bg="#3B6F9E", activebackground="#2D587F", activeforeground="white", command=search_food, **button_style).grid(row=0, column=3, padx=5)

# -----------------------
# Start
# -----------------------
show_food()
root.mainloop()