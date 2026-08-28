from unittest.mock import patch

from app.core import security


def test_render_email_template_coverage():
    context = {"project_name": "Test Project"}
    # Mock the file reading to avoid FileNotFoundError in CI
    # Directly mock read_text to return the template string
    with patch(
        "pathlib.Path.read_text", return_value="<html>{{ project_name }}</html>"
    ):
        content = security.render_email_template(
            template_name="test_template.html", context=context
        )
    assert "Test Project" in content
