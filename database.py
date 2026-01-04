import sqlite3
import click
from flask import g, current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

DATABASE = 'app.db' # Tên database hợp nhất

def get_db():
    """Mở một kết nối database mới nếu chưa có cho context hiện tại."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            DATABASE,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """Đóng kết nối database."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Xóa dữ liệu cũ, tạo bảng mới VÀ tạo tài khoản Admin mặc định."""
    db = get_db()
    
    # 1. Thực thi file schema.sql để tạo bảng
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
        
    # 2. --- TỰ ĐỘNG TẠO ADMIN ---
    try:
        # Bạn có thể đổi thông tin đăng nhập mặc định tại đây
        admin_user = "admin"
        admin_email = "admin@gmail.com"
        admin_pass = "admin123" 
        hashed_pw = generate_password_hash(admin_pass)
        
        # Insert Admin User
        cursor = db.execute(
            "INSERT INTO users (username, email, password, role, gold) VALUES (?, ?, ?, ?, ?)",
            (admin_user, admin_email, hashed_pw, 'admin', 9999)
        )
        admin_id = cursor.lastrowid
        
        # Insert Admin Pet (Để tránh lỗi logic nếu admin lỡ vào dashboard)
        db.execute(
            "INSERT INTO pets (user_id, name, skin_id, background_id) VALUES (?, ?, 0, 0)", 
            (admin_id, "Admin Bot")
        )
        
        db.commit()
        click.echo(f"Đã tạo Admin mặc định: {admin_email} / {admin_pass}")
        
    except sqlite3.IntegrityError:
        click.echo("Admin account already exists.")
    except Exception as e:
        click.echo(f"Lỗi khi tạo admin: {e}")

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Xóa dữ liệu hiện có và tạo bảng mới."""
    init_db()
    click.echo('Đã khởi tạo database.')

def init_app(app):
    """Đăng ký các hàm quản lý database với application."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

