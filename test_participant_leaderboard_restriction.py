import requests
import sqlite3

BASE_URL = "http://127.0.0.1:8000"

def test_leaderboard_restriction():
    s = requests.Session()

    # 1. Create/sign-in participant account
    ident = "student_restrict_test@uni.edu"
    pwd = "student_password_123"

    # Step 1 check
    r1 = s.post(BASE_URL, data={'action': 'check', 'identifier': ident, 'password': pwd})
    if "step2" in r1.text or "Set a password" in r1.text:
        # Step 2 create
        r2 = s.post(BASE_URL, data={'action': 'create', 'identifier': ident, 'password': pwd, 'confirm_password': pwd})
        assert "Session ID Ready!" in r2.text or r2.status_code == 200, "Account creation failed"

    # 2. Access dashboard
    r_dash = s.get(f"{BASE_URL}/dashboard")
    assert r_dash.status_code == 200, "Failed to load participant dashboard"
    assert "href=\"/leaderboard\"" not in r_dash.text, "Leaderboard link still present in participant dashboard"
    print("✓ Participant dashboard correctly excludes Leaderboard navigation link.")

    # 3. Attempt to access GET /leaderboard as participant (should redirect to /dashboard)
    r_lb = s.get(f"{BASE_URL}/leaderboard", allow_redirects=True)
    assert r_lb.status_code == 200, "Failed GET /leaderboard request"
    assert "/dashboard" in r_lb.url, "GET /leaderboard did not redirect to /dashboard"
    assert "The leaderboard is restricted to administrators." in r_lb.text, "Restriction flash message missing"
    print("✓ Participant GET /leaderboard attempt correctly blocked & redirected to /dashboard.")

    # 4. Attempt to access GET /admin/leaderboard as participant (should redirect away with admin error)
    r_admin_lb = s.get(f"{BASE_URL}/admin/leaderboard", allow_redirects=True)
    assert "Admin access required." in r_admin_lb.text or "/admin/leaderboard" not in r_admin_lb.url, "Participant accessed admin leaderboard"
    print("✓ Participant GET /admin/leaderboard attempt correctly blocked by admin_required decorator.")

    print("\n---> ALL PARTICIPANT LEADERBOARD RESTRICTION TESTS PASSED!")

if __name__ == '__main__':
    test_leaderboard_restriction()
