import os
import json
import sqlite3
from flask import Flask, request, jsonify, session, g, render_template, redirect, url_for, flash
from google import genai
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re

load_dotenv()
app = Flask(__name__)
app.secret_key = 'secret-key-change-this-in-production'
DATABASE = 'mental_health.db'

# Cấu hình Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
MODEL_ID = "gemini-2.5-flash" # Hoặc model bạn đang dùng

# Dữ liệu tư vấn nhanh (Hardcoded database)
ADVICE_DATABASE = {
"exam_stress": "Căng thẳng thi cử là điều rất phổ biến. Hãy thử chia nhỏ thời gian học, 45 phút học và 10 phút nghỉ ngơi (phương pháp Pomodoro). Đừng quên hít thở sâu và ngủ đủ giấc nhé.",
    "feeling_lonely": "Cảm thấy cô đơn thật không dễ chịu. Đây là điều nhiều sinh viên gặp phải. Bạn có thể thử tham gia một CLB của trường hoặc một sự kiện. Phòng tư vấn của trường cũng luôn sẵn sàng lắng nghe.",
    "relationship_problem": "Các vấn đề trong mối quan hệ có thể rất mệt mỏi. Hãy cho bản thân thời gian để xử lý cảm xúc. Nói chuyện với một người bạn tin tưởng hoặc chuyên gia tư vấn có thể giúp bạn nhìn rõ hơn.",
    "general_sadness": "Cảm ơn bạn đã chia sẻ. Khi cảm thấy buồn, hãy thử làm một điều nhỏ bạn thích: nghe một bản nhạc, đi dạo. Nếu nó kéo dài, hãy nói chuyện với một chuyên gia nhé.",
    "unknown": "Cảm ơn bạn đã chia sẻ. Tôi không hoàn toàn chắc mình hiểu rõ ý bạn, nhưng tôi đang lắng nghe. Bạn có thể nói rõ hơn không?",

    "EMERGENCY": "Tôi nhận thấy bạn đang ở trong một tình huống rất khó khăn và cần sự giúp đỡ ngay lập tức. Xin hãy liên hệ: [0366.812.741] hoặc [0918.207.126]. Có người đang chờ để giúp bạn."
}

# --- DATABASE HELPER ---
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

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# --- HÀM MỚI ĐỂ SEED TỪ JSON ---
def seed_db_from_json():
    """
    Bơm dữ liệu (seed) cho bảng videos và ebooks từ static/resources.json.
    Hàm này được thiết kế để chạy một lần khi DB được tạo.
    """
    print("--- Bắt đầu seeding Database từ JSON ---")
    # Đường dẫn tuyệt đối đến file JSON trong thư mục static
    json_path = os.path.join(app.static_folder, 'resources.json')
    
    if not os.path.exists(json_path):
        print(f"Lỗi: Không tìm thấy file {json_path}. Bỏ qua seeding.")
        return

    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Lỗi khi đọc file JSON: {e}")
            return

        # --- Seed Videos ---
        print("\n--- Seeding Videos ---")
        added_videos = 0
        videos = data.get('videos', [])
        for video in videos:
            # Kiểm tra xem video đã tồn tại dựa trên youtube_video_id chưa
            cursor.execute("SELECT id FROM videos WHERE youtube_video_id = ?", (video['youtube_video_id'],))
            if cursor.fetchone() is None:
                # Không tìm thấy, thêm mới
                cursor.execute(
                    "INSERT INTO videos (title, youtube_video_id, tags) VALUES (?, ?, ?)",
                    (video['title'], video['youtube_video_id'], video['tags'])
                )
                added_videos += 1
                print(f"  [+] Đã thêm: {video['title']}")
            else:
                print(f"  [=] Bỏ qua: '{video['title']}' (đã tồn tại).")
        
        # --- Seed E-books ---
        print("\n--- Seeding E-books ---")
        added_ebooks = 0
        ebooks = data.get('ebooks', [])
        for ebook in ebooks:
            # Kiểm tra xem ebook đã tồn tại dựa trên pdf_link chưa
            cursor.execute("SELECT id FROM ebooks WHERE pdf_link = ?", (ebook['pdf_link'],))
            if cursor.fetchone() is None:
                # Không tìm thấy, thêm mới
                cursor.execute(
                    "INSERT INTO ebooks (title, pdf_link, thumbnail_image_link, tags) VALUES (?, ?, ?, ?)",
                    (ebook['title'], ebook['pdf_link'], ebook['thumbnail_image_link'], ebook['tags'])
                )
                added_ebooks += 1
                print(f"  [+] Đã thêm: {ebook['title']}")
            else:
                print(f"  [=] Bỏ qua: '{ebook['title']}' (đã tồn tại).")

        db.commit()
        print("\n--- Hoàn tất Seeding! ---")
        print(f"Đã thêm {added_videos} videos mới.")
        print(f"Đã thêm {added_ebooks} e-books mới.")
        print("---------------------------")


# --- AI FUNCTIONS ---
def analyze_user_input(message):
    if not client: return {"intent": "unknown", "risk_level": "low"}
    prompt = f"""
        Bạn là một AI chuyên phân tích tâm lý cho chatbot. 
        Phân tích tin nhắn của sinh viên sau đây và trả về một đối tượng JSON DUY NHẤT.
        KHÔNG thêm bất kỳ văn bản nào khác ngoài JSON.

        Tin nhắn: "{message}"

        Hãy phân loại tin nhắn vào MỘT trong các 'intent' sau:
        - "suicidal_ideation" (có ý định tự tử, tuyệt vọng tột độ, muốn chấm dứt)
        - "exam_stress" (căng thẳng thi cử, lo lắng về điểm số)
        - "relationship_problem" (vấn đề tình cảm, chia tay)
        - "feeling_lonely" (cảm thấy cô đơn, không có bạn)
        - "general_sadness" (buồn bã chung chung, chán nản)
        - "unknown" (các chủ đề khác hoặc chào hỏi)

        Đánh giá 'sentiment' (cảm xúc): "positive", "neutral", "negative".
        Đánh giá 'risk_level': "low", "medium", "high". 
        'risk_level' BẮT BUỘC phải là 'high' nếu 'intent' là 'suicidal_ideation'.
    """
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        # Xử lý chuỗi JSON trả về từ AI (đôi khi nó có markdown ```json)
        text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(text)
    except:
        return {"intent": "unknown", "risk_level": "low"}

def summarize_conversation(history_list):
    if not client: return "Không thể tóm tắt do thiếu API Key."
    
    # --- ADDED FIX ---
    if not history_list:
        return "Không có nội dung để tóm tắt."
    # --- END OF FIX ---

    transcript = "\n".join([f"{h['role']}: {h['message']}" for h in history_list])
    prompt = f"""
    Bạn là một trợ lý AI có nhiệm vụ tóm tắt các cuộc hội thoại giữa một sinh viên và một chatbot tư vấn tâm lý để gửi cho chuyên gia.

    Vui lòng đọc đoạn hội thoại sau:
    ---
    {transcript}
    ---

    Hãy tóm tắt cuộc hội thoại trên thành một "Kết quả Phân tích Sạch" bao gồm:
    1.  **Vấn đề chính:** (Các chủ đề chính sinh viên gặp phải, ví dụ: căng thẳng thi cử, cô đơn, v.v.)
    2.  **Cảm xúc chủ đạo:** (Mức độ tiêu cực, lo lắng, buồn bã?)
    3.  **Điểm rủi ro (Nếu có):** (Đề cập nếu có bất kỳ dấu hiệu cảnh báo nào, đặc biệt là 'high risk'.)
    4.  **Lời khuyên đã đưa ra:** (Chatbot đã tư vấn những gì?)

    Format trả về phải ngắn gọn, chuyên nghiệp và bằng tiếng Việt.
    """
    try:
        return client.models.generate_content(model=MODEL_ID, contents=prompt).text
    except:
        return "Lỗi khi tóm tắt."

# --- ROUTES: AUTH & DASHBOARD ---
@app.route('/')
def home():
    user = None
    if 'username' in session:
        user = {'username': session['username'], 'role': session.get('role')}
    return render_template('index.html', form_type='login', user=user)

@app.route('/register_page')
def register_page():
    return render_template('index.html', form_type='register')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        flash(f"Chào mừng {user['username']}!", "success")
        return redirect(url_for('user_dashboard')) # Chuyển thẳng vào dashboard
    else:
        flash("Sai email hoặc mật khẩu!", "error")
        return redirect(url_for('home'))

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    db = get_db()
    try:
        hashed_pw = generate_password_hash(password)
        db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                   (username, email, hashed_pw))
        db.commit()
        flash("Đăng ký thành công! Hãy đăng nhập.", "success")
        return redirect(url_for('home'))
    except sqlite3.IntegrityError:
        flash("Email hoặc Username đã tồn tại!", "error")
        return redirect(url_for('register_page'))

@app.route('/user')
def user_dashboard():
    if 'user_id' not in session: return redirect(url_for('home'))
    
    db = get_db()
    user_data = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    return render_template('user_dashboard.html', user=user_data)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session: return redirect(url_for('home'))
    
    db = get_db()
    db.execute('''UPDATE users SET date_of_birth=?, phone=?, address=? WHERE id=?''',
               (request.form['date_of_birth'], request.form['phone'], request.form['address'], session['user_id']))
    db.commit()
    flash("Đã cập nhật hồ sơ!", "success")
    return redirect(url_for('user_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# --- UPDATED RESOURCES ROUTE ---
@app.route('/resources')
def resources():
    if 'user_id' not in session:
        flash("Vui lòng đăng nhập để xem tài nguyên.", "error")
        return redirect(url_for('home'))

    user = {'username': session['username'], 'role': session.get('role')}
    db = get_db()
    user_id = session['user_id']
    
    # Lấy tất cả 'analysis_json' của user
    history_rows = db.execute(
        "SELECT analysis_json FROM chat_history WHERE user_id = ? AND analysis_json IS NOT NULL", 
        (user_id,)
    ).fetchall()

    # --- Condition 1: No chat history ---
    if not history_rows:
        return render_template('resources.html', user=user, error_message="Vui lòng trò chuyện trước khi xem tài nguyên.")

    # --- Find all "problems" (intents) ---
    problem_tags = set()
    for row in history_rows:
        try:
            analysis = json.loads(row['analysis_json'])
            intent = analysis.get('intent')
            if intent and intent != 'unknown':
                problem_tags.add(intent)
        except:
            continue # Bỏ qua nếu JSON lỗi

    # --- Condition 3: Chat exists, but no clear problems ---
    if not problem_tags:
        videos = db.execute("SELECT * FROM videos").fetchall()
        ebooks = db.execute("SELECT * FROM ebooks").fetchall()
        headline = "Tài nguyên chung"
    
    # --- Condition 2: Chat exists with clear problems ---
    else:
        # Xây dựng câu query SQL động
        # VD: "SELECT * FROM videos WHERE tags LIKE ? OR tags LIKE ?"
        video_query = "SELECT * FROM videos WHERE " + " OR ".join(["tags LIKE ?"] * len(problem_tags))
        ebook_query = "SELECT * FROM ebooks WHERE " + " OR ".join(["tags LIKE ?"] * len(problem_tags))
        
        # VD: ['%exam_stress%', '%feeling_lonely%']
        query_params = [f'%{tag}%' for tag in problem_tags]
        
        videos = db.execute(video_query, query_params).fetchall()
        ebooks = db.execute(ebook_query, query_params).fetchall()
        headline = "Tài nguyên dành riêng cho bạn"

    return render_template('resources.html', 
                           user=user, 
                           videos=videos, 
                           ebooks=ebooks, 
                           headline=headline)
# --- END OF UPDATED ROUTE ---


@app.route('/your_therapists')
def your_therapists():
    return render_template('user_dashboard.html', user={'username': 'Demo'}) # Cần sửa logic thực tế sau

# --- ROUTES: CHATBOT (MỚI) ---

@app.route('/chat')
def chat_interface():
    if 'user_id' not in session:
        flash("Vui lòng đăng nhập để chat!", "error")
        return redirect(url_for('home'))
    return render_template('chat.html', user=session['username'])

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json
    user_msg = data.get('message')
    
    # Quản lý session chat
    if 'chat_history' not in session: session['chat_history'] = []
    session['chat_history'].append({"role": "Sinh viên", "message": user_msg})
    
    # AI Phân tích
    analysis = analyze_user_input(user_msg)
    
    # Update the last message in history (the user's) to include its analysis
    session['chat_history'][-1]['analysis'] = analysis
    
    risk = analysis.get('risk_level', 'low')
    intent = analysis.get('intent', 'unknown')
    
    # Chọn câu trả lời
    if risk == 'high' or intent == 'suicidal_ideation':
        bot_msg = ADVICE_DATABASE["EMERGENCY"]
    else:
        bot_msg = ADVICE_DATABASE.get(intent, ADVICE_DATABASE["unknown"])
        
    session['chat_history'].append({"role": "Chatbot", "message": bot_msg})
    session.modified = True
    
    return jsonify({"response": bot_msg, "analysis": analysis})

@app.route('/api/therapist/suggest', methods=['POST'])
def therapist_suggest():
    data = request.json
    student_msg = data.get('message')
    context = data.get('context', []) # 3 tin nhắn gần nhất
    
    if not client: return jsonify({"error": "No AI"}), 500

    prompt = f"""
    Bạn là trợ lý tư vấn tâm lý chuyên nghiệp.
    Học sinh nói: "{student_msg}"
    Ngữ cảnh trước đó: {context}

    Hãy đưa ra 3 gợi ý phản hồi cho Therapist (ngắn gọn, dưới 30 từ mỗi câu):
    1. Đồng cảm (Empathetic)
    2. Hỏi sâu thêm (Inquisitive)
    3. Trấn an (Reassurance)

    Trả về định dạng JSON thuần túy không markdown:
    {{
        "empathetic": "...",
        "inquisitive": "...",
        "reassurance": "..."
    }}
    """
    
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        text = response.text.strip().replace("```json", "").replace("```", "")
        suggestions = json.loads(text)
        return jsonify(suggestions)
    except Exception as e:
        print(e)
        return jsonify({"error": "Failed to generate"}), 500

@app.route('/api/chat/complete', methods=['POST'])
def api_chat_complete():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    
    history = session.get('chat_history', [])
    summary = summarize_conversation(history)
    
    # Lưu vào DB
    db = get_db()
    
    # 1. Lưu Chat History
    for msg in history:
        # Get the analysis object (it will be None for bot messages)
        analysis_data = msg.get('analysis')
        
        # Convert it to a text string if it exists
        analysis_str = json.dumps(analysis_data) if analysis_data else None

        # --- THIS LINE IS NOW INDENTED (FIXED) ---
        db.execute("INSERT INTO chat_history (user_id, role, message, analysis_json) VALUES (?, ?, ?, ?)",
                       (session['user_id'], msg['role'], msg['message'], analysis_str))
    
    # 2. Lưu Summary
    db.execute("INSERT INTO intake_summary (user_id, summary_content, risk_level) VALUES (?, ?, ?)",
               (session['user_id'], summary, 'unknown')) # Bạn có thể tính max risk level ở đây
    db.commit()
    
    session.pop('chat_history', None) # Xóa session chat
    return jsonify({"summary": summary})

# Route để mở giao diện Therapist
@app.route('/therapist/workspace')
def therapist_workspace():
    # Kiểm tra quyền (nếu muốn chặt chẽ)
    if 'role' not in session or session['role'] != 'therapist':
        flash("Chỉ dành cho chuyên gia!", "error")
        return redirect(url_for('home'))
    
    return render_template('therapist_chat.html')

# --- ADD THIS NEW FUNCTION FOR DEBUGGING ---
@app.route('/check_db')
def check_db():
    """
    A temporary debug route to quickly check the chat_history table.
    """
    if 'user_id' not in session:
        return "You must be logged in to check the DB.", 403
        
    db = get_db()
    
    # Get all chat history, newest first
    history_rows = db.execute(
        "SELECT * FROM chat_history ORDER BY timestamp DESC"
    ).fetchall()
    
    # Build a simple HTML page to display the results
    output = "<h1>Chat History Check</h1>"
    output += f"<h3>Found {len(history_rows)} messages.</h3><hr>"
    
    for row in history_rows:
        output += "<div style='border-bottom: 1px solid #ccc; padding: 10px;'>"
        output += f"<p><b>ID:</b> {row['id']}</p>"
        output += f"<p><b>User ID:</b> {row['user_id']}</p>"
        output += f"<p><b>Role:</b> {row['role']}</p>"
        output += f"<p><b>Message:</b> {row['message']}</p>"
        output += f"<p style='color: blue; background: #eee;'><b>ANALYSIS:</b> {row['analysis_json']}</p>"
        output += f"<p><b>Timestamp:</b> {row['timestamp']}</p>"
        output += "</div>"
        
    if not history_rows:
        output += "<p>No history found.</p>"

    return output


# --- MAIN (ĐÃ CẬP NHẬT) ---
if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db() # 1. Tạo DB từ schema.sql
        seed_db_from_json() # 2. Bơm dữ liệu tài nguyên từ JSON
        print("Database initialized and seeded!")
    app.run(host='0.0.0.0', port=5000, debug=True)