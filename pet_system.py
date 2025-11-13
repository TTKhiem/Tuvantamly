# -*- coding: utf-8 -*-

# --- IMPORT CÁC THƯ VIỆN CẦN THIẾT ---
import os
import random
import re
import sqlite3
from datetime import date, datetime

import google.generativeai as genai
from flask import (Flask, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

# --- CÁC HẰNG SỐ VÀ CẤU HÌNH TOÀN CỤC ---
DATABASE = 'users.db'
APP_SECRET = 'change_this_to_something_random_and_secret'

# Dán API Key của bạn vào đây
GOOGLE_API_KEY = ""

app = Flask(__name__)
app.secret_key = APP_SECRET


# --- CẤU HÌNH GEMINI API ---
gemini_model = None
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        
        generation_config = {
            "temperature": 0.8,
            "top_p": 1,
            "top_k": 1,
            "max_output_tokens": 2048
        }

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]

        gemini_model = genai.GenerativeModel(
            model_name="gemini-1.0-pro",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
    except Exception as e:
        print(f"Lỗi khi khởi tạo model Gemini: {e}")

# Persona cho Pet-bot khi trò chuyện
PET_BOT_PERSONA = """
Bạn là một người bạn đồng hành ảo nhỏ bé, thân thiện và giàu lòng cảm thông.
Vai trò của bạn là lắng nghe, an ủi và đưa ra những lời động viên nhẹ nhàng.
QUY TẮC BẮT BUỘC:
1. **KHÔNG BAO GIỜ** đưa ra lời khuyên y tế, tâm lý trị liệu hoặc chẩn đoán.
2. Giữ câu trả lời **ngắn gọn, đơn giản và thân thiện**, giống như một thú cưng đáng yêu đang nói chuyện.
3. Sử dụng các biểu tượng cảm xúc đơn giản (ví dụ: 😊, ❤️, ✨, 🐾, 🤗).
4. Nếu người dùng đề cập đến vấn đề nghiêm trọng, hãy nhẹ nhàng gợi ý họ tìm đến chuyên gia.
"""


# --- CÁC HÀM HỖ TRỢ DATABASE ---
def get_db():
    """Mở một kết nối database mới nếu chưa có cho context hiện tại."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    """Đóng kết nối database khi teardown."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


# --- HỆ THỐNG PET: LỚP, DỮ LIỆU VÀ CÁC HÀM HỖ TRỢ ---
EVOLUTION_STAGES = {
    1: {"name_template": "Young {}", "appearance": {"face": "^_^", "css_class": "stage-1"}},
    5: {"name_template": "Energetic {}", "appearance": {"face": "O_O", "css_class": "stage-2"}},
    10: {"name_template": "Wise {}", "appearance": {"face": "(`-´)", "css_class": "stage-3"}}
}

class Pet:
    def __init__(self, pet_id, user_id, name, level=1, happiness=50, energy=100, experience=0):
        self.pet_id = pet_id
        self.user_id = user_id
        self.base_name = name
        self.name = name
        self.level = level
        self.happiness = happiness
        self.energy = energy
        self.experience = experience
        self.exp_to_next_level = self._calculate_exp_for_level(level)
        self.appearance = {}
        self.mood = 'Vui vẻ 😊'
        self._update_evolution_stage()
        self.update_mood()

    @classmethod
    def from_db_row(cls, row):
        return cls(row['id'], row['user_id'], row['name'], row['level'], row['happiness'], row['energy'], row['experience'])

    def update_mood(self):
        if self.energy < 30:
            self.mood = 'Buồn ngủ 😴'
        elif self.happiness < 40:
            self.mood = 'Hơi buồn 😟'
        elif self.happiness > 90 and self.energy > 80:
            self.mood = 'Rất hào hứng! ✨'
        else:
            self.mood = 'Vui vẻ 😊'

    def to_dict(self):
        return {
            "name": self.name,
            "level": self.level,
            "happiness": self.happiness,
            "energy": self.energy,
            "experience": self.experience,
            "exp_to_next_level": self.exp_to_next_level,
            "appearance": self.appearance,
            "mood": self.mood
        }

    @staticmethod
    def _calculate_exp_for_level(level):
        return int(100 * (level ** 1.5))

    def _update_evolution_stage(self):
        current_stage = None
        for level_req, stage_data in EVOLUTION_STAGES.items():
            if self.level >= level_req:
                current_stage = stage_data
        if current_stage:
            self.name = current_stage["name_template"].format(self.base_name)
            self.appearance = current_stage["appearance"]

    def _level_up(self):
        leveled_up = False
        while self.experience >= self.exp_to_next_level:
            leveled_up = True
            self.level += 1
            self.experience -= self.exp_to_next_level
            self.exp_to_next_level = self._calculate_exp_for_level(self.level)
            self.happiness = 100
            self.energy = 100
        if leveled_up:
            self._update_evolution_stage()

    def gain_experience(self, amount):
        self.experience += amount
        self._level_up()

    def feed(self, food_value=25):
        self.happiness = min(100, self.happiness + food_value)
        self.energy = min(100, self.energy + int(food_value / 2))

    def play(self, happiness_value=30, energy_cost=20):
        if self.energy >= energy_cost:
            self.energy -= energy_cost
            self.happiness = min(100, self.happiness + happiness_value)
            return True
        return False

    def choose_action(self):
        self.update_mood()
        if self.mood == 'Buồn ngủ 😴':
            action, quote = random.choices([("rest", "Zzz..."), ("motivate", "Tớ cần nghỉ một chút...")], weights=[80, 20], k=1)[0]
        elif self.mood == 'Hơi buồn 😟':
            action, quote = random.choices([("motivate", "Cảm ơn vì đã ở đây với tớ."), ("rest", "...")], weights=[70, 30], k=1)[0]
        else:
            action, quote = random.choices([("wander", ""), ("motivate", "Một ngày thật tuyệt!"), ("motivate", "Cùng làm gì đó vui nào!")], weights=[50, 25, 25], k=1)[0]
        
        if action == "wander":
            direction = random.choice(["left", "right", "up", "down"])
            self.energy = max(0, self.energy - 3)
            return {"action": "wander", "direction": direction, **self.to_dict()}
        elif action == "rest":
            self.energy = min(100, self.energy + 20)
            return {"action": "rest", "quote": quote, **self.to_dict()}
        else: # motivate
            self.happiness = min(100, self.happiness + 5)
            return {"action": "motivate", "quote": quote, **self.to_dict()}


# --- HỆ THỐNG NHIỆM VỤ VÀ CỬA HÀNG ---
QUEST_POOL = [
    {"id": 1, "type": "simple", "title": "Uống một ly nước đầy", "reward_exp": 10, "reward_gold": 5},
    {"id": 2, "type": "simple", "title": "Dọn dẹp một góc nhỏ trong phòng", "reward_exp": 25, "reward_gold": 10},
    {"id": 3, "type": "quiz", "title": "Quiz về Chánh Niệm", "reward_exp": 30, "reward_gold": 10, "data": {"question": "Đâu là cốt lõi của việc thực hành chánh niệm?", "options": [{"text": "Suy nghĩ về tương lai", "correct": False}, {"text": "Tập trung vào khoảnh khắc hiện tại", "correct": True}, {"text": "Phớt lờ cảm xúc của bạn", "correct": False}, {"text": "Làm nhiều việc cùng lúc", "correct": False}]}},
    {"id": 4, "type": "puzzle", "title": "Giải đố chữ", "reward_exp": 35, "reward_gold": 15, "data": {"question": "Sắp xếp lại từ liên quan đến sự bình yên: 'N A B H I N'", "scrambled_word": "N A B H I N", "correct_answer": "AN BINH"}},
    {"id": 101, "type": "journaling", "title": "Viết Nhật Ký Biết Ơn", "reward_exp": 30, "reward_gold": 15, "data": {"prompt": "Hôm nay, điều gì nhỏ bé đã mang lại niềm vui cho bạn?"}},
    {"id": 102, "type": "breathing", "title": "Bài tập Hít Thở Hộp (1 phút)", "reward_exp": 40, "reward_gold": 10, "data": {"duration_seconds": 60}}
]

SHOP_ITEMS = [
    {"id": 1001, "name": "Mũ Cao Bồi", "price": 100, "icon": "🤠", "type": "hat"},
    {"id": 1002, "name": "Kính Râm", "price": 75, "icon": "😎", "type": "accessory"},
    {"id": 1003, "name": "Nơ Cổ", "price": 120, "icon": "🎀", "type": "accessory"},
    {"id": 2001, "name": "Cây Xương Rồng", "price": 150, "icon": "🌵", "type": "furniture"},
    {"id": 2002, "name": "Chậu Hoa", "price": 130, "icon": "🌸", "type": "furniture"},
    {"id": 3001, "name": "Bánh Donut", "price": 20, "icon": "🍩", "type": "food", "value": 50},
    {"id": 3002, "name": "Táo", "price": 15, "icon": "🍎", "type": "food", "value": 35}
]


# --- CÁC HÀM TRUY XUẤT DỮ LIỆU NGƯỜI DÙNG ---
def get_current_user_id():
    return session.get('user_id')

def load_pet(user_id):
    cur = get_db().execute('SELECT * FROM pets WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    return Pet.from_db_row(row) if row else None

def save_pet(pet):
    db = get_db()
    db.execute('UPDATE pets SET level = ?, happiness = ?, energy = ?, experience = ? WHERE id = ?',
               (pet.level, pet.happiness, pet.energy, pet.experience, pet.pet_id))
    db.commit()

def get_user_gold(user_id):
    cur = get_db().execute('SELECT gold FROM users WHERE id = ?', (user_id,))
    row = cur.fetchone()
    return row['gold'] if row else 0

def update_user_gold(user_id, new_gold):
    db = get_db()
    db.execute('UPDATE users SET gold = ? WHERE id = ?', (new_gold, user_id))
    db.commit()

def get_user_inventory(user_id):
    cur = get_db().execute('SELECT item_id FROM user_inventory WHERE user_id = ?', (user_id,))
    item_ids = [row['item_id'] for row in cur.fetchall()]
    return [item for item in SHOP_ITEMS if item['id'] in item_ids]

def add_item_to_inventory(user_id, item_id):
    db = get_db()
    db.execute('INSERT INTO user_inventory (user_id, item_id) VALUES (?, ?)', (user_id, item_id))
    db.commit()

def get_daily_quests(user_id):
    today = date.today()
    db = get_db()
    cur = db.execute('SELECT * FROM daily_quests WHERE user_id = ? AND date_assigned = ?', (user_id, today))
    rows = cur.fetchall()

    if not rows:
        num_quests = min(4, len(QUEST_POOL))
        new_quests_data = random.sample(QUEST_POOL, num_quests)
        for quest_data in new_quests_data:
            db.execute('INSERT INTO daily_quests (user_id, quest_id, date_assigned) VALUES (?, ?, ?)',
                       (user_id, quest_data['id'], today))
        db.commit()
        return get_daily_quests(user_id) # Gọi lại để lấy dữ liệu mới chèn

    active_quests = []
    for row in rows:
        quest_info = next((q for q in QUEST_POOL if q['id'] == row['quest_id']), None)
        if quest_info:
            full_quest = quest_info.copy()
            full_quest['completed'] = bool(row['completed'])
            active_quests.append(full_quest)
    return active_quests

def mark_quest_completed(user_id, quest_id):
    today = date.today()
    db = get_db()
    db.execute('UPDATE daily_quests SET completed = 1 WHERE user_id = ? AND quest_id = ? AND date_assigned = ?',
               (user_id, quest_id, today))
    db.commit()


# --- ROUTES XÁC THỰC (AUTHENTICATION) ---
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    cur = get_db().execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()

    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        flash(f"Chào mừng {user['username']}!", "success")
    else:
        flash("Sai email hoặc mật khẩu!", "error")
        
    return redirect(url_for('home'))

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    if not username or not email or not password:
        flash("Vui lòng nhập đầy đủ thông tin!", "error")
        return redirect(url_for('register_page'))

    db = get_db()
    if db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone():
        flash("Email đã tồn tại!", "error")
        return redirect(url_for('register_page'))
    
    hashed_password = generate_password_hash(password)
    cur = db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                     (username, email, hashed_password))
    user_id = cur.lastrowid
    db.execute("INSERT INTO pets (user_id, name) VALUES (?, ?)", (user_id, "Bạn Đồng Hành"))
    db.commit()

    flash("Đăng ký thành công! Hãy đăng nhập.", "success")
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Đã đăng xuất.", "info")
    return redirect(url_for('home'))


# --- ROUTES HIỂN THỊ TRANG (PAGE RENDERING) ---
def get_user_data(user_id):
    """Lấy dữ liệu chung cho các trang."""
    user, pet_dict, quests = None, None, None
    if user_id:
        db = get_db()
        user_row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user_row:
            user = dict(user_row)
        pet_obj = load_pet(user_id)
        if pet_obj:
            pet_dict = pet_obj.to_dict()
        quests = get_daily_quests(user_id)
    return user, pet_dict, quests

@app.route('/')
def home():
    user_id = get_current_user_id()
    user, pet, quests = get_user_data(user_id)
    return render_template('index.html', user=user, pet=pet, quests=quests, form_type='login')

@app.route('/register_page')
def register_page():
    user_id = get_current_user_id()
    user, pet, quests = get_user_data(user_id)
    return render_template('index.html', user=user, pet=pet, quests=quests, form_type='register')

@app.route('/pet_page')
def pet_page():
    user_id = get_current_user_id()
    if not user_id:
        return redirect(url_for('home'))

    pet = load_pet(user_id)
    if not pet:
        flash("Không tìm thấy pet của bạn!", "error")
        return redirect(url_for('home'))
        
    return render_template('pet.html', pet_name=pet.name, username=session.get('username'))

@app.route('/user_dashboard')
def user_dashboard():
    flash("Chào mừng tới trang của bạn!", "info")
    return redirect(url_for('pet_page'))

@app.route('/your_therapists')
def your_therapists():
    flash("Trang 'Your Therapists' đang được xây dựng!", "info")
    return redirect(url_for('home'))


# --- ROUTES API ---
def check_auth():
    """Kiểm tra xem người dùng đã đăng nhập chưa."""
    if not get_current_user_id():
        return jsonify({"error": "Unauthorized"}), 401
    return None

def get_all_game_data(user_id, pet=None):
    """Tổng hợp tất cả dữ liệu game cho API response."""
    if pet is None:
        pet = load_pet(user_id)
    
    pet_dict = pet.to_dict() if pet else None
    
    return {
        "pet": pet_dict,
        "quests": get_daily_quests(user_id),
        "gold": get_user_gold(user_id),
        "inventory": get_user_inventory(user_id)
    }

@app.route('/api/game_data')
def get_game_data_api():
    auth_error = check_auth()
    if auth_error: return auth_error
    
    user_id = get_current_user_id()
    return jsonify(get_all_game_data(user_id))

@app.route('/api/pet/action')
def get_pet_action():
    auth_error = check_auth()
    if auth_error: return auth_error
    
    user_id = get_current_user_id()
    pet = load_pet(user_id)
    if not pet:
        return jsonify({"error": "No pet found for user"}), 404
        
    action_result = pet.choose_action()
    save_pet(pet)
    return jsonify(action_result)

@app.route('/api/start_quest/<int:quest_id>')
def start_quest_api(quest_id):
    auth_error = check_auth()
    if auth_error: return auth_error
    
    user_id = get_current_user_id()
    quests = get_daily_quests(user_id)
    quest = next((q for q in quests if q['id'] == quest_id), None)
    
    if quest and quest['type'] in ['quiz', 'puzzle', 'journaling', 'breathing']:
        return jsonify({
            "id": quest['id'],
            "type": quest['type'],
            "title": quest['title'],
            "data": quest['data']
        })
        
    return jsonify({"error": "Quest not found"}), 404

@app.route('/api/complete_quest/<int:quest_id>', methods=['POST'])
def complete_quest_api(quest_id):
    auth_error = check_auth()
    if auth_error: return auth_error

    user_id = get_current_user_id()
    quests = get_daily_quests(user_id)
    quest = next((q for q in quests if q['id'] == quest_id), None)

    if quest and not quest["completed"]:
        pet = load_pet(user_id)
        gold = get_user_gold(user_id)
        
        mark_quest_completed(user_id, quest_id)
        pet.gain_experience(quest.get("reward_exp", 0))
        update_user_gold(user_id, gold + quest.get("reward_gold", 0))
        save_pet(pet)
        
        return jsonify(get_all_game_data(user_id, pet))
        
    return jsonify({"error": "Invalid quest"}), 400

@app.route('/api/pet/feed', methods=['POST'])
def feed_pet_api():
    auth_error = check_auth()
    if auth_error: return auth_error

    user_id = get_current_user_id()
    gold = get_user_gold(user_id)
    feed_cost = 10

    if gold >= feed_cost:
        pet = load_pet(user_id)
        pet.feed()
        update_user_gold(user_id, gold - feed_cost)
        save_pet(pet)
        return jsonify(get_all_game_data(user_id, pet))
        
    return jsonify({"error": "Not enough gold!"}), 400

@app.route('/api/pet/play', methods=['POST'])
def play_pet_api():
    auth_error = check_auth()
    if auth_error: return auth_error
    
    user_id = get_current_user_id()
    pet = load_pet(user_id)
    
    if pet.play():
        save_pet(pet)
        return jsonify(get_all_game_data(user_id, pet))
        
    return jsonify({"error": "Pet is too tired to play!"}), 400

@app.route('/api/shop/items')
def get_shop_items_api():
    return jsonify(SHOP_ITEMS)

@app.route('/api/shop/buy/<int:item_id>', methods=['POST'])
def buy_item_api(item_id):
    auth_error = check_auth()
    if auth_error: return auth_error

    user_id = get_current_user_id()
    gold = get_user_gold(user_id)
    inventory = get_user_inventory(user_id)
    item = next((i for i in SHOP_ITEMS if i['id'] == item_id), None)

    if not item:
        return jsonify({"error": "Item not found"}), 404
    if item['type'] != 'food' and any(i['id'] == item_id for i in inventory):
        return jsonify({"error": "Item already owned"}), 400
    if gold < item['price']:
        return jsonify({"error": "Not enough gold"}), 400

    update_user_gold(user_id, gold - item['price'])
    
    if item['type'] != 'food':
        add_item_to_inventory(user_id, item_id)
    else:
        pet = load_pet(user_id)
        pet.feed(item.get('value', 25))
        save_pet(pet)
        
    return jsonify({
        "message": "Item purchased successfully!",
        "gold": get_user_gold(user_id),
        "inventory": get_user_inventory(user_id)
    })

@app.route('/api/pet/chat', methods=['POST'])
def pet_chat_api():
    auth_error = check_auth()
    if auth_error: return auth_error

    if not GOOGLE_API_KEY or not gemini_model:
        return jsonify({"reply": "Xin lỗi, tớ chưa sẵn sàng để trò chuyện lúc này (API key lỗi)."}), 500

    user_id = get_current_user_id()
    pet = load_pet(user_id)
    if not pet:
        return jsonify({"error": "Không tìm thấy pet của bạn."}), 404
        
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "Không có tin nhắn nào được gửi."}), 400

    try:
        # Bắt đầu cuộc trò chuyện với persona đã định nghĩa
        convo = gemini_model.start_chat(history=[
            {"role": "user", "parts": [PET_BOT_PERSONA.replace("Sparky", pet.base_name)]},
            {"role": "model", "parts": [f"Chào bạn! Tớ là {pet.name} đây. Tớ có thể giúp gì cho bạn hôm nay? 😊"]},
        ])
        
        convo.send_message(user_message)
        bot_reply = convo.last.text
        
        return jsonify({
            "reply": bot_reply,
            "pet_face": pet.appearance.get("face", "^_^"),
            "pet_mood": pet.mood
        })

    except Exception as e:
        print(f"Lỗi khi gọi Gemini API: {e}")
        return jsonify({"reply": "Huhu, tớ đang bị rối một chút, không thể trả lời bạn ngay được. 🐾"}), 500


# --- CHẠY ỨNG DỤNG ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)```
