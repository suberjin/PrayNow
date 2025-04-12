import sqlite3
from datetime import datetime

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('prayers.db', check_same_thread=False)
cursor = conn.cursor()

# Create the prayers table if it doesn't exist
def create_table():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS prayers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        prayer TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    ''')
    conn.commit()

# Expose the connection and cursor for use in other modules
__all__ = ['conn', 'cursor', 'create_table']
