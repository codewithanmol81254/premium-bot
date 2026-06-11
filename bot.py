import os
import re
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from yt_dlp import YoutubeDL

# --- FLASK WEB SERVER FOR 24/7 HOSTING ---
app = Flask('')

@app.route('/')
def home():
    return "🚀 Anmol's Ultra Premium Bot is Running 24/7 Successfully!"

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web_server)
    t.start()
# ----------------------------------------

API_TOKEN = "8951596090:AAFeX3jht3Yjm_v26CgUsHmiz0MVK-2-nPg"
db = {}

def format_duration(seconds):
    if not seconds: return "Unknown"
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins}:{secs:02d} Mins"

def extract_spotify_info_via_ydl(url):
    try:
        ydl_opts = {'extract_flat': True, 'skip_download': True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                title = info.get('title')
                artist = info.get('artist') or info.get('uploader')
                return f"{title} {artist}" if title and artist else title
    except Exception:
        pass
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ **WELCOME TO ANMOL'S PREMIUM BOT** ✨\n\n"
        "🔗 Mujhe kisi bhi video ya music ka link bhejien.\n"
        "⚡ Aapko milega sabse advance graphical user interface aur high quality downloads!"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        await update.message.reply_text("⚠️ **Invalid Link!** Please sahi URL bhejien.")
        return

    user_id = update.message.from_user.id
    status_msg = await update.message.reply_text("🔍 **Analyzing Link... Please wait.**")

    if re.search(r'spotify\.com', url, re.IGNORECASE):
        await status_msg.edit_text("🎵 **Spotify Link Detected! Extracting Details...**")
        song_details = extract_spotify_info_via_ydl(url)
        if not song_details:
            song_details = extract_spotify_info_via_ydl(url.split('?')[0])

        if song_details:
            db[user_id] = {"query": f"ytsearch:{song_details}", "is_spotify": True}
            await status_msg.edit_text(f"💎 **Found:** `{song_details}`\n⚡ Original 320kbps Audio extraction shuru...")
            await start_download(update, context, user_id, "mp3", status_msg)
        else:
            await status_msg.edit_text("❌ Is Spotify link se details nahi nikal payi. Naam text mein likh kar bhejien.")
        return

    try:
        with YoutubeDL({'skip_download': True, 'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Premium Media Asset')
            thumbnail = info.get('thumbnail') or info.get('thumbnails', [{}])[0].get('url')
            uploader = info.get('uploader', 'Unknown Creator')
            duration = format_duration(info.get('duration'))

        db[user_id] = {"query": url, "is_spotify": False}
        keyboard = [
            [InlineKeyboardButton("🎬 Cinematic Video (MP4)", callback_data="mp4")],
            [InlineKeyboardButton("🎵 Original Audio (320kbps MP3)", callback_data="mp3")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await status_msg.delete()

        caption_text = (
            f"📝 **TITLE:** `{title}`\n"
            f"👤 **CREATOR:** `{uploader}`\n"
            f"⏱️ **DURATION:** `{duration}`\n\n"
            f"✨ **Select format to download:**"
        )

        if thumbnail:
            await context.bot.send_photo(chat_id=update.message.chat_id, photo=thumbnail, caption=caption_text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(caption_text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        await status_msg.edit_text(f"❌ **Link scan nahi ho paya.**\nError: {str(e)}")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    choice = query.data
    await query.answer()

    if user_id not in db:
        await query.message.reply_text("❌ Session expired! Link phir se bhejien.")
        return

    await query.message.delete()
    status_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="⚙️ **[Processing] Dedicated server se high-speed link inject ho raha hai...**")
    await start_download(update, context, user_id, choice, status_msg)

async def start_download(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, choice, status_msg):
    search_query = db[user_id]["query"]
    chat_id = update.effective_chat.id

    if choice == "mp4":
        ydl_opts = {'format': 'best[ext=mp4]/best', 'outtmpl': '%(title)s.%(ext)s', 'restrictfilenames': True}
    else:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'restrictfilenames': True,
            'default_search': 'ytsearch',
            'noplaylist': True,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}]
        }

    try:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="🚀 **[Downloading] Fetching original media blocks...**")
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=True)
            if "entries" in info and info['entries']:
                video_data = info['entries'][0]
                filename = ydl.prepare_filename(video_data)
                title = video_data.get('title', 'Audio')
            else:
                filename = ydl.prepare_filename(info)
                title = info.get('title', 'Asset')
            
            if choice == "mp3":
                base, _ = os.path.splitext(filename)
                filename = base + ".mp3"

        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text="📤 **[Uploading] Pushing high quality file to Telegram Cloud...**")
        with open(filename, 'rb') as file_asset:
            if choice == "mp4":
                await context.bot.send_video(chat_id=chat_id, video=file_asset, caption=f"🎬 **{title}**\n\n⚡ *Downloaded via @Anmol_Bot*", parse_mode="Markdown")
            else:
                await context.bot.send_audio(chat_id=chat_id, audio=file_asset, title=title, caption=f"🎵 **{title}**\n\n⚡ *Downloaded via @Anmol_Bot*", parse_mode="Markdown")

        if os.path.exists(filename): os.remove(filename)
        await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
    except Exception as e:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"❌ **Download failed!**\nError: {str(e)}")

    if user_id in db: del db[user_id]

def main():
    keep_alive()
    application = Application.builder().token(API_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    application.add_handler(CallbackQueryHandler(button_click))
    print("🚀 Ultra Premium Visual Server Active...")
    application.run_polling()

if __name__ == '__main__':
    main()
  
