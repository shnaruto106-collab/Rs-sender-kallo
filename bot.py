import logging, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, filters)
from telegram.constants import ParseMode
import config as C
import database as db
import keyboards as kb
import utils as U

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

PENDING = {}
def is_owner(uid): return uid == C.OWNER_ID

# ---------- force-sub ----------
async def check_fs(bot, uid):
    missing = []
    for chat_id, name, url in db.get_force_subs():
        try:
            m = await bot.get_chat_member(chat_id, uid)
            if m.status in ("left", "kicked"): missing.append((name, url))
        except Exception: missing.append((name, url))
    return missing

def fs_kb(missing):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"📢 Join {n}", url=u)] for n, u in missing] +
        [[InlineKeyboardButton("✅ Joined", callback_data="fs_joined")]])

async def gate(update, ctx):
    u = update.effective_user
    if db.is_banned(u.id):
        await update.effective_message.reply_text("🚫 You are banned.")
        return False
    missing = await check_fs(ctx.bot, u.id)
    if missing:
        await update.effective_message.reply_text("⚠️ Join our channels first:",
                                                   reply_markup=fs_kb(missing))
        return False
    return True

# ---------- /start ----------
async def start(update, ctx):
    u = update.effective_user
    db.save_user(u.id, u.username, u.first_name)
    if not db.get_user_plan(u.id):
        basic = next((p for p in db.list_plans() if p[3] == 0), None)
        if basic: db.set_user_plan(u.id, basic[0])
    if not await gate(update, ctx): return
    p = db.get_user_plan(u.id)
    plan_line = f"{p[2]} *{p[1]}* · {('∞' if p[3]==-1 else p[3])}/day" if p else "none"
    await update.message.reply_text(
        f"👋 Hello *{u.first_name}*!\n\n"
        f"💎 Plan: {plan_line}\n"
        f"💳 Credit: *{db.get_credit(u.id)}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(is_owner(u.id), db.is_admin(u.id)))

# ---------- callback router ----------
async def on_cb(update, ctx):
    q = update.callback_query; await q.answer()
    u = q.from_user; d = q.data

    if d == "fs_joined":
        m = await check_fs(ctx.bot, u.id)
        await q.edit_message_text("✅ Verified!" if not m else "❌ Not joined all.",
                                   reply_markup=None if not m else fs_kb(m))
        return
    if db.is_banned(u.id):
        await q.edit_message_text("🚫 Banned."); return
    m = await check_fs(ctx.bot, u.id)
    if m:
        await q.edit_message_text("⚠️ Join channels first:", reply_markup=fs_kb(m)); return

    # ---- home ----
    if d == "home":
        await q.edit_message_text("🏠 Main Menu",
            reply_markup=kb.main_menu(is_owner(u.id), db.is_admin(u.id))); return

    # ---- reset ----
    if d == "reset_start":
        if not is_owner(u.id):
            if db.daily_count(u.id) >= db.effective_limit(u.id):
                await q.edit_message_text("⛔ Daily limit reached.", reply_markup=kb.back()); return
            cd = db.effective_cooldown(u.id) * 3600
            last = db.get_last_reset(u.id)
            if cd and last and time.time() - last < cd:
                left = int((cd - (time.time()-last))/60)
                await q.edit_message_text(f"⏱ Cooldown: *{left} min* left.",
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back()); return
        await q.edit_message_text("📧 Send the *email / username* to reset:",
                                   parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back())
        PENDING[u.id] = {"action": "reset"}; return

    # ---- my info ----
    if d == "my_stats":
        p = db.get_user_plan(u.id)
        if p:
            lim = "∞" if p[3] == -1 else p[3]
            plan_txt = f"{p[2]} *{p[1]}* — {lim}/day · {p[4]}h cd"
        else: plan_txt = "none"
        eff = db.effective_limit(u.id); eff_txt = "∞" if eff > 9999 else eff
        await q.edit_message_text(
            f"📊 *Your Stats*\n\n💎 Plan: {plan_txt}\n"
            f"📅 Used today: *{db.daily_count(u.id)}/{eff_txt}*\n"
            f"💳 Credit: *{db.get_credit(u.id)}*",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back()); return

    if d == "my_credit":
        await q.edit_message_text(f"💳 Credit: *{db.get_credit(u.id)}*",
                                   parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back()); return

    # ---- admin ----
    if d == "admin_panel" and (is_owner(u.id) or db.is_admin(u.id)):
        await q.edit_message_text("🛠 Admin Panel", reply_markup=kb.admin_panel()); return
    if d == "adm_stats":
        await q.edit_message_text(f"👥 Users: *{len(db.get_all_users())}*",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("admin_panel")); return

    # ---- buy plan ----
    if d == "buy_plan":
        await q.edit_message_text("💎 *Available Plans*\n\nChoose one. Owner approves requests.",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.buy_plan_menu()); return
    if d == "plan_free_info":
        await q.edit_message_text(
            "🥉 *Basic Plan — FREE*\n\nEvery member gets it automatically.\n"
            "📅 *15 resets/day* · ⏱ *24h cooldown*",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("buy_plan")); return

    if d.startswith("plan_buy:"):
        pid = int(d.split(":")[1]); p = db.get_plan(pid)
        if not p: await q.edit_message_text("Plan gone."); return
        cur = db.get_user_plan(u.id)
        if cur and p[3] <= cur[3]:
            await q.edit_message_text(
                f"⚠️ You already have *{cur[2]} {cur[1]}*. Choose a higher plan.",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("buy_plan")); return
        if db.get_credit(u.id) < p[3]:
            await q.edit_message_text(
                f"❌ Need *{p[3]}* credit. You have *{db.get_credit(u.id)}*.",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("buy_plan")); return
        rid = db.create_request(u.id, p[0])
        try:
            await ctx.bot.send_message(C.OWNER_ID,
                f"💎 *New Plan Request*\n\n👤 `{u.id}` ({u.first_name})\n"
                f"📦 {p[2]} *{p[1]}*\n💳 Cost: *{p[3]}*\n"
                f"📅 *{'∞' if p[4]==-1 else p[4]}* · ⏱ *{p[5]}h*",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.plan_request_kb(rid))
        except Exception as e: log.warning("notify: %s", e)
        await q.edit_message_text(f"⏳ Request sent for {p[2]} *{p[1]}*. Wait for approval.",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back()); return

    # ---- approve/reject ----
    if d.startswith("plan_ok:") and is_owner(u.id):
        rid = int(d.split(":")[1]); r = db.get_request(rid)
        if not r or r[3] != "pending": await q.edit_message_text("Already handled."); return
        tuid, pid = r[1], r[2]; p = db.get_plan(pid)
        if db.get_credit(tuid) < p[3]:
            await q.edit_message_text("⚠️ User no longer has enough credit."); return
        db.remove_credit(tuid, p[3]); db.set_user_plan(tuid, pid)
        if p[6]: db.add_credit(tuid, p[6])
        db.update_request(rid, "approved")
        await q.edit_message_text(f"✅ Approved for `{tuid}` — {p[2]} *{p[1]}*",
            parse_mode=ParseMode.MARKDOWN)
        try:
            await ctx.bot.send_message(tuid,
                f"🎉 Plan activated!\n{p[2]} *{p[1]}*\n"
                f"📅 *{'∞' if p[4]==-1 else p[4]}* · ⏱ *{p[5]}h*",
                parse_mode=ParseMode.MARKDOWN)
        except Exception: pass
        return
    if d.startswith("plan_no:") and is_owner(u.id):
        rid = int(d.split(":")[1]); r = db.get_request(rid)
        if not r or r[3] != "pending": await q.edit_message_text("Already handled."); return
        db.update_request(rid, "rejected")
        await q.edit_message_text("❌ Rejected.")
        try: await ctx.bot.send_message(r[1], "❌ Your plan request was rejected.")
        except Exception: pass
        return

    # ---- owner panel ----
    if d == "owner_panel" and is_owner(u.id):
        await q.edit_message_text("👑 *Owner Panel*", parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.owner_panel()); return
    if d == "own_stats":
        s = db.coupon_stats()
        await q.edit_message_text(
            f"📈 *Bot Stats*\n\n👥 Users: *{len(db.get_all_users())}*\n"
            f"⚙️ Daily limit: *{db.get_daily_limit()}*\n⏱ Cooldown: *{db.get_cooldown()}h*\n"
            f"📢 Force-Subs: *{len(db.get_force_subs())}*\n👤 Admins: *{len(db.list_admins())}*\n"
            f"💎 Plans: *{len(db.list_plans())}*\n"
            f"🎟 Coupons active: *{s['active']}* · used: *{s['used']}*\n"
            f"📥 Pending: *{len(db.pending_requests())}*",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("owner_panel")); return

    if d == "own_daily" and is_owner(u.id):
        await q.edit_message_text(f"⚙️ Global daily limit: *{db.get_daily_limit()}*\nSend new number:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("owner_panel"))
        PENDING[u.id] = {"action": "set_daily"}; return
    if d == "own_cool" and is_owner(u.id):
        await q.edit_message_text(f"⏱ Cooldown: *{db.get_cooldown()}h*\nSend new hours:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("owner_panel"))
        PENDING[u.id] = {"action": "set_cool"}; return

    if d == "own_user" and is_owner(u.id):
        await q.edit_message_text("👥 Send *user_id* to manage:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("owner_panel"))
        PENDING[u.id] = {"action": "pick_user"}; return

    if d == "own_pending" and is_owner(u.id):
        reqs = db.pending_requests()
        if not reqs:
            await q.edit_message_text("📥 No pending requests.", reply_markup=kb.back("owner_panel")); return
        for rid, tuid, pname, pemoji in reqs:
            try:
                await ctx.bot.send_message(u.id,
                    f"💎 Request #{rid}\n👤 `{tuid}` → {pemoji} *{pname}*",
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb.plan_request_kb(rid))
            except Exception: pass
        await q.edit_message_text("📥 Sent pending requests above.",
            reply_markup=kb.back("owner_panel")); return

    # ---- user manage ----
    if d.startswith("u_") and is_owner(u.id):
        parts = d.split(":"); act = parts[0]; target = int(parts[1])
        if act == "u_cred_add":   prompt, PENDING[u.id] = f"➕ Amount to ADD for `{target}`:",  {"action":"cred_add","target":target}
        elif act == "u_cred_rm":  prompt, PENDING[u.id] = f"➖ Amount to REMOVE for `{target}`:", {"action":"cred_rm","target":target}
        elif act == "u_cred_set": prompt, PENDING[u.id] = f"✏️ New credit VALUE for `{target}`:", {"action":"cred_set","target":target}
        elif act == "u_lim_set":  prompt, PENDING[u.id] = f"📅 New daily limit for `{target}`:", {"action":"lim_set","target":target}
        elif act == "u_lim_rst":
            db.reset_user_limit(target)
            await q.edit_message_text(f"✅ Limit reset for `{target}`",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.user_manage_panel(target)); return
        elif act == "u_day_rst":
            db.set_daily_count(target, 0)
            await q.edit_message_text(f"✅ Today's count reset for `{target}`",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.user_manage_panel(target)); return
        elif act == "u_ban":
            db.set_ban(target, 1)
            await q.edit_message_text(f"🚫 Banned `{target}`",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.user_manage_panel(target)); return
        elif act == "u_unban":
            db.set_ban(target, 0)
            await q.edit_message_text(f"✅ Unbanned `{target}`",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.user_manage_panel(target)); return
        else: return
        await q.edit_message_text(prompt, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.back(f"manage:{target}")); return

    if d.startswith("manage:") and is_owner(u.id):
        target = int(d.split(":")[1]); r = db.get_user(target)
        if not r: await q.edit_message_text("User not found.", reply_markup=kb.back("owner_panel")); return
        p = db.get_user_plan(target)
        plan_txt = f"{p[2]} {p[1]}" if p else "none"
        await q.edit_message_text(
            f"👤 *User* `{target}`\n\n💎 Plan: *{plan_txt}*\n"
            f"💳 Credit: *{db.get_credit(target)}*\n"
            f"📅 Daily: *{db.daily_count(target)}/{db.effective_limit(target)}*\n"
            f"🚫 Banned: *{'yes' if db.is_banned(target) else 'no'}*",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.user_manage_panel(target)); return

    # ---- gift plan ----
    if d.startswith("gift_menu:") and is_owner(u.id):
        target = int(d.split(":")[1])
        await q.edit_message_text("🎁 Choose plan to gift:",
            reply_markup=kb.gift_plan_menu(target)); return
    if d.startswith("gift:") and is_owner(u.id):
        _, uid_s, pid_s = d.split(":")
        target, pid = int(uid_s), int(pid_s)
        p = db.get_plan(pid)
        db.set_user_plan(target, pid)
        if p[6]: db.add_credit(target, p[6])
        await q.edit_message_text(f"🎁 Gave {p[2]} *{p[1]}* to `{target}`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.user_manage_panel(target))
        try:
            await ctx.bot.send_message(target,
                f"🎁 Owner gifted you {p[2]} *{p[1]}*!\n"
                f"📅 *{'∞' if p[4]==-1 else p[4]}* · ⏱ *{p[5]}h*",
                parse_mode=ParseMode.MARKDOWN)
        except Exception: pass
        return

    # ---- admin mgmt ----
    if d == "own_admins" and is_owner(u.id):
        k = [[InlineKeyboardButton("➕ Add", callback_data="adm_add"),
              InlineKeyboardButton("➖ Remove", callback_data="adm_rm")],
             [InlineKeyboardButton("📋 List", callback_data="adm_list")],
             [InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]]
        await q.edit_message_text("👤 *Admin Management*", parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(k)); return
    if d == "adm_add" and is_owner(u.id):
        await q.edit_message_text("Send `<user_id>`:", parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back("own_admins")); PENDING[u.id] = {"action":"adm_add"}; return
    if d == "adm_rm" and is_owner(u.id):
        await q.edit_message_text("Send `<user_id>`:", parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back("own_admins")); PENDING[u.id] = {"action":"adm_rm"}; return
    if d == "adm_list" and is_owner(u.id):
        a = db.list_admins()
        txt = "📋 Admins:\n" + ("\n".join(f"• `{x}`" for x in a) if a else "none")
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back("own_admins")); return

    # ---- force-sub mgmt ----
    if d == "own_fs" and is_owner(u.id):
        k = [[InlineKeyboardButton("➕ Add", callback_data="fs_add"),
              InlineKeyboardButton("➖ Remove", callback_data="fs_rm")],
             [InlineKeyboardButton("📋 List", callback_data="fs_list")],
             [InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]]
        await q.edit_message_text("📢 *Force-Sub*", parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(k)); return
    if d == "fs_add" and is_owner(u.id):
        await q.edit_message_text("Send: `<@chat_id> | <Name> | <https://t.me/...>`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("own_fs"))
        PENDING[u.id] = {"action":"fs_add"}; return
    if d == "fs_rm" and is_owner(u.id):
        await q.edit_message_text("Send `<@chat_id>`:", parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back("own_fs")); PENDING[u.id] = {"action":"fs_rm"}; return
    if d == "fs_list" and is_owner(u.id):
        s = db.get_force_subs()
        txt = "📋 Force-Subs:\n" + ("\n".join(f"• `{c}` — {n}" for c,n,u_ in s) if s else "none")
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.back("own_fs")); return

    # ---- plans ----
    if d == "own_plans" and is_owner(u.id):
        await q.edit_message_text("💎 *Plan Manager*", parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.owner_plans_menu()); return
    if d == "plan_add" and is_owner(u.id):
        await q.edit_message_text(
            "Send: `name | emoji | price | daily_limit(-1=∞) | cooldown_h | bonus`\n"
            "Example: `Gold | 🥇 | 200 | 40 | 8 | 25`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("own_plans"))
        PENDING[u.id] = {"action":"plan_add"}; return
    if d.startswith("plan_edit:") and is_owner(u.id):
        pid = int(d.split(":")[1]); p = db.get_plan(pid)
        await q.edit_message_text(
            f"✏️ *{p[2]} {p[1]}*\n\n💳 *{p[3]}* · 📅 *{'∞' if p[4]==-1 else p[4]}* · "
            f"⏱ *{p[5]}h* · 🎁 *{p[6]}*",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.plan_edit_menu(pid)); return
    if d.startswith("plan_field:") and is_owner(u.id):
        _, pid_s, field = d.split(":")
        await q.edit_message_text(f"Send new value for `{field}`:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back(f"plan_edit:{pid_s}"))
        PENDING[u.id] = {"action":"plan_field","pid":int(pid_s),"field":field}; return
    if d.startswith("plan_del:") and is_owner(u.id):
        db.delete_plan(int(d.split(":")[1]))
        await q.edit_message_text("🗑 Deleted.", reply_markup=kb.owner_plans_menu()); return

    # ---- redeem ----
    if d == "redeem_start":
        await q.edit_message_text("🎟 Send your coupon code:\n\n_Codes are case-insensitive._",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back())
        PENDING[u.id] = {"action": "redeem"}; return

    # ---- coupons ----
    if d == "own_coupons" and is_owner(u.id):
        await q.edit_message_text("🎟 *Coupon Manager*",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.owner_coupons_menu()); return
    if d == "cpn_gen" and is_owner(u.id):
        await q.edit_message_text(
            "🎟 *Generate Coupon*\n\n"
            f"Send: `<credit> | <expiry_hours> | <amount>`\n"
            f"• credit (default `{C.DEFAULT_COUPON_CREDIT}`)\n"
            f"• expiry_hours (default `{C.DEFAULT_COUPON_EXPIRY_H}`)\n"
            f"• amount (1–{C.MAX_COUPONS_PER_GENERATE})\n\n"
            f"Example: `500 | 24 | 1`\nOr just `500` for one 24h coupon.",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("own_coupons"))
        PENDING[u.id] = {"action": "cpn_gen"}; return
    if d == "cpn_list" and is_owner(u.id):
        rows = db.list_coupons(30)
        if not rows:
            await q.edit_message_text("📋 No coupons yet.",
                reply_markup=kb.back("own_coupons")); return
        lines = ["📋 *Latest 30 Coupons*\n"]
        now = int(time.time())
        for code, credit, expiry, used_by, revoked in rows:
            if revoked:               status = "🗑 revoked"
            elif used_by:             status = f"✅ used by `{used_by}`"
            elif expiry <= now:       status = "⌛ expired"
            else:                     status = f"⏳ active ~{int((expiry-now)/60)}m"
            lines.append(f"`{code}` · *{credit}*💳 · {status}")
        await q.edit_message_text("\n".join(lines),
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("own_coupons")); return
    if d == "cpn_stats" and is_owner(u.id):
        s = db.coupon_stats()
        await q.edit_message_text(
            f"📊 *Coupon Stats*\n\n"
            f"Total: *{s['total']}*\n🟢 Active: *{s['active']}*\n"
            f"✅ Used: *{s['used']}*\n⌛ Expired: *{s['expired']}*",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("own_coupons")); return
    if d == "cpn_revoke" and is_owner(u.id):
        await q.edit_message_text("🗑 Send the coupon *code* to revoke:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("own_coupons"))
        PENDING[u.id] = {"action": "cpn_revoke"}; return
    if d == "cpn_done":
        await q.edit_message_text("✅ Coupon created.",
            reply_markup=kb.owner_coupons_menu()); return

# ---------- text handler ----------
async def on_text(update, ctx):
    u = update.effective_user
    if not update.message or not update.message.text: return
    st = PENDING.get(u.id)
    if not st: return
    txt = update.message.text.strip(); act = st["action"]

    if act == "reset":
        PENDING.pop(u.id, None)
        if not is_owner(u.id):
            if db.daily_count(u.id) >= db.effective_limit(u.id):
                await update.message.reply_text("⛔ Daily limit reached."); return
            cd = db.effective_cooldown(u.id) * 3600
            last = db.get_last_reset(u.id)
            if cd and last and time.time() - last < cd:
                left = int((cd - (time.time()-last))/60)
                await update.message.reply_text(f"⏱ Cooldown: {left} min left."); return
        msg = await update.message.reply_text("⏳ Sending...")
        res = U.send_reset(txt)
        db.log_reset(u.id, txt, res)
        db.inc_daily(u.id); db.set_last_reset(u.id, int(time.time()))
        if res.startswith("email:"): out = f"✅ *Sent!*\n📧 `{res.split(':',1)[1]}`"
        elif res == "phone": out = "✅ *Sent via phone!*"
        elif res == "error:not_found": out = "❌ Not found."
        else: out = f"⚠️ `{res}`"
        await msg.edit_text(out, parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back()); return

    if act == "redeem":
        PENDING.pop(u.id, None)
        status, credit = db.redeem_coupon(txt, u.id)
        if status == "ok":
            await update.message.reply_text(
                f"🎉 *Coupon redeemed!*\n\n💰 +{credit} credit\n"
                f"💳 New balance: *{db.get_credit(u.id)}*",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back())
        elif status == "not_found":
            await update.message.reply_text("❌ *Wrong coupon.* Please check the code.",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("redeem_start"))
        elif status == "used":
            await update.message.reply_text("❌ *Coupon already used.*",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back())
        elif status == "expired":
            await update.message.reply_text("⌛ *Coupon expired.*",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back())
        elif status == "revoked":
            await update.message.reply_text("🚫 *Coupon was revoked by owner.*",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back())
        return

    if not is_owner(u.id): PENDING.pop(u.id, None); return

    try:
        if act == "set_daily":
            db.set_daily_limit(int(txt))
            await update.message.reply_text(f"✅ Daily = *{txt}*",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("owner_panel"))
        elif act == "set_cool":
            db.set_cooldown(int(txt))
            await update.message.reply_text(f"✅ Cooldown = *{txt}h*",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("owner_panel"))
        elif act == "pick_user":
            target = int(txt); r = db.get_user(target)
            if not r:
                await update.message.reply_text("❌ User not found."); PENDING.pop(u.id, None); return
            p = db.get_user_plan(target); plan_txt = f"{p[2]} {p[1]}" if p else "none"
            await update.message.reply_text(
                f"👤 *User* `{target}`\n\n💎 Plan: *{plan_txt}*\n"
                f"💳 Credit: *{db.get_credit(target)}*\n"
                f"📅 Daily: *{db.daily_count(target)}/{db.effective_limit(target)}*\n"
                f"🚫 Banned: *{'yes' if db.is_banned(target) else 'no'}*",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.user_manage_panel(target))
        elif act in ("cred_add","cred_rm","cred_set"):
            target = st["target"]; n = int(txt)
            if act == "cred_add": db.add_credit(target, n)
            elif act == "cred_rm": db.remove_credit(target, n)
            else: db.set_credit(target, n)
            await update.message.reply_text(f"✅ Credit for `{target}` = *{db.get_credit(target)}*",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.user_manage_panel(target))
        elif act == "lim_set":
            target = st["target"]; db.set_user_limit(target, int(txt))
            await update.message.reply_text(f"✅ Limit for `{target}` = *{txt}*",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.user_manage_panel(target))
        elif act == "adm_add":
            db.add_admin(int(txt))
            await update.message.reply_text(f"✅ Admin added: `{txt}`",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("own_admins"))
        elif act == "adm_rm":
            db.remove_admin(int(txt))
            await update.message.reply_text(f"✅ Admin removed: `{txt}`",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("own_admins"))
        elif act == "fs_add":
            parts = [x.strip() for x in txt.split("|")]
            if len(parts) != 3: raise ValueError("Format: @chat | Name | URL")
            db.add_force_sub(*parts)
            await update.message.reply_text("✅ Force-sub added.", reply_markup=kb.back("own_fs"))
        elif act == "fs_rm":
            db.remove_force_sub(txt)
            await update.message.reply_text("✅ Removed.", reply_markup=kb.back("own_fs"))
        elif act == "plan_add":
            parts = [x.strip() for x in txt.split("|")]
            if len(parts) != 6: raise ValueError("Need 6 fields")
            name, emoji, price, lim, cool, bonus = parts
            db.add_plan(name, emoji, int(price), int(lim), int(cool), int(bonus))
            await update.message.reply_text("✅ Plan added.", reply_markup=kb.owner_plans_menu())
        elif act == "plan_field":
            pid = st["pid"]; field = st["field"]
            val = txt if field in ("name","emoji") else int(txt)
            db.edit_plan(pid, field, val)
            await update.message.reply_text(f"✅ Updated `{field}`.",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.plan_edit_menu(pid))
        elif act == "cpn_gen":
            PENDING.pop(u.id, None)
            parts = [p.strip() for p in txt.split("|")]
            if len(parts) == 1:
                credit = int(parts[0]); hours = C.DEFAULT_COUPON_EXPIRY_H; amount = 1
            elif len(parts) == 3:
                credit, hours, amount = int(parts[0]), int(parts[1]), int(parts[2])
            else:
                raise ValueError("Use `credit` or `credit | hours | amount`")
            if amount < 1 or amount > C.MAX_COUPONS_PER_GENERATE:
                raise ValueError(f"Amount must be 1–{C.MAX_COUPONS_PER_GENERATE}")
            codes = [db.create_coupon(credit, hours, u.id) for _ in range(amount)]
            if amount == 1:
                await update.message.reply_text(
                    f"🎟 *Coupon created!*\n\nCode: `{codes[0]}`\n"
                    f"💰 Credit: *{credit}*\n⏱ Expires in *{hours}h*",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb.coupon_result_kb(codes[0]))
            else:
                txt_codes = "\n".join(f"`{c}`" for c in codes)
                await update.message.reply_text(
                    f"🎟 *{amount} coupons created!*\n\n{txt_codes}\n\n"
                    f"💰 {credit} each · ⏱ {hours}h",
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("own_coupons"))
            return
        elif act == "cpn_revoke":
            PENDING.pop(u.id, None)
            db.revoke_coupon(txt)
            await update.message.reply_text(f"🗑 Revoked `{txt.upper()}` (if unused).",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back("own_coupons"))
            return
        PENDING.pop(u.id, None)
    except Exception as e:
        await update.message.reply_text(f"⚠️ `{e}`", parse_mode=ParseMode.MARKDOWN)

# ---------- error handler ----------
async def on_error(update, ctx):
    log.exception("err", exc_info=ctx.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("⚠️ Error. Try again.")
    except Exception: pass

# ---------- main ----------
def main():
    db.init_db()
    db.seed_plans()
    app = Application.builder().token(C.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)
    log.info("Bot running")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
