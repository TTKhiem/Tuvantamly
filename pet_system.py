import random
import sqlite3
import re
from datetime import date, datetime
from flask import Flask, jsonify, render_template, g, session, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'users.db'
APP_SECRET = 'change_this_to_something_random_and_secret'

app = Flask(__name__)
app.secret_key = APP_SECRET

# --- DATABASE HELPER FUNCTIONS ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- PET SYSTEM CLASSES & DATA ---
EVOLUTION_STAGES = {
    1: {"name_template": "Young {}", "appearance": {"face": "^_^", "css_class": "stage-1"}},
    5: {"name_template": "Energetic {}", "appearance": {"face": "O_O", "css_class": "stage-2"}},
    10: {"name_template": "Wise {}", "appearance": {"face": "(`-´)", "css_class": "stage-3"}}
}

class Pet:
    def __init__(self, pet_id, user_id, name, level=1, happiness=50, energy=100, experience=0):
        self.pet_id = pet_id; self.user_id = user_id; self.base_name = name; self.name = name; self.level = level; self.happiness = happiness; self.energy = energy; self.experience = experience; self.exp_to_next_level = self._calculate_exp_for_level(level); self.appearance = {}; self.mood = 'Vui vẻ 😊'; self._update_evolution_stage(); self.update_mood()
    @classmethod
    def from_db_row(cls, row): return cls(row['id'], row['user_id'], row['name'], row['level'], row['happiness'], row['energy'], row['experience'])
    def update_mood(self):
        if self.energy < 30: self.mood = 'Buồn ngủ 😴'
        elif self.happiness < 40: self.mood = 'Hơi buồn 😟'
        elif self.happiness > 90 and self.energy > 80: self.mood = 'Rất hào hứng! ✨'
        else: self.mood = 'Vui vẻ 😊'
    def to_dict(self): return {"name": self.name, "level": self.level, "happiness": self.happiness, "energy": self.energy, "experience": self.experience, "exp_to_next_level": self.exp_to_next_level, "appearance": self.appearance, "mood": self.mood}
    @staticmethod
    def _calculate_exp_for_level(level): return int(100 * (level ** 1.5))
    def _update_evolution_stage(self):
        current_stage = None
        for level_req, stage_data in EVOLUTION_STAGES.items():
            if self.level >= level_req: current_stage = stage_data
        if current_stage: self.name = current_stage["name_template"].format(self.base_name); self.appearance = current_stage["appearance"]
    def _level_up(self):
        leveled_up = False
        while self.experience >= self.exp_to_next_level:
            leveled_up = True; self.level += 1; self.experience -= self.exp_to_next_level; self.exp_to_next_level = self._calculate_exp_for_level(self.level); self.happiness = 100; self.energy = 100
        if leveled_up: self._update_evolution_stage()
    def gain_experience(self, amount): self.experience += amount; self._level_up()
    def feed(self, food_value=25): self.happiness = min(100, self.happiness + food_value); self.energy = min(100, self.energy + int(food_value/2))
    def play(self, happiness_value=30, energy_cost=20):
        if self.energy >= energy_cost: self.energy -= energy_cost; self.happiness = min(100, self.happiness + happiness_value); return True
        return False
    def choose_action(self):
        self.update_mood()
        if self.mood == 'Buồn ngủ 😴': action, quote = random.choices([("rest", "Zzz..."), ("motivate", "Tớ cần nghỉ một chút...")], weights=[80, 20], k=1)[0]
        elif self.mood == 'Hơi buồn 😟': action, quote = random.choices([("motivate", "Cảm ơn vì đã ở đây với tớ."), ("rest", "...")], weights=[70, 30], k=1)[0]
        else: action, quote = random.choices([("wander", ""), ("motivate", "Một ngày thật tuyệt!"), ("motivate", "Cùng làm gì đó vui nào!")], weights=[50, 25, 25], k=1)[0]
        if action == "wander": direction = random.choice(["left", "right", "up", "down"]); self.energy = max(0, self.energy - 3); return {"action": "wander", "direction": direction, **self.to_dict()}
        elif action == "rest": self.energy = min(100, self.energy + 20); return {"action": "rest", "quote": quote, **self.to_dict()}
        else: self.happiness = min(100, self.happiness + 5); return {"action": "motivate", "quote": quote, **self.to_dict()}

# --- DATA LOADING/SAVING ---
def get_current_user_id():
    return session.get('user_id')

def load_pet(user_id):
    cur = get_db().execute('SELECT * FROM pets WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    if row: return Pet.from_db_row(row)
    return None

def save_pet(pet):
    get_db().execute('UPDATE pets SET level = ?, happiness = ?, energy = ?, experience = ? WHERE id = ?', 
                     (pet.level, pet.happiness, pet.energy, pet.experience, pet.pet_id))
    get_db().commit()

def get_user_gold(user_id):
    cur = get_db().execute('SELECT gold FROM users WHERE id = ?', (user_id,))
    row = cur.fetchone()
    return row['gold'] if row else 0

def update_user_gold(user_id, new_gold):
    get_db().execute('UPDATE users SET gold = ? WHERE id = ?', (new_gold, user_id))
    get_db().commit()

def get_user_inventory(user_id):
    cur = get_db().execute('SELECT item_id FROM user_inventory WHERE user_id = ?', (user_id,))
    item_ids = [row['item_id'] for row in cur.fetchall()]
    return [item for item in SHOP_ITEMS if item['id'] in item_ids]

def add_item_to_inventory(user_id, item_id):
    get_db().execute('INSERT INTO user_inventory (user_id, item_id) VALUES (?, ?)', (user_id, item_id))
    get_db().commit()

# --- QUESTS & SHOP DATA ---
QUEST_POOL = [
    { "id": 1, "type": "simple", "title": "Uống một ly nước đầy", "reward_exp": 10, "reward_gold": 5 },
    { "id": 2, "type": "simple", "title": "Dọn dẹp một góc nhỏ trong phòng", "reward_exp": 25, "reward_gold": 10 },
    { "id": 3, "type": "quiz", "title": "Quiz về Chánh Niệm", "reward_exp": 30, "reward_gold": 10, "data": { "question": "Đâu là cốt lõi của việc thực hành chánh niệm?", "options": [{ "text": "Suy nghĩ về tương lai", "correct": False }, { "text": "Tập trung vào khoảnh khắc hiện tại", "correct": True }, { "text": "Phớt lờ cảm xúc của bạn", "correct": False }, { "text": "Làm nhiều việc cùng lúc", "correct": False }]}},
    { "id": 4, "type": "puzzle", "title": "Giải đố chữ", "reward_exp": 35, "reward_gold": 15, "data": { "question": "Sắp xếp lại từ liên quan đến sự bình yên: 'N A B H I N'", "scrambled_word": "N A B H I N", "correct_answer": "AN BINH" }},
    { "id": 101, "type": "journaling", "title": "Viết Nhật Ký Biết Ơn", "reward_exp": 30, "reward_gold": 15, "data": { "prompt": "Hôm nay, điều gì nhỏ bé đã mang lại niềm vui cho bạn?" }},
    { "id": 102, "type": "breathing", "title": "Bài tập Hít Thở Hộp (1 phút)", "reward_exp": 40, "reward_gold": 10, "data": { "duration_seconds": 60 }}
]
SHOP_ITEMS = [
    { "id": 1001, "name": "Mũ Cao Bồi", "price": 100, "icon": "🤠", "type": "hat" },
    { "id": 1002, "name": "Kính Râm", "price": 75, "icon": "😎", "type": "accessory" },
    { "id": 1003, "name": "Nơ Cổ", "price": 120, "icon": "🎀", "type": "accessory" },
    { "id": 2001, "name": "Cây Xương Rồng", "price": 150, "icon": "🌵", "type": "furniture" },
    { "id": 2002, "name": "Chậu Hoa", "price": 130, "icon": "🌸", "type": "furniture" },
    { "id": 3001, "name": "Bánh Donut", "price": 20, "icon": "🍩", "type": "food", "value": 50 },
    { "id": 3002, "name": "Táo", "price": 15, "icon": "🍎", "type": "food", "value": 35 }
]

def get_daily_quests(user_id):
    today = date.today()
    cur = get_db().execute('SELECT * FROM daily_quests WHERE user_id = ? AND date_assigned = ?', (user_id, today))
    rows = cur.fetchall()
    if not rows:
        num_quests = min(4, len(QUEST_POOL))
        new_quests_data = random.sample(QUEST_POOL, num_quests)
        for quest_data in new_quests_data:
            get_db().execute('INSERT INTO daily_quests (user_id, quest_id, date_assigned) VALUES (?, ?, ?)', (user_id, quest_data['id'], today))
        get_db().commit()
        return get_daily_quests(user_id)
    active_quests = []
    for row in rows:
        quest_info = next((q for q in QUEST_POOL if q['id'] == row['quest_id']), None)
        if quest_info:
            full_quest = quest_info.copy(); full_quest['completed'] = bool(row['completed']); active_quests.append(full_quest)
    return active_quests

def mark_quest_completed(user_id, quest_id):
    today = date.today()
    get_db().execute('UPDATE daily_quests SET completed = 1 WHERE user_id = ? AND quest_id = ? AND date_assigned = ?', (user_id, quest_id, today))
    get_db().commit()

# --- AUTHENTICATION ROUTES ---

@app.route('/login', methods=['POST'])
def login():
    # This route now ONLY handles the POST from the homepage popup
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
    
    return redirect(url_for('home')) # Always redirect back to home

@app.route('/register', methods=['POST'])
def register():
    # This route now ONLY handles the POST from the homepage popup
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    if not username or not email or not password:
         flash("Vui lòng nhập đầy đủ thông tin!", "error")
         return redirect(url_for('register_page')) # Redirect back to register page on error

    cur = get_db().execute("SELECT * FROM users WHERE email = ?", (email,))
    if cur.fetchone():
        flash("Email đã tồn tại!", "error")
        return redirect(url_for('register_page')) # Redirect back to register page

    hashed_password = generate_password_hash(password)
    cur = get_db().execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_password))
    user_id = cur.lastrowid

    # Create Default Pet for new User
    get_db().execute("INSERT INTO pets (user_id, name) VALUES (?, ?)", (user_id, "Bạn Đồng Hành"))
    get_db().commit()

    flash("Đăng ký thành công! Hãy đăng nhập.", "success")
    return redirect(url_for('home')) # Redirect to home for login

@app.route('/logout')
def logout():
    session.clear()
    flash("Đã đăng xuất.", "info")
    return redirect(url_for('home'))

# --- MAIN APP ROUTES ---

def get_user_data(user_id):
    """ Helper to get all user data for templates """
    user, pet, quests = None, None, None
    if user_id:
        db = get_db()
        user_row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user_row:
            user = dict(user_row) # Convert Row to dict
        pet_obj = load_pet(user_id)
        if pet_obj:
            pet = pet_obj.to_dict()
        quests = get_daily_quests(user_id)
    return user, pet, quests

@app.route('/')
def home():
    """ This is the main homepage route that serves index.html """
    user_id = get_current_user_id()
    user, pet, quests = get_user_data(user_id)
    
    # 'form_type' controls which popup is active
    return render_template('index.html', user=user, pet=pet, quests=quests, form_type='login')

@app.route('/register_page')
def register_page():
    """ NEW: This route shows the homepage with the register popup active """
    user_id = get_current_user_id()
    user, pet, quests = get_user_data(user_id)
    
    # 'form_type' controls which popup is active
    return render_template('index.html', user=user, pet=pet, quests=quests, form_type='register')


@app.route('/pet_page')
def pet_page():
    """ This is the route for the main pet app """
    user_id = get_current_user_id()
    if not user_id:
        return redirect(url_for('home')) # Redirect to home if not logged in
    
    pet = load_pet(user_id)
    if not pet:
        # This case shouldn't happen if register works, but as a fallback
        flash("Could not find your pet!", "error")
        return redirect(url_for('home'))

    return render_template('pet.html', pet_name=pet.name, username=session.get('username'))

@app.route('/user_dashboard')
def user_dashboard():
    """ NEW: Added this route, as it's linked in your header. """
    # For now, let's redirect to the pet page, as it's the main "dashboard"
    flash("Chào mừng tới trang của bạn!", "info")
    return redirect(url_for('pet_page'))

@app.route('/your_therapists')
def your_therapists():
    """ NEW: Added this dummy route, as it's in your header. """
    # You can build this out later.
    flash("Trang 'Your Therapists' đang được xây dựng!", "info")
    return redirect(url_for('home'))


# --- API ROUTES ---
def check_auth():
    if not get_current_user_id():
        return jsonify({"error": "Unauthorized"}), 401
    return None

def get_all_game_data(user_id, pet=None):
    if not pet: pet = load_pet(user_id)
    pet_dict = pet.to_dict() if pet else None
    return {"pet": pet_dict, "quests": get_daily_quests(user_id), "gold": get_user_gold(user_id), "inventory": get_user_inventory(user_id)}

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
    auth_error = check_auth(); 
    if auth_error: return auth_error
    user_id = get_current_user_id()
    quests = get_daily_quests(user_id)
    quest = next((q for q in quests if q['id'] == quest_id), None)
    if quest and quest['type'] in ['quiz', 'puzzle', 'journaling', 'breathing']:
        return jsonify({"id": quest['id'], "type": quest['type'], "title": quest['title'], "data": quest['data']})
    return jsonify({"error": "Quest not found"}), 404

@app.route('/api/complete_quest/<int:quest_id>', methods=['POST'])
def complete_quest_api(quest_id):
    auth_error = check_auth(); 
    if auth_error: return auth_error
    user_id = get_current_user_id()
    quests = get_daily_quests(user_id)
    quest = next((q for q in quests if q['id'] == quest_id), None)
    if quest and not quest["completed"]:
        pet = load_pet(user_id); gold = get_user_gold(user_id)
        mark_quest_completed(user_id, quest_id)
        pet.gain_experience(quest.get("reward_exp", 0))
        update_user_gold(user_id, gold + quest.get("reward_gold", 0))
        save_pet(pet)
        return jsonify(get_all_game_data(user_id, pet))
    return jsonify({"error": "Invalid quest"}), 400

@app.route('/api/pet/feed', methods=['POST'])
def feed_pet_api():
    auth_error = check_auth(); 
    if auth_error: return auth_error
    user_id = get_current_user_id(); gold = get_user_gold(user_id); feed_cost = 10
    if gold >= feed_cost:
        pet = load_pet(user_id); pet.feed()
        update_user_gold(user_id, gold - feed_cost); save_pet(pet)
        return jsonify(get_all_game_data(user_id, pet))
    return jsonify({"error": "Not enough gold!"}), 400

@app.route('/api/pet/play', methods=['POST'])
def play_pet_api():
    auth_error = check_auth(); 
    if auth_error: return auth_error
    # --- THIS IS THE FIX ---
    user_id = get_current_user_id(); pet = load_pet(user_id) # Was user_i
    if pet.play():
        save_pet(pet)
        return jsonify(get_all_game_data(user_id, pet)) # Was user_i
    # --- END FIX ---
    return jsonify({"error": "Pet tired!"}), 400

@app.route('/api/shop/items')
def get_shop_items_api(): return jsonify(SHOP_ITEMS)

@app.route('/api/shop/buy/<int:item_id>', methods=['POST'])
def buy_item_api(item_id):
    auth_error = check_auth(); 
    if auth_error: return auth_error
    user_id = get_current_user_id(); gold = get_user_gold(user_id); inventory = get_user_inventory(user_id)
    item = next((i for i in SHOP_ITEMS if i['id'] == item_id), None)
    if not item: return jsonify({"error": "Item missing"}), 404
    if item['type'] != 'food' and any(i['id'] == item_id for i in inventory): return jsonify({"error": "Owned"}), 400
    if gold < item['price']: return jsonify({"error": "No gold"}), 400
    update_user_gold(user_id, gold - item['price'])
    if item['type'] != 'food': add_item_to_inventory(user_id, item_id)
    else: pet = load_pet(user_id); pet.feed(item.get('value', 25)); save_pet(pet)
    return jsonify({"message": "Bought!", "gold": get_user_gold(user_id), "inventory": get_user_inventory(user_id)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)