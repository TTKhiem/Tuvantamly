import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_NAME = 'users.db'

def create_database():
    # Use IF NOT EXISTS so we don't wipe data if run accidentally
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # --- 1. Users Table (Merged from your main.py and my previous version) ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user', 
                date_of_birth TEXT,
                phone TEXT,
                address TEXT,
                gold INTEGER DEFAULT 200,
                date_joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # --- 2. Pets Table ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                happiness INTEGER DEFAULT 50,
                energy INTEGER DEFAULT 100,
                experience INTEGER DEFAULT 0,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # --- 3. Inventory Table ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # --- 4. Daily Quests Table ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                quest_id INTEGER NOT NULL,
                completed BOOLEAN DEFAULT 0,
                date_assigned DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # --- Initial Admin User ---
        cursor.execute("SELECT id FROM users WHERE username = 'Admin'")
        if not cursor.fetchone():
            # NOTE: We must hash the admin password too!
            admin_pass = generate_password_hash('123')
            cursor.execute('''
                INSERT INTO users (username, email, password, role, gold)
                VALUES ('Admin', 'admin@gmail.com', ?, 'admin', 9999)
            ''', (admin_pass,))
            admin_id = cursor.lastrowid
            # Give admin a pet
            cursor.execute('''
                INSERT INTO pets (user_id, name, level, happiness, energy, experience)
                VALUES (?, 'AdminPet', 10, 100, 100, 0)
            ''', (admin_id,))

        conn.commit()
        print(f"Database {DB_NAME} updated successfully.")

if __name__ == '__main__':
    create_database()