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

# Aapki fresh normal API Key
API_TOKEN = "8951596090:AAH2CfioszIDBCoEs_PRGj1j-fu9R4nT1OA"
user_sessions = {}

# Ekdam normal aur basic options jo sabhi sites par work karte hain
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
        "👋 **Welcome to Downloader Bot!**\n\nMujhe koi bhi YouTube, Spotify, ya Instagram link bhejien, main download kar dunga."
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("⚠️ Please sahi URL bhejien.")
        return

    user_id = update.message.from_user.id
    status_msg = await update.message.reply_text("🔍 **Link scan ho raha hai...**")

    try:
        # Normal extraction bina kisi extra masking restrictions ke
        with YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Media File')
            thumbnail = info.get('thumbnail')

        user_sessions[user_id] = {"url": url}
        
        keyboard = [
            [InlineKeyboardButton("🎬 Video (MP4)", callback_data="mp4")],
            [InlineKeyboardButton("🎵 Audio (MP3/M4A)", callback_data="mp3")]
        ]
        
        caption = f"📝 **Title:** `{title}`\n\nFormat select karein:"
        await status_msg.delete()

        if thumbnail:
            await context.bot.send_photo(
                chat_id=update.message.chat_id, 
                photo=thumbnail, 
                caption=caption, 
                reply_markup=InlineKeyboardMarkup(keyboard), 
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                caption, 
                reply_markup=InlineKeyboardMarkup(keyboard), 
                parse_mode="Markdown"
            )

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
    chat_id = update.effective_chat.id
    await query.message.delete()
    
    status_msg = await context.bot.send_message(chat_id=chat_id, text="⚙️ **Processing file...**")

    # Simple download system based on user choice
    if choice == "mp4":
        opts = {**YTDL_OPTS, 'format': 'best', 'outtmpl': '%(title)s.%(ext)s'}
    else:
        opts = {**YTDL_OPTS, 'format': 'bestaudio', 'outtmpl': '%(title)s.%(ext)s'}

    try:
        await status_msg.edit_text("📥 **Downloading from server...**")
        with open('download_running.lock', 'w') as f: f.write('1') # Simple single process lock
        
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            title = info.get('title', 'Media')

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
        await status_msg.edit_text("❌ **Download failed!** Server temporary busy tha. Koshish karein ki thoda ruk kar link bhejien.")
    
    finally:
        if os.path.exists('download_running.lock'): os.remove('download_running.lock')
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
    
        
