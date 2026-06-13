import os
import asyncio
import threading
import sys
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from yt_dlp import YoutubeDL

# Safe import for requests to support our high-end fallback animation system
try:
    import requests
except ImportError:
    requests = None

# --- AUTO FFMPEG INSTALLER FOR RENDER (ChatGPT Fixed) ---
def install_ffmpeg():
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_exe)
        print(f"✅ FFmpeg successfully linked from imageio_ffmpeg: {ffmpeg_exe}")
    except Exception as e:
        print(f"⚠️ FFmpeg auto-link via imageio failed, trying fallback: {e}")

# --- SIMPLE KEEP ALIVE FOR RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Anmol Bot is Running Heavily!"

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    threading.Thread(target=run_web_server, daemon=True).start()
# ------------------------------------

API_TOKEN = "8951596090:AAGTkiEELj5KwrT-0HaQS8QKa1wJ_7LzV2o"
user_sessions = {}

# Enhanced options to mimic an authentic mobile browser and bypass IP block
YTDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'extractor_args': {'youtube': {'player_client': ['android', 'web_embedded']}},
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ **Anmol's Premium Downloader Bot Active!**\n\nMujhe Instagram, YouTube, ya Spotify ka koi bhi link bhejien, main bina kisi block ke download karne ki koshish karunga."
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("⚠️ Please sahi URL bhejien bhai.")
        return

    user_id = update.message.from_user.id
    status_msg = await update.message.reply_text("🔍 **Link scan ho raha hai...**")

    if "spotify" in url.lower():
        url = url.split('?')[0]

    try:
        # Purani UI ke mutabik thumbnail aur details extract karna
        with YoutubeDL(YTDL_OPTS) as ydl:
            search_url = f"ytsearch1:{url}" if "spotify" in url.lower() else url
            info = ydl.extract_info(search_url, download=False)
            
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
                
            title = info.get('title', 'Media File')
            thumbnail = info.get('thumbnail')

        user_sessions[user_id] = {"url": url, "title": title}
        
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
        print(f"Scan Error: {e}")
        # Purana mast UI fallback mechanism agar local IP restricted ho jaye
        if "spotify" in url.lower() or "youtube" in url.lower():
            user_sessions[user_id] = {"url": url, "title": "Premium Track"}
            keyboard = [[InlineKeyboardButton("🎵 Download Premium Audio", callback_data="mp3")]]
            await status_msg.edit_text("🎵 YouTube/Spotify link detected! Direct high-speed download format select karein:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await status_msg.edit_text("❌ **Link scan nahi ho paya.**\nServer busy hai ya IP restricted hai. Ek baar dobara link bhejien.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    choice = query.data
    await query.answer()

    if user_id not in user_sessions:
        await query.message.reply_text("❌ Session expired! Please link dobara bhejien.")
        return

    url = user_sessions[user_id]["url"]
    saved_title = user_sessions[user_id]["title"]
    chat_id = update.effective_chat.id
    await query.message.delete()
    
    status_msg = await context.bot.send_message(chat_id=chat_id, text="⚙️ **Downloading...**")

    # Anti-FFmpeg robust options mixed with ChatGPT format suggestions
    if choice == "mp4":
        opts = {**YTDL_OPTS, 'format': 'best[ext=mp4]/best', 'outtmpl': f'video_{user_id}.%(ext)s'}
    else:
        opts = {
            **YTDL_OPTS, 
            'format': 'bestaudio/best',  # Flexible extraction rule
            'outtmpl': f'audio_{user_id}.%(ext)s',
            'postprocs': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }
        if "spotify" in url.lower():
            opts['default_search'] = 'ytsearch1'

    try:
        download_target = f"ytsearch1:{url}" if ("spotify" in url.lower() and choice == "mp3") else url
        filename = None
        
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(download_target, download=True)
                
