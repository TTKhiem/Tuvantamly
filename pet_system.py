# pet_system.py

import random
from flask import Flask, jsonify, render_template
from datetime import date

### --- PET SYSTEM (Không thay đổi) --- ###
# ... (Toàn bộ class Pet của bạn giữ nguyên, tôi sẽ rút gọn nó ở đây)
EVOLUTION_STAGES = {1: {"name_template": "Young {}", "appearance": {"face": "^_^", "css_class": "stage-1"}}, 5: {"name_template": "Energetic {}", "appearance": {"face": "O_O", "css_class": "stage-2"}}, 10: {"name_template": "Wise {}", "appearance": {"face": "(`-´)", "css_class": "stage-3"}}}
class Pet:
    def __init__(self, pet_id, user_id, name, level=1, happiness=50, energy=100, experience=0): self.pet_id=pet_id; self.user_id=user_id; self.base_name=name; self.name=name; self.level=level; self.happiness=happiness; self.energy=energy; self.experience=experience; self.exp_to_next_level=self._calculate_exp_for_level(level); self.appearance={}; self._update_evolution_stage()
    def to_dict(self): return {"name": self.name, "level": self.level, "happiness": self.happiness, "energy": self.energy, "experience": self.experience, "exp_to_next_level": self.exp_to_next_level, "appearance": self.appearance}
    @staticmethod
    def _calculate_exp_for_level(level): return int(100 * (level ** 1.5))
    def _update_evolution_stage(self):
        current_stage = None
        for level_req, stage_data in EVOLUTION_STAGES.items():
            if self.level >= level_req: current_stage = stage_data
        if current_stage: self.name = current_stage["name_template"].format(self.base_name); self.appearance = current_stage["appearance"]
    def _level_up(self):
        leveled_up = False
        while self.experience >= self.exp_to_next_level: leveled_up=True; self.level+=1; self.experience-=self.exp_to_next_level; self.exp_to_next_level=self._calculate_exp_for_level(self.level); self.happiness=100; self.energy=100
        if leveled_up: self._update_evolution_stage()
    def gain_experience(self, amount): self.experience += amount; self._level_up()
    def feed(self, food_value=25): self.happiness=min(100, self.happiness + food_value); self.energy=min(100, self.energy + int(food_value/2))
    def play(self, happiness_value=30, energy_cost=20):
        if self.energy >= energy_cost: self.energy-=energy_cost; self.happiness=min(100, self.happiness+happiness_value); return True
        return False
    def motivate(self): quote=random.choice(["Keep going! 🌟", "Small steps forward. 🐾"]); self.happiness=min(100, self.happiness+5); return {"action":"motivate", "quote":quote, **self.to_dict()}
    def wander(self): move=random.choice(["left","right","up","down"]); self.energy=max(0,self.energy-3); return {"action":"wander", "direction":move, **self.to_dict()}
    def rest(self): self.energy=min(100, self.energy+20); return {"action":"rest", **self.to_dict()}
    def choose_action(self):
        if self.energy < 20: action_name=random.choices(["rest","motivate","wander"],weights=[80,10,10],k=1)[0]
        else: action_name=random.choices(["wander","motivate","rest"],weights=[50,40,10],k=1)[0]
        return {"motivate":self.motivate,"wander":self.wander,"rest":self.rest}[action_name]()


### --- QUEST SYSTEM (UPGRADED WITH INTERACTIVE QUESTS) --- ###

# NEW: The Quest Pool now includes a 'type' and 'data' for interactive quests.
QUEST_POOL = [
    # Type 'simple': Just click to complete
    { "id": 1, "type": "simple", "title": "Drink a full glass of water", "reward_exp": 10, "reward_gold": 5 },
    { "id": 2, "type": "simple", "title": "Tidy up one small area of your room", "reward_exp": 25, "reward_gold": 10 },
    
    # Type 'quiz': A multiple-choice question
    { "id": 3, "type": "quiz", "title": "Mindfulness Quiz", "reward_exp": 30, "reward_gold": 10,
      "data": {
          "question": "Which of these is a core practice of mindfulness?",
          "options": [
              { "text": "Thinking about the future", "correct": False },
              { "text": "Focusing on the present moment", "correct": True },
              { "text": "Ignoring your feelings", "correct": False },
              { "text": "Doing multiple tasks at once", "correct": False }
          ]
      }
    },
    
    # Type 'puzzle': An anagram (word scramble)
    { "id": 4, "type": "puzzle", "title": "Unscramble the Word", "reward_exp": 35, "reward_gold": 15,
      "data": {
          "question": "Unscramble this word related to calmness: 'E C A P E'",
          "scrambled_word": "E C A P E",
          "correct_answer": "PEACE"
      }
    },

    # More examples
    { "id": 5, "type": "simple", "title": "Do a gentle 5-minute stretch", "reward_exp": 20, "reward_gold": 5 },
    { "id": 6, "type": "simple", "title": "Write down one positive thing that happened today", "reward_exp": 20, "reward_gold": 10 },
]

# In-memory "database"
g_user_gold = 50
g_pet_instance = Pet(pet_id=1, user_id=1, name="Sparky")
g_current_daily_quests = []
g_last_quest_reset_date = None

def check_and_reset_quests_if_needed():
    global g_current_daily_quests, g_last_quest_reset_date
    today = date.today()
    if g_last_quest_reset_date != today:
        print(f"--- Resetting daily quests for {today} ---")
        num_quests = min(4, len(QUEST_POOL))
        new_quests_data = random.sample(QUEST_POOL, num_quests)
        g_current_daily_quests = []
        for quest_data in new_quests_data:
            new_quest = quest_data.copy()
            new_quest['completed'] = False
            g_current_daily_quests.append(new_quest)
        g_last_quest_reset_date = today

### --- FLASK APP SETUP --- ###
app = Flask(__name__)

### --- ROUTES AND API ENDPOINTS --- ###

@app.route('/')
def index():
    return render_template('pet.html', pet_name=g_pet_instance.name)

@app.route('/api/game_data')
def get_game_data():
    check_and_reset_quests_if_needed()
    return jsonify({
        "pet": g_pet_instance.to_dict(),
        "quests": g_current_daily_quests,
        "gold": g_user_gold
    })

# --- NEW API TO GET DATA FOR AN INTERACTIVE QUEST ---
@app.route('/api/start_quest/<int:quest_id>')
def start_quest(quest_id):
    """Returns the specific data needed to run a quiz or puzzle."""
    check_and_reset_quests_if_needed()
    quest = next((q for q in g_current_daily_quests if q['id'] == quest_id), None)
    
    if quest and quest['type'] in ['quiz', 'puzzle']:
        # Only return the necessary data, not the answer for puzzles
        return jsonify({
            "id": quest['id'],
            "type": quest['type'],
            "title": quest['title'],
            "data": quest['data']
        })
    else:
        return jsonify({"error": "Quest not found or is not interactive"}), 404

# --- API `complete_quest` is now simpler ---
# The frontend will only call this AFTER the user has solved the puzzle/quiz.
@app.route('/api/complete_quest/<int:quest_id>', methods=['POST'])
def complete_quest(quest_id):
    check_and_reset_quests_if_needed()
    global g_user_gold
    quest = next((q for q in g_current_daily_quests if q['id'] == quest_id), None)
    
    if quest and not quest["completed"]:
        quest["completed"] = True
        g_pet_instance.gain_experience(quest.get("reward_exp", 0))
        g_user_gold += quest.get("reward_gold", 0)
    
    return jsonify({
        "pet": g_pet_instance.to_dict(),
        "quests": g_current_daily_quests,
        "gold": g_user_gold
    })

# --- Other APIs (no changes) ---
@app.route('/api/pet/action')
def get_pet_action(): return jsonify(g_pet_instance.choose_action())
@app.route('/api/pet/feed', methods=['POST'])
def feed_pet():
    global g_user_gold; feed_cost = 10
    if g_user_gold >= feed_cost:
        g_user_gold -= feed_cost; g_pet_instance.feed()
        return jsonify({"pet": g_pet_instance.to_dict(), "quests": g_current_daily_quests, "gold": g_user_gold})
    return jsonify({"error": "Not enough gold!"}), 400
@app.route('/api/pet/play', methods=['POST'])
def play_with_pet():
    g_pet_instance.play()
    return jsonify({"pet": g_pet_instance.to_dict(), "quests": g_current_daily_quests, "gold": g_user_gold})

### --- RUN THE APP --- ###
if __name__ == '__main__':
    app.run(debug=True, port=5000)