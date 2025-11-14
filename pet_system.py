import random
from datetime import date

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
        if self.energy < 30: self.mood = 'Buồn ngủ 😴'
        elif self.happiness < 40: self.mood = 'Hơi buồn 😟'
        elif self.happiness > 90 and self.energy > 80: self.mood = 'Rất hào hứng! ✨'
        else: self.mood = 'Vui vẻ 😊'

    def to_dict(self):
        return {"name": self.name, "level": self.level, "happiness": self.happiness, "energy": self.energy, "experience": self.experience, "exp_to_next_level": self.exp_to_next_level, "appearance": self.appearance, "mood": self.mood}

    @staticmethod
    def _calculate_exp_for_level(level): return int(100 * (level ** 1.5))

    def _update_evolution_stage(self):
        current_stage = None
        for level_req, stage_data in EVOLUTION_STAGES.items():
            if self.level >= level_req: current_stage = stage_data
        if current_stage: self.name, self.appearance = current_stage["name_template"].format(self.base_name), current_stage["appearance"]

    def _level_up(self):
        leveled_up = False
        while self.experience >= self.exp_to_next_level:
            leveled_up = True; self.level += 1; self.experience -= self.exp_to_next_level
            self.exp_to_next_level = self._calculate_exp_for_level(self.level); self.happiness, self.energy = 100, 100
        if leveled_up: self._update_evolution_stage()

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

# --- CÁC HÀM TRUY XUẤT DỮ LIỆU (DATABASE FUNCTIONS) ---
def load_pet(db, user_id):
    row = db.execute('SELECT * FROM pets WHERE user_id = ?', (user_id,)).fetchone()
    return Pet.from_db_row(row) if row else None

def save_pet(db, pet):
    db.execute('UPDATE pets SET level = ?, happiness = ?, energy = ?, experience = ? WHERE id = ?',
               (pet.level, pet.happiness, pet.energy, pet.experience, pet.pet_id))
    db.commit()

def get_user_gold(db, user_id):
    row = db.execute('SELECT gold FROM users WHERE id = ?', (user_id,)).fetchone()
    return row['gold'] if row else 0

def update_user_gold(db, user_id, new_gold):
    db.execute('UPDATE users SET gold = ? WHERE id = ?', (new_gold, user_id))
    db.commit()

def get_user_inventory(db, user_id):
    item_ids = [row['item_id'] for row in db.execute('SELECT item_id FROM user_inventory WHERE user_id = ?', (user_id,)).fetchall()]
    return [item for item in SHOP_ITEMS if item['id'] in item_ids]

def add_item_to_inventory(db, user_id, item_id):
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