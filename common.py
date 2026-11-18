import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
def admin_ids():
    return {int(x.strip()) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip().isdigit()}
async def notify_admins(app, text, photo=None, oid=None):
    ids=admin_ids()
    keyboard=InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ تأیید",callback_data=f"approve:{oid}"),
        InlineKeyboardButton("❌ رد",callback_data=f"reject:{oid}")
    ]]) if oid else None
    for uid in ids:
        try:
            if photo: await app.bot.send_photo(uid,photo,caption=text,reply_markup=keyboard)
            else: await app.bot.send_message(uid,text,reply_markup=keyboard)
        except Exception:
            import logging; logging.exception("Admin notification failed for %s",uid)
def money_text(value): return str(value)
