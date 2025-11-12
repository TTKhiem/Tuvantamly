#Figure: Tell Problem -> Gemini phân tích và đưa ra mức độ vấn đề -> Respond tạm thời với phân loại DB có sẵn "ADVICE_DATABASE"
# Sau để dữ liệu dưới dạng JSON và đưa cho specialist or sth
# TO BE IMPLEMENTED: Tóm tắt nội dung đoạn trò chuyện - intended data: 
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")
    
client = genai.Client(api_key = gemini_api_key)
model = "gemini-2.5-flash"

ADVICE_DATABASE = {
    "exam_stress": "Căng thẳng thi cử là điều rất phổ biến. Hãy thử chia nhỏ thời gian học, 45 phút học và 10 phút nghỉ ngơi (phương pháp Pomodoro). Đừng quên hít thở sâu và ngủ đủ giấc nhé.",
    "feeling_lonely": "Cảm thấy cô đơn thật không dễ chịu. Đây là điều nhiều sinh viên gặp phải. Bạn có thể thử tham gia một CLB của trường hoặc một sự kiện. Phòng tư vấn của trường cũng luôn sẵn sàng lắng nghe.",
    "relationship_problem": "Các vấn đề trong mối quan hệ có thể rất mệt mỏi. Hãy cho bản thân thời gian để xử lý cảm xúc. Nói chuyện với một người bạn tin tưởng hoặc chuyên gia tư vấn có thể giúp bạn nhìn rõ hơn.",
    "general_sadness": "Cảm ơn bạn đã chia sẻ. Khi cảm thấy buồn, hãy thử làm một điều nhỏ bạn thích: nghe một bản nhạc, đi dạo. Nếu nó kéo dài, hãy nói chuyện với một chuyên gia nhé.",
    "unknown": "Cảm ơn bạn đã chia sẻ. Tôi không hoàn toàn chắc mình hiểu rõ ý bạn, nhưng tôi đang lắng nghe. Bạn có thể nói rõ hơn không?",
    

    "EMERGENCY": "Tôi nhận thấy bạn đang ở trong một tình huống rất khó khăn và cần sự giúp đỡ ngay lập tức. Xin hãy liên hệ: [SỐ ĐIỆN THOẠI ĐƯỜNG DÂY NÓNG KHẨN CẤP] hoặc [TÊN TRUNG TÂM HỖ TRỢ CỦA TRƯỜNG]. Có người đang chờ để giúp bạn."
}

def analyze_user_input(message):
    if not model:
        return {"intent": "unknown", "sentiment": "neutral", "risk_level": "low"}

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

    Format JSON trả về phải là:
    {{
      "intent": "...",
      "sentiment": "...",
      "risk_level": "..."
    }}
    """
    
    try:
        response = client.models.generate_content(model = model, contents = prompt)
        json_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        analysis = json.loads(json_text)
        return analysis
    
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        print(f"Raw response was: {response.text}")
        return {
            "intent": "unknown",
            "sentiment": "neutral",
            "risk_level": "low"
        }

def format_history_for_summarization(history_list):
    transcript = ""
    for entry in history_list:
        role = "Sinh viên" if entry.get("role") == "student" else "Chatbot"
        message = entry.get("message", "")
        transcript += f"{role}: {message}\n"
    return transcript

def summarize_conversation(chat_history):
    print("\n[LOG] Đang chuẩn bị tóm tắt...")
    transcript = format_history_for_summarization(chat_history)
    
    if not transcript:
        return "Không có nội dung để tóm tắt."

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
        response = client.models.generate_content(model = model, contents = prompt)
        return response.text
    except Exception as e:
        print(f"Can't call API: {e}")
        return "API isssue."
    
def main_chat_loop():
    chat_history = []
    print("--- Chatbot Sức khỏe Tinh thần ---")
    print("Chào bạn, tôi là chatbot hỗ trợ. Tôi có thể giúp gì cho bạn?")
    print("(Gõ 'bye' hoặc 'tạm biệt' để kết thúc cuộc trò chuyện)")

    while True:
        user_message = input("Type a message: ")
        
        if user_message.lower() in ['bye', 'tạm biệt', 'quit']:
            print("Chatbot: Cảm ơn bạn đã chia sẻ. Hãy giữ gìn sức khỏe nhé. Tạm biệt!")
            break
        
        chat_history.append({
            "role": "student",
            "message": user_message,
        })
        
        analysis = analyze_user_input(user_message)
        intent = analysis.get('intent', 'unknown')
        risk_level = analysis.get('risk_level', 'low')

        print(f"[LOG] Phân tích: {analysis}")

        if risk_level == 'high' or intent == 'suicidal_ideation':
            response_message = ADVICE_DATABASE["EMERGENCY"]
            print(f"[ALERT] HIGH RISK DETECTED. User: '{user_message}'")
        else:
            response_message = ADVICE_DATABASE.get(intent, ADVICE_DATABASE["unknown"])

        print(f"Chatbot: {response_message}")
        chat_history.append({
            "role": "chatbot",
            "message": response_message,
            "analysis_for_this_turn": analysis
        })

    if chat_history:
        summary = summarize_conversation(chat_history)
        
        print("\n" + "="*30)
        print(" BÁO CÁO TÓM TẮT CHO CHUYÊN GIA ")
        print("="*30)
        print(summary)
        print("="*30)
        
        final_data = {
            "conversation_history": chat_history,
            "final_summary_for_specialist": summary
        }
        
        with open("results.json", 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        print(f"\n[LOG] Đã lưu toàn bộ lịch sử và tóm tắt vào 'results.json'")
    
    else:
        print("[LOG] Không có cuộc hội thoại nào được ghi lại.")

if __name__ == "__main__":
    main_chat_loop()
        
# user_message = input("Nhap van de cua ban: ")
# analysis = analyze_user_input(user_message)
# intent = analysis.get('intent', 'unknown')
# risk_level = analysis.get('risk_level', 'low')

# print(f"[LOG] Message: '{user_message}' -> Analysis: {analysis}")

# if risk_level == 'high' or intent == 'suicidal_ideation':
#     response_message = ADVICE_DATABASE["EMERGENCY"]
#     print(f"[ALERT] HIGH RISK DETECTED. User: '{user_message}'")
# else:
#     response_message = ADVICE_DATABASE.get(intent, ADVICE_DATABASE["unknown"])

# print(response_message)

# data = ({
#     "response": response_message,
#     "analysis": analysis,
#     "message": user_message
# })

# with open("results.json", 'w', encoding='utf-8') as f:
#     json.dump(data, f, indent = 2, ensure_ascii=False)



