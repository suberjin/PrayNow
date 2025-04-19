import sqlite3
from datetime import datetime

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('prayers.db', check_same_thread=False)
cursor = conn.cursor()

# Create the prayers and categories tables if they don't exist
def create_table():
    # Create categories table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    ''')

    # Create prayers table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS prayers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        prayer TEXT,
        category_id INTEGER,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )
    ''')

    # Insert default categories if they don't exist
    categories = [
        "Подяки",
        "Спасіння",
        "Військові",
        "Здоровʼя",
        "Інші",
        "Термінові"
    ]
    
    for category in categories:
        cursor.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (category,))
    
    conn.commit()

# Get all categories
def get_all_categories():
    cursor.execute('SELECT id, name FROM categories ORDER BY name')
    return cursor.fetchall()

# Get category by ID
def get_category_by_id(category_id):
    cursor.execute('SELECT name FROM categories WHERE id = ?', (category_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# Expose the connection and cursor for use in other modules
__all__ = ['conn', 'cursor', 'create_table', 'get_all_categories', 'get_category_by_id']
