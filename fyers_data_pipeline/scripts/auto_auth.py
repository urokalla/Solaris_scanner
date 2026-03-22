import os, sys, time, requests, pyotp, ssl, urllib3
from fyers_apiv3 import fyersModel; from dotenv import load_dotenv
from requests.adapters import HTTPAdapter; from urllib3.poolmanager import PoolManager
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context(); ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx; return super().init_poolmanager(*args, **kwargs)

def get_access_token():
    load_dotenv(os.path.join(os.getcwd(), "config/.env"))
    creds = {k: os.getenv(f"FYERS_{k}") for k in ["CLIENT_ID", "SECRET_KEY", "REDIRECT_URL", "USERNAME", "PIN", "TOTP_KEY"]}
    if not all(creds.values()): return print("❌ Missing credentials")
    
    session = fyersModel.SessionModel(client_id=creds["CLIENT_ID"], secret_key=creds["SECRET_KEY"], redirect_uri=creds["REDIRECT_URL"], response_type="code", grant_type="authorization_code")
    s = requests.Session(); s.mount('https://', TLSAdapter()); headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        # Step 1: GET Handshake
        url1 = f"https://api.fyers.in/api/v3/login/step1?fy_id={creds['USERNAME']}&app_id=2"
        r1_raw = s.get(url1, headers=headers, verify=False)
        try: r1 = r1_raw.json()
        except: return print(f"❌ Step 1 (BAD JSON): {r1_raw.status_code} - {r1_raw.text[:300]}")
        if r1.get('s') != 'ok': return print(f"❌ Step 1 (FYERS ERR): {r1}")
        
        # Step 2: POST Credentials
        r2_raw = s.post("https://api.fyers.in/api/v3/login/step2", json={"request_key": r1['request_key'], "pasword": creds["PIN"], "totp": pyotp.TOTP(creds["TOTP_KEY"]).now()}, headers=headers, verify=False)
        try: r2 = r2_raw.json()
        except: return print(f"❌ Step 2 (BAD JSON): {r2_raw.status_code} - {r2_raw.text[:300]}")
        if r2.get('s') != 'ok': return print(f"❌ Step 2 (FYERS ERR): {r2}")
        
        # Step 3: Auth Code Generation
        headers["Authorization"] = f"Bearer {r2['data']['token_v3']}"
        r3_raw = s.post("https://api.fyers.in/api/v3/token", json={"fyers_id": creds["USERNAME"], "app_id": creds["CLIENT_ID"][:-4], "redirect_uri": creds["REDIRECT_URL"], "appType": "100", "response_type": "code", "create_cookie": True}, headers=headers, verify=False)
        try: r3 = r3_raw.json()
        except: return print(f"❌ Step 3 (BAD JSON): {r3_raw.status_code} - {r3_raw.text[:300]}")
        
        auth_code = r3.get('Url', '').split('auth_code=')[-1].split('&')[0]
        if not auth_code: return print(f"❌ Step 3 (AUTH CODE NULL): {r3}")
        
        session.set_token(auth_code)
        resp = session.generate_token()
        if "access_token" in resp:
            token_path = "access_token.txt" # Relative to /app in container mapping
            with open(token_path, "w") as f: f.write(resp["access_token"])
            print(f"✅ Success! Token saved to {token_path}")
        else: print(f"❌ Final: {resp}")
    except Exception as e: print(f"❌ Exception: {e}")

if __name__ == "__main__": get_access_token()
