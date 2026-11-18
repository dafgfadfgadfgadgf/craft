import os, asyncio, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from db import init_db, create_order, get_order, update_order, get_waiting_receipt_order
from common import admin_ids, notify_admins, money_text

TOKEN=os.getenv("MAIN_BOT_TOKEN")
SUPPORT=os.getenv("SUPPORT_USERNAME","Craftoriaa").lstrip("@")
CARD=os.getenv("CARD_NUMBER","شماره کارت توسط مدیریت تنظیم نشده است")
logging.basicConfig(level=logging.INFO)

def home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 ثبت سفارش", callback_data="new_order")],
        [InlineKeyboardButton("🎧 پشتیبانی", url=f"https://t.me/{SUPPORT}")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "به فروشگاه Craftoria خوش آمدید! ✨\n\nبرای ثبت سفارش روی دکمه زیر بزنید.",
        reply_markup=home()
    )

async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    context.user_data.clear()
    context.user_data["step"]="name"
    await q.message.reply_text("لطفاً نام و نام خانوادگی خود را وارد کنید:")

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step=context.user_data.get("step")
    if not step: 
        await update.message.reply_text("برای شروع یا ثبت سفارش از منوی اصلی استفاده کنید.", reply_markup=home()); return
    value=update.message.text.strip()
    if step=="name":
        if len(value)<4:
            await update.message.reply_text("لطفاً نام و نام خانوادگی کامل را وارد کنید."); return
        context.user_data["name"]=value
        context.user_data["step"]="phone"
        kb=ReplyKeyboardMarkup([[KeyboardButton("📱 ارسال شماره تلفن", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("شماره تلفن خود را ارسال کنید یا به‌صورت متنی بنویسید:", reply_markup=kb)
    elif step=="phone":
        context.user_data["phone"]=value
        context.user_data["step"]="photo"
        await update.message.reply_text("حالا عکس اسکین یا آیتم ماینکرفتی که می‌خواهید را ارسال کنید. 📷", reply_markup=ReplyKeyboardMarkup([["لغو سفارش"]],resize_keyboard=True))
    elif step=="address":
        if len(value)<8:
            await update.message.reply_text("لطفاً آدرس دقیق‌تری وارد کنید (شهر، خیابان، پلاک و واحد در صورت وجود)."); return
        oid=context.user_data.get("order_id")
        update_order(oid, address=value, status="address_received")
        order=get_order(oid)
        await update.message.reply_text("✅ آدرس شما ثبت شد.\nسفارش شما در سریع‌ترین حالت ممکن برایتان ارسال می‌شود.\n\nجهت اطلاع از وضعیت بسته می‌توانید به پشتیبانی پیام دهید: @"+SUPPORT,
            reply_markup=home())
        await notify_admins(context.application, f"📍 آدرس سفارش #{oid} دریافت شد.\nمشتری: {order['name']}\nآدرس: {value}")
        context.user_data.clear()

async def on_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("step")!="phone": return
    context.user_data["phone"]=update.message.contact.phone_number
    context.user_data["step"]="photo"
    await update.message.reply_text("شماره دریافت شد. حالا عکس اسکین یا آیتم ماینکرفتی را ارسال کنید. 📷",
        reply_markup=ReplyKeyboardMarkup([["لغو سفارش"]],resize_keyboard=True))

async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step=context.user_data.get("step")
    if step=="photo":
        photo=update.message.photo[-1].file_id
        oid=create_order(update.effective_user.id, update.effective_user.username or "",
                         context.user_data["name"], context.user_data["phone"], photo)
        context.user_data.update(step=None, order_id=oid)
        await update.message.reply_text(f"✅ عکس شما ارسال شد و سفارش با شماره #{oid} ثبت شد.\nپس از بررسی، نتیجه برایتان ارسال می‌شود.",
            reply_markup=home())
        caption=(f"🆕 سفارش جدید Craftoria #{oid}\n"
                 f"👤 نام: {context.user_data['name']}\n"
                 f"📱 تلفن: {context.user_data['phone']}\n"
                 f"🆔 کاربر: {update.effective_user.id}\n"
                 f"🔗 نام کاربری: @{update.effective_user.username or 'ندارد'}")
        await notify_admins(context.application, caption, photo=photo, oid=oid)
        context.user_data.clear()
    else:
        waiting=get_waiting_receipt_order(update.effective_user.id)
        if not waiting:
            await update.message.reply_text("برای این عکس سفارش در انتظار رسید پیدا نشد. ابتدا سفارش ثبت کنید.", reply_markup=home())
            return
        oid=waiting["id"]
        update_order(oid, receipt_file_id=update.message.photo[-1].file_id, status="receipt_received")
        order=get_order(oid)
        await update.message.reply_text("🧾 رسید شما دریافت شد و برای بررسی به مدیریت ارسال شد.\nلطفاً آدرس دقیق دریافت سفارش را وارد کنید:")
        context.user_data["step"]="address"
        await notify_admins(context.application, f"🧾 رسید پرداخت سفارش #{oid} دریافت شد.\nمشتری: {order['name']}",
                            photo=update.message.photo[-1].file_id, oid=oid)

async def on_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text=="لغو سفارش":
        context.user_data.clear()
        await update.message.reply_text("سفارش لغو شد.",reply_markup=home()); return
    await on_text(update,context)

async def main():
    if not TOKEN: raise RuntimeError("MAIN_BOT_TOKEN در فایل .env تنظیم نشده است")
    init_db()
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(begin, pattern="^new_order$"))
    app.add_handler(MessageHandler(filters.CONTACT,on_contact))
    app.add_handler(MessageHandler(filters.PHOTO,on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,on_text_router))
    await app.initialize(); await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__=="__main__": asyncio.run(main())
