import os
import asyncio
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from yt_dlp import YoutubeDL

# --- SIMPLE KEEP ALIVE FOR RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running Perfectly!"

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    threading.Thread(target=run_web_server, daemon=True).start()
# ------------------------------------

API_TOKEN = "8951596090:AAGTkiEELj5KwrT-0HaQS8QKa1wJ_7LzV2o"
user_sessions = {}

YTDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ **Anmol's Premium Downloader Bot Active** ✨\n\nMujhe koi bhi YouTube, Spotify, ya Instagram link bhejien, main download kar dunga."
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("⚠️ Please sahi URL bhejien.")
        return

    user_id = update.message.from_user.id
    status_msg = await update.message.reply_text("🔍 **Link scan ho raha hai...**")

    is_spotify = "spotify.com" in url.lower() or "spotify" in url.lower()
    if is_spotify:
        url = url.split('?')[0]

    try:
        with YoutubeDL(YTDL_OPTS) as ydl:
            search_url = f"ytsearch:{url}" if is_spotify else url
            info = ydl.extract_info(search_url, download=False)
            
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
                
            title = info.get('title', 'Media File')
            thumbnail = info.get('thumbnail')

        user_sessions[user_id] = {"url": url, "is_spotify": is_spotify}
        
        keyboard = [
            [InlineKeyboardButton("🎬 Video (MP4)", callback_data="mp4")],
            [InlineKeyboardButton("🎵 Audio (Premium M4A)", callback_data="mp3")]
        ]
        
        caption = f"📝 **Title:** `{title}`\n\nFormat select karein:"
        await status_msg.delete()

        if thumbnail:
            await context.bot.send_photo(chat_id=update.message.chat_id, photo=thumbnail, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    except Exception as e:
        print(f"Extraction Error: {e}")
        await status_msg.edit_text("❌ **Link scan nahi ho paya.**\nEk baar link check karke dobara bhejien.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    choice = query.data
    await query.answer()

    if user_id not in user_sessions:
        await query.message.reply_text("❌ Session expired! Please link dobara bhejien.")
        return

    url = user_sessions[user_id]["url"]
    is_spotify = user_sessions[user_id]["is_spotify"]
    chat_id = update.effective_chat.id
    await query.message.delete()
    
    status_msg = await context.bot.send_message(chat_id=chat_id, text="⚙️ **Processing file...**")

    # PERMANENT FIXED NO-FFMPEG FORMATS
    if choice == "mp4":
        # Direct single container mp4 video
        opts = {**YTDL_OPTS, 'format': 'best[ext=mp4]/best', 'outtmpl': '%(title)s.%(ext)s'}
    else:
        # Direct single container premium m4a audio (Sabse safe aur high quality audio bina FFmpeg ke)
        opts = {**YTDL_OPTS, 'format': 'ba[ext=m4a]/bestaudio', 'outtmpl': '%(title)s.%(ext)s'}
        if is_spotify:
            opts['default_search'] = 'ytsearch'

    try:
        await status_msg.edit_text("📥 **Downloading from server...**")
        
        download_target = f"ytsearch:{url}" if (is_spotify and choice == "mp3") else url
        
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(download_target, download=True)
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
            
            # File extensions and paths calculation safely
            filename = ydl.prepare_filename(info)
            # Agar file format native alag ho gaya toh fix extension
            if not os.path.exists(filename):
                base, _ = os.path.splitext(filename)
                if os.path.exists(base + ".m4a"): filename = base + ".m4a"
                elif os.path.exists(base + ".mp4"): filename = base + ".mp4"
            
            title = info.get('title', 'Media File')

        await status_msg.edit_text("📤 **Uploading to Telegram...**")
        
        with open(filename, 'rb') as file_data:
            if choice == "mp4":
                await context.bot.send_video(chat_id=chat_id, video=file_data, caption=f"🎬 *{title}*")
            else:
                await context.bot.send_audio(chat_id=chat_id, audio=file_data, title=title)

        if os.path.exists(filename): 
            os.remove(filename)
        await status_msg.delete()

    except Exception as e:
        print(f"Download Error: {e}")
        await status_msg.edit_text("❌ **Download failed!** Server ne format accept nahi kiya. Ek baar dobara koshish karein.")
    
    finally:
        if user_id in user_sessions: del user_sessions[user_id]

async def main_async():
    keep_alive()
    application = Application.builder().token(API_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    application.add_handler(CallbackQueryHandler(button_click))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    while True: 
        await asyncio.sleep(3600)

def main():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(main_async())

if __name__ == '__main__':
    main()
    
