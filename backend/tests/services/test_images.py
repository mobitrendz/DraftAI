from app.services.ai import images


def test_gemini_image_config_for_flash_models():
    config = images._gemini_image_generation_config(
        "gemini-2.5-flash-image", aspect_ratio="21:9"
    )
    assert config == {
        "responseModalities": ["IMAGE"],
        "imageConfig": {"aspectRatio": "21:9"},
    }


def test_gemini_image_config_for_gemini_3_models():
    config = images._gemini_image_generation_config(
        "gemini-3-pro-image", aspect_ratio="16:9"
    )
    assert config["responseModalities"] == ["IMAGE"]
    assert config["imageConfig"]["aspectRatio"] == "16:9"
    assert config["imageConfig"]["imageSize"] == "1K"


def test_format_image_error_quota():
    message = images._format_image_error(
        status_code=429,
        body=(
            '{"error": {"message": "Quota exceeded for metric: '
            "generativelanguage.googleapis.com/generate_content_free_tier_requests, "
            'limit: 0, model: gemini-2.5-flash-image"}}'
        ),
    )
    assert "free tier" in message.lower()
    assert "limit: 0" not in message
    assert "gemini-2.5-flash-image" not in message


def test_format_image_error_rate_limit_retry():
    message = images._format_image_error(
        status_code=429,
        body='{"error": {"message": "Please retry in 12.5s."}}',
    )
    assert "12 seconds" in message


def test_format_image_error_resource_exhausted():
    message = images._format_image_error(
        status_code=429,
        body='{"error": {"code": 429, "message": "Resource has been exhausted", "status": "RESOURCE_EXHAUSTED"}}',
    )
    assert "rate-limit" in message
