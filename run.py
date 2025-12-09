import subprocess
import time

# FastAPI ni ishga tushiramiz
fastapi = subprocess.Popen(["uvicorn", "main:app", "--port", "8001"])

# Telegram botni ishga tushiramiz
time.sleep(2)  # server ko‘tarilishini kutish
bot = subprocess.Popen(["python", "bot.py"])

print("FastAPI + Telegram bot birga ishlayapti!")

fastapi.wait()
bot.wait()
