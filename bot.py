import os
import asyncio
from flask import Flask, request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from yt_dlp import YoutubeDL

try:
    import requests
except ImportError:
    requests = None

# --- FLASK WEB SERVER ENGINE ---
app = Flask('')
application = None

@app.route('/')
def home():
    return "Anmol's Telegram Webhook Engine is 24/7 Active!"

# Telegram isme direct message bhejega
@app.route('/webhook', methods=['POST'])
def webhook():
    if application:
        update = Update.de_json(request.get_json(force=True), application.bot)
        # Background task me process karne ke liye taaki Flask jaldi response kare
        asyncio.run_coroutine_threadsafe(application.process_update(update), asyncio.get_event_loop())
    return "OK", 200

# --- BOT LOGIC ---
API_TOKEN = "8951596090:AAFeX3jht3Yjm_v26CgUsHmiz0MVK-2-nPg"
# Render ka apna URL automatic utha lega, ya aap apna URL manually bhi daal sakte hain
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL', 'https://your-render-app-name.onrender.com')

db = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Welcome Back, Anmol Bhai!**\n\n"
        "⚡ **Render Webhook High-Speed Engine Active!**\n"
        "Ab bot bina kisi delay ke 24/7 instant response karega. Mujhe koi bhi link bhejein!"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        await update.message.reply_text("⚠️ Please ek sahi link bhejein.")
        return

    user_id = update.message.from_user.id
    db[user_id] = url

    keyboard = [[
        InlineKeyboardButton("🎬 Video (MP4)", callback_data="mp4"),
        InlineKeyboardButton("🎵 Audio (MP3)", callback_data="mp3")
    ]]
    await update.message.reply_text("📥 Link mil gaya! Kya download karna hai?", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    choice = query.data
    await query.answer()

    if user_id not in db:
        await query.edit_message_text("❌ Session expired! Link dobara bhejein.")
        return

    url = db[user_id]
    chat_id = query.message.chat_id
    status_msg = await query.edit_message_text("⚡ Processing via Cloud Server... Please wait.")

    filename = None
    download_success = False
    title = "Premium Media"

    if requests is not None:
        try:
            if "spotify" in url.lower():
                api_url = f"https://api.sandipbaruwal.codes/spotify?url={url}"
            else:
                api_type = "audio" if choice == "mp3" else "video"
                api_url = f"https://api.deku.poscloud.tech/youtube?url={url}&type={api_type}"

            res = requests.get(api_url, timeout=20).json()
            download_link = res.get("download") or res.get("result") or res.get("url")
            
            if download_link:
                filename = f"cloud_{user_id}.mp4" if choice == "mp4" else f"cloud_{user_id}.mp3"
                with requests.get(download_link, stream=True) as r:
                    with open(filename, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    download_success = True
        except Exception as api_err:
            print(f"Proxy failed: {api_err}")

    if not download_success:
        ydl_opts = {
            'format': 'best[ext=mp4]/best' if choice == "mp4" else 'bestaudio/best',
            'outtmpl': f'local_{user_id}.%(ext)s',
            'restrictfilenames': True,
            'quiet': True
        }
        if choice == "mp3":
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Media File')
                raw_filename = ydl.prepare_filename(info)
                filename = os.path.splitext(raw_filename)[0] + ".mp3" if choice == "mp3" else raw_filename
                download_success = True
        except Exception as ytdl_err:
            print(f"Backup failed: {ytdl_err}")

    try:
        if download_success and filename and os.path.exists(filename):
            with open(filename, 'rb') as file_asset:
                if choice == "mp4":
                    await context.bot.send_video(chat_id=chat_id, video=file_asset, caption=f"🎬 {title}\n⚡ @Anmol_Bot", read_timeout=60, write_timeout=120)
                else:
                    await context.bot.send_audio(chat_id=chat_id, audio=file_asset, title=title, caption=f"🎵 {title}\n⚡ @Anmol_Bot", read_timeout=60, write_timeout=120)
            if os.path.exists(filename):
                os.remove(filename)
            await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
        else:
            raise Exception("Failed")
    except Exception:
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="❌ Server busy ya link restricted hai. Koshish karte rahein.")
        except Exception:
            pass

    if user_id in db:
        del db[user_id]

# Webhook initialization logic
def init_application():
    global application
    # Event loop setup for webhook handling
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    application = Application.builder().token(API_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    application.add_handler(CallbackQueryHandler(button_click))
    
    # Init application engine inside memory
    asyncio.get_event_loop().run_until_complete(application.initialize())
    
    # Telegram ko batana ki is Render URL par saare messages bhejo
    webhook_url = f"{RENDER_URL.rstrip('/')}/webhook"
    asyncio.get_event_loop().run_until_complete(application.bot.set_webhook(url=webhook_url))
    print(f"✅ Webhook successfully connected to: {webhook_url}")

if __name__ == '__main__':
    init_application()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
