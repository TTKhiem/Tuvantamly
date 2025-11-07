import sqlite3
import os

def create_database():
    if not os.path.exists('users.db'):
        with sqlite3.connect('users.db') as conn:
            conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, ' \
            'email TEXT, password TEXT, role TEXT DEFAULT "user",' \
            'date_of_birth TEXT, phone TEXT, address TEXT, date_joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
            
            conn.execute('''
    INSERT INTO users (username, email, password, role)
    VALUES ('Admin', 'admin@gmail.com', '123', 'admin')
            
''')
            conn.commit()

if __name__ == '__main__':
    create_database()