from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def home():
    # Hiển thị form đăng nhập
    return render_template('index.html', form_type='login')

@app.route('/register_page')
def register_page():
    # Hiển thị form đăng ký
    return render_template('index.html', form_type='register')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    return f"Đăng nhập thành công! Email: {email}"

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    return f"Đăng ký thành công! Tài khoản: {username}"

if __name__ == '__main__':
    app.run(debug=True)
