import requests
import uuid
import random
import string
import re
import time

PROXIES = [None]

def send_reset(target):
    proxy = random.choice(PROXIES)
    proxies = {"http": proxy, "https": proxy} if proxy else None

    url = "https://i.instagram.com/api/v2/accounts/send_password_reset/"
    
    data = {
        "_csrftoken": "".join(random.choices(string.ascii_letters + string.digits, k=32)),
        "username": target,
        "guid": str(uuid.uuid4()),
        "device_id": str(uuid.uuid4())
    }
    
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

    time.sleep(random.uniform(1.0, 3.0))

    try:
        response = requests.post(url, headers=headers, data=data, proxies=proxies, timeout=20)
        text = response.text.lower()

        # 🚨 DEBUG লাইন
        print(f"DEBUG: {response.status_code} - {response.text}") 

        if "obfuscated_email" in text:
            ev = re.search(r'[a-zA-Z0-9\*\._%+-]+@[a-zA-Z0-9\.-]+\.[a-zA-Z]{2,}', response.text)
            if ev: return f"email:{ev.group(0)}"
            return "phone"
        elif response.status_code == 404 or "not found" in text:
            return "error:not_found"
        elif "rate limit" in text or response.status_code == 429:
            return "error:rate_limited"
        elif "obfuscated_phone" in text:
            return "phone"
        else:
            return f"error:{response.status_code}"

    except Exception as e:
        return f"error:{str(e)[:15]}"
