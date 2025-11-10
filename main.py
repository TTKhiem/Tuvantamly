from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash 
from datetime import datetime
import re

from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.secret_key = 'secret-key'  

@app.route('/')
def home():
    user = None
    if 'username' in session:
        user = {'username': session['username'], 'role': session['role']}
    return render_template('index.html', form_type='login', user=user)

@app.route('/register_page')

def register_page():
    return render_template('index.html', form_type='register')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        with sqlite3.connect('users.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
            user = cur.fetchone()

        if user:
            session['username'] = user[1]
            session['role'] = user[4]
            flash(f"Chào mừng {session['username']}!", "success")
            return redirect(url_for('home'))
        else:
            flash("Sai email hoặc mật khẩu!", "error")
            return render_template('index.html')  # quay lại trang login hiện tại
    else:
        return render_template('index.html')


@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing = cur.fetchone()

        if existing:
            flash("Email đã tồn tại!", "error")
            return redirect(url_for('register_page'))
        else:
            cur.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                        (username, email, password))
            conn.commit()
            flash(f"Đăng ký thành công! Hãy đăng nhập, {username} 🎉", "success")
            return redirect(url_for('home'))  
@app.route('/user')
def user_dashboard():
    if 'role' not in session or session['role'] != 'user':
        return redirect(url_for('home'))
    
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row 
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (session['username'],))
        user_data = cur.fetchone()

    return render_template('user_dashboard.html', user=user_data)
@app.route('/your_pists')
def your_therapists():
    return render_template('user_dashboard.html')
@app.route('/admin')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('home'))
    return f"Chào quản trị viên {session['username']} 🛠️"   
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        return redirect(url_for('home'))

    username = session['username']
    date_of_birth = request.form.get('date_of_birth')
    phone = request.form.get('phone')
    address = request.form.get('address')

    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute('''
            UPDATE users 
            SET date_of_birth = ?, phone = ?, address = ?, date_joined = ?
            WHERE username = ?
        ''', (date_of_birth, phone, address, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username))
        conn.commit()

    flash("Cập nhật thông tin thành công!", "success")
    return redirect(url_for('user_dashboard'))

if __name__ == '__main__':
    
   app.run(host='0.0.0.0', port=5000, debug=True)

# @app.route('/register', methods=['POST'])
# def register():
#     username = request.form.get('username', '').strip()
#     email = request.form.get('email', '').strip()
#     password = request.form.get('password', '').strip()

#     # 1️⃣ Kiểm tra trống
#     if not username or not email or not password:
#         flash("Vui lòng nhập đầy đủ thông tin!", "error")
#         return redirect(url_for('register_page'))

#     # 2️⃣ Kiểm tra định dạng email hợp lệ (mọi tên miền, miễn đúng cú pháp)
#     email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
#     if not re.match(email_pattern, email):
#         flash("Email không hợp lệ! Vui lòng nhập đúng định dạng (vd: ten@gmail.com).", "error")
#         return redirect(url_for('register_page'))

#     # 3️⃣ Kiểm tra username (chỉ cho phép chữ, số, gạch dưới; 3–20 ký tự)
#     if not re.match(r'^[A-Za-z0-9_]{3,20}$', username):
#         flash("Tên người dùng chỉ được chứa chữ, số hoặc dấu gạch dưới (3-20 ký tự).", "error")
#         return redirect(url_for('register_page'))

#     # 4️⃣ Kiểm tra độ mạnh mật khẩu (ít nhất 6 ký tự, có cả chữ và số)
#     if len(password) < 6 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
#         flash("Mật khẩu phải có ít nhất 6 ký tự, bao gồm cả chữ và số!", "error")
#         return redirect(url_for('register_page'))

#     # 5️⃣ Kiểm tra email trùng trong database
#     with sqlite3.connect('users.db') as conn:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM users WHERE email = ?", (email,))
#         existing = cur.fetchone()

#         if existing:
#             flash("Email này đã được đăng ký! Hãy thử email khác.", "error")
#             return redirect(url_for'register_page'))

#         # 6️⃣ Hash mật khẩu để bảo mật trước khi lưu
#         hashed_password = generate_password_hash(password)

#         # 7️⃣ Thêm user vào database
#         cur.execute("""
#             INSERT INTO users (username, email, password)
#             VALUES (?, ?, ?)
#         """, (username, email, hashed_password))
#         conn.commit()

#     # 8️⃣ Thông báo thành công
#     flash(f"Đăng ký thành công! Hãy đăng nhập, {username} 🎉", "success")
#     # return redirect(url_for('home'))
    # return render_template('index.html', form_type='register')