import logging
import requests
from aiogram import Bot, Dispatcher, executor, types

# --- BOT TOKEN KIRIT ---
BOT_TOKEN = "8524264464:AAHEvfJmM0bM2LvEY_CXn0DZDcAPEpu0wEY"

# --- FASTAPI MANZILI ---
API_BASE = "http://localhost:8001"   # FastAPI port

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)


# /start deep-link handler
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    args = message.get_args()     # MUHIM: staff_123 shu yerga tushadi!

    # deep-link bor bo‘lsa
    if args and args.startswith("staff_"):
        staff_id = args.split("_")[1]

        # tugmalarni yasash
        keyboard = types.inline_keyboard.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("A'lo 👍", callback_data=f"vote:{staff_id}:like"),
            types.InlineKeyboardButton("Yaxshi 🙂", callback_data=f"vote:{staff_id}:neutral"),
            types.InlineKeyboardButton("Yomon 👎", callback_data=f"vote:{staff_id}:dislike")
        )

        await message.answer(
            f"Xodim ID: {staff_id}\nBahoni tanlang:",
            reply_markup=keyboard
        )

    else:
        await message.answer("QR kodi orqali kirish kerak 🙂")


# Tugma bosilganda
@dp.callback_query_handler(lambda c: c.data.startswith("vote"))
async def vote_handler(callback: types.CallbackQuery):
    _, staff_id, kind = callback.data.split(":")

    # backendga yuboramiz
    try:
        requests.get(f"{API_BASE}/vote/{staff_id}/{kind}")
    except:
        await callback.answer("Serverga ulanib bo‘lmadi!", show_alert=True)
        return

    # javob
    await callback.answer("Rahmat! Baho qabul qilindi!")
    await callback.message.edit_text("Baho berildi 😊")


# Polling mode (oddiy)
if __name__ == '__main__':
    executor.start_polling(dp)


import threading
import subprocess

def run_bot():
    subprocess.Popen(["python", "bot.py"])

# FastAPI yuklanganda botni ham ishga tushiramiz
@app.on_event("startup")
def start_bot():
    t = threading.Thread(target=run_bot)
    t.start()
