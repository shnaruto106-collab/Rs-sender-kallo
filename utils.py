import aiohttp
import re
import random
import string
import asyncio

async def send_reset(target):
    """
    Instagram Password Reset via Web API (V1)
    """
    url = "https://www.instagram.com/api/v1/accounts/send_recovery_flow_email/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://instagram.com/accounts/password/reset/",
        "Origin": "https://instagram.com",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # Input চেক (ইমেইল নাকি ইউজারনেম)
    is_email = "@" in target
    data = {
        "email": target if is_email else "",
        "username": target if not is_email else "",
        "user_id": "",
        "query": target
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers, timeout=20) as response:
                status = response.status
                text = await response.text()
                
                # FadeHost লগে দেখার জন্য
                print(f"DEBUG: {status} - {text[:100]}")

                if status in [200, 201]:
                    return "success"
                elif status == 404:
                    return "error:not_found"
                elif status == 429:
                    return "error:rate_limited"
                elif "<!doctype html>" in text.lower():
                    return "error:ip_blocked"
                else:
                    return f"error:{status}"

    except asyncio.TimeoutError:
        return "error:timeout"
    except Exception as e:
        return f"error:{str(e)[:15]}"
