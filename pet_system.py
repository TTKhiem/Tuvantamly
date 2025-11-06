import random
from flask import Flask, jsonify, render_template

# --- Pet Class (from your file) ---
# I've modified choose_action to be more robust
class Pet:
    def __init__(self, pet_id, user_id, name, level=1, happiness=50, energy=100, experience=0):
        self.pet_id = pet_id
        self.user_id = user_id
        self.name = name
        self.level = level
        self.happiness = happiness
        self.energy = energy
        self.experience = experience

    def motivate(self):
        """Returns a motivational quote and boosts happiness."""
        quotes = [
            "Keep going, you're doing great! 🌟",
            "Remember, small steps still move you forward. 🐾",
            "You are stronger than you think 💪",
            "Take a deep breath — you've got this 💫",
            "Even slow progress is progress. 🌱",
            "Be kind to yourself today. ❤️"
        ]
        quote = random.choice(quotes)
        self.happiness = min(100, self.happiness + 5)
        # In a real app, you'd save this new happiness value to the database
        # update_pet_in_db(self.pet_id, happiness=self.happiness)
        return {"action": "motivate", "quote": quote, "happiness": self.happiness, "energy": self.energy}

    def wander(self):
        """Chooses a random direction to move and uses a bit of energy."""
        directions = ["left", "right", "up", "down", "up-left", "up-right", "down-left", "down-right"]
        move = random.choice(directions)
        self.energy = max(0, self.energy - 3)
        # In a real app, you'd save this new energy value to the database
        # update_pet_in_db(self.pet_id, energy=self.energy)
        return {"action": "wander", "direction": move, "happiness": self.happiness, "energy": self.energy}

    def rest(self):
        """Restores energy."""
        self.energy = min(100, self.energy + 20)
        # In a real app, you'd save this new energy value to the database
        # update_pet_in_db(self.pet_id, energy=self.energy)
        return {"action": "rest", "happiness": self.happiness, "energy": self.energy}

    def choose_action(self):
        """Chooses and performs a random action based on current stats."""
        if self.energy < 20:
            # If energy is low, 80% chance to rest
            action_name = random.choices(["rest", "motivate", "wander"], weights=[80, 10, 10], k=1)[0]
        else:
            # Otherwise, 50% chance to wander, 40% to motivate, 10% to rest
            action_name = random.choices(["wander", "motivate", "rest"], weights=[50, 40, 10], k=1)[0]

        # Call the chosen action method and return its result
        if action_name == "motivate":
            return self.motivate()
        elif action_name == "wander":
            return self.wander()
        else: # action_name == "rest"
            return self.rest()

# --- Flask App Setup ---
app = Flask(__name__)

# --- Database Simulation ---
# In a real app, you'd fetch this from your SQLite database
# based on the logged-in user's ID.
# For this example, we'll create one pet instance in memory.
g_pet_instance = Pet(pet_id=1, user_id=1, name="Sparky")
# ---

@app.route('/')
def index():
    """Serves the main HTML page."""
    # The pet's name is passed to the template
    return render_template('pet.html', pet_name=g_pet_instance.name)

@app.route('/api/pet/stats')
def get_stats():
    """API endpoint to get the pet's current stats."""
    return jsonify({
        "level": g_pet_instance.level,
        "happiness": g_pet_instance.happiness,
        "energy": g_pet_instance.energy,
        "experience": g_pet_instance.experience
    })

@app.route('/api/pet/action')
def get_pet_action():
    """
    API endpoint for the front-end to call.
    Triggers the pet to choose an action and returns the result.
    """
    action_result = g_pet_instance.choose_action()
    return jsonify(action_result)

# --- Run the App ---
if __name__ == '__main__':
    # Make sure to set debug=False in a production environment
    app.run(debug=True, port=5000)