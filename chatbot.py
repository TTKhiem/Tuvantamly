# --- START OF FILE chatbot.py ---

import os
import json
import re
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- CẤU HÌNH GLOBAL ---
chatbot_client = None 
pet_bot_client = None   
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

# --- 2. HÀM TIỆN ÍCH (HELPER FUNCTIONS) ---

def init_gemini_clients(chatbot_api_key, petbot_api_key):
    """Khởi tạo client với cấu hình an toàn."""
    global chatbot_client, pet_bot_client

    if chatbot_api_key:
        try:
            genai.configure(api_key=chatbot_api_key)
            chatbot_client = genai.GenerativeModel(model_name=MODEL_ID)
            print("✅ SoulMate AI (Counseling) ready.")
        except Exception as e:
            print(f"❌ Error initializing SoulMate AI: {e}")

    if petbot_api_key:
        try:
            # Nếu dùng chung key thì không cần configure lại, nhưng để an toàn cứ check
            if petbot_api_key != chatbot_api_key:
                genai.configure(api_key=petbot_api_key)
            pet_bot_client = genai.GenerativeModel(model_name=MODEL_ID)
            print("✅ Pet AI ready.")
        except Exception as e:
            print(f"❌ Error initializing Pet AI: {e}")

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
    """
    Phân tích tâm lý người dùng đằng sau tin nhắn.
    Trả về: Intent, Sentiment, Risk Level.
    """
    if not chatbot_client: 
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
        response = chatbot_client.generate_content(prompt, safety_settings=SAFETY_SETTINGS)
        data = clean_json_response(response.text)
        if data: return data
        return {"intent": "unknown", "sentiment": "neutral", "risk_level": "low"}
    except Exception as e:
        print(f"Analyze Error: {e}")
        return {"intent": "unknown", "sentiment": "neutral", "risk_level": "low"}

def generate_soulmate_response(user_message, history=[]):
    """
    Sinh câu trả lời của SoulMate dựa trên lịch sử chat.
    Đây là hàm quan trọng nhất cho tính năng Chat.
    """
    if not chatbot_client: return FALLBACK_RESPONSES["default"]

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
        chat = chatbot_client.start_chat(history=gemini_history)
        
        # Gửi tin nhắn mới
        response = chat.send_message(user_message, safety_settings=SAFETY_SETTINGS)
        return response.text.strip()
    
    except Exception as e:
        print(f"Generate Error: {e}")
        return FALLBACK_RESPONSES["default"]

# --- 4. CHỨC NĂNG HỖ TRỢ: TAGGING & SUMMARY ---

def extract_tags_from_conversation(history_list):
    """Tự động gắn Tag cho user dựa trên toàn bộ cuộc hội thoại."""
    if not chatbot_client or not history_list: return "General"

    transcript = "\n".join([f"{h['role']}: {h['message']}" for h in history_list])
    
    prompt = f"""
    Dựa trên hội thoại:
    {transcript}
    
    Chọn tối đa 2 từ khóa tiếng Anh chính xác nhất miêu tả vấn đề của user trong danh sách:
    [Academic, Relationship, Family, Anxiety, Depression, Loneliness, Career, General]
    
    Output: Chỉ trả về từ khóa, ngăn cách bằng dấu phẩy. Ví dụ: Academic, Stress
    """
    
    try:
        response = chatbot_client.generate_content(prompt)
        return response.text.strip().replace(".", "")
    except Exception:
        return "General"

def summarize_conversation(history_list):
    """Tóm tắt cho Therapist."""
    if not chatbot_client: return "Lỗi kết nối AI."
    
    transcript = "\n".join([f"{h['role']}: {h['message']}" for h in history_list])
    prompt = f"""
    Đóng vai trợ lý bác sĩ tâm lý. Tóm tắt hồ sơ sau (Tiếng Việt):
    ---
    {transcript}
    ---
    Output format:
    - Vấn đề chính: ...
    - Cảm xúc: ...
    - Đánh giá rủi ro: ...
    - Khuyến nghị sơ bộ: ...
    """
    try:
        return chatbot_client.generate_content(prompt).text
    except Exception:
        return "Không thể tóm tắt."

def get_therapist_suggestions(student_msg, context):
    """Gợi ý câu trả lời cho Therapist trong thời gian thực."""
    if not chatbot_client: return None
    
    context_str = "\n".join([f"{m['role']}: {m['message']}" for m in context[-3:]])
    prompt = f"""
    Context: {context_str}
    User: "{student_msg}"
    
    Gợi ý 3 câu trả lời ngắn cho Therapist (JSON):
    {{
        "empathetic": "Thấu cảm...",
        "probing": "Đặt câu hỏi khai thác...",
        "action": "Hướng giải pháp..."
    }}
    """
    try:
        res = chatbot_client.generate_content(prompt)
        return clean_json_response(res.text)
    except Exception:
        return None

# --- 5. CHỨC NĂNG PET (VUI VẺ) ---

def get_pet_chat_response(pet_name, user_message):
    """Pet phản hồi nhanh, vui vẻ."""
    if not pet_bot_client: return f"{pet_name} đang ngủ... Zzz..."

    try:
        # Prompt được format với tên Pet cụ thể
        system = PET_SYSTEM_PROMPT.format(pet_name=pet_name)
        
        chat = pet_bot_client.start_chat(history=[
            {"role": "user", "parts": [system]},
            {"role": "model", "parts": [f"Gâu gâu! {pet_name} đã sẵn sàng! 🦴"]}
        ])
        
        response = chat.send_message(user_message)
        return response.text.strip()
    except Exception:
        return f"{pet_name} dụi đầu vào bạn... (Mất kết nối)" 
