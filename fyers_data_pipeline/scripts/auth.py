import os
import sys
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def generate_token():
    config_path = os.path.join(os.getcwd(), "config/.env")
    load_dotenv(config_path)
    
    client_id = os.getenv("FYERS_CLIENT_ID")
    secret_key = os.getenv("FYERS_SECRET_KEY")
    redirect_url = os.getenv("FYERS_REDIRECT_URL")
    
    print("--- Fyers Authentication Tool ---")
    if not all([client_id, secret_key, redirect_url]):
        print("❌ Error: Missing credentials in config/.env")
        return

    # 1. Initialize session
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_url,
        response_type="code",
        grant_type="authorization_code"
    )
    
    # 2. Get the auth URL
    auth_url = session.generate_authcode()
    print(f"\n1. Click the link below to login to Fyers:\n{auth_url}")
    
    print("\n2. After logging in, you will be redirected to a page.")
    print("Copy the URL of that page and paste it here.")
    
    redirected_url = input("\nPaste the redirected URL: ").strip()
    
    # 3. Extract the auth_code from the URL
    try:
        if "auth_code=" in redirected_url:
            auth_code = redirected_url.split("auth_code=")[1].split("&")[0]
        else:
            auth_code = redirected_url
            
        # 4. Generate the access token
        session.set_token(auth_code)
        response = session.generate_token()
        
        if "access_token" in response:
            access_token = response["access_token"]
            token_path = os.path.join(os.getcwd(), "access_token.txt")
            with open(token_path, "w") as f:
                f.write(access_token)
            print(f"\n✅ Success! Token saved to: {token_path}")
        else:
            print(f"\n❌ Fyers API Error: {response}")
            
    except Exception as e:
        print(f"\n❌ Local Error: {e}")

if __name__ == "__main__":
    generate_token()
