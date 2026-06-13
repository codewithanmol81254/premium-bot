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

# --- AUTO FFMPEG INSTALLER FOR RENDER ---
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

# !!! AAPKA FRESH NEW TELEGRAM BOT TOKEN !!!
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

    if choice == "mp4":
        opts = {**YTDL_OPTS, 'format': 'best[ext=mp4]/best', 'outtmpl': f'video_{user_id}.%(ext)s'}
    else:
        opts = {
            **YTDL_OPTS, 
            'format': 'bestaudio/best',
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
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
                
                raw_filename = ydl.prepare_filename(info)
                base, _ = os.path.splitext(raw_filename)
                
                for ext in ['.mp3', '.m4a', '.mp4', '.webm', '.opus']:
                    test_path = base + ext
                    if os.path.exists(test_path):
                        filename = test_path
                        break
                
                if not filename and os.path.exists(raw_filename):
                    filename = raw_filename
                    
        except Exception as yt_err:
            print(f"Primary YT-DLP engine blocked, using API fallback: {yt_err}")
            if choice == "mp3" and requests is not None:
                await status_msg.edit_text("🚀 **Bypassing Server restriction... Fetching High Quality Audio...**")
                api_url = f"https://api.vreden.web.id/api/ytmp3?url={url}" if "youtube" in url.lower() else f"https://api.vreden.web.id/api/spotify?url={url}"
                res = requests.get(api_url).json()
                download_link = res.get("result", {}).get("download") or res.get("result", {}).get("music")
                if download_link:
                    filename = f"track_{user_id}.mp3"
                    with requests.get(download_link, stream=True) as r:
                        with open(filename, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)

        if filename and os.path.exists(filename):
            await status_msg.edit_text("📤 **Uploading to Telegram...**")
            with open(filename, 'rb') as file_data:
                if choice == "mp4" and filename.endswith(".mp4"):
                    await context.bot.send_video(chat_id=chat_id, video=file_data, caption=f"🎬 *{saved_title}*")
                else:
                    await context.bot.send_audio(chat_id=chat_id, audio=file_data, title=saved_title)
            
            os.remove(filename)
            await status_msg.delete()
        else:
            raise Exception("File generation failed on all layers.")

    except Exception as e:
        print(f"Final Execution Error: {e}")
        await status_msg.edit_text("❌ **Download failed!** Server ne temporary process block kiya hai. Koshish karein ki link dobara bhejien ya Instagram link try karein.")
    
    finally:
        if user_id in user_sessions: del user_sessions[user_id]

async def main_async():
    install_ffmpeg()
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
    
