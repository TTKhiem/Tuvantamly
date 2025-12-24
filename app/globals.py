import json
import os
from dotenv import load_dotenv
from flask import Flask
from flask_socketio import SocketIO

from app import database


def from_json_filter(value):
    """Bộ lọc Jinja để chuyển đổi JSON string thành Python object."""
    if value is None:
        return None
    return json.loads(value)


# In-memory storage used by socket handlers
rooms = {}
connected_users = {}

# Flask/SocketIO setup
load_dotenv()
BASE_DIR = os.path.dirname(__file__)
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.jinja_env.filters["from_json"] = from_json_filter
socketio = SocketIO(app)
app.config["DATABASE"] = database.DATABASE
app.secret_key = os.getenv("APP_SECRET")