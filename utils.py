import requests
import uuid
import secrets
import base64
import datetime
import asyncio

def _check_instagram_sync(email):
    dev_uuid     = str(uuid.uuid4())
    fam_uuid     = str(uuid.uuid4())
    android_id   = 'android-' + secrets.token_hex(8)
    qe_device_id = str(uuid.uuid4())
    ts           = str(int(datetime.datetime.now().timestamp()))
    tz_offset    = str(datetime.datetime.now().astimezone().utcoffset().total_seconds())

    payload_json = (
        '{"client_input_params":{"aac":"{\\"aac_init_timestamp\\":' + ts +
        ',\\"aacjid\\":\\"' + str(uuid.uuid4()) +
        '\\",\\"aaccs\\":\\"' + secrets.token_urlsafe(32) +
        '\\"}","flash_call_permissions_status":{"READ_PHONE_STATE":"PERMANENTLY_DENIED",'
        '"READ_CALL_LOG":"DENIED","ANSWER_PHONE_CALLS":"DENIED"},'
        '"was_headers_prefill_available":0,"network_bssid":null,"sfdid":"",'
        '"fetched_email_token_list":{},"search_query":"' + email + '",'
        '"auth_secure_device_id":"","ig_oauth_token":[],"cloud_trust_token":null,'
        '"was_headers_prefill_used":0,"sso_accounts_auth_data":[],'
        '"encrypted_msisdn":"","device_network_info":null,"text_input_id":"akyuf0:61",'
        '"zero_balance_state":null,"android_build_type":"release","accounts_list":[],'
        '"is_oauth_without_permission":0,"ig_android_qe_device_id":"' + qe_device_id + '",'
        '"gms_incoming_call_retriever_eligibility":"client_not_supported",'
        '"search_screen_type":"email_or_username","is_whatsapp_installed":1,'
        '"lois_settings":{"lois_token":""},"ig_vetted_device_nonce":null,'
        '"headers_infra_flow_id":"","fetched_email_list":[]},'
        '"server_params":{"event_request_id":"' + str(uuid.uuid4()) + '",'
        '"is_from_logged_out":0,"layered_homepage_experiment_group":null,'
        '"device_id":"' + android_id + '","login_surface":"login_home",'
        '"waterfall_id":"' + str(uuid.uuid4()) + '",'
        '"INTERNAL__latency_qpl_instance_id":6.3987980400102E13,'
        '"is_platform_login":0,"context_data":"","login_entry_point":"logged_out",'
        '"INTERNAL__latency_qpl_marker_id":36707139,'
        '"family_device_id":"' + fam_uuid + '",'
        '"offline_experiment_group":"caa_iteration_v3_perf_ig_4",'
        '"access_flow_version":"pre_mt_behavior","is_from_logged_in_switcher":0,'
        '"qe_device_id":"' + qe_device_id + '"}}'
    )

    data = {
        'params': payload_json,
        'bk_client_context': '{"bloks_version":"5e47baf35c5a270b44c8906c8b99063564b30ef69779f3dee0b828bee2e4ef5b","styles_id":"instagram"}',
        'bloks_versioning_id': '5e47baf35c5a270b44c8906c8b99063564b30ef69779f3dee0b828bee2e4ef5b'
    }
    headers = {
        'User-Agent': 'Instagram 370.1.0.43.96 Android (34/14; 450dpi; 1080x2207; samsung; SM-A235F; a23; qcom; en_IN; 704872281)',
        'accept-language': 'en-IN, en-US',
        'x-bloks-version-id': '5e47baf35c5a270b44c8906c8b99063564b30ef69779f3dee0b828bee2e4ef5b',
        'x-fb-friendly-name': 'IgApi: bloks/async_action/com.bloks.www.caa.ar.search.async/',
        'x-ig-android-id': android_id,
        'x-ig-app-id': '567067343352427',
        'x-ig-app-locale': 'en_IN',
        'x-ig-client-endpoint': 'com.bloks.www.caa.ar.search',
        'x-ig-device-id': dev_uuid,
        'x-ig-family-device-id': fam_uuid,
        'x-ig-timezone-offset': tz_offset,
        'x-mid': base64.urlsafe_b64encode(secrets.token_bytes(18)).decode().rstrip('='),
        'x-pigeon-rawclienttime': ts,
        'x-pigeon-session-id': f'UFS-{uuid.uuid4()}-0',
    }
    url = 'https://i.instagram.com/api/v1/bloks/async_action/com.bloks.www.caa.ar.search.async/'
    
    try:
        # এখানে প্রতিটা রিকোয়েস্টের জন্য আলাদা সেশন তৈরি হয়, তাই একসাথে অনেক রিকোয়েস্ট গেলেও আটকে যায় না
        with requests.Session() as session:
            resp = session.post(url, data=data, headers=headers, timeout=20)
            if resp.status_code == 429: return "error:rate_limited"
            elif resp.status_code == 403: return "error:ip_blocked"
            elif email.lower() in resp.text.lower(): return "success"
            else: return "error:not_found"
    except requests.exceptions.Timeout:
        return "error:timeout"
    except Exception:
        return "error:unknown"

async def send_reset(target):
    """
    Async Wrapper: এটি বটকে ব্লক হতে দেবে না এবং 
    প্রতিটি ইউজারের রিকোয়েস্ট আলাদা থ্রেডে পাঠাবে।
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _check_instagram_sync, target)
