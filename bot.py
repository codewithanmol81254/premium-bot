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
    return "🚀 Anmol's Premium Bot is Running Successfully!"

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    threading.Thread(target=run_web_server, daemon=True).start()
# ----------------------------------------

API_TOKEN = "8951596090:AAH2CfioszIDBCoEs_PRGj1j-fu9R4nT1OA"
db = {}

# YouTube block bypass karne ke liye generic mobile user-agent aur options
YTDL_COMMON_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
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
        "🔗 Mujhe kisi bhi video ya music ka link bhejien (YouTube, Shorts, Insta Reels, FB, Spotify).\n"
        "⚡ Direct high quality download ready hai!"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        await update.message.reply_text("⚠️ **Invalid Link!** Please sahi URL bhejien.")
        return

    user_id = update.message.from_user.id
    status_msg = await update.message.reply_text("🔍 **Analyzing Link... Please wait.**")

    if "spotify.com" in url.lower():
        clean_url = url.split('?')[0]
        db[user_id] = {"query": clean_url, "is_spotify": True}
        keyboard = [[InlineKeyboardButton("🎵 Download Original Audio", callback_data="mp3")]]
        await status_msg.delete()
        await update.message.reply_text("💎 **Spotify Link Detected!**\n⚡ Click niche kijiye:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    try:
        opts = {**YTDL_COMMON_OPTS, 'skip_download': True}
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Premium Media Asset')
            thumbnail = info.get('thumbnail') or info.get('thumbnails', [{}])[0].get('url')
            uploader = info.get('uploader', 'Unknown Creator')
            duration = format_duration(info.get('duration'))

        db[user_id] = {"query": url, "is_spotify": False}
        keyboard = [
            [InlineKeyboardButton("🎬 Video (MP4)", callback_data="mp4")],
            [InlineKeyboardButton("🎵 Audio (M4A)", callback_data="mp3")]
        ]
        await status_msg.delete()

        caption_text = f"📝 **TITLE:** `{title}`\n👤 **CREATOR:** `{uploader}`\n⏱️ **DURATION:** `{duration}`\n\n✨ **Select format:**"

        if thumbnail:
            await context.bot.send_photo(chat_id=update.message.chat_id, photo=thumbnail, caption=caption_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(caption_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        await status_msg.edit_text(f"❌ **Link scan nahi ho paya.**\nError: IP temporary restricted by provider. Please try again in a moment or use another link.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    choice = query.data
    await query.answer()

    if user_id not in db:
        await query.message.reply_text("❌ Session expired! Link phir se bhejien.")
        return

    await query.message.delete()
    status_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="⚙️ **[Processing] High-speed downloading started...**")
    await start_download(update, context, user_id, choice, status_msg)

async def start_download(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, choice, status_msg):
    search_query = db[user_id]["query"]
    chat_id = update.effective_chat.id

    if choice == "mp4":
        ydl_opts = {**YTDL_COMMON_OPTS, 'format': 'best[ext=mp4]/best', 'outtmpl': '%(title)s.%(ext)s', 'restrictfilenames': True}
    else:
        ydl_opts = {
            **YTDL_COMMON_OPTS,
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'restrictfilenames': True,
            'default_search': 'ytsearch',
            'noplaylist': True
        }

    try:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="🚀 **[Downloading] Fetching stream...**")
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=True)
            if "entries" in info and info['entries']:
                video_data = info['entries'][0]
                filename = ydl.prepare_filename(video_data)
                title = video_data.get('title', 'Audio Asset')
            else:
                filename = ydl.prepare_filename(info)
                title = info.get('title', 'Media Asset')

        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="📤 **[Uploading] Pushing file to Telegram...**")
        with open(filename, 'rb') as file_asset:
            if choice == "mp4":
                await context.bot.send_video(chat_id=chat_id, video=file_asset, caption=f"🎬 **{title}**\n\n⚡ *Downloaded via @Anmol_Bot*", parse_mode="Markdown")
            else:
                await context.bot.send_audio(chat_id=chat_id, audio=file_asset, title=title, caption=f"🎵 **{title}**\n\n⚡ *Downloaded via @Anmol_Bot*", parse_mode="Markdown")

        if os.path.exists(filename): os.remove(filename)
        await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
    except Exception as e:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"❌ **Download failed!**\nServer is busy. Please re-send the link in a few seconds.")

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
    
    
