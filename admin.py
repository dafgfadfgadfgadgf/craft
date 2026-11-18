import os, asyncio, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from db import init_db, get_order, update_order
from common import admin_ids, money_text

TOKEN=os.getenv("ADMIN_BOT_TOKEN")
MAIN_TOKEN=os.getenv("MAIN_BOT_TOKEN")
CARD=os.getenv("CARD_NUMBER","شماره کارت توسط مدیریت تنظیم نشده است")
logging.basicConfig(level=logging.INFO)

def allowed(uid): return uid in admin_ids()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update.effective_user.id):
        await update.message.reply_text("⛔ دسترسی ندارید."); return
    await update.message.reply_text("پنل مدیریت Craftoria فعال است.\nبرای مشاهده راهنما /help را بزنید.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed(update.effective_user.id):
        await update.message.reply_text("دستورها:\n/orders - سفارش‌های اخیر\nبرای تعیین قیمت، پس از تأیید سفارش عدد قیمت را همین‌جا ارسال کنید.")

async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update.effective_user.id): return
    from db import recent_orders
    rows=recent_orders()
    if not rows: await update.message.reply_text("هنوز سفارشی ثبت نشده."); return
    for o in rows:
        await update.message.reply_text(f"#{o['id']} | {o['status']} | {o['name']} | {o['phone']}")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    if not allowed(q.from_user.id): await q.answer("دسترسی ندارید",show_alert=True); return
    await q.answer()
    action,oid=q.data.split(":")
    o=get_order(int(oid))
    if not o: await q.message.reply_text("سفارش پیدا نشد."); return
    if action=="reject":
        update_order(oid,status="rejected")
        await context.bot.send_message(o["user_id"],f"❌ سفارش شما با شماره #{oid} رد شد.\nبرای راهنمایی: @"+os.getenv("SUPPORT_USERNAME","Craftoriaa").lstrip("@"))
        await q.message.reply_text(f"سفارش #{oid} رد شد.")
    elif action=="approve":
        update_order(oid,status="awaiting_price")
        context.user_data["pricing_order"]=int(oid)
        await q.message.reply_text(f"✅ سفارش #{oid} تأیید شد. حالا قیمت را به عدد وارد کنید:")

async def photo_admin(context, chat_id, file_id, caption):
    await context.bot.send_photo(chat_id, file_id, caption=caption)

async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update.effective_user.id): return
    oid=context.user_data.get("pricing_order")
    if not oid: return
    raw=update.message.text.strip()
    if not raw or len(raw)>40:
        await update.message.reply_text("قیمت معتبر وارد کنید."); return
    o=get_order(oid)
    update_order(oid,price=raw,status="awaiting_receipt")
    try:
        from telegram import Bot
        async with Bot(MAIN_TOKEN) as bot:
            await bot.send_message(o["user_id"],
                f"🎉 سفارش شما تأیید شد!\n💰 مبلغ قابل پرداخت: {raw}\n\n💳 شماره کارت:\n{CARD}\n\nپس از پرداخت، تصویر رسید را همین‌جا ارسال کنید.")
    except Exception:
        logging.exception("Could not message customer")
        await update.message.reply_text("ارسال قیمت به مشتری ناموفق بود؛ توکن ربات اصلی را بررسی کنید.")
        return
    await update.message.reply_text(f"قیمت برای مشتری سفارش #{oid} ارسال شد.")
    context.user_data.pop("pricing_order",None)

async def main():
    if not TOKEN or not MAIN_TOKEN: raise RuntimeError("ADMIN_BOT_TOKEN و MAIN_BOT_TOKEN را در .env تنظیم کنید")
    init_db()
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("help",help_cmd))
    app.add_handler(CommandHandler("orders",orders))
    app.add_handler(CallbackQueryHandler(callback,pattern="^(approve|reject):"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,admin_text))
    await app.initialize(); await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__=="__main__": asyncio.run(main())
