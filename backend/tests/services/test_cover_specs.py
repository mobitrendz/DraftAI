from app.models.content import CoverImagePlatform
from app.services.ai.cover_specs import get_cover_spec


def test_devto_cover_spec_dimensions():
    spec = get_cover_spec(CoverImagePlatform.DEVTO)
    assert spec.width == 1000
    assert spec.height == 420
    assert spec.gemini_aspect_ratio == "21:9"


def test_linkedin_cover_spec_dimensions():
    spec = get_cover_spec(CoverImagePlatform.LINKEDIN)
    assert spec.width == 1200
    assert spec.height == 627
    assert spec.gemini_aspect_ratio == "16:9"
