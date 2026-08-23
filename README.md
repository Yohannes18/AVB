# 🏦 AdvancedVulnBank & CTF Flag Acceptor

Welcome to the finalized AdvancedVulnBank CTF platform! This repository contains a highly vulnerable banking application configured with 55 unique vulnerabilities, alongside a centralized Flag Acceptor for managing intern scoring.

## 🚀 Deployment (AWS EC2)

When your AWS account verification is complete, you can deploy this entire stack to an EC2 instance.

### Step 1: Provision the Server
Ensure your AWS CLI is configured (`aws configure`). Then, use the provided deployment script to launch an Ubuntu EC2 instance:
```bash
bash deploy_aws.sh
```
*(Note: The deployment script contains intentional misconfigurations, such as a `0.0.0.0/0` security group, which are part of the CTF experience. It will also automatically execute `setup.sh` on the server to install Docker).*

### Step 2: Sync the Application Code
Once the server is running, use `scp` to copy this entire directory to the `/opt/vulnbank` folder on the new server:
```bash
scp -i /path/to/your/aws-key.pem -r ./* ubuntu@<EC2-INSTANCE-IP>:/opt/vulnbank/
```

### Step 3: Start the Platform
SSH into the server and start both the Vulnerable Bank and the Flag Acceptor:
```bash
ssh -i /path/to/your/aws-key.pem ubuntu@<EC2-INSTANCE-IP>
cd /opt/vulnbank
sudo docker-compose up -d
```

## 🏁 How the CTF Works

* **Flag Acceptor (Port 8000):** Interns visit `http://<EC2-INSTANCE-IP>:8000` to dynamically register and receive an `Intern ID` (e.g., `INT-8A2B9`).
* **Vulnerable Bank (Port 5000):** Interns visit `http://<EC2-INSTANCE-IP>:5000` and use the "Configure Intern ID" link on the login page to bind their ID to the bank. The bank will then generate 55 cryptographically unique flags specifically for them.
* **Admin Leaderboard:** To view intern progress, go to the Flag Acceptor login page, enter `ADMIN` as the Intern ID, and use the password `super_secret_admin_password_123`.

---

## 💾 Database Persistence & Deployment Checklist

To ensure no state or intern scores are lost across container rebuilds or server restarts, all database files and snapshot directories MUST be mounted via volume bindings in `docker-compose.yml`:

### 1. Required Volume Mounts (`docker-compose.yml`)

| Service | Host Path | Container Path | Description |
| :--- | :--- | :--- | :--- |
| `vulnbank` | `./bank.db` | `/app/bank.db` | Primary application SQLite database |
| `vulnbank` | `./backup` | `/app/backup` | Backup vulnerability target directory |
| `vulnbank` | `./config` | `/app/config` | Config vulnerability target directory |
| `vulnbank` | `./backups` | `/app/backups` | Scheduled snapshot backup directory |
| `flag_acceptor` | `./scoreboard.db` | `/app/scoreboard.db` | Intern score & credential database |
| `flag_acceptor` | `./backups` | `/app/backups` | Scheduled snapshot backup directory |

### 2. Startup Audit Log Verification

Upon boot, both services print a `STARTUP DB PERSISTENCE AUDIT` to stdout. Verify startup logs after any deployment:

```bash
docker logs flag_acceptor
docker logs advanced_vulnbank
```

**Healthy Log Output Example (`flag_acceptor`):**
```text
============================================================
[STARTUP DB PERSISTENCE AUDIT - FLAG ACCEPTOR]
Database Path: /app/scoreboard.db
  - Table 'interns': 18 rows
  - Table 'submissions': 1 rows
============================================================
[BACKUP WORKER] Snapshot created: backups/scoreboard_20260823_200032.db
```

**Healthy Log Output Example (`advanced_vulnbank`):**
```text
============================================================
[STARTUP DB PERSISTENCE AUDIT - VULNBANK]
Database Path: /app/bank.db
  - Table 'users': 7 rows
  - Table 'transactions': 74 rows
  - Table 'hidden_data': 4 rows
============================================================
[BACKUP WORKER] Snapshot created: backups/bank_20260823_200032.db
```

> ⚠️ **Warning:** If row counts unexpectedly drop to `0` after container restart, immediately check host volume mounts before allowing interns to access the platform.

### 3. Post-Deployment Verification Procedure

1. **Rebuild Container Layers:** Always run `docker compose build && docker compose up -d` after modifying python code so live containers execute current code.
2. **Run Persistence Test:** Run `python3 test_all_db_persistence.py` to confirm rows survive `docker compose down && docker compose up -d`.
3. **Verify Snapshot Backups:** Inspect `backups/` using `ls -la backups/` to confirm timestamped `.db` files are created. Automated workers retain the 10 most recent snapshots and prune older files.

