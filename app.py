from flask import Flask, request, render_template, redirect, session, flash, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "weak_secret_key_12345"
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect('bank.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT,
            balance REAL DEFAULT 1000.0,
            role TEXT DEFAULT 'user',
            profile_photo TEXT DEFAULT 'default.png'
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute("INSERT OR IGNORE INTO users (username, email, password, balance, role) VALUES (?, ?, ?, ?, ?)",
                 ("admin", "admin@bank.com", "admin123", 999999.0, "admin"))
    conn.execute("INSERT OR IGNORE INTO users (username, email, password, balance, role) VALUES (?, ?, ?, ?, ?)",
                 ("user1", "user1@bank.com", "password123", 500.0, "user"))
    
    conn.commit()
    conn.close()
    print("[+] Database initialized")

init_db()

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                        (username, email, password))
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect('/')
        except sqlite3.IntegrityError:
            flash("Username or Email already exists!", "danger")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    
    # Vulnerable SQL Injection
    query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'"
    
    conn = get_db()
    try:
        user = conn.execute(query).fetchone()
    except:
        user = None
    finally:
        conn.close()
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        flash("Login successful!", "success")
        return redirect('/dashboard')
    
    flash("Invalid credentials!", "danger")
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    all_users = conn.execute("SELECT * FROM users").fetchall()
    
    # PRIVATE COMMENTS - only show current user's comments
    comments = conn.execute("SELECT * FROM comments WHERE user_id = ? ORDER BY id DESC", 
                           (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('dashboard.html', user=user, all_users=all_users, comments=comments)

@app.route('/transfer', methods=['POST'])
def transfer():
    if 'user_id' not in session:
        return redirect('/')
    
    from_id = int(request.form.get('from_account', session['user_id']))
    to_id = int(request.form.get('to_account', 0))
    amount = float(request.form.get('amount', 0))
    
    conn = get_db()
    conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, from_id))
    conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, to_id))
    conn.commit()
    conn.close()
    
    flash(f"Successfully transferred ${amount}!", "success")
    return redirect('/dashboard')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect('/')
    
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        new_name = request.form.get('username')
        
        if new_name and new_name != user['username']:
            try:
                conn.execute("UPDATE users SET username = ? WHERE id = ?", (new_name, session['user_id']))
                session['username'] = new_name
                flash("Username updated successfully!", "success")
            except sqlite3.IntegrityError:
                flash("This username is already taken!", "danger")
        
        current_pass = request.form.get('current_password')
        new_pass = request.form.get('new_password')
        confirm_pass = request.form.get('confirm_password')
        
        if current_pass and new_pass and confirm_pass:
            if user['password'] == current_pass:
                if new_pass == confirm_pass:
                    conn.execute("UPDATE users SET password = ? WHERE id = ?", (new_pass, session['user_id']))
                    flash("Password updated successfully!", "success")
                else:
                    flash("New passwords do not match!", "danger")
            else:
                flash("Current password is incorrect!", "danger")
        
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                conn.execute("UPDATE users SET profile_photo = ? WHERE id = ?", (filename, session['user_id']))
                flash("Profile photo updated!", "success")
        
        conn.commit()
    
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/comment', methods=['POST'])
def comment():
    if 'user_id' not in session:
        return redirect('/')
    
    comment_text = request.form.get('comment', '')
    
    conn = get_db()
    conn.execute("INSERT INTO comments (user_id, username, comment) VALUES (?, ?, ?)",
                 (session['user_id'], session['username'], comment_text))
    conn.commit()
    conn.close()
    
    flash("Comment posted successfully!", "success")
    return redirect('/dashboard')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    try:
        result = os.popen(f"echo {query}").read()
    except:
        result = "Error"
    return render_template('search.html', result=result, query=query)

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect('/')

if __name__ == '__main__':
    print("🚀 Advanced VulnBank running on http://0.0.0.0:5000")
    print("Accounts: admin/admin123 | user1/password123")
    app.run(host='0.0.0.0', debug=True, port=5000)
