import os
import re
import asyncio
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from yt_dlp import YoutubeDL

# --- FLASK WEB SERVER FOR 24/7 HOSTING ---
app = Flask('')

@app.route('/')
def home():
    return "🚀 Anmol's Premium Bot is Active!"

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    threading.Thread(target=run_web_server, daemon=True).start()
# ----------------------------------------

API_TOKEN = "8951596090:AAH2CfioszIDBCoEs_PRGj1j-fu9R4nT1OA"
db = {}

# Advanced extraction parameters to heavily bypass YouTube cloud bans
YTDL_COMMON_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'extracted_flat': 'in_playlist',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Sec-Fetch-Mode': 'navigate',
    }
}

def format_duration(seconds):
    if not seconds: return "Unknown"
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins}:{secs:02d} Mins"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ **WELCOME TO ANMOL'S PREMIUM DOWNLOADER BOT** ✨\n\n"
        "🔗 Mujhe kisi bhi video ka link bhejien.\n"
        "⚡ Direct high quality download aur inline keys ready hain!"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("⚠️ Please sahi URL bhejien.")
        return

    user_id = update.message.from_user.id
    status_msg = await update.message.reply_text("🔍 **Analyzing Link... Please wait.**")

    try:
        opts = {**YTDL_COMMON_OPTS, 'skip_download': True}
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Media Asset')
            thumbnail = info.get('thumbnail')
            uploader = info.get('uploader', 'Unknown')
            duration = format_duration(info.get('duration'))

        db[user_id] = {"query": url}
        keyboard = [
            [InlineKeyboardButton("🎬 Video (MP4)", callback_data="mp4")],
            [InlineKeyboardButton("🎵 Audio (M4A)", callback_data="mp3")]
        ]
        await status_msg.delete()

        caption = f"📝 **TITLE:** `{title}`\n👤 **BY:** `{uploader}`\n⏱️ **TIME:** `{duration}`\n\n✨ Select format:"
        if thumbnail:
            await context.bot.send_photo(chat_id=update.message.chat_id, photo=thumbnail, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        # Prints real reason in logs so we can read it on Render
        print(f"🔥 Extraction Error Trace: {str(e)}")
        await status_msg.edit_text(f"❌ **Link structure issue or IP restricted.**\n\n💡 *Tip: Ek baar Instagram link ya dusra YouTube link try karke dekhein.*")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    choice = query.data
    await query.answer()

    if user_id not in db:
        await query.message.reply_text("❌ Session expired!")
        return

    await query.message.delete()
    status_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="⚙️ **[Processing] Extracting data streams...**")
    
    search_query = db[user_id]["query"]
    chat_id = update.effective_chat.id

    if choice == "mp4":
        ydl_opts = {**YTDL_COMMON_OPTS, 'format': 'best', 'outtmpl': '%(title)s.%(ext)s'}
    else:
        ydl_opts = {**YTDL_COMMON_OPTS, 'format': 'bestaudio', 'outtmpl': '%(title)s.%(ext)s'}

    try:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="🚀 **[Downloading] Grabbing direct cloud assets...**")
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=True)
            filename = ydl.prepare_filename(info)
            title = info.get('title', 'Asset')

        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="📤 **[Uploading] Sending file...**")
        with open(filename, 'rb') as file_asset:
            if choice == "mp4":
                await context.bot.send_video(chat_id=chat_id, video=file_asset, caption=f"🎬 *{title}*")
            else:
                await context.bot.send_audio(chat_id=chat_id, audio=file_asset, title=title)

        if os.path.exists(filename): os.remove(filename)
        await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
    except Exception as e:
        print(f"🔥 Download Error Trace: {str(e)}")
        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"❌ **System temporary restricted.** Try again or check with another link.")

    if user_id in db: del db[user_id]

async def main_async():
    keep_alive()
    application = Application.builder().token(API_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    application.add_handler(CallbackQueryHandler(button_click))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    while True: await asyncio.sleep(3600)

def main():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(main_async())

if __name__ == '__main__':
    main()
            
