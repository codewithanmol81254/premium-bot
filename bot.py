import os
import asyncio
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from yt_dlp import YoutubeDL

# Network requests tool for cloud proxy bypass
try:
    import requests
except ImportError:
    requests = None

# --- WEB SERVER FOR RENDER 24/7 KEEP ALIVE ---
app = Flask('')

@app.route('/')
def home():
    return "Anmol's Bot is Running 24/7 Heavily!"

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    threading.Thread(target=run_web_server, daemon=True).start()
# ---------------------------------------------

API_TOKEN = "8951596090:AAFeX3jht3Yjm_v26CgUsHmiz0MVK-2-nPg"
db = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Welcome, Anmol Bhai!**\n\n"
        "⚡ **Render 24/7 Cloud Engine Active!**\n"
        "Mujhe kisi bhi video/music ka link bhejein, cloud bypass system se instant download hoga."
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

    # --- LAYER 1: TRY CLOUD PROXY API FIRST (Bypasses Render Blocked IP) ---
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
            print(f"Cloud Proxy Bypass failed, switching to local backup: {api_err}")

    # --- LAYER 2: LOCAL YT-DLP BACKUP (Runs if API fails) ---
    if not download_success:
        ydl_opts = {
            'format': 'best[ext=mp4]/best' if choice == "mp4" else 'bestaudio/best',
            'outtmpl': f'local_{user_id}.%(ext)s',
            'restrictfilenames': True,
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
                
            if filename and os.path.exists(filename):
                download_success = True
        except Exception as ytdl_err:
            print(f"Local backup engine also failed: {ytdl_err}")

    # --- UPLOAD AND CLEANUP LAYER ---
    try:
        if download_success and filename and os.path.exists(filename):
            await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="📤 Uploading to Telegram...")
            
            with open(filename, 'rb') as file_asset:
                if choice == "mp4":
                    await context.bot.send_video(chat_id=chat_id, video=file_asset, caption=f"🎬 {title}\n⚡ @Anmol_Bot", read_timeout=60, write_timeout=120)
                else:
                    await context.bot.send_audio(chat_id=chat_id, audio=file_asset, title=title, caption=f"🎵 {title}\n⚡ @Anmol_Bot", read_timeout=60, write_timeout=120)

            if os.path.exists(filename):
                os.remove(filename)
            await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
        else:
            raise Exception("All data routing infrastructure failed on Render network.")
            
    except Exception as final_err:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="❌ Server completely busy or link restricted. Please thodi der baad dobara koshish karein.")

    if user_id in db:
        del db[user_id]

def main():
    keep_alive() # Starts background web server for Render 24/7 webcheck
    print("🚀 Starting Bot Framework on Render Cloud...")
    application = Application.builder().token(API_TOKEN).read_timeout(60).write_timeout(120).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    application.add_handler(CallbackQueryHandler(button_click))

    print("✅ System Online. Polling active.")
    application.run_polling()

if __name__ == '__main__':
    main()
    
