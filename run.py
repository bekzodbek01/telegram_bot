import subprocess
import time

def start_fastapi():
    return subprocess.Popen(
        ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001"]
    )

def start_bot():
    return subprocess.Popen(["python", "bot.py"])

if __name__ == "__main__":
    print("⏳ FastAPI ishga tushirilmoqda...")
    fastapi = start_fastapi()

    time.sleep(2)

    print("🤖 Telegram bot ishga tushirilmoqda...")
    bot = start_bot()

    print("🚀 FastAPI + Telegram bot birga ishlayapti!")
    print("\n🟦 ADMIN PANELGA KIRISH:")
    print("👉 http://127.0.0.1:8001/admin/staffs\n")

    try:
        fastapi.wait()
        bot.wait()
    except KeyboardInterrupt:
        print("\n⛔ Dastur to‘xtatildi!")
        fastapi.terminate()
        bot.terminate()
