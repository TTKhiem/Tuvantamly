-- Bảng người dùng
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
    date_joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags TEXT DEFAULT ''
);

-- Bảng thú cưng (ĐÃ CẬP NHẬT ĐỦ 2 CỘT SKIN VÀ BACKGROUND)
CREATE TABLE IF NOT EXISTS pets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    level INTEGER DEFAULT 1,
    happiness INTEGER DEFAULT 50,
    energy INTEGER DEFAULT 100,
    experience INTEGER DEFAULT 0,
    skin_id INTEGER DEFAULT 0,         -- Cột Skin
    background_id INTEGER DEFAULT 0,   -- Cột Background (Bị thiếu ở bản cũ)
    last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Bảng túi đồ
CREATE TABLE IF NOT EXISTS user_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Bảng nhiệm vụ hàng ngày
CREATE TABLE IF NOT EXISTS daily_quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    quest_id INTEGER NOT NULL,
    completed BOOLEAN DEFAULT 0,
    date_assigned DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Bảng lịch sử chat
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Bảng tóm tắt buổi tư vấn
CREATE TABLE IF NOT EXISTS intake_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    summary_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);


CREATE TABLE IF NOT EXISTS chat_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_code TEXT NOT NULL,
    username TEXT NOT NULL,
    message_text TEXT,
    timestamp TEXT NOT NULL
);

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
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    roomcode TEXT NOT NULL

    -- FOREIGN KEY (student_user_id) REFERENCES users(user_id),
    -- FOREIGN KEY (therapist_user_id) REFERENCES users(user_id)
);