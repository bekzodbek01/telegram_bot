import os
from pathlib import Path
import qrcode

QR_DIR = Path("static/qr")
QR_DIR.mkdir(parents=True, exist_ok=True)

def make_qr_for_staff(staff_id: int, bot_username: str = "SenBaholash_bot"):
    # Telegram deep link with start param (e.g., t.me/SenBaholash_bot?start=staff_123)
    payload = f"https://t.me/{bot_username}?start=staff_{staff_id}"
    img = qrcode.make(payload)
    filename = QR_DIR / f"staff_{staff_id}.png"
    img.save(filename)
    return str(filename), payload
