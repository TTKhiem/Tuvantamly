from contextlib import contextmanager
import sqlite3

db_path = "app.db"

@contextmanager
def setup_cursor():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    finally:
        conn.close()

def add_student_to_matchmaking_queue(user_id, urgency, topic, session_id):
    with setup_cursor() as cursor:
        cursor.execute("INSERT INTO matchmaking_queue_students (user_id, urgency, topic, session_id) VALUES (?, ?, ?, ?)", (user_id, urgency, topic, session_id))

def add_therapist_to_matchmaking_queue(user_id, expertise, session_id):
    with setup_cursor() as cursor:
        cursor.execute("INSERT INTO matchmaking_queue_therapists (user_id, expertise, session_id) VALUES (?, ?, ?)", (user_id, expertise, session_id))
    
def get_all_students_from_matchmaking_queue():
    with setup_cursor() as cursor:
        cursor.execute("SELECT * FROM matchmaking_queue_students ORDER BY urgency DESC, timestamp ASC")
        return cursor.fetchall()

def get_all_therapists_from_matchmaking_queue():
    with setup_cursor() as cursor:
        cursor.execute("SELECT * FROM matchmaking_queue_therapists ORDER BY timestamp ASC")
        return cursor.fetchall()

def delete_student_from_matchmaking_queue(user_id):
    with setup_cursor() as cursor:
        cursor.execute("DELETE FROM matchmaking_queue_students WHERE user_id = ?", (user_id,))

def delete_therapist_from_matchmaking_queue(user_id):
    with setup_cursor() as cursor:
        cursor.execute("DELETE FROM matchmaking_queue_therapists WHERE user_id = ?", (user_id,))

def delete_student_and_therapist_from_matchmaking_queue(student, therapist):
    delete_student_from_matchmaking_queue(student["user_id"])
    delete_therapist_from_matchmaking_queue(therapist["user_id"])

def add_student_and_therapist_to_matchmaking_results(pair: dict):
    with setup_cursor() as cursor:
        cursor.execute("INSERT INTO matchmaking_results (student_user_id, therapist_user_id, student_session_id, therapist_session_id) VALUES (?, ?, ?, ?)", (pair["student_user_id"], pair["therapist_user_id"], pair["student_session_id"], pair["therapist_session_id"]))

def get_therapist_expertise_tag(user_id):
    with setup_cursor() as cursor:
        cursor.execute("SELECT tags FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()

def check_student_already_matched(user_id):
    with setup_cursor() as cursor:
        cursor.execute("SELECT 1 FROM matchmaking_results WHERE student_user_id = ?", (user_id,))
        return cursor.fetchone() is not None

def check_student_already_in_matchmaking_queue(user_id):
    with setup_cursor() as cursor:
        cursor.execute("SELECT 1 FROM matchmaking_queue_students WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None
    
def check_therapist_already_in_matchmaking_queue(user_id):
    with setup_cursor() as cursor:
        cursor.execute("SELECT 1 FROM matchmaking_queue_therapists WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None

def get_match_id_based_on_pair(pair: dict):
    with setup_cursor() as cursor:
        cursor.execute("SELECT id FROM matchmaking_results WHERE student_user_id = ? AND therapist_user_id = ?", (pair["student_user_id"], pair["therapist_user_id"]))
        row = cursor.fetchone()
    if row:
        return row[0]
    return None

def get_matches_for_user(user_id):
    with setup_cursor() as cursor:
        cursor.execute("SELECT * FROM matchmaking_results WHERE student_user_id = ? OR therapist_user_id = ? ORDER BY matched_at ASC", (user_id, user_id))
        rows = cursor.fetchall()
    matches = []
    for row in rows:
        matches.append({
            "match_id": row[0],
            "student_user_id": row[1],
            "therapist_user_id": row[2],
            "matched_at": row[3]
        })
    return matches

def add_student_and_therapist_to_matchmaking_results(pair: dict):
    #thêm 'roomcode' vào danh sách các cột và giá trị
    with setup_cursor() as cursor:
        cursor.execute(
            "INSERT INTO matchmaking_results (student_user_id, therapist_user_id, student_session_id, therapist_session_id, roomcode) VALUES (?, ?, ?, ?, ?)", 
            (
                pair["student_user_id"], 
                pair["therapist_user_id"], 
                pair["student_session_id"], 
                pair["therapist_session_id"],
                pair["roomcode"] 
            )
        )

def get_current_match_roomcode(user_id):
    """
    Kiểm tra và trả về roomcode từ trận đấu gần nhất của sinh viên.
    Giả định 1 sinh viên chỉ có 1 trận đấu hoạt động tại 1 thời điểm.
    """
    with setup_cursor() as cursor:
        cursor.execute(
            "SELECT roomcode FROM matchmaking_results WHERE student_user_id = ? ORDER BY matched_at DESC LIMIT 1", 
            (user_id
             ,)
        )
        row = cursor.fetchone()
    if row and row['roomcode']:
        return row['roomcode']
    return None
def delete_match_by_roomcode(room_code):
    """Xóa bản ghi match dựa trên room_code"""
    with setup_cursor() as cursor:
        cursor.execute("DELETE FROM matchmaking_results WHERE roomcode = ?", (room_code,))
        
def get_all_matched_roomcodes_for_therapist(user_id):
    """Lấy tất cả các roomcode mà therapist này đã được ghép đôi."""
    with setup_cursor() as cursor:
        cursor.execute(
            """
            SELECT roomcode, student_user_id, matched_at
            FROM matchmaking_results 
            WHERE therapist_user_id = ? 
            ORDER BY matched_at DESC
            """, 
            (user_id,)
        )
        # Trả về danh sách các bản ghi (bao gồm roomcode, student_user_id, matched_at)
        return cursor.fetchall()
def get_all_users():
    """Lấy tất cả người dùng cho Admin Dashboard."""
    with setup_cursor() as cursor:
        # Loại bỏ trường password vì lý do bảo mật
        cursor.execute("SELECT id, username, email, role, gold, tags, date_joined FROM users ORDER BY id ASC")
        rows=cursor.fetchall()
        return [dict(row) for row in rows]
        
def get_all_matchmaking_results():
    """Lấy tất cả matchmaking results cho Admin Dashboard."""
    with setup_cursor() as cursor:
        cursor.execute("SELECT * FROM matchmaking_results ORDER BY matched_at DESC")
        return cursor.fetchall()

def extract_topic_from_tags(tags):
    # Chuyển đổi tags thành danh sách các chủ đề
    topics = [tag.strip() for tag in tags.split(",")]
    return topics

def admin_create_match_result(pair: dict):
    """
    Tạo bản ghi match thủ công từ Admin.
    Sử dụng hàm này để tránh trùng lặp logic với add_student_and_therapist_to_matchmaking_results.
    """
    with setup_cursor() as cursor:
        cursor.execute(
            "INSERT INTO matchmaking_results (student_user_id, therapist_user_id, student_session_id, therapist_session_id, roomcode) VALUES (?, ?, ?, ?, ?)", 
            (
                pair["student_user_id"], 
                pair["therapist_user_id"], 
                pair["student_session_id"], 
                pair["therapist_session_id"],
                pair["roomcode"] 
            )
        )
