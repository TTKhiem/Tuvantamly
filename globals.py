import os
import sqlite3
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, flash
from dotenv import load_dotenv
from flask_socketio import SocketIO
import database
import chatbot
import json
from jinja2_time import TimeExtension

def from_json_filter(value):
    """Bộ lọc Jinja để chuyển đổi JSON string thành Python object."""
    if value is None:
        return None
    return json.loads(value)

# --- Global In-memory Storage  ---
rooms = {} 
connected_users = {} 

# --- KHỞI TẠO ỨNG DỤNG ---
load_dotenv()
app = Flask(__name__)
app.jinja_env.filters['from_json'] = from_json_filter
socketio = SocketIO(app)
app.config['DATABASE'] = database.DATABASE
app.secret_key = os.getenv("APP_SECRET")

# Lấy các API key từ file .env
chatbot_api_key = os.getenv("GOOGLE_CHATBOT_API_KEY")
petbot_api_key = os.getenv("GOOGLE_PETBOT_API_KEY")
therapist_api_key = os.getenv("GOOGLE_THERAPIST_API_KEY")

# Khởi tạo các Gemini client với các key tương ứng
chatbot.init_gemini_clients(chatbot_api_key, petbot_api_key, therapist_api_key)

# Đăng ký các hàm database với app
database.init_app(app)