"""트렌드 수집기 — 주 5회(평일) Aside 브라우저 에이전트로 수집.

  python scripts/collect_trends.py            # 오늘 수집 → data/trends/YYYY-WW.json 에 병합
  python scripts/collect_trends.py --report   # 이번 주 파일 요약만

산출: data/trends/YYYY-WW.json
  {"week": "2026-W37", "collected": ["2026-09-11", ...],
   "items": [{"url","platform","title","reactions","summary","topics":[...],"collected_at"}]}
"""
import json, os, subprocess, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / "data" / "trends"
ASIDE = Path(os.environ.get("LOCALAPPDATA", "")) / "Aside" / "CLI" / "current" / "aside.exe"

KEYWORDS = ["재활 운동", "통증", "거북목", "허리 통증", "무릎 통증", "헬스장 마케팅", "PT 마케팅", "물리치료사"]
IG_TAGS = ["거북목", "라운드숄더", "허리통증", "무릎통증", "어깨통증", "재활운동", "자세교정"]
SOURCES = {
    "newsletter": [
        ("스티비 인기 뉴스레터", "https://stibee.com/explore"),
        ("디에디트", "https://the-edit.co.kr/"),
        ("캐릿", "https://www.careet.net/"),
        ("마케팅 소사이어티", "https://www.google.com/search?q=마케팅+소사이어티+뉴스레터"),
    ],
    "social": [
        ("링크드인", "https://www.linkedin.com/search/results/content/?keywords={kw}&sortBy=%22relevance%22"),
        ("스레드", "https://www.threads.net/search?q={kw}"),
        ("X", "https://x.com/search?q={kw}&f=top"),
    ],
    "instagram": [
        ("인스타 해시태그 인기", "https://www.instagram.com/explore/tags/{tag}/"),
    ],
    "long": [
        ("브런치", "https://brunch.co.kr/search?q={kw}"),
        ("퍼블리", "https://publy.co/search?query={kw}"),
        ("네이버 블로그", "https://search.naver.com/search.naver?ssc=tab.blog.all&query={kw}"),
    ],
}


def week_file(d):
    y, w, _ = d.isocalendar()
    return TR / f"{y}-W{w:02d}.json"


def build_prompt(today, tmp_out):
    kws = " / ".join(KEYWORDS)
    tags = " ".join("#" + t for t in IG_TAGS)
    src = "\n".join(f"  - [{g}] {n}: {u}" for g, lst in SOURCES.items() for n, u in lst)
    return f"""트렌드 수집(읽기 전용). 좋아요·팔로우·댓글·구독 등 쓰기 동작은 절대 하지 마라. 로그인 화면이 나오면 입력하지 말고 그 소스는 건너뛰어라.

목적: 재활 PT샵 인스타·블로그 콘텐츠 주제 발굴. 두 종류를 모은다.
 (A) 콘텐츠 주제 — 키워드: {kws}
 (B) 마케팅 방법론 — 데이터 마케팅 뉴스레터가 이번 주 다루는 주제(콘텐츠 형식·훅·채널 전략)

소스 (사이트별 {{kw}}에 키워드를 넣어 검색, 소스당 상위 3~5개):
{src}
  - [instagram] 해시태그 인기: https://www.instagram.com/explore/tags/<태그>/

각 항목에서 수집: url, platform, title, reactions(좋아요·공유·댓글·조회 등 보이는 수치 합계, 없으면 null), summary(2문장), topics(추출 주제 태그 2~4개, 예: "거북목", "자가진단", "훅 패턴", "캐러셀 형식"), kind("A" 또는 "B"), posted_at(보이면).
소스당 최대 5개, 전체 25~40개. 최근 30일 안의 글 우선.

인스타그램 (저장 많이 되는 콘텐츠 벤치마크): 남의 게시물 저장 수는 안 보이므로, 해시태그 페이지의 '인기 게시물' 상단(알고리즘이 저장·공유 신호로 올린 것)을 대리 지표로 쓴다.
태그: {tags} — 각 태그의 인기 게시물 상위 5개를 열어 수집: url, platform="instagram", title(캡션 첫 줄), reactions(좋아요+댓글+리포스트 합계 — 리포스트(공유)는 저장의 대리 지표로 반드시 별도 필드 reposts에도 기록, 릴스면 views 필드에 조회수), summary(형식: 캐러셀/릴스/이미지 + 장수 + 훅 패턴 한 줄 + 왜 저장될 만한지), topics(태그명 + "저장형식:체크리스트|루틴|금지동작|비교|기타"), kind="A", account(계정명).

저장: {tmp_out} (UTF-8 JSON 배열). 끝나면 소스별 수집 개수와, 가장 반응 높은 항목 3개를 한 줄씩 보고하라."""


def collect(today):
    TR.mkdir(parents=True, exist_ok=True)
    tmp = TR / f"_raw_{today}.json"
    r = subprocess.run([str(ASIDE), "exec", "--permission", "full-access", build_prompt(today, tmp)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-1500:])
    if not tmp.exists():
        print("raw MISSING"); return
    items = json.loads(tmp.read_text(encoding="utf-8"))
    wf = week_file(date.fromisoformat(today))
    data = json.loads(wf.read_text(encoding="utf-8")) if wf.exists() else {"week": wf.stem, "collected": [], "items": []}
    seen = {i["url"] for i in data["items"]}
    added = 0
    for it in items:
        if it.get("url") and it["url"] not in seen:
            it["collected_at"] = today; data["items"].append(it); seen.add(it["url"]); added += 1
    if today not in data["collected"]:
        data["collected"].append(today)
    wf.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"merged {added} new → {wf.name} (total {len(data['items'])})")


def report(today):
    wf = week_file(date.fromisoformat(today))
    if not wf.exists():
        print("no data"); return
    d = json.loads(wf.read_text(encoding="utf-8"))
    from collections import Counter
    plat = Counter(i.get("platform") for i in d["items"])
    top = Counter(t for i in d["items"] for t in i.get("topics", []))
    print(f"{d['week']} 수집일 {d['collected']} 항목 {len(d['items'])}")
    print("플랫폼:", dict(plat))
    print("주제 TOP:", top.most_common(15))
    for i in sorted(d["items"], key=lambda x: -(x.get("reactions") or 0))[:8]:
        print(f"  [{i.get('kind')}] {i.get('reactions')} {i.get('platform')} | {i.get('title')} | {i.get('url')}")


if __name__ == "__main__":
    today = str(date.today())
    if "--report" not in sys.argv:
        collect(today)
    report(today)
