1. Cài đặt các gói:
pip install Flask
pip install google-generativeai
pip install python-dotenv
pip install Werkzeug
2. Tạo một file mới tên là .env trong thư mục gốc của dự án.
Sao chép nội dung dưới đây và dán vào file .env:
GOOGLE_CHATBOT_API_KEY="YOUR_GEMINI_API_KEY_FOR_COUNSELING_HERE"
GOOGLE_PETBOT_API_KEY="YOUR_GEMINI_API_KEY_FOR_THE_PET_HERE"
APP_SECRET=your_app_secret // Dòng này cứ copy y chang là được

3. Chạy web và register tài khoản như bình thường. Sau đó vào app.db set role cho tài khoản:
   ở Terminal gõ:
   sqlite3 app.db
   SELECT id, username, role FROM users;
   // Đổi role qua therapist
   UPDATE users SET role = 'therapist' WHERE id = 1; // xem id qua app.db 
   . exit thoát và chạy lại main



   

