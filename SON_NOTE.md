# thêm mới:
- SON_NOTE.md
- /matchmaking
- decorators.py
- /templates: student_matchmaking.html, therapist_matchmaking.html
- /static: matchmaking_script.js 


# chỉnh sửa file gốc (version panh đưa):
- schema.sql:
+ thêm 3 table: matchmaking_queue_students, matchmaking_queue_therapists, matchmaking_results
+ chỉnh table users: cột role

- main.py:
+ hàm def init_db (line 63): đem 2 biến db_path và schema_path ra ngoài hàm
+ hàm login (line 108):
* thêm điều kiện if not email or not password
* thêm session['user_id'] = user['id'] ở điều kiện if user
+ thêm from decorators import admin_required, student_required, therapist_required
+ thêm from matchmaking.matchmaking_repository import add_student_to_matchmaking_queue, add_therapist_to_matchmaking_queue
+ thêm from matchmaking.matchmaking_logic import run_matchmaking
+ các route cho matchmaking (line 208 -> line 220)
