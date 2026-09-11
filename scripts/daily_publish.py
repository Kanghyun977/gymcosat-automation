"""매일 09:00 자동 실행 — 큐의 다음 편(캐러셀 + 릴스)을 Aside로 게시하고 성과·트렌드를 수집.

  python scripts/daily_publish.py            # 큐 다음 편 게시 + 수집
  python scripts/daily_publish.py --dry      # 무엇을 올릴지 표시만
  python scripts/daily_publish.py --reel-only <dir>   # 특정 편 릴스만 게시

queue.json: {"items": [{"dir": "output/instagram/2026-09-12_xxx", "carousel": "pending|published|skip", "reel": "pending|published|skip"}]}
로그: logs/daily_YYYY-MM-DD.log
"""
import json, os, subprocess, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Q = ROOT / "queue.json"
LOG = ROOT / "logs"
ASIDE = Path(os.environ.get("LOCALAPPDATA", "")) / "Aside" / "CLI" / "current" / "aside.exe"


def log(msg):
    LOG.mkdir(exist_ok=True)
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with open(LOG / f"daily_{datetime.now():%Y-%m-%d}.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def aside(prompt, timeout=1500):
    r = subprocess.run([str(ASIDE), "exec", "--permission", "full-access", prompt],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return r.stdout


def publish_carousel(d: Path):
    title = json.loads((d / "content.json").read_text(encoding="utf-8"))["slides"][0]["title"].replace("\n", " ")
    n = len(list(d.glob("0?.png")))
    out = aside(f"""인스타그램(gymcosat_official 로그인). 캐러셀 1개 게시. 다른 쓰기 동작 금지.
먼저 프로필 최신 게시물 3개를 확인해 첫 장 문구 '{title}' 캐러셀이 이미 있으면 그 URL만 published.json에 저장하고 다시 올리지 마라.
없으면: 폴더 {d}\\ 의 01~{n:02d}.png 순서 업로드 → 비율 '원본' → 편집 없이 → caption.txt 내용 그대로 캡션 → 공동작성자·위치 없음 → 공유.
게시 후 URL을 {d}\\published.json 에 {{url, published_at, status:'published'}} 로 저장. 막히면 보고 후 멈춰라.""")
    log(out[-600:])
    return (d / "published.json").exists()


def publish_reel(d: Path):
    title = json.loads((d / "content.json").read_text(encoding="utf-8"))["reel_script"]["hook"]
    out = aside(f"""인스타그램(gymcosat_official 로그인). 릴스 1개 게시. 다른 쓰기 동작 금지.
먼저 프로필 릴스 탭 최신 3개를 확인해 캡션 첫 줄이 '{title[:20]}'로 시작하는 릴스가 이미 있으면 그 URL만 reel_published.json에 저장하고 다시 올리지 마라.
없으면: 만들기(+) → 릴스/게시물 → 동영상 {d}\\reel.mp4 업로드 → 비율 원본(9:16) → 커버 이미지는 {d}\\reel_cover.png 선택(가능하면) → 편집 없이 → 캡션은 {d}\\caption.txt 내용 그대로 → 공동작성자·위치 없음 → 공유.
게시 후 URL을 {d}\\reel_published.json 에 {{url, published_at, status:'published'}} 로 저장. 막히면 보고 후 멈춰라.""")
    log(out[-600:])
    return (d / "reel_published.json").exists()


def main():
    args = sys.argv[1:]
    if "--reel-only" in args:
        d = ROOT / args[args.index("--reel-only") + 1]
        log(f"reel-only {d.name}: {'ok' if publish_reel(d) else 'FAIL'}"); return
    q = json.loads(Q.read_text(encoding="utf-8"))
    item = next((i for i in q["items"] if i["carousel"] == "pending" or i["reel"] == "pending"), None)
    if not item:
        log("queue empty"); return
    d = ROOT / item["dir"]
    if "--dry" in args:
        print("next:", item); return
    log(f"start {d.name}")
    if item["carousel"] == "pending":
        item["carousel"] = "published" if publish_carousel(d) else "failed"
        Q.write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding="utf-8")
    if item["reel"] == "pending" and (d / "reel.mp4").exists():
        item["reel"] = "published" if publish_reel(d) else "failed"
        Q.write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"done {d.name}: carousel={item['carousel']} reel={item['reel']}")
    # 수집
    for s in ("ig_collect_insights.py", "collect_trends.py"):
        try:
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / s)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1500)
            log(f"{s}: {r.stdout[-300:].strip()}")
        except Exception as e:
            log(f"{s} error: {e}")
    subprocess.run(["git", "add", "-A"], cwd=ROOT); subprocess.run(["git", "commit", "-q", "-m", f"daily {datetime.now():%Y-%m-%d}: {d.name}"], cwd=ROOT); subprocess.run(["git", "push", "-q"], cwd=ROOT)


if __name__ == "__main__":
    main()
