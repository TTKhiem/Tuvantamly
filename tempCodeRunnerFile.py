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