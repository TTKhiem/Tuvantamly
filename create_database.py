import sqlite3
import os

def create_database():
    if not os.path.exists('users.db'):
        with sqlite3.connect('users.db') as conn:
            # User table (as before)
            conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, ' \
            'email TEXT, password TEXT, role TEXT DEFAULT "user",' \
            'date_of_birth TEXT, phone TEXT, address TEXT, date_joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
            
            conn.execute('''
    INSERT INTO users (username, email, password, role)
    VALUES ('Admin', 'admin@gmail.com', '123', 'admin')
            
''')
            
            # NEW: Add chat_logs table ===
            conn.execute('''
            CREATE TABLE chat_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_code TEXT NOT NULL,
                username TEXT NOT NULL,
                message_text TEXT,
                timestamp TEXT NOT NULL
            )
            ''')
            # =================================
            
            conn.commit()

if __name__ == '__main__':
    create_database()