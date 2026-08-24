import pytest
import flag_acceptor as acceptor
import app as bank_app

def test_prelogin_flag_generation_and_submission(tmp_path):
    """Test that pre-login flags generated with DEFAULT seed or without session pass acceptor validation."""
    with bank_app.app.test_request_context('/login'):
        # Generate pre-login SQLi flag without session
        prelogin_flag = bank_app.get_flag('sqli_login')
        assert prelogin_flag.startswith('FLAG{SQLi_Auth_Byp4ss_L0g1n_V1ct0ry_')

    # Test that flag_acceptor dashboard accepts this pre-login flag for a student 'INT-TEST123'
    client = acceptor.app.test_client()
    with client.session_transaction() as sess:
        sess['intern_id'] = 'INT-TEST123'

    res = client.post('/dashboard', data={'flag': prelogin_flag}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Correct! You solved: SQLi #1: Auth Bypass on Login Form!" in res.data or b"already submitted" in res.data

def test_cookie_persisted_intern_id(tmp_path):
    """Test that setting intern_id cookie in bank_app makes pre-login flags student-specific."""
    client = bank_app.app.test_client()
    client.set_cookie('intern_id', 'INT-COOKIE99')

    with bank_app.app.test_request_context('/login', headers={'Cookie': 'intern_id=INT-COOKIE99'}):
        flag = bank_app.get_flag('sqli_login')
        expected_flag = acceptor.generate_student_flag('sqli_login', 'INT-COOKIE99')
        assert flag == expected_flag
