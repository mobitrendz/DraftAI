import io

from PIL import Image

from app.services.ai.cover_resize import resize_cover_image_bytes


def _solid_png(width: int, height: int) -> bytes:
    image = Image.new("RGB", (width, height), color=(120, 80, 200))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_resize_cover_image_bytes_scales_to_target_dimensions():
    data = _solid_png(1792, 1024)
    resized, content_type = resize_cover_image_bytes(
        data, width=1000, height=420, content_type="image/png"
    )
    image = Image.open(io.BytesIO(resized))
    assert image.size == (1000, 420)
    assert content_type == "image/png"


def test_resize_cover_image_bytes_skips_resize_when_already_correct():
    data = _solid_png(1200, 627)
    resized, content_type = resize_cover_image_bytes(
        data, width=1200, height=627, content_type="image/png"
    )
    assert resized == data
    assert content_type == "image/png"
