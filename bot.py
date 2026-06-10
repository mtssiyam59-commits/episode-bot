import os
import re
import asyncio
import logging
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import yt_dlp

# ─── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.environ.get("BOT_TOKEN", "8241770582:AAEMIco0udyUQGloio12uggoBCou0cCyks8")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@episode1249")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── YouTube URL DETECT ────────────────────────────────────────────────────────
YT_PATTERN = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)"
    r"[\w\-]+"
)

def extract_yt_url(text: str) -> str | None:
    match = YT_PATTERN.search(text or "")
    return match.group(0) if match else None

# ─── DOWNLOAD (temp directory use করে) ───────────────────────────────────────
def download_video(url: str, tmp_dir: str) -> tuple[Path, str]:
    ydl_opts = {
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(tmp_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = Path(ydl.prepare_filename(info))
        if not file_path.exists():
            file_path = file_path.with_suffix(".mp4")
        return file_path, info.get("title", "Episode")

# ─── HANDLER ──────────────────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    text = message.text or message.caption or ""

    yt_url = extract_yt_url(text)
    if not yt_url:
        return

    chat_id = update.effective_chat.id
    status_msg = await message.reply_text("⬇️ *Downloading 720p...* please wait", parse_mode=ParseMode.MARKDOWN)

    try:
        # temp folder এ download করো — Render restart এ auto clean হয়
        with tempfile.TemporaryDirectory() as tmp_dir:
            await status_msg.edit_text("⬇️ *Downloading 720p video...*", parse_mode=ParseMode.MARKDOWN)
            loop = asyncio.get_event_loop()
            file_path, title = await loop.run_in_executor(None, download_video, yt_url, tmp_dir)

            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"Downloaded: {title} ({file_size_mb:.1f} MB)")

            if file_size_mb > 1900:
                await status_msg.edit_text("❌ File too large (>1.9 GB). Cannot send via Telegram.")
                return

            await status_msg.edit_text("📤 *Uploading to Telegram...*", parse_mode=ParseMode.MARKDOWN)
            caption = f"🎬 *{title}*\n🔗 [Source]({yt_url})"

            # User কে পাঠাও
            with open(file_path, "rb") as f:
                sent = await context.bot.send_video(
                    chat_id=chat_id,
                    video=f,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    supports_streaming=True,
                )

            # Channel এ forward করো (same file_id reuse — extra upload লাগবে না)
            await context.bot.forward_message(
                chat_id=CHANNEL_ID,
                from_chat_id=chat_id,
                message_id=sent.message_id,
            )

            await status_msg.edit_text("✅ *Done! Sent to you & the channel.*", parse_mode=ParseMode.MARKDOWN)

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Download error: {e}")
        await status_msg.edit_text(f"❌ Download failed:\n`{e}`", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(f"❌ Error: `{e}`", parse_mode=ParseMode.MARKDOWN)

# ─── KEEP ALIVE (Render free plan এ sleep এড়াতে) ────────────────────────────
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def log_message(self, *args):
        pass  # server log বন্ধ

def run_ping_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    server.serve_forever()

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    # Render কে জাগিয়ে রাখতে HTTP server background এ চালাও
    threading.Thread(target=run_ping_server, daemon=True).start()
    logger.info("Keep-alive server started.")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
