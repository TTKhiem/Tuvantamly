from flask import session, request, url_for
from flask_socketio import join_room, leave_room, send, emit
import sqlite3
from datetime import datetime
from globals import socketio
from globals import rooms, connected_users
from socket_helperfuncs import generate_unique_code1, get_user_data
import matchmaking_logic
import matchmaking_repository
import json
from socket_helperfuncs import get_user_data
from matchmaking_repository import get_current_match_roomcode

# --- HÀM HỖ TRỢ MỚI: TẢI DỮ LIỆU PHÒNG TỪ SQLITE ---
def load_room_data_from_sqlite(room_code):
    """Lấy tin nhắn cũ từ DB để khôi phục phòng vào bộ nhớ."""
    try:
        with sqlite3.connect('app.db') as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT username, message_text, timestamp FROM chat_logs WHERE room_code = ? ORDER BY timestamp ASC",
                (room_code,)
            )
            existing_messages = cur.fetchall()
        
        # if not existing_messages:
        #     return None # Phòng không có lịch sử

        # -----------------------------------------------------------------
        # BƯỚC 1: Xử lý và Định dạng tin nhắn (Định nghĩa loaded_messages)
        # -----------------------------------------------------------------
        loaded_messages = []
        for msg in existing_messages:
            try:
                # Định dạng lại timestamp cho hiển thị
                ts_obj = datetime.strptime(msg[2], '%Y-%m-%d %H:%M:%S.%f')
                formatted_ts = ts_obj.strftime('%Y-%m-%d %H:%M')
            except ValueError:
                formatted_ts = msg[2] # Fallback
            loaded_messages.append({"name": msg[0], "message": msg[1], "timestamp": formatted_ts})
        
        # -----------------------------------------------------------------
        # BƯỚC 2: Khôi phục vào biến toàn cục 'rooms' (rooms đã tồn tại)
        # -----------------------------------------------------------------
        if room_code not in rooms:
             # Bây giờ loaded_messages đã có giá trị hợp lệ
             rooms[room_code] = {"members": 0, "messages": loaded_messages} 
             print(f"Phong {room_code} da duoc khoi phuc tu SQLite.") 
            
        # -----------------------------------------------------------------
            
        return loaded_messages
    except Exception as e:
        # Sử dụng `print` để xem lỗi thật sự nếu có (ví dụ: lỗi DB khác)
        print(f"Loi truy van SQLite trong Socket Connect: {e}") 
        return None
        
@socketio.on("connect")
def connect(auth):
    name = session.get("username")
    room = session.get("room") 
    sid = request.sid

    if not name:
        return 
    
    connected_users[name] = sid
    print(f"CLIENT CONNECTED: {name} (SID: {sid})")
    
    if not room:
        return 
    
    # --- FIX QUAN TRỌNG: Tải lại trạng thái phòng nếu bị mất (Do đa luồng) ---
    if room not in rooms:
        # Nếu phòng không có trong bộ nhớ cục bộ, thử tải từ SQLite
        loaded_messages = load_room_data_from_sqlite(room)
        
        if loaded_messages is not None:
            # Khôi phục phòng vào bộ nhớ
            rooms[room] = {"members": 0, "messages": loaded_messages}
            print(f"Phong {room} da dc khoi phuc tu SQLite cho Socket Connect.")
        else:
            # Nếu không có trong bộ nhớ và không có trong DB (lịch sử)
            leave_room(room)
            print(f"Socket Disconnect: Phong {room} khong ton tai hoac khong co lich su.")
            return

    # --- Logic tham gia phòng (sau khi phòng đã được đảm bảo tồn tại trong 'rooms') ---
    join_room(room)
    now_display_format = datetime.now().strftime('%Y-%m-%d %H:%M')
    rooms[room]["members"] += 1
    # System message removed

# ... (Các hàm disconnect, message, find_match, cancel_match, join_private_room giữ nguyên) ...

# socket._handlers.py (UPDATED disconnect function)

@socketio.on("disconnect")
def disconnect():
    name = session.get("username")
    room = session.get("room")
    sid = request.sid 
    user_data = get_user_data(name) # Need to fetch user_id for DB delete
    
    if name in connected_users:
        del connected_users[name]
        print(f"CLIENT DISCONNECTED: {name} (SID: {sid})")
        print(f"Connected users: {list(connected_users.keys())}")

    # --- NEW DB QUEUE LOGIC ---
    if user_data:
        user_id = user_data["id"]
        # Assuming the user role is stored in session/user_data (e.g., 'therapist' or 'user')
        if user_data["role"] == 'therapist':
            matchmaking_repository.delete_therapist_from_matchmaking_queue(user_id)
        else: # user/student
            matchmaking_repository.delete_student_from_matchmaking_queue(user_id)
        print(f"Removed user {name} from DB matchmaking queue.")
    
    # OLD CODE: global matchmaking_queue # REMOVE THIS LINE
    # OLD CODE: matchmaking_queue = [u for u in matchmaking_queue if u["username"] != name] # REMOVE THIS LINE
    # --------------------------
    
    if room and room in rooms:
        leave_room(room)
        # ... (rest of the room disconnect logic)
        rooms[room]["members"] -= 1
        now_display_format = datetime.now().strftime('%Y-%m-%d %H:%M')
        # System message removed: send({"name": name, "message": "da roi phong.", "timestamp": now_display_format}, to=room)
        
        if rooms[room]["members"] <= 0:
            del rooms[room] 
        
        print(f"{name} da roi phong {room}")


@socketio.on("message")
def message(data):
    name = session.get("username")
    message_content = data.get("data")
    
    # 1. XÁC ĐỊNH MÃ PHÒNG (Room Code)
    # Therapist Messenger gửi room_code trong data; Student sử dụng session
    room = data.get("room_code") if data.get("room_code") else session.get("room")
    
    if not room or room not in rooms or not name or not message_content:
        # Nếu không có phòng, phòng không tồn tại trong bộ nhớ, hoặc không có tên/tin nhắn, thì dừng
        return 
    
    # Lấy timestamp hiện tại
    now = datetime.now()
    now_db_format = now.strftime("%Y-%m-%d %H:%M:%S.%f") 
    now_display_format = now.strftime('%Y-%m-%d %H:%M') 
    
    # 2. LƯU VÀO CƠ SỞ DỮ LIỆU (DB - chat_logs)
    try:
        with sqlite3.connect('app.db') as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO chat_logs (room_code, username, message_text, timestamp) VALUES (?, ?, ?, ?)",
                (room, name, message_content, now_db_format)
            )
            conn.commit()
    except Exception as e:
        print(f"Lỗi khi lưu tin nhắn vào DB: {e}")
        # Vẫn tiếp tục xử lý gửi tin nhắn dù DB lỗi để đảm bảo chat realtime
        
    # 3. LƯU VÀO BỘ NHỚ TOÀN CỤC (rooms)
    content_for_memory = {
        "name": name,
        "message": message_content,
        "timestamp": now_display_format
    }
    rooms[room]["messages"].append(content_for_memory)
    
    # 4. PHÁT SÓNG TIN NHẮN (Broadcasting)
    # Gửi tin nhắn đến tất cả mọi người trong phòng (bao gồm cả người gửi)
    send_data = {
        "name": name,
        "message": message_content,
        "timestamp": now_display_format,
        "room_code": room # Gửi kèm room_code để Therapist Messenger biết hiển thị vào cửa sổ nào
    }
    send(send_data, to=room)
    print(f"{name} (phong {room}): {message_content}")

# ... (All other @socketio.on functions: find_match, cancel_match, join_private_room) ...




@socketio.on("find_match")
def find_match(): 
    name = session.get("username")
    sid = request.sid
    
    print(f"--- [FIND MATCH] Request from: {name} ---")

    if not name:
        return

    user_data = get_user_data(name)
    if not user_data:
        emit("match_error", {"message": "Không tìm thấy hồ sơ người dùng."})
        return

    user_id = user_data["id"]
    user_role = user_data["role"]
    user_tags = user_data.get('tags_list', [])

    # ----------------------------------------------------
    # 1. KIỂM TRA: SINH VIÊN ĐÃ CÓ TRẬN ĐẤU CŨ CHƯA? (Logic bạn muốn giữ)
    # ----------------------------------------------------
    if user_role == 'user': 
        # Chỉ áp dụng hạn chế này cho Sinh viên
        active_room_code = get_current_match_roomcode(user_id)
        
        if active_room_code:
            print(f"--- [FIND MATCH] Blocked: Student {name} has active room {active_room_code}")
            # Thông báo cho client để chuyển hướng đến phòng chat đã lưu
            emit("match_error", {
                "message": f"Bạn đang có cuộc trò chuyện tại phòng: **{active_room_code}**. Vui lòng tiếp tục.",
                "action": "redirect_to_active_room",
                "room_code": active_room_code
            })
            return # Dừng ngay, không cho tìm trận mới
    # ----------------------------------------------------

    # 2. Chuẩn bị dữ liệu cho Queue (Xử lý an toàn cho tài khoản mới)
    urgency = 0 
    topic = "General" 
    expertise = "General"

    if user_role == 'user':
        if user_tags and 'urgency' in user_tags:
            urgency = 1
        if user_tags and len(user_tags) > 0:
            topic = str(user_tags)
        
        print(f"--- [FIND MATCH] Adding Student to Queue: Topic={topic}, Urgency={urgency}")

        if not matchmaking_repository.check_student_already_in_matchmaking_queue(user_id):
            matchmaking_repository.add_student_to_matchmaking_queue(user_id, urgency, topic, sid)
        else:
            print(f"Student {name} already in queue.")

    elif user_role == 'therapist':
        if user_tags and len(user_tags) > 0:
            expertise = str(user_tags)
            
        print(f"--- [FIND MATCH] Adding Therapist to Queue: Expertise={expertise}")

        if not matchmaking_repository.check_therapist_already_in_matchmaking_queue(user_id):
            matchmaking_repository.add_therapist_to_matchmaking_queue(user_id, expertise, sid)
        else:
            print(f"Therapist {name} already in queue.")
    else:
        emit("match_error", {"message": "Vai trò không hợp lệ."})
        return

    # 3. Thông báo và Chạy thuật toán ghép cặp
    emit("finding_match", {"message": "Đang tìm kiếm người phù hợp..."})
    
    print("--- [FIND MATCH] Running matchmaking algorithm...")
    matchmaking_logic.run_matchmaking()


#button to cancel matchmaking
# socket._handlers.py (UPDATED cancel_match function)

@socketio.on("cancel_match")
def cancel_match():
    name = session.get("username")
    
    if not name:
        return
    
    user_data = get_user_data(name)
    if not user_data:
        return

    user_id = user_data["id"]
    user_role = user_data["role"]

    # --- NEW DB QUEUE LOGIC ---
    if user_role == 'therapist':
        matchmaking_repository.delete_therapist_from_matchmaking_queue(user_id)
        print(f"Removed Therapist {name} from DB matchmaking queue.")
    else: # user/student
        matchmaking_repository.delete_student_from_matchmaking_queue(user_id)
        print(f"Removed Student {name} from DB matchmaking queue.")
    # --------------------------
    
    emit("match_cancelled", {"message": "Đã hủy tìm kiếm."})


#keep this function unchanged
@socketio.on("join_private_room")
def join_private_room(data):
    """
    Client emits this after clicking the 'Join' button
    from the 'match_found' or 'redirect_to_active_room' notification.
    """
    name = session.get("username")
    room_code = data.get("room_code")
    if not name or not room_code:
        return
        
    # -----------------------------------------------------------------
    # >>> FIX: Khôi phục phòng từ DB nếu nó không có trong bộ nhớ (rooms)
    # -----------------------------------------------------------------
    if room_code not in rooms:
        restored_messages = load_room_data_from_sqlite(room_code)
        
        # if not restored_messages:
        #     # Nếu không tìm thấy trong bộ nhớ và cũng không tìm thấy lịch sử trong DB
        #     emit("match_error", {"message": "Lỗi: Phòng được tìm thấy không còn tồn tại hoặc đã bị xóa khỏi DB."})
        #     return
        
        # Nếu khôi phục thành công, phòng đã được thêm vào biến global 'rooms'
        print(f"Phòng {room_code} đã được khôi phục trong SocketIO handler.")
    
    # -----------------------------------------------------------------
        
    # 2. Tell the client's browser to redirect to the room's URL
    # (Đến đây, chúng ta đã đảm bảo phòng tồn tại trong 'rooms' trước khi chuyển hướng)
    room_url = url_for("chat_room_view", room_code=room_code)
    emit("redirect_to_room", {"url": room_url})
    print(f"Redirecting {name} to {room_url}")

@socketio.on("join_room_request")
def handle_join_room_request(data):
    name = session.get("username")
    room_code = data.get("room_code")
    
    if session.get('role') != 'therapist' or not room_code:
        return

    # 1. Rời khỏi phòng cũ (nếu có)
    old_room = session.get("room")
    if old_room and old_room != room_code:
        leave_room(old_room)
        print(f"Therapist {name} left room {old_room}.")

    # 2. Tham gia phòng mới
    join_room(room_code)
    session["room"] = room_code 
    session.modified = True
    print(f"Therapist {name} joined room {room_code}.")
    
    # Gửi lịch sử tin nhắn của phòng đó (Phải gửi lại cho chính người yêu cầu)
    if room_code in rooms:
        emit('room_history', {
            'room_code': room_code,
            'messages': rooms[room_code]["messages"]
        }, room=request.sid)
