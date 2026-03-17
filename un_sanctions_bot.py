import os
import json
import re
import requests
from xml.etree import ElementTree as ET

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

XML_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
PAGE_URL = "https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list"
STATE_FILE = "un_last_seen.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def load_last_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_last_seen(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def format_date(date_str):
    """2026-03-16T23:00:06.145Z -> 2026-03-16"""
    if not date_str:
        return "unknown"
    return date_str[:10]


def fetch_xml_stats():
    resp = requests.get(XML_URL, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    last_modified = root.get('dateGenerated', '') or root.get('date', '')
    individuals = root.findall('.//{*}INDIVIDUAL') or root.findall('.//INDIVIDUAL')
    entities = root.findall('.//{*}ENTITY') or root.findall('.//ENTITY')
    ind_count = len(individuals)
    ent_count = len(entities)
    print(f"XML 파싱 완료: 개인 {ind_count}명, 단체 {ent_count}개, 생성일: {last_modified}")
    return {
        "last_modified": last_modified,
        "individuals": ind_count,
        "entities": ent_count
    }


def fetch_page_stats():
    resp = requests.get(PAGE_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    text = resp.text
    date_match = re.search(r'last updated on (\d+ \w+ \d{4})', text)
    last_updated = date_match.group(1) if date_match else "unknown"
    ind_match = re.search(r'Individuals \((\d+) individuals\)', text)
    ind_count = int(ind_match.group(1)) if ind_match else 0
    ent_match = re.search(r'Entities and other groups \((\d+) entities\)', text)
    ent_count = int(ent_match.group(1)) if ent_match else 0
    print(f"페이지 파싱: 최종업데이트={last_updated}, 개인={ind_count}, 단체={ent_count}")
    return {
        "last_modified": last_updated,
        "individuals": ind_count,
        "entities": ent_count
    }


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


def fmt_diff(n):
    if n > 0:
        return f"<b>+{n} \U0001F4C8</b>"
    elif n < 0:
        return f"<b>{n} \U0001F4C9</b>"
    else:
        return "<b>변동없음</b>"


def main():
    print("UN 통합 제재대상자 명단 모니터링 시작...")

    state = load_last_seen()

    try:
        current = fetch_xml_stats()
    except Exception as e:
        print(f"XML 파싱 실패: {e}, 페이지 파싱으로 전환")
        try:
            current = fetch_page_stats()
        except Exception as e2:
            print(f"페이지 파싱도 실패: {e2}")
            send_telegram("\u26a0\ufe0f [UN 제재명단] 데이터 조회 실패. 수동 확인 필요.\n" + PAGE_URL)
            return

    last_modified = current["last_modified"]
    last_modified_short = format_date(last_modified)
    ind_count = current["individuals"]
    ent_count = current["entities"]
    total = ind_count + ent_count

    prev_modified = state.get("last_modified")
    prev_modified_short = format_date(prev_modified) if prev_modified else None
    prev_ind = state.get("individuals", 0)
    prev_ent = state.get("entities", 0)
    prev_total = prev_ind + prev_ent

    ind_diff = ind_count - prev_ind
    ent_diff = ent_count - prev_ent
    total_diff = total - prev_total

    print(f"현재: {last_modified} / 개인 {ind_count} / 단체 {ent_count} / 합계 {total}")
    print(f"이전: {prev_modified} / 개인 {prev_ind} / 단체 {prev_ent} / 합계 {prev_total}")

    if not prev_modified:
        msg = (
            "\U0001F30D <b>[UN] 통합 제재대상자 명단 모니터링 시작</b>\n\n"
            f"\U0001F4C5 UN 명단 최종 업데이트: <b>{last_modified_short}</b>\n"
            f"\U0001F465 개인: <b>{ind_count:,}명</b>\n"
            f"\U0001F3E2 단체: <b>{ent_count:,}개</b>\n"
            f"\U0001F4CA 합계: <b>{total:,}건</b>\n\n"
            f"\U0001F517 <a href=\"{PAGE_URL}\">명단 바로가기</a>\n"
            f"{PAGE_URL}\n\n"
            "앞으로 변경 시 알림을 드립니다."
        )
        send_telegram(msg)
        save_last_seen(current)
        print("최초 실행 완료")

    elif last_modified != prev_modified or total != prev_total:
        msg = (
            "\U0001F6A8 <b>[UN] 통합 제재대상자 명단 업데이트!</b>\n\n"
            f"\U0001F4C5 UN 명단 최종 업데이트: <b>{last_modified_short}</b>\n"
            f"   (이전: {prev_modified_short})\n\n"
            f"\U0001F465 개인: <b>{ind_count:,}명</b> ({fmt_diff(ind_diff)})\n"
            f"\U0001F3E2 단체: <b>{ent_count:,}개</b> ({fmt_diff(ent_diff)})\n"
            f"\U0001F4CA 합계: <b>{total:,}건</b> (전체 {fmt_diff(total_diff)})\n\n"
            f"\U0001F517 <a href=\"{PAGE_URL}\">명단 바로가기</a>\n"
            f"{PAGE_URL}"
        )
        send_telegram(msg)
        save_last_seen(current)
        print("변경 감지 알림 발송 완료")

    else:
        msg = (
            "\u2705 <b>[UN] 통합 제재대상자 명단 모니터링</b>\n\n"
            "변경사항 없습니다.\n\n"
            f"\U0001F4C5 UN 명단 최종 업데이트: <b>{last_modified_short}</b>\n"
            f"\U0001F465 개인: <b>{ind_count:,}명</b>\n"
            f"\U0001F3E2 단체: <b>{ent_count:,}개</b>\n"
            f"\U0001F4CA 합계: <b>{total:,}건</b>\n\n"
            f"\U0001F517 <a href=\"{PAGE_URL}\">명단 바로가기</a>\n"
            f"{PAGE_URL}"
        )
        send_telegram(msg)
        print("변경 없음 알림 발송 완료")


if __name__ == "__main__":
    main()
