import requests
import sqlite3
import re
import time

BASE_URL = "http://127.0.0.1:8000"

def get_session_id_from_response(html_text):
    match = re.search(r'INT-[A-Z0-9]{5}', html_text)
    if match:
        return match.group(0)
    return None

def run_tests():
    # Clean up test identifiers from scoreboard.db
    conn = sqlite3.connect('scoreboard.db')
    conn.execute("DELETE FROM interns WHERE identifier IN ('seq_test_user@bank.com', 'orphaned_user@bank.com')")
    conn.commit()
    conn.close()

    print("=== SCENARIO 1: New identifier, first submission (Step 1 -> Step 2 transition) ===")
    session1 = requests.Session()
    r1 = session1.post(BASE_URL, data={'action': 'check', 'identifier': 'seq_test_user@bank.com', 'password': 'mysecretpass'})
    print(f"HTTP Status: {r1.status_code}")
    print(f"Contains Step 2 Title ('First time here'): {'First time here' in r1.text}")
    print(f"Contains 'No account found for this ID': {'No account found for this ID' in r1.text}")
    print(f"Has form action='create': {'value=\"create\"' in r1.text}")
    print(f"Session ID issued yet?: {get_session_id_from_response(r1.text)}")
    assert 'First time here' in r1.text, "Failed Scenario 1: Step 2 title missing!"
    assert get_session_id_from_response(r1.text) is None, "Failed Scenario 1: ID should not be issued on Step 1 check!"
    print("-> SCENARIO 1 PASSED: New identifier cleanly transitions to 'Create Account' step.\n")

    print("=== SCENARIO 2: Complete account creation (Step 2 submission) ===")
    r2 = session1.post(BASE_URL, data={'action': 'create', 'identifier': 'seq_test_user@bank.com', 'password': 'mysecretpass', 'confirm_password': 'mysecretpass'})
    id_created = get_session_id_from_response(r2.text)
    print(f"HTTP Status: {r2.status_code}")
    print(f"Contains 'Account created successfully!': {'Account created successfully!' in r2.text}")
    print(f"Generated Session ID: {id_created}")
    assert 'Account created successfully!' in r2.text, "Failed Scenario 2: Account creation failed!"
    assert id_created is not None, "Failed Scenario 2: Session ID missing!"
    print("-> SCENARIO 2 PASSED: Account created and Session ID returned.\n")

    print("=== SCENARIO 3: Same identifier, correct password submitted again (Step 1 Login) ===")
    session2 = requests.Session()
    r3 = session2.post(BASE_URL, data={'action': 'check', 'identifier': 'seq_test_user@bank.com', 'password': 'mysecretpass'})
    id_relogin = get_session_id_from_response(r3.text)
    print(f"HTTP Status: {r3.status_code}")
    print(f"Contains 'Welcome back!': {'Welcome back!' in r3.text}")
    print(f"Returned Session ID: {id_relogin}")
    print(f"Same ID as creation?: {id_created == id_relogin}")
    assert 'Welcome back!' in r3.text, "Failed Scenario 3: Welcome back flash missing!"
    assert id_created == id_relogin, "Failed Scenario 3: Session ID changed on relogin!"
    print("-> SCENARIO 3 PASSED: Logging in with existing identifier returns same Session ID.\n")

    print("=== SCENARIO 4: Same identifier, wrong password ===")
    session3 = requests.Session()
    r4 = session3.post(BASE_URL, data={'action': 'check', 'identifier': 'seq_test_user@bank.com', 'password': 'WRONGPASS'})
    id_wrong = get_session_id_from_response(r4.text)
    print(f"HTTP Status: {r4.status_code}")
    print(f"Contains 'Invalid credentials': {'Invalid credentials' in r4.text}")
    print(f"Session ID issued?: {id_wrong}")
    print(f"Remains on Step 1?: {'value=\"check\"' in r4.text}")
    assert 'Invalid credentials' in r4.text, "Failed Scenario 4: Rejection message missing!"
    assert id_wrong is None, "Failed Scenario 4: Session ID issued on wrong password!"
    assert 'value="check"' in r4.text, "Failed Scenario 4: Did not stay on Step 1!"
    print("-> SCENARIO 4 PASSED: Rejection enforced on wrong password, remains on Step 1.\n")

    print("=== SCENARIO 5: Unknown identifier submitted twice without completing account creation ===")
    # First submit 'orphaned_user@bank.com' on Step 1 (does not call create)
    s_orphan = requests.Session()
    s_orphan.post(BASE_URL, data={'action': 'check', 'identifier': 'orphaned_user@bank.com', 'password': 'pass1'})
    # Second submit 'orphaned_user@bank.com' on Step 1 again (does not call create)
    s_orphan.post(BASE_URL, data={'action': 'check', 'identifier': 'orphaned_user@bank.com', 'password': 'pass1'})
    
    # Check DB
    conn = sqlite3.connect('scoreboard.db')
    rows = conn.execute("SELECT * FROM interns WHERE identifier = 'orphaned_user@bank.com'").fetchall()
    conn.close()
    print(f"Database rows found for orphaned_user@bank.com: {len(rows)}")
    assert len(rows) == 0, f"Failed Scenario 5: Orphaned rows created! ({rows})"
    print("-> SCENARIO 5 PASSED: 0 rows created when account creation was not completed.\n")

if __name__ == '__main__':
    run_tests()
