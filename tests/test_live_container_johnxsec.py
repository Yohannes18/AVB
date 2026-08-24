import requests
import subprocess
import sqlite3
import re
import time

BASE_URL = "http://127.0.0.1:8000"

def wait_for_server(url, max_retries=10):
    for i in range(max_retries):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False

def get_session_id_from_response(html_text):
    # Match ID from success flash message or instant-copy card only (ignoring placeholder text)
    match = re.search(r'(?:Registration successful|Welcome back).*?(INT-[A-Z0-9]{5})', html_text, re.DOTALL)
    if match:
        return match.group(1)
    return None

def run_test():
    # Clean up any existing test records for JohnxSec first
    conn = sqlite3.connect('scoreboard.db')
    conn.execute("DELETE FROM interns WHERE identifier = 'johnxsec'")
    conn.commit()
    conn.close()
    
    print("--- STEP 1: Register JohnxSec with password 'testpass1' ---")
    wait_for_server(BASE_URL)
    payload1 = {
        'action': 'register',
        'identifier': 'JohnxSec',
        'password': 'testpass1'
    }
    r1 = requests.post(BASE_URL, data=payload1)
    id1 = get_session_id_from_response(r1.text)
    print(f"HTTP Status: {r1.status_code}")
    print(f"Returned Session ID: {id1}")
    print(f"Flash message: {'Registration successful' in r1.text or 'Welcome back' in r1.text}")
    
    # Query database to confirm row state
    conn = sqlite3.connect('scoreboard.db')
    row1 = conn.execute("SELECT id, identifier, intern_id, created_at FROM interns WHERE identifier = 'johnxsec'").fetchone()
    conn.close()
    print(f"DB Record after step 1: {row1}\n")
    
    print("--- STEP 2: Restart Containers (docker compose down && docker compose up -d) ---")
    subprocess.run(["docker", "compose", "down"], check=True)
    subprocess.run(["docker", "compose", "up", "-d"], check=True)
    print("Waiting for flag_acceptor container on port 8000 to be ready...")
    ready = wait_for_server(BASE_URL)
    print(f"Container ready: {ready}\n")
    
    print("--- STEP 3: Register JohnxSec again with 'testpass1' (Post-Restart) ---")
    payload2 = {
        'action': 'register',
        'identifier': 'JohnxSec',
        'password': 'testpass1'
    }
    r2 = requests.post(BASE_URL, data=payload2)
    id2 = get_session_id_from_response(r2.text)
    print(f"HTTP Status: {r2.status_code}")
    print(f"Returned Session ID: {id2}")
    print(f"Contains 'Welcome back!': {'Welcome back!' in r2.text}")
    print(f"Same ID preserved after container restart?: {id1 == id2} ({id1} == {id2})\n")
    
    print("--- STEP 4: Attempt JohnxSec again with WRONG password ('wrongpass') ---")
    payload3 = {
        'action': 'register',
        'identifier': 'JohnxSec',
        'password': 'wrongpass'
    }
    r3 = requests.post(BASE_URL, data=payload3)
    id3 = get_session_id_from_response(r3.text)
    print(f"HTTP Status: {r3.status_code}")
    print(f"Returned Session ID: {id3}")
    print(f"Contains 'Invalid credentials': {'Invalid credentials' in r3.text}")
    print(f"Rejected correctly?: {'Invalid credentials' in r3.text and id3 is None}\n")

if __name__ == '__main__':
    run_test()
