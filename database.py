import sqlite3

# Create database and table
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


# Insert food
def insert(food_name, mfg_date, expiry_date):

    conn = sqlite3.connect("food.db")

    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO food(food_name,mfg_date,expiry_date) VALUES(?,?,?)",
        (food_name, mfg_date, expiry_date)
    )

    conn.commit()
    conn.close()


# Fetch all records
def fetch():

    conn = sqlite3.connect("food.db")

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM food")

    rows = cursor.fetchall()

    conn.close()

    return rows
if __name__ == "__main__":
    connect()

    rows = fetch()

    for row in rows:
        print(row)
    