import os
import re
import asyncio
import logging
import tempfile
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
 
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.constants import ParseMode
import yt_dlp
import imageio_ffmpeg
 
# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
LOCAL_API_URL = os.environ.get("LOCAL_API_URL", "")  # যেমন: http://telegram-api-server.railway.internal:8081
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@your_channel_username")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
 
CREDIT = "\n\n━━━━━━━━━━━━━━━━━━━━━\n👨‍💻 *Developed by:* RH RATUL"
 
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
 
# ─── /start ───────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "বন্ধু"
    await update.message.reply_text(
        f"╔══════════════════════╗\n"
        f"║   🎬 RH EPISODE BOT   ║\n"
        f"╚══════════════════════╝\n\n"
        f"👋 স্বাগতম, *{name}*!\n\n"
        f"⚡ *আমি কী করতে পারি?*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ YouTube ভিডিও ডাউনলোড\n"
        f"✅ Notification bot থেকে forward করলেই কাজ\n"
        f"✅ Auto Channel Upload\n\n"
        f"📌 *কীভাবে ব্যবহার করবেন?*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"▶️ YouTube link পাঠান\n"
        f"▶️ অথবা Notification bot থেকে forward করুন\n\n"
        f"🔥 *Bot 24/7 Active!*\n\n"
        f"📢 *Channel:* {CHANNEL_ID}"
        f"{CREDIT}",
        parse_mode=ParseMode.MARKDOWN
    )
 
# ─── URL DETECT ───────────────────────────────────────────────────────────────
YT_PATTERN = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)"
    r"[\w\-]+"
)
 
def find_yt_url(message) -> str | None:
    for src in [message.text, message.caption]:
        m = YT_PATTERN.search(src or "")
        if m:
            return m.group(0)
    for elist in [message.entities, message.caption_entities]:
        for e in (elist or []):
            if e.url:
                m = YT_PATTERN.search(e.url)
                if m:
                    return m.group(0)
    if message.reply_markup:
        for row in (message.reply_markup.inline_keyboard or []):
            for btn in row:
                if btn.url:
                    m = YT_PATTERN.search(btn.url)
                    if m:
                        return m.group(0)
    return None
 
# ─── DOWNLOAD ─────────────────────────────────────────────────────────────────
def download_video(url: str, tmp_dir: str):
    out_tmpl = os.path.join(tmp_dir, "%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]/best",
        "merge_output_format": "mp4",
        "outtmpl": out_tmpl,
        "ffmpeg_location": FFMPEG,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "geo_bypass_country": "US",
        "retries": 5,
        "fragment_retries": 5,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "android_vr", "web", "mweb"],
            }
        },
    }
 
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
        # extension fix
        for ext in [".webm", ".mkv"]:
            if path.with_suffix(ext).exists():
                path = path.with_suffix(ext)
        if not path.exists():
            path = path.with_suffix(".mp4")
        if not path.exists():
            files = list(Path(tmp_dir).glob("*.*"))
            if files:
                path = max(files, key=lambda f: f.stat().st_size)
        return path, info.get("title", "Episode")
 
# ─── HANDLER ──────────────────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return
 
    url = find_yt_url(msg)
    if not url:
        await msg.reply_text(
            f"❓ *YouTube link পাওয়া যায়নি!*\n\n"
            f"▶️ YouTube link পাঠান বা Notification bot থেকে forward করুন"
            f"{CREDIT}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
 
    chat_id = update.effective_chat.id
    status = await msg.reply_text(
        f"⬇️ *ডাউনলোড হচ্ছে...*\n_একটু অপেক্ষা করুন_{CREDIT}",
        parse_mode=ParseMode.MARKDOWN
    )
 
    try:
        with tempfile.TemporaryDirectory() as tmp:
            loop = asyncio.get_event_loop()
            path, title = await loop.run_in_executor(None, download_video, url, tmp)
 
            size_mb = path.stat().st_size / (1024 * 1024)
            logger.info(f"Downloaded: {title} ({size_mb:.1f} MB)")
 
            if size_mb > 1900:
                await status.edit_text(f"❌ ফাইল অনেক বড়।{CREDIT}", parse_mode=ParseMode.MARKDOWN)
                return
 
            await status.edit_text(
                f"📤 *আপলোড হচ্ছে...*\n_📦 {size_mb:.1f} MB_{CREDIT}",
                parse_mode=ParseMode.MARKDOWN
            )
 
            caption = (
                f"🎬 *{title}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔗 [YouTube]({url})"
                f"{CREDIT}"
            )
 
            with open(path, "rb") as f:
                sent = await context.bot.send_video(
                    chat_id=chat_id,
                    video=f,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    supports_streaming=True,
                    read_timeout=600,
                    write_timeout=600,
                    connect_timeout=60,
                    pool_timeout=600,
                )
 
            await context.bot.forward_message(
                chat_id=CHANNEL_ID,
                from_chat_id=chat_id,
                message_id=sent.message_id,
            )
 
            await status.edit_text(
                "╔══════════════════════╗\n"
                "║   ✅ সম্পন্ন হয়েছে!   ║\n"
                "╚══════════════════════╝\n\n"
                "📥 আপনাকে পাঠানো হয়েছে\n"
                "📢 Channel এও upload হয়েছে"
                f"{CREDIT}",
                parse_mode=ParseMode.MARKDOWN
            )
 
    except Exception as e:
        logger.error(f"Error: {e}")
        await status.edit_text(
            f"❌ *ব্যর্থ হয়েছে*\n\n`{e}`{CREDIT}",
            parse_mode=ParseMode.MARKDOWN
        )
 
# ─── KEEP ALIVE ───────────────────────────────────────────────────────────────
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"RH Episode Bot is alive!")
    def log_message(self, *args):
        pass
 
def run_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), PingHandler).serve_forever()
 
# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    threading.Thread(target=run_server, daemon=True).start()
    logger.info("Keep-alive started.")
    builder = Application.builder().token(BOT_TOKEN)
    if LOCAL_API_URL:
        builder = builder.base_url(f"{LOCAL_API_URL}/bot").base_file_url(f"{LOCAL_API_URL}/file/bot")
    app = builder.build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
 
if __name__ == "__main__":
    main()
