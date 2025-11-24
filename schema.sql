-- Create the 'users' table if it doesn't already exist
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    username TEXT,
    email TEXT, 
    password TEXT, 
    role TEXT NOT NULL CHECK(role IN ('admin', 'student', 'therapist', 'user')) DEFAULT 'user',
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


-- matchmaking tables - Son
CREATE TABLE IF NOT EXISTS matchmaking_queue_students (
    user_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    urgency INTEGER NOT NULL CHECK (urgency IN (0, 1)),
    topic TEXT,
    timestamp TEXT DEFAULT (datetime('now', 'localtime'))
); 

CREATE TABLE IF NOT EXISTS matchmaking_queue_therapists (
    user_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    expertise TEXT,
    timestamp TEXT DEFAULT (datetime('now', 'localtime'))
);

-- test xong set student id unique
CREATE TABLE IF NOT EXISTS matchmaking_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_user_id INTEGER NOT NULL,   -- 1 student → only 1 therapist
    therapist_user_id INTEGER NOT NULL,        -- therapist can repeat (many students)
    student_session_id TEXT NOT NULL,
    therapist_session_id TEXT NOT NULL,
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    -- FOREIGN KEY (student_user_id) REFERENCES users(user_id),
    -- FOREIGN KEY (therapist_user_id) REFERENCES users(user_id)
);