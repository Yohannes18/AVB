from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify, make_response, abort
import sqlite3
import os
import shutil
import glob
import hashlib
import pickle
import subprocess
import yaml
import xml.etree.ElementTree as ET
import jwt
import base64
import json
from datetime import datetime, timedelta
from functools import wraps
import logging
import tempfile
from werkzeug.utils import secure_filename
import uuid
import secrets
import requests
from lxml import etree
import zipfile
import io
import threading
import time
import socket
import gzip
import hmac
from urllib.parse import urlparse
from jinja2 import Environment, BaseLoader
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)
app.secret_key = "super_secret_key_123"  # VULNERABILITY 1: Hardcoded secret key
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads/'
# VULNERABILITY 2: Allowing dangerous file extensions
app.config['ALLOWED_EXTENSIONS'] = {
    'png', 'jpg', 'jpeg', 'gif', 'php', 'py', 'sh', 'exe', 'jsp', 'asp', 'aspx'
}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('backup', exist_ok=True)
os.makedirs('config', exist_ok=True)
os.makedirs('flags', exist_ok=True)

# ── CTF FLAGS ──────────────────────────────────────────────────────────────
# One flag per vulnerability. Returned/shown when the vuln is successfully hit.
CTF_FLAGS = {
    # Original 47 vulns
    'hardcoded_secret':  'FLAG{H4rdC0d3d_S3cr3t_K3y_Ex90s3d}',
    'sqli_login':        'FLAG{SQLi_Auth_Byp4ss_L0g1n_V1ct0ry}',
    'sqli_register':     'FLAG{SQLi_R3g1st3r_1ns3rt_1nj3ct10n}',
    'sqli_search':       'FLAG{SQLi_UNION_S34rch_R3sults}',
    'sqli_transfer':     'FLAG{SQLi_Tr4nsf3r_B4l4nc3_M4n1p}',
    'sqli_profile':      'FLAG{SQLi_PR0F1LE_UPD4T3_BYPASS}',
    'sqli_api':          'FLAG{SQLi_AP1_3ndp01nt_Dump}',
    'xss_stored':        'FLAG{St0r3d_XSS_C0mm3nt_1nj3ct10n}',
    'cmd_injection':     'FLAG{CMD_1nj3ct10n_B4ckup_Byp4ss}',
    'rce_eval':          'FLAG{RCE_3v4l_Pyth0n_C0d3_Ex3c}',
    'ssrf_basic':        'FLAG{SSRF_B4s1c_Url_F3tch3r}',
    'xxe':               'FLAG{XXE_3xt3rn4l_3nt1ty_1nj3ct10n}',
    'pickle_rce':        'FLAG{P1ckl3_D3s3r1al1z4t10n_RCE}',
    'yaml_rce':          'FLAG{YAML_Uns4f3_L04d_RC3}',
    'lfi':               'FLAG{LF1_L0c4l_F1l3_1nclus10n}',
    'idor':              'FLAG{1D0R_1ns3cur3_D1r3ct_0bj3ct_R3f}',
    'upload_webshell':   'FLAG{Unr3str1ct3d_F1l3_Upl04d_W3bsh3ll}',
    'mass_export':       'FLAG{M4ss_D4t4_3xp0rt_N0_Auth}',
    'jwt_weak':          'FLAG{JWT_W34k_S3cr3t_S1gn4tur3}',
    'session_fixation':  'FLAG{S3ss10n_F1x4t10n_4tt4ck}',
    'reset_bypass':      'FLAG{P4ssw0rd_R3s3t_M4g1c_Byp4ss}',
    'debug_endpoint':    'FLAG{D3bug_3ndp01nt_3nv_D1scl0sur3}',
    'header_bypass':     'FLAG{X_4dm1n_H34d3r_R0l3_Byp4ss}',
    # 7 complex vulns
    'jwt_confusion':     'FLAG{JWT_4lg0r1thm_C0nfus10n_RS256_HS256}',
    'blind_sqli':        'FLAG{Bl1nd_SQLi_T1m1ng_St4ck3d_Qu3r13s}',
    'ssti':              'FLAG{SSTI_J1nj4_T3mpl4t3_RCE_0wn3d}',
    'deser_chain':       'FLAG{D3s3r_Ch41n_P1ckl3_Z1p_Y4ML}',
    'zip_slip':          'FLAG{Z1p_Sl1p_P4th_Tr4v3rs4l_0v3rwr1t3}',
    'toctou':            'FLAG{T0CT0U_R4c3_C0nd1t10n_D0ubl3_Sp3nd}',
    'ssrf_advanced':     'FLAG{SSRF_DNS_R3b1nd_Bl0ckl1st_Byp4ss}',
    'crypto_aes':        'FLAG{Crypt0_St4t1c_IV_ECB_P3ngu1n_4tt4ck}',
    'crypto_rsa':        'FLAG{Crypt0_T1ny_RSA_Pr1m3s_N0_P4dd1ng}',
    'oauth_redirect':    'FLAG{0Auth_0p3n_R3d1r3ct_JWT_L34k}',
}

from flask import has_request_context

def get_flag(key):
    """Return the dynamic flag for a given vulnerability key."""
    base_flag = CTF_FLAGS.get(key, 'FLAG{UNKNOWN}')
    
    # Prioritize session ID (if registered dynamically), fallback to ENV
    student_id = 'DEFAULT'
    if has_request_context():
        if session.get('intern_id'):
            student_id = session.get('intern_id')
        elif session.get('user_id'):
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT intern_id FROM users WHERE id = ?", (session['user_id'],))
                row = cursor.fetchone()
                if row and row['intern_id']:
                    student_id = row['intern_id']
                    session['intern_id'] = student_id
                conn.close()
            except Exception:
                pass
    if student_id == 'DEFAULT':
        student_id = os.environ.get('STUDENT_ID', 'DEFAULT')
    
    # Generate an 8-character suffix unique to this student and this vulnerability
    suffix_seed = f"{key}:{student_id}:{app.secret_key}".encode()
    suffix = hashlib.md5(suffix_seed).hexdigest()[:8]
    
    # Strip the closing '}' and append the suffix
    if base_flag.endswith('}'):
        return f"{base_flag[:-1]}_{suffix}}}"
    return f"{base_flag}_{suffix}"

@app.context_processor
def inject_student_id():
    """Inject STUDENT_ID into all templates for UI watermarking."""
    student_id = 'DEFAULT'
    if has_request_context():
        if session.get('intern_id'):
            student_id = session.get('intern_id')
        elif session.get('user_id'):
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT intern_id FROM users WHERE id = ?", (session['user_id'],))
                row = cursor.fetchone()
                if row and row['intern_id']:
                    student_id = row['intern_id']
                    session['intern_id'] = student_id
                conn.close()
            except Exception:
                pass
    if student_id == 'DEFAULT':
        student_id = os.environ.get('STUDENT_ID', 'DEFAULT')
    return dict(STUDENT_ID=student_id)

@app.route('/setup', methods=['GET', 'POST'])
def setup_intern():
    """Allow interns to inject their dynamic ID from the Flag Acceptor into the bank (Locked once set)."""
    current_id = session.get('intern_id')
    if not current_id and session.get('user_id'):
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT intern_id FROM users WHERE id = ?", (session['user_id'],))
            row = cursor.fetchone()
            if row and row['intern_id']:
                current_id = row['intern_id']
                session['intern_id'] = current_id
            conn.close()
        except Exception:
            pass
    if not current_id:
        current_id = os.environ.get('STUDENT_ID', 'DEFAULT')

    # IMMUTABLE HARD GUARD: If ID is already configured (not DEFAULT), block access completely & redirect!
    if current_id and current_id != 'DEFAULT':
        flash(f"Your Registration ID is permanently locked to {current_id} for the competition.", "info")
        if session.get('user_id'):
            return redirect('/profile')
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_intern_id = request.form.get('intern_id', '').strip().upper()
        if new_intern_id:
            session['intern_id'] = new_intern_id
            if session.get('user_id'):
                with db_write_lock:
                    conn = get_db()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("UPDATE users SET intern_id = ? WHERE id = ?", (new_intern_id, session['user_id']))
                        conn.commit()
                    except Exception:
                        pass
                    finally:
                        conn.close()
            flash(f"Registration ID permanently bound & locked to {new_intern_id}!", "success")
            if session.get('user_id'):
                return redirect('/profile')
            return redirect(url_for('login'))

    return render_template('setup.html')

# Create flag files for file-read vulns (LFI / XXE / SSRF)
def _write_flag_files():
    lfi_flag = 'flags/flag_lfi.txt'
    xxe_flag = 'flags/flag_xxe.txt'
    ssrf_flag = 'flags/flag_ssrf.txt'
    if not os.path.exists(lfi_flag):
        open(lfi_flag, 'w').write(f"LFI confirmed!\n{get_flag('lfi')}\n")
    if not os.path.exists(xxe_flag):
        open(xxe_flag, 'w').write(f"XXE confirmed!\n{get_flag('xxe')}\n")
    if not os.path.exists(ssrf_flag):
        open(ssrf_flag, 'w').write(f"SSRF confirmed!\n{get_flag('ssrf_basic')}\n")


# VULNERABILITY 3: Sensitive data in logs
logging.basicConfig(level=logging.DEBUG, filename='bank.log')
logger = logging.getLogger(__name__)

# Multiple DB paths for discovery
DB_PATHS = {
    'primary': 'bank.db',
    'backup': 'backup/bank_backup.db',
    'config': 'config/app_config.db'
}

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

db_write_lock = threading.Lock()

def get_db():
    conn = sqlite3.connect(DB_PATHS['primary'], timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA busy_timeout=30000;')
        conn.execute('PRAGMA synchronous=NORMAL;')
    except Exception:
        pass
    return conn


def init_db():
    """Initialize database with intentionally vulnerable configurations."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password TEXT NOT NULL,
            balance REAL DEFAULT 1000.0,
            role TEXT DEFAULT 'user',
            profile_photo TEXT DEFAULT 'default.png',
            api_key TEXT,
            secret_question TEXT,
            secret_answer TEXT,
            is_admin INTEGER DEFAULT 0,
            last_login TEXT,
            session_token TEXT,
            intern_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN intern_id TEXT;")
    except Exception:
        pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_account TEXT,
            to_account TEXT,
            amount REAL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT,
            status TEXT DEFAULT 'completed'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # VULNERABILITY 4: Flag stored in plain DB table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hidden_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flag TEXT UNIQUE,
            secret_info TEXT
        )
    ''')

    # New tables for complex vulnerabilities
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            token TEXT,
            refresh_token TEXT,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oauth_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state TEXT,
            redirect_uri TEXT,
            client_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            token TEXT,
            expires_at TIMESTAMP,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS encryption_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_name TEXT UNIQUE,
            key_value TEXT,
            algorithm TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # VULNERABILITY: Weak base64 key stored in DB in plaintext
    cursor.execute(
        "INSERT OR IGNORE INTO encryption_keys (key_name, key_value, algorithm) VALUES (?, ?, ?)",
        ('master_key', 'VGhpcy1pcy1hLXdlYWstZW5jcnlwdGlvbi1rZXktMjAyNA==', 'AES-256-CBC')
    )
    cursor.execute(
        "INSERT OR IGNORE INTO hidden_data (flag, secret_info) VALUES (?, ?)",
        ('jwt_confusion', 'RSA public key used as HMAC secret')
    )

    # VULNERABILITY 5: Weak MD5 password hashing
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, email, password, role, balance, is_admin, api_key) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ('admin', 'admin@bank.com', hashlib.md5('admin123'.encode()).hexdigest(), 'admin', 1000000, 1, 'ADMIN_API_KEY_12345')
    )
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, email, password, role, balance) VALUES (?, ?, ?, ?, ?)",
        ('user1', 'user1@bank.com', hashlib.md5('password123'.encode()).hexdigest(), 'user', 5000)
    )
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, email, password, role, balance) VALUES (?, ?, ?, ?, ?)",
        ('john_doe', 'john@example.com', 'plaintext_password', 'user', 2000)
    )
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, email, password, role, balance) VALUES (?, ?, ?, ?, ?)",
        ('test_user', 'test@bank.com', hashlib.sha1('test123'.encode()).hexdigest(), 'user', 3000)
    )

    cursor.execute(
        "INSERT OR IGNORE INTO hidden_data (flag, secret_info) VALUES (?, ?)",
        ('sqli_search', 'Hidden admin password: Sup3rS3cr3t@2024')
    )
    cursor.execute(
        "INSERT OR IGNORE INTO hidden_data (flag, secret_info) VALUES (?, ?)",
        ('ssti', '{{ config.__class__.__init__.__globals__ }}')
    )
    cursor.execute(
        "INSERT OR IGNORE INTO hidden_data (flag, secret_info) VALUES (?, ?)",
        ('pickle_rce', 'Gadget chain via __reduce__')
    )

    # VULNERABILITY 6: Plaintext credentials stored in logs table
    cursor.execute(
        "INSERT INTO admin_logs (admin_id, action, details, ip_address) VALUES (?, ?, ?, ?)",
        (1, 'system_init', 'Admin password: Sup3rS3cr3t@2024', '127.0.0.1')
    )

    conn.commit()
    conn.close()


def safe_init_db(retries=5):
    """Wrapper to safely run init_db with retries and process-wide lock on lock contention."""
    with db_write_lock:
        for attempt in range(retries):
            try:
                init_db()
                return
            except sqlite3.OperationalError as e:
                if ('locked' in str(e) or 'busy' in str(e)) and attempt < retries - 1:
                    time.sleep(0.2 * (attempt + 1))
                else:
                    raise


# ─────────────────────────────────────────────
# HELPER FUNCTIONS (each intentionally vulnerable)
# ─────────────────────────────────────────────

# VULNERABILITY 7: Insecure Deserialization
def load_user_preferences(user_id):
    filepath = f'user_prefs_{user_id}.pkl'
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            return pickle.load(f)  # Unsafe pickle.load
    return {}


def save_user_preferences(user_id, preferences):
    filepath = f'user_prefs_{user_id}.pkl'
    with open(filepath, 'wb') as f:
        pickle.dump(preferences, f)


# VULNERABILITY 8: Command Injection via os.system
def backup_database(filename):
    cmd = f"cp bank.db {filename}"
    os.system(cmd)  # No input sanitization


# VULNERABILITY 9: Weak JWT secret + no algorithm verification
def generate_token(username):
    payload = {
        'username': username,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow(),
        'role': 'user'
    }
    return jwt.encode(payload, 'weak_secret', algorithm='HS256')


def verify_token(token):
    try:
        # VULNERABILITY 10: signature verification disabled
        payload = jwt.decode(token, options={'verify_signature': False})
        return payload
    except Exception:
        return None


# VULNERABILITY 11: SSRF – no restriction on internal URLs
def fetch_url(url):
    try:
        response = requests.get(url, timeout=5, allow_redirects=True)
        return response.text
    except Exception as e:
        return str(e)


# VULNERABILITY 12: XXE via lxml with external entity resolution
def parse_xml_data(xml_data):
    parser = etree.XMLParser(resolve_entities=True, no_network=False, huge_tree=True)
    root = etree.fromstring(xml_data, parser=parser)
    return etree.tostring(root)


# VULNERABILITY 13: Plain-string SQL in password reset (no parameterisation)
def reset_password(username, new_password):
    with db_write_lock:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET password = '{new_password}' WHERE username = '{username}'")
        conn.commit()
        conn.close()


# ─────────────────────────────────────────────
# DECORATORS
# ─────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        conn = get_db()
        cursor = conn.cursor()
        # VULNERABILITY 14: f-string SQL injection
        cursor.execute(f"SELECT role FROM users WHERE id = {session['user_id']}")
        user = cursor.fetchone()
        conn.close()
        # VULNERABILITY 15: Role bypass via custom request header
        if user and (user['role'] == 'admin' or request.headers.get('X-Admin') == 'true'):
            return f(*args, **kwargs)
        abort(403)
    return decorated_function


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email    = request.form.get('email')
        password = request.form.get('password')

        with db_write_lock:
            conn   = get_db()
            cursor = conn.cursor()
            # VULNERABILITY 16: MD5 password hashing
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            try:
                # VULNERABILITY 17: SQL Injection in INSERT
                cursor.execute(
                    f"INSERT INTO users (username, email, password) VALUES ('{username}', '{email}', '{hashed_password}')"
                )
                conn.commit()
                user_id = cursor.lastrowid
                session['user_id']  = user_id
                session['username'] = username
                session['role']     = 'user'
                return redirect('/dashboard')
            except Exception as e:
                flash(f'Error: {str(e)}', 'error')
            finally:
                conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username')
    password = request.form.get('password')

    conn   = get_db()
    cursor = conn.cursor()
    # VULNERABILITY 18: SQL Injection in login query
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    user = cursor.fetchone()
    conn.close()

    if user:
        stored_password      = user['password']
        input_password_hash  = hashlib.md5(password.encode()).hexdigest()
        # VULNERABILITY 19: Plaintext comparison fallback
        if stored_password == input_password_hash or password == stored_password:
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['role']     = user['role']
            # VULNERABILITY 20: Session fixation (token generated but old session reused)
            session['session_token'] = secrets.token_hex(16)

            # Persist or populate intern_id across logins
            try:
                db_intern_id = user['intern_id'] if 'intern_id' in user.keys() else None
            except Exception:
                db_intern_id = None

            if db_intern_id:
                session['intern_id'] = db_intern_id
            elif session.get('intern_id'):
                with db_write_lock:
                    conn = get_db()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("UPDATE users SET intern_id = ? WHERE id = ?", (session['intern_id'], user['id']))
                        conn.commit()
                    except Exception:
                        pass
                    finally:
                        conn.close()

            return redirect('/dashboard')

    sqli_indicators = ["'", '--', 'OR ', 'UNION', '/*']
    if any(i.upper() in username.upper() for i in sqli_indicators):
        flash(f'[SQLI-LOGIN] {get_flag("sqli_login")}', 'success')
    else:
        flash('Invalid credentials', 'error')
    return redirect('/')


@app.route('/logout')
def logout():
    # VULNERABILITY 21: Session not properly invalidated server-side
    session.clear()
    return redirect('/')


@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    conn    = get_db()
    cursor  = conn.cursor()

    # VULNERABILITY 22: f-string SQL injection
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    user = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()['count']

    cursor.execute(f"SELECT * FROM comments ORDER BY created_at DESC LIMIT 20")
    comments = cursor.fetchall()

    # VULNERABILITY 23: All transactions exposed to every user
    cursor.execute("SELECT * FROM transactions ORDER BY transaction_date DESC LIMIT 10")
    transactions = cursor.fetchall()

    cursor.execute("SELECT * FROM users")
    all_users = cursor.fetchall()

    conn.close()
    return render_template('dashboard.html', user=user, user_count=user_count,
                           comments=comments, transactions=transactions, all_users=all_users)


@app.route('/transfer', methods=['POST'])
@login_required
def transfer():
    from_account = request.form.get('from_account')
    to_account   = request.form.get('to_account')
    amount       = float(request.form.get('amount', 0))

    with db_write_lock:
        conn   = get_db()
        cursor = conn.cursor()

        # VULNERABILITY 24: SQL Injection + no CSRF token
        cursor.execute(f"SELECT balance FROM users WHERE username = '{from_account}'")
        from_user = cursor.fetchone()

        if from_user and from_user['balance'] >= amount:
            # VULNERABILITY 25: Race condition – non-atomic update
            cursor.execute(f"UPDATE users SET balance = balance - {amount} WHERE username = '{from_account}'")
            cursor.execute(f"UPDATE users SET balance = balance + {amount} WHERE username = '{to_account}'")
            cursor.execute(
                f"INSERT INTO transactions (from_account, to_account, amount) VALUES ('{from_account}', '{to_account}', {amount})"
            )
            conn.commit()
            flash(f'Transfer complete! [SQLI-TRANSFER] {get_flag("sqli_transfer")}', 'success')
        else:
            flash('Insufficient funds or account not found', 'error')

        conn.close()
    return redirect('/dashboard')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']

    if request.method == 'POST':
        username = request.form.get('username')
        email    = request.form.get('email')

        with db_write_lock:
            conn   = get_db()
            cursor = conn.cursor()
            try:
                # VULNERABILITY 26: SQL Injection in profile update
                cursor.execute(f"UPDATE users SET username = '{username}', email = '{email}' WHERE id = {user_id}")
                conn.commit()
                session['username'] = username
                flash('Profile updated', 'success')
            except Exception as e:
                flash(f'Error updating profile: {str(e)}', 'error')
            finally:
                conn.close()
        return redirect('/profile')

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    user = cursor.fetchone()
    conn.close()
    return render_template('profile.html', user=user)


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect('/upload')

        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect('/upload')

        if file:
            # VULNERABILITY 27: No file-type validation → webshell upload
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            with db_write_lock:
                conn   = get_db()
                cursor = conn.cursor()
                cursor.execute(f"UPDATE users SET profile_photo = '{filename}' WHERE id = {session['user_id']}")
                conn.commit()
                conn.close()

            dangerous_exts = {'.php','.py','.sh','.exe','.jsp','.asp','.aspx'}
            ext = os.path.splitext(filename)[1].lower()
            if ext in dangerous_exts:
                flash(f'Webshell uploaded! [UPLOAD] {get_flag("upload_webshell")} -- /uploads/{filename}', 'success')
            else:
                flash(f'File uploaded to {filepath}', 'success')
            return redirect('/profile')
    return render_template('upload.html')


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # VULNERABILITY 29: Path traversal via filename parameter
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/comment', methods=['POST'])
@login_required
def comment():
    comment_text = request.form.get('comment')
    user_id  = session['user_id']
    username = session['username']

    with db_write_lock:
        conn   = get_db()
        cursor = conn.cursor()
        # VULNERABILITY 30: Stored XSS – no output encoding
        cursor.execute(
            f"INSERT INTO comments (user_id, username, comment) VALUES ({user_id}, '{username}', '{comment_text}')"
        )
        conn.commit()
        conn.close()
    xss_triggers = ['<script', 'javascript:', 'onerror=', 'onload=', 'svg/onload']
    if any(t in comment_text.lower() for t in xss_triggers):
        flash(f'[XSS] {get_flag("xss_stored")}', 'success')
    return redirect('/dashboard')


@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')

    conn   = get_db()
    cursor = conn.cursor()
    # VULNERABILITY 31: SQL Injection in search
    cursor.execute(
        f"SELECT * FROM transactions WHERE description LIKE '%{query}%' "
        f"OR from_account LIKE '%{query}%' OR to_account LIKE '%{query}%'"
    )
    results = cursor.fetchall()
    conn.close()
    return render_template('search.html', results=results, query=query)


# VULNERABILITY 32: IDOR – no authentication, user_id taken from URL
@app.route('/api/user/<int:user_id>')
def api_user(user_id):
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT id, username, email, balance, role, api_key FROM users WHERE id = {user_id}")
    user = cursor.fetchone()
    conn.close()
    if user:
        result = dict(user)
        result['flag'] = get_flag('idor')
        result['note'] = 'IDOR: no auth check on /api/user/<id>'
        return jsonify(result)
    return jsonify({'error': 'User not found'}), 404


# VULNERABILITY 33: No authentication on transfer API + SQL Injection
@app.route('/api/transfer', methods=['POST'])
def api_transfer():
    data         = request.get_json()
    from_account = data.get('from_account')
    to_account   = data.get('to_account')
    amount       = data.get('amount')

    with db_write_lock:
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET balance = balance - {amount} WHERE username = '{from_account}'")
        cursor.execute(f"UPDATE users SET balance = balance + {amount} WHERE username = '{to_account}'")
        conn.commit()
        conn.close()
    return jsonify({'status': 'success', 'flag': get_flag('sqli_api'),
                    'note': 'No auth + SQLi on unauthenticated API endpoint'})


@app.route('/admin')
@admin_required
def admin_panel():
    conn   = get_db()
    cursor = conn.cursor()
    # VULNERABILITY 34: Full data dump including secrets
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.execute("SELECT * FROM admin_logs")
    logs = cursor.fetchall()
    cursor.execute("SELECT * FROM hidden_data")
    hidden_rows = cursor.fetchall()
    conn.close()

    hidden = []
    for row in hidden_rows:
        row_dict = dict(row)
        flag_val = row_dict.get('flag', '')
        if flag_val in CTF_FLAGS:
            row_dict['flag'] = get_flag(flag_val)
        hidden.append(row_dict)

    return render_template('admin.html', users=users, logs=logs, hidden=hidden)


@app.route('/backup', methods=['GET', 'POST'])
@login_required
def backup():
    if request.method == 'POST':
        filename = request.form.get('filename', 'backup.db')
        # VULNERABILITY 35: Command injection via filename
        backup_database(filename)
        if any(c in filename for c in [';', '|', '&', '`', '$']):
            flash(f'[CMD-INJECT] {get_flag("cmd_injection")}', 'success')
        else:
            flash(f'Backup created: {filename}', 'success')
        return redirect('/dashboard')
    return render_template('backup.html')


@app.route('/import', methods=['GET', 'POST'])
@admin_required
def import_data():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file'}), 400
        file = request.files['file']
        data = file.read()
        try:
            # VULNERABILITY 36: Unsafe YAML deserialization (yaml.load with Loader)
            imported_data = yaml.load(data, Loader=yaml.Loader)
            return jsonify({'status': 'success', 'data': str(imported_data),
                            'flag': get_flag('yaml_rce')})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return render_template('import.html')


@app.route('/parse-xml', methods=['GET', 'POST'])
@login_required
def parse_xml_endpoint():
    if request.method == 'POST':
        xml_data = request.data
        try:
            # VULNERABILITY 37: XXE
            result = parse_xml_data(xml_data)
            flag_comment = f'<!-- [XXE] {get_flag("xxe")} -->'.encode()
            return flag_comment + b'\n' + result
        except Exception as e:
            return str(e), 500
    return render_template('parse_xml.html')


@app.route('/fetch', methods=['GET', 'POST'])
@login_required
def fetch():
    if request.method == 'POST':
        url = request.form.get('url')
        # VULNERABILITY 38: SSRF
        content = fetch_url(url)
        flag_banner = f'[SSRF] {get_flag("ssrf_basic")}\n\n'
        return render_template('fetch.html', content=flag_banner + content, url=url)
    return render_template('fetch.html', content=None, url=None)


@app.route('/token')
@login_required
def get_token():
    token = generate_token(session['username'])
    return jsonify({'token': token})


@app.route('/verify-token', methods=['POST'])
def verify_token_endpoint():
    token   = request.json.get('token')
    payload = verify_token(token) or {}
    if payload.get('role') == 'admin':
        payload['flag'] = get_flag('jwt_weak')
    return jsonify(payload)


@app.route('/debug')
def debug():
    # VULNERABILITY 39: Debug endpoint exposing env vars + system info
    flag = get_flag('debug_endpoint')
    return f"""
    <h1>Debug Information</h1>
    <p style='color:lime;font-family:monospace;font-size:16px;padding:10px;background:#111'>
    [DEBUG FLAG] {flag}</p>
    <pre>
Working Directory: {os.getcwd()}
Environment Variables:
{json.dumps(dict(os.environ), indent=2)}

Database Files: {json.dumps(DB_PATHS, indent=2)}
    </pre>
    """


# VULNERABILITY 40: RCE via eval()
@app.route('/execute', methods=['GET', 'POST'])
@admin_required
def execute():
    result = ''
    if request.method == 'POST':
        code = request.form.get('code', '')
        try:
            eval_out = str(eval(code))
            result = f'{eval_out}\n\n[RCE] {get_flag("rce_eval")}'
        except Exception as e:
            result = str(e)
    return render_template('execute.html', result=result)


# VULNERABILITY 41: Local File Inclusion
@app.route('/read-file')
@login_required
def read_file():
    filename = request.args.get('file', '')
    try:
        with open(filename, 'r') as f:
            content = f.read()
        lfi_flag = f'<!-- [LFI] {get_flag("lfi")} -->\n'
        return f'<pre>{lfi_flag}{content}</pre>'
    except Exception as e:
        return str(e)


# VULNERABILITY 42: Insecure deserialization via raw POST body
@app.route('/set-preference', methods=['POST'])
@login_required
def set_preference():
    data = request.get_data()
    try:
        preferences = pickle.loads(data)
        save_user_preferences(session['user_id'], preferences)
        return jsonify({'status': 'success', 'flag': get_flag('pickle_rce'),
                        'note': 'Pickle __reduce__ RCE payload executed'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get-preference')
@login_required
def get_preference():
    preferences = load_user_preferences(session['user_id'])
    return jsonify(preferences)


# VULNERABILITY 43: Password reset with no real identity verification
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password_endpoint():
    if request.method == 'POST':
        username        = request.form.get('username')
        new_password    = request.form.get('new_password')
        security_answer = request.form.get('security_answer')

        conn   = get_db()
        cursor = conn.cursor()
        # VULNERABILITY 44: SQL Injection in reset + magic bypass answer
        cursor.execute(f"SELECT secret_answer FROM users WHERE username = '{username}'")
        user = cursor.fetchone()
        conn.close()

        if user:
            if security_answer == user['secret_answer'] or security_answer == 'admin':
                reset_password(username, new_password)
                flash(f'[RESET-BYPASS] {get_flag("reset_bypass")}', 'success')
                return redirect('/')
        flash('Invalid security answer', 'error')
        return redirect('/reset-password')
    return render_template('reset_password.html')


# VULNERABILITY 45: Mass data export without proper authorisation
@app.route('/api/export-data')
@login_required
def export_data():
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.execute("SELECT * FROM transactions")
    transactions = cursor.fetchall()
    conn.close()
    return jsonify({
        'flag':         get_flag('mass_export'),
        'users':        [dict(u) for u in users],
        'transactions': [dict(t) for t in transactions]
    })


# VULNERABILITY 46: Information disclosure in 404/500 pages
@app.errorhandler(404)
def not_found(e):
    return f"404 Error: {request.url} not found. Details: {e}", 404


@app.errorhandler(500)
def internal_error(e):
    return f"500 Internal Server Error: {str(e)}", 500


# ─────────────────────────────────────────────
# COMPLEX VULNERABILITIES (V48–V54)
# ─────────────────────────────────────────────

# ── V48: JWT Algorithm Confusion (RS256 → HS256 key confusion) ──
def _ensure_rsa_keys():
    """Generate RSA keypair on first run; stored insecurely for attack surface."""
    os.makedirs('keys', exist_ok=True)
    priv_path = 'keys/private_key.pem'
    pub_path  = 'keys/public_key.pem'
    if not os.path.exists(priv_path):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)  # VULN: weak 1024-bit key
        with open(priv_path, 'wb') as f:
            f.write(private_key.private_bytes(serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption()))
        with open(pub_path, 'wb') as f:
            f.write(private_key.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))


def generate_rs256_token(user_id, username, role='user'):
    payload = {
        'user_id': user_id, 'username': username, 'role': role,
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow(), 'iss': 'vuln-bank',
    }
    with open('keys/private_key.pem', 'rb') as f:
        private_key = f.read()
    return jwt.encode(payload, private_key, algorithm='RS256')


@app.route('/api/secure-token')
@login_required
def get_secure_token():
    token = generate_rs256_token(session['user_id'], session['username'], session.get('role', 'user'))
    with open('keys/public_key.pem', 'r') as f:
        pub = f.read()
    return jsonify({'token': token, 'public_key': pub})


@app.route('/api/verify-secure-token', methods=['POST'])
def verify_secure_token():
    token = request.json.get('token', '')
    try:
        # VULNERABILITY 48b: Accepts both RS256 and HS256 -- algorithm confusion
        with open('keys/public_key.pem', 'rb') as f:
            pub = f.read()
        payload = jwt.decode(token, pub, algorithms=['RS256', 'HS256'],
                             options={'verify_aud': False})
        resp = {'valid': True, 'payload': payload}
        if payload.get('role') == 'admin':
            resp['flag'] = get_flag('jwt_confusion')
            resp['note'] = 'Admin role forged via HS256 algorithm confusion!'
        return jsonify(resp)
    except Exception as e:
        # VULNERABILITY 48c: Falls back to no-verify
        try:
            payload = jwt.decode(token, options={'verify_signature': False})
            return jsonify({'valid': True, 'payload': payload,
                            'flag': get_flag('jwt_confusion'),
                            'warning': 'Signature not verified -- none algorithm accepted'})
        except Exception:
            return jsonify({'error': str(e)}), 401


# ── V49: Blind SQLi + stacked queries ──
@app.route('/api/search-transactions', methods=['POST'])
@login_required
def search_transactions_advanced():
    data        = request.get_json() or {}
    search_term = data.get('search', '')
    sort_by     = data.get('sort', 'transaction_date')
    order       = data.get('order', 'DESC')

    with db_write_lock:
        conn   = get_db()
        cursor = conn.cursor()

        # VULNERABILITY 49a: stacked queries via executescript
        if ';' in search_term:
            try:
                cursor.executescript(search_term)
                conn.commit()
            except Exception:
                pass

        # Comprehensive Integrity Guard: If a DROP TABLE script damaged ANY core table, auto-repair immediately
        try:
            cursor.execute("SELECT 1 FROM users LIMIT 1")
            cursor.execute("SELECT 1 FROM transactions LIMIT 1")
            cursor.execute("SELECT 1 FROM comments LIMIT 1")
            cursor.execute("SELECT 1 FROM hidden_data LIMIT 1")
        except Exception:
            safe_init_db()
            cursor = conn.cursor()

    # VULNERABILITY 49b: Blind time-based SQLi (SQLite uses randomblob for timing)
    # e.g. search=' AND (SELECT CASE WHEN (1=1) THEN randomblob(50000000) ELSE 1 END)--
    query = (f"SELECT * FROM transactions "
             f"WHERE description LIKE '%{search_term}%' "
             f"OR from_account LIKE '%{search_term}%' "
             f"OR to_account LIKE '%{search_term}%' "
             f"ORDER BY {sort_by} {order}")
    try:
        cursor.execute(query)
        results = [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        results = [{'error': str(e)}]
    conn.close()
    # Flag always returned; stacked query / blind timing attack unlocks it
    return jsonify({'flag': get_flag('blind_sqli'), 'results': results})


# ── V50: Server-Side Template Injection (SSTI) ──
@app.route('/render-template', methods=['GET', 'POST'])
@login_required
def render_custom_template():
    template_content = ''
    result = ''
    if request.method == 'POST':
        template_content = request.form.get('template', '')
        # VULNERABILITY 50: SSTI — raw user input rendered by Jinja2
        # Payload: {{ ''.__class__.__mro__[1].__subclasses__() }}
        # RCE:     {{ config.__class__.__init__.__globals__['os'].popen('id').read() }}
        try:
            env = Environment(loader=BaseLoader())
            tmpl = env.from_string(template_content)
            result = tmpl.render(config=app.config, request=request, session=dict(session))
            # Flag appended to every render -- SSTI confirmed when {{ }} evaluates
            result = f'{result}\n\n[SSTI] {get_flag("ssti")}'
        except Exception as e:
            result = f'Template Error: {e}'
    return render_template('ssti.html', template_content=template_content, result=result)


# ── V51: Advanced Deserialization Chain (Pickle / ZIP slip / YAML) ──
@app.route('/advanced-import', methods=['GET', 'POST'])
@login_required
def advanced_import():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect('/advanced-import')
        file    = request.files['file']
        content = file.read()

        # VULNERABILITY 51a: Pickle RCE
        if content[:2] == b'\x80\x04' or content[:2] == b'\x80\x05':
            try:
                data = pickle.loads(content)
                flash(f'[PICKLE-RCE] {get_flag("pickle_rce")} | Output: {str(data)[:100]}', 'success')
            except Exception as e:
                flash(f'Pickle error: {e}', 'error')

        # VULNERABILITY 51b: Zip Slip -- path traversal detection with extraction sandbox
        elif content[:2] == b'PK':
            try:
                sandbox_dir = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], 'zip_sandbox'))
                os.makedirs(sandbox_dir, exist_ok=True)
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    names = zf.namelist()
                    traversal = [n for n in names if '..' in n or n.startswith('/')]
                    for name in names:
                        info = zf.getinfo(name)
                        # Size guard: max 5MB per file to prevent zip-bomb DoS
                        if info.file_size <= 5 * 1024 * 1024:
                            # Sandboxed extraction guard: prevent escaping sandbox_dir
                            target_path = os.path.abspath(os.path.join(sandbox_dir, name))
                            if not target_path.startswith(sandbox_dir):
                                safe_name = os.path.basename(name)
                                target_path = os.path.join(sandbox_dir, safe_name)
                            if not info.is_dir():
                                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                                with zf.open(name) as src, open(target_path, 'wb') as dst:
                                    dst.write(src.read())

                if traversal:
                    flash(f'[ZIP-SLIP] {get_flag("zip_slip")} | Traversal paths detected: {traversal}', 'success')
                else:
                    flash(f'[DESER-CHAIN] {get_flag("deser_chain")} | ZIP extracted {len(names)} files safely to sandbox', 'success')
            except Exception as e:
                flash(f'ZIP error: {e}', 'error')

        # VULNERABILITY 51c: Gzip decompression bomb (no size limit)
        elif content[:2] == b'\x1f\x8b':
            try:
                decompressed = gzip.decompress(content)
                flash(f'[DESER-CHAIN] {get_flag("deser_chain")} | Gzip decompressed: {len(decompressed)} bytes', 'success')
            except Exception as e:
                flash(f'Gzip error: {e}', 'error')

        # VULNERABILITY 51d: YAML unsafe load
        else:
            try:
                data = yaml.load(content, Loader=yaml.Loader)
                flash(f'[YAML-RCE] {get_flag("yaml_rce")} | {str(data)[:100]}', 'success')
            except Exception as e:
                flash(f'YAML error: {e}', 'error')

        return redirect('/advanced-import')
    return render_template('advanced_import.html')


# ── V52: TOCTOU Race Condition in Transfer ──
@app.route('/secure-transfer', methods=['GET', 'POST'])
@login_required
def secure_transfer():
    if request.method == 'POST':
        from_account = request.form.get('from_account')
        to_account   = request.form.get('to_account')
        amount       = float(request.form.get('amount', 0))

        with db_write_lock:
            conn   = get_db()
            cursor = conn.cursor()

            # VULNERABILITY 52: TOCTOU — check then sleep then act
            cursor.execute(f"SELECT balance FROM users WHERE username = '{from_account}'")
            user = cursor.fetchone()

            if user and user['balance'] >= amount:
                time.sleep(0.15)  # VULN: deliberate race window
                cursor.execute(f"UPDATE users SET balance = balance - {amount} WHERE username = '{from_account}'")
                cursor.execute(f"UPDATE users SET balance = balance + {amount} WHERE username = '{to_account}'")
                cursor.execute(
                    f"INSERT INTO transactions (from_account, to_account, amount, description) "
                    f"VALUES ('{from_account}', '{to_account}', {amount}, 'secure-transfer')"
                )
                conn.commit()
                flash(f'[TOCTOU] {get_flag("toctou")} | Transfer complete -- exploit with 10+ concurrent requests', 'success')
            else:
                flash('Insufficient funds', 'error')
            conn.close()
        return redirect('/secure-transfer')
    return render_template('secure_transfer.html')


# ── V53: Advanced SSRF with DNS rebinding bypass ──
@app.route('/fetch-url', methods=['GET', 'POST'])
@login_required
def fetch_url_advanced():
    result = None
    url = ''
    if request.method == 'POST':
        url = request.form.get('url', '')
        parsed = urlparse(url)

        # VULNERABILITY 53: Weak blocklist — bypassable with:
        # decimal IP (2130706433), hex (0x7f000001), IPv6 [::1],
        # short form 127.1, 0.0.0.0, DNS rebinding
        BLOCKED = {'169.254.169.254', 'metadata.google.internal'}
        try:
            hostname = parsed.hostname or ''
            if hostname in BLOCKED:
                return render_template('fetch_advanced.html', result={'error': 'Blocked'}, url=url)

            # TOCTOU: resolve once for check, but request uses original URL
            ip = socket.gethostbyname(hostname)
            if ip.startswith('169.254.'):
                return render_template('fetch_advanced.html', result={'error': 'Blocked'}, url=url)

            resp = requests.get(url, timeout=5, allow_redirects=True)
            result = {
                'status_code': resp.status_code,
                'headers': dict(resp.headers),
                'content': resp.text[:2000],
                'flag': get_flag('ssrf_advanced'),
                'note': 'SSRF blocklist bypassed via IP encoding / DNS rebinding'
            }
        except Exception as e:
            result = {'error': str(e)}
    return render_template('fetch_advanced.html', result=result, url=url)


# ── V54: Cryptographic Oracle (weak AES/RSA/hash) ──
@app.route('/api/encrypt', methods=['POST'])
@login_required
def encrypt_data():
    data      = request.get_json() or {}
    plaintext = data.get('data', '').encode()
    algorithm = data.get('algorithm', 'AES')
    mode_name = data.get('mode', 'CBC')

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key_value FROM encryption_keys WHERE key_name = 'master_key'")
    row = cursor.fetchone()
    conn.close()
    raw_key = base64.b64decode(row['key_value'])  # 32 bytes but weak derivation

    if algorithm == 'AES':
        # VULNERABILITY 54a: Static IV — never changes
        iv = b'1234567890123456'
        padded = plaintext + b'\x00' * (16 - len(plaintext) % 16)

        if mode_name == 'ECB':
            # VULNERABILITY 54b: ECB mode reveals patterns
            cipher = Cipher(algorithms.AES(raw_key), modes.ECB(), backend=default_backend())
        else:
            cipher = Cipher(algorithms.AES(raw_key), modes.CBC(iv), backend=default_backend())

        enc = cipher.encryptor()
        ct  = enc.update(padded) + enc.finalize()
        flag_key = 'crypto_aes'
        return jsonify({'ciphertext': base64.b64encode(ct).decode(),
                        'iv': base64.b64encode(iv).decode() if mode_name != 'ECB' else None,
                        'mode': mode_name,
                        'flag': get_flag(flag_key),
                        'vuln': 'Static IV reuse -- CBC-IV attack / ECB penguin pattern leak'})

    elif algorithm == 'RSA':
        # VULNERABILITY 54c: Tiny textbook RSA — no padding, small primes
        p, q, e = 61, 53, 3
        n   = p * q
        phi = (p - 1) * (q - 1)
        d   = pow(e, -1, phi)
        m   = int.from_bytes(plaintext[:2], 'big') if len(plaintext) >= 2 else int.from_bytes(plaintext, 'big')
        ct  = pow(m % n, e, n)
        return jsonify({'ciphertext': ct, 'n': n, 'e': e,
                        'private_d': d,
                        'flag': get_flag('crypto_rsa'),
                        'vuln': 'Weak RSA: p=61,q=53 -- factored instantly; private key leaked'})

    elif algorithm == 'HASH':
        ht = data.get('hash_type', 'md5')
        if ht == 'md5':
            return jsonify({'hash': hashlib.md5(plaintext).hexdigest(), 'vuln': 'MD5 is broken'})
        elif ht == 'sha1':
            return jsonify({'hash': hashlib.sha1(plaintext).hexdigest(), 'vuln': 'SHA1 is broken'})
        else:
            return jsonify({'hash': plaintext.decode(), 'vuln': 'Plaintext — no hashing at all'})

    return jsonify({'error': 'Unsupported algorithm'}), 400


@app.route('/crypto')
@login_required
def crypto_lab():
    return render_template('crypto.html')


# ── Bonus V55: OAuth callback with open redirect + token leakage ──
@app.route('/api/oauth/callback')
def oauth_callback():
    # VULNERABILITY 55: state not validated, redirect_uri not allowlisted
    redirect_uri = request.args.get('redirect_uri', '/dashboard')
    # VULNERABILITY 55b: admin JWT leaked in URL redirect
    token = generate_rs256_token(1, 'admin', 'admin')
    # If the user successfully injects an external URL (open redirect), they get the flag
    if redirect_uri.startswith('http://') or redirect_uri.startswith('https://'):
        flash(f'[OAUTH-REDIRECT] {get_flag("oauth_redirect")} | Token leaked to: {redirect_uri}', 'success')
    return redirect(f"{redirect_uri}?token={token}")


def start_periodic_reseed_worker(interval_seconds=900):
    """Background worker thread to periodically check & repair DB schema every 15 minutes."""
    def _reseed_loop():
        while True:
            time.sleep(interval_seconds)
            try:
                with app.app_context():
                    safe_init_db()
                    logger.info("[RESEED] Periodic database schema integrity check complete.")
            except Exception as e:
                logger.error(f"[RESEED ERROR] Failed periodic database repair: {e}")

    thread = threading.Thread(target=_reseed_loop, daemon=True)
    thread.start()


def log_startup_db_audit():
    """Logs startup DB path and critical table row counts to stdout for visibility."""
    db_path = os.path.abspath('bank.db')
    print("=" * 60, flush=True)
    print(f"[STARTUP DB PERSISTENCE AUDIT - VULNBANK]", flush=True)
    print(f"Database Path: {db_path}", flush=True)
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            tables = ['users', 'transactions', 'hidden_data']
            for t in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {t}")
                    count = cursor.fetchone()[0]
                    print(f"  - Table '{t}': {count} rows", flush=True)
                except sqlite3.OperationalError:
                    print(f"  - Table '{t}': [Missing/Error]", flush=True)
            conn.close()
        except Exception as e:
            print(f"  - Error reading DB: {e}", flush=True)
    else:
        print("  - WARNING: bank.db does not exist yet!", flush=True)
    print("=" * 60, flush=True)


def create_db_backup(db_name, prefix):
    """Creates a timestamped snapshot backup of db_name and retains the last 10 backups."""
    if not os.path.exists(db_name):
        return
    os.makedirs('backups', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join('backups', f"{prefix}_{timestamp}.db")
    try:
        shutil.copy2(db_name, backup_path)
        print(f"[BACKUP WORKER] Snapshot created: {backup_path}", flush=True)
        existing_backups = sorted(glob.glob(f"backups/{prefix}_*.db"))
        if len(existing_backups) > 10:
            for old_b in existing_backups[:-10]:
                os.remove(old_b)
                print(f"[BACKUP WORKER] Pruned old backup: {old_b}", flush=True)
    except Exception as e:
        print(f"[BACKUP WORKER] Backup failed for {db_name}: {e}", flush=True)


def backup_all_vulnbank_databases():
    """Runs snapshot backups for all database files used by vulnbank."""
    targets = [
        ('bank.db', 'bank'),
        ('backup/bank_backup.db', 'bank_backup'),
        ('config/app_config.db', 'app_config')
    ]
    for db_path, prefix in targets:
        create_db_backup(db_path, prefix)


def start_periodic_backup_worker(interval_seconds=900):
    """Background worker thread to periodically snapshot all databases every 15 minutes."""
    def _backup_loop():
        backup_all_vulnbank_databases()
        while True:
            time.sleep(interval_seconds)
            backup_all_vulnbank_databases()

    thread = threading.Thread(target=_backup_loop, daemon=True)
    thread.start()


# ─────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────

if __name__ == '__main__':
    safe_init_db()
    
    # Guard against Werkzeug reloader double-init in debug mode
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        log_startup_db_audit()
        _ensure_rsa_keys()
        _write_flag_files()
        start_periodic_reseed_worker(interval_seconds=900)
        start_periodic_backup_worker(interval_seconds=900)

    # VULNERABILITY 47: debug=True in production + binding to 0.0.0.0
    app.run(debug=True, host='0.0.0.0', port=5000)
