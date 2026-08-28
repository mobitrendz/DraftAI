from dataclasses import dataclass

from app.models.content import CoverImagePlatform


@dataclass(frozen=True)
class CoverPlatformSpec:
    width: int
    height: int
    gemini_aspect_ratio: str
    label: str


COVER_PLATFORM_SPECS: dict[CoverImagePlatform, CoverPlatformSpec] = {
    CoverImagePlatform.DEVTO: CoverPlatformSpec(
        width=1000,
        height=420,
        gemini_aspect_ratio="21:9",
        label="DEV.to",
    ),
    CoverImagePlatform.LINKEDIN: CoverPlatformSpec(
        width=1200,
        height=627,
        gemini_aspect_ratio="16:9",
        label="LinkedIn",
    ),
}


def get_cover_spec(platform: CoverImagePlatform) -> CoverPlatformSpec:
    return COVER_PLATFORM_SPECS[platform]
