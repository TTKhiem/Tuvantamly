from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_socketio import join_room, leave_room, send, SocketIO, emit
import sqlite3
import os
from datetime import datetime
import re
from werkzeug.security import generate_password_hash
import random
from string import ascii_uppercase
from decorators import admin_required, student_required, therapist_required
from matchmaking.matchmaking_repository import add_student_to_matchmaking_queue, add_therapist_to_matchmaking_queue, get_therapist_expertise_tag, check_student_already_matched, check_student_already_in_matchmaking_queue, check_therapist_already_in_matchmaking_queue, delete_student_from_matchmaking_queue, delete_therapist_from_matchmaking_queue
from matchmaking.matchmaking_logic import run_matchmaking
from chat_with_therapist.chat_routes import chat_bp


app = Flask(__name__)
app.secret_key = 'secret-key'
app.register_blueprint(chat_bp)
socketio = SocketIO(app, cors_allowed_origins="*")

# === NEW: In-memory storage for matchmaking ===
rooms = {} 
# Stores {room_code: {"members": 0, "messages": []}}

connected_users = {} 
# Stores {username: sid} - Maps a username to their unique Socket.IO SID
# This is how we send a direct message to a user *before* they're in a room

matchmaking_queue = [] 
# Stores list of users waiting for a match
# e.g., [{"username": "Alice", "sid": "sid_A", "tags": ["tag1", "tag2"]}]
# ===============================================

def generate_unique_code(length):
# ... existing code ...
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        if code not in rooms:
            break
    return code

# --- Database Helper Function ---
def get_user_data(username):
# ... existing code ...
    """Fetches user data, including tags, from the DB."""
    with sqlite3.connect('users.db') as conn:
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
            user_dict['tags_list'] = tags_list # return list of tags
            return user_dict
        return None

# --- NEW: Database Initialization Function ---
db_path = 'users.db'
schema_path = 'schema.sql'
def init_db():
# ... existing code ...
    """
    Initializes the database using the schema.sql file.
    This creates the tables if they don't exist and inserts
    the default admin user if it's not already present.
    """
    
    # Check if the schema file exists
    if not os.path.exists(schema_path):
        print(f"Error: '{schema_path}' not found. Cannot initialize database.")
        return

    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
            # Read the SQL commands from the schema.sql file
            with open(schema_path, 'r') as f:
                sql_script = f.read()
            
            # Execute all commands in the file (creates tables, inserts admin)
            cur.executescript(sql_script)
            conn.commit()
            print("Database initialized successfully.")
            
    except sqlite3.Error as e:
        print(f"An error occurred while initializing the database: {e}")
        
# === Standard HTTP Routes ===

@app.route('/')
def home():
# ... existing code ...
    user = None
    if 'username' in session:
        user = {'username': session['username'], 'role': session['role']}
    return render_template('index.html', form_type='login', user=user)

@app.route('/register_page')
def register_page():
# ... existing code ...
    return render_template('index.html', form_type='register')

@app.route('/login', methods=['POST'])
def login():
# ... existing code ...
    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        flash("Vui lòng nhập email và mật khẩu!", "danger")
        return redirect(url_for('login'))

    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cur.fetchone()
    if user:
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['role'] = user[4]
        flash(f"Chào mừng {session['username']}!", "success")
        return redirect(url_for('home'))
    else:
        return "Sai email hoặc mật khẩu!"

@app.route('/register', methods=['POST'])
def register():
# ... existing code ...
    # ... (Your existing register code)
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing = cur.fetchone()

        if existing:
            flash("Email đã tồn tại!", "error")
            return redirect(url_for('register_page'))
        else:
            # Store tags as an empty string for now
            cur.execute("INSERT INTO users (username, email, password, tags) VALUES (?, ?, ?, ?)", 
                        (username, email, password, "")) # Add empty tags
            conn.commit()
            flash(f"Đăng ký thành công! Hãy đăng nhập, {username} 🎉", "success")
            return redirect(url_for('home'))

@app.route('/user')
def user_dashboard():
# ... existing code ...
    if 'username' not in session:
        return redirect(url_for('home'))
    
    # Use our helper function to get user data
    user_data = get_user_data(session['username'])
    if not user_data:
        flash("Lỗi: Không tìm thấy người dùng.", "error")
        return redirect(url_for('logout'))

    return render_template('user_dashboard.html', user=user_data)

@app.route('/admin')
def admin_dashboard():
# ... existing code ...
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('home'))
    return f"Chào quản trị viên {session['username']} 🛠️"   

@app.route('/logout')
def logout():
# ... existing code ...
    session.clear()
    return redirect(url_for('home'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
# ... existing code ...
    if 'username' not in session:
        return redirect(url_for('home'))

    username = session['username']
    date_of_birth = request.form.get('date_of_birth')
    phone = request.form.get('phone')
    address = request.form.get('address')
    tags = request.form.get('tags') # <-- NEW: Get tags from form

    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute('''
            UPDATE users 
            SET date_of_birth = ?, phone = ?, address = ?, tags = ?, date_joined = ?
            WHERE username = ?
        ''', (date_of_birth, phone, address, tags, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username))
        conn.commit()

    flash("Cập nhật thông tin thành công!", "success")
    return redirect(url_for('user_dashboard'))

@app.route("/update-student-topic-tag", methods=['POST'])
def update_student_topic_tag():
# ... existing code ...
    if 'username' not in session:
        return redirect(url_for('home'))

    username = session.get('username')
    data = request.get_json()
    tags = data.get("tags") # <-- NEW: Get tags from form

    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute('''
            UPDATE users 
            SET tags = ?
            WHERE username = ?
        ''', (tags, username))
        conn.commit()
    
    return jsonify({"status": "ok", "tags": tags})


# === CÁC ROUTE CHO matchmaking ===

@app.route("/matchmaking/student")
@student_required
def student_matchmaking():
    user_id = session["user_id"]
    is_in_queue = check_student_already_in_matchmaking_queue(user_id)
    is_matched = check_student_already_matched(user_id)
    return render_template("matchmaking_student.html", is_in_queue=is_in_queue, is_matched=is_matched)

@app.route("/matchmaking/therapist")
@therapist_required
def therapist_matchmaking():
    user_id = session["user_id"]
    is_in_queue = check_therapist_already_in_matchmaking_queue(user_id)
    return render_template("matchmaking_therapist.html", is_in_queue=is_in_queue)

@app.route("/api/matchmaking/student-normal", methods = ["POST"])
@student_required
def api_matchmaking_student_normal():
    user_id = session.get("user_id")
    urgency = 0
    topic = request.get_json().get("topic")
    add_student_to_matchmaking_queue(user_id, urgency, topic)
    run_matchmaking()
    return redirect(url_for("student_matchmaking"))

@app.route("/api/matchmaking/student-urgent", methods = ["POST"])
@student_required
def api_matchmaking_student_urgent():
    user_id = session.get("user_id")
    urgency = 1
    topic = "urgent"
    add_student_to_matchmaking_queue(user_id, urgency, topic)
    run_matchmaking()
    return redirect(url_for("student_matchmaking"))

@app.route("/api/matchmaking/student-cancel", methods = ["POST"])
@student_required
def api_matchmaking_student_cancel():
    user_id = session.get("user_id")
    delete_student_from_matchmaking_queue(user_id)
    return redirect(url_for("student_matchmaking"))

@app.route("/api/matchmaking/therapist", methods = ["POST"])
@therapist_required
def api_matchmaking_therapist():
    user_id = session.get("user_id")
    expertise = get_therapist_expertise_tag(user_id)[0]
    add_therapist_to_matchmaking_queue(user_id, expertise)
    run_matchmaking()
    return redirect(url_for("therapist_matchmaking"))

@app.route("/api/matchmaking/therapist-cancel", methods = ["POST"])
@therapist_required
def api_matchmaking_therapist_cancel():
    user_id = session.get("user_id")
    delete_therapist_from_matchmaking_queue(user_id)
    return redirect(url_for("therapist_matchmaking"))


# ===========================================================================================================


# === CÁC ROUTE CHO CHAT (Existing) ===

@app.route('/chat')
def chat_home():
# ... existing code ...
    if 'username' not in session:
        flash("Bạn cần đăng nhập để sử dụng chat!", "error")
        return redirect(url_for('home'))
    
    # Get user's tags to display on the page
    username = session.get('username')
    user_data = get_user_data(username)
    # ko để tag trong table nữa
    user_tags = user_data.get('tags_list', [])
    user_role = session.get('role')

    with sqlite3.connect("users.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT room_code 
            FROM chat_logs 
            WHERE username = ?
            ORDER BY timestamp DESC
        """, (username,))
        rooms = [row[0] for row in cur.fetchall()]

    return render_template('chat_home.html', name=username, user_tags=user_tags, user_role = user_role, rooms=rooms)

@app.route('/chat_room', methods=["POST"])
def chat_room_post():
# ... existing code ...
    # This route is for MANUAL room creation/joining
    name = session.get("username")
    if not name:
        return redirect(url_for('chat_home'))

    code = request.form.get("code")
    join = request.form.get("join", False)
    create = request.form.get("create", False)

    if join != False and not code: # bấm nút join room mà ko có code phòng
        flash("Vui lòng nhập mã phòng.", "error")
        return redirect(url_for('chat_home'))

    room = code
    if create != False: # bấm nút create room
        room = generate_unique_code(4)
        rooms[room] = {"members": 0, "messages": []}
    elif code not in rooms: # bấm nút join room mà code phòng không tồn tại trong memory
        with sqlite3.connect('users.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT username, message_text, timestamp FROM chat_logs WHERE room_code = ? ORDER BY timestamp ASC", (code,))
            existing_messages = cur.fetchall()
        if not existing_messages: # coi db rồi mà phòng không tồn tại
            flash("Phòng không tồn tại.", "error")
            return redirect(url_for('chat_home'))
        
        loaded_messages = []
        for msg in existing_messages:
            try: # đổi format ngày giờ
                ts_obj = datetime.strptime(msg[2], '%Y-%m-%d %H:%M:%S.%f')
                formatted_ts = ts_obj.strftime('%Y-%m-%d %H:%M')
            except ValueError:
                formatted_ts = msg[2] # Fallback
            loaded_messages.append({"name": msg[0], "message": msg[1], "timestamp": formatted_ts})
        
        rooms[code] = {"members": 0, "messages": loaded_messages} # lưu code phòng vào memory

    session["room"] = room
    return redirect(url_for("chat_room_view", room_code=room))

@app.route('/chat_room/<string:room_code>')
def chat_room_view(room_code):
    # room = session.get("room") <-- This was the bug. Session is empty.
    name = session.get("username")

    # If user isn't logged in, boot them.
    if not name:
        flash("Bạn cần đăng nhập để tham gia chat.", "error")
        return redirect(url_for("home"))
        
    # Check if this user has ever joined this room in chat_logs
    with sqlite3.connect("users.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) 
            FROM chat_logs 
            WHERE room_code = ? AND username = ?
        """, (room_code, name))
        exists = cur.fetchone()[0]

    if exists == 0:
        print("check")
        flash("Phòng chat này không tồn tại hoặc đã kết thúc.", "error")
        return redirect(url_for("chat_home"))
        

    # Fetch all messages for this room
    with sqlite3.connect("users.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT username, message_text, timestamp
            FROM chat_logs
            WHERE room_code = ?
            ORDER BY timestamp ASC
        """, (room_code,))
        messages = cur.fetchall()

    # --- THIS IS THE FIX ---
    # The user is logged in AND the room exists.
    # Set the room in their session NOW, based on the URL.
    session["room"] = room_code
    
    # Now, render the page.
    return render_template("chat_room.html", code=room_code, messages=messages, name=name)

# === CÁC HÀM XỬ LÝ SOCKET.IO ===

# def try_to_make_matches():
# # ... existing code ...
#     """Logic to find a match in the queue."""
#     # This is a simple O(n^2) search.
#     # For a real app, you'd use a more efficient algorithm.
    
#     # For demo: We match two "client" roles (as you said)
#     # We will match the first two users in the queue who share *any* tag
    
#     i = 0
#     while i < len(matchmaking_queue):
#         j = i + 1
#         while j < len(matchmaking_queue):
#             user_a = matchmaking_queue[i]
#             user_b = matchmaking_queue[j]
            
#             # Find common tags
#             common_tags = set(user_a["tags"]) & set(user_b["tags"])
            
#             if common_tags:
#                 print(f"MATCH FOUND: {user_a['username']} and {user_b['username']} on tags: {common_tags}")
                
#                 # 1. Remove both from queue (careful with indices)
#                 # Remove higher index first
#                 matchmaking_queue.pop(j)
#                 matchmaking_queue.pop(i)
                
#                 # 2. Create a new room for them
#                 new_room_code = generate_unique_code(6) # 6 chars for matched rooms
#                 rooms[new_room_code] = {"members": 0, "messages": []}
                
#                 # 3. Notify both users using their SID
#                 match_data = {
#                     "room_code": new_room_code,
#                     "matched_with": user_b["username"],
#                     "tags": list(common_tags)
#                 }
#                 socketio.emit("match_found", match_data, to=user_a["sid"])
                
#                 match_data["matched_with"] = user_a["username"] # Update for user B
#                 socketio.emit("match_found", match_data, to=user_b["sid"])
                
#                 # --- THIS IS THE FIX ---
#                 # A match was made. Stop searching and exit the function.
#                 return
#                 # -----------------------
            
#             j += 1
#         i += 1


def notify_users_of_new_match(student_user_id, therapist_user_id, student_session_id, therapist_session_id):
    # """
    # Emit a 'new_match' event to both student and therapist when a match is created.
    # Front-end can listen to this event to update sidebar and allow joining the room.
    # """
    print(f"MATCH FOUND: {student_user_id}, {therapist_user_id}, {student_session_id}, {therapist_session_id}")
    # 2. Create a new room for them
    new_room_code = generate_unique_code(6) # 6 chars for matched rooms
    rooms[new_room_code] = {"members": 0, "messages": []}
    
    # 3. Notify both users using their SID
    match_data = {
        "room_code": new_room_code,
        "matched_with": "{student_user_id} và {therapist_user_id}",
    }
    socketio.emit("match_found", match_data, to=student_session_id)
    socketio.emit("match_found", match_data, to=therapist_session_id)
    print("check")
    
    # --- THIS IS THE FIX ---
    # A match was made. Stop searching and exit the function.
    return
    # -----------------------


@socketio.on("connect")
def connect(auth):
# ... existing code ...
    name = session.get("username")
    room = session.get("room") # This will be None if they're on chat_home
    sid = request.sid

    if not name:
        return # Not logged in, disconnect
    
    # --- Matchmaking System ---
    # Track every connected user, even if they're not in a room yet
    connected_users[name] = sid
    print(f"CLIENT CONNECTED: {name} (SID: {sid})")
    print(f"Connected users: {list(connected_users.keys())}")
    
    # --- Standard Room System ---
    if not room:
        return # User is on chat_home, not in a room yet
    
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    now_display_format = datetime.now().strftime('%Y-%m-%d %H:%M')
    send({"name": name, "message": "đã tham gia phòng.", "timestamp": now_display_format}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} tham gia phòng {room}")

@socketio.on("disconnect")
def disconnect():
# ... existing code ...
    name = session.get("username")
    room = session.get("room")
    sid = request.sid # Get sid one last time

    # --- Matchmaking System ---
    if name in connected_users:
        del connected_users[name]
        print(f"CLIENT DISCONNECTED: {name} (SID: {sid})")
        print(f"Connected users: {list(connected_users.keys())}")

    # Remove user from matchmaking queue if they disconnect
    global matchmaking_queue
    matchmaking_queue = [u for u in matchmaking_queue if u["username"] != name]
    
    # --- Standard Room System ---
    if room and room in rooms:
        leave_room(room)
        rooms[room]["members"] -= 1
        now_display_format = datetime.now().strftime('%Y-%m-%d %H:%M')
        send({"name": name, "message": "đã rời phòng.", "timestamp": now_display_format}, to=room)
        
        if rooms[room]["members"] <= 0:
            del rooms[room] # Or keep for history, as before
        
        print(f"{name} đã rời phòng {room}")

@socketio.on("message")
def message(data):
# ... existing code ...
    room = session.get("room")
    name = session.get("username")
    if room not in rooms or not name:
        return 
    
    now = datetime.now()
    now_db_format = now.strftime("%Y-%m-%d %H:%M:%S.%f") 
    now_display_format = now.strftime('%Y-%m-%d %H:%M') 
    
    content = {
        "name": name,
        "message": data["data"],
        "timestamp": now_display_format
    }
    
    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_logs (room_code, username, message_text, timestamp) VALUES (?, ?, ?, ?)",
            (room, name, data["data"], now_db_format)
        )
        conn.commit()
    
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{name} (phòng {room}): {data['data']}")

# === NEW: Socket.IO Handlers for Matchmaking ===

@socketio.on("find_match")
def find_match(): # <--- THE FIX: Removed the 'data' argument
    name = session.get("username")
    role = session.get("role")
    user_id = session.get("user_id")
    
    if not name:
        return

    # Check if user is already in the queue
    if role == "student":
        if check_student_already_in_matchmaking_queue(user_id) == True:
            print(f"{name} is already in the queue.")
            return
    elif role == "therapist":
        if check_therapist_already_in_matchmaking_queue(user_id) == True:
            print(f"{name} is already in the queue.")
            return

    # Get user's tags from the database
    user_data = get_user_data(name)
    if not user_data or not user_data.get('tags_list'):
        emit("match_error", {"message": "Vui lòng thêm 'tags' vào hồ sơ của bạn để kết nối."})
        return

    user_tags = user_data['tags_list']
    
    # Add user to the queue
    if role == "student":
        add_student_to_matchmaking_queue(user_id, 0, user_tags[0], connected_users[name])
    elif role == "therapist":
        add_therapist_to_matchmaking_queue(user_id, user_tags[0], connected_users[name])
    print(f"Added {name} to matchmaking queue with tags: {user_tags}")
    emit("finding_match", {"message": "Đang tìm kiếm người phù hợp..."})
    
    # Try to find a match
    run_matchmaking()

@socketio.on("cancel_match")
def cancel_match():
# ... existing code ...
    name = session.get("username")
    role = session.get("role")
    user_id = session.get("user_id")
    if not name:
        return
    if not user_id:
        print("User is not in session! Cannot cancel.")
        return
        
    if role == "student":
        delete_student_from_matchmaking_queue(user_id)
    elif role == "therapist":
        delete_therapist_from_matchmaking_queue(user_id)
    
    print(f"Removed {name} from matchmaking queue.")
    emit("match_cancelled", {"message": "Đã hủy tìm kiếm."})

@socketio.on("join_private_room")
def join_private_room(data):
    """
    Client emits this after clicking the 'Join' button
    from the 'match_found' notification.
    """
    name = session.get("username")
    room_code = data.get("room_code")
    
    if not name or not room_code:
        return
        
    if room_code not in rooms:
        emit("match_error", {"message": "Lỗi: Phòng được tìm thấy không còn tồn tại."})
        return
        
    # session["room"] = room_code 
    # -----------------------------------------------
        
    # 2. Tell the client's browser to redirect to the room's URL
    room_url = url_for("chat_room_view", room_code=room_code)
    emit("redirect_to_room", {"url": room_url})
    print(f"Redirecting {name} to {room_url}")

if __name__ == '__main__':
   init_db() # <-- ADD THIS LINE to run the DB setup on start
   socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)