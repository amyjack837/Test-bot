import os
import re
import subprocess
import instaloader
from pytube import YouTube
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
COOKIE_FILE = "youtube_cookies.txt"
INSTA_CRED_FILE = "insta_credentials.txt"
ADMIN_PASSWORD = "Sohel"
pending_confirmations = {}

def extract_urls(text):
    return re.findall(r'(https?://[^\s]+)', text)

# Commands that require admin password
async def secure_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.message.text.strip().split()[0]
    if command not in ["/add", "/insta", "/delete", "/gram"]:
        await update.message.reply_text("❌ Unknown secure command.")
        return
    pending_confirmations[update.effective_user.id] = command
    await update.message.reply_text("🔐 Please reply with admin password to confirm this command.")

# Handle admin password reply
async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    if user_id in pending_confirmations:
        confirmed_command = pending_confirmations[user_id]
        if password == ADMIN_PASSWORD:
            del pending_confirmations[user_id]
            context.user_data["confirmed"] = confirmed_command
            await update.message.reply_text("✅ Password accepted. Now send the required file for " + confirmed_command)
        else:
            await update.message.reply_text("❌ Incorrect password. Access denied.")
    else:
        await handle_links(update, context)

# Add YouTube cookie
async def add_cookie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("confirmed") != "/add":
        return
    msg = update.message
    if msg.document and msg.document.file_name.endswith(".txt"):
        await msg.document.get_file().download_to_drive(COOKIE_FILE)
        context.user_data["confirmed"] = None
        await msg.reply_text("✅ YouTube cookie saved.")

# Delete YouTube cookie
async def delete_cookie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("confirmed") != "/delete":
        await update.message.reply_text("❌ You are not authorized to delete cookie. Use /delete first.")
        return
    if os.path.exists(COOKIE_FILE):
        os.remove(COOKIE_FILE)
        context.user_data["confirmed"] = None
        await update.message.reply_text("🗑️ YouTube cookie deleted.")

# Add Instagram credentials
async def add_insta_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("confirmed") != "/insta":
        return
    msg = update.message
    if msg.document and msg.document.file_name.endswith(".txt"):
        await msg.document.get_file().download_to_drive(INSTA_CRED_FILE)
        context.user_data["confirmed"] = None
        await msg.reply_text("✅ Instagram credentials saved.")

# Delete Instagram credentials
async def delete_insta_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("confirmed") != "/gram":
        await update.message.reply_text("❌ You are not authorized to delete Instagram credentials. Use /gram first.")
        return
    if os.path.exists(INSTA_CRED_FILE):
        os.remove(INSTA_CRED_FILE)
        context.user_data["confirmed"] = None
        await update.message.reply_text("🗑️ Instagram credentials deleted.")

# Login and download from Instagram
def get_instaloader_logged():
    if not os.path.exists(INSTA_CRED_FILE):
        raise Exception("⚠️ No Instagram credentials. Use /insta to upload them.")
    with open(INSTA_CRED_FILE, 'r') as f:
        for line in f:
            if ':' in line:
                username, password = line.strip().split(':', 1)
                try:
                    L = instaloader.Instaloader(dirname_pattern="downloads", download_videos=True)
                    L.login(username.strip(), password.strip())
                    return L
                except:
                    continue
    raise Exception("❌ Instagram login failed. Try updating credentials.")

def download_instagram(url):
    shortcode = url.rstrip('/').split('/')[-1]
    L = get_instaloader_logged()
    post = instaloader.Post.from_shortcode(L.context, shortcode)
    folder = os.path.join("downloads", shortcode)
    L.download_post(post, target=shortcode)
    return folder

def download_youtube(url):
    output_file = "downloads/%(title)s.%(ext)s"
    command = ["yt-dlp", url, "-o", output_file]
    if os.path.exists(COOKIE_FILE):
        command[1:1] = ["--cookies", COOKIE_FILE]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if "HTTP Error 403" in result.stderr or "cookies" in result.stderr:
        raise Exception("🔒 YouTube cookie expired or invalid.")
    return result

# Handle incoming links
async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    urls = extract_urls(update.message.text or "")
    for url in urls:
        try:
            if "instagram.com" in url:
                await update.message.reply_text("📥 Downloading Instagram post...")
                folder = download_instagram(url)
                for f in os.listdir(folder):
                    fp = os.path.join(folder, f)
                    if os.path.isfile(fp) and os.path.getsize(fp) < 48 * 1024 * 1024:
                        await update.message.reply_document(open(fp, 'rb'))
                        os.remove(fp)
            elif "youtube.com" in url or "youtu.be" in url:
                await update.message.reply_text("📥 Downloading YouTube video...")
                result = download_youtube(url)
                match = re.search(r"Destination: (.+)", result.stdout + result.stderr)
                if match:
                    filepath = match.group(1)
                    if os.path.exists(filepath) and os.path.getsize(filepath) < 48 * 1024 * 1024:
                        await update.message.reply_video(open(filepath, 'rb'))
                        os.remove(filepath)
                    else:
                        await update.message.reply_text("⚠️ File too large.")
        except Exception as e:
            await update.message.reply_text(str(e))

# Bot setup
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("add", secure_command))
app.add_handler(CommandHandler("insta", secure_command))
app.add_handler(CommandHandler("delete", secure_command))
app.add_handler(CommandHandler("gram", secure_command))
app.add_handler(CommandHandler("gram_delete", delete_insta_credentials))
app.add_handler(CommandHandler("cookie_delete", delete_cookie))
app.add_handler(MessageHandler(filters.Document.FILE_EXTENSION("txt"), add_cookie))
app.add_handler(MessageHandler(filters.Document.FILE_EXTENSION("txt"), add_insta_credentials))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password))

if __name__ == "__main__":
    os.makedirs("downloads", exist_ok=True)
    app.run_polling()
