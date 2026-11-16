import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "9019122585:AAEb-HXkGWB5IlyNlnauJunyaZWznWGvSCE")
OWNER_ID  = int(os.getenv("OWNER_ID", "8635902333"))

# Default global limits (overridable inline by owner)
DEFAULT_MEMBER_DAILY_LIMIT = 15
DEFAULT_COOLDOWN_HOURS     = 24

# Coupon defaults
DEFAULT_COUPON_CREDIT    = 500
DEFAULT_COUPON_EXPIRY_H  = 24
MAX_COUPONS_PER_GENERATE = 20
