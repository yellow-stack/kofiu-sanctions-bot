import os
import requests
from datetime import datetime, timedelta, timezone

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

STORY_URL = "https://story.pay.naver.com/popular"

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("에러: 텔레그램 토큰 정보가 없습니다.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    resp = requests.post(url, json=payload, timeout=30)
    return resp.ok

def main():
    KST = timezone(timedelta(hours=9))
    today = datetime.now(KST).strftime('%Y-%m-%d')

    print(f"네이버페이 머니스토리 알림 발송 ({today})")

    msg = (
        "\U0001F4B0 <b>[네이버페이] 머니스토리 인기글</b>\n\n"
        f"\U0001F4C5 {today}\n\n"
        f"\U0001F517 <a href=\"{STORY_URL}\">머니스토리 바로가기</a>\n"
        f"{STORY_URL}"
    )

    if send_telegram(msg):
        print("알림 발송 완료")
    else:
        print("알림 발송 실패")

if __name__ == "__main__":
    main()
