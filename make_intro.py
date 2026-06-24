"""Generate Astra AI intro video."""
import math
import numpy as np
import imageio
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FPS = 30
SEC_PER_SLIDE = 4
FADE_DURATION = 0.5  # seconds

# Theme colors
BG = (3, 3, 12)
SURFACE = (10, 10, 30)
ACCENT = (0, 240, 255)
GREEN = (0, 255, 136)
TEXT = (238, 240, 255)
TEXT_SEC = (104, 104, 187)

# Find a good font
def get_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/seguiemj.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/seguisb.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/Calibri.ttf",
        "C:/Windows/Fonts/Calibrib.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


FONT_TITLE = get_font(72, bold=True)
FONT_SUB = get_font(36)
FONT_SMALL = get_font(28)
FONT_ICON = get_font(48)


def make_gradient(w, h, colors):
    """Create a smooth gradient image."""
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        c = []
        for i in range(3):
            v = colors[0][i] * (1 - t) + colors[1][i] * t
            c.append(int(v))
        draw.line([(0, y), (w, y)], fill=tuple(c))
    return img


def text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def alpha_blend(bg, fg, alpha):
    """Alpha composite fg onto bg."""
    return tuple(int(fg[i] * alpha + bg[i] * (1 - alpha)) for i in range(3))


def create_slide(title, subtitle, icon_text="◆", accent_color=ACCENT):
    """Create a single slide as PIL Image."""
    base = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(base)

    # Background gradient
    grad = make_gradient(W, H, [BG, (5, 5, 25), SURFACE, (5, 5, 20)])
    base = Image.blend(base, grad, 0.5)
    draw = ImageDraw.Draw(base)

    # Glowing accent circles (simple approach)
    for r in range(200, 100, -20):
        a = max(2, (200 - r) // 10)
        fill = alpha_blend(BG, accent_color, a / 100)
        draw.ellipse([W - 200 - r, 200 - r, W - 200 + r, 200 + r], fill=fill)
    for r in range(220, 120, -20):
        a = max(2, (220 - r) // 10)
        fill = alpha_blend(BG, GREEN, a / 100)
        draw.ellipse([200 - r, H - 200 - r, 200 + r, H - 200 + r], fill=fill)

    # Decorative lines
    for i in range(5):
        y = H // 2 + i * 6
        grad_len = W // 3
        for x in range(W // 2 - grad_len, W // 2 + grad_len):
            t = 1 - abs(x - W // 2) / grad_len
            a = int(8 * t)
            c = tuple(min(255, int(cc * t * 0.5)) for cc in accent_color)
            draw.point((x, y), fill=c)

    # Icon
    tw, th = text_size(draw, icon_text, FONT_ICON)
    ix = (W - tw) // 2
    iy = 120
    draw.text((ix, iy), icon_text, fill=accent_color, font=FONT_ICON)

    # Title
    tw, th = text_size(draw, title, FONT_TITLE)
    tx = (W - tw) // 2
    ty = 260
    # Glow effect
    glow_color = tuple(c // 3 for c in accent_color)
    for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 3), (0, -3), (3, 0), (-3, 0)]:
        draw.text((tx + dx, ty + dy), title, fill=glow_color, font=FONT_TITLE)
    draw.text((tx, ty), title, fill=TEXT, font=FONT_TITLE)

    # Subtitle
    if subtitle:
        tw2, th2 = text_size(draw, subtitle, FONT_SUB)
        sx = (W - tw2) // 2
        sy = ty + th + 30
        draw.text((sx, sy), subtitle, fill=TEXT_SEC, font=FONT_SUB)

    # Bottom bar
    bar_y = H - 80
    bar_w = 200
    bx = (W - bar_w) // 2
    for x in range(bar_w):
        t = 1 - abs(x - bar_w / 2) / (bar_w / 2)
        c = alpha_blend(BG, accent_color, t * 0.7)
        draw.point((bx + x, bar_y), fill=c)

    return base


def fade_transition(frame1, frame2, t):
    """Cross-fade between two frames. t: 0..1"""
    return Image.blend(frame1, frame2, t)


def main():
    slides_data = [
        ("✦ Astra AI", "Персональный AI-ассистент", "⬡", ACCENT),
        ("💬 Живое общение", "Естественный диалог как с другом", "💬", GREEN),
        ("🎤 Голосовое управление", "Говори — Astra поймёт", "🎤", ACCENT),
        ("🚀 Команды", "Открой браузер, скриншот, погода…", "🚀", (255, 136, 0)),
        ("🧠 Gemini AI", "Сложные вопросы, код, идеи", "🧠", (136, 68, 255)),
        ("📝 Заметки", "Запомни, напомни — никогда не забудет", "📝", GREEN),
        ("🎨 Генерация изображений", "Нарисуй что угодно словами", "🎨", ACCENT),
        ("⚡ Ctrl+Alt+A", "Начни прямо сейчас", "⚡", GREEN),
    ]

    # Render all slides
    print("Rendering slides...")
    slides = []
    for title, sub, icon, color in slides_data:
        slides.append(create_slide(title, sub, icon, color))

    total_slides = len(slides)
    total_duration = total_slides * SEC_PER_SLIDE
    total_frames = int(total_duration * FPS)
    fade_frames = int(FADE_DURATION * FPS)

    print(f"Generating {total_frames} frames ({total_duration}s)...")
    
    writer = imageio.get_writer(
        "C:/Users/admin/Desktop/AstraAI_v2.0_Release/intro.mp4",
        fps=FPS,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
    )

    for i in range(total_slides):
        slide = slides[i]
        next_slide = slides[(i + 1) % total_slides]
        start_frame = i * SEC_PER_SLIDE * FPS

        # Full display of current slide
        hold_frames = SEC_PER_SLIDE * FPS - fade_frames
        for f in range(hold_frames):
            writer.append_data(np.array(slide))

        # Cross-fade to next slide
        for f in range(fade_frames):
            t = (f + 1) / fade_frames
            frame = fade_transition(slide, next_slide, t)
            writer.append_data(np.array(frame))

        print(f"  Slide {i + 1}/{total_slides} done")

    writer.close()
    print("Done! Video saved to intro.mp4")


if __name__ == "__main__":
    main()
