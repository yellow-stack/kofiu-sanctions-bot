import os
import json
import requests

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

API_URL = (
    "https://www.kofiu.go.kr/cmn/board/selectLawList.do"
    "?selScope=&subSech=&size=10&page=1&seCd=001"
    "&ntcnYardOrdrNo=&lawordInfoOrdrNo="
)
KEYWORD = "금융거래등제한대상자"
STATE_FILE = "last_seen.json"
VIEW_BASE_URL = "https://www.kofiu.go.kr/kor/law/announce_view.do?lawordInfoOrdrNo="


def load_last_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_ordr_no": None}


def save_last_seen(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_notices():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; KoFIU-Bot/1.0)"}
    resp = requests.get(API_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("result", [])


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
    print("KoFIU 금융거래등제한대상자 모니터링 시작...")

    state = load_last_seen()
    last_ordr_no = state.get("last_ordr_no")

    notices = fetch_notices()
    print(f"총 {len(notices)}건 조회됨")

    # 키워드 필터링
    filtered = [
        n for n in notices
        if KEYWORD in n.get("lawordInfoSjNm", "")
    ]
    print(f"'{KEYWORD}' 관련 공고: {len(filtered)}건")

    if not filtered:
        print("관련 공고 없음")
        return

    # 가장 최신 공고 (첫 번째)
    latest = filtered[0]
    latest_ordr_no = latest.get("lawordInfoOrdrNo")
    latest_title = latest.get("lawordInfoSjNm", "")
    latest_date = latest.get("lawordInfoRgiDt", "")[:10]
    view_url = VIEW_BASE_URL + str(latest_ordr_no)

    print(f"최신 공고: [{latest_ordr_no}] {latest_title} ({latest_date})")
    print(f"이전 저장값: {last_ordr_no}")

    if last_ordr_no is None:
        # 최초 실행: 현재 최신값 저장하고 알림 발송
        msg = (
            "\U0001F6A8 <b>[KoFIU] 금융거래등제한대상자 고시 모니터링 시작</b>\n\n"
            f"\U0001F4CB 현재 최신 공고:\n"
            f"  <b>{latest_title}</b>\n"
            f"  \U0001F4C5 등록일: {latest_date}\n"
            f"  \U0001F517 <a href=\"{view_url}\">공고 바로가기</a>\n\n"
            "앞으로 새 공고 등록 시 알림을 드립니다."
        )
        send_telegram(msg)
        save_last_seen({"last_ordr_no": latest_ordr_no})
        print("최초 실행 완료 - 현재 최신값 저장")
    elif str(latest_ordr_no) != str(last_ordr_no):
        # 새 공고 발견
        msg = (
            "\U0001F6A8 <b>[KoFIU] 금융거래등제한대상자 고시 업데이트!</b>\n\n"
            f"\U0001F4CB 신규 공고:\n"
            f"  <b>{latest_title}</b>\n"
            f"  \U0001F4C5 등록일: {latest_date}\n"
            f"  \U0001F517 <a href=\"{view_url}\">공고 바로가기</a>"
        )
        send_telegram(msg)
        save_last_seen({"last_ordr_no": latest_ordr_no})
        print(f"새 공고 감지 및 알림 발송: {latest_title}")
    else:
        print("변경사항 없음")
        # 매일 아침 현황 요약 알림
        msg = (
            "\u2705 <b>[KoFIU] 금융거래등제한대상자 모니터링</b>\n\n"
            "변경사항 없습니다.\n\n"
            f"\U0001F4CB 최근 공고:\n"
            f"  {latest_title}\n"
            f"  \U0001F4C5 {latest_date}\n"
            f"  \U0001F517 <a href=\"{view_url}\">공고 바로가기</a>"
        )
        send_telegram(msg)
        print("변경 없음 알림 발송 완료")


if __name__ == "__main__":
    main()
