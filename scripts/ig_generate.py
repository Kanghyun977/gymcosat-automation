"""인스타 캐러셀 콘텐츠 생성.

  python scripts/ig_generate.py "거북목" --no 1            # Claude API로 생성 (.env의 ANTHROPIC_API_KEY)
  python scripts/ig_generate.py --from-json path.json      # 이미 만든 JSON을 렌더링만

산출물: output/instagram/YYYY-MM-DD_<topic>/ content.json, 01~NN.png, caption.txt, reel_script.md
"""
import argparse, json, os, re, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ig_render  # noqa: E402

PROMPT = (ROOT / "prompts" / "ig_carousel.md").read_text(encoding="utf-8")


def load_env():
    p = ROOT / ".env"
    if p.exists():
        for ln in p.read_text(encoding="utf-8").splitlines():
            if "=" in ln and not ln.startswith("#"):
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def generate(topic, series_no, extra=""):
    load_env()
    import anthropic
    client = anthropic.Anthropic()
    user = f"주제: {topic}\n시리즈 번호: {series_no}\n{extra}\nJSON만 출력하라."
    msg = client.messages.create(
        model="claude-sonnet-5", max_tokens=4000, system=PROMPT,
        messages=[{"role": "user", "content": user}],
    )
    text = msg.content[0].text
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0))


def save_and_render(data):
    slug = re.sub(r"[^\w가-힣]+", "_", data["topic"]).strip("_")
    out = ROOT / "output" / "instagram" / f"{date.today()}_{slug}"
    out.mkdir(parents=True, exist_ok=True)
    cp = out / "content.json"
    cp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    ig_render.main(cp)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("topic", nargs="?")
    ap.add_argument("--no", type=int, default=1)
    ap.add_argument("--from-json")
    ap.add_argument("--extra", default="")
    a = ap.parse_args()
    if a.from_json:
        data = json.loads(Path(a.from_json).read_text(encoding="utf-8"))
    else:
        if not a.topic:
            ap.error("topic 또는 --from-json 필요")
        data = generate(a.topic, a.no, a.extra)
    print(save_and_render(data))
