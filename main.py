import os
import re
import tempfile
from pytube import YouTube
import instaloader
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Extract URLs from text
def extract_urls(text):
    return re.findall(r'(https?://[^\s]+)', text)

# YouTube downloader using pytube
def download_youtube(url):
    yt = YouTube(url)
    stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
    if stream:
        return stream.download(output_path="downloads")
    return None

# Instagram downloader using instaloader
def download_instagram(url):
    L = instaloader.Instaloader(dirname_pattern="downloads", download_videos=True, save_metadata=False, download_comments=False)
    shortcode = url.rstrip('/').split('/')[-1]
    post_url = f"https://www.instagram.com/p/{shortcode}/"
    post = instaloader.Post.from_shortcode(L.context, shortcode)
    L.download_post(post, target=shortcode)
    return os.path.join("downloads", shortcode)

# Telegram bot handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    urls = extract_urls(msg.text or "")
    if not urls:
        await msg.reply_text("❌ No valid link found.")
        return

    for url in urls:
        await msg.reply_text(f"📥 Processing: {url}")
        try:
            filename = None
            if "youtube.com" in url or "youtu.be" in url:
                filename = download_youtube(url)
            elif "instagram.com" in url:
                folder = download_instagram(url)
                files = os.listdir(folder)
                for f in files:
                    filepath = os.path.join(folder, f)
                    if os.path.isfile(filepath) and os.path.getsize(filepath) < 48 * 1024 * 1024:
                        await msg.reply_document(document=open(filepath, 'rb'))
                        os.remove(filepath)
                continue  # skip general file reply for Instagram

            if filename and os.path.getsize(filename) < 48 * 1024 * 1024:
                await msg.reply_video(video=open(filename, 'rb'))
                os.remove(filename)
            elif filename:
                await msg.reply_text("⚠️ File too large for Telegram.")
        except Exception as e:
            await msg.reply_text(f"❌ Error: {str(e)}")

# Setup the bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    os.makedirs("downloads", exist_ok=True)
    app.run_polling()
