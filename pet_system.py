import random
from datetime import date

# --- CẤU HÌNH SKIN (HÓA THÂN) ---
PET_SKINS = {
    0: {"name": "Mặc định", "face": "😊", "css_class": "skin-emoji"},
    101: {"name": "Mèo Cam", "face": "🐱", "css_class": "skin-emoji"},
    102: {"name": "Chó Shiba", "face": "🐶", "css_class": "skin-emoji"},
    103: {"name": "Rồng Lửa", "face": "🐲", "css_class": "skin-emoji"},
    104: {"name": "Alien", "face": "👽", "css_class": "skin-emoji"},
    105: {"name": "Cá Mập", "face": "🦈", "css_class": "skin-emoji"},
    106: {"name": "Tiểu Hổ", "face": "🐯", "css_class": "skin-emoji"},
    107: {"name": "Thỏ Ngọc", "face": "🐰", "css_class": "skin-emoji"},
    108: {"name": "Gấu Trúc", "face": "🐼", "css_class": "skin-emoji"},
    109: {"name": "Chim Cánh Cụt", "face": "🐧", "css_class": "skin-emoji"},
    110: {"name": "Ếch Xanh", "face": "🐸", "css_class": "skin-emoji"},
    111: {"name": "Heo Hồng", "face": "🐷", "css_class": "skin-emoji"},
    112: {"name": "Sư Tử", "face": "🦁", "css_class": "skin-emoji"},
    113: {"name": "Gà Con", "face": "🐥", "css_class": "skin-emoji"},
    114: {"name": "Bạch Tuộc", "face": "🐙", "css_class": "skin-emoji"},
    115: {"name": "Kỳ Lân", "face": "🦄", "css_class": "skin-emoji"},
    116: {"name": "Ma Cute", "face": "👻", "css_class": "skin-emoji"},
    117: {"name": "Robot", "face": "🤖", "css_class": "skin-emoji"},
    118: {"name": "Cáo Lửa", "face": "🦊", "css_class": "skin-emoji"},
    119: {"name": "Koala", "face": "🐨", "css_class": "skin-emoji"},
    120: {"name": "Rùa Con", "face": "🐢", "css_class": "skin-emoji"},
}

# --- CẤU HÌNH BACKGROUND (HÌNH NỀN) ---
PET_BACKGROUNDS = {
    0: "/static/images/pet_backgrounds/default.png", 
    201: "/static/images/pet_backgrounds/dong_co.png",
    202: "/static/images/pet_backgrounds/phong_khach.png",
    203: "/static/images/pet_backgrounds/bai_bien.png",
    204: "/static/images/pet_backgrounds/vu_tru.png",
    205: "/static/images/pet_backgrounds/rung.png",
    206: "/static/images/pet_backgrounds/dai_duong.png",
}

# --- HỆ THỐNG PET ---
EVOLUTION_STAGES = {
    1: {"name_template": "Young {}", "face": "^_^"},
    5: {"name_template": "Energetic {}", "face": "O_O"},
    10: {"name_template": "Wise {}", "face": "(`-´)"}
}

class Pet:
    def __init__(self, pet_id, user_id, name, level=1, happiness=50, energy=100, experience=0, skin_id=0, background_id=0):
        self.pet_id = pet_id
        self.user_id = user_id
        self.base_name = name
        self.name = name
        self.level = level
        self.happiness = happiness
        self.energy = energy
        self.experience = experience
        self.skin_id = skin_id if skin_id is not None else 0
        self.background_id = background_id if background_id is not None else 0
        self.exp_to_next_level = self._calculate_exp_for_level(level)
        self.appearance = {}
        self.background_url = ""
        self.mood = 'Vui vẻ 😊'
        
        self._update_appearance()
        self.update_mood()

    @classmethod
    def from_db_row(cls, row):
        # Lấy skin_id và background_id từ DB
        keys = row.keys()
        skin_id = row['skin_id'] if 'skin_id' in keys else 0
        background_id = row['background_id'] if 'background_id' in keys else 0
        
        return cls(row['id'], row['user_id'], row['name'], row['level'], row['happiness'], row['energy'], row['experience'], skin_id, background_id)

    def _update_appearance(self):
        # 1. Cập nhật Skin (Face)
        if self.skin_id in PET_SKINS:
            skin = PET_SKINS[self.skin_id]
            self.appearance = {"face": skin["face"], "css_class": skin["css_class"]}
        else:
            self.appearance = {"face": "😊", "css_class": "skin-emoji"}

        # 2. Cập nhật Background URL
        if self.background_id in PET_BACKGROUNDS:
            self.background_url = PET_BACKGROUNDS[self.background_id]
        else:
            self.background_url = PET_BACKGROUNDS[0]

        # 3. Cập nhật tên theo level
        current_stage = EVOLUTION_STAGES[1]
        for level_req, stage_data in EVOLUTION_STAGES.items():
            if self.level >= level_req: current_stage = stage_data
        self.name = current_stage["name_template"].format(self.base_name)

    def update_mood(self):
        if self.energy < 30: self.mood = 'Buồn ngủ 😴'
        elif self.happiness < 40: self.mood = 'Hơi buồn 😟'
        elif self.happiness > 90 and self.energy > 80: self.mood = 'Rất hào hứng! ✨'
        else: self.mood = 'Vui vẻ 😊'

    def to_dict(self):
        return {
            "name": self.name, "level": self.level, "happiness": self.happiness, 
            "energy": self.energy, "experience": self.experience, 
            "exp_to_next_level": self.exp_to_next_level, 
            "appearance": self.appearance, "mood": self.mood,
            "skin_id": self.skin_id,
            "background_url": self.background_url # Trả về URL hình nền
        }

    @staticmethod
    def _calculate_exp_for_level(level): return int(100 * (level ** 1.5))

    def _level_up(self):
        leveled_up = False
        while self.experience >= self.exp_to_next_level:
            leveled_up = True; self.level += 1; self.experience -= self.exp_to_next_level
            self.exp_to_next_level = self._calculate_exp_for_level(self.level); self.happiness, self.energy = 100, 100
        if leveled_up: self._update_appearance()

    def gain_experience(self, amount): self.experience += amount; self._level_up()
    def feed(self, food_value=25): self.happiness, self.energy = min(100, self.happiness + food_value), min(100, self.energy + int(food_value / 2))
    def play(self, happiness_value=30, energy_cost=20):
        if self.energy >= energy_cost: self.energy -= energy_cost; self.happiness = min(100, self.happiness + happiness_value); return True
        return False

    def choose_action(self):
        self.update_mood()
        actions = {'Buồn ngủ 😴': ([("rest", "Zzz..."), ("motivate", "Tớ cần nghỉ một chút...")], [80, 20]),
                   'Hơi buồn 😟': ([("motivate", "Cảm ơn vì đã ở đây với tớ."), ("rest", "...")], [70, 30])}
        default_actions = ([("wander", ""), ("motivate", "Một ngày thật tuyệt!"), ("motivate", "Cùng làm gì đó vui nào!")], [50, 25, 25])
        
        action_pool, weights = actions.get(self.mood, default_actions)
        action, quote = random.choices(action_pool, weights=weights, k=1)[0]
        
        if action == "wander": self.energy = max(0, self.energy - 3); return {"action": "wander", "direction": random.choice(["left", "right", "up", "down"]), **self.to_dict()}
        elif action == "rest": self.energy = min(100, self.energy + 20); return {"action": "rest", "quote": quote, **self.to_dict()}
        else: self.happiness = min(100, self.happiness + 5); return {"action": "motivate", "quote": quote, **self.to_dict()}

# --- HỆ THỐNG NHIỆM VỤ ---
QUEST_POOL = [
    {"id": 1, "type": "simple", "title": "Uống một ly nước đầy", "reward_exp": 10, "reward_gold": 5},
    {"id": 2, "type": "simple", "title": "Dọn dẹp một góc nhỏ trong phòng", "reward_exp": 25, "reward_gold": 10},
    {"id": 3, "type": "quiz", "title": "Quiz về Chánh Niệm", "reward_exp": 30, "reward_gold": 10, "data": {"question": "Đâu là cốt lõi của việc thực hành chánh niệm?", "options": [{"text": "Suy nghĩ về tương lai", "correct": False}, {"text": "Tập trung vào khoảnh khắc hiện tại", "correct": True}, {"text": "Phớt lờ cảm xúc của bạn", "correct": False}, {"text": "Làm nhiều việc cùng lúc", "correct": False}]}},
    {"id": 4, "type": "puzzle", "title": "Giải đố chữ", "reward_exp": 35, "reward_gold": 15, "data": {"question": "Sắp xếp lại từ liên quan đến sự bình yên: 'N A B H I N'", "scrambled_word": "N A B H I N", "correct_answer": "AN BINH"}},
    {"id": 101, "type": "journaling", "title": "Viết Nhật Ký Biết Ơn", "reward_exp": 30, "reward_gold": 15, "data": {"prompt": "Hôm nay, điều gì nhỏ bé đã mang lại niềm vui cho bạn?"}},
    {"id": 102, "type": "breathing", "title": "Bài tập Hít Thở Hộp (1 phút)", "reward_exp": 40, "reward_gold": 10, "data": {"duration_seconds": 60}}
]

# --- CỬA HÀNG (SKIN + BACKGROUND + FOOD) ---
SHOP_ITEMS = [
    # ================= SKIN (THÚ CƯNG) =================
    {"id": 101, "name": "Skin: Mèo Cam", "price": 100, "icon": "🐱", "type": "skin", "description": "Hoàng thượng."},
    {"id": 102, "name": "Skin: Chó Shiba", "price": 100, "icon": "🐶", "type": "skin", "description": "Gâu gâu!"},
    {"id": 107, "name": "Skin: Thỏ Ngọc", "price": 120, "icon": "🐰", "type": "skin", "description": "Nhảy nhót."},
    {"id": 113, "name": "Skin: Gà Con", "price": 120, "icon": "🐥", "type": "skin", "description": "Chip chip!"},
    {"id": 105, "name": "Skin: Cá Mập", "price": 250, "icon": "🦈", "type": "skin", "description": "Baby Shark."},
    {"id": 109, "name": "Skin: Cánh Cụt", "price": 250, "icon": "🐧", "type": "skin", "description": "Nam Cực."},
    {"id": 104, "name": "Skin: Alien", "price": 350, "icon": "👽", "type": "skin", "description": "Sao Hỏa."},
    {"id": 103, "name": "Skin: Rồng Lửa", "price": 550, "icon": "🐲", "type": "skin", "description": "Siêu ngầu."},
    {"id": 117, "name": "Skin: Robot", "price": 800, "icon": "🤖", "type": "skin", "description": "Công nghệ AI."},

    # ================= BACKGROUND (HÌNH NỀN) =================
    {"id": 201, "name": "Nền: Đồng Cỏ", "price": 150, "icon": "🏞️", "type": "background", "description": "Không khí trong lành."},
    {"id": 202, "name": "Nền: Phòng Khách", "price": 200, "icon": "🛋️", "type": "background", "description": "Ấm cúng, tiện nghi."},
    {"id": 203, "name": "Nền: Bãi Biển", "price": 300, "icon": "🏖️", "type": "background", "description": "Nắng vàng biển xanh."},
    {"id": 205, "name": "Nền: Rừng Phép Thuật", "price": 400, "icon": "🌲", "type": "background", "description": "Huyền bí."},
    {"id": 206, "name": "Nền: Đại Dương", "price": 450, "icon": "🌊", "type": "background", "description": "Thích hợp cho cá."},
    {"id": 204, "name": "Nền: Vũ Trụ", "price": 600, "icon": "🌌", "type": "background", "description": "Bay vào không gian."},

    # ================= FOOD (THỨC ĂN) =================
    {"id": 3003, "name": "Kẹo Ngọt", "price": 5, "icon": "🍬", "type": "food", "value": 15, "description": "+15 HP"},
    {"id": 3004, "name": "Sữa Tươi", "price": 10, "icon": "🥛", "type": "food", "value": 25, "description": "+25 HP"},
    {"id": 3001, "name": "Bánh Donut", "price": 20, "icon": "🍩", "type": "food", "value": 50, "description": "+50 HP"},
    {"id": 3005, "name": "Pizza", "price": 30, "icon": "🍕", "type": "food", "value": 65, "description": "+65 HP"},
    {"id": 3008, "name": "Bánh Kem", "price": 60, "icon": "🎂", "type": "food", "value": 100, "description": "Full HP"}
]

# --- CÁC HÀM TRUY XUẤT DỮ LIỆU ---
def load_pet(db, user_id):
    row = db.execute('SELECT * FROM pets WHERE user_id = ?', (user_id,)).fetchone()
    if row:
        return Pet.from_db_row(row)
    else:
        try:
            # Tạo pet mặc định với background_id = 0
            db.execute("INSERT INTO pets (user_id, name, skin_id, background_id) VALUES (?, ?, 0, 0)", (user_id, "Bạn Đồng Hành"))
            db.commit()
            row = db.execute('SELECT * FROM pets WHERE user_id = ?', (user_id,)).fetchone()
            return Pet.from_db_row(row)
        except Exception as e:
            print(f"Lỗi tạo pet: {e}")
            return None

def save_pet(db, pet):
    # Lưu cả skin_id và background_id
    db.execute('UPDATE pets SET level = ?, happiness = ?, energy = ?, experience = ?, skin_id = ?, background_id = ? WHERE id = ?',
               (pet.level, pet.happiness, pet.energy, pet.experience, pet.skin_id, pet.background_id, pet.pet_id))
    db.commit()

# HÀM TRANG BỊ (Xử lý cả Skin và Background)
def equip_skin(db, user_id, item_id):
    pet = load_pet(db, user_id)
    if not pet: return False

    # Tìm item trong shop để biết loại (skin hay background)
    item = next((i for i in SHOP_ITEMS if i['id'] == item_id), None)
    
    if item_id == 0: # Mặc định (thường dùng cho Skin)
        pet.skin_id = 0
    elif item:
        if item['type'] == 'skin':
            pet.skin_id = item_id
        elif item['type'] == 'background':
            pet.background_id = item_id
    elif item_id == 200: # Quy ước 200 là về background mặc định
        pet.background_id = 0

    pet._update_appearance()
    save_pet(db, pet)
    return True

# ... (Các hàm get_user_gold, update_user_gold, get_user_inventory, add_item_to_inventory, get_daily_quests, mark_quest_completed giữ nguyên) ...
def get_user_gold(db, user_id):
    row = db.execute('SELECT gold FROM users WHERE id = ?', (user_id,)).fetchone()
    return row['gold'] if row else 0

def update_user_gold(db, user_id, new_gold):
    db.execute('UPDATE users SET gold = ? WHERE id = ?', (new_gold, user_id))
    db.commit()

def get_user_inventory(db, user_id):
    item_ids = [row['item_id'] for row in db.execute('SELECT item_id FROM user_inventory WHERE user_id = ?', (user_id,)).fetchall()]
    inventory = []
    for item_id in item_ids:
        item = next((i for i in SHOP_ITEMS if i['id'] == item_id), None)
        if item: inventory.append(item)
    
    # Thêm item mặc định
    inventory.insert(0, {"id": 0, "name": "Pet Mặc định", "icon": "😊", "type": "skin", "description": "Skin gốc"})
    inventory.insert(1, {"id": 200, "name": "Nền Mặc định", "icon": "🏠", "type": "background", "description": "Phòng gốc"})
    
    return inventory

def add_item_to_inventory(db, user_id, item_id):
    existing = db.execute('SELECT 1 FROM user_inventory WHERE user_id = ? AND item_id = ?', (user_id, item_id)).fetchone()
    if not existing:
        db.execute('INSERT INTO user_inventory (user_id, item_id) VALUES (?, ?)', (user_id, item_id))
        db.commit()

def get_daily_quests(db, user_id):
    today = date.today()
    rows = db.execute('SELECT * FROM daily_quests WHERE user_id = ? AND date_assigned = ?', (user_id, today)).fetchall()

    if not rows:
        num_quests = min(4, len(QUEST_POOL))
        new_quests_data = random.sample(QUEST_POOL, num_quests)
        for quest_data in new_quests_data:
            db.execute('INSERT INTO daily_quests (user_id, quest_id, date_assigned) VALUES (?, ?, ?)',
                       (user_id, quest_data['id'], today))
        db.commit()
        return get_daily_quests(db, user_id)

    active_quests = []
    for row in rows:
        quest_info = next((q for q in QUEST_POOL if q['id'] == row['quest_id']), None)
        if quest_info:
            full_quest = {**quest_info, 'completed': bool(row['completed'])}
            active_quests.append(full_quest)
    return active_quests

def mark_quest_completed(db, user_id, quest_id):
    today = date.today()
    db.execute('UPDATE daily_quests SET completed = 1 WHERE user_id = ? AND quest_id = ? AND date_assigned = ?',
               (user_id, quest_id, today))
    db.commit()
