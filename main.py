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
from chatbot import analyze_student_state
from socket_helperfuncs import generate_unique_code1, get_user_data, notify_users_of_new_match,get_user_data_by_id
from socket_handlers import load_room_data_from_sqlite
from matchmaking_repository import get_all_matched_roomcodes_for_therapist,delete_match_by_roomcode,get_current_match_roomcode,get_all_users,get_all_matchmaking_results,admin_create_match_result


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


        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard')) 
        elif user['role'] == 'therapist':
            return redirect(url_for('therapist_dashboard_redirect'))
        elif user['tags'] == '':
            return redirect(url_for('chat_interface'))
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
    if session.get('role') == 'admin': return redirect(url_for('admin_dashboard'))
    
    db = database.get_db()
    user_data = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    
    # --- [THÊM MỚI] LẤY DỮ LIỆU PET VÀ QUEST ---
    pet_data = None
    pet_obj = pet_system.load_pet(db, session['user_id'])
    if pet_obj: 
        pet_data = pet_obj.to_dict()
        
    quests_data = pet_system.get_daily_quests(db, session['user_id'])
    # -------------------------------------------
    # KIỂM TRA XEM CÓ ĐANG MATCH KHÔNG
    current_match_code = get_current_match_roomcode(session['user_id'])
    # Gửi thêm biến pet và quests sang template
    return render_template('dashboard.html', 
                           user=user_data, 
                           current_match_code=current_match_code,
                           pet=pet_data,      # <--- QUAN TRỌNG
                           quests=quests_data) # <--- QUAN TRỌNG

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
    if 'user_id' not in session: 
        return redirect(url_for('home'))
    
    # --- THÊM ĐOẠN KIỂM TRA NÀY ---
    db = database.get_db()
    
    # Kiểm tra xem user đã có pet trong DB chưa
    has_pet = db.execute("SELECT 1 FROM pets WHERE user_id = ?", (session['user_id'],)).fetchone()
    
    if not has_pet:
        # Nếu chưa có pet, đá về Dashboard để nhận nuôi
        flash("Bạn chưa có thú cưng! Hãy nhận nuôi tại Dashboard trước nhé.", "info")
        return redirect(url_for('dashboard'))
    # ------------------------------

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
    
    # 1. Phân tích ngầm (để lưu DB hoặc cảnh báo)
    analysis = chatbot.analyze_user_input(user_msg)
    
    # 2. Sinh câu trả lời "có hồn" dựa trên lịch sử
    # Truyền cả lịch sử chat vào để AI nhớ ngữ cảnh
    # (Lưu ý: history ở đây là CÁC TIN NHẮN CŨ, không bao gồm tin nhắn hiện tại user vừa gửi, vì tin đó được truyền qua tham số user_message rồi)
    bot_msg = chatbot.generate_soulmate_response(user_msg, session['chat_history'])
    
    # 3. SAU KHI CÓ CÂU TRẢ LỜI, MỚI LƯU CẢ 2 VÀO HISTORY
    session['chat_history'].append({"role": "Sinh viên", "message": user_msg})
    session['chat_history'].append({"role": "Chatbot", "message": bot_msg})
    session.modified = True
    
    return jsonify({"response": bot_msg, "analysis": analysis})

@app.route('/api/chat/complete', methods=['POST'])
def api_chat_complete():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    
    history = session.get('chat_history', [])
    user_id = session['user_id']
    db = database.get_db()

    # 1. Tóm tắt cuộc hội thoại (Logic cũ)
    summary = chatbot.summarize_conversation(history)
    
    # 2. [MỚI] Trích xuất Tags từ AI
    detected_tags = chatbot.extract_tags_from_conversation(history)
    print(f"--- AI DETECTED TAGS FOR USER {user_id}: {detected_tags} ---")

    # 3. Lưu lịch sử chat vào bảng chat_history (Logic cũ)
    for msg in history:
        db.execute("INSERT INTO chat_history (user_id, role, message) VALUES (?, ?, ?)",
                   (user_id, msg['role'], msg['message']))
    
    # 4. Lưu tóm tắt vào bảng intake_summary (Logic cũ)
    db.execute("INSERT INTO intake_summary (user_id, summary_content) VALUES (?, ?)", (user_id, summary))
    
    # 5. [MỚI] Cập nhật Tags vào bảng Users
    # Chỉ cập nhật nếu user chưa có tags hoặc muốn ghi đè tags mới nhất
    db.execute("UPDATE users SET tags = ? WHERE id = ?", (detected_tags, user_id))
    
    db.commit()
    
    # Xóa lịch sử trong session
    session.pop('chat_history', None)
    
    # Cập nhật session tags luôn để không cần login lại mới thấy
    session['tags'] = detected_tags

    return jsonify({"summary": summary, "tags": detected_tags}) 

# --- ROUTES CHO THERAPIST ---


@app.route('/therapist/dashboard')
def therapist_dashboard():
    if session.get('role') != 'therapist' or 'user_id' not in session:
        flash("Bạn không có quyền truy cập trang này!", "error")
        return redirect(url_for('home'))

    user_id = session['user_id']
    therapist_matches = get_all_matched_roomcodes_for_therapist(user_id)
    active_chat_rooms = [] 

    for match in therapist_matches:
        room_code = match["roomcode"]
        student_user_id = match["student_user_id"]
        
        load_room_data_from_sqlite(room_code) 
            
        if room_code in rooms:
            student_data = get_user_data_by_id(student_user_id)
            messages = rooms[room_code]["messages"] # Lấy full lịch sử
            last_message = messages[-1] if messages else None
            
            # --- [UPDATE] GỌI AI ĐỂ PHÂN TÍCH ---
            # Chuyển đổi format messages của rooms (dict) sang format của chatbot (list dict role/message)
            formatted_history = []
            for m in messages:
                # Map tên user thành role để AI hiểu
                role = "Sinh viên" if m['name'] == student_data['username'] else "Therapist"
                formatted_history.append({"role": role, "message": m['message']})
            
            # Gọi hàm phân tích mới
            try:
                ai_summary_points = chatbot.analyze_student_state(student_user_id, formatted_history)
            except Exception as e:
                print(f"Lỗi AI phân tích: {e}")
                ai_summary_points = [{"point": "Không thể phân tích (lỗi AI)"}]
            # ------------------------------------

            active_chat_rooms.append({
                "room_code": room_code,
                "student_name": student_data["username"] if student_data else f"Sinh viên {student_user_id}",
                "matched_at": match["matched_at"],
                "last_message": last_message,
                "ai_summary": ai_summary_points,
                "messages": messages, 
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
    return redirect(url_for('therapist_dashboard'))

# @app.route('/therapist/workspace')
# def therapist_workspace():
#     if session.get('role') != 'therapist':
#         flash("Chỉ dành cho chuyên gia!", "error")
#         return redirect(url_for('home'))
#     return render_template('therapist_chat.html')



@app.route('/api/therapist/suggest', methods=['POST'])
def therapist_suggest():
    if session.get('role') != 'therapist': return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    try:
        suggestions = chatbot.get_therapist_suggestions(data.get('message'), data.get('context', []))
        if suggestions:
            return jsonify(suggestions)
        else:
            # Fallback suggestions nếu AI không sinh được
            return jsonify({"empathetic": "Tôi hiểu cảm xúc của em.", "probing": "Em có muốn kể thêm chi tiết không?", "cbt_action": "Hãy thử nhìn vấn đề từ góc độ khác."})
    except Exception as e:
        print(f"Therapist suggest error: {e}")
        return jsonify({"error": str(e)}), 500


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

# --- ROUTE MỚI: NHẬN NUÔI PET (ẤP TRỨNG) ---
@app.route('/api/pet/adopt', methods=['POST'])
def adopt_pet_api():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    
    db = database.get_db()
    user_id = session['user_id']
    
    # Kiểm tra xem đã có pet chưa
    existing_pet = db.execute("SELECT 1 FROM pets WHERE user_id = ?", (user_id,)).fetchone()
    if existing_pet:
        return jsonify({"success": False, "message": "Bạn đã có thú cưng rồi!"})

    try:
        # Tạo pet mới
        db.execute("INSERT INTO pets (user_id, name, skin_id, background_id) VALUES (?, ?, 0, 0)", 
                   (user_id, "Bạn Đồng Hành"))
        db.commit()
        return jsonify({"success": True, "message": "Nhận nuôi thành công!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

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



# --------------------------------------------------------------------------
# --- CÁC ROUTE VÀ API MỚI CHO ADMIN DASHBOARD ---
# --------------------------------------------------------------------------

def admin_required(f):
    """Decorator để kiểm tra vai trò admin."""
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin' or 'user_id' not in session:
            flash("Bạn không có quyền truy cập trang này!", "error")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__ # Đảm bảo tên hàm đúng
    return decorated_function

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html', active_page='dashboard')

# --- TRANG PHỤ 1: QUẢN LÝ USER ---

@app.route('/admin/users')
@admin_required
def admin_users():
    users = get_all_users()
    return render_template('admin_users.html', users=users, active_page='users')

@app.route('/api/admin/update_user', methods=['POST'])
@admin_required
def api_admin_update_user():
    data = request.json
    user_id = data.get('id')
    password = data.get('password') # Đây là mật khẩu mới hoặc chuỗi rỗng
    role = data.get('role')
    tags = data.get('tags')
    gold = data.get('gold')
    
    db = database.get_db()
    
    try:
        # 1. Cập nhật role, tags, gold
        update_query = "UPDATE users SET role = ?, tags = ?, gold = ? WHERE id = ?"
        db.execute(update_query, (role, tags, gold, user_id))
        
        # 2. Cập nhật password (CHỈ KHI CÓ MẬT KHẨU MỚI ĐƯỢC NHẬP)
        if password and len(password.strip()) > 0: # Kiểm tra chuỗi có nội dung
            hashed_pw = generate_password_hash(password)
            db.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_pw, user_id))
            
        db.commit()
        return jsonify({"success": True, "message": f"User {user_id} updated."})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Database Error: {e}"}), 500


# API LẤY MẬT KHẨU (CHỈ DÀNH CHO ADMIN)
@app.route('/api/admin/get_user_password/<int:user_id>')
@admin_required
def api_admin_get_user_password(user_id):
    """Lấy mật khẩu đã hash của người dùng."""
    db = database.get_db()
    user = db.execute("SELECT password FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        # Trả về mật khẩu đã hash hiện tại
        return jsonify({"success": True, "password_hash": user['password']})
    return jsonify({"success": False, "message": "User not found"}), 404


@app.route('/api/admin/add_user', methods=['POST'])
@admin_required
def api_admin_add_user():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role') # Bây giờ là trường bắt buộc
    
    # Các trường tùy chọn
    address = data.get('address')
    phone = data.get('phone')
    date_of_birth = data.get('date_of_birth')
    tags = data.get('tags', '')
    gold = data.get('gold', 200) 
    
    db = database.get_db()

    # --- CẬP NHẬT KIỂM TRA BẮT BUỘC: Thêm ROLE ---
    if not username or not email or not password or not role:
        return jsonify({"success": False, "message": "Missing required fields: Username, Email, Password, and Role."}), 400
    # --------------------------

    try:
        # 1. Hash mật khẩu
        hashed_pw = generate_password_hash(password)

        # 2. Thêm người dùng vào bảng users
        cursor = db.execute(
            "INSERT INTO users (username, email, password, role, tags, gold, address, phone, date_of_birth) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (username, email, hashed_pw, role, tags, gold, address, phone, date_of_birth)
        )
        user_id = cursor.lastrowid
        
        # 3. Tạo pet mặc định cho người dùng mới
        db.execute("INSERT INTO pets (user_id, name) VALUES (?, ?)", (user_id, "Bạn Đồng Hành"))
        
        db.commit()
        return jsonify({"success": True, "message": f"User {username} added with ID {user_id}."})
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({"success": False, "message": "Email or Username already exists!"}), 409
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Database Error: {e}"}), 500
    

@app.route('/api/admin/delete_user/<int:user_id>', methods=['DELETE'])
@admin_required
def api_admin_delete_user(user_id):
    db = database.get_db()

    # KHÔNG CHO PHÉP ADMIN XÓA TÀI KHOẢN CỦA CHÍNH MÌNH (Self-Deletion Prevention)
    if int(user_id) == session.get('user_id'):
        return jsonify({"success": False, "message": "You cannot delete your own active account."}), 403

    try:
        # Bắt đầu Transaction
        db.execute("BEGIN TRANSACTION")
        
        # --- BƯỚC MỚI: LẤY USERNAME TRƯỚC KHI XÓA KHỎI BẢNG USERS ---
        user_to_delete = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user_to_delete:
            db.rollback()
            return jsonify({"success": False, "message": f"User ID {user_id} not found."}), 404
            
        username_to_delete = user_to_delete['username']
        # ---------------------------------------------------------------------

        # 1. Xóa các bản ghi có khóa ngoại (Foreign Key) trực tiếp đến user_id
        db.execute("DELETE FROM pets WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM user_inventory WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM daily_quests WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM intake_summary WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM matchmaking_queue_students WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM matchmaking_queue_therapists WHERE user_id = ?", (user_id,))
        
        # 2. Xóa khỏi matchmaking_results (User có thể là student HOẶC therapist)
        db.execute("DELETE FROM matchmaking_results WHERE student_user_id = ? OR therapist_user_id = ?", (user_id, user_id))

        # ---   XÓA CHAT_LOGS DỰA TRÊN USERNAME ---
        db.execute("DELETE FROM chat_logs WHERE username = ?", (username_to_delete,))
        # -----------------------------------------------------

        # 3. Cuối cùng, xóa user khỏi bảng users
        result = db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        if result.rowcount == 0:
            db.rollback()
            return jsonify({"success": False, "message": f"User ID {user_id} not found."}), 404

        # Kết thúc Transaction
        db.commit()
        return jsonify({"success": True, "message": f"User ID {user_id} and all related data successfully deleted."})
        
    except Exception as e:
        db.rollback()
        print(f"Lỗi khi xóa user {user_id}: {e}")
        return jsonify({"success": False, "message": f"Database Error during deletion: {e}"}), 500
    

# --- TRANG PHỤ 2: QUẢN LÝ MATCHMAKING ---
@app.route('/admin/matches')
@admin_required
def admin_matches():
    matches = get_all_matchmaking_results()
    users = get_all_users() # Dùng để hiển thị danh sách người dùng cho việc tạo match thủ công
    return render_template('admin_matches.html', matches=matches, users=users, active_page='matches')

@app.route('/api/admin/add_match', methods=['POST'])
@admin_required
def api_admin_add_match():
    data = request.json
    student_id = data.get('student_id')
    therapist_id = data.get('therapist_id')

    if not student_id or not therapist_id:
        return jsonify({"success": False, "message": "Missing IDs"}), 400
        
    # 1. Lấy SID (Giả định là admin tạo match thủ công, SID không quan trọng lắm, nhưng cần có giá trị)
    # *FIX*: Cần lấy dữ liệu session của student/therapist đang online để lấy SID thật.
    # Tuy nhiên, để đơn giản, ta sẽ dùng SID của Admin và thông báo cho 2 người kia sau khi họ kết nối.
    # Hoặc, ta có thể dùng một giá trị mặc định, vì khi họ kết nối, SID thật sẽ được gán.

    # Lấy thông tin người dùng từ DB (cần cho notify và phòng ngừa lỗi)
    student_data = get_user_data_by_id(student_id)
    therapist_data = get_user_data_by_id(therapist_id)
    
    if not student_data or not therapist_data:
         return jsonify({"success": False, "message": "Student or Therapist not found"}), 404

    # Lấy SID thực tế nếu họ đang online, nếu không dùng SID của Admin hoặc placeholder
    student_sid = connected_users.get(student_data["username"], "ADMIN_PLACEHOLDER")
    therapist_sid = connected_users.get(therapist_data["username"], "ADMIN_PLACEHOLDER")

    # 2. Tạo Room Code
    room_code = generate_unique_code1(6)
    
    # 3. Lưu vào DB
    pair = {
        "student_user_id": student_id,
        "therapist_user_id": therapist_id,
        "student_session_id": student_sid,
        "therapist_session_id": therapist_sid,
        "roomcode": room_code
    }
    admin_create_match_result(pair) # Hàm mới trong repo
    
    # 4. Tạo phòng trong bộ nhớ (để chat được ngay)
    rooms[room_code] = {"members": 0, "messages": []}
    
    # 5. Thông báo (Nếu họ đang online)
    if student_sid in connected_users.values() or therapist_sid in connected_users.values():
        notify_users_of_new_match(student_id, therapist_id, student_sid, therapist_sid, room_code)
        
    return jsonify({"success": True, "message": f"Match created: {room_code}"})

@app.route('/api/admin/delete_match/<room_code>', methods=['DELETE'])
@admin_required
def api_admin_delete_match(room_code):
    delete_match_by_roomcode(room_code)
    # Xóa khỏi bộ nhớ nếu còn
    if room_code in rooms:
        del rooms[room_code]
    return jsonify({"success": True, "message": f"Match {room_code} deleted."})

# --- TRANG PHỤ 3: CHAT LOGS ---
@app.route('/admin/chat_logs')
@admin_required
def admin_chat_logs():
    db = database.get_db()
    # Lấy danh sách các room_code duy nhất từ chat_logs
    room_codes = db.execute("SELECT DISTINCT room_code FROM chat_logs ORDER BY room_code ASC").fetchall()
    
    # Lấy thông tin match (student/therapist) cho mỗi room_code
    chat_rooms = []
    for row in room_codes:
        room_code = row['room_code']
        # Lấy thông tin match từ matchmaking_results
        match_info = db.execute(
            """
            SELECT student_user_id, therapist_user_id, matched_at 
            FROM matchmaking_results 
            WHERE roomcode = ? 
            LIMIT 1
            """, 
            (room_code,)
        ).fetchone()

        student_name = "N/A"
        therapist_name = "N/A"
        
        if match_info:
            student = get_user_data_by_id(match_info['student_user_id'])
            therapist = get_user_data_by_id(match_info['therapist_user_id'])
            student_name = student['username'] if student else "ID " + str(match_info['student_user_id'])
            therapist_name = therapist['username'] if therapist else "ID " + str(match_info['therapist_user_id'])

        chat_rooms.append({
            "room_code": room_code,
            "student_name": student_name,
            "therapist_name": therapist_name,
            "matched_at": match_info['matched_at'] if match_info else "N/A"
        })
        
    return render_template('admin_chat_logs.html', chat_rooms=chat_rooms, active_page='chat_logs')

@app.route('/api/admin/chat_logs/<room_code>')
@admin_required
def api_admin_get_chat_logs(room_code):
    db = database.get_db()
    # Lấy tất cả tin nhắn của room_code
    messages = db.execute(
        "SELECT username, message_text, timestamp FROM chat_logs WHERE room_code = ? ORDER BY timestamp ASC",
        (room_code,)
    ).fetchall()
    
    # Định dạng lại tin nhắn cho đẹp
    chat_logs = []
    for msg in messages:
        chat_logs.append({
            "username": msg['username'],
            "message_text": msg['message_text'],
            "timestamp": msg['timestamp']
        })
        
    return jsonify(chat_logs)



# --- MAIN ---
if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        with app.app_context():
            database.init_db()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
    # app.run(host='0.0.0.0', port=5000, debug=True)







