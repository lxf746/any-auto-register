import sys, io, json, time, re
import requests as req
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from platforms.kiro.core import KiroRegister

# Create tempy.email mailbox
resp = req.post("https://tempy.email/api/v1/mailbox", json={}, timeout=15)
email = resp.json()["email"]
print(f"Email: {email}")

r = KiroRegister(tag="KIRO")
redir = r.step1_kiro_init(); r.step2_get_wsh(redir)
r.step3_signin_flow(email); r.step4_signup_flow(email)
r.step5_get_tes_token(); r.step6_profile_load()
time.sleep(3)
resp7 = r.step7_send_otp(email)
if resp7 is None: print("send-otp FAILED"); sys.exit(1)

# Wait for OTP
start = time.time()
otp = None
while time.time() - start < 90:
    msgs_r = req.get(f"https://tempy.email/api/v1/mailbox/{email}/messages", timeout=15)
    if msgs_r.status_code == 200:
        for msg in msgs_r.json().get("messages", []):
            body = str(msg.get("body_text", "")) or str(msg.get("text", "")) or str(msg.get("html", ""))
            m = re.search(r"(?<!#)(?<!\d)(\d{6})(?!\d)", body)
            if m: otp = m.group(1); break
    if otp: break
    time.sleep(3)
if not otp: print("No OTP"); sys.exit(1)
print(f"OTP: {otp}")

identity = r.step8_create_identity(otp, email, "KIRO Tester")
sr = r.step9_signup_registration(identity["registrationCode"], identity["signInState"])
pwd_state = r.step10_set_password("KiroAuto123!", email, sr)
login_res = r.step11_final_login(email, pwd_state)
print(f"Step 11 done!")

tokens = r.step12_get_tokens()
if tokens:
    print(f"\n✅ Tokens obtained:")
    for k, v in tokens.items():
        val = str(v)[:60]
        print(f"  {k}={val}")
    # Try step 12f: OIDC device auth → refreshToken
    print(f"\n--- Step 12f: Device Auth ---")
    token_id = tokens.get("accessToken", "")
    bearer = tokens.get("sessionToken", "")
    ref = r.step12f_device_auth(bearer)
    if ref:
        print(f"\n✅ Refresh token obtained: {str(ref.get('refreshToken',''))[:60]}")
    else:
        print(f"\n⚠️ Step 12f failed (non-critical for Q&A)")
else:
    print(f"\n⚠️ Token fetch failed (account still created)")
