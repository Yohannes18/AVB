import requests
import re
from flag_acceptor import generate_student_flag

import sqlite3

BASE_URL = "http://127.0.0.1:8000"

def test_categorized_dashboard_and_submission():
    ident = "categorized_test_student@uni.edu"
    pwd = "student_password_123"

    # Cleanup existing submissions for test student to ensure repeatable test runs
    try:
        conn = sqlite3.connect('scoreboard.db')
        c = conn.cursor()
        c.execute("DELETE FROM submissions WHERE intern_id IN (SELECT intern_id FROM interns WHERE identifier = ?)", (ident,))
        conn.commit()
        conn.close()
    except Exception:
        pass

    s = requests.Session()
    # 1. Sign in / Create
    r1 = s.post(BASE_URL, data={'action': 'check', 'identifier': ident, 'password': pwd})
    if "step2" in r1.text or "Set a password" in r1.text:
        r1 = s.post(BASE_URL, data={'action': 'create', 'identifier': ident, 'password': pwd, 'confirm_password': pwd})

    # Extract intern_id from dashboard
    r_dash = s.get(f"{BASE_URL}/dashboard")
    assert r_dash.status_code == 200
    m = re.search(r'ID:\s*(INT-[A-Z0-9]+)', r_dash.text)
    assert m, "Failed to find intern ID in dashboard"
    intern_id = m.group(1)
    print(f"✓ Found intern ID: {intern_id}")

    # Check categories rendered in HTML
    categories_expected = [
        "SQL Injection",
        "Code Execution",
        "Auth, Session",
        "JWT",
        "File System",
        "Server-Side Request Forgery",
        "Cryptography"
    ]
    for cat_title in categories_expected:
        assert cat_title in r_dash.text, f"Category title '{cat_title}' missing from dashboard HTML"
    print("✓ All 7 vulnerability categories successfully rendered in dashboard.")

    # 2. Submit a valid flag for SQLi #1 (sqli_login)
    sqli_flag = generate_student_flag("sqli_login", intern_id)
    r_sub = s.post(f"{BASE_URL}/dashboard", data={'flag': sqli_flag})
    assert r_sub.status_code == 200
    assert "🎉 Correct! You solved: SQLi #1: Auth Bypass on Login Form!" in r_sub.text, "Flash message missing for solved flag"
    assert "Flag Solved" in r_sub.text or "Solved" in r_sub.text or "status-pill solved" in r_sub.text, "Flag slot did not mark as solved"
    print("✓ Submitting SQLi flag correctly solved the slot and updated dashboard state.")

    # 3. Submit a valid flag for RCE #1 (cmd_injection)
    rce_flag = generate_student_flag("cmd_injection", intern_id)
    r_sub2 = s.post(f"{BASE_URL}/dashboard", data={'flag': rce_flag})
    assert r_sub2.status_code == 200
    assert "🎉 Correct! You solved: RCE #1: Backup System OS Command Injection!" in r_sub2.text
    print("✓ Submitting Command Injection flag correctly solved the RCE slot.")

    print("\n---> CATEGORIZED DASHBOARD & SUBMISSION TESTS PASSED!")

if __name__ == '__main__':
    test_categorized_dashboard_and_submission()
