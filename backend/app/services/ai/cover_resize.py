import io

from PIL import Image


def resize_cover_image_bytes(
    data: bytes,
    *,
    width: int,
    height: int,
    content_type: str = "image/png",
) -> tuple[bytes, str]:
    """Resize generated cover bytes to exact platform dimensions."""
    with Image.open(io.BytesIO(data)) as image:
        if image.size == (width, height):
            return data, content_type

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "png" in content_type else "RGB")

        resized = image.resize((width, height), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        if content_type == "image/jpeg":
            if resized.mode == "RGBA":
                resized = resized.convert("RGB")
            resized.save(buffer, format="JPEG", quality=92)
            return buffer.getvalue(), "image/jpeg"

        if resized.mode not in ("RGB", "RGBA"):
            resized = resized.convert("RGBA")
        resized.save(buffer, format="PNG")
        return buffer.getvalue(), "image/png"
