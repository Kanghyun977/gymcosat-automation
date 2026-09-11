"""캐러셀 JSON → 1080x1350 PNG 슬라이드 렌더링 (브랜드 템플릿 v2).

v2 — taste-skill 원칙 적용: 강한 타이포 위계(키커/헤드라인/본문), 절제된 밀도,
종이 질감(그레인), 얇은 룰·작은 라벨·페이지 번호 디테일, 고스트 숫자, 한 장 한 아이디어.

usage: python scripts/ig_render.py output/instagram/<dir>/content.json
"""
import json, random, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "templates" / "brand.json").read_text(encoding="utf-8"))
W, H = BRAND["size"]
M = BRAND["margin"]
C = BRAND["colors"]
KICKER = {"check": "SELF CHECK · 자가진단", "body": "WHY · 원인", "dont": "DON'T · 이건 하지 마세요", "exercise": "DO · 해결 운동"}


def font(size, weight="Regular"):
    f = ImageFont.truetype(BRAND["font"], size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def wrap(draw, text, f, max_w):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        t = cur + ch
        if draw.textlength(t, font=f) > max_w and cur:
            sp = cur.rfind(" ")
            if sp > 0:
                lines.append(cur[:sp]); cur = cur[sp + 1:] + ch
            else:
                lines.append(cur); cur = ch
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def block(draw, x, y, text, f, fill, max_w, gap=1.22):
    for ln in wrap(draw, text, f, max_w):
        draw.text((x, y), ln, font=f, fill=fill)
        y += int(f.size * gap)
    return y


def grain(img, amount=10):
    """종이 질감 — 미세한 노이즈 오버레이"""
    rnd = random.Random(7)
    noise = Image.effect_noise((W // 3, H // 3), amount).resize((W, H), Image.BILINEAR)
    noise = noise.point(lambda v: 128 + (v - 128) // 2)
    base = img.convert("L")
    return Image.blend(img, Image.merge("RGB", (noise, noise, noise)), 0.06)


def frame(d, fg):
    """얇은 프레임 룰 + 코너 마크"""
    d.rectangle([M - 30, M - 30, W - M + 30, H - M + 30], outline=fg, width=1)
    for x in (M - 30, W - M + 30):
        for y in (M - 30, H - M + 30):
            d.line([x - 10, y, x + 10, y], fill=fg, width=1); d.line([x, y - 10, x, y + 10], fill=fg, width=1)


def header(d, page, total, series, dark):
    fg = C["white"] if dark else C["green"]
    mu = "#A9C4BB" if dark else C["text_muted"]
    d.text((M, M - 4), BRAND["name"], font=font(26, "Bold"), fill=fg)
    d.text((M + 150, M), "·  " + series, font=font(22, "Medium"), fill=mu)
    pg = f"{page:02d} / {total:02d}"
    f = font(22, "Medium")
    d.text((W - M - d.textlength(pg, font=f), M), pg, font=f, fill=mu)
    d.line([M, M + 44, W - M, M + 44], fill=mu, width=1)


def footer(d, dark, hint="넘겨보세요  →"):
    mu = "#A9C4BB" if dark else C["text_muted"]
    d.line([M, H - M - 40, W - M, H - M - 40], fill=mu, width=1)
    d.text((M, H - M - 26), BRAND["handle"], font=font(22, "Medium"), fill=mu)
    f = font(22, "Medium")
    d.text((W - M - d.textlength(hint, font=f), H - M - 26), hint, font=f, fill=mu)


def ghost_number(d, n, dark):
    """고스트 숫자 — 배경에 크게 깔리는 번호"""
    col = "#155C48" if dark else "#E6E1D6"
    f = font(520, "Black")
    d.text((W - M - d.textlength(n, font=f) + 40, H - 700), n, font=f, fill=col)


def place_image(img, rel, box):
    """박스 안에 일러스트를 비율 유지로 맞춰 흰 카드 위에 배치"""
    l, t, r, b = box
    bw, bh = r - l, b - t
    if bh < 200:
        return
    src = Image.open(ROOT / rel).convert("RGB")
    sw, sh = src.size
    k = min(bw / sw, bh / sh)
    src = src.resize((int(sw * k), int(sh * k)), Image.LANCZOS)
    card = Image.new("RGB", (bw, bh), "#FFFFFF")
    card.paste(src, ((bw - src.width) // 2, (bh - src.height) // 2))
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, bw - 1, bh - 1], 24, fill=255)
    img.paste(card, (l, t), mask)


def render_slide(s, page, total, series):
    kind = s["kind"]
    dark = kind in ("hook", "cta")
    img = Image.new("RGB", (W, H), C["green"] if dark else C["cream"])
    d = ImageDraw.Draw(img)
    maxw = W - 2 * M
    fg = C["white"] if dark else C["green"]
    mu = "#A9C4BB" if dark else C["text_muted"]

    if kind == "hook":
        frame(d, "#2E6B58")
        header(d, page, total, series, dark)
        has_img = bool(s.get("image")) and Path(ROOT / s["image"]).exists()
        y = 250 if has_img else 400
        d.text((M, y - 70), "01  —  물리치료사가 묻습니다", font=font(24, "Medium"), fill=mu)
        y = block(d, M, y, s["title"], font(84 if has_img else 96, "Black"), C["white"], maxw, 1.12)
        d.rectangle([M, y + 30, M + 140, y + 36], fill=C["accent"])
        if s.get("sub"):
            y = block(d, M, y + 70, s["sub"], font(34, "Medium"), "#DCE8E3", maxw - 60, 1.4)
        if has_img:
            place_image(img, s["image"], (M, max(y + 40, 640), W - M, H - M - 60))
            d = ImageDraw.Draw(img)
        footer(d, dark)

    elif kind == "cta":
        frame(d, "#2E6B58")
        header(d, page, total, series, dark)
        y = 380
        d.text((M, y - 70), "마지막 장", font=font(24, "Medium"), fill=mu)
        y = block(d, M, y, s["title"], font(76, "Black"), C["white"], maxw, 1.14)
        d.rectangle([M, y + 36, M + 140, y + 42], fill=C["accent"])
        y = block(d, M, y + 80, BRAND["cta_default"], font(32, "Medium"), "#DCE8E3", maxw - 60, 1.45)
        if s.get("sub"):
            # 다음 편 예고 카드
            y += 40
            d.rounded_rectangle([M, y, W - M, y + 120], 16, fill="#0A3529", outline="#2E6B58", width=1)
            d.text((M + 32, y + 22), "NEXT", font=font(20, "Bold"), fill=C["accent"])
            block(d, M + 32, y + 52, s["sub"].replace("다음 편: ", ""), font(30, "Bold"), C["white"], maxw - 64, 1.2)
        footer(d, dark, "팔로우  ♡")

    else:
        frame(d, "#D8D2C4")
        exercise_no = None
        if kind == "exercise":
            t = s["title"]
            for k, v in {"①": "1", "②": "2", "③": "3", "④": "4"}.items():
                if t.startswith(k):
                    exercise_no = v; break
        if exercise_no:
            ghost_number(d, exercise_no, dark)
        header(d, page, total, series, dark)

        def body(d, y):
            kick = KICKER.get(kind, "")
            d.text((M, y), kick, font=font(22, "Bold"), fill=C["accent"] if kind == "dont" else C["green"])
            d.line([M, y + 40, M + 60, y + 40], fill=C["green"], width=2)
            y += 80
            title = s["title"]
            if exercise_no:
                title = title[1:].strip()
            y = block(d, M, y, title, font(70, "Bold"), C["green"], maxw, 1.16)
            y += 48
            if s.get("image") and Path(ROOT / s["image"]).exists():
                y += 0
            if kind == "check":
                for it in s.get("items", []):
                    d.rounded_rectangle([M, y + 12, M + 46, y + 58], 6, outline=C["green"], width=3)
                    d.text((M + 8, y + 6), "✓", font=font(34, "Bold"), fill=C["green"])
                    y = block(d, M + 74, y, it, font(42, "Medium"), C["text_dark"], maxw - 74, 1.3) + 26
            else:
                for i, ln in enumerate(s.get("lines", []), 1):
                    d.line([M, y + 14, M, y + 52], fill=C["accent"] if kind == "exercise" else C["green"], width=4)
                    y = block(d, M + 36, y, ln, font(40, "Medium"), C["text_dark"], maxw - 36, 1.32) + 26
            return y

        has_img = bool(s.get("image")) and Path(ROOT / s["image"]).exists()
        h = body(ImageDraw.Draw(Image.new("RGB", (W, H))), 0)
        y0 = M + 90 if has_img else max(M + 90, (H - h) // 2 - 10)
        y_end = body(d, y0)
        if has_img:
            place_image(img, s["image"], (M, y_end + 10, W - M, H - M - 60))
            d = ImageDraw.Draw(img)
        footer(d, dark)

    return grain(img)


def main(path):
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    out = p.parent
    series = f"{BRAND['series']} #{data.get('series_no', 1)}"
    total = len(data["slides"])
    for i, s in enumerate(data["slides"], 1):
        render_slide(s, i, total, series).save(out / f"{i:02d}.png")
    cap = data["caption"].rstrip() + "\n\n" + " ".join(data["hashtags"])
    (out / "caption.txt").write_text(cap, encoding="utf-8")
    r = data.get("reel_script")
    if r:
        md = f"# 릴스 대본 — {data['topic']} ({r.get('duration_sec', 45)}초)\n\n**[0~3초 훅]** {r['hook']}\n\n" + \
             "".join(f"**[포인트 {i}]** {t}\n\n" for i, t in enumerate(r["points"], 1)) + f"**[마무리]** {r['cta']}\n"
        (out / "reel_script.md").write_text(md, encoding="utf-8")
    print(f"rendered {total} slides → {out}")


if __name__ == "__main__":
    main(sys.argv[1])
