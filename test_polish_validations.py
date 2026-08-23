import requests
import sqlite3
import re
import time

BASE_URL = "http://127.0.0.1:8000"

def wait_for_server(url, max_retries=10):
    for _ in range(max_retries):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False

def get_session_id_from_response(html_text):
    match = re.search(r'INT-[A-Z0-9]{5}', html_text)
    if match:
        return match.group(0)
    return None

def run_tests():
    wait_for_server(BASE_URL)
    
    # Clean up test records
    conn = sqlite3.connect('scoreboard.db')
    conn.execute("DELETE FROM interns WHERE identifier IN ('short_pass_user@bank.com', 'normal_user@bank.com', 'admin')")
    conn.commit()
    conn.close()

    print("=== TEST 1: Short Password Rejection (< 4 characters) ===")
    s1 = requests.Session()
    # Step 1 check
    s1.post(BASE_URL, data={'action': 'check', 'identifier': 'short_pass_user@bank.com', 'password': 'a'})
    # Step 2 create with 1-char password
    r1 = s1.post(BASE_URL, data={'action': 'create', 'identifier': 'short_pass_user@bank.com', 'password': 'a', 'confirm_password': 'a'})
    print(f"HTTP Status: {r1.status_code}")
    print(f"Contains 'Password must be at least 4 characters': {'Password must be at least 4 characters' in r1.text}")
    print(f"Preserves step 2: {'value=\"create\"' in r1.text}")
    print(f"Session ID issued?: {get_session_id_from_response(r1.text)}")
    assert 'Password must be at least 4 characters' in r1.text, "Failed Test 1: Short password rejection flash missing!"
    assert get_session_id_from_response(r1.text) is None, "Failed Test 1: Session ID issued on short password!"
    print("-> TEST 1a PASSED: 1-character password rejected cleanly.\n")

    # Retry Step 2 with valid 8-char password
    r1_valid = s1.post(BASE_URL, data={'action': 'create', 'identifier': 'short_pass_user@bank.com', 'password': 'validpass123', 'confirm_password': 'validpass123'})
    id_valid = get_session_id_from_response(r1_valid.text)
    print(f"Retry with valid password (validpass123) -> Session ID: {id_valid}")
    assert id_valid is not None, "Failed Test 1: Valid password retry failed!"
    print("-> TEST 1b PASSED: Valid password registration succeeded as expected.\n")

    print("=== TEST 2: Reserved Admin Identifier Rejection ('admin') ===")
    s2 = requests.Session()
    r2 = s2.post(BASE_URL, data={'action': 'create', 'identifier': 'admin', 'password': 'mysecretpass', 'confirm_password': 'mysecretpass'})
    print(f"HTTP Status: {r2.status_code}")
    print(f"Contains 'This identifier is reserved': {'This identifier is reserved' in r2.text}")
    print(f"Session ID issued?: {get_session_id_from_response(r2.text)}")
    
    conn = sqlite3.connect('scoreboard.db')
    admin_rows = conn.execute("SELECT * FROM interns WHERE identifier = 'admin'").fetchall()
    conn.close()
    print(f"Database rows created for 'admin': {len(admin_rows)}")
    assert 'This identifier is reserved' in r2.text, "Failed Test 2: Reserved identifier flash missing!"
    assert len(admin_rows) == 0, "Failed Test 2: Row created for reserved identifier admin!"
    print("-> TEST 2 PASSED: 'admin' identifier creation rejected cleanly with zero rows inserted.\n")

    print("=== TEST 3: Regression Check (Normal Registration & Relogin) ===")
    s3 = requests.Session()
    # Scenario 2: Create normal user
    s3.post(BASE_URL, data={'action': 'check', 'identifier': 'normal_user@bank.com', 'password': 'normalpass'})
    r3_create = s3.post(BASE_URL, data={'action': 'create', 'identifier': 'normal_user@bank.com', 'password': 'normalpass', 'confirm_password': 'normalpass'})
    id_normal = get_session_id_from_response(r3_create.text)
    print(f"Scenario 2 (Account Creation) -> Session ID: {id_normal}")
    assert id_normal is not None, "Failed Test 3: Account creation regression!"

    # Scenario 3: Relogin normal user
    s3_relogin = requests.Session()
    r3_login = s3_relogin.post(BASE_URL, data={'action': 'check', 'identifier': 'normal_user@bank.com', 'password': 'normalpass'})
    id_relogin = get_session_id_from_response(r3_login.text)
    print(f"Scenario 3 (Relogin) -> Session ID: {id_relogin}")
    print(f"Same ID returned?: {id_normal == id_relogin}")
    assert id_normal == id_relogin, "Failed Test 3: Relogin ID mismatch regression!"
    assert 'Welcome back!' in r3_login.text, "Failed Test 3: Welcome back flash missing!"
    print("-> TEST 3 PASSED: Normal registration & relogin remain 100% functional without regressions.\n")

if __name__ == '__main__':
    run_tests()
