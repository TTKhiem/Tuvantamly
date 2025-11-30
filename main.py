from globals import app, database, chatbot, socketio, rooms, connected_users
import os
import sqlite3
import json
from flask import request, jsonify, session, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO
import socket_handlers
# Import các module đã tách
import pet_system
import random
from datetime import datetime
from socket_helperfuncs import generate_unique_code1, get_user_data, notify_users_of_new_match,get_user_data_by_id
from socket_handlers import load_room_data_from_sqlite
from matchmaking_repository import get_all_matched_roomcodes_for_therapist,delete_match_by_roomcode,get_current_match_roomcode


#TESTING FUNCTION
def get_ai_summary_for_student(student_user_id):
    # Đây là placeholder, bạn có thể thay thế bằng logic truy vấn DB hoặc gọi AI sau.
    return [
        {"point": "Tình trạng chung: Lo lắng về thi cử."},
        {"point": "Cảm xúc: Buồn bã, tuyệt vọng."},
        {"point": "Điểm rủi ro: Cần được theo dõi sát sao."},
    ]


# --- ROUTES HIỂN THỊ TRANG (PAGE RENDERING) ---

@app.route('/')
def home():
    user_data, pet_data, quests_data = None, None, None
    if 'user_id' in session:
        db = database.get_db()
        user_data = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        pet_obj = pet_system.load_pet(db, session['user_id'])
        if pet_obj: pet_data = pet_obj.to_dict()
        quests_data = pet_system.get_daily_quests(db, session['user_id'])
    return render_template('index.html', user=user_data, pet=pet_data, quests=quests_data, form_type='login')

@app.route('/register_page')
def register_page():
    return render_template('index.html', form_type='register')

# --- ROUTES XÁC THỰC (AUTHENTICATION) ---
@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    db = database.get_db()
    try:
        hashed_pw = generate_password_hash(password)
        cursor = db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                   (username, email, hashed_pw))
        user_id = cursor.lastrowid
        db.execute("INSERT INTO pets (user_id, name) VALUES (?, ?)", (user_id, "Bạn Đồng Hành"))
        db.commit()
        flash("Đăng ký thành công! Hãy đăng nhập.", "success")
        return redirect(url_for('home'))
    except sqlite3.IntegrityError:
        flash("Email hoặc Username đã tồn tại!", "error")
        return redirect(url_for('register_page'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    db = database.get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role'] 
        flash(f"Chào mừng {user['username']}!", "success")

        if user['role'] == 'therapist':
            return redirect(url_for('therapist_dashboard_redirect'))
        else:
            return redirect(url_for('home'))
    else:
        flash("Sai email hoặc mật khẩu!", "error")
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for('home'))

# --- ROUTES DASHBOARD & USER PROFILE ---
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('home'))
    if session.get('role') == 'therapist': return redirect(url_for('therapist_dashboard_redirect'))
    
    db = database.get_db()
    user_data = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    
    # >> KIỂM TRA XEM CÓ ĐANG MATCH KHÔNG ĐỂ HIỆN NÚT
    current_match_code = get_current_match_roomcode(session['user_id'])
    
    return render_template('dashboard.html', user=user_data, current_match_code=current_match_code)

# 2. ROUTE MỚI: KẾT THÚC TRÒ CHUYỆN (Dùng chung cho cả 2)
@app.route('/end_chat', methods=['POST'])
def end_chat():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    room_code = request.form.get('room_code')
    role = session.get('role')

    if room_code:
        # Xóa khỏi DB matchmaking_results
        delete_match_by_roomcode(room_code)
        
        # Nếu muốn xóa luôn lịch sử chat, bạn có thể gọi thêm lệnh xóa chat_logs ở đây.
        # Nhưng thường thì nên giữ chat_logs lại để làm bằng chứng/lịch sử.
        
        # Cập nhật thông báo
        flash("Đã kết thúc cuộc trò chuyện thành công.", "success")
        
        # Xóa session phòng hiện tại để tránh join lại
        if session.get('room') == room_code:
            session['room'] = None

    # Chuyển hướng về trang tương ứng
    if role == 'therapist':
        return redirect(url_for('therapist_dashboard_redirect'))
    else:
        return redirect(url_for('dashboard'))
    
@app.route('/pet_page')
def pet_page():
    if 'user_id' not in session: return redirect(url_for('home'))
    return render_template('pet.html', username=session.get('username'))

@app.route('/user_profile')
def user_profile():
    if 'user_id' not in session: return redirect(url_for('home'))
    db = database.get_db()
    user_data = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    return render_template('dashboard.html', user=user_data)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session: return redirect(url_for('home'))
    db = database.get_db()
    db.execute('''UPDATE users SET date_of_birth=?, phone=?, address=? WHERE id=?''',
               (request.form['date_of_birth'], request.form['phone'], request.form['address'], session['user_id']))
    db.commit()
    flash("Đã cập nhật hồ sơ!", "success")
    return redirect(url_for('user_profile'))

# --- ROUTES CHATBOT TƯ VẤN ---
@app.route('/chat')
def chat_interface():
    if 'user_id' not in session:
        flash("Vui lòng đăng nhập để chat!", "error")
        return redirect(url_for('home'))
    return render_template('chat.html', user=session['username'])

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    
    user_msg = request.json.get('message')
    if 'chat_history' not in session: session['chat_history'] = []
    session['chat_history'].append({"role": "Sinh viên", "message": user_msg})
    
    analysis = chatbot.analyze_user_input(user_msg)
    risk = analysis.get('risk_level', 'low')
    intent = analysis.get('intent', 'unknown')
    
    bot_msg = chatbot.ADVICE_DATABASE.get("EMERGENCY") if risk == 'high' else chatbot.ADVICE_DATABASE.get(intent, chatbot.ADVICE_DATABASE["unknown"])
        
    session['chat_history'].append({"role": "Chatbot", "message": bot_msg})
    session.modified = True
    
    return jsonify({"response": bot_msg, "analysis": analysis})

@app.route('/api/chat/complete', methods=['POST'])
def api_chat_complete():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    
    history = session.get('chat_history', [])
    summary = chatbot.summarize_conversation(history)
    db = database.get_db()
    user_id = session['user_id']

    for msg in history:
        db.execute("INSERT INTO chat_history (user_id, role, message) VALUES (?, ?, ?)",
                   (user_id, msg['role'], msg['message']))
    
    db.execute("INSERT INTO intake_summary (user_id, summary_content) VALUES (?, ?)", (user_id, summary))
    db.commit()
    
    session.pop('chat_history', None)
    return jsonify({"summary": summary})

# --- ROUTES CHO THERAPIST ---


@app.route('/therapist/messenger')
def therapist_messenger():
    if session.get('role') != 'therapist' or 'user_id' not in session:
        flash("Bạn không có quyền truy cập trang này!", "error")
        return redirect(url_for('home'))

    user_id = session['user_id']
    therapist_matches = get_all_matched_roomcodes_for_therapist(user_id)
    active_chat_rooms = [] 

    for match in therapist_matches:
        room_code = match["roomcode"]
        student_user_id = match["student_user_id"]
        
        # 1. Khôi phục phòng vào bộ nhớ nếu cần (Quan trọng)
        load_room_data_from_sqlite(room_code) 
            
        # 2. Thu thập dữ liệu
        if room_code in rooms:
            student_data = get_user_data_by_id(student_user_id)
            messages = rooms[room_code]["messages"]
            last_message = messages[-1] if messages else None
            
            active_chat_rooms.append({
                "room_code": room_code,
                "student_name": student_data["username"] if student_data else f"Sinh viên {student_user_id}",
                "matched_at": match["matched_at"],
                "last_message": last_message,
                "ai_summary": get_ai_summary_for_student(student_user_id),
                "messages": messages, # Truyền lịch sử tin nhắn để JS load nhanh
            })
    
    # Thiết lập phòng mặc định và truyền dữ liệu ban đầu
    initial_messages = []
    initial_summary = []
    if active_chat_rooms:
        session["room"] = active_chat_rooms[0]["room_code"]
        initial_messages = active_chat_rooms[0]["messages"]
        initial_summary = active_chat_rooms[0]["ai_summary"]
    else:
        session["room"] = None
        
    # Chú ý: Bạn cần dùng | tojson | safe để truyền Array/List sang JS
    return render_template('therapist_dashboard.html', 
                           active_chat_rooms_json=json.dumps(active_chat_rooms), # <--- SỬA DÒNG NÀY
                           initial_messages_json=json.dumps(initial_messages),
                           initial_summary_json=json.dumps(initial_summary),
                           name=session['username'],
                           user_role='therapist')


@app.route('/therapist/dashboard')
def therapist_dashboard_redirect():
    return redirect(url_for('therapist_messenger'))

@app.route('/therapist/workspace')
def therapist_workspace():
    if session.get('role') != 'therapist':
        flash("Chỉ dành cho chuyên gia!", "error")
        return redirect(url_for('home'))
    return render_template('therapist_chat.html')



@app.route('/api/therapist/suggest', methods=['POST'])
def therapist_suggest():
    if session.get('role') != 'therapist': return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    suggestions = chatbot.get_therapist_suggestions(data.get('message'), data.get('context', []))
    if suggestions:
        return jsonify(suggestions)
    return jsonify({"error": "Failed to generate"}), 500


# --- API ROUTES CHO PET SYSTEM ---
def check_auth():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    return None

def get_all_game_data(db, user_id, pet=None):
    if pet is None:
        pet = pet_system.load_pet(db, user_id)
    return {
        "pet": pet.to_dict() if pet else None,
        "quests": pet_system.get_daily_quests(db, user_id),
        "gold": pet_system.get_user_gold(db, user_id),
        "inventory": pet_system.get_user_inventory(db, user_id)
    }

@app.route('/api/game_data')
def get_game_data_api():
    if err := check_auth(): return err
    return jsonify(get_all_game_data(database.get_db(), session['user_id']))

@app.route('/api/pet/action')
def get_pet_action():
    if err := check_auth(): return err
    db = database.get_db()
    pet = pet_system.load_pet(db, session['user_id'])
    if not pet: return jsonify({"error": "No pet found"}), 404
    action_result = pet.choose_action()
    pet_system.save_pet(db, pet)
    return jsonify(action_result)

@app.route('/api/complete_quest/<int:quest_id>', methods=['POST'])
def complete_quest_api(quest_id):
    if err := check_auth(): return err
    db, user_id = database.get_db(), session['user_id']
    quests = pet_system.get_daily_quests(db, user_id)
    quest = next((q for q in quests if q['id'] == quest_id), None)
    if quest and not quest["completed"]:
        pet, gold = pet_system.load_pet(db, user_id), pet_system.get_user_gold(db, user_id)
        pet_system.mark_quest_completed(db, user_id, quest_id)
        pet.gain_experience(quest.get("reward_exp", 0))
        pet_system.update_user_gold(db, user_id, gold + quest.get("reward_gold", 0))
        pet_system.save_pet(db, pet)
        return jsonify(get_all_game_data(db, user_id, pet))
    return jsonify({"error": "Invalid quest"}), 400

@app.route('/api/pet/feed', methods=['POST'])
def feed_pet_api():
    if err := check_auth(): return err
    db, user_id = database.get_db(), session['user_id']
    gold = pet_system.get_user_gold(db, user_id)
    if gold >= 10:
        pet = pet_system.load_pet(db, user_id)
        pet.feed()
        pet_system.update_user_gold(db, user_id, gold - 10)
        pet_system.save_pet(db, pet)
        return jsonify(get_all_game_data(db, user_id, pet))
    return jsonify({"error": "Not enough gold!"}), 400

@app.route('/api/pet/play', methods=['POST'])
def play_pet_api():
    if err := check_auth(): return err
    db, user_id = database.get_db(), session['user_id']
    pet = pet_system.load_pet(db, user_id)
    if pet.play():
        pet_system.save_pet(db, pet)
        return jsonify(get_all_game_data(db, user_id, pet))
    return jsonify({"error": "Pet is too tired to play!"}), 400

@app.route('/api/shop/items')
def get_shop_items_api():
    return jsonify(pet_system.SHOP_ITEMS)

@app.route('/api/shop/buy/<int:item_id>', methods=['POST'])
def buy_item_api(item_id):
    if err := check_auth(): return err
    db, user_id = database.get_db(), session['user_id']
    gold = pet_system.get_user_gold(db, user_id)
    inventory = pet_system.get_user_inventory(db, user_id)
    item = next((i for i in pet_system.SHOP_ITEMS if i['id'] == item_id), None)

    if not item: return jsonify({"error": "Item not found"}), 404
    
    # Nếu là skin mà đã có rồi thì báo lỗi
    if item['type'] == 'skin' and any(i['id'] == item_id for i in inventory): 
        return jsonify({"error": "Bạn đã sở hữu skin này rồi!"}), 400
    
    if gold < item['price']: return jsonify({"error": "Not enough gold"}), 400

    pet_system.update_user_gold(db, user_id, gold - item['price'])
    
    if item['type'] != 'food': 
        pet_system.add_item_to_inventory(db, user_id, item_id)
    else:
        # Thức ăn thì dùng luôn
        pet = pet_system.load_pet(db, user_id)
        pet.feed(item.get('value', 25))
        pet_system.save_pet(db, pet)
        
    return jsonify({"message": "Mua thành công!", "gold": pet_system.get_user_gold(db, user_id), "inventory": pet_system.get_user_inventory(db, user_id)})

# --- ROUTE MỚI: TRANG BỊ SKIN ---
@app.route('/api/pet/equip/<int:item_id>', methods=['POST'])
def equip_item_api(item_id):
    if err := check_auth(): return err
    db = database.get_db()
    user_id = session['user_id']
    
    # Kiểm tra xem user có item đó không (trừ item 0 là mặc định)
    inventory = pet_system.get_user_inventory(db, user_id)
    has_item = any(i['id'] == item_id for i in inventory)
    
    if item_id == 0 or has_item:
        pet_system.equip_skin(db, user_id, item_id)
        return jsonify(get_all_game_data(db, user_id))
    
    return jsonify({"error": "Bạn chưa sở hữu skin này!"}), 400


@app.route('/api/pet/chat', methods=['POST'])
def pet_chat_api():
    if err := check_auth(): return err
    db = database.get_db()
    pet = pet_system.load_pet(db, session['user_id'])
    if not pet: return jsonify({"error": "Không tìm thấy pet."}), 404
    
    user_message = request.json.get("message")
    bot_reply = chatbot.get_pet_chat_response(pet.base_name, user_message)
    
    return jsonify({"reply": bot_reply, "pet_face": pet.appearance.get("face", "^_^"), "pet_mood": pet.mood})

@app.route('/api/start_quest/<int:quest_id>')
def start_quest_api(quest_id):
    if err := check_auth(): return err
    quests = pet_system.get_daily_quests(database.get_db(), session['user_id'])
    quest = next((q for q in quests if q['id'] == quest_id), None)
    if quest and quest['type'] in ['quiz', 'puzzle', 'journaling', 'breathing']:
        return jsonify({"id": quest['id'], "type": quest['type'], "title": quest['title'], "data": quest['data']})
    return jsonify({"error": "Quest not found"}), 404


# === CÁC ROUTE CHO CHAT (Existing) ===

@app.route('/chat_home')
def chat_home():
# ... existing code ...
    if 'username' not in session:
        flash("Bạn cần đăng nhập để sử dụng chat!", "error")
        return redirect(url_for('home'))
    
    # Get user's tags to display on the page
    user_data = get_user_data(session.get('username'))
    user_tags = user_data.get('tags_list', [])

    return render_template('chat_home.html', name=session.get('username'), user_tags=user_tags)

@app.route('/chat_room', methods=["POST"])
def chat_room_post():
    name = session.get("username")
    if not name:
        return redirect(url_for('chat_home'))

    code = request.form.get("code")
    join = request.form.get("join", False)
    create = request.form.get("create", False)

    room = code
    
    # 1. Manual Room Creation
    if create != False:
        room = generate_unique_code1(4)
        rooms[room] = {"members": 0, "messages": []}
    
    # 2. Manual Room Joining
    elif join != False:
        if not code:
            flash("Vui lòng nhập mã phòng.", "error")
            return render_template("chat_home.html", name=name)
        
        # Room exists in active memory (rooms)
        if code in rooms:
            # Do nothing, just proceed to join. Messages are already in 'rooms'.
            pass 
        # Room does NOT exist in active memory (rooms), so check database
        else:
            loaded_messages = []
            with sqlite3.connect('app.db') as conn:
                cur = conn.cursor()
                cur.execute("SELECT username, message_text, timestamp FROM chat_logs WHERE room_code = ? ORDER BY timestamp ASC", (code,))
                existing_messages = cur.fetchall()
            
            if not existing_messages:
                # Room does not exist in memory OR in the database
                flash("Phòng không tồn tại.", "error")
                # Need to get user_tags for chat_home.html rendering
                user_data = get_user_data(name)
                user_tags = user_data.get('tags_list', [])
                return render_template("chat_home.html", name=name, user_tags=user_tags) 
            
            # Load messages from database
            for msg in existing_messages:
                try:
                    # Attempt to parse the timestamp (assuming it was saved as a string)
                    ts_obj = datetime.strptime(msg[2], '%Y-%m-%d %H:%M:%S.%f')
                    formatted_ts = ts_obj.strftime('%Y-%m-%d %H:%M')
                except ValueError:
                    formatted_ts = msg[2] # Fallback if format is different or missing
                loaded_messages.append({"name": msg[0], "message": msg[1], "timestamp": formatted_ts})
            
            # Add the room and its loaded messages to the active rooms dictionary
            rooms[code] = {"members": 0, "messages": loaded_messages}
            room = code # Ensure 'room' variable is set correctly

    # 3. Handle errors if no action was taken (e.g., neither join nor create)
    else:
        # Should not happen with the current form structure, but good for completeness
        flash("Hành động không hợp lệ.", "error")
        return redirect(url_for('chat_home'))

    session["room"] = room
    session.modified = True
    return redirect(url_for("chat_room_view", room_code=room))


# @app.route('/chat_room/<string:room_code>')
# def chat_room_view(room_code):
#     # room = session.get("room") <-- This was the bug. Session is empty.
#     name = session.get("username")

#     # If user isn't logged in, boot them.
#     if not name:
#         flash("Bạn cần đăng nhập để tham gia chat.", "error")
#         return redirect(url_for("home"))
        
#     # If room doesn't exist (e.g., from a bad link or old match), boot them.
#     if room_code not in rooms:
#         flash("Phòng chat này không tồn tại hoặc đã kết thúc.", "error")
#         return redirect(url_for("chat_home"))
        
#     # --- THIS IS THE FIX ---
#     # The user is logged in AND the room exists.
#     # Set the room in their session NOW, based on the URL.
#     session["room"] = room_code
#     session.modified = True # <-- ADD THIS LINE
#     # Now, render the page.
#     return render_template("chat_room.html", code=room_code, messages=rooms[room_code]["messages"], name=name)


@app.route('/chat_room/<string:room_code>')
def chat_room_view(room_code):
    name = session.get("username")

    if not name:
        flash("Bạn cần đăng nhập để tham gia chat.", "error")
        return redirect(url_for("home"))
        
    # --- LOGIC KHÔI PHỤC PHÒNG (QUAN TRỌNG) ---
    if room_code not in rooms:
        # Nếu phòng không tồn tại trong bộ nhớ, thử tải lại từ DB
        restored_messages = load_room_data_from_sqlite(room_code) # load_room_data_from_sqlite sẽ tự động khôi phục vào global rooms
        
        if not restored_messages:
            flash("Phòng chat này không tồn tại hoặc đã kết thúc.", "error")
            return redirect(url_for("chat_home"))
    # --- END LOGIC KHÔI PHỤC PHÒNG ---

    # Phòng đã sẵn sàng (trong bộ nhớ hoặc đã được khôi phục)
    session["room"] = room_code
    session.modified = True 
    return render_template("chat_room.html", code=room_code, messages=rooms[room_code]["messages"], name=name,user_role=session.get('role'))

# --- MAIN ---
if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        with app.app_context():
            database.init_db()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
    # app.run(host='0.0.0.0', port=5000, debug=True)
