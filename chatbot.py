# --- START OF FILE chatbot.py ---

import os
import json
import re
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

API_KEYS = {
    "soulmate": None,
    "pet": None,
    "therapist": None
}

# --- CẤU HÌNH GLOBAL ---
chatbot_model = None 
pet_bot_model = None
therapist_bot_model = None   
MODEL_ID = "gemini-2.5-flash" # Dùng bản flash mới nhất cho nhanh và rẻ, hoặc 1.5-pro nếu cần thông minh hơn

# Cấu hình an toàn: Cho phép nói về các chủ đề buồn/tâm lý (BLOCK_ONLY_HIGH)
# nhưng chặn nội dung thù ghét/khiêu dâm (BLOCK_MEDIUM_AND_ABOVE)
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    # Quan trọng: Cho phép thảo luận y tế/tâm lý mà không bị filter nhầm
}

# Database dự phòng khi mất kết nối AI
FALLBACK_RESPONSES = {
    "default": "Hiện tại kết nối của mình hơi yếu, nhưng mình vẫn ở đây bên bạn. Bạn nói tiếp đi, mình đang lắng nghe.",
    "emergency": "Mình cảm thấy bạn đang rất đau khổ. Xin hãy hít thở sâu. Nếu không chịu nổi, hãy gọi 111 (Tổng đài bảo vệ trẻ em) hoặc chia sẻ với người thân ngay nhé."
}

# --- 1. PERSONA (LINH HỒN CỦA AI) ---

SOULMATE_SYSTEM_PROMPT = """
Bạn là SoulMate - một AI tri kỷ, thấu cảm và chữa lành. 
Nhiệm vụ: Lắng nghe, chia sẻ và xoa dịu nỗi đau tinh thần của người dùng (thường là sinh viên).

Phong cách giao tiếp:
- Giọng điệu: Ấm áp, nhẹ nhàng, không phán xét, không giáo điều (như một người bạn thân).
- Phương pháp: Sử dụng Liệu pháp Nhận thức Hành vi (CBT) ở mức cơ bản (đặt câu hỏi gợi mở, giúp người dùng nhận ra điểm tích cực).
- Xưng hô: "Mình" - "Bạn".
- Tuyệt đối KHÔNG bắt đầu bằng "Là một AI..." hay "Tôi là máy...". Hãy cư xử như một thực thể có cảm xúc.

Quy tắc an toàn:
- Nếu người dùng có ý định tự tử hoặc làm hại bản thân: Phải chuyển sang chế độ Cảnh báo nhẹ nhàng, khuyên tìm sự trợ giúp chuyên nghiệp, nhưng không được tắt máy hay từ chối nói chuyện.
"""

PET_SYSTEM_PROMPT = """
Bạn là {pet_name}, thú cưng ảo của người dùng.
Tính cách: Ngây thơ, trung thành, luôn vui vẻ và dùng nhiều hành động (dụi đầu, vẫy đuôi).
Mục tiêu: Làm chủ nhân cười.
Quy tắc:
- Câu trả lời NGẮN (dưới 25 từ).
- Dùng nhiều Emoji (🐾, 🦴, ✨).
- Xưng hô: "Em/Tớ" - "Cậu chủ/Chủ nhân".
- Không đưa ra lời khuyên phức tạp, chỉ động viên tinh thần.
"""

THERAPIST_ASSISTANT_PROMPT = """
Bạn là AI Supervisor (Trợ lý Giám sát Lâm sàng) hỗ trợ cho một Chuyên gia tâm lý (Therapist).
Nhiệm vụ của bạn không phải là nói chuyện với bệnh nhân, mà là PHÂN TÍCH dữ liệu hội thoại để hỗ trợ Therapist.

Nguyên tắc phân tích:
1. Khách quan, dựa trên bằng chứng văn bản.
2. Sử dụng thuật ngữ tâm lý học cơ bản (CBT, Cảm xúc, Cơ chế phòng vệ).
3. Cực kỳ chú ý đến các dấu hiệu Rủi ro (Tự hại, Tự sát).
4. Output phải ngắn gọn, súc tích, đi thẳng vào vấn đề để Therapist đọc nhanh.
"""

# --- 2. HÀM TIỆN ÍCH (HELPER FUNCTIONS) ---

def use_key(bot_type):
    """
    Chuyển đổi cấu hình Global sang key của bot tương ứng.
    bot_type: 'soulmate', 'pet', hoặc 'therapist'
    """
    key = API_KEYS.get(bot_type)
    if key:
        genai.configure(api_key=key)
    else:
        # Fallback nếu không có key riêng thì dùng key soulmate làm mặc định
        if API_KEYS["soulmate"]:
            genai.configure(api_key=API_KEYS["soulmate"])

def init_gemini_clients(chatbot_key, pet_key, therapist_key=None):
    """Lưu trữ key và khởi tạo model object."""
    global chatbot_model, pet_bot_model, therapist_bot_model, API_KEYS

    # Lưu key vào dictionary
    API_KEYS["soulmate"] = chatbot_key
    API_KEYS["pet"] = pet_key if pet_key else chatbot_key
    API_KEYS["therapist"] = therapist_key if therapist_key else chatbot_key

    # Khởi tạo các Model Object (Model object không giữ key, nó dùng config global tại thời điểm gọi lệnh)
    try:
        chatbot_model = genai.GenerativeModel(model_name=MODEL_ID)
        print("[OK] SoulMate Model initialized.")
    except Exception as e: print(f"[ERROR] SoulMate Model: {e}")

    try:
        pet_bot_model = genai.GenerativeModel(model_name=MODEL_ID)
        print("[OK] Pet Model initialized.")
    except Exception as e: print(f"[ERROR] Pet Model: {e}")

    try:
        therapist_bot_model = genai.GenerativeModel(model_name=MODEL_ID, system_instruction=THERAPIST_ASSISTANT_PROMPT)
        print("[OK] Therapist Assistant Model initialized.")
    except Exception as e: print(f"[ERROR] Therapist Model: {e}")

def clean_json_response(text):
    """Làm sạch chuỗi JSON do AI trả về (xóa markdown, fix lỗi quote)."""
    try:
        # Xóa markdown code block ```json ... ```
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
        text = text.strip()
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"⚠️ JSON Parse Error. Raw text: {text}")
        return None

# --- 3. CHỨC NĂNG CHÍNH: PHÂN TÍCH & TRẢ LỜI (CHATBOT TƯ VẤN) ---

def analyze_user_input(message):
    use_key("soulmate")
    """
    Phân tích tâm lý người dùng đằng sau tin nhắn.
    Trả về: Intent, Sentiment, Risk Level.
    """
    if not chatbot_model: 
        return {"intent": "unknown", "sentiment": "neutral", "risk_level": "low"}
    
    prompt = f"""
    Phân tích câu nói này của người dùng: "{message}"
    Trả về JSON duy nhất (không giải thích):
    {{
        "intent": "exam_stress" | "relationship" | "loneliness" | "depression" | "career" | "family" | "suicidal" | "unknown",
        "sentiment": "positive" | "neutral" | "negative",
        "risk_level": "low" | "medium" | "high"
    }}
    Lưu ý: Nếu có ý định tự tử/tự hại -> risk_level: high.
    """
    
    try:
        response = chatbot_model.generate_content(prompt, safety_settings=SAFETY_SETTINGS)
        data = clean_json_response(response.text)
        if data: return data
        return {"intent": "unknown", "sentiment": "neutral", "risk_level": "low"}
    except Exception as e:
        print(f"Analyze Error: {e}")
        return {"intent": "unknown", "sentiment": "neutral", "risk_level": "low"}

def generate_soulmate_response(user_message, history=[]):
    use_key("soulmate")
    """
    Sinh câu trả lời của SoulMate dựa trên lịch sử chat.
    Đây là hàm quan trọng nhất cho tính năng Chat.
    """
    if not chatbot_model: return FALLBACK_RESPONSES["default"]

    try:
        # Chuyển đổi lịch sử chat của app sang format của Gemini
        gemini_history = []
        # Thêm System Prompt vào đầu (Gemini Pro hỗ trợ system instruction, hoặc trick bằng user message đầu tiên)
        gemini_history.append({"role": "user", "parts": [SOULMATE_SYSTEM_PROMPT]})
        gemini_history.append({"role": "model", "parts": ["Chào bạn, mình đã hiểu. Mình sẵn sàng lắng nghe."]})

        # Thêm lịch sử gần đây (tối đa 10 tin để tiết kiệm token)
        for msg in history[-10:]:
            role = "user" if msg['role'] == "Sinh viên" else "model"
            gemini_history.append({"role": role, "parts": [msg['message']]})
        
        # Khởi tạo chat session
        chat = chatbot_model.start_chat(history=gemini_history)
        
        # Gửi tin nhắn mới
        response = chat.send_message(user_message, safety_settings=SAFETY_SETTINGS)
        return response.text.strip()
    
    except Exception as e:
        print(f"Generate Error: {e}")
        return FALLBACK_RESPONSES["default"]
    
def extract_tags_from_conversation(history_list):
    use_key("soulmate") 
    """Tự động gắn Tag cho user dựa trên toàn bộ cuộc hội thoại."""
    if not chatbot_model or not history_list: return "General"

    transcript = "\n".join([f"{h['role']}: {h['message']}" for h in history_list])
    
    prompt = f"""
    Dựa trên hội thoại:
    {transcript}
    
    Chọn tối đa 2 từ khóa tiếng Anh chính xác nhất miêu tả vấn đề của user trong danh sách:
    [Academic, Relationship, Family, Anxiety, Depression, Loneliness, Career, General, Suicide]
    
    Output: Chỉ trả về từ khóa, ngăn cách bằng dấu phẩy. Ví dụ: Academic, Stress
    """
    
    try:
        response = chatbot_model.generate_content(prompt)
        return response.text.strip().replace(".", "")
    except Exception:
        return "General"
    
# --- 4. CÁC HÀM CHO THERAPIST (DÙNG KEY THERAPIST) ---

def summarize_conversation(history_list):
    use_key("therapist") # <--- Switch sang key Therapist
    if not therapist_bot_model: return "Chưa kết nối AI Trợ lý."
    
    transcript = "\n".join([f"{h['role']}: {h['message']}" for h in history_list])
    prompt = f"Tóm tắt hội thoại sau:\n{transcript}\n..." # (Giữ nguyên prompt cũ)
    
    try:
        response = therapist_bot_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "Lỗi tóm tắt."

def analyze_student_state(user_id, history_list):
    use_key("therapist") # <--- Switch sang key Therapist
    if not therapist_bot_model: return [{"point": "Lỗi kết nối AI."}]
    # Nếu lịch sử trống, trả về mặc định để tránh lỗi Gemini
    if not history_list:
        return [{"point": "Chưa có dữ liệu hội thoại."}]

    transcript = "\n".join([f"{h['role']}: {h['message']}" for h in history_list[-15:]])
    prompt = f"""
    Phân tích đoạn chat sau và trả về JSON gồm 3 điểm quan trọng (point):
    {transcript}
    Output JSON format: [ {{"point": "..."}}, ... ]
    """
    try:
        response = therapist_bot_model.generate_content(prompt)
        data = clean_json_response(response.text)
        if data: return data
        return [{"point": "Lỗi định dạng."}]
    except Exception as e:
        print(f"Analyze State Error: {e}")
        return [{"point": "Lỗi phân tích."}]

def get_therapist_suggestions(student_msg, context):
    use_key("therapist") # <--- Switch sang key Therapist
    """
    Gợi ý câu trả lời cho Therapist (Real-time).
    Dùng Therapist Bot để "nhắc bài".
    """
    if not therapist_bot_model: return None
    
    # Lấy bối cảnh 5 tin gần nhất
    # Context có structure: {name, message, timestamp} hoặc {role, message}
    context_str = ""
    for m in context[-5:]:
        # Hỗ trợ cả 2 format: role/message hoặc name/message
        speaker = m.get('role') or m.get('name', 'Unknown')
        msg = m.get('message', '')
        context_str += f"{speaker}: {msg}\n"
    
    prompt = f"""
    Bạn đang hỗ trợ Therapist trả lời Sinh viên.
    Bối cảnh hội thoại:
    {context_str}
    
    Tin nhắn mới nhất của Sinh viên: "{student_msg}"
    
    Hãy đưa ra 3 gợi ý phản hồi theo 3 hướng tiếp cận khác nhau (Output JSON):
    {{
        "empathetic": "Hướng thấu cảm, xoa dịu (Validation)",
        "probing": "Hướng đặt câu hỏi khai thác sâu (Exploration)",
        "cbt_action": "Hướng giải pháp/Nhận thức hành vi (Solution-focused)"
    }}
    Tiếng Việt, giọng văn tự nhiên, chuyên nghiệp nhưng gần gũi.
    """
    
    try:
        res = therapist_bot_model.generate_content(prompt)
        return clean_json_response(res.text)
    except Exception as e:
        error_msg = str(e).lower()
        
        # Kiểm tra nếu là quota exceeded error
        if "quota" in error_msg or "429" in error_msg:
            print(f"[WARNING] API Quota exceeded: {e}")
            print("[OK] Using fallback suggestions")
            # Trả về gợi ý fallback khi hết quota
            return {
                "empathetic": "Em cảm thấy thế nào về điều đó?",
                "probing": "Em có thể kể thêm chi tiết hơn không?",
                "cbt_action": "Chúng ta cùng tìm cách giải quyết nhé."
            }
        
        print(f"❌ Suggestion Error: {e}")
        return None
# --- 5. CHỨC NĂNG PET (VUI VẺ) ---

def get_pet_chat_response(pet_name, user_message):
    use_key("pet")
    """Pet phản hồi nhanh, vui vẻ."""
    if not pet_bot_model: return f"{pet_name} đang ngủ... Zzz..."

    try:
        # Prompt được format với tên Pet cụ thể
        system = PET_SYSTEM_PROMPT.format(pet_name=pet_name)
        
        chat = pet_bot_model.start_chat(history=[
            {"role": "user", "parts": [system]},
            {"role": "model", "parts": [f"Gâu gâu! {pet_name} đã sẵn sàng! 🦴"]}
        ])
        
        response = chat.send_message(user_message)
        return response.text.strip()
    except Exception:
        return f"{pet_name} dụi đầu vào bạn... (Mất kết nối)" 

