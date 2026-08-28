import pytest
import httpx

from app.models.ai_agent_config import AIModelOption
from app.services.ai import model_discovery


@pytest.mark.asyncio
async def test_list_gemini_models_parses_text_models(monkeypatch):
    class FakeResponse:
        status_code = 200
        request = httpx.Request("GET", "https://example.com/models")

        @staticmethod
        def json():
            return {
                "models": [
                    {
                        "name": "models/gemini-2.5-pro",
                        "displayName": "Gemini 2.5 Pro",
                        "description": "Best for complex writing",
                        "supportedGenerationMethods": ["generateContent"],
                        "inputTokenLimit": 1048576,
                    },
                    {
                        "name": "models/gemini-2.0-flash-lite",
                        "displayName": "Gemini 2.0 Flash Lite",
                        "description": "Small context",
                        "supportedGenerationMethods": ["generateContent"],
                        "inputTokenLimit": 4096,
                    },
                    {
                        "name": "models/gemini-3-pro-image",
                        "displayName": "Gemini 3 Pro Image",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/embedding-001",
                        "displayName": "Embedding",
                        "supportedGenerationMethods": ["embedContent"],
                    },
                ]
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, params=None):
            assert url.endswith("/models")
            assert params == {"key": "gemini-key"}
            return FakeResponse()

    monkeypatch.setattr(model_discovery.httpx, "AsyncClient", lambda **_kwargs: FakeClient())

    models = await model_discovery.list_gemini_models(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        api_key="gemini-key",
    )
    assert [m.id for m in models] == ["gemini-2.5-pro"]
    assert models[0].label == "Gemini 2.5 Pro"
    assert models[0].context_window_tokens == 1048576


@pytest.mark.asyncio
async def test_list_gemini_models_skips_low_context_models(monkeypatch):
    class FakeResponse:
        status_code = 200
        request = httpx.Request("GET", "https://example.com/models")

        @staticmethod
        def json():
            return {
                "models": [
                    {
                        "name": "models/gemini-2.0-flash-lite",
                        "displayName": "Gemini 2.0 Flash Lite",
                        "supportedGenerationMethods": ["generateContent"],
                        "inputTokenLimit": 4096,
                    }
                ]
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, params=None):
            return FakeResponse()

    monkeypatch.setattr(model_discovery.httpx, "AsyncClient", lambda **_kwargs: FakeClient())

    models = await model_discovery.list_gemini_models(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        api_key="gemini-key",
    )
    assert models == []


@pytest.mark.asyncio
async def test_list_anthropic_models_parses_response(monkeypatch):
    class FakeResponse:
        status_code = 200
        request = httpx.Request("GET", "https://example.com/models")

        @staticmethod
        def json():
            return {
                "data": [
                    {
                        "id": "claude-sonnet-4-20250514",
                        "display_name": "Claude Sonnet 4",
                        "description": "Latest Sonnet generation",
                    }
                ]
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, headers=None):
            assert url.endswith("/models")
            assert headers["x-api-key"] == "anthropic-key"
            return FakeResponse()

    monkeypatch.setattr(model_discovery.httpx, "AsyncClient", lambda **_kwargs: FakeClient())

    models = await model_discovery.list_anthropic_models(
        base_url="https://api.anthropic.com/v1",
        api_key="anthropic-key",
    )
    assert models == [
        AIModelOption(
            id="claude-sonnet-4-20250514",
            label="Claude Sonnet 4",
            description="Latest Sonnet generation",
        )
    ]


@pytest.mark.asyncio
async def test_discover_provider_models_routes_gemini_and_anthropic():
    async def fake_gemini(**_kwargs):
        return [AIModelOption(id="gemini-2.5-pro", label="Gemini 2.5 Pro", description=None)]

    async def fake_anthropic(**_kwargs):
        return [
            AIModelOption(
                id="claude-sonnet-4-20250514",
                label="Claude Sonnet 4",
                description=None,
            )
        ]

    model_discovery.list_gemini_models = fake_gemini
    model_discovery.list_anthropic_models = fake_anthropic

    gemini = await model_discovery.discover_provider_models(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        api_adapter="gemini",
        api_key="gemini-key",
    )
    anthropic = await model_discovery.discover_provider_models(
        base_url="https://api.anthropic.com/v1",
        api_adapter="anthropic_messages",
        api_key="anthropic-key",
    )
    assert gemini[0].id == "gemini-2.5-pro"
    assert anthropic[0].id == "claude-sonnet-4-20250514"
