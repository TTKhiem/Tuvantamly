# pet_system.py

import random
from flask import Flask, jsonify, render_template
from datetime import date

### --- PET SYSTEM (UPGRADED WITH MOODS) --- ###
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

### --- QUEST SYSTEM (UPGRADED WITH HEALING QUESTS) --- ###
QUEST_POOL = [
    { "id": 1, "type": "simple", "title": "Uống một ly nước đầy", "reward_exp": 10, "reward_gold": 5 },
    { "id": 2, "type": "simple", "title": "Dọn dẹp một góc nhỏ trong phòng", "reward_exp": 25, "reward_gold": 10 },
    { "id": 3, "type": "quiz", "title": "Quiz về Chánh Niệm", "reward_exp": 30, "reward_gold": 10, "data": { "question": "Đâu là cốt lõi của việc thực hành chánh niệm?", "options": [{ "text": "Suy nghĩ về tương lai", "correct": False }, { "text": "Tập trung vào khoảnh khắc hiện tại", "correct": True }, { "text": "Phớt lờ cảm xúc của bạn", "correct": False }, { "text": "Làm nhiều việc cùng lúc", "correct": False }]}},
    { "id": 4, "type": "puzzle", "title": "Giải đố chữ", "reward_exp": 35, "reward_gold": 15, "data": { "question": "Sắp xếp lại từ liên quan đến sự bình yên: 'N A B H I N'", "scrambled_word": "N A B H I N", "correct_answer": "AN BINH" }},
    { "id": 101, "type": "journaling", "title": "Viết Nhật Ký Biết Ơn", "reward_exp": 30, "reward_gold": 15, "data": { "prompt": "Hôm nay, điều gì nhỏ bé đã mang lại niềm vui cho bạn?" }},
    { "id": 102, "type": "breathing", "title": "Bài tập Hít Thở Hộp (1 phút)", "reward_exp": 40, "reward_gold": 10, "data": { "duration_seconds": 60 }}
]

# --- MỚI: HỆ THỐNG CỬA HÀNG (SHOP) ---
SHOP_ITEMS = [
    { "id": 1001, "name": "Mũ Cao Bồi", "price": 100, "icon": "🤠", "type": "hat" },
    { "id": 1002, "name": "Kính Râm", "price": 75, "icon": "😎", "type": "accessory" },
    { "id": 1003, "name": "Nơ Cổ", "price": 120, "icon": "🎀", "type": "accessory" },
    { "id": 2001, "name": "Cây Xương Rồng", "price": 150, "icon": "🌵", "type": "furniture" },
    { "id": 2002, "name": "Chậu Hoa", "price": 130, "icon": "🌸", "type": "furniture" },
    { "id": 3001, "name": "Bánh Donut", "price": 20, "icon": "🍩", "type": "food", "value": 50 },
    { "id": 3002, "name": "Táo", "price": 15, "icon": "🍎", "type": "food", "value": 35 }
]

# In-memory "database"
g_user_gold = 200 # Tăng tiền để có thể mua sắm
g_pet_instance = Pet(pet_id=1, user_id=1, name="Sparky")
g_current_daily_quests = []
g_last_quest_reset_date = None
g_user_inventory = [] # MỚI: Tủ đồ của người dùng

def check_and_reset_quests_if_needed():
    global g_current_daily_quests, g_last_quest_reset_date
    today = date.today()
    if g_last_quest_reset_date != today:
        print(f"--- Resetting daily quests for {today} ---")
        num_quests = min(4, len(QUEST_POOL))
        new_quests_data = random.sample(QUEST_POOL, num_quests)
        g_current_daily_quests = []
        for quest_data in new_quests_data:
            new_quest = quest_data.copy(); new_quest['completed'] = False; g_current_daily_quests.append(new_quest)
        g_last_quest_reset_date = today

app = Flask(__name__)

@app.route('/')
def index(): return render_template('pet.html', pet_name=g_pet_instance.name)

@app.route('/api/game_data')
def get_game_data():
    check_and_reset_quests_if_needed()
    g_pet_instance.update_mood()
    return jsonify({
        "pet": g_pet_instance.to_dict(),
        "quests": g_current_daily_quests,
        "gold": g_user_gold,
        "inventory": g_user_inventory # MỚI: Trả về tủ đồ
    })

@app.route('/api/start_quest/<int:quest_id>')
def start_quest(quest_id):
    check_and_reset_quests_if_needed()
    quest = next((q for q in g_current_daily_quests if q['id'] == quest_id), None)
    if quest and quest['type'] in ['quiz', 'puzzle', 'journaling', 'breathing']:
        return jsonify({"id": quest['id'], "type": quest['type'], "title": quest['title'], "data": quest['data']})
    return jsonify({"error": "Quest not found or is not interactive"}), 404

@app.route('/api/complete_quest/<int:quest_id>', methods=['POST'])
def complete_quest(quest_id):
    check_and_reset_quests_if_needed()
    global g_user_gold
    quest = next((q for q in g_current_daily_quests if q['id'] == quest_id), None)
    if quest and not quest["completed"]:
        quest["completed"] = True
        g_pet_instance.gain_experience(quest.get("reward_exp", 0))
        g_user_gold += quest.get("reward_gold", 0)
    g_pet_instance.update_mood()
    return jsonify({"pet": g_pet_instance.to_dict(), "quests": g_current_daily_quests, "gold": g_user_gold, "inventory": g_user_inventory})

@app.route('/api/pet/action')
def get_pet_action(): return jsonify(g_pet_instance.choose_action())

@app.route('/api/pet/feed', methods=['POST'])
def feed_pet():
    global g_user_gold; feed_cost = 10
    if g_user_gold >= feed_cost:
        g_user_gold -= feed_cost
        g_pet_instance.feed()
        g_pet_instance.update_mood()
        return jsonify({"pet": g_pet_instance.to_dict(), "quests": g_current_daily_quests, "gold": g_user_gold, "inventory": g_user_inventory})
    return jsonify({"error": "Not enough gold!"}), 400

@app.route('/api/pet/play', methods=['POST'])
def play_with_pet():
    g_pet_instance.play()
    g_pet_instance.update_mood()
    return jsonify({"pet": g_pet_instance.to_dict(), "quests": g_current_daily_quests, "gold": g_user_gold, "inventory": g_user_inventory})

# --- MỚI: CÁC API CHO CỬA HÀNG ---
@app.route('/api/shop/items')
def get_shop_items():
    return jsonify(SHOP_ITEMS)

@app.route('/api/shop/buy/<int:item_id>', methods=['POST'])
def buy_item(item_id):
    global g_user_gold, g_user_inventory
    item_to_buy = next((item for item in SHOP_ITEMS if item['id'] == item_id), None)
    if not item_to_buy: return jsonify({"error": "Vật phẩm không tồn tại."}), 404
    if item_to_buy['type'] != 'food' and any(i['id'] == item_id for i in g_user_inventory): return jsonify({"error": "Bạn đã sở hữu vật phẩm này rồi."}), 400
    if g_user_gold < item_to_buy['price']: return jsonify({"error": "Bạn không đủ vàng."}), 400
    g_user_gold -= item_to_buy['price']
    g_user_inventory.append(item_to_buy)
    return jsonify({"message": f"Đã mua {item_to_buy['name']} thành công!", "gold": g_user_gold, "inventory": g_user_inventory})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
