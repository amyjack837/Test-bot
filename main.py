import os
import re
from yt_dlp import YoutubeDL
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

YDL_OPTS = {
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'format': 'bestvideo+bestaudio/best',
    'noplaylist': True,
    'quiet': True,
}

def extract_urls(text):
    return re.findall(r'(https?://[^\s]+)', text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    urls = extract_urls(msg.text or "")
    if not urls:
        await msg.reply_text("❌ No valid link found.")
        return

    for url in urls:
        await msg.reply_text(f"📥 Downloading: {url}")
        try:
            with YoutubeDL(YDL_OPTS) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

                if os.path.getsize(filename) > 48 * 1024 * 1024:
                    await msg.reply_text("⚠️ File too large for Telegram.")
                else:
                    if filename.endswith(('.mp4', '.mkv')):
                        await msg.reply_video(video=open(filename, 'rb'))
                    else:
                        await msg.reply_document(document=open(filename, 'rb'))

                os.remove(filename)
        except Exception as e:
            await msg.reply_text(f"❌ Error: {str(e)}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    os.makedirs("downloads", exist_ok=True)
    app.run_polling()