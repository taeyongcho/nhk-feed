# -*- coding: utf-8 -*-
"""
RSS + AI 쉬운 일본어 뉴스 피드 v3
────────────────────────────────
① 일본 언론사 RSS에서 오늘의 실제 헤드라인 수집 (마이니치·아사히 등)
② Claude가 그중 5건을 골라 사실 확인(웹검색) 후 쉬운 일본어로 '새로 작성'
③ nhk-easy.json 출력 (앱 형식 동일 — 앱 수정 불필요)

기사 본문은 가져오지 않음(저작권·유료기사). 헤드라인은 주제 근거로만 사용.
필요: ANTHROPIC_API_KEY (GitHub Secrets)
"""
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import requests

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5"
NUM_ARTICLES = 5
KST = timezone(timedelta(hours=9))

# RSS 소스 — 실패해도 다음 것으로 넘어감. 필요 시 여기만 수정
RSS_FEEDS = [
    ("毎日新聞 速報", "https://mainichi.jp/rss/etc/mainichi-flash.rss"),
    ("朝日新聞 総合", "https://www.asahi.com/rss/asahi/newsheadlines.rdf"),
    ("NHKニュース 主要", "https://www.nhk.or.jp/rss/news/cat0.xml"),
]

session = requests.Session()
session.headers["User-Agent"] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                 "AppleWebKit/537.36 (KHTML, like Gecko) "
                                 "Chrome/126.0.0.0 Safari/537.36")


def fetch_headlines():
    """RSS들에서 제목만 수집 (본문 미수집)"""
    titles = []
    for name, url in RSS_FEEDS:
        try:
            r = session.get(url, timeout=20)
            print(f"  RSS {name}: HTTP {r.status_code}")
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
            # RSS2.0 <item><title>, RSS1.0(RDF) {ns}item/{ns}title 모두 대응
            found = [el.text.strip() for el in root.iter()
                     if el.tag.endswith("title") and el.text and el.text.strip()]
            # 첫 번째는 채널 제목이므로 제외
            items = found[1:11]
            print(f"    헤드라인 {len(items)}건")
            titles.extend(items)
        except Exception as e:
            print(f"  RSS {name} 실패: {e}")
    # 중복 제거, 순서 유지
    seen, out = set(), []
    for t in titles:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:20]


def parse_json_lenient(text):
    t = re.sub(r"```(json)?", "", text).strip()
    s, e = t.find("{"), t.rfind("}")
    if s >= 0 and e > s:
        t = t[s:e + 1]
    return json.loads(t)


def call_claude(api_key, headlines):
    hl = "\n".join(f"- {t}" for t in headlines)
    prompt = f"""다음은 오늘 일본 주요 언론사 RSS에서 가져온 실제 헤드라인 목록입니다:

{hl}

이 중에서 분야가 겹치지 않게 {NUM_ARTICLES}건을 골라, 각 뉴스를 웹에서 검색해 사실을 확인한 뒤,
기사 원문을 옮기지 말고 JLPT N4~N3 학습자가 읽기 좋은 쉬운 일본어로 완전히 새로 작성하세요:
- 제목: 쉬운 일본어 한 줄 (원 헤드라인 그대로 복사 금지)
- 본문: 8~12문장, 쉬운 어휘와 기본 문형 위주

아래 JSON만 출력. 코드블록·설명·URL 금지:
{{"articles":[{{"title":"...","body":"..."}}]}}"""

    body = {
        "model": MODEL, "max_tokens": 4000,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {"Content-Type": "application/json", "x-api-key": api_key,
               "anthropic-version": "2023-06-01"}
    for attempt in range(1, 4):
        r = requests.post(API_URL, headers=headers, json=body, timeout=300)
        print(f"  API: HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            return "".join(b.get("text", "") for b in data.get("content", [])
                           if b.get("type") == "text")
        if r.status_code in (429, 529) and attempt < 3:
            time.sleep(20 * attempt)
            continue
        sys.exit(f"❌ API 오류: {r.text[:300]}")
    sys.exit("❌ API 재시도 초과")


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        sys.exit("❌ ANTHROPIC_API_KEY 없음 (GitHub Secrets 확인)")

    print("① RSS 헤드라인 수집")
    headlines = fetch_headlines()
    print(f"  수집 총 {len(headlines)}건")
    if not headlines:
        print("  ⚠️ RSS 전부 실패 — AI 단독 검색 모드로 진행")
        headlines = ["(RSS 수집 실패 — 오늘 일본 주요 뉴스를 직접 검색해서 고르세요)"]

    print("② AI 쉬운 일본어 작성")
    text = call_claude(api_key, headlines)
    parsed = parse_json_lenient(text)

    today = datetime.now(KST).strftime("%Y-%m-%d")
    stamp = datetime.now(KST).strftime("%H%M")
    articles = []
    for i, a in enumerate(parsed.get("articles", [])):
        title = (a.get("title") or "").strip()
        body_text = (a.get("body") or "").strip()
        if title and len(body_text) > 50:
            articles.append({"id": f"rss-{today}-{stamp}-{i}", "date": today,
                             "title": title, "body": body_text})
    if not articles:
        sys.exit("❌ 유효 기사 없음: " + text[:200])

    feed = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "RSS headlines + AI easy-Japanese rewrite (original text)",
            "articles": articles}
    with open("nhk-easy.json", "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=1)
    print(f"✅ 완료: 기사 {len(articles)}건 저장")


if __name__ == "__main__":
    main()
