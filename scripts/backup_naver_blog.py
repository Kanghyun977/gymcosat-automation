"""네이버 블로그(97_cosat) 전체 백업 — 읽기 전용.

산출물 (backup/naver_blog/):
  posts_index.json          전체 글 메타 목록
  posts/<logNo>.json        글별 메타 + 본문 텍스트 + 이미지 URL 목록
  html/<logNo>.html         원본 페이지 HTML
  images/<logNo>/*.jpg      본문 이미지 원본
"""
import json, re, sys, time, html
from pathlib import Path
from datetime import datetime
import urllib.request

BLOG_ID = "97_cosat"
ROOT = Path(__file__).resolve().parent.parent / "backup" / "naver_blog"
UA = {"User-Agent": "Mozilla/5.0", "Referer": f"https://m.blog.naver.com/{BLOG_ID}"}


def get(url, binary=False, retry=3):
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
                return data if binary else data.decode("utf-8", "replace")
        except Exception as e:
            if i == retry - 1:
                print(f"  ! fail {url}: {e}")
                return None
            time.sleep(2)


def fetch_index():
    items, page = [], 1
    while True:
        url = f"https://m.blog.naver.com/api/blogs/{BLOG_ID}/post-list?categoryNo=0&itemCount=30&page={page}"
        d = json.loads(get(url))
        batch = d.get("result", d).get("items", [])
        if not batch:
            break
        items += batch
        print(f"index page {page}: {len(items)}")
        page += 1
        time.sleep(0.5)
    return items


def extract_body(raw):
    # 스마트에디터 본문 영역만
    m = re.search(r'<div class="se-main-container">(.*?)</div>\s*</div>\s*<div class="se_component_wrap', raw, re.S)
    if not m:
        m = re.search(r'<div class="se-main-container">(.*)', raw, re.S)
    body = m.group(1) if m else raw
    imgs = re.findall(r'data-lazy-src="([^"]+)"|<img[^>]+src="(https://postfiles[^"]+)"', body)
    imgs = [a or b for a, b in imgs]
    imgs = [re.sub(r"\?type=w\d+.*$", "?type=w966", u) for u in imgs]
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)
    text = re.sub(r"</p>|<br\s*/?>|</div>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t​]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    return text, list(dict.fromkeys(imgs))


def main(with_images=True):
    (ROOT / "posts").mkdir(parents=True, exist_ok=True)
    (ROOT / "html").mkdir(exist_ok=True)
    idx_path = ROOT / "posts_index.json"
    items = fetch_index()
    index = []
    for it in items:
        index.append({
            "logNo": str(it["logNo"]),
            "title": it.get("titleWithInspectMessage"),
            "date": datetime.fromtimestamp(it["addDate"] / 1000).strftime("%Y-%m-%d %H:%M"),
            "category": it.get("categoryName"),
            "categoryNo": it.get("categoryNo"),
            "sympathy": it.get("sympathyCnt"),
            "comments": it.get("commentCnt"),
            "brief": it.get("briefContents"),
            "thumbnail": it.get("thumbnailUrl"),
            "url": f"https://blog.naver.com/{BLOG_ID}/{it['logNo']}",
        })
    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"index saved: {len(index)} posts")

    for n, p in enumerate(index, 1):
        out = ROOT / "posts" / f"{p['logNo']}.json"
        if out.exists():
            continue
        url = f"https://m.blog.naver.com/PostView.naver?blogId={BLOG_ID}&logNo={p['logNo']}"
        raw = get(url)
        if not raw:
            continue
        (ROOT / "html" / f"{p['logNo']}.html").write_text(raw, encoding="utf-8")
        text, imgs = extract_body(raw)
        rec = dict(p, body=text, images=imgs, chars=len(text))
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        if with_images and imgs:
            d = ROOT / "images" / p["logNo"]
            d.mkdir(parents=True, exist_ok=True)
            for i, u in enumerate(imgs):
                f = d / f"{i:02d}.jpg"
                if not f.exists():
                    b = get(u, binary=True)
                    if b:
                        f.write_bytes(b)
        print(f"[{n}/{len(index)}] {p['date'][:10]} {p['title'][:40]} ({len(text)}자, img {len(imgs)})")
        time.sleep(0.4)
    print("done")


if __name__ == "__main__":
    main(with_images="--no-images" not in sys.argv)
