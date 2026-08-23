import requests
import sqlite3

BASE_URL = "http://127.0.0.1:5000"

def test_intern_id_flow():
    s = requests.Session()
    
    # 1. Post setup with intern_id INT-TEST99
    r_setup = s.post(f"{BASE_URL}/setup", data={'intern_id': 'INT-TEST99'}, allow_redirects=True)
    print(f"Setup POST status: {r_setup.status_code}")
    
    # 2. Login as admin
    r_login = s.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': 'admin123'}, allow_redirects=True)
    print(f"Login POST status: {r_login.status_code}")
    
    # 3. Check profile page
    r_profile = s.get(f"{BASE_URL}/profile")
    print(f"Profile GET status: {r_profile.status_code}")
    assert r_profile.status_code == 200, "Failed to load /profile"
    
    assert "LOCKED & BOUND" in r_profile.text, "LOCKED & BOUND badge missing from /profile"
    assert "INT-TEST99" in r_profile.text, "Configured Intern ID INT-TEST99 missing from /profile"
    print("Profile page correctly displays LOCKED & BOUND Intern ID INT-TEST99!")

    # 4. Check DB persistence for user admin
    conn = sqlite3.connect('bank.db')
    cursor = conn.cursor()
    cursor.execute("SELECT intern_id FROM users WHERE username = 'admin'")
    row = cursor.fetchone()
    conn.close()
    
    print(f"Database stored intern_id for admin: {row[0] if row else None}")
    assert row and row[0] == 'INT-TEST99', "Intern ID was not persisted in bank.db users table"
    
    # 5. Check GET /setup when already configured (should be read-only / locked)
    r_setup_revisit = s.get(f"{BASE_URL}/setup")
    assert r_setup_revisit.status_code == 200, "Failed GET /setup"
    assert "Your Registration ID is locked to INT-TEST99" in r_setup_revisit.text, "Lock notice missing from GET /setup"
    print("Re-visiting GET /setup correctly shows lock banner: 'Your Registration ID is locked to INT-TEST99'")

    # 6. Attempt POST /setup with a different ID (should be rejected and locked)
    r_reconfig = s.post(f"{BASE_URL}/setup", data={'intern_id': 'INT-NEWID123'}, allow_redirects=True)
    assert "Registration ID is locked to INT-TEST99" in r_reconfig.text, "POST reconfiguration was not blocked"
    print("POST /setup reconfiguration attempt was successfully BLOCKED and rejected!")

    print("\n---> ALL PERMANENT INTERN ID LOCKING & PROTECTION TESTS PASSED!")

if __name__ == '__main__':
    test_intern_id_flow()
