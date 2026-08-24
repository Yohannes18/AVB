import random
import string
import os
import sqlite3
import hashlib
import shutil
import glob
import threading
import time
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "acceptor_super_secret_key"
ADMIN_PASSWORD = "super_secret_admin_password_123"

# Must match the vulnerable app exactly to generate identical hashes
APP_SECRET_KEY = b"super_secret_key_123"

CTF_FLAGS = {
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

FLAG_CATEGORIES = [
    {
        'id': 'sqli',
        'title': '💉 SQL Injection (SQLi)',
        'icon': '💉',
        'description': 'Exploit database query flaws across authentication, registration, search, balance manipulation, profile updates, and API endpoints.',
        'flags': [
            {'key': 'sqli_login', 'title': 'SQLi #1: Auth Bypass on Login Form', 'hint': 'Bypass the authentication check on the login form without knowing the password.'},
            {'key': 'sqli_register', 'title': 'SQLi #2: User Registration Insert Injection', 'hint': 'Inject malicious SQL statements into user registration fields.'},
            {'key': 'sqli_search', 'title': 'SQLi #3: UNION Search Query Data Extraction', 'hint': 'Use UNION SELECT payloads in search inputs to extract hidden database rows.'},
            {'key': 'sqli_transfer', 'title': 'SQLi #4: Transfer Balance Manipulation', 'hint': 'Manipulate SQL queries during fund transfers to alter account balances.'},
            {'key': 'sqli_profile', 'title': 'SQLi #5: Profile Update Parameter Injection', 'hint': 'Exploit unsanitized inputs inside profile update endpoints.'},
            {'key': 'sqli_api', 'title': 'SQLi #6: API Endpoint Database Dump', 'hint': 'Extract full database tables through vulnerable REST API parameters.'},
            {'key': 'blind_sqli', 'title': 'SQLi #7: Blind Time-Based & Stacked Queries', 'hint': 'Infer sensitive data or trigger stacked queries using time delays.'},
        ]
    },
    {
        'id': 'rce',
        'title': '⚡ Code Execution, SSTI & Deserialization',
        'icon': '⚡',
        'description': 'Gain remote code execution (RCE) via OS command injection, Python code execution, template injection, and insecure object deserialization.',
        'flags': [
            {'key': 'cmd_injection', 'title': 'RCE #1: Backup System OS Command Injection', 'hint': 'Inject arbitrary shell commands into system backup processes.'},
            {'key': 'rce_eval', 'title': 'RCE #2: Python eval() Dynamic Code Execution', 'hint': 'Execute arbitrary Python code using insecure eval() input handling.'},
            {'key': 'ssti', 'title': 'RCE #3: Jinja2 Server-Side Template Injection', 'hint': 'Exploit Jinja2 template rendering to read environment variables and execute code.'},
            {'key': 'pickle_rce', 'title': 'RCE #4: Python Pickle Deserialization RCE', 'hint': 'Craft malicious Python pickle payloads to trigger arbitrary system execution.'},
            {'key': 'yaml_rce', 'title': 'RCE #5: Unsafe PyYAML Deserialization RCE', 'hint': 'Leverage unsafe PyYAML load functions to execute code on import.'},
            {'key': 'deser_chain', 'title': 'RCE #6: Advanced Deserialization Gadget Chain', 'hint': 'Chain multiple deserialization flaws (Pickle/Zip/YAML) for full server takeover.'},
        ]
    },
    {
        'id': 'auth',
        'title': '🔐 Auth, Session, XSS & Access Control',
        'icon': '🔐',
        'description': 'Bypass authorization barriers, exploit IDOR, manipulate sessions, perform stored XSS, and expose internal secrets.',
        'flags': [
            {'key': 'hardcoded_secret', 'title': 'Auth #1: Hardcoded Secret Key Exposure', 'hint': 'Locate static secret keys exposed in source code or client bundles.'},
            {'key': 'xss_stored', 'title': 'Auth #2: Stored Cross-Site Scripting (XSS)', 'hint': 'Inject persistent HTML/JavaScript payloads in public comment sections.'},
            {'key': 'idor', 'title': 'Auth #3: Insecure Direct Object Reference (IDOR)', 'hint': 'Access unauthorized private user records by altering object IDs.'},
            {'key': 'session_fixation', 'title': 'Auth #4: Session Fixation Attack', 'hint': 'Force a victim account to reuse an attacker-controlled session ID.'},
            {'key': 'reset_bypass', 'title': 'Auth #5: Password Reset Logic & Magic Token Bypass', 'hint': 'Exploit flaws in token generation or verification to reset arbitrary passwords.'},
            {'key': 'header_bypass', 'title': 'Auth #6: HTTP Custom Header Role Bypass (X-Admin-Role)', 'hint': 'Gain administrative access by injecting custom HTTP role headers.'},
            {'key': 'mass_export', 'title': 'Auth #7: Unauthenticated Mass Data Export', 'hint': 'Download complete database exports from unprotected API endpoints.'},
            {'key': 'debug_endpoint', 'title': 'Auth #8: Environment Secret Disclosure via Debug Endpoint', 'hint': 'Inspect leftover developer debug endpoints exposing environment variables.'},
        ]
    },
    {
        'id': 'jwt',
        'title': '🔑 JWT & OAuth Vulnerabilities',
        'icon': '🔑',
        'description': 'Forge JSON Web Tokens, perform algorithm switching attacks, and steal OAuth authorization tokens.',
        'flags': [
            {'key': 'jwt_weak', 'title': 'JWT #1: Weak HMAC Secret Key Signature Forgery', 'hint': 'Crack weak secret keys to forge valid signed JWT tokens.'},
            {'key': 'jwt_confusion', 'title': 'JWT #2: Algorithm Confusion (RS256 -> HS256)', 'hint': 'Bypass signature verification by forcing RS256 public key verification as HS256.'},
            {'key': 'oauth_redirect', 'title': 'OAuth #1: Open Redirect Token Leakage', 'hint': 'Intercept OAuth tokens by redirecting authentication flow to an external domain.'},
        ]
    },
    {
        'id': 'files',
        'title': '📁 File System & File Upload Vulnerabilities',
        'icon': '📁',
        'description': 'Read arbitrary system files, bypass file upload restrictions, and exploit path traversal vulnerabilities.',
        'flags': [
            {'key': 'lfi', 'title': 'File #1: Local File Inclusion (LFI)', 'hint': 'Traverse system directory trees to read confidential system files.'},
            {'key': 'xxe', 'title': 'File #2: XML External Entity Injection (XXE)', 'hint': 'Exploit XML document parsers to read internal system files.'},
            {'key': 'upload_webshell', 'title': 'File #3: Unrestricted File Upload Webshell', 'hint': 'Bypass file extension filters to upload executable web shells.'},
            {'key': 'zip_slip', 'title': 'File #4: Zip Slip Path Traversal Archive Overwrite', 'hint': 'Extract zip archives containing directory traversal paths to overwrite files.'},
        ]
    },
    {
        'id': 'ssrf',
        'title': '🌐 Server-Side Request Forgery (SSRF)',
        'icon': '🌐',
        'description': 'Abuse server-side network fetchers to reach internal network infrastructure.',
        'flags': [
            {'key': 'ssrf_basic', 'title': 'SSRF #1: Basic Internal URL Fetcher', 'hint': 'Force the web server to send requests to local internal services.'},
            {'key': 'ssrf_advanced', 'title': 'SSRF #2: Advanced DNS Rebinding & Blocklist Bypass', 'hint': 'Bypass IP restriction blocklists using DNS rebinding or alternate representations.'},
        ]
    },
    {
        'id': 'crypto',
        'title': '⚙️ Cryptography & Race Conditions',
        'icon': '⚙️',
        'description': 'Exploit race conditions, static AES initial vectors, and weak RSA prime factors.',
        'flags': [
            {'key': 'toctou', 'title': 'Crypto/Logic #1: TOCTOU Double-Spend Race Condition', 'hint': 'Send parallel concurrent requests to withdraw funds twice before state updates.'},
            {'key': 'crypto_aes', 'title': 'Crypto #2: Static IV / ECB Mode AES Encryption Attack', 'hint': 'Exploit deterministic AES ECB block patterns to decrypt encrypted messages.'},
            {'key': 'crypto_rsa', 'title': 'Crypto #3: Small RSA Prime Factorization & Missing Padding', 'hint': 'Factor small RSA modulus N to derive private keys without OAEP padding.'},
        ]
    }
]

from werkzeug.security import generate_password_hash, check_password_hash

def generate_student_flag(key, student_id):
    base_flag = CTF_FLAGS[key]
    suffix_seed = f"{key}:{student_id}:{APP_SECRET_KEY.decode()}".encode()
    suffix = hashlib.md5(suffix_seed).hexdigest()[:8]
    if base_flag.endswith('}'):
        return f"{base_flag[:-1]}_{suffix}}}"
    return f"{base_flag}_{suffix}"

def init_db():
    conn = sqlite3.connect('scoreboard.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id TEXT,
            vuln_key TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(intern_id, vuln_key)
        )
    ''')
    
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='interns'")
    row = cursor.fetchone()
    
    if not row:
        cursor.execute('''
            CREATE TABLE interns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier TEXT UNIQUE,
                password_hash TEXT,
                intern_id TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        sql = row[0]
        # Rebuild table if identifier lacks UNIQUE constraint at DB level
        if 'identifier TEXT UNIQUE' not in sql and 'UNIQUE(identifier)' not in sql and 'UNIQUE (identifier)' not in sql:
            cursor.execute("ALTER TABLE interns RENAME TO interns_old")
            cursor.execute('''
                CREATE TABLE interns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT UNIQUE,
                    password_hash TEXT,
                    intern_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute("PRAGMA table_info(interns_old)")
            old_cols = [c[1] for c in cursor.fetchall()]
            
            if 'identifier' in old_cols:
                cursor.execute('''
                    INSERT OR IGNORE INTO interns (id, identifier, password_hash, intern_id, created_at)
                    SELECT id, identifier, password_hash, intern_id, created_at FROM interns_old
                ''')
            else:
                cursor.execute('''
                    INSERT OR IGNORE INTO interns (id, intern_id)
                    SELECT id, intern_id FROM interns_old
                ''')
            cursor.execute("DROP TABLE interns_old")

    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('scoreboard.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'intern_id' not in session and 'admin' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin') or session.get('intern_id'):
            flash("Admin access required.", "error")
            if session.get('intern_id'):
                return redirect(url_for('dashboard'))
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        
        # --- STEP 1: Check Identifier / Sign In / Register ---
        if action in ['check', 'register']:
            identifier = request.form.get('identifier', '').strip().lower()
            password = request.form.get('password', '').strip()
            
            if not identifier:
                flash("Email or Student ID is required.", "error")
                return render_template('acceptor_index.html', step='step1')
                
            # Admin Login Check
            if identifier in ['admin', 'administrator']:
                if password == ADMIN_PASSWORD:
                    session.clear()
                    session['admin'] = True
                    return redirect(url_for('admin_leaderboard'))
                else:
                    flash("Invalid admin password.", "error")
                    return render_template('acceptor_index.html', step='step1', identifier=identifier)

            if not password:
                flash("Password is required.", "error")
                return render_template('acceptor_index.html', step='step1', identifier=identifier)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT intern_id, password_hash FROM interns WHERE identifier = ?", (identifier,))
            user = cursor.fetchone()
            conn.close()

            if user:
                # Existing account -> Verify password
                if check_password_hash(user['password_hash'], password):
                    existing_id = user['intern_id']
                    session.clear()
                    session['intern_id'] = existing_id
                    flash(f"Welcome back! Your persistent Session ID is {existing_id}", "success")
                    return render_template('acceptor_index.html', step='logged_in', new_id=existing_id, identifier=identifier)
                else:
                    flash("Invalid credentials.", "error")
                    return render_template('acceptor_index.html', step='step1', identifier=identifier)
            else:
                if action == 'register':
                    random_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                    new_id = f"INT-{random_id}"
                    pwd_hash = generate_password_hash(password)

                    conn = get_db()
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO interns (identifier, password_hash, intern_id) VALUES (?, ?, ?)",
                            (identifier, pwd_hash, new_id)
                        )
                        conn.commit()
                        conn.close()
                    except sqlite3.IntegrityError:
                        conn.close()
                        flash("An account with this Email/Student ID already exists. Please sign in.", "error")
                        return render_template('acceptor_index.html', step='step1', identifier=identifier)

                    session.clear()
                    session['intern_id'] = new_id
                    flash(f"Registration successful! Your persistent Session ID is {new_id}", "success")
                    return render_template('acceptor_index.html', step='logged_in', new_id=new_id, identifier=identifier)
                else:
                    # Unknown identifier -> Transition cleanly to Step 2 (Create Account)
                    flash("No account found for this ID. Set a password below to generate your persistent Session ID.", "info")
                    return render_template('acceptor_index.html', step='step2', identifier=identifier, initial_password=password)

        # --- STEP 2: Create Account & Generate Session ID ---
        elif action == 'create':
            identifier = request.form.get('identifier', '').strip().lower()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()

            if not identifier or not password:
                flash("Identifier and password are required.", "error")
                return render_template('acceptor_index.html', step='step2', identifier=identifier)

            if identifier in ['admin', 'administrator']:
                flash("This identifier is reserved. Please use your email or student ID instead.", "error")
                return render_template('acceptor_index.html', step='step2', identifier=identifier)

            if password != confirm_password:
                flash("Passwords do not match. Please try again.", "error")
                return render_template('acceptor_index.html', step='step2', identifier=identifier)

            if len(password) < 4:
                flash("Password must be at least 4 characters.", "error")
                return render_template('acceptor_index.html', step='step2', identifier=identifier)

            # Generate random 5-char alphanumeric intern ID
            random_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            new_id = f"INT-{random_id}"
            pwd_hash = generate_password_hash(password)

            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO interns (identifier, password_hash, intern_id) VALUES (?, ?, ?)",
                    (identifier, pwd_hash, new_id)
                )
                conn.commit()
                conn.close()
            except sqlite3.IntegrityError:
                # Race condition: identifier was created mid-flight
                conn.close()
                flash("An account with this Email/Student ID already exists. Please sign in.", "error")
                return render_template('acceptor_index.html', step='step1', identifier=identifier)

            session.clear()
            session['intern_id'] = new_id
            flash(f"Registration successful! Account created successfully! Your persistent Session ID is {new_id}", "success")
            return render_template('acceptor_index.html', step='logged_in', new_id=new_id, identifier=identifier)

    # Check if already logged in via session
    if session.get('intern_id'):
        return render_template('acceptor_index.html', step='logged_in', new_id=session.get('intern_id'))

    return render_template('acceptor_index.html', step='step1')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if session.get('admin') and not session.get('intern_id'):
        return redirect(url_for('admin_leaderboard'))
        
    intern_id = session['intern_id']
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        submitted_flag = request.form.get('flag', '').strip()
        
        # Check against all possible flags for this intern
        found_vuln_key = None
        found_title = None
        for key in CTF_FLAGS.keys():
            expected_flag = generate_student_flag(key, intern_id)
            if submitted_flag == expected_flag:
                found_vuln_key = key
                break
                
        if found_vuln_key:
            # Resolve human readable title from FLAG_CATEGORIES
            for cat in FLAG_CATEGORIES:
                for f in cat['flags']:
                    if f['key'] == found_vuln_key:
                        found_title = f['title']
                        break
            if not found_title:
                found_title = found_vuln_key

            try:
                cursor.execute(
                    "INSERT INTO submissions (intern_id, vuln_key) VALUES (?, ?)", 
                    (intern_id, found_vuln_key)
                )
                conn.commit()
                flash(f"🎉 Correct! You solved: {found_title}!", "success")
            except sqlite3.IntegrityError:
                flash(f"⚠️ You already submitted the [{found_title}] flag!", "warning")
        else:
            flash("❌ Incorrect or malformed flag.", "error")

    # Get current progress
    cursor.execute("SELECT vuln_key, submitted_at FROM submissions WHERE intern_id = ? ORDER BY submitted_at DESC", (intern_id,))
    submissions_raw = cursor.fetchall()
    conn.close()
    
    solved_map = {row['vuln_key']: row['submitted_at'] for row in submissions_raw}
    submissions = [dict(row) for row in submissions_raw]

    # Build category breakdown
    categories_data = []
    for cat in FLAG_CATEGORIES:
        cat_solved = 0
        flags_list = []
        for f in cat['flags']:
            is_solved = f['key'] in solved_map
            if is_solved:
                cat_solved += 1
            flags_list.append({
                'key': f['key'],
                'title': f['title'],
                'hint': f['hint'],
                'is_solved': is_solved,
                'submitted_at': solved_map.get(f['key'])
            })
        categories_data.append({
            'id': cat['id'],
            'title': cat['title'],
            'icon': cat['icon'],
            'description': cat['description'],
            'solved_count': cat_solved,
            'total_count': len(cat['flags']),
            'flags': flags_list
        })
    
    total_vulns = len(CTF_FLAGS)
    progress = len(solved_map)
    
    return render_template('acceptor_dashboard.html', 
                           intern_id=intern_id, 
                           submissions=submissions, 
                           progress=progress, 
                           total_vulns=total_vulns,
                           categories=categories_data)

@app.route('/leaderboard')
def public_leaderboard():
    if session.get('admin'):
        return redirect(url_for('admin_leaderboard'))
    flash("The leaderboard is restricted to administrators.", "warning")
    return redirect(url_for('dashboard'))

@app.route('/admin/leaderboard')
@admin_required
def admin_leaderboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            i.intern_id, 
            i.identifier, 
            i.created_at,
            COUNT(s.id) as score, 
            MAX(s.submitted_at) as last_submission
        FROM interns i
        LEFT JOIN submissions s ON i.intern_id = s.intern_id
        GROUP BY i.intern_id, i.identifier, i.created_at
        ORDER BY score DESC, last_submission ASC, i.created_at DESC
    ''')
    raw_rankings = cursor.fetchall()
    
    rankings = []
    total_flags = len(CTF_FLAGS)
    for row in raw_rankings:
        r = dict(row)
        cursor.execute('''
            SELECT vuln_key, submitted_at 
            FROM submissions 
            WHERE intern_id = ? 
            ORDER BY submitted_at DESC
        ''', (r['intern_id'],))
        r['solved_flags'] = [dict(sub) for sub in cursor.fetchall()]
        r['progress_percent'] = round((r['score'] / total_flags) * 100, 1) if total_flags > 0 else 0
        rankings.append(r)
        
    conn.close()
    return render_template('acceptor_leaderboard.html', rankings=rankings, total_vulns=total_flags)

def log_startup_db_audit():
    """Logs startup DB path and critical table row counts to stdout for visibility."""
    db_path = os.path.abspath('scoreboard.db')
    print("=" * 60, flush=True)
    print(f"[STARTUP DB PERSISTENCE AUDIT - FLAG ACCEPTOR]", flush=True)
    print(f"Database Path: {db_path}", flush=True)
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            tables = ['interns', 'submissions']
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
        print("  - WARNING: scoreboard.db does not exist yet!", flush=True)
    print("=" * 60, flush=True)


def create_db_backup(db_name='scoreboard.db', prefix='scoreboard'):
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


def start_periodic_backup_worker(interval_seconds=900):
    """Background worker thread to periodically snapshot database every 15 minutes."""
    def _backup_loop():
        create_db_backup('scoreboard.db', 'scoreboard')
        while True:
            time.sleep(interval_seconds)
            create_db_backup('scoreboard.db', 'scoreboard')

    thread = threading.Thread(target=_backup_loop, daemon=True)
    thread.start()


if __name__ == '__main__':
    init_db()
    # Guard against Werkzeug reloader double-init in debug mode
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        log_startup_db_audit()
        start_periodic_backup_worker(interval_seconds=900)
    app.run(host='0.0.0.0', port=8000, debug=True)
