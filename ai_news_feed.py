# -*- coding: utf-8 -*-
"""
AI 쉬운 일본어 뉴스 피드 생성기 (NHK 스크래핑 대체)
Claude API 웹검색으로 오늘의 일본 주요뉴스를 찾아
JLPT N4~N3 수준의 쉬운 일본어로 '새로 작성'한 요약 피드를 만듭니다.
출력: nhk-easy.json (기존 앱 형식과 동일 — 앱 수정 불필요)

필요: ANTHROPIC_API_KEY 환경변수 (GitHub Secrets)
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta

import requests

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5"
NUM_ARTICLES = 5

KST = timezone(timedelta(hours=9))

PROMPT = f"""오늘 일본의 주요 뉴스 {NUM_ARTICLES}건을 웹에서 검색하세요.
분야를 다양하게 (사회, 경제, 과학/기술, 생활, 날씨/재해 등) 골고루 고르세요.

각 뉴스를 기사 원문을 옮기지 말고, JLPT N4~N3 학습자가 읽기 좋은
쉬운 일본어로 완전히 새로 요약해서 작성하세요:
- 제목: 쉬운 일본어 한 줄
- 본문: 8~12문장, 쉬운 어휘와 기본 문형 위주, 어려운 한자어는 쉬운 표현으로

아래 JSON만 출력하세요. 코드블록·설명·URL 금지:
{{"articles":[{{"title":"...","body":"..."}}]}}"""


def parse_json_lenient(text):
    t = re.sub(r"```(json)?", "", text).strip()
    s, e = t.find("{"), t.rfind("}")
    if s >= 0 and e > s:
        t = t[s:e + 1]
    return json.loads(t)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        sys.exit("❌ ANTHROPIC_API_KEY 환경변수가 없습니다 (GitHub Secrets 확인)")

    body = {
        "model": MODEL,
        "max_tokens": 4000,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{"role": "user", "content": PROMPT}],
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    for attempt in range(1, 4):
        r = requests.post(API_URL, headers=headers, json=body, timeout=300)
        print(f"API 응답: HTTP {r.status_code}")
        if r.status_code == 200:
            break
        if r.status_code in (429, 529) and attempt < 3:
            time.sleep(20 * attempt)
            continue
        sys.exit(f"❌ API 오류: {r.text[:300]}")

    data = r.json()
    text = "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text")
    parsed = parse_json_lenient(text)
    raw_articles = parsed.get("articles", [])

    today = datetime.now(KST).strftime("%Y-%m-%d")
    stamp = datetime.now(KST).strftime("%H%M")
    articles = []
    for i, a in enumerate(raw_articles):
        title = (a.get("title") or "").strip()
        body_text = (a.get("body") or "").strip()
        if title and len(body_text) > 50:
            articles.append({
                "id": f"ai-{today}-{stamp}-{i}",
                "date": today,
                "title": title,
                "body": body_text,
            })

    if not articles:
        sys.exit("❌ 유효한 기사가 없습니다: " + text[:200])

    feed = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "AI easy-Japanese daily news summary (original text)",
        "articles": articles,
    }
    with open("nhk-easy.json", "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=1)
    print(f"✅ 완료: 기사 {len(articles)}건 저장")


if __name__ == "__main__":
    main()
