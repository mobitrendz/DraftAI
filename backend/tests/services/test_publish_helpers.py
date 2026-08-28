from app.services.publish import build_linkedin_clipboard_text


def test_build_linkedin_clipboard_text_appends_url():
    text = build_linkedin_clipboard_text(
        teaser_text="Check out my new article!",
        article_url="https://dev.to/user/article",
    )
    assert text == "Check out my new article!\n\nhttps://dev.to/user/article"


def test_build_linkedin_clipboard_text_skips_duplicate_url():
    text = build_linkedin_clipboard_text(
        teaser_text="Read more at https://dev.to/user/article",
        article_url="https://dev.to/user/article",
    )
    assert text == "Read more at https://dev.to/user/article"


def test_build_linkedin_clipboard_text_without_url():
    text = build_linkedin_clipboard_text(
        teaser_text="Coming soon",
        article_url=None,
    )
    assert text == "Coming soon"
