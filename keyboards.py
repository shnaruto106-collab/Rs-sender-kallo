from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import database as db

def main_menu(is_owner=False, is_admin=False):
    kb = [
        [InlineKeyboardButton("🔁 Send Reset", callback_data="reset_start")],
        [InlineKeyboardButton("💎 Buy Plan", callback_data="buy_plan"),
         InlineKeyboardButton("📊 My Stats", callback_data="my_stats")],
        [InlineKeyboardButton("💳 Credit", callback_data="my_credit"),
         InlineKeyboardButton("🎟 Redeem Coupon", callback_data="redeem_start")],
    ]
    if is_admin or is_owner:
        kb.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel")])
    if is_owner:
        kb.append([InlineKeyboardButton("👑 Owner Panel", callback_data="owner_panel")])
    return InlineKeyboardMarkup(kb)

def back(target="home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=target)]])

def owner_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Manage User", callback_data="own_user")],
        [InlineKeyboardButton("💎 Plans", callback_data="own_plans"),
         InlineKeyboardButton("🎟 Coupons", callback_data="own_coupons")],
        [InlineKeyboardButton("⚙️ Daily Limit", callback_data="own_daily"),
         InlineKeyboardButton("⏱ Cooldown", callback_data="own_cool")],
        [InlineKeyboardButton("👤 Admins", callback_data="own_admins"),
         InlineKeyboardButton("📢 Force-Sub", callback_data="own_fs")],
        [InlineKeyboardButton("📥 Pending Requests", callback_data="own_pending")],
        [InlineKeyboardButton("📈 Stats", callback_data="own_stats")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")],
    ])

def admin_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="adm_stats")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")],
    ])

def user_manage_panel(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Credit", callback_data=f"u_cred_add:{uid}"),
         InlineKeyboardButton("➖ Rm Credit", callback_data=f"u_cred_rm:{uid}")],
        [InlineKeyboardButton("✏️ Set Credit", callback_data=f"u_cred_set:{uid}")],
        [InlineKeyboardButton("📅 Set Daily Limit", callback_data=f"u_lim_set:{uid}")],
        [InlineKeyboardButton("♻️ Reset Limit", callback_data=f"u_lim_rst:{uid}")],
        [InlineKeyboardButton("🔄 Reset Today Count", callback_data=f"u_day_rst:{uid}")],
        [InlineKeyboardButton("🎁 Give Plan", callback_data=f"gift_menu:{uid}")],
        [InlineKeyboardButton("🚫 Ban", callback_data=f"u_ban:{uid}"),
         InlineKeyboardButton("✅ Unban", callback_data=f"u_unban:{uid}")],
        [InlineKeyboardButton("🔙 Back", callback_data="own_user")],
    ])

def buy_plan_menu():
    rows = []
    for pid, name, emoji, price, lim, cool, bonus in db.list_plans():
        lim_txt = "∞" if lim == -1 else f"{lim}/day"
        if price == 0:
            rows.append([InlineKeyboardButton(f"{emoji} {name} — {lim_txt} · FREE ✅",
                                              callback_data="plan_free_info")])
        else:
            rows.append([InlineKeyboardButton(f"{emoji} {name} — {lim_txt} · {price}💳",
                                              callback_data=f"plan_buy:{pid}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def plan_request_kb(rid):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"plan_ok:{rid}"),
        InlineKeyboardButton("❌ Reject",  callback_data=f"plan_no:{rid}"),
    ]])

def owner_plans_menu():
    rows = [[InlineKeyboardButton("➕ Add Plan", callback_data="plan_add")]]
    for pid, name, emoji, price, lim, cool, bonus in db.list_plans():
        rows.append([InlineKeyboardButton(f"✏️ {emoji} {name}", callback_data=f"plan_edit:{pid}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="owner_panel")])
    return InlineKeyboardMarkup(rows)

def plan_edit_menu(pid):
    fields = [("name","📝 Name"),("emoji","😀 Emoji"),("price","💳 Price"),
              ("daily_limit","📅 Daily Limit"),("cooldown","⏱ Cooldown(h)"),
              ("bonus","🎁 Bonus")]
    rows = [[InlineKeyboardButton(label, callback_data=f"plan_field:{pid}:{f}")]
            for f, label in fields]
    rows.append([InlineKeyboardButton("🗑 Delete", callback_data=f"plan_del:{pid}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="own_plans")])
    return InlineKeyboardMarkup(rows)

def gift_plan_menu(uid):
    rows = []
    for pid, name, emoji, *_ in db.list_plans():
        rows.append([InlineKeyboardButton(f"{emoji} {name}", callback_data=f"gift:{uid}:{pid}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data=f"manage:{uid}")])
    return InlineKeyboardMarkup(rows)

def owner_coupons_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Generate Coupon", callback_data="cpn_gen")],
        [InlineKeyboardButton("📋 List Coupons", callback_data="cpn_list"),
         InlineKeyboardButton("📊 Stats", callback_data="cpn_stats")],
        [InlineKeyboardButton("🗑 Revoke", callback_data="cpn_revoke")],
        [InlineKeyboardButton("🔙 Back", callback_data="owner_panel")],
    ])

def coupon_result_kb(code):
    share_text = f"🎟 Coupon: {code}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Share to Channel",
            url=f"https://t.me/share/url?url={share_text}&text=Grab%20it%20fast!")],
        [InlineKeyboardButton("✅ Done", callback_data="cpn_done")],
    ])
