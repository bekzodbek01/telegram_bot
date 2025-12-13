import os
from pathlib import Path
import qrcode

QR_DIR = Path("static/qr")
QR_DIR.mkdir(parents=True, exist_ok=True)

def make_qr_for_staff(staff_id: int, bot_username: str = "SenBaholash_bot"):
    # Telegram deep link
    payload = f"https://t.me/{bot_username}?start=staff_{staff_id}"

    filename = QR_DIR / f"staff_{staff_id}.png"

    # Agar fayl yo‘q bo‘lsa — yangidan yaratamiz
    if not filename.exists():
        img = qrcode.make(payload)
        img.save(filename)

    # Qaytarish uchun STATIC yo‘l formatida beramiz:
    # masalan: static/qr/staff_11.png
    return f"static/qr/staff_{staff_id}.png"
