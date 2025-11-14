-- Create the 'users' table if it doesn't already exist
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    username TEXT,
    email TEXT, 
    password TEXT, 
    role TEXT DEFAULT "user",
    date_of_birth TEXT, 
    phone TEXT, 
    address TEXT, 
    date_joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags TEXT
);

-- Create the 'chat_logs' table if it doesn't already exist
CREATE TABLE IF NOT EXISTS chat_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_code TEXT NOT NULL,
    username TEXT NOT NULL,
    message_text TEXT,
    timestamp TEXT NOT NULL
);

-- Insert the default Admin user IF the email 'admin@gmail.com' doesn't already exist
-- This prevents creating duplicate admins every time the app starts
INSERT INTO users (username, email, password, role, tags) 
SELECT 'Admin', 'admin@gmail.com', '123', 'admin', 'admin'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'admin@gmail.com');