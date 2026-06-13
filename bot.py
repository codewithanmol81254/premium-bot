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

API_TOKEN = "8951596090:AAGTkiEELj5KwrT-0HaQS8QKa1wJ_7LzV2o"
user_sessions = {}

YTDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'extractor_args': {'youtube': {'player_client': ['ios', 'android', 'web_embedded']}},
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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

    title = "Premium Track"
    thumbnail = None
    is_scan_successful = False

    try:
        with YoutubeDL(YTDL_OPTS) as ydl:
            search_url = f"ytsearch1:{url}" if "spotify" in url.lower() else url
            info = ydl.extract_info(search_url, download=False)
            
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
                
            title = info.get('title', 'Media File')
            thumbnail = info.get('thumbnail')
            is_scan_successful = True

    except Exception as e:
        print(f"Scan Bypass triggered: {e}")
        if "youtube.com" in url.lower() or "youtu.be" in url.lower():
            title = "YouTube Premium Media"
            is_scan_successful = True
        elif "spotify" in url.lower():
            title = "Spotify Premium Track"
            is_scan_successful = True

    if is_scan_successful:
        user_sessions[user_id] = {"url": url, "title": title}
        
        keyboard = [
            [InlineKeyboardButton("🎬 Video (MP4)", callback_data="mp4")],
            [InlineKeyboardButton("🎵 Audio (Premium MP3)", callback_data="mp3")]
        ]
        
        caption = f"📝 **Title:** `{title}`\n\nFormat select karein:"
        await status_msg.delete()

        if thumbnail:
            try:
                await context.bot.send_photo(chat_id=update.message.chat_id, photo=thumbnail, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await status_msg.edit_text("❌ **Link scan nahi ho paya.**\nEk baar dobara bhejien ya check karein.")

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

    filename = None
    download_success = False

    # --- LAYER 1: CORE LOCAL ENGINE (YT-DLP) ---
    try:
        download_target = f"ytsearch1:{url}" if ("spotify" in url.lower() and choice == "mp3") else url
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
                
        if filename and os.path.exists(filename):
            download_success = True
    except Exception as e:
        print(f"Layer 1 Fail (Local Engine Blocked): {e}")

    # --- LAYER 2: BACKUP CLOUD API ROUTE A (Vreden API) ---
    if not download_success and requests is not None:
        try:
            await status_msg.edit_text("🚀 **Bypassing Server restriction... Trying Route A...**")
            if choice == "mp3":
                api_url = f"https://api.vreden.web.id/api/ytmp3?url={url}" if ("youtube" in url.lower() or "youtu" in url.lower()) else f"https://api.vreden.web.id/api/spotify?url={url}"
            else:
                api_url = f"https://api.vreden.web.id/api/ytmp4?url={url}"

            res = requests.get(api_url, timeout=15).json()
            download_link = res.get("result", {}).get("download") or res.get("result", {}).get("music") or res.get("result", {}).get("video")
            
            if download_link:
                filename = f"download_a_{user_id}.mp4" if choice == "mp4" else f"track_a_{user_id}.mp3"
                with requests.get(download_link, stream=True) as r:
                    with open(filename, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8112):
                            f.write(chunk)
                if os.path.exists(filename):
                    download_success = True
        except Exception as e:
            print(f"Layer 2 Fail (Route A Down): {e}")

    # --- LAYER 3: BACKUP CLOUD API ROUTE B (Ayna/Decoded Mirror API Bypass) ---
    if not download_success and requests is not None:
        try:
            await status_msg.edit_text("⚡ **Route A Busy. Switching to Ultra Route B...**")
            # Using an alternate resilient mirror endpoint architecture
            if choice == "mp3":
                api_url = f"https://api.sandipbaruwal.codes/spotify?url={url}" if "spotify" in url.lower() else f"https://api.deku.poscloud.tech/youtube?url={url}&type=audio"
            else:
                api_url = f"https://api.deku.poscloud.tech/youtube?url={url}&type=video"

            res = requests.get(api_url, timeout=15).json()
            # Dynamic extraction based on standard response formats
            download_link = res.get("download") or res.get("result") or res.get("url")
            
            if download_link:
                filename = f"download_b_{user_id}.mp4" if choice == "mp4" else f"track_b_{user_id}.mp3"
                with requests.get(download_link, stream=True) as r:
                    with open(filename, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8112):
                            f.write(chunk)
                if os.path.exists(filename):
                    download_success = True
        except Exception as e:
            print(f"Layer 3 Fail (Route B Down): {e}")

    # --- FINAL UPLOAD LOGIC ---
    try:
        if download_success and filename and os.path.exists(filename):
            await status_msg.edit_text("📤 **Uploading to Telegram...**")
            with open(filename, 'rb') as file_data:
                if choice == "mp4":
                    await context.bot.send_video(chat_id=chat_id, video=file_data, caption=f"🎬 *{saved_title}*")
                else:
                    await context.bot.send_audio(chat_id=chat_id, audio=file_data, title=saved_title)
            
            os.remove(filename)
            await status_msg.delete()
        else:
            raise Exception("All download layers exhausted and failed.")
    except Exception as e:
        print(f"Final Send Error: {e}")
        await status_msg.edit_text("❌ **All Routes Busy!** YouTube strict block lagaya hai. Koshish karein ki thodi der baad link bhejien ya koi aur link try karein.")
    
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
    
