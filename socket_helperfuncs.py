import random
from string import ascii_uppercase
from globals import rooms, connected_users
from flask import session, request
from globals import socketio
import sqlite3
from datetime import datetime


def generate_unique_code1(length):
    # Keep the helper function here since it relies on the global `rooms`
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        if code not in rooms:
            break
    return code
def get_user_data(username):
# ... existing code ...
    """Fetches user data, including tags, from the DB."""
    with sqlite3.connect('app.db') as conn:
        conn.row_factory = sqlite3.Row 
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = cur.fetchone()
        
        if user_data:
            # Parse tags from a comma-separated string into a list
            tags_list = []
            if user_data['tags']:
                tags_list = [tag.strip() for tag in user_data['tags'].split(',')]
            
            # Convert Row object to a dictionary and add parsed tags
            user_dict = dict(user_data)
            user_dict['tags_list'] = tags_list
            return user_dict
        return None
    
def get_user_data_by_id(user_id):
    """Lấy dữ liệu người dùng (bao gồm tags) từ DB dựa trên ID."""
    with sqlite3.connect('app.db') as conn:
        conn.row_factory = sqlite3.Row 
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_data = cur.fetchone()
        
        if user_data:
            tags_list = []
            if user_data['tags']:
                tags_list = [tag.strip() for tag in user_data['tags'].split(',')]
            
            user_dict = dict(user_data)
            user_dict['tags_list'] = tags_list
            return user_dict
        return None


#*****NOTE OLD CODE***********
# def notify_users_of_new_match(student_user_id, therapist_user_id, student_session_id, therapist_session_id):
#     # """
#     # Emit a 'new_match' event to both student and therapist when a match is created.
#     # Front-end can listen to this event to update sidebar and allow joining the room.
#     # """
#     print(f"MATCH FOUND: {student_user_id}, {therapist_user_id}, {student_session_id}, {therapist_session_id}")
#     # 2. Create a new room for them
#     new_room_code = generate_unique_code1(6) # 6 chars for matched rooms
#     rooms[new_room_code] = {"members": 0, "messages": []}
    
#     # 3. Notify both users using their SID
#     match_data = {
#         "room_code": new_room_code,
#         "matched_with": "{student_user_id} và {therapist_user_id}",
#     }
#     socketio.emit("match_found", match_data, to=student_session_id)
#     socketio.emit("match_found", match_data, to=therapist_session_id)
#     print("check")
    
#     # --- THIS IS THE FIX ---
#     # A match was made. Stop searching and exit the function.
#     return
#     # -----------------------
# *****NOTE OLD CODE***************

    




#**********NOTE OLD CODE ************
# def notify_users_of_new_match(student_user_id, therapist_user_id, student_session_id, therapist_session_id):
#     """
#     Thông báo cho cả sinh viên và chuyên gia khi tìm thấy trận đấu.
#     """
    
#     # 1. Lấy thông tin người dùng (ĐÃ THÊM HÀM get_user_data_by_id ở trên)
#     student_data = get_user_data_by_id(student_user_id) 
#     therapist_data = get_user_data_by_id(therapist_user_id) 
    
#     student_name = student_data.get('username') if student_data else "Sinh viên"
#     therapist_name = therapist_data.get('username') if therapist_data else "Tư vấn viên"
#     student_tags = student_data.get('tags_list', []) if student_data else []
    
#     # Tags chung: Tạm thời lấy tags của sinh viên làm chủ đề
#     common_tags = student_tags
    
#     print(f"MATCH FOUND: Student {student_name} (SID: {student_session_id}), Therapist {therapist_name} (SID: {therapist_session_id})")
    
#     # 2. Tạo phòng mới
#     new_room_code = generate_unique_code1(6) # 6 chars for matched rooms
#     rooms[new_room_code] = {"members": 0, "messages": []}
    
#     # 3. Notify cả hai người dùng bằng SID
    
#     # Dữ liệu cho Sinh viên
#     match_data_student = {
#         "room_code": new_room_code,
#         "matched_with": therapist_name, # Hiện tên người ghép đôi
#         "tags": common_tags
#     }
#     # Dữ liệu cho Tư vấn viên
#     match_data_therapist = {
#         "room_code": new_room_code,
#         "matched_with": student_name,
#         "tags": common_tags
#     }
    
#     socketio.emit("match_found", match_data_student, to=student_session_id)
#     socketio.emit("match_found", match_data_therapist, to=therapist_session_id)
#     print("Thong bao match_found da duoc gui.")
    
#     # --- LOGIC DỪNG TÌM KIẾM ---
#     # KHÔNG NÊN có 'return' ở đây nếu hàm này được gọi từ run_matchmaking, 
#     # vì run_matchmaking cần phải hoàn tất vòng lặp của nó.
#     # Logic dừng/xóa khỏi queue đã được xử lý trong matchmaking_logic.py
#     # do đó, tôi ĐÃ XÓA đoạn code 'return' gây lỗi.
#**********NOTE OLD CODE ************




def notify_users_of_new_match(student_user_id, therapist_user_id, student_session_id, therapist_session_id, new_room_code):
    """
    Thông báo cho cả sinh viên và chuyên gia khi tìm thấy trận đấu.
    """
    
    # 1. Lấy thông tin người dùng (ĐÃ THÊM HÀM get_user_data_by_id ở trên)
    student_data = get_user_data_by_id(student_user_id) 
    therapist_data = get_user_data_by_id(therapist_user_id) 
    
    student_name = student_data.get('username') if student_data else "Sinh viên"
    therapist_name = therapist_data.get('username') if therapist_data else "Tư vấn viên"
    student_tags = student_data.get('tags_list', []) if student_data else []
    
    # Tags chung: Tạm thời lấy tags của sinh viên làm chủ đề
    common_tags = student_tags
    
    print(f"MATCH FOUND: Student {student_name} (SID: {student_session_id}), Therapist {therapist_name} (SID: {therapist_session_id})")
    
    rooms[new_room_code] = {"members": 0, "messages": []}
    
    # 3. Notify cả hai người dùng bằng SID
    
    # Dữ liệu cho Sinh viên
    match_data_student = {
        "room_code": new_room_code,
        "matched_with": therapist_name, # Hiện tên người ghép đôi
        "tags": common_tags
    }
    # Dữ liệu cho Tư vấn viên
    match_data_therapist = {
        "room_code": new_room_code,
        "matched_with": student_name,
        "tags": common_tags
    }
    
    socketio.emit("match_found", match_data_student, to=student_session_id)
    socketio.emit("match_found", match_data_therapist, to=therapist_session_id)
    print("Thong bao match_found da duoc gui.")