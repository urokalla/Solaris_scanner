from selenium import webdriver
from selenium.webdriver.chrome.options import Options; from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait; from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager; from selenium.webdriver.chrome.service import Service
import pyotp, urllib.parse as urlparse, fyers_apiv3.fyersModel as fyersModel

def run_automated_login(self):
    auth_code = get_auth_code_headless(self)
    session = fyersModel.SessionModel(client_id=self.client_id, secret_key=self.secret_key, redirect_uri=self.redirect_url, response_type="code", grant_type="authorization_code")
    session.set_token(auth_code); res = session.generate_token()
    if "access_token" in res:
        with open(self.token_file, "w") as f: f.write(res["access_token"])
        return res["access_token"]
    raise Exception(f"Token fail: {res}")

def get_auth_code_headless(self):
    opts = Options(); opts.add_argument("--headless"); opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts); wait = WebDriverWait(driver, 20)
    try:
        url = fyersModel.SessionModel(client_id=self.client_id, redirect_uri=self.redirect_url, response_type="code", grant_type="authorization_code").generate_authcode()
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.ID, "login_client_id"))).send_keys(self.username)
        driver.find_element(By.ID, "clientIdSubmit").click()
        totp = pyotp.TOTP(self.totp_key.replace(" ", "")).now()
        wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="otp-container"]/input[1]'))).send_keys(totp)
        driver.find_element(By.ID, "confirmOtpSubmit").click()
        pins = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "pin-input")))
        for i, d in enumerate(self.pin): pins[i].send_keys(d)
        driver.find_element(By.ID, "verifyPinSubmit").click()
        wait.until(lambda d: self.redirect_url in d.current_url)
        return urlparse.parse_qs(urlparse.urlparse(driver.current_url).query)['auth_code'][0]
    finally: driver.quit()
