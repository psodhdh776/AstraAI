"""Generate realistic Astra AI intro video with neural voiceover."""
import asyncio, math, json, subprocess
import edge_tts
import numpy as np
import imageio
import imageio_ffmpeg as iifmpeg
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1088  # divisible by 16
FPS = 30
FADE = 15  # frames for cross-fade

# Colors
BG_DARK = (3, 3, 12)
BG_MID = (8, 8, 26)
ACCENT = (0, 200, 220)
ACCENT2 = (255, 0, 128)
GREEN = (0, 220, 120)
PURPLE = (120, 60, 255)
ORANGE = (255, 160, 0)
TEXT_MAIN = (230, 235, 255)
TEXT_SEC = (140, 145, 190)

# Fonts
def get_font(size):
    for p in [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/seguisb.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]:
        try:
            return ImageFont.truetype(p, size)
        except:
            pass
    return ImageFont.load_default()

FONT_TITLE = get_font(64)
FONT_SUB = get_font(32)
FONT_TAG = get_font(22)

# ─── Slide Definitions ───

class Slide:
    def __init__(self, title, subtitle, tag, icon, color1, color2):
        self.title = title
        self.subtitle = subtitle
        self.tag = tag
        self.icon = icon
        self.color1 = color1
        self.color2 = color2

SLIDES = [
    Slide("Astra AI v2.0", "Персональный AI-ассистент", "✦ ЗАПУСК", "⬡", ACCENT, ACCENT2),
    Slide("Живое общение", "Естественный диалог как с человеком", "💬 ЧАТ", "💬", GREEN, ACCENT),
    Slide("Голосовое управление", "Скажи — Astra поймёт и выполнит", "🎤 ГОЛОС", "🎤", ACCENT, PURPLE),
    Slide("Команды и инструменты", "Браузер · Скриншот · Погода · Калькулятор", "🚀 УПРАВЛЕНИЕ", "🚀", ORANGE, ACCENT2),
    Slide("Gemini AI", "Любые вопросы · Код · Идеи", "🧠 ИНТЕЛЛЕКТ", "🧠", PURPLE, ACCENT),
    Slide("Заметки и напоминания", "Ничего не забудет", "📝 ПАМЯТЬ", "📝", GREEN, ACCENT2),
    Slide("Генерация изображений", "Опиши словами — Astra нарисует", "🎨 ТВОРЧЕСТВО", "🎨", ACCENT, PURPLE),
    Slide("Ctrl + Alt + A", "Начни прямо сейчас", "⚡ СТАРТ", "⚡", GREEN, ACCENT),
]

# ─── Drawing Primitives ───

def text_size(draw, text, font):
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0], b[3] - b[1]

def draw_gradient(draw, x1, y1, x2, y2, c1, c2, vertical=True):
    """Draw gradient rect."""
    if vertical:
        for y in range(y1, y2):
            t = (y - y1) / max(1, y2 - y1)
            c = tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
            draw.line([(x1, y), (x2, y)], fill=c)

def draw_rounded_rect(draw, x1, y1, x2, y2, r, fill):
    """Draw filled rounded rect."""
    draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill)

def draw_glow_text(draw, x, y, text, font, color, glow_color=None, glow_radius=4):
    """Draw text with glow effect."""
    if glow_color is None:
        glow_color = tuple(c // 2 for c in color)
    # Glow passes
    for dx in range(-glow_radius, glow_radius + 1, 2):
        for dy in range(-glow_radius, glow_radius + 1, 2):
            if dx == 0 and dy == 0:
                continue
            dist = (dx * dx + dy * dy) ** 0.5
            if dist > glow_radius:
                continue
            a = int(80 * (1 - dist / glow_radius))
            gc = alpha_blend(BG_DARK, glow_color, a / 255)
            draw.text((x + dx, y + dy), text, fill=gc, font=font)
    # Main text
    draw.text((x, y), text, fill=color, font=font)

def alpha_blend(bg, fg, alpha):
    return tuple(int(fg[i] * alpha + bg[i] * (1 - alpha)) for i in range(3))

def create_slide_frame(slide, t):
    """Create a single video frame for a slide. t: 0..1 animation progress."""
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img, "RGBA")

    # ── Animated background ──
    # Sweeping gradient
    offset = int(t * 60) % 200
    draw_gradient(draw, 0, 0, W, H, BG_DARK, (5, 5, 20))
    # Animated diagonal glow lines
    for i in range(-200, H + 200, 60):
        y = i + offset
        if 0 <= y < H:
            c = alpha_blend(BG_DARK, slide.color2, max(0, 15 - abs(y - H // 2) * 0.05) / 255)
            draw.line([(0, y), (W, y)], fill=c + (max(0, min(255, 20 - abs(i) // 20)),))

    # ── Floating accent blobs ──
    blob_cx = W - 250 + int(math.sin(t * math.pi * 0.5) * 30)
    blob_cy = 180 + int(math.cos(t * math.pi * 0.3) * 20)
    for r in range(220, 60, -25):
        a = max(3, (220 - r) // 8)
        c = alpha_blend(BG_DARK, slide.color1, a / 255)
        draw.ellipse([blob_cx - r, blob_cy - r, blob_cx + r, blob_cy + r],
                      fill=c + (max(0, min(255, a)),))

    blob2_cx = 250 - int(math.sin(t * math.pi * 0.5) * 20)
    blob2_cy = H - 220 + int(math.cos(t * math.pi * 0.4) * 15)
    for r in range(200, 50, -25):
        a = max(3, (200 - r) // 8)
        c = alpha_blend(BG_DARK, slide.color2, a / 255)
        draw.ellipse([blob2_cx - r, blob2_cy - r, blob2_cx + r, blob2_cy + r],
                      fill=c + (max(0, min(255, a)),))

    # ── Tag badge (top-left) ──
    tag_w, tag_h = text_size(draw, slide.tag, FONT_TAG)
    badge_pad = 10
    bx, by = 50, 40
    draw_rounded_rect(draw, bx, by, bx + tag_w + badge_pad * 2, by + tag_h + badge_pad * 2, 6, BG_MID + (200,))
    draw_glow_text(draw, bx + badge_pad, by + badge_pad, slide.tag, FONT_TAG, slide.color1, glow_radius=3)

    # ── Icon ──
    icon_size = 72
    i_font = get_font(int(icon_size * 0.8))
    icon_x = W // 2 - icon_size // 2
    icon_y = 200 + int(math.sin(t * math.pi * 0.3) * 8)
    # Icon glow circle
    for r in range(50, 10, -8):
        a = max(5, (50 - r) * 2)
        c = alpha_blend(BG_DARK, slide.color1, a / 255)
        draw.ellipse([icon_x + icon_size // 2 - r, icon_y + icon_size // 2 - r,
                      icon_x + icon_size // 2 + r, icon_y + icon_size // 2 + r],
                      fill=c + (max(0, min(255, a)),))
    draw_glow_text(draw, icon_x + 8, icon_y + 2, slide.icon, i_font, slide.color1, glow_radius=5)

    # ── Title ──
    tw, th = text_size(draw, slide.title, FONT_TITLE)
    tx = max(50, (W - tw) // 2)
    ty = icon_y + 100
    draw_glow_text(draw, tx, ty, slide.title, FONT_TITLE, TEXT_MAIN, slide.color1, glow_radius=6)

    # ── Subtitle ──
    sw, sh = text_size(draw, slide.subtitle, FONT_SUB)
    sx = max(50, (W - sw) // 2)
    sy = ty + th + 25
    draw.text((sx, sy), slide.subtitle, fill=TEXT_SEC, font=FONT_SUB)

    # ── Bottom progress bar ──
    bar_y = H - 40
    bar_w = 300
    bar_h = 3
    bar_x = (W - bar_w) // 2
    draw_rounded_rect(draw, bar_x, bar_y, bar_x + bar_w, bar_y + bar_h, 2, BG_MID + (150,))
    fill_w = int(bar_w * t)
    if fill_w > 0:
        draw_rounded_rect(draw, bar_x, bar_y, bar_x + fill_w, bar_y + bar_h, 2, slide.color1 + (220,))

    # ── Bottom hint (first and last slide) ──
    if slide.tag == "✦ ЗАПУСК":
        hint = "Нажми Ctrl+Alt+A чтобы открыть"
        hw, hh = text_size(draw, hint, FONT_TAG)
        draw_glow_text(draw, (W - hw) // 2, H - 100, hint, FONT_TAG, TEXT_SEC, slide.color1, glow_radius=2)
    elif slide.tag == "⚡ СТАРТ":
        hint = "github.com / astra-ai"
        hw, hh = text_size(draw, hint, FONT_TAG)
        draw_glow_text(draw, (W - hw) // 2, H - 100, hint, FONT_TAG, TEXT_SEC, slide.color1, glow_radius=2)

    return img

def cross_fade(img1, img2, t):
    return Image.blend(img1, img2, t)

async def main():
    print("Generating neural voiceover...")
    narrator = "ru-RU-SvetlanaNeural"
    phrases = [
        "Astra AI v2.0 — твой персональный ассистент на Windows.",
        "Живое общение. Разговаривай с Astra как с человеком.",
        "Голосовое управление. Просто скажи — Astra услышит.",
        "Команды и инструменты. Браузер, скриншот, погода — всё одной фразой.",
        "Gemini AI. Любые вопросы, код, идеи.",
        "Заметки и напоминания. Astra ничего не забывает.",
        "Генерация изображений. Опиши словами — и Astra нарисует.",
        "Ctrl+Alt+A чтобы начать. Astra AI ждёт тебя.",
    ]
    full_text = " ".join(phrases)
    audio_path = "C:/Users/admin/Desktop/AstraAI_v2.0_Release/voiceover_neural.mp3"
    communicate = edge_tts.Communicate(full_text, narrator, rate="-10%")
    await communicate.save(audio_path)
    print("Voiceover saved.")

    # Get audio duration via ffmpeg
    ffmpeg_exe = iifmpeg.get_ffmpeg_exe()
    probe = subprocess.run(
        [ffmpeg_exe, "-i", audio_path, "-f", "null", "-"],
        capture_output=True, text=True
    )
    dur_match = __import__('re').search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
    if dur_match:
        h, m, s = dur_match.groups()
        audio_dur = int(h) * 3600 + int(m) * 60 + float(s)
    else:
        raise RuntimeError("Could not determine audio duration")
    print(f"Audio duration: {audio_dur:.1f}s")

    # Calculate video params
    sec_per_slide = audio_dur / len(SLIDES)
    total_frames = int(audio_dur * FPS)
    fade_frames = FADE
    hold_frames = int(sec_per_slide * FPS) - fade_frames

    print(f"Rendering {total_frames} frames ({audio_dur:.1f}s)...")

    video_path = "C:/Users/admin/Desktop/AstraAI_v2.0_Release/intro_neural.mp4"
    writer = imageio.get_writer(video_path, fps=FPS, codec="libx264", quality=8, pixelformat="yuv420p")

    for si, slide in enumerate(SLIDES):
        slide_dur = total_frames // len(SLIDES)
        for fi in range(slide_dur):
            progress = (fi % (hold_frames + fade_frames)) / max(1, hold_frames)
            # Animate: slide in from bottom
            t = min(1.0, fi / max(1, hold_frames))
            frame = create_slide_frame(slide, t)

            # Cross-fade transition
            if fi < fade_frames and si > 0:
                prev_slide = SLIDES[si - 1]
                prev_frame = create_slide_frame(prev_slide, 1.0)
                frame = cross_fade(prev_frame, frame, fi / fade_frames)

            writer.append_data(np.array(frame))

        print(f"  Slide {si + 1}/{len(SLIDES)} done")

    writer.close()
    print("Video rendered.")

    # ── Merge with audio ──
    final_path = "C:/Users/admin/Desktop/AstraAI_v2.0_Release/intro_final_v2.mp4"
    merge_cmd = [
        ffmpeg_exe, "-i", video_path, "-i", audio_path,
        "-c:v", "libx264", "-c:a", "aac",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", "-y", final_path,
    ]
    subprocess.run(merge_cmd, capture_output=True)
    print(f"Done! Saved to intro_final_v2.mp4")

asyncio.run(main())
