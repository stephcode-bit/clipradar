"""Generate a scroll-stopping vertical thumbnail: a frame from the clip
with a bold, high-contrast hook-text overlay and a gradient legibility bar.
"""

import textwrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _load_font(size: int):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gradient_bar(width: int, height: int, top_alpha=0, bottom_alpha=210):
    grad = Image.new("L", (1, height))
    for y in range(height):
        alpha = int(top_alpha + (bottom_alpha - top_alpha) * (y / max(height - 1, 1)))
        grad.putpixel((0, y), alpha)
    alpha_mask = grad.resize((width, height))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    overlay.putalpha(alpha_mask)
    return overlay


def make_thumbnail(frame_path: str, hook_text: str, badge_text: str, out_path: str):
    img = Image.open(frame_path).convert("RGB")
    img = img.resize((W, H)) if img.size != (W, H) else img
    img = img.convert("RGBA")

    bar_h = int(H * 0.42)
    bar = _gradient_bar(W, bar_h)
    img.alpha_composite(bar, (0, H - bar_h))

    draw = ImageDraw.Draw(img)

    words = hook_text.strip().split()
    wrapped = textwrap.wrap(" ".join(words[:14]), width=16)[:4]
    font_size = 92 if len(wrapped) <= 2 else 74
    font = _load_font(font_size)

    line_gap = int(font_size * 1.15)
    total_h = line_gap * len(wrapped)
    y = H - bar_h + int((bar_h - total_h) * 0.55)

    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) / 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255),
                   stroke_width=6, stroke_fill=(0, 0, 0, 255))
        y += line_gap

    if badge_text:
        badge_font = _load_font(42)
        pad = 22
        bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        badge_box = [40, 40, 40 + bw + pad * 2, 40 + bh + pad * 2]
        draw.rounded_rectangle(badge_box, radius=16, fill=(255, 45, 85, 235))
        draw.text((40 + pad, 40 + pad - bbox[1]), badge_text, font=badge_font, fill=(255, 255, 255, 255))

    img.convert("RGB").save(out_path, quality=92)
    return out_path
