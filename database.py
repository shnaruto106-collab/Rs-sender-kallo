import sqlite3, threading, time, secrets, string
from contextlib import contextmanager

DB_PATH = "reset_bot.db"
_lock = threading.Lock()

@contextmanager
def db():
    c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    try:
        yield c
        c.commit()
    finally:
        c.close()

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            joined_at INTEGER, is_banned INTEGER DEFAULT 0, credit INTEGER DEFAULT 0,
            daily_limit INTEGER, last_reset INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, target TEXT, result TEXT, created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS daily (
            user_id INTEGER, day TEXT, count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, day)
        );
        CREATE TABLE IF NOT EXISTS force_subs (chat_id TEXT PRIMARY KEY, name TEXT, url TEXT);
        CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT);
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, emoji TEXT,
            price INTEGER, daily_limit INTEGER, cooldown INTEGER, bonus INTEGER
        );
        CREATE TABLE IF NOT EXISTS user_plans (
            user_id INTEGER PRIMARY KEY, plan_id INTEGER, activated INTEGER
        );
        CREATE TABLE IF NOT EXISTS plan_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan_id INTEGER,
            status TEXT DEFAULT 'pending', created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS coupons (
            code TEXT PRIMARY KEY, credit INTEGER, expiry INTEGER,
            created_by INTEGER, created_at INTEGER,
            used_by INTEGER DEFAULT NULL, used_at INTEGER DEFAULT NULL,
            revoked INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_coupons_used ON coupons(used_by);
        """)

# ---------- settings ----------
def get_setting(k, default=None):
    with db() as c:
        r = c.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
        return r[0] if r else default
def set_setting(k, v):
    with _lock, db() as c:
        c.execute("INSERT INTO settings (k,v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=?", (k, v, v))
def get_daily_limit():   return int(get_setting("daily_limit", 15))
def set_daily_limit(n):  set_setting("daily_limit", str(n))
def get_cooldown():      return int(get_setting("cooldown", 24))
def set_cooldown(h):     set_setting("cooldown", str(h))

# ---------- users ----------
def save_user(uid, uname, fname):
    with _lock, db() as c:
        c.execute("""INSERT INTO users (user_id,username,first_name,joined_at) VALUES (?,?,?,?)
                     ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,
                     first_name=excluded.first_name""",
                  (uid, uname or "", fname or "", int(time.time())))
def get_user(uid):
    with db() as c: return c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
def is_banned(uid):
    r = get_user(uid); return bool(r and r[4])
def set_ban(uid, v):
    with _lock, db() as c: c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (v, uid))
def get_credit(uid):
    r = get_user(uid); return r[5] if r else 0
def add_credit(uid, n):
    with _lock, db() as c: c.execute("UPDATE users SET credit=credit+? WHERE user_id=?", (n, uid))
def remove_credit(uid, n):
    with _lock, db() as c: c.execute("UPDATE users SET credit=MAX(credit-?,0) WHERE user_id=?", (n, uid))
def set_credit(uid, n):
    with _lock, db() as c: c.execute("UPDATE users SET credit=? WHERE user_id=?", (n, uid))
def get_user_limit(uid):
    r = get_user(uid)
    if r and r[6] is not None: return r[6]
    return get_daily_limit()
def set_user_limit(uid, n):
    with _lock, db() as c: c.execute("UPDATE users SET daily_limit=? WHERE user_id=?", (n, uid))
def reset_user_limit(uid):
    with _lock, db() as c: c.execute("UPDATE users SET daily_limit=NULL WHERE user_id=?", (uid,))
def get_last_reset(uid):
    r = get_user(uid); return r[7] if r else 0
def set_last_reset(uid, ts):
    with _lock, db() as c: c.execute("UPDATE users SET last_reset=? WHERE user_id=?", (ts, uid))

def today(): return time.strftime("%Y-%m-%d")
def daily_count(uid):
    with db() as c:
        r = c.execute("SELECT count FROM daily WHERE user_id=? AND day=?", (uid, today())).fetchone()
        return r[0] if r else 0
def set_daily_count(uid, n):
    with _lock, db() as c:
        c.execute("""INSERT INTO daily (user_id,day,count) VALUES (?,?,?)
                     ON CONFLICT(user_id,day) DO UPDATE SET count=?""", (uid, today(), n, n))
def inc_daily(uid):
    with _lock, db() as c:
        c.execute("""INSERT INTO daily (user_id,day,count) VALUES (?,?,1)
                     ON CONFLICT(user_id,day) DO UPDATE SET count=count+1""", (uid, today()))
def log_reset(uid, target, result):
    with _lock, db() as c:
        c.execute("INSERT INTO resets (user_id,target,result,created_at) VALUES (?,?,?,?)",
                  (uid, target, result, int(time.time())))
def get_all_users():
    with db() as c: return [r[0] for r in c.execute("SELECT user_id FROM users").fetchall()]

# ---------- admins ----------
def add_admin(uid):
    with _lock, db() as c: c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (uid,))
def remove_admin(uid):
    with _lock, db() as c: c.execute("DELETE FROM admins WHERE user_id=?", (uid,))
def is_admin(uid):
    with db() as c: return c.execute("SELECT 1 FROM admins WHERE user_id=?", (uid,)).fetchone() is not None
def list_admins():
    with db() as c: return [r[0] for r in c.execute("SELECT user_id FROM admins").fetchall()]

# ---------- force-sub ----------
def add_force_sub(chat_id, name, url):
    with _lock, db() as c:
        c.execute("""INSERT INTO force_subs (chat_id,name,url) VALUES (?,?,?)
                     ON CONFLICT(chat_id) DO UPDATE SET name=?,url=?""", (chat_id, name, url, name, url))
def remove_force_sub(chat_id):
    with _lock, db() as c: c.execute("DELETE FROM force_subs WHERE chat_id=?", (chat_id,))
def get_force_subs():
    with db() as c: return c.execute("SELECT chat_id,name,url FROM force_subs").fetchall()

# ---------- plans ----------
DEFAULT_PLANS = [
    ("Basic",     "🥉", 0,    15, 24, 0),
    ("Standard",  "🥈", 50,   22, 24, 5),
    ("Premium",   "🥇", 150,  32, 12, 20),
    ("Pro",       "💠", 300,  46, 6,  50),
    ("VIP",       "👑", 600,  67, 3,  100),
    ("Unlimited", "⚡", 1500, -1, 0,  200),
]
def seed_plans(force=False):
    with _lock, db() as c:
        n = c.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
        if n == 0 or force:
            if force: c.execute("DELETE FROM plans")
            for p in DEFAULT_PLANS:
                c.execute("INSERT INTO plans (name,emoji,price,daily_limit,cooldown,bonus) "
                          "VALUES (?,?,?,?,?,?)", p)
def list_plans():
    with db() as c:
        return c.execute("SELECT id,name,emoji,price,daily_limit,cooldown,bonus "
                         "FROM plans ORDER BY price").fetchall()
def get_plan(pid):
    with db() as c:
        return c.execute("SELECT id,name,emoji,price,daily_limit,cooldown,bonus "
                         "FROM plans WHERE id=?", (pid,)).fetchone()
def add_plan(name, emoji, price, daily_limit, cooldown, bonus):
    with _lock, db() as c:
        c.execute("INSERT INTO plans (name,emoji,price,daily_limit,cooldown,bonus) "
                  "VALUES (?,?,?,?,?,?)", (name, emoji, price, daily_limit, cooldown, bonus))
def edit_plan(pid, field, value):
    allowed = {"name","emoji","price","daily_limit","cooldown","bonus"}
    if field not in allowed: return
    with _lock, db() as c: c.execute(f"UPDATE plans SET {field}=? WHERE id=?", (value, pid))
def delete_plan(pid):
    with _lock, db() as c: c.execute("DELETE FROM plans WHERE id=?", (pid,))

def get_user_plan(uid):
    with db() as c:
        return c.execute("""SELECT p.id,p.name,p.emoji,p.daily_limit,p.cooldown,p.bonus
                            FROM user_plans up JOIN plans p ON p.id=up.plan_id
                            WHERE up.user_id=?""", (uid,)).fetchone()
def set_user_plan(uid, pid):
    with _lock, db() as c:
        c.execute("""INSERT INTO user_plans (user_id,plan_id,activated) VALUES (?,?,?)
                     ON CONFLICT(user_id) DO UPDATE SET plan_id=?,activated=?""",
                  (uid, pid, int(time.time()), pid, int(time.time())))

def create_request(uid, pid):
    with _lock, db() as c:
        c.execute("INSERT INTO plan_requests (user_id,plan_id,created_at) VALUES (?,?,?)",
                  (uid, pid, int(time.time())))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]
def get_request(rid):
    with db() as c:
        return c.execute("SELECT id,user_id,plan_id,status FROM plan_requests WHERE id=?", (rid,)).fetchone()
def update_request(rid, status):
    with _lock, db() as c: c.execute("UPDATE plan_requests SET status=? WHERE id=?", (status, rid))
def pending_requests():
    with db() as c:
        return c.execute("""SELECT r.id,r.user_id,p.name,p.emoji FROM plan_requests r
                            JOIN plans p ON p.id=r.plan_id
                            WHERE r.status='pending' ORDER BY r.created_at""").fetchall()

def effective_limit(uid):
    p = get_user_plan(uid)
    if p and p[3] != -1: return p[3]
    if p and p[3] == -1: return 999999
    return get_user_limit(uid)
def effective_cooldown(uid):
    p = get_user_plan(uid)
    if p: return p[4]
    return get_cooldown()

# ---------- coupons ----------
def _gen_code(length=10):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def create_coupon(credit, expiry_hours, created_by):
    with _lock, db() as c:
        for _ in range(20):
            code = _gen_code()
            try:
                c.execute("INSERT INTO coupons (code,credit,expiry,created_by,created_at) "
                          "VALUES (?,?,?,?,?)",
                          (code, credit,
                           int(time.time()) + expiry_hours * 3600,
                           created_by, int(time.time())))
                return code
            except sqlite3.IntegrityError:
                continue
        raise RuntimeError("Could not generate unique code")

def get_coupon(code):
    with db() as c:
        return c.execute("""SELECT code,credit,expiry,used_by,used_at,revoked
                            FROM coupons WHERE code=?""", (code.upper(),)).fetchone()

def redeem_coupon(code, uid):
    code = code.strip().upper()
    with _lock, db() as c:
        r = c.execute("""SELECT credit,expiry,used_by,revoked
                         FROM coupons WHERE code=?""", (code,)).fetchone()
        if not r: return ("not_found", 0)
        credit, expiry, used_by, revoked = r
        if revoked: return ("revoked", 0)
        if used_by is not None: return ("used", 0)
        if int(time.time()) > expiry: return ("expired", 0)
        c.execute("""UPDATE coupons SET used_by=?, used_at=?
                     WHERE code=? AND used_by IS NULL""",
                  (uid, int(time.time()), code))
        if c.total_changes == 0: return ("used", 0)
        c.execute("UPDATE users SET credit=credit+? WHERE user_id=?", (credit, uid))
        return ("ok", credit)

def list_coupons(limit=30):
    with db() as c:
        return c.execute("""SELECT code,credit,expiry,used_by,revoked
                            FROM coupons ORDER BY created_at DESC LIMIT ?""",
                         (limit,)).fetchall()
def revoke_coupon(code):
    with _lock, db() as c:
        c.execute("UPDATE coupons SET revoked=1 WHERE code=? AND used_by IS NULL",
                  (code.upper(),))
def coupon_stats():
    with db() as c:
        now = int(time.time())
        total   = c.execute("SELECT COUNT(*) FROM coupons").fetchone()[0]
        used    = c.execute("SELECT COUNT(*) FROM coupons WHERE used_by IS NOT NULL").fetchone()[0]
        active  = c.execute("SELECT COUNT(*) FROM coupons WHERE used_by IS NULL AND revoked=0 AND expiry>?", (now,)).fetchone()[0]
        expired = c.execute("SELECT COUNT(*) FROM coupons WHERE used_by IS NULL AND revoked=0 AND expiry<=?", (now,)).fetchone()[0]
        return {"total": total, "used": used, "active": active, "expired": expired}
