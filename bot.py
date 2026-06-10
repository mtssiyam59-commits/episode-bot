import os
import re
import asyncio
import logging
import tempfile
from pathlib import Path
 
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.constants import ParseMode
import yt_dlp
 
# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@your_channel_username")
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
 
CREDIT = "\n\n━━━━━━━━━━━━━━━━━━━━━\n👨‍💻 *Developed by:* RH RATUL"
 
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
 
# ─── /start HANDLER ───────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "বন্ধু"
    msg = (
        f"╔══════════════════════╗\n"
        f"║   🎬 RH EPISODE BOT   ║\n"
        f"╚══════════════════════╝\n\n"
        f"👋 স্বাগতম, *{name}*!\n\n"
        f"⚡ *আমি কী করতে পারি?*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ YouTube ভিডিও ডাউনলোড\n"
        f"✅ Notification bot থেকে forward করলেই কাজ\n"
        f"✅ 720p HD Quality\n"
        f"✅ Channel এ Auto Upload\n\n"
        f"📌 *কীভাবে ব্যবহার করবেন?*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"▶️ যেকোনো YouTube link পাঠান\n"
        f"▶️ অথবা Notification bot থেকে forward করুন\n\n"
        f"🔥 *Bot টি 24/7 Active আছে!*\n\n"
        f"📢 *Channel:* {CHANNEL_ID}"
        f"{CREDIT}"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
 
# ─── YouTube URL DETECT ───────────────────────────────────────────────────────
YT_PATTERN = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)"
    r"[\w\-]+"
)
 
def extract_yt_url(text: str) -> str | None:
    match = YT_PATTERN.search(text or "")
    return match.group(0) if match else None
 
def find_yt_url_in_message(message) -> str | None:
    for src in [message.text, message.caption]:
        url = extract_yt_url(src)
        if url:
            return url
    for entity_list in [message.entities, message.caption_entities]:
        for entity in (entity_list or []):
            if entity.url:
                url = extract_yt_url(entity.url)
                if url:
                    return url
    if message.reply_markup:
        for row in (message.reply_markup.inline_keyboard or []):
            for button in row:
                if button.url:
                    url = extract_yt_url(button.url)
                    if url:
                        return url
    return None
 
# ─── DOWNLOAD ─────────────────────────────────────────────────────────────────
def download_video(url: str, tmp_dir: str) -> tuple[Path, str]:
    ydl_opts = {
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(tmp_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
 
    # cookies.txt থাকলে use করো
    if os.path.exists(COOKIES_FILE):
        ydl_opts["cookiefile"] = COOKIES_FILE
        logger.info("Using cookies.txt for authentication")
 
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = Path(ydl.prepare_filename(info))
        if not file_path.exists():
            file_path = file_path.with_suffix(".mp4")
        return file_path, info.get("title", "Episode")
 
# ─── MESSAGE HANDLER ──────────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message:
        return
 
    yt_url = find_yt_url_in_message(message)
    if not yt_url:
        await message.reply_text(
            "❓ *YouTube link পাওয়া যায়নি!*\n\n"
            "▶️ একটি YouTube link পাঠান অথবা\n"
            "▶️ Notification bot থেকে forward করুন"
            f"{CREDIT}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
 
    chat_id = update.effective_chat.id
    status_msg = await message.reply_text(
        f"⏳ *প্রসেস শুরু হচ্ছে...*{CREDIT}",
        parse_mode=ParseMode.MARKDOWN
    )
 
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            await status_msg.edit_text(
                f"🔍 *ভিডিও খোঁজা হচ্ছে...*{CREDIT}",
                parse_mode=ParseMode.MARKDOWN
            )
            await status_msg.edit_text(
                f"⬇️ *720p HD ডাউনলোড হচ্ছে...*\n_একটু অপেক্ষা করুন_{CREDIT}",
                parse_mode=ParseMode.MARKDOWN
            )
            loop = asyncio.get_event_loop()
            file_path, title = await loop.run_in_executor(None, download_video, yt_url, tmp_dir)
 
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"Downloaded: {title} ({file_size_mb:.1f} MB)")
 
            if file_size_mb > 1900:
                await status_msg.edit_text(
                    f"❌ ফাইল অনেক বড় (>1.9 GB)। পাঠানো সম্ভব নয়।{CREDIT}",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
 
            await status_msg.edit_text(
                f"📤 *Telegram এ আপলোড হচ্ছে...*\n_📦 Size: {file_size_mb:.1f} MB_{CREDIT}",
                parse_mode=ParseMode.MARKDOWN
            )
 
            caption = (
                f"🎬 *{title}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📺 *Quality:* 720p HD\n"
                f"🔗 *Source:* [YouTube]({yt_url})"
                f"{CREDIT}"
            )
 
            with open(file_path, "rb") as f:
                sent = await context.bot.send_video(
                    chat_id=chat_id,
                    video=f,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    supports_streaming=True,
                )
 
            await context.bot.forward_message(
                chat_id=CHANNEL_ID,
                from_chat_id=chat_id,
                message_id=sent.message_id,
            )
 
            await status_msg.edit_text(
                "╔══════════════════════╗\n"
                "║   ✅ সম্পন্ন হয়েছে!   ║\n"
                "╚══════════════════════╝\n\n"
                "📥 ভিডিও আপনাকে পাঠানো হয়েছে\n"
                "📢 Channel এও আপলোড হয়েছে"
                f"{CREDIT}",
                parse_mode=ParseMode.MARKDOWN
            )
 
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Download error: {e}")
        await status_msg.edit_text(
            f"❌ *ডাউনলোড ব্যর্থ হয়েছে*\n\n`{e}`{CREDIT}",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(
            f"❌ *সমস্যা হয়েছে*\n\n`{e}`{CREDIT}",
            parse_mode=ParseMode.MARKDOWN
        )
 
# ─── KEEP ALIVE ───────────────────────────────────────────────────────────────
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
 
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"RH Episode Bot is alive!")
    def log_message(self, *args):
        pass
 
def run_ping_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    server.serve_forever()
 
# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    threading.Thread(target=run_ping_server, daemon=True).start()
    logger.info("Keep-alive server started.")
 
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
 
    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
 
if __name__ == "__main__":
    main()
