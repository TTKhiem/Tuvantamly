import os
import sqlite3
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, flash
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Import các module đã tách
import database
import chatbot
import pet_system

# --- KHỞI TẠO ỨNG DỤNG ---
load_dotenv()
app = Flask(__name__)
app.config['DATABASE'] = database.DATABASE
app.secret_key = os.getenv("APP_SECRET")

# Lấy các API key từ file .env
chatbot_api_key = os.getenv("GOOGLE_CHATBOT_API_KEY")
petbot_api_key = os.getenv("GOOGLE_PETBOT_API_KEY")

# Khởi tạo các Gemini client với các key tương ứng
chatbot.init_gemini_clients(chatbot_api_key, petbot_api_key)

# Đăng ký các hàm database với app
database.init_app(app)


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
            return redirect(url_for('therapist_dashboard'))
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
    if session.get('role') == 'therapist': return redirect(url_for('therapist_dashboard'))
    db = database.get_db()
    user_data = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    return render_template('dashboard.html', user = user_data)
    
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
@app.route('/therapist/dashboard')
def therapist_dashboard():
    if session.get('role') != 'therapist':
        flash("Bạn không có quyền truy cập trang này!", "error")
        return redirect(url_for('home'))

    db = database.get_db()
    summaries = db.execute(
        """
        SELECT s.id as summary_id, s.user_id, s.summary_content, u.username, s.created_at
        FROM intake_summary s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.created_at DESC
        """
    ).fetchall()
    return render_template('therapist_dashboard.html', summaries=summaries)

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

# --- MAIN ---
if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        with app.app_context():
            database.init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
