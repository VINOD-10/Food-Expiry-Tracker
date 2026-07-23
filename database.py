import sqlite3

# -----------------------------
# Create database and table
# -----------------------------
def connect():

    conn = sqlite3.connect("food.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS food(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_name TEXT,
        mfg_date TEXT,
        expiry_date TEXT
    )
    """)

    conn.commit()
    conn.close()


# -----------------------------
# Insert food
# -----------------------------
def insert(food_name, mfg_date, expiry_date):

    conn = sqlite3.connect("food.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO food(food_name, mfg_date, expiry_date) VALUES (?, ?, ?)",
        (food_name, mfg_date, expiry_date)
    )

    conn.commit()
    conn.close()


# -----------------------------
# Fetch all records
# -----------------------------
def fetch():

    conn = sqlite3.connect("food.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM food")

    rows = cursor.fetchall()

    conn.close()

    return rows


# -----------------------------
# Search food
# -----------------------------
def search(food_name):

    conn = sqlite3.connect("food.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM food WHERE food_name LIKE ?",
        ('%' + food_name + '%',)
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


# -----------------------------
# Delete one food
# -----------------------------
def delete(food_id):

    conn = sqlite3.connect("food.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM food WHERE id=?",
        (food_id,)
    )

    conn.commit()
    conn.close()


# -----------------------------
# Delete all foods
# -----------------------------
def delete_all():

    conn = sqlite3.connect("food.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM food")

    conn.commit()
    conn.close()