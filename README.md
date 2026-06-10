# 🤖 Telegram Episode Downloader Bot — Render.com Deploy

## ✅ Step 1: GitHub এ upload করো

1. [github.com](https://github.com) এ account খোলো (free)
2. New repository বানাও (যেকোনো নাম, যেমন `episode-bot`)
3. এই ৩টা file upload করো:
   - `bot.py`
   - `requirements.txt`
   - `render.yaml`

---

## ✅ Step 2: Render.com এ deploy করো

1. [render.com](https://render.com) এ **GitHub দিয়ে** login করো (card লাগবে না)
2. **New → Background Worker** click করো
3. তোমার GitHub repo select করো
4. এই settings দাও:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
5. **Environment Variables** এ দুটো add করো:
   - `BOT_TOKEN` → তোমার bot token (@BotFather থেকে)
   - `CHANNEL_ID` → তোমার channel (যেমন `@mychannel`)
6. **Deploy** চাপো — হয়ে যাবে! ✅

---

## ✅ Step 3: Bot কে Channel Admin করো

Telegram এ তোমার channel এ গিয়ে bot কে **Admin** বানাও,
"Post Messages" permission দাও।

---

## 🔄 Bot কীভাবে কাজ করে?

1. Notification bot থেকে message **forward** করো তোমার bot এ
2. Bot YouTube link detect করবে
3. **720p** তে download করবে
4. **তোমাকে** send করবে
5. তারপর **Channel এ** forward করবে
6. Temp file automatically delete হয়ে যাবে

---

## ⚠️ Render Free Plan সীমাবদ্ধতা

- মাঝে মাঝে **spin down** হতে পারে (প্রথম request এ 30-50 sec দেরি)
- **Background Worker** type select করলে এই সমস্যা কম হয়
