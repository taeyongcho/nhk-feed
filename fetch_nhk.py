# NHK Easy News → nhk-easy.json 생성 (개인 JLPT 학습용 피드) — v2 진단 강화판
import json
import re
import sys
import time
import traceback
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

LIST_URL = "https://www3.nhk.or.jp/news/easy/news-list.json"
ARTICLE_URL = "https://www3.nhk.or.jp/news/easy/{id}/{id}.html"
MAX_ARTICLES = 10

session = requests.Session()
# 일반 브라우저와 동일한 헤더 (커스텀 UA는 차단될 수 있음)
session.headers.update({
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.8",
    "Referer": "https://www3.nhk.or.jp/news/easy/",
})


def get(url, tries=3):
    """상태코드·본문 앞부분까지 로그로 남기는 GET (재시도 포함)"""
    last = None
    for attempt in range(1, tries + 1):
        try:
            r = session.get(url, timeout=30)
            print(f"  GET {url} → HTTP {r.status_code} ({len(r.content)} bytes)")
            if r.status_code == 200:
                return r
            last = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  접속 오류 (시도 {attempt}/{tries}): {e}")
            last = e
        time.sleep(3 * attempt)
    raise last


def fetch_list():
    r = get(LIST_URL)
    data = json.loads(r.content.decode("utf-8-sig"))
    by_date = data[0] if isinstance(data, list) else data
    print(f"  목록 날짜: {sorted(by_date.keys(), reverse=True)[:3]}")
    items = []
    for d in sorted(by_date.keys(), reverse=True)[:3]:
        for a in by_date[d]:
            items.append({
                "id": a.get("news_id", ""),
                "date": d,
                "title": (a.get("title") or "").strip(),
            })
    return [i for i in items if i["id"]][:MAX_ARTICLES]


def fetch_article(news_id):
    r = get(ARTICLE_URL.format(id=news_id))
    soup = BeautifulSoup(r.content, "html.parser")
    for t in soup.select("rt, rp"):
        t.decompose()
    body_el = soup.select_one("#js-article-body") or soup.select_one(".article-body")
    if not body_el:
        print(f"  ⚠️ {news_id}: 본문 요소를 찾지 못함 (페이지 구조 변경 가능)")
        return None
    text = body_el.get_text("\n")
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return text


def main():
    print(f"시작: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    items = fetch_list()
    print(f"기사 후보 {len(items)}건")
    if not items:
        sys.exit("❌ 목록이 비어 있음")

    articles = []
    for it in items:
        try:
            body = fetch_article(it["id"])
        except Exception as e:
            print(f"  ❌ 기사 실패 {it['id']}: {e}")
            continue
        if body:
            articles.append({**it, "body": body})
        time.sleep(1)  # 예의상 간격

    print(f"본문 확보 {len(articles)}건")
    if not articles:
        sys.exit("❌ 본문을 하나도 가져오지 못함")

    feed = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "NHK NEWS WEB EASY (personal study use)",
        "articles": articles,
    }
    with open("nhk-easy.json", "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=1)
    print(f"✅ 완료: nhk-easy.json 저장 (기사 {len(articles)}건)")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(1)
