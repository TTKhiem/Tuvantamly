1. Installation guide:
pip install flask / uv pip install flask
pip install google_genai / uv pip install google_genai
pip install dotenv / uv pip install dotenv

Create a .env file and follow the format ("{}" are unecessary)
GEMINI_API_KEY = {KEY}

2. Running the code:
Run the code -> Control C (cancel server) -> type "python seed_db.py" in terminal -> run the main.py again

3. How the video/e-book function works:
- You need to chat with the bot first, if there's no conversation then it will show a message if you click on resources telling u to talk to the bot
- After talking to the bot, then the videos are recommended based on 4 general intents "exam_stress", "loneliness", "relationship", "general sadness"
- Unconfirmed status will show all of the video/e-books available
- Clicking on a video will lead to a modal showing the video, clicking on an e-book will lead you to the links
- The forward and backward arrow works like a loop so after it finishes showing all of the video it will loop back to the first one

4. Editing file database:
- The database is saved in seed_db
- Video has 3 columns (title, youtube_video_id and tags), do note that youtube_video_id is ONLY THE ID (after the "v=" part and before the "&t")
- E-book has 4 columns (title, pdf_link, thumbnail_image_link, tags), pdf and thumbnail are the full url
- After updating, delete the database and repeat running the code
