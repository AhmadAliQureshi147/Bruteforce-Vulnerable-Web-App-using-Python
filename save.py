from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for session management and flash messages


# Initialize the SQLite database with weak passwords
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')
    # Inserting weak passwords
    weak_passwords = [
        ('admin', 'admin'),
        ('user', 'password'),
        ('guest', '1234'),
        ('test', 'admin123'),
        ('root', 'root'),
        ('demo', 'demo'),
        ('admin', 'password123'),
        ('user1', '123456'),
        ('admin1', 'qwerty'),
        ('testuser', 'letmein')
    ]
    c.executemany('INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)', weak_passwords)
    conn.commit()
    conn.close()


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check the credentials against the database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            flash('Login successful!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid credentials. Try again.', 'danger')

    return render_template('login.html')


if __name__ == '__main__':
    init_db()  # Initialize the database with weak passwords
    app.run(host='0.0.0.0',port=5000,debug=True)
