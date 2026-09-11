"""캐러셀 JSON → 1080x1350 PNG 슬라이드 렌더링 (브랜드 템플릿).

usage: python scripts/ig_render.py output/instagram/<dir>/content.json
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "templates" / "brand.json").read_text(encoding="utf-8"))
W, H = BRAND["size"]
M = BRAND["margin"]
C = BRAND["colors"]


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
            # 어절 단위로 끊기
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


def draw_block(draw, x, y, text, f, fill, max_w, gap=1.25):
    for ln in wrap(draw, text, f, max_w):
        draw.text((x, y), ln, font=f, fill=fill)
        y += int(f.size * gap)
    return y


def header(draw, page, total, series, dark_bg):
    fg = C["white"] if dark_bg else C["green"]
    muted = "#BFD3CC" if dark_bg else C["text_muted"]
    draw.text((M, 56), BRAND["name"], font=font(30, "Bold"), fill=fg)
    s = f"{series}"
    draw.text((M, 96), s, font=font(24, "Medium"), fill=muted)
    pg = f"{page}/{total}"
    f = font(26, "Medium")
    draw.text((W - M - draw.textlength(pg, font=f), 60), pg, font=f, fill=muted)


def footer(draw, dark_bg):
    fg = "#BFD3CC" if dark_bg else C["text_muted"]
    draw.text((M, H - 90), BRAND["handle"], font=font(24, "Medium"), fill=fg)
    hint = "→ 넘겨보세요"
    f = font(24, "Medium")
    draw.text((W - M - draw.textlength(hint, font=f), H - 90), hint, font=f, fill=fg)


def render_slide(s, page, total, series):
    kind = s["kind"]
    dark = kind in ("hook", "cta")
    img = Image.new("RGB", (W, H), C["green"] if dark else C["cream"])
    d = ImageDraw.Draw(img)
    header(d, page, total, series, dark)
    maxw = W - 2 * M

    if kind == "hook":
        y = 330
        y = draw_block(d, M, y, s["title"], font(84, "Black"), C["white"], maxw, 1.2)
        if s.get("sub"):
            d.rectangle([M, y + 30, M + 120, y + 38], fill=C["accent"])
            draw_block(d, M, y + 70, s["sub"], font(40, "Medium"), "#DCE8E3", maxw, 1.35)

    elif kind == "cta":
        y = 360
        y = draw_block(d, M, y, s["title"], font(72, "Black"), C["white"], maxw, 1.2)
        d.rectangle([M, y + 30, M + 120, y + 38], fill=C["accent"])
        y = draw_block(d, M, y + 70, BRAND["cta_default"], font(36, "Medium"), "#DCE8E3", maxw, 1.4)
        if s.get("sub"):
            draw_block(d, M, y + 40, s["sub"], font(34, "Bold"), C["accent"], maxw)

    else:
        # 1차: 높이 측정용 더미 캔버스, 2차: 중앙 정렬해 실제 그리기
        def body(d, y0):
            y = y0
            tag = {"check": "자가진단", "body": "원인", "dont": "주의", "exercise": "해결 운동"}.get(kind, "")
            if tag:
                f = font(28, "Bold"); tw = d.textlength(tag, font=f)
                d.rounded_rectangle([M, y, M + tw + 44, y + 52], 26, fill=C["green"])
                d.text((M + 22, y + 9), tag, font=f, fill=C["white"])
                y += 100
            y = draw_block(d, M, y, s["title"], font(74, "Bold"), C["green"], maxw, 1.2)
            y += 50
            if kind == "check":
                for it in s.get("items", []):
                    d.rounded_rectangle([M, y + 14, M + 48, y + 62], 8, outline=C["green"], width=4)
                    d.text((M + 9, y + 8), "✓", font=font(36, "Bold"), fill=C["green"])
                    y = draw_block(d, M + 76, y, it, font(46, "Medium"), C["text_dark"], maxw - 76, 1.3) + 30
            else:
                for ln in s.get("lines", []):
                    d.ellipse([M, y + 20, M + 18, y + 38], fill=C["accent"] if kind == "exercise" else C["green"])
                    y = draw_block(d, M + 44, y, ln, font(44, "Medium"), C["text_dark"], maxw - 44, 1.3) + 30
            return y
        h = body(ImageDraw.Draw(Image.new("RGB", (W, H))), 0)
        y0 = max(200, (H - h) // 2 - 20)
        body(d, y0)
    footer(d, dark)
    return img


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
