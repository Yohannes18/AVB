# 🛡️ Cybersecurity Internship CTF & Evaluation Manual

Welcome to the Cybersecurity Internship Practical Assessment! This hands-on evaluation tests your web application security assessment, penetration testing, and vulnerability reporting skills on a realistic banking application (**SecureBank**).

---

## 📌 Executive Summary & Rules of Engagement

1. **Individual Assessment:** This is an individual practical exam. Every candidate is assigned a unique, cryptographically generated **Candidate Session ID** (or Intern ID).
2. **Dynamic Anti-Cheat Flags:** All flags embedded within the target application are dynamically salted with your personal **Session ID**. 
   > ⚠️ **Warning:** Flags are strictly non-transferable. Submitting another candidate's flag will result in an automated anti-cheat flag and failure of the assessment.
3. **Session Verification Requirement:** All vulnerability submissions and reports are validated against your registered **Session ID** metadata (`<meta name="session-ref">`).
4. **Scope:** Only test the target application on Port `5000`. Do NOT attack or attempt to disrupt the Flag Acceptor portal infrastructure on Port `8000`.

---

## 🚀 Getting Started: Step-by-Step Instructions

### Step 1: Generate Your Unique Session ID

1. Open your web browser and navigate to the **Flag Acceptor Portal**:
   ```text
   http://<YOUR_AWS_EC2_IP>:8000
   ```
2. Click the green **"Generate New Intern ID"** button.
3. The portal will generate your unique ID (e.g., `INT-A1B2C`).
4. **Important:** Copy and save this ID. You will use it to log into the Flag Acceptor and to bind your target banking instance.

---

### Step 2: Configure Your Target Banking Instance

1. Navigate to the **SecureBank Application**:
   ```text
   http://<YOUR_AWS_EC2_IP>:5000
   ```
2. On the main sign-in page, click the **"Configure Session ID"** link at the bottom.
3. Paste your generated **Session ID** (e.g., `INT-A1B2C`) into the form and submit.
4. You will be redirected back to the login page. Your **Session ID** is now securely registered to your active environment session.

---

### Step 3: Exploitation & Flag Submission

As you identify and exploit vulnerabilities across the application, you will uncover confirmation flags formatted as:
```text
FLAG{Vulnerability_Name_XXXXXXXX}
```

#### How to Submit Flags:
1. Return to the **Flag Acceptor Portal** (`http://<YOUR_AWS_EC2_IP>:8000`).
2. Log in using your **Intern ID**.
3. Paste your discovered flag into the **"Submit Discovered Flag"** input box and click **Submit Flag**.
4. The system will validate your flag and increment your score tracker.

---

## 📋 Final Technical Report Requirements

At the conclusion of the evaluation period, you must submit a formal **Penetration Testing & Vulnerability Assessment Report**.

### Report Structure Checklist:
For each vulnerability you discover, your report MUST include:

1. **Vulnerability Title & Severity:** Classified according to CVSSv3 / OWASP standards (Low, Medium, High, Critical).
2. **Vulnerability Category:** (e.g., SQL Injection, Remote Code Execution, SSRF, Broken Access Control).
3. **Proof of Concept (PoC):** Step-by-step instructions to reproduce the exploit.
4. **Screenshots:** Full-screen screenshots displaying the exploit output AND your visible **Intern ID Watermark**.
5. **Impact Analysis:** Explanation of the business and security impact if exploited by a real-world adversary.
6. **Remediation & Code Fix:** Concrete recommendations and code snippets showing how to patch the vulnerability.

---

## 🎯 Target Vulnerability Categories (Checklist)

The target application contains over 30 distinct vulnerabilities covering OWASP Top 10 and real-world CVE patterns. Use this list to guide your testing:

- [ ] **Authentication & Session Management** (Bypasses, Session Fixation, Weak Credentials)
- [ ] **Injection Flaws** (SQLi, Command Injection, Python `eval()` RCE, SSTI)
- [ ] **File & Data Insecurity** (LFI, Path Traversal, Zip Slip, Unrestricted File Upload)
- [ ] **Deserialization Attacks** (Python Pickle, Unsafe YAML Loading, Deserialization Chains)
- [ ] **Server-Side Request Forgery & XXE** (Basic SSRF, DNS Rebinding SSRF, XML External Entity)
- [ ] **Cryptographic Weaknesses** (Hardcoded Secrets, AES Static IV, RSA Tiny Primes)
- [ ] **Broken Access Control & API Security** (IDOR, Mass Data Export, JWT Confusion / Weak Signing)

> [!IMPORTANT]
> **Scoring & Flag Resolution Note:**  
> When extracting database tables (such as `hidden_data`) via raw SQL Injection, queries will return challenge key identifiers (e.g. `jwt_confusion`, `sqli_search`) instead of raw static flags. To resolve these keys into your valid, per-intern salted flag for submission, you must pivot to gain access to administrative views (e.g., `/admin`) where the application dynamically renders your salted flag.

---

Good luck with your security assessment! Work systematically, document every step, and ensure your fixes are actionable.
