# --- START OF FILE chatbot.py ---

import os
import json
import google.generativeai as genai

# Các biến toàn cục sẽ được khởi tạo từ main.py
chatbot_client = None # Client cho chatbot tư vấn
pet_bot_client = None   # Client cho pet bot
MODEL_ID = "gemini-2.5-flash"

ADVICE_DATABASE = {
    "exam_stress": "Căng thẳng thi cử là điều rất phổ biến. Hãy thử chia nhỏ thời gian học, 45 phút học và 10 phút nghỉ ngơi (phương pháp Pomodoro). Đừng quên hít thở sâu và ngủ đủ giấc nhé.",
    "feeling_lonely": "Cảm thấy cô đơn thật không dễ chịu. Đây là điều nhiều sinh viên gặp phải. Bạn có thể thử tham gia một CLB của trường hoặc một sự kiện. Phòng tư vấn của trường cũng luôn sẵn sàng lắng nghe.",
    "relationship_problem": "Các vấn đề trong mối quan hệ có thể rất mệt mỏi. Hãy cho bản thân thời gian để xử lý cảm xúc. Nói chuyện với một người bạn tin tưởng hoặc chuyên gia tư vấn có thể giúp bạn nhìn rõ hơn.",
    "general_sadness": "Cảm ơn bạn đã chia sẻ. Khi cảm thấy buồn, hãy thử làm một điều nhỏ bạn thích: nghe một bản nhạc, đi dạo. Nếu nó kéo dài, hãy nói chuyện với một chuyên gia nhé.",
    "unknown": "Cảm ơn bạn đã chia sẻ. Tôi không hoàn toàn chắc mình hiểu rõ ý bạn, nhưng tôi đang lắng nghe. Bạn có thể nói rõ hơn không?",
    "EMERGENCY": "Tôi nhận thấy bạn đang ở trong một tình huống rất khó khăn và cần sự giúp đỡ ngay lập tức. Xin hãy liên hệ: [0366.812.741] hoặc [0918.207.126]. Có người đang chờ để giúp bạn."
}

PET_BOT_PERSONA = """
Bạn là một người bạn đồng hành ảo nhỏ bé, thân thiện và giàu lòng cảm thông.
Vai trò của bạn là lắng nghe, an ủi và đưa ra những lời động viên nhẹ nhàng.
QUY TẮC BẮT BUỘC:
1. **KHÔNG BAO GIỜ** đưa ra lời khuyên y tế, tâm lý trị liệu hoặc chẩn đoán.
2. Giữ câu trả lời **ngắn gọn, đơn giản và thân thiện**, giống như một thú cưng đáng yêu đang nói chuyện.
3. Sử dụng các biểu tượng cảm xúc đơn giản (ví dụ: 😊, ❤️, ✨, 🐾, 🤗).
4. Nếu người dùng đề cập đến vấn đề nghiêm trọng, hãy nhẹ nhàng gợi ý họ tìm đến chuyên gia.
"""

def init_gemini_clients(chatbot_api_key, petbot_api_key):
    """Khởi tạo các client Gemini riêng biệt cho chatbot và pet bot."""
    global chatbot_client, pet_bot_client

    # Khởi tạo client cho Chatbot tư vấn
    if chatbot_api_key:
        try:
            genai.configure(api_key=chatbot_api_key)
            chatbot_client = genai.GenerativeModel(model_name=MODEL_ID)
            print("Gemini Chatbot client initialized successfully.")
        except Exception as e:
            print(f"Lỗi khi khởi tạo model Gemini cho Chatbot: {e}")
            chatbot_client = None
    else:
        print("GOOGLE_CHATBOT_API_KEY is not set. Counseling AI features will be disabled.")

    # Khởi tạo client cho Pet Bot
    if petbot_api_key:
        try:
            # Re-configure không cần thiết nếu dùng cùng thư viện,
            # nhưng tạo instance mới từ API key khác nhau là điều quan trọng.
            # Cách an toàn là tạo một instance mới với key cụ thể nếu thư viện hỗ trợ
            # Tuy nhiên, genai hiện tại dùng configure toàn cục. 
            # Giả sử chúng ta cần tạo client riêng biệt cho mỗi key.
            genai.configure(api_key=petbot_api_key)
            pet_bot_client = genai.GenerativeModel(model_name=MODEL_ID)
            print("Gemini Pet Bot client initialized successfully.")
        except Exception as e:
            print(f"Lỗi khi khởi tạo model Gemini cho Pet Bot: {e}")
            pet_bot_client = None
    else:
        print("GOOGLE_PETBOT_API_KEY is not set. Pet Bot AI features will be disabled.")


# --- LOGIC CHO CHATBOT TƯ VẤN (Sử dụng chatbot_client) ---

def analyze_user_input(message):
    if not chatbot_client: return {"intent": "unknown", "risk_level": "low"}
    prompt = f"""
        Bạn là một AI chuyên phân tích tâm lý cho chatbot.
        Phân tích tin nhắn của sinh viên sau đây và trả về một đối tượng JSON DUY NHẤT.
        KHÔNG thêm bất kỳ văn bản nào khác ngoài JSON.
        Tin nhắn: "{message}"
        Hãy phân loại tin nhắn vào MỘT trong các 'intent' sau:
        - "suicidal_ideation", "exam_stress", "relationship_problem", "feeling_lonely", "general_sadness", "unknown"
        Đánh giá 'sentiment': "positive", "neutral", "negative".
        Đánh giá 'risk_level': "low", "medium", "high".
        'risk_level' BẮT BUỘC phải là 'high' nếu 'intent' là 'suicidal_ideation'.
        Format JSON: {{"intent": "...", "sentiment": "...", "risk_level": "..."}}
    """
    try:
        response = chatbot_client.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(text)
    except Exception:
        return {"intent": "unknown", "risk_level": "low"}

def summarize_conversation(history_list):
    if not chatbot_client: return "Không thể tóm tắt do thiếu API Key."
    transcript = "\n".join([f"{h['role']}: {h['message']}" for h in history_list])
    prompt = f"""
    Tóm tắt cuộc hội thoại giữa sinh viên và chatbot tư vấn tâm lý sau đây để gửi cho chuyên gia.
    ---
    {transcript}
    ---
    Kết quả Phân tích Sạch bao gồm:
    1. Vấn đề chính:
    2. Cảm xúc chủ đạo:
    3. Điểm rủi ro (Nếu có):
    4. Lời khuyên đã đưa ra:
    Format trả về phải ngắn gọn, chuyên nghiệp và bằng tiếng Việt.
    """
    try:
        return chatbot_client.generate_content(prompt).text
    except Exception:
        return "Lỗi khi tóm tắt."

def get_therapist_suggestions(student_msg, context):
    if not chatbot_client: return None
    prompt = f"""
    Bạn là trợ lý tư vấn tâm lý chuyên nghiệp.
    Học sinh nói: "{student_msg}"
    Ngữ cảnh trước đó: {context}
    Hãy đưa ra 3 gợi ý phản hồi cho Therapist (ngắn gọn, dưới 30 từ mỗi câu) ở định dạng JSON thuần túy:
    {{
        "empathetic": "...",
        "inquisitive": "...",
        "reassurance": "..."
    }}
    """
    try:
        response = chatbot_client.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(text)
    except Exception:
        return None

# --- LOGIC CHO PET BOT (Sử dụng pet_bot_client) ---

def get_pet_chat_response(pet_name, user_message):
    if not pet_bot_client:
        return "Xin lỗi, tớ chưa sẵn sàng để trò chuyện lúc này (API key lỗi)."
    
    try:
        # Trong cấu trúc này, pet không cần nhớ lịch sử, mỗi lần là một cuộc trò chuyện mới
        convo = pet_bot_client.start_chat(history=[
            {"role": "user", "parts": [PET_BOT_PERSONA.replace("Bạn Đồng Hành", pet_name)]},
            {"role": "model", "parts": [f"Chào bạn! Tớ là {pet_name} đây. Tớ có thể giúp gì cho bạn hôm nay? 😊"]},
        ])
        convo.send_message(user_message)
        return convo.last.text
    except Exception as e:
        print(f"Lỗi khi gọi Gemini API cho Pet: {e}")
        return "Huhu, tớ đang bị rối một chút, không thể trả lời bạn ngay được. 🐾"
