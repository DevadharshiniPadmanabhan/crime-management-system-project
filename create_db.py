import sqlite3

conn = sqlite3.connect("database1.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aadhaar TEXT UNIQUE NOT NULL,
    dob TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print("database1.db created successfully")
