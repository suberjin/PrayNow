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
    
    # Create whitelist table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS whitelist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT UNIQUE,
        added_at TEXT
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
    
    # Insert default whitelisted user - first check if exists
    admin_id = 282269567
    admin_username = "suberjin"
    
    # Check if admin already exists by ID or username
    cursor.execute('SELECT 1 FROM whitelist WHERE user_id = ? OR username = ?', (admin_id, admin_username))
    if not cursor.fetchone():
        # Only insert if admin doesn't exist
        now = datetime.now().isoformat()
        try:
            cursor.execute('''
            INSERT INTO whitelist (user_id, username, added_at)
            VALUES (?, ?, ?)
            ''', (admin_id, admin_username, now))
            logger.info(f"Added default admin {admin_username} (ID: {admin_id}) to whitelist")
        except Exception as e:
            logger.error(f"Error adding default admin to whitelist: {str(e)}")
    
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

# Check if user is in whitelist
def is_user_whitelisted(user_id, username=None):
    logger.debug(f"Checking if user {user_id} or {username} is whitelisted")
    
    try:
        # Try by user_id first
        if user_id is not None:
            cursor.execute('SELECT 1 FROM whitelist WHERE user_id = ?', (user_id,))
            if cursor.fetchone():
                logger.debug(f"User {user_id} found in whitelist by ID")
                return True
        
        # If not found and username provided, try by username
        if username:
            cursor.execute('SELECT 1 FROM whitelist WHERE username = ?', (username,))
            if cursor.fetchone():
                logger.debug(f"User {username} found in whitelist by username")
                # Update user_id in whitelist if we only had the username before
                if user_id is not None:
                    try:
                        cursor.execute('UPDATE whitelist SET user_id = ? WHERE username = ? AND (user_id IS NULL OR user_id = 0)', 
                                    (user_id, username))
                        conn.commit()
                    except Exception as e:
                        logger.error(f"Error updating user_id for username {username}: {str(e)}")
                return True
        
        logger.debug(f"User {user_id}/{username} not found in whitelist")
        return False
    except Exception as e:
        logger.error(f"Error checking whitelist for user {user_id}/{username}: {str(e)}")
        # In case of error, default to denying access
        return False

# Add user to whitelist
def add_user_to_whitelist(user_id, username=None):
    logger.info(f"Adding user {user_id}/{username} to whitelist")
    
    # Basic validation
    if user_id is None and (username is None or not username.strip()):
        logger.error("Cannot add to whitelist: both user_id and username are empty")
        return False
    
    try:
        now = datetime.now().isoformat()
        
        # Check if user already exists by ID or username
        if user_id is not None:
            cursor.execute('SELECT id FROM whitelist WHERE user_id = ?', (user_id,))
            if cursor.fetchone():
                logger.info(f"User with ID {user_id} already in whitelist, updating username if provided")
                if username:
                    cursor.execute('UPDATE whitelist SET username = ? WHERE user_id = ?', (username, user_id))
                    conn.commit()
                return True
        
        if username:
            cursor.execute('SELECT id FROM whitelist WHERE username = ?', (username,))
            if cursor.fetchone():
                logger.info(f"User with username {username} already in whitelist, updating user_id if provided")
                if user_id is not None:
                    cursor.execute('UPDATE whitelist SET user_id = ? WHERE username = ?', (user_id, username))
                    conn.commit()
                return True
        
        # Insert new user
        cursor.execute('''
        INSERT INTO whitelist (user_id, username, added_at)
        VALUES (?, ?, ?)
        ''', (user_id, username, now))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding user to whitelist: {str(e)}")
        return False

# Remove user from whitelist
def remove_user_from_whitelist(user_id=None, username=None):
    logger.info(f"Removing user {user_id}/{username} from whitelist")
    
    # Basic validation
    if user_id is None and (username is None or not username.strip()):
        logger.error("Cannot remove from whitelist: both user_id and username are empty")
        return False
    
    try:
        if user_id is not None:
            cursor.execute('DELETE FROM whitelist WHERE user_id = ?', (user_id,))
        elif username:
            cursor.execute('DELETE FROM whitelist WHERE username = ?', (username,))
        else:
            return False
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error removing user from whitelist: {str(e)}")
        return False

# Get all whitelisted users
def get_all_whitelisted_users():
    logger.debug("Fetching all whitelisted users")
    cursor.execute('SELECT user_id, username, added_at FROM whitelist ORDER BY added_at DESC')
    users = cursor.fetchall()
    logger.debug(f"Retrieved {len(users)} whitelisted users")
    return users

# Expose the connection and cursor for use in other modules
__all__ = ['conn', 'cursor', 'create_table', 'get_all_categories', 'get_category_by_id', 
           'is_user_whitelisted', 'add_user_to_whitelist', 'remove_user_from_whitelist',
           'get_all_whitelisted_users']
