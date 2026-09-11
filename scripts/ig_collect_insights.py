"""인스타 성과 수집 — Aside 브라우저 에이전트로 인사이트를 읽어 일별 스냅샷 저장.

  python scripts/ig_collect_insights.py            # 오늘 스냅샷 수집 + 병합
  python scripts/ig_collect_insights.py --merge    # 수집 없이 병합·요약만

산출물:
  data/instagram/insights/YYYY-MM-DD.json   당일 스냅샷 (계정 + 게시물별)
  data/instagram/insights/timeline.csv      일별 계정 지표 누적
  data/instagram/insights/posts_timeline.csv  게시물×일 지표 누적
"""
import csv, json, os, subprocess, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INS = ROOT / "data" / "instagram" / "insights"
ASIDE = Path(os.environ.get("LOCALAPPDATA", "")) / "Aside" / "CLI" / "current" / "aside.exe"
ACCOUNT = "gymcosat_official"

# 추적 대상: 파이프라인이 발행한 게시물(published.json) + 기존 상위 게시물
def tracked_posts():
    posts = []
    for pj in (ROOT / "output" / "instagram").glob("*/published.json"):
        d = json.loads(pj.read_text(encoding="utf-8"))
        posts.append({"url": d["url"], "label": pj.parent.name, "source": "pipeline"})
    all_posts = json.loads((ROOT / "data" / "instagram" / "posts.json").read_text(encoding="utf-8"))
    top = sorted(all_posts, key=lambda x: -(x.get("like_count") or 0))[:5]
    for p in top:
        posts.append({"url": p["url"], "label": "baseline_top", "source": "baseline"})
    return posts


def build_prompt(today, posts):
    out = INS / f"{today}.json"
    lines = "\n".join(f"  - {p['url']}  (label: {p['label']})" for p in posts)
    return f"""인스타그램에 {ACCOUNT} 로 로그인돼 있다. 읽기 전용 성과 수집이다. 좋아요·팔로우·댓글·게시 등 쓰기 동작은 절대 하지 마라.

1. 계정 지표: https://www.instagram.com/{ACCOUNT}/ 에서 팔로워 수, 팔로잉, 게시물 수.
   가능하면 프로페셔널 대시보드(https://www.instagram.com/accounts/insights/ 또는 프로필의 '인사이트')에서 최근 7일 도달 계정 수, 프로필 방문, 팔로워 증감도 읽어라. 없으면 null.
2. 게시물 지표 — 아래 각 URL을 열어 좋아요, 댓글 수를 읽고, 게시물의 '인사이트 보기'가 있으면 열어서 도달(reach), 노출(impressions), 저장(saves), 공유(shares), 프로필 방문, 팔로우, 비팔로워 도달 비율을 읽어라. 없는 값은 null.
{lines}
3. 저장: {out}  (UTF-8 JSON)
{{
  "date": "{today}",
  "account": {{"followers": n, "following": n, "posts": n, "reach_7d": n|null, "profile_visits_7d": n|null, "follower_change_7d": n|null}},
  "posts": [{{"url": "...", "label": "...", "likes": n, "comments": n, "reach": n|null, "impressions": n|null, "saves": n|null, "shares": n|null, "profile_visits": n|null, "follows": n|null, "non_follower_reach_pct": n|null}}]
}}
4. 끝나면 팔로워 수와 파이프라인 게시물(label이 2026-으로 시작)의 도달·저장·팔로우를 한 줄로 요약하라."""


def collect(today):
    INS.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt(today, tracked_posts())
    r = subprocess.run([str(ASIDE), "exec", "--permission", "full-access", prompt], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-1500:])
    return (INS / f"{today}.json").exists()


def merge():
    snaps = sorted(INS.glob("????-??-??.json"))
    with open(INS / "timeline.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["date", "followers", "following", "posts", "reach_7d", "profile_visits_7d", "follower_change_7d"])
        for s in snaps:
            d = json.loads(s.read_text(encoding="utf-8")); a = d["account"]
            w.writerow([d["date"], a.get("followers"), a.get("following"), a.get("posts"), a.get("reach_7d"), a.get("profile_visits_7d"), a.get("follower_change_7d")])
    with open(INS / "posts_timeline.csv", "w", newline="", encoding="utf-8") as f:
        cols = ["date", "label", "url", "likes", "comments", "reach", "impressions", "saves", "shares", "profile_visits", "follows", "non_follower_reach_pct"]
        w = csv.writer(f); w.writerow(cols)
        for s in snaps:
            d = json.loads(s.read_text(encoding="utf-8"))
            for p in d["posts"]:
                w.writerow([d["date"]] + [p.get(c) for c in cols[1:]])
    # 요약
    if snaps:
        first, last = [json.loads(s.read_text(encoding="utf-8")) for s in (snaps[0], snaps[-1])]
        f0, f1 = first["account"].get("followers"), last["account"].get("followers")
        print(f"팔로워 {f0} → {f1} ({first['date']} → {last['date']}, {len(snaps)}일)")
        for p in last["posts"]:
            if p["label"].startswith("2026-"):
                print(f"  {p['label']}: 좋아요 {p.get('likes')} 저장 {p.get('saves')} 도달 {p.get('reach')} 팔로우 {p.get('follows')} 비팔로워 {p.get('non_follower_reach_pct')}%")


if __name__ == "__main__":
    today = str(date.today())
    if "--merge" not in sys.argv:
        ok = collect(today)
        print("snapshot:", "saved" if ok else "MISSING")
    merge()
