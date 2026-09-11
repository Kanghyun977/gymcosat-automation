"""릴스 자동 제작 — 캐러셀 슬라이드 + 대본 TTS + 자막 → 1080x1920 mp4.

  python scripts/reel_make.py output/instagram/<dir>/           # content.json + 01~08.png 사용
  python scripts/reel_make.py output/instagram/<dir>/ --voice ko-KR-InJoonNeural

산출: <dir>/reel.mp4, <dir>/reel_cover.png
촬영본이 있으면 --video path.mp4 로 상단 영상을 교체(자막·음성은 동일).
"""
import asyncio, json, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "templates" / "brand.json").read_text(encoding="utf-8"))
C = BRAND["colors"]
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1080, 1920
VOICE = "ko-KR-InJoonNeural"  # 남성. 여성: ko-KR-SunHiNeural


def font(size, weight="Bold"):
    f = ImageFont.truetype(BRAND["font"], size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def wrap(d, text, f, max_w):
    lines, cur = [], ""
    for ch in text:
        t = cur + ch
        if d.textlength(t, font=f) > max_w and cur:
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


async def tts(text, out, voice):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate="+8%").save(str(out))


def duration(path):
    r = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True, errors="replace")
    import re
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def frame(slide_png, caption, label, dark=True):
    """상단: 슬라이드(1080x1350) / 하단: 자막 밴드(570)"""
    img = Image.new("RGB", (W, H), C["green_dark"])
    if slide_png and Path(slide_png).exists():
        s = Image.open(slide_png).convert("RGB").resize((1080, 1350))
        img.paste(s, (0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 1350, W, H], fill=C["green_dark"])
    d.rectangle([60, 1350, 200, 1356], fill=C["accent"])
    d.text((60, 1385), label, font=font(24, "Medium"), fill="#A9C4BB")
    f = font(46, "Bold")
    lines = wrap(d, caption, f, W - 120)[:5]
    y = 1440
    for ln in lines:
        d.text((60, y), ln, font=f, fill=C["white"])
        y += 62
    d.text((60, H - 70), BRAND["handle"], font=font(24, "Medium"), fill="#A9C4BB")
    return img


def main(dir_path, voice=VOICE, video=None):
    out = Path(dir_path)
    data = json.loads((out / "content.json").read_text(encoding="utf-8"))
    r = data["reel_script"]
    # 세그먼트: (텍스트, 슬라이드, 라벨)
    ex = [i for i, s in enumerate(data["slides"], 1) if s["kind"] == "exercise"]
    segs = [(r["hook"], out / "01.png", "HOOK")]
    for i, p in enumerate(r["points"]):
        sl = out / f"{ex[i]:02d}.png" if i < len(ex) else out / "03.png"
        segs.append((p, sl, f"POINT {i + 1}"))
    segs.append((r["cta"], out / f"{len(data['slides']):02d}.png", "FOLLOW"))

    tmp = Path(tempfile.mkdtemp())
    parts = []
    for i, (text, slide, label) in enumerate(segs):
        a = tmp / f"a{i}.mp3"; asyncio.run(tts(text, a, voice))
        dur = duration(a) + 0.35
        # 자막을 문장 단위로 쪼개 순차 표시
        sents = [s.strip() for s in text.replace("?", "?|").replace(".", ".|").replace("!", "!|").split("|") if s.strip()]
        per = dur / max(1, len(sents))
        seg_files = []
        for j, sent in enumerate(sents):
            fp = tmp / f"f{i}_{j}.png"; frame(slide, sent, label).save(fp)
            v = tmp / f"v{i}_{j}.mp4"
            subprocess.run([FF, "-y", "-loglevel", "error", "-loop", "1", "-i", str(fp), "-t", f"{per:.2f}",
                            "-vf", "scale=1080:1920,format=yuv420p", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", str(v)], check=True)
            seg_files.append(v)
        lst = tmp / f"l{i}.txt"; lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in seg_files), encoding="utf-8")
        vcat = tmp / f"vc{i}.mp4"
        subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vcat)], check=True)
        seg = tmp / f"s{i}.mp4"
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(vcat), "-i", str(a), "-c:v", "copy", "-c:a", "aac", "-shortest", str(seg)], check=True)
        parts.append(seg)
    lst = tmp / "all.txt"; lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    final = out / "reel.mp4"
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(final)], check=True)
    frame(out / "01.png", r["hook"], "HOOK").save(out / "reel_cover.png")
    print(f"reel: {final} ({duration(final):.1f}s)")


if __name__ == "__main__":
    args = sys.argv[1:]
    voice = VOICE
    if "--voice" in args:
        voice = args[args.index("--voice") + 1]
    main(args[0], voice)
