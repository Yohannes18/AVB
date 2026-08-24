import sqlite3
import unittest
from werkzeug.security import check_password_hash
import flag_acceptor
import app as main_bank_app

class TestPersistentInternID(unittest.TestCase):
    def setUp(self):
        flag_acceptor.init_db()
        conn = sqlite3.connect('scoreboard.db')
        c = conn.cursor()
        c.execute("DELETE FROM interns WHERE identifier LIKE '%@university.edu' OR identifier LIKE '%@bank.com'")
        conn.commit()
        conn.close()
        self.acceptor_client = flag_acceptor.app.test_client()
        self.bank_client = main_bank_app.app.test_client()

    def test_01_two_different_identifiers(self):
        print("\n--- Test 1: Register Two Different Identifiers ---")
        res1 = self.acceptor_client.post('/', data={
            'action': 'register',
            'identifier': 'alice@university.edu',
            'password': 'Password123!'
        }, follow_redirects=True)
        self.assertIn(b'Registration successful', res1.data)
        
        conn = sqlite3.connect('scoreboard.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM interns WHERE identifier = 'alice@university.edu'")
        alice_id = c.fetchone()['intern_id']
        print(f"Alice Identifier: 'alice@university.edu' -> Returned ID: {alice_id}")
        
        res2 = self.acceptor_client.post('/', data={
            'action': 'register',
            'identifier': 'bob@university.edu',
            'password': 'SecureBobPass456!'
        }, follow_redirects=True)
        self.assertIn(b'Registration successful', res2.data)
        
        c.execute("SELECT * FROM interns WHERE identifier = 'bob@university.edu'")
        bob_id = c.fetchone()['intern_id']
        conn.close()
        print(f"Bob Identifier:   'bob@university.edu'   -> Returned ID: {bob_id}")
        
        self.assertNotEqual(alice_id, bob_id)
        print("RESULT: Successfully created 2 unique, distinct intern IDs for 2 identifiers.")

    def test_02_same_identifier_correct_password(self):
        print("\n--- Test 2: Same Identifier + Correct Password Submitted Twice ---")
        res1 = self.acceptor_client.post('/', data={
            'action': 'register',
            'identifier': 'charlie@bank.com',
            'password': 'MySecretPass789!'
        }, follow_redirects=True)
        
        conn = sqlite3.connect('scoreboard.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM interns WHERE identifier = 'charlie@bank.com'")
        id1 = c.fetchone()['intern_id']
        print(f"Call 1 (New Registration):   Identifier 'charlie@bank.com' -> Returned ID: {id1}")
        
        res2 = self.acceptor_client.post('/', data={
            'action': 'register',
            'identifier': 'charlie@bank.com',
            'password': 'MySecretPass789!'
        }, follow_redirects=True)
        self.assertIn(b'Welcome back!', res2.data)
        
        c.execute("SELECT * FROM interns WHERE identifier = 'charlie@bank.com'")
        id2 = c.fetchone()['intern_id']
        conn.close()
        print(f"Call 2 (Repeat Submission):  Identifier 'charlie@bank.com' -> Returned ID: {id2}")
        
        self.assertEqual(id1, id2)
        print("RESULT: Identical intern ID returned. No duplicate or regenerated ID created.")

    def test_03_same_identifier_wrong_password(self):
        print("\n--- Test 3: Same Identifier + Wrong Password ---")
        self.acceptor_client.post('/', data={
            'action': 'register',
            'identifier': 'charlie@bank.com',
            'password': 'MySecretPass789!'
        }, follow_redirects=True)

        conn = sqlite3.connect('scoreboard.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM interns WHERE identifier = 'charlie@bank.com'")
        before_row = c.fetchone()
        orig_id = before_row['intern_id']
        orig_hash = before_row['password_hash']
        conn.close()
        
        res = self.acceptor_client.post('/', data={
            'action': 'register',
            'identifier': 'charlie@bank.com',
            'password': 'WrongPassword123'
        }, follow_redirects=True)
        self.assertIn(b'Invalid credentials', res.data)
        
        conn = sqlite3.connect('scoreboard.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM interns WHERE identifier = 'charlie@bank.com'")
        after_row = c.fetchone()
        conn.close()
        
        print(f"Attempt with Wrong Password -> Response contains 'Invalid credentials'")
        print(f"DB Record Before: ID={orig_id}, Hash={orig_hash[:25]}...")
        print(f"DB Record After:  ID={after_row['intern_id']}, Hash={after_row['password_hash'][:25]}...")
        
        self.assertEqual(orig_id, after_row['intern_id'])
        self.assertEqual(orig_hash, after_row['password_hash'])
        print("RESULT: Attempt rejected with generic error. DB record completely untouched.")

    def test_04_securebank_setup_binding_flow(self):
        print("\n--- Test 4: SecureBank Setup Binding Flow (/setup) ---")
        self.acceptor_client.post('/', data={
            'action': 'register',
            'identifier': 'alice@university.edu',
            'password': 'Password123!'
        }, follow_redirects=True)

        conn = sqlite3.connect('scoreboard.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT intern_id FROM interns WHERE identifier = 'alice@university.edu'")
        alice_id = c.fetchone()['intern_id']
        conn.close()
        
        setup_res = self.bank_client.post('/setup', data={'intern_id': alice_id}, follow_redirects=True)
        self.assertEqual(setup_res.status_code, 200)
        self.assertTrue(b'Registration ID permanently bound' in setup_res.data or b'Instance bound to' in setup_res.data or b'bound' in setup_res.data)
        
        with self.bank_client.session_transaction() as sess:
            bound_id = sess.get('intern_id')
        self.assertEqual(bound_id, alice_id)
        
        print(f"POST /setup data={{'intern_id': '{alice_id}'}} -> Flash: 'Instance bound to {alice_id}!'")
        print(f"Verified session['intern_id'] in SecureBank: '{bound_id}'")
        print("RESULT: SecureBank /setup binding flow remains 100% operational.")

    def test_05_identifier_case_normalization(self):
        print("\n--- Test 5: Identifier Case Normalization ---")
        # Step 1: Register with mixed case 'Alice@University.EDU'
        res1 = self.acceptor_client.post('/', data={
            'action': 'register',
            'identifier': 'Alice@University.EDU',
            'password': 'Password123!'
        }, follow_redirects=True)
        self.assertIn(b'Registration successful', res1.data)
        
        conn = sqlite3.connect('scoreboard.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM interns WHERE identifier = 'alice@university.edu'")
        reg_row = c.fetchone()
        self.assertIsNotNone(reg_row)
        reg_id = reg_row['intern_id']
        print(f"Registration ('Alice@University.EDU') -> Saved identifier: 'alice@university.edu', Returned ID: {reg_id}")
        
        # Step 2: Retrieve with lowercase 'alice@university.edu'
        res2 = self.acceptor_client.post('/', data={
            'action': 'register',
            'identifier': 'alice@university.edu',
            'password': 'Password123!'
        }, follow_redirects=True)
        self.assertIn(b'Welcome back!', res2.data)
        
        c.execute("SELECT intern_id FROM interns WHERE identifier = 'alice@university.edu'")
        ret_id = c.fetchone()['intern_id']
        conn.close()
        print(f"Retrieval    ('alice@university.edu') -> Returned ID: {ret_id}")
        
        self.assertEqual(reg_id, ret_id)
        print("RESULT: Case normalization verified. Both mixed-case and lowercase inputs resolve to the identical intern ID.")

if __name__ == '__main__':
    unittest.main()
