from __future__ import annotations

import os
import requests
from dotenv import load_dotenv


load_dotenv()


def get_config() -> tuple[str, str]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    return token, chat_id


def send_message(message: str) -> bool:
    token, chat_id = get_config()
    if not token or not chat_id:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=30)
        data = resp.json()
        if not data.get("ok"):
            print(f"Telegram API error: {data}")
            return False
        return True
    except Exception as exc:
        print(f"Telegram send failed: {exc}")
        return False


if __name__ == "__main__":
    token, chat_id = get_config()
    print("TELEGRAM_BOT_TOKEN:", token)
    print("TELEGRAM_CHAT_ID:", chat_id)
    send_message("Test message from Data Marketplace API.")
