import io

from PIL import Image

from app.models.content import CoverImagePlatform
from app.services.ai.cover_specs import get_cover_spec
from app.services.ai.template_cover import (
    TEMPLATE_PROVIDER,
    _cover_display_text,
    generate_template_cover_bytes,
)


def test_generate_template_cover_bytes_returns_valid_png():
    data = generate_template_cover_bytes(
        title="Building Reliable CI Pipelines with GitHub Actions",
        subtitle="Abstract tech illustration",
    )
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    image = Image.open(io.BytesIO(data))
    assert image.size == (1280, 720)
    assert image.mode == "RGB"


def test_generate_template_cover_bytes_uses_platform_dimensions():
    spec = get_cover_spec(CoverImagePlatform.DEVTO)
    data = generate_template_cover_bytes(
        title="DEV.to cover",
        subtitle="Subtitle",
        width=spec.width,
        height=spec.height,
    )
    image = Image.open(io.BytesIO(data))
    assert image.size == (1000, 420)


def test_generate_template_cover_bytes_handles_empty_title():
    data = generate_template_cover_bytes(title="   ", subtitle=None)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")


def test_cover_display_text_prefers_prompt_over_title():
    assert (
        _cover_display_text(
            title="My Article Title",
            subtitle="Abstract cloud infrastructure illustration",
        )
        == "Abstract cloud infrastructure illustration"
    )


def test_cover_display_text_falls_back_to_title():
    assert _cover_display_text(title="Fallback title", subtitle=None) == "Fallback title"


def test_template_provider_constant():
    assert TEMPLATE_PROVIDER == "pillow-template"
