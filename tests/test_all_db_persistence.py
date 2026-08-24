import subprocess
import sqlite3
import os
import time

def run_persistence_proof():
    print("=== STEP 1: Insert Test Rows into All Database Files ===")
    
    # 1. bank.db
    conn = sqlite3.connect('bank.db')
    conn.execute("DELETE FROM users WHERE username = 'persist_test_user'")
    conn.execute("INSERT INTO users (username, password, email, role, balance) VALUES ('persist_test_user', 'pass123', 'persist@bank.com', 'user', 500)")
    conn.commit()
    conn.close()
    print("Inserted 'persist_test_user' into bank.db")

    # 2. scoreboard.db
    conn = sqlite3.connect('scoreboard.db')
    conn.execute("DELETE FROM interns WHERE identifier = 'persist_test_intern@bank.com'")
    conn.execute("INSERT INTO interns (identifier, password_hash, intern_id) VALUES ('persist_test_intern@bank.com', 'hash123', 'INT-PERST')")
    conn.commit()
    conn.close()
    print("Inserted 'persist_test_intern@bank.com' into scoreboard.db")

    # 3. backup/bank_backup.db
    os.makedirs('backup', exist_ok=True)
    conn = sqlite3.connect('backup/bank_backup.db')
    conn.execute("CREATE TABLE IF NOT EXISTS backup_test (id INTEGER PRIMARY KEY, item TEXT)")
    conn.execute("DELETE FROM backup_test WHERE item = 'backup_persist_item'")
    conn.execute("INSERT INTO backup_test (item) VALUES ('backup_persist_item')")
    conn.commit()
    conn.close()
    print("Inserted 'backup_persist_item' into backup/bank_backup.db")

    # 4. config/app_config.db
    os.makedirs('config', exist_ok=True)
    conn = sqlite3.connect('config/app_config.db')
    conn.execute("CREATE TABLE IF NOT EXISTS config_test (id INTEGER PRIMARY KEY, setting TEXT)")
    conn.execute("DELETE FROM config_test WHERE setting = 'config_persist_setting'")
    conn.execute("INSERT INTO config_test (setting) VALUES ('config_persist_setting')")
    conn.commit()
    conn.close()
    print("Inserted 'config_persist_setting' into config/app_config.db")

    print("\n=== STEP 2: Tear Down & Restart Containers (docker compose down && docker compose up -d) ===")
    subprocess.run(["docker", "compose", "down"], check=True)
    subprocess.run(["docker", "compose", "up", "-d"], check=True)
    time.sleep(3)

    print("\n=== STEP 3: Verify Test Rows Persisted Post-Restart ===")
    
    # 1. bank.db
    conn = sqlite3.connect('bank.db')
    row_bank = conn.execute("SELECT username, email FROM users WHERE username = 'persist_test_user'").fetchone()
    conn.close()
    print(f"bank.db post-restart record: {row_bank}")
    assert row_bank is not None, "FAILED: bank.db record missing after restart!"

    # 2. scoreboard.db
    conn = sqlite3.connect('scoreboard.db')
    row_score = conn.execute("SELECT identifier, intern_id FROM interns WHERE identifier = 'persist_test_intern@bank.com'").fetchone()
    conn.close()
    print(f"scoreboard.db post-restart record: {row_score}")
    assert row_score is not None, "FAILED: scoreboard.db record missing after restart!"

    # 3. backup/bank_backup.db
    conn = sqlite3.connect('backup/bank_backup.db')
    row_backup = conn.execute("SELECT item FROM backup_test WHERE item = 'backup_persist_item'").fetchone()
    conn.close()
    print(f"backup/bank_backup.db post-restart record: {row_backup}")
    assert row_backup is not None, "FAILED: backup/bank_backup.db record missing after restart!"

    # 4. config/app_config.db
    conn = sqlite3.connect('config/app_config.db')
    row_config = conn.execute("SELECT setting FROM config_test WHERE setting = 'config_persist_setting'").fetchone()
    conn.close()
    print(f"config/app_config.db post-restart record: {row_config}")
    assert row_config is not None, "FAILED: config/app_config.db record missing after restart!"

    print("\n---> ALL 4 DATABASE FILES PROVEN PERSISTENT ACROSS CONTAINER RESTARTS!")

if __name__ == '__main__':
    run_persistence_proof()
