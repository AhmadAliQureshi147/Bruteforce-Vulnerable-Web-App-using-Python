from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import time
import bcrypt

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for session management and flash messages

LOCKOUT_THRESHOLD = 3  # Number of allowed failed attempts
LOCKOUT_DURATION = 600  # Lockout duration in seconds (10 minutes

# Initialize the SQLite database with hashed passwords
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            failed_attempts INTEGER DEFAULT 0,
            lockout_time INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS login_attempts (
            ip_address TEXT PRIMARY KEY,
            failed_attempts INTEGER DEFAULT 0,
            lockout_time INTEGER DEFAULT 0
        )
    ''')
    # Inserting hashed passwords
    weak_passwords = [
        ('admin', bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt())),
        ('user', bcrypt.hashpw('password'.encode('utf-8'), bcrypt.gensalt())),
        ('guest', bcrypt.hashpw('1234'.encode('utf-8'), bcrypt.gensalt())),
        ('test', bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())),
        ('root', bcrypt.hashpw('root'.encode('utf-8'), bcrypt.gensalt())),
        ('demo', bcrypt.hashpw('demo'.encode('utf-8'), bcrypt.gensalt())),
        ('admin', bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt())),
        ('user1', bcrypt.hashpw('123456'.encode('utf-8'), bcrypt.gensalt())),
        ('admin1', bcrypt.hashpw('qwerty'.encode('utf-8'), bcrypt.gensalt())),
        ('testuser', bcrypt.hashpw('letmein'.encode('utf-8'), bcrypt.gensalt()))
    ]
    c.executemany('INSERT OR IGNORE INTO users (username, password, failed_attempts, lockout_time) VALUES (?, ?, ?, ?)',
                  [(u, p, 0, 0) for u, p in weak_passwords])
    conn.commit()
    conn.close()


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        ip_address = request.remote_addr

        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        current_time = int(time.time())

        # Check login attempts for the IP address
        c.execute('SELECT failed_attempts, lockout_time FROM login_attempts WHERE ip_address = ?', (ip_address,))
        attempt = c.fetchone()

        if attempt:
            failed_attempts, lockout_time = attempt

            if failed_attempts >= LOCKOUT_THRESHOLD and current_time - lockout_time < LOCKOUT_DURATION:
                flash('Too many failed login attempts. Try again later.', 'danger')
                print(f'Login portal locked for IP {ip_address}. Time left: {LOCKOUT_DURATION - (current_time - lockout_time)} seconds.')
                conn.close()
                return render_template('login.html')
            elif current_time - lockout_time >= LOCKOUT_DURATION:
                # Reset failed attempts after lockout duration has passed
                failed_attempts = 0
                lockout_time = 0

        # Check if the username exists in the users table
        c.execute('SELECT password, failed_attempts, lockout_time FROM users WHERE username = ?', (username,))
        user = c.fetchone()

        if user:
            db_password, user_failed_attempts, user_lockout_time = user

            if user_failed_attempts >= LOCKOUT_THRESHOLD and current_time - user_lockout_time < LOCKOUT_DURATION:
                flash('Account locked due to too many failed login attempts. Try again later.', 'danger')
                print(f'Account for {username} is locked. Failed attempts: {user_failed_attempts}. Time left: {LOCKOUT_DURATION - (current_time - user_lockout_time)} seconds. IP: {ip_address}')
            elif bcrypt.checkpw(password.encode('utf-8'), db_password):
                c.execute('UPDATE users SET failed_attempts = 0, lockout_time = 0 WHERE username = ?', (username,))
                conn.commit()
                c.execute('DELETE FROM login_attempts WHERE ip_address = ?', (ip_address,))
                conn.commit()
                flash('Login successful!', 'success')
                print(f'User {username} logged in successfully. IP: {ip_address}')
                conn.close()
                return redirect(url_for('login'))
            else:
                user_failed_attempts += 1
                user_lockout_time = current_time if user_failed_attempts >= LOCKOUT_THRESHOLD else user_lockout_time
                c.execute('UPDATE users SET failed_attempts = ?, lockout_time = ? WHERE username = ?',
                          (user_failed_attempts, user_lockout_time, username))
                conn.commit()
                flash('Invalid credentials. Try again.', 'danger')
                print(f'Invalid login attempt for user {username}. Failed attempts: {user_failed_attempts}. IP: {ip_address}')
        else:
            # Handle non-existent users
            if not attempt:
                c.execute('INSERT INTO login_attempts (ip_address, failed_attempts, lockout_time) VALUES (?, ?, ?)',
                          (ip_address, 1, current_time))
                conn.commit()
                flash('Invalid credentials. Try again.', 'danger')
                print(f'First invalid login attempt for non-existent user {username}. IP: {ip_address}')
            else:
                failed_attempts += 1
                lockout_time = current_time if failed_attempts >= LOCKOUT_THRESHOLD else lockout_time
                c.execute('UPDATE login_attempts SET failed_attempts = ?, lockout_time = ? WHERE ip_address = ?',
                          (failed_attempts, lockout_time, ip_address))
                conn.commit()
                flash('Invalid credentials. Try again.', 'danger')
                print(f'Invalid login attempt for non-existent user {username}. Failed attempts: {failed_attempts}. IP: {ip_address}')

        conn.close()

    return render_template('save.html')


if __name__ == '__main__':
    init_db()  # Initialize the database with hashed passwords
    app.run(host='0.0.0.0', port=5000, debug=True)
