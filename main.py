from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from datetime import datetime
# from create_therapists import get_therapists
import re

from werkzeug.security import generate_password_hash
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

app = Flask(__name__)
app.secret_key = 'secret-key'  # Dùng cho flash message
socketio = SocketIO(app)
rooms = {} # Thêm bộ nhớ cho phòng chat

# ✅ Tạo database nếu chưa có

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break
    return code


@app.route('/')
def home():
    user = None
    if 'username' in session:
        user = {'username': session['username'], 'role': session['role']}
    return render_template('index.html', form_type='login', user=user)

@app.route('/register_page')

def register_page():
    return render_template('index.html', form_type='register')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cur.fetchone()

    # if user:
    #     session['username'] = user[1]
    #     session['role'] = user[4]   # cột role

    #     if session['role'] == 'admin':
    #         return redirect(url_for('admin_dashboard'))
    #     else:
    #         return redirect(url_for('user_dashboard'))
    if user:
        session['username'] = user[1]
        session['role'] = user[4]  # cột role
        flash(f"Chào mừng {session['username']}!", "success")
        return redirect(url_for('home'))  # ✅ luôn quay về home

    else:
        return "Sai email hoặc mật khẩu!"
 

# @app.route('/register', methods=['POST'])
# def register():
#     username = request.form.get('username')
#     email = request.form.get('email')
#     password = request.form.get('password')

#     with sqlite3.connect('users.db') as conn:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM users WHERE email = ?", (email,))
#         existing = cur.fetchone()

#         if existing:
#             flash("Email đã tồn tại!", "error")
#             return redirect(url_for('register_page'))
#         else:
#             cur.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
#                         (username, email, password))
#             conn.commit()
#             flash(f"Đăng ký thành công! Hãy đăng nhập, {username} 🎉", "success")
#             return redirect(url_for('home'))  # ⬅️ Redirect về home để login
@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    # 1️⃣ Kiểm tra trống
    if not username or not email or not password:
        flash("Vui lòng nhập đầy đủ thông tin!", "error")
        return redirect(url_for('register_page'))

    # 2️⃣ Kiểm tra định dạng email hợp lệ (mọi tên miền, miễn đúng cú pháp)
    email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not re.match(email_pattern, email):
        flash("Email không hợp lệ! Vui lòng nhập đúng định dạng (vd: ten@gmail.com).", "error")
        return redirect(url_for('register_page'))

    # 3️⃣ Kiểm tra username (chỉ cho phép chữ, số, gạch dưới; 3–20 ký tự)
    if not re.match(r'^[A-Za-z0-9_]{3,20}$', username):
        flash("Tên người dùng chỉ được chứa chữ, số hoặc dấu gạch dưới (3-20 ký tự).", "error")
        return redirect(url_for('register_page'))

    # 4️⃣ Kiểm tra độ mạnh mật khẩu (ít nhất 6 ký tự, có cả chữ và số)
    if len(password) < 6 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        flash("Mật khẩu phải có ít nhất 6 ký tự, bao gồm cả chữ và số!", "error")
        return redirect(url_for('register_page'))

    # 5️⃣ Kiểm tra email trùng trong database
    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing = cur.fetchone()

        if existing:
            flash("Email này đã được đăng ký! Hãy thử email khác.", "error")
            return redirect(url_for('register_page'))

        # 6️⃣ Hash mật khẩu để bảo mật trước khi lưu
        hashed_password = generate_password_hash(password)

        # 7️⃣ Thêm user vào database
        cur.execute("""
            INSERT INTO users (username, email, password)
            VALUES (?, ?, ?)
        """, (username, email, hashed_password))
        conn.commit()

    # 8️⃣ Thông báo thành công
    flash(f"Đăng ký thành công! Hãy đăng nhập, {username} 🎉", "success")
    return redirect(url_for('home'))
@app.route('/user')
def user_dashboard():
    if 'role' not in session or session['role'] != 'user':
        return redirect(url_for('home'))
    
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row  # cho phép truy cập theo tên cột
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (session['username'],))
        user_data = cur.fetchone()

    return render_template('user_dashboard.html', user=user_data)

@app.route('/admin')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('home'))
    return f"Chào quản trị viên {session['username']} 🛠️"   
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        return redirect(url_for('home'))

    username = session['username']
    date_of_birth = request.form.get('date_of_birth')
    phone = request.form.get('phone')
    address = request.form.get('address')

    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute('''
            UPDATE users 
            SET date_of_birth = ?, phone = ?, address = ?, date_joined = ?
            WHERE username = ?
        ''', (date_of_birth, phone, address, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username))
        conn.commit()

    flash("Cập nhật thông tin thành công!", "success")
    return redirect(url_for('user_dashboard'))


# === CÁC ROUTE CHO CHAT ===

@app.route('/chat')
def chat_home():
    # Kiểm tra xem đã đăng nhập chưa
    if 'username' not in session:
        flash("Bạn cần đăng nhập để sử dụng chat!", "error")
        return redirect(url_for('home'))

    # Lấy tên từ session và hiển thị trang chọn phòng
    return render_template('chat_home.html', name=session.get('username'))

@app.route('/chat_room', methods=["POST"])
def chat_room_post():
    name = session.get("username")
    if not name:
        return redirect(url_for('chat_home'))

    code = request.form.get("code")
    join = request.form.get("join", False)
    create = request.form.get("create", False)

    if join != False and not code:
        flash("Vui lòng nhập mã phòng.", "error")
        return render_template("chat_home.html", name=name)

    room = code
    if create != False:
        room = generate_unique_code(4)
        # New room, so message history is empty
        rooms[room] = {"members": 0, "messages": []}
    elif code not in rooms:
        # Room isn't in memory. Check DB for history.
        with sqlite3.connect('users.db') as conn:
            cur = conn.cursor()
            # Select messages for this room
            cur.execute("SELECT username, message_text, timestamp FROM chat_logs WHERE room_code = ? ORDER BY timestamp ASC", (code,))
            existing_messages = cur.fetchall()

        if not existing_messages:
            # No history found. This room code is invalid.
            flash("Phòng không tồn tại.", "error")
            return render_template("chat_home.html", name=name)
        
        # Room exists, load its history into memory
        loaded_messages = []
        for msg in existing_messages:
            # Parse the full timestamp string from DB
            ts_obj = datetime.strptime(msg[2], '%Y-%m-%d %H:%M:%S.%f')
            # Format it for display
            formatted_ts = ts_obj.strftime('%Y-%m-%d %H:%M')
            loaded_messages.append({"name": msg[0], "message": msg[1], "timestamp": formatted_ts})
        
        rooms[code] = {"members": 0, "messages": loaded_messages}
        print(f"Loaded {len(loaded_messages)} messages for room {code} from DB.")

    session["room"] = room
    return redirect(url_for("chat_room_view", room_code=room))


@app.route('/chat_room/<string:room_code>')
def chat_room_view(room_code):
    room = session.get("room")
    name = session.get("username")

    if not name or not room or room != room_code or room not in rooms:
        flash("Lỗi truy cập phòng chat. Vui lòng thử lại.", "error")
        session.pop("room", None)
        return redirect(url_for("chat_home"))

    # Pass the pre-loaded messages (from DB or new) to the template
    return render_template("chat_room.html", code=room, messages=rooms[room]["messages"], name=name)

# === CÁC HÀM XỬ LÝ SOCKET.IO ===

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("username")

    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    # Add timestamp to server messages
    now_display_format = datetime.now().strftime('%Y-%m-%d %H:%M')
    send({"name": name, "message": "đã tham gia phòng.", "timestamp": now_display_format}, to=room)
    
    rooms[room]["members"] += 1
    print(f"{name} tham gia phòng {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("username")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        # Add timestamp to server messages
        now_display_format = datetime.now().strftime('%Y-%m-%d %H:%M')
        send({"name": name, "message": "đã rời phòng.", "timestamp": now_display_format}, to=room)

        if rooms[room]["members"] <= 0:
            # You might want to keep the room in memory if you want to keep logs
            # Or you can delete it. DB history will still be saved.
            del rooms[room]

        print(f"{name} đã rời phòng {room}")

@socketio.on("message")
def message(data):
    room = session.get("room")
    name = session.get("username")
    if room not in rooms or not name:
        return 

    now = datetime.now()
    # Format for DB (precise)
    now_db_format = now.strftime("%Y-%m-%d %H:%M:%S.%f") 
    # Format for display (clean)
    now_display_format = now.strftime('%Y-%m-%d %H:%M') 
    
    # 1. Create content for sending to clients
    content = {
        "name": name,
        "message": data["data"],
        "timestamp": now_display_format # Send the clean format
    }
    
    # 2. Save the message to the database
    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_logs (room_code, username, message_text, timestamp) VALUES (?, ?, ?, ?)",
            (room, name, data["data"], now_db_format) # Save the precise format
        )
        conn.commit()

    # 3. Send to clients
    send(content, to=room)
    
    # 4. Save to in-memory list (for new users joining this session)
    rooms[room]["messages"].append(content)
    
    print(f"{name} (phòng {room}): {data['data']}")





if __name__ == '__main__':
    
   socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
