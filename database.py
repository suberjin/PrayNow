import sqlite3
from datetime import datetime
import logging

# Get logger
logger = logging.getLogger(__name__)

# Connect to SQLite database (or create it if it doesn't exist)
logger.info("Connecting to prayers.db database")
conn = sqlite3.connect('prayers.db', check_same_thread=False)
cursor = conn.cursor()

# Create the prayers and categories tables if they don't exist
def create_table():
    logger.info("Creating database tables if they don't exist")
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
    logger.info("Database setup completed")

# Get all categories
def get_all_categories():
    logger.debug("Fetching all categories")
    cursor.execute('SELECT id, name FROM categories ORDER BY name')
    categories = cursor.fetchall()
    logger.debug(f"Retrieved {len(categories)} categories")
    return categories

# Get category by ID
def get_category_by_id(category_id):
    logger.debug(f"Fetching category with ID: {category_id}")
    cursor.execute('SELECT name FROM categories WHERE id = ?', (category_id,))
    result = cursor.fetchone()
    if result:
        logger.debug(f"Found category: {result[0]}")
    else:
        logger.warning(f"Category with ID {category_id} not found")
    return result[0] if result else None

# Expose the connection and cursor for use in other modules
__all__ = ['conn', 'cursor', 'create_table', 'get_all_categories', 'get_category_by_id']
