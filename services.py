from database import conn, cursor
from datetime import datetime

# Function to insert a prayer into the database
def insert_prayer(user_id, username, prayer):
    now = datetime.now().isoformat()
    cursor.execute('''
    INSERT INTO prayers (user_id, username, prayer, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, prayer, now, now))
    conn.commit()

# Function to fetch all prayers for a user
def fetch_prayers(user_id):
    cursor.execute('SELECT id, prayer FROM prayers WHERE user_id = ?', (user_id,))
    return cursor.fetchall()

# Function to update a prayer in the database
def update_prayer(prayer_id, new_text):
    now = datetime.now().isoformat()
    cursor.execute('UPDATE prayers SET prayer = ?, updated_at = ? WHERE id = ?', (new_text, now, prayer_id))
    conn.commit()

# Function to delete a prayer from the database
def delete_prayer(prayer_id):
    cursor.execute('DELETE FROM prayers WHERE id = ?', (prayer_id,))
    conn.commit() 