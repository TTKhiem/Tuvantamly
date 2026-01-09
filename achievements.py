"""
Quản lý Achievement System & Streaks cho SoulMate
"""

import sqlite3
from datetime import datetime, timedelta

# Định nghĩa các Achievement
ACHIEVEMENTS = {
    'khoi_dau': {
        'id': 'khoi_dau',
        'name': 'Khởi đầu',
        'emoji': '🌟',
        'color': '#FFF3CD',
        'description': 'Hoàn thành lần đầu tiên',
        'condition': 'first_action'
    },
    '5_chats': {
        'id': '5_chats',
        'name': '5 Cuộc chat',
        'emoji': '💬',
        'color': '#DCE9F5',
        'description': 'Hoàn thành 5 cuộc chat',
        'condition': 'chat_count >= 5'
    },
    '10_quests': {
        'id': '10_quests',
        'name': '10 Quest',
        'emoji': '🎯',
        'color': '#DCF0E7',
        'description': 'Hoàn thành 10 nhiệm vụ',
        'condition': 'quest_count >= 10'
    }
}


def get_db():
    """Lấy kết nối database"""
    db = sqlite3.connect('app.db')
    db.row_factory = sqlite3.Row
    return db


def initialize_user_streak(user_id):
    """Tạo streak record cho user mới"""
    db = get_db()
    try:
        db.execute("""
            INSERT INTO user_streaks (user_id, current_streak, longest_streak, last_activity_date)
            VALUES (?, 1, 1, CURRENT_DATE)
        """, (user_id,))
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # User đã có streak record rồi
    finally:
        db.close()


def update_streak(user_id):
    """
    Cập nhật streak khi user có activity
    - Nếu activity hôm nay → không thay đổi
    - Nếu activity hôm qua → tăng streak
    - Nếu vắng > 1 ngày → reset streak
    """
    db = get_db()
    try:
        # Lấy streak hiện tại
        streak = db.execute(
            "SELECT * FROM user_streaks WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if not streak:
            initialize_user_streak(user_id)
            return {'current_streak': 1, 'action': 'initialized'}

        last_date = datetime.strptime(streak['last_activity_date'], '%Y-%m-%d').date()
        today = datetime.now().date()
        days_diff = (today - last_date).days

        if days_diff == 0:
            # Đã activity hôm nay rồi
            return {'current_streak': streak['current_streak'], 'action': 'already_today'}

        elif days_diff == 1:
            # Liên tục - tăng streak
            new_streak = streak['current_streak'] + 1
            db.execute("""
                UPDATE user_streaks 
                SET current_streak = ?, longest_streak = MAX(longest_streak, ?), last_activity_date = CURRENT_DATE
                WHERE user_id = ?
            """, (new_streak, new_streak, user_id))
            db.commit()
            return {'current_streak': new_streak, 'action': 'streak_increased'}

        else:
            # Vắng > 1 ngày - reset streak
            db.execute("""
                UPDATE user_streaks 
                SET current_streak = 1, last_activity_date = CURRENT_DATE
                WHERE user_id = ?
            """, (user_id,))
            db.commit()
            return {'current_streak': 1, 'action': 'streak_reset'}

    finally:
        db.close()


def check_and_unlock_achievement(user_id, achievement_id):
    """
    Kiểm tra và unlock achievement nếu chưa có
    Return: True nếu vừa unlock, False nếu đã có hoặc không đủ điều kiện
    """
    db = get_db()
    try:
        # Kiểm tra xem user đã có achievement này chưa
        existing = db.execute("""
            SELECT * FROM user_achievements 
            WHERE user_id = ? AND achievement_id = ?
        """, (user_id, achievement_id)).fetchone()

        if existing:
            return False  # Đã có rồi

        # Unlock achievement
        db.execute("""
            INSERT INTO user_achievements (user_id, achievement_id)
            VALUES (?, ?)
        """, (user_id, achievement_id))
        db.commit()
        return True  # Vừa unlock

    except sqlite3.IntegrityError:
        return False
    finally:
        db.close()


def check_all_achievements(user_id):
    """
    Kiểm tra tất cả achievements cho user và unlock nếu đủ điều kiện
    """
    db = get_db()
    try:
        # Đếm số chat (từ matchmaking_results)
        chat_count = db.execute("""
            SELECT COUNT(*) as count FROM matchmaking_results 
            WHERE student_user_id = ? OR therapist_user_id = ?
        """, (user_id, user_id)).fetchone()['count']

        # Đếm số quest hoàn thành
        quest_count = db.execute("""
            SELECT COUNT(*) as count FROM daily_quests 
            WHERE user_id = ? AND completed = 1
        """, (user_id,)).fetchone()['count']

        unlocked = []

        # Kiểm điều kiện từng achievement
        if check_and_unlock_achievement(user_id, 'khoi_dau'):
            unlocked.append('khoi_dau')

        if chat_count >= 5:
            if check_and_unlock_achievement(user_id, '5_chats'):
                unlocked.append('5_chats')

        if quest_count >= 10:
            if check_and_unlock_achievement(user_id, '10_quests'):
                unlocked.append('10_quests')

        return {
            'unlocked': unlocked,
            'chat_count': chat_count,
            'quest_count': quest_count
        }

    finally:
        db.close()


def get_user_achievements(user_id):
    """Lấy danh sách achievements của user"""
    db = get_db()
    try:
        achievements = db.execute("""
            SELECT achievement_id, earned_at FROM user_achievements 
            WHERE user_id = ?
            ORDER BY earned_at DESC
        """, (user_id,)).fetchall()

        result = []
        for ach in achievements:
            ach_def = ACHIEVEMENTS.get(ach['achievement_id'])
            if ach_def:
                result.append({
                    **ach_def,
                    'earned_at': ach['earned_at']
                })

        return result

    finally:
        db.close()


def get_user_streak(user_id):
    """Lấy thông tin streak của user"""
    db = get_db()
    try:
        streak = db.execute("""
            SELECT * FROM user_streaks WHERE user_id = ?
        """, (user_id,)).fetchone()

        if not streak:
            initialize_user_streak(user_id)
            streak = db.execute(
                "SELECT * FROM user_streaks WHERE user_id = ?",
                (user_id,)
            ).fetchone()

        return {
            'current_streak': streak['current_streak'],
            'longest_streak': streak['longest_streak'],
            'last_activity_date': streak['last_activity_date'],
            'percentage': min(int((streak['current_streak'] / 14) * 100), 100)  # 14 ngày = 100%
        }

    finally:
        db.close()


def get_achievements_data(user_id):
    """Lấy toàn bộ dữ liệu achievements cho dashboard"""
    achievements = get_user_achievements(user_id)
    streak = get_user_streak(user_id)

    # Tính toán tất cả achievements có sẵn
    all_badges = [ACHIEVEMENTS[key] for key in ACHIEVEMENTS.keys()]

    # Đánh dấu badges đã unlock
    unlocked_ids = {ach['id'] for ach in achievements}
    for badge in all_badges:
        badge['unlocked'] = badge['id'] in unlocked_ids

    return {
        'streak': streak,
        'achievements': achievements,
        'all_badges': all_badges
    }
