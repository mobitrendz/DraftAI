import hashlib
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings

TEMPLATE_PROVIDER = "pillow-template"

_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/Library/Fonts/Arial.ttf",
)

_PALETTES: tuple[tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]], ...] = (
    ((15, 23, 42), (30, 64, 175), (96, 165, 250)),
    ((17, 24, 39), (88, 28, 135), (192, 132, 252)),
    ((20, 30, 48), (6, 95, 70), (52, 211, 153)),
    ((24, 24, 27), (127, 29, 29), (248, 113, 113)),
    ((15, 23, 42), (14, 116, 144), (34, 211, 238)),
)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        font_path = Path(path)
        if font_path.is_file():
            return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _cover_display_text(*, title: str, subtitle: str | None) -> str:
    """Pick on-image copy: prefer the cover prompt, not the article title."""
    prompt_text = (subtitle or "").strip()
    title_text = title.strip()
    if prompt_text and prompt_text.lower() != title_text.lower():
        return prompt_text
    if prompt_text:
        return prompt_text
    return title_text or "Untitled draft"


def _palette_from_seed(seed: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    index = digest[0] % len(_PALETTES)
    return _PALETTES[index]


def _draw_vertical_gradient(
    image: Image.Image,
    *,
    top_rgb: tuple[int, int, int],
    bottom_rgb: tuple[int, int, int],
) -> None:
    width, height = image.size
    pixels = image.load()
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = tuple(
            int(top_rgb[channel] + (bottom_rgb[channel] - top_rgb[channel]) * ratio)
            for channel in range(3)
        )
        for x in range(width):
            pixels[x, y] = color


def _draw_abstract_shapes(
    draw: ImageDraw.ImageDraw,
    *,
    width: int,
    height: int,
    accent_rgb: tuple[int, int, int],
    seed: str,
) -> None:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    accent = (*accent_rgb, 72)
    accent_soft = (*accent_rgb, 40)
    accent_bright = tuple(min(channel + 40, 255) for channel in accent_rgb) + (110,)

    shapes = [
        (int(width * 0.72), int(height * 0.18), int(width * 0.42)),
        (int(width * 0.12), int(height * 0.55), int(width * 0.28)),
        (int(width * 0.58), int(height * 0.62), int(width * 0.22)),
    ]
    for index, (cx, cy, radius) in enumerate(shapes):
        offset = (digest[index + 1] % 40) - 20
        draw.ellipse(
            (cx - radius + offset, cy - radius, cx + radius + offset, cy + radius),
            fill=accent_soft if index % 2 else accent,
        )

    stripe_width = max(6, int(width * 0.012))
    stripe_x = int(width * (0.55 + (digest[4] % 20) / 100))
    draw.rectangle(
        (stripe_x, 0, stripe_x + stripe_width, height),
        fill=accent_bright,
    )

    dot_spacing = max(18, int(width * 0.03))
    dot_radius = max(2, int(width * 0.004))
    for row in range(0, height, dot_spacing * 2):
        for col in range(0, int(width * 0.35), dot_spacing):
            if (row // dot_spacing + col // dot_spacing) % 2 == 0:
                draw.ellipse(
                    (
                        col - dot_radius,
                        row - dot_radius,
                        col + dot_radius,
                        row + dot_radius,
                    ),
                    fill=(*accent_rgb, 55),
                )


def _draw_cover_headline(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    width: int,
    height: int,
    accent_rgb: tuple[int, int, int],
) -> None:
    margin_x = int(width * 0.08)
    max_text_width = width - (margin_x * 2)
    headline_font_size = max(18, min(56, int(height * 0.14)))
    headline_font = _load_font(headline_font_size)

    lines = _wrap_text(
        draw,
        text,
        font=headline_font,
        max_width=max_text_width,
    )[:3]
    if len(lines) == 3 and len(lines[-1]) > 3:
        lines[-1] = lines[-1][: max(len(lines[-1]) - 3, 0)] + "..."

    line_height = int(headline_font_size * 1.15)
    block_height = len(lines) * line_height
    cursor_y = (height - block_height) // 2

    draw.rectangle(
        (margin_x - 16, cursor_y - 10, margin_x - 6, cursor_y + block_height + 10),
        fill=accent_rgb,
    )

    for line in lines:
        draw.text(
            (margin_x, cursor_y),
            line,
            font=headline_font,
            fill=(248, 250, 252),
        )
        cursor_y += line_height


def generate_template_cover_bytes(
    *,
    title: str,
    subtitle: str | None = None,
    width: int | None = None,
    height: int | None = None,
) -> bytes:
    """Build a branded template cover when AI image APIs are unavailable.

    Renders the cover prompt (subtitle) as on-image text. The article title is
    used only for palette variety and is avoided when it would duplicate DEV.to.
    """
    width = width if width is not None else settings.COVER_TEMPLATE_WIDTH
    height = height if height is not None else settings.COVER_TEMPLATE_HEIGHT
    seed = (title or "").strip() or (subtitle or "").strip() or "draftai-cover"
    display_text = _cover_display_text(title=title, subtitle=subtitle)
    top_rgb, bottom_rgb, accent_rgb = _palette_from_seed(seed)

    image = Image.new("RGB", (width, height))
    _draw_vertical_gradient(image, top_rgb=top_rgb, bottom_rgb=bottom_rgb)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    _draw_abstract_shapes(
        ImageDraw.Draw(overlay),
        width=width,
        height=height,
        accent_rgb=accent_rgb,
        seed=seed,
    )
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(image)

    _draw_cover_headline(
        draw,
        text=display_text,
        width=width,
        height=height,
        accent_rgb=accent_rgb,
    )

    margin_x = int(width * 0.08)
    brand_font_size = max(11, min(22, int(height * 0.05)))
    brand_font = _load_font(brand_font_size)
    draw.text(
        (margin_x, height - max(40, int(height * 0.12))),
        settings.PROJECT_NAME,
        font=brand_font,
        fill=(203, 213, 225),
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
