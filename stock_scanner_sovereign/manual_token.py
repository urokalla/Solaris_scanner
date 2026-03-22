import os
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv

def manual_auth():
    # Load credentials from the standard .env location
    local_env = os.path.join(os.path.dirname(__file__), ".env")
    pipeline_env = os.path.join(os.path.dirname(__file__), "..", "fyers_data_pipeline", "config", ".env")
    
    env_path = local_env if os.path.exists(local_env) else pipeline_env
    load_dotenv(env_path)
    
    client_id = os.getenv("FYERS_CLIENT_ID")
    secret_key = os.getenv("FYERS_SECRET_KEY")
    redirect_url = os.getenv("FYERS_REDIRECT_URL")
    
    if not all([client_id, secret_key, redirect_url]):
        print("❌ Error: Missing credentials in .env")
        print(f"Checked path: {env_path}")
        return

    # Initialize Fyers Session
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_url,
        response_type="code",
        grant_type="authorization_code"
    )
    
    # Generate the Auth URL
    auth_url = session.generate_authcode()
    print("\n" + "="*60)
    print("STEP 1: Copy and paste this URL into your browser:")
    print("-" * 60)
    print(auth_url)
    print("-" * 60)
    
    print("\nSTEP 2: Log in. After login, you will be redirected to a blank page.")
    print("Copy the ENTIRE URL from the address bar (it contains 'auth_code=...')")
    
    redirected_url = input("\nSTEP 3: Paste the redirected URL here: ").strip()
    
    if not redirected_url:
        print("❌ Error: URL cannot be empty.")
        return

    try:
        # Extract auth_code
        if "auth_code=" in redirected_url:
            auth_code = redirected_url.split("auth_code=")[1].split("&")[0]
        else:
            auth_code = redirected_url
            
        # Optional: verify length
        if len(auth_code) < 10:
            print(f"❌ Error: Invalid auth code extracted: {auth_code}")
            return

        # Exchange code for access token
        session.set_token(auth_code)
        response = session.generate_token()
        
        if "access_token" in response:
            token = response["access_token"]
            # Save to the specific path expected by the scanner
            token_file = os.path.join(os.path.dirname(__file__), "access_token.txt")
            with open(token_file, "w") as f:
                f.write(token)
            print("\n" + "="*60)
            print(f"✅ SUCCESS! Access Token saved to: {token_file}")
            print("The 'sovereign_scanner' container will now be able to start.")
            print("="*60)
        else:
            print(f"\n❌ Fyers API Error: {response}")
            
    except Exception as e:
        print(f"\n❌ Local Error: {e}")

if __name__ == "__main__":
    manual_auth()
