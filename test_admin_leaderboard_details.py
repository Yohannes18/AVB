import requests
import sqlite3
import re
import time

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    # 1. Admin Login
    s_admin = requests.Session()
    r_admin_login = s_admin.post(BASE_URL, data={'action': 'check', 'identifier': 'admin', 'password': 'super_secret_admin_password_123'})
    assert r_admin_login.status_code == 200 or r_admin_login.status_code == 302, "Admin login failed!"

    r_leaderboard = s_admin.get(f"{BASE_URL}/admin/leaderboard")
    print(f"Leaderboard HTTP Status: {r_leaderboard.status_code}")
    assert r_leaderboard.status_code == 200, "Failed to load /admin/leaderboard"

    # Verify that all registered interns (even with 0 flags solved) pop up in the leaderboard
    conn = sqlite3.connect('scoreboard.db')
    cursor = conn.cursor()
    cursor.execute("SELECT intern_id, identifier FROM interns")
    all_interns = cursor.fetchall()
    conn.close()

    print(f"Total registered interns in database: {len(all_interns)}")
    print(f"Contains 'Admin Scoreboard & Cohort Analytics': {'Admin Scoreboard & Cohort Analytics' in r_leaderboard.text}")
    print(f"Contains 'Total Registered Students': {'Total Registered Students' in r_leaderboard.text}")

    # Check that registered session IDs and identifiers appear in the rendered HTML
    found_count = 0
    for i_id, ident in all_interns:
        if i_id in r_leaderboard.text:
            found_count += 1
    
    print(f"Registered Session IDs found in rendered HTML leaderboard: {found_count} / {len(all_interns)}")
    assert found_count == len(all_interns), f"Mismatch: expected all {len(all_interns)} registered students to appear in leaderboard, found {found_count}"

    print("\n---> ADMIN LEADERBOARD TEST PASSED: All registered students now pop up with detailed information!")

if __name__ == '__main__':
    run_tests()
