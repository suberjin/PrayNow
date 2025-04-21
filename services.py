from database import conn, cursor
from datetime import datetime
import logging

# Get logger
logger = logging.getLogger(__name__)

# Function to insert a prayer into the database
def insert_prayer(user_id, username, prayer, category_id, first_name="", last_name=""):
    logger.info(f"Inserting prayer for user {user_id} in category {category_id}")
    try:
        now = datetime.now().isoformat()
        cursor.execute('''
        INSERT INTO prayers (user_id, username, first_name, last_name, prayer, category_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, prayer, category_id, now, now))
        conn.commit()
        logger.info(f"Prayer inserted successfully for user {user_id}, rowid: {cursor.lastrowid}")
        return True
    except Exception as e:
        logger.error(f"Error inserting prayer: {str(e)}")
        return False

# Function to fetch all prayers for a user
def fetch_prayers(user_id):
    cursor.execute('''
    SELECT p.id, p.prayer, c.name 
    FROM prayers p
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE p.user_id = ? 
    ORDER BY p.created_at DESC
    ''', (user_id,))
    return cursor.fetchall()

# Function to fetch prayers for a user filtered by category
def fetch_prayers_by_category(user_id, category_id):
    cursor.execute('''
    SELECT p.id, p.prayer, c.name 
    FROM prayers p
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE p.user_id = ? AND p.category_id = ?
    ORDER BY p.created_at DESC
    ''', (user_id, category_id))
    return cursor.fetchall()

# Function to update a prayer in the database
def update_prayer(prayer_id, new_text, category_id=None):
    now = datetime.now().isoformat()
    if category_id is not None:
        cursor.execute('''
        UPDATE prayers 
        SET prayer = ?, category_id = ?, updated_at = ? 
        WHERE id = ?
        ''', (new_text, category_id, now, prayer_id))
    else:
        cursor.execute('''
        UPDATE prayers 
        SET prayer = ?, updated_at = ? 
        WHERE id = ?
        ''', (new_text, now, prayer_id))
    conn.commit()

# Function to delete a prayer from the database
def delete_prayer(prayer_id):
    cursor.execute('DELETE FROM prayers WHERE id = ?', (prayer_id,))
    conn.commit()

# Function to fetch a single prayer by ID
def get_prayer_by_id(prayer_id):
    cursor.execute('''
    SELECT p.prayer, p.category_id, c.name
    FROM prayers p
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE p.id = ?
    ''', (prayer_id,))
    result = cursor.fetchone()
    return result if result else None

# Function to fetch all prayers from all users
def fetch_all_prayers(limit=10, offset=0):
    """
    Gets all prayers with pagination to avoid loading too much data at once.
    
    Args:
        limit: Maximum number of prayers to load at once
        offset: Offset from the beginning of the list
        
    Returns:
        List of prayers with the specified limit and offset
    """
    query = '''
    SELECT p.prayer, p.username, p.created_at, p.first_name, p.last_name, c.name
    FROM prayers p
    LEFT JOIN categories c ON p.category_id = c.id
    ORDER BY p.created_at DESC
    LIMIT ? OFFSET ?
    '''
    
    cursor.execute(query, (limit, offset))
    return cursor.fetchall()

# Function to fetch all prayers from all users filtered by category
def fetch_all_prayers_by_category(category_id, limit=10, offset=0):
    """
    Gets all prayers of a specific category with pagination.
    
    Args:
        category_id: Category ID
        limit: Maximum number of prayers to load at once
        offset: Offset from the beginning of the list
        
    Returns:
        List of prayers of the specified category with the specified limit and offset
    """
    query = '''
    SELECT p.prayer, p.username, p.created_at, p.first_name, p.last_name, c.name
    FROM prayers p
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE p.category_id = ?
    ORDER BY p.created_at DESC
    LIMIT ? OFFSET ?
    '''
    
    cursor.execute(query, (category_id, limit, offset))
    return cursor.fetchall()

# Function to count total prayers
def count_all_prayers():
    """
    Counts the total number of prayers.
    
    Returns:
        Integer - number of prayers
    """
    cursor.execute('SELECT COUNT(*) FROM prayers')
    return cursor.fetchone()[0]

# Function to count prayers in a specific category
def count_prayers_by_category(category_id):
    """
    Counts the number of prayers in a specific category.
    
    Args:
        category_id: Category ID
        
    Returns:
        Integer - number of prayers in the category
    """
    cursor.execute('SELECT COUNT(*) FROM prayers WHERE category_id = ?', (category_id,))
    return cursor.fetchone()[0] 