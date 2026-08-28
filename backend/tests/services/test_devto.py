from app.services.platforms.devto import prepare_devto_body_markdown


def test_prepare_devto_body_markdown_strips_duplicate_title_heading():
    body = prepare_devto_body_markdown(
        title="My Article Title",
        body_markdown="# My Article Title\n\nIntro paragraph.",
    )
    assert body == "Intro paragraph."


def test_prepare_devto_body_markdown_keeps_distinct_heading():
    body = prepare_devto_body_markdown(
        title="My Article Title",
        body_markdown="# Different Section\n\nContent.",
    )
    assert body.startswith("# Different Section")
