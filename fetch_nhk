# NHK Easy News → nhk-easy.json 생성 (개인 JLPT 학습용 피드)
# GitHub Actions에서 정기 실행됨
import json
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

LIST_URL = "https://www3.nhk.or.jp/news/easy/news-list.json"
ARTICLE_URL = "https://www3.nhk.or.jp/news/easy/{id}/{id}.html"
MAX_ARTICLES = 10  # 최근 기사만 유지 (개인 학습용 — 아카이브하지 않음)

session = requests.Session()
session.headers["User-Agent"] = "Mozilla/5.0 (personal JLPT study feed)"


def fetch_list():
    r = session.get(LIST_URL, timeout=30)
    r.raise_for_status()
    data = json.loads(r.content.decode("utf-8-sig"))
    by_date = data[0] if isinstance(data, list) else data
    items = []
    for d in sorted(by_date.keys(), reverse=True)[:3]:  # 최근 3일치에서
        for a in by_date[d]:
            items.append({
                "id": a.get("news_id", ""),
                "date": d,
                "title": (a.get("title") or "").strip(),
            })
    return [i for i in items if i["id"]][:MAX_ARTICLES]


def fetch_article(news_id):
    r = session.get(ARTICLE_URL.format(id=news_id), timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")
    # 후리가나 제거
    for t in soup.select("rt, rp"):
        t.decompose()
    body_el = soup.select_one("#js-article-body") or soup.select_one(".article-body")
    if not body_el:
        return None
    text = body_el.get_text("\n")
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return text


def main():
    items = fetch_list()
    if not items:
        print("목록이 비어 있음 — 중단", file=sys.stderr)
        sys.exit(1)

    articles = []
    for it in items:
        try:
            body = fetch_article(it["id"])
        except Exception as e:
            print(f"기사 실패 {it['id']}: {e}", file=sys.stderr)
            continue
        if body:
            articles.append({**it, "body": body})

    if not articles:
        print("본문을 하나도 가져오지 못함 — 기존 파일 유지", file=sys.stderr)
        sys.exit(1)

    feed = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "NHK NEWS WEB EASY (personal study use)",
        "articles": articles,
    }
    with open("nhk-easy.json", "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=1)
    print(f"완료: 기사 {len(articles)}건 저장")


if __name__ == "__main__":
    main()
