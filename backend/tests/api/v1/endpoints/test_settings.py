import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_read_platform_config_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/settings/platform")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_read_platform_config_defaults(
    client: AsyncClient, isolated_user_token: str
):
    response = await client.get(
        "/api/v1/settings/platform",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["devto_enabled"] is True
    assert data["linkedin_enabled"] is True
    assert data["has_devto_api_key"] is False


@pytest.mark.asyncio
async def test_update_platform_config(
    client: AsyncClient, normal_user_token: str
):
    response = await client.patch(
        "/api/v1/settings/platform",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={
            "devto_enabled": False,
            "devto_profile_url": "https://dev.to/draftai",
            "devto_api_key": "secret-devto-key",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["devto_enabled"] is False
    assert data["devto_profile_url"] == "https://dev.to/draftai"
    assert data["has_devto_api_key"] is True
    assert "secret-devto-key" not in response.text


@pytest.mark.asyncio
async def test_read_ai_config_defaults(client: AsyncClient, isolated_user_token: str):
    response = await client.get(
        "/api/v1/settings/ai",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "openai"
    assert data["model"] == "gpt-4o"
    assert data["cover_image_model"] == "gemini-2.5-flash-image"
    assert data["saved_api_keys"]["openai"] is False


@pytest.mark.asyncio
async def test_update_ai_config(client: AsyncClient, normal_user_token: str):
    response = await client.patch(
        "/api/v1/settings/ai",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={
            "model": "gpt-4o-mini",
            "temperature": 0.4,
            "provider_api_keys": {"openai": "sk-test-openai"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "gpt-4o-mini"
    assert data["temperature"] == 0.4
    assert data["saved_api_keys"]["openai"] is True
    assert "sk-test-openai" not in response.text


@pytest.mark.asyncio
async def test_update_ai_config_legacy_key_field(client: AsyncClient, normal_user_token: str):
    response = await client.patch(
        "/api/v1/settings/ai",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"openai_api_key": "sk-legacy-key"},
    )
    assert response.status_code == 200
    assert response.json()["saved_api_keys"]["openai"] is True


@pytest.mark.asyncio
async def test_update_ai_config_cover_image_model(
    client: AsyncClient, normal_user_token: str
):
    response = await client.patch(
        "/api/v1/settings/ai",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"cover_image_model": "dall-e-3"},
    )
    assert response.status_code == 200
    assert response.json()["cover_image_model"] == "dall-e-3"


@pytest.mark.asyncio
async def test_read_ai_models_catalog(client: AsyncClient, isolated_user_token: str):
    response = await client.get(
        "/api/v1/settings/ai/models",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    providers = {entry["slug"]: entry for entry in data["providers"]}
    assert len(providers) >= 5
    assert "openai" in providers
    assert providers["openai"]["default_model"] == "gpt-4o"
    assert providers["openai"]["label"] == "OpenAI"
    assert any(m["id"] == "gpt-4o-mini" for m in providers["openai"]["models"])
    assert providers["gemini"]["default_model"] == "gemini-2.0-flash"
    assert any(m["id"] == "gemini-2.5-pro" for m in providers["gemini"]["models"])
    groq_models = [m["id"] for m in providers["groq"]["models"]]
    assert "gemma2-9b-it" not in groq_models
    assert "llama-3.3-70b-versatile" in groq_models
    assert providers["anthropic"]["default_model"] == "claude-3-5-sonnet-20241022"
    assert data["default_cover_image_model"] == "gemini-2.5-flash-image"
    assert data["cover_image_models"] == []
    assert len(data["credential_providers"]) >= 5
    assert "ollama" in providers
    assert providers["ollama"]["models_source"] == "ollama"
    assert data["ollama"] is not None
    assert data["ollama"]["base_url"]


@pytest.mark.asyncio
async def test_read_ai_models_catalog_cover_models_require_provider_keys(
    client: AsyncClient, normal_user_token: str
):
    await client.patch(
        "/api/v1/settings/ai",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={"provider_api_keys": {"gemini": "AIza-test-gemini"}},
    )

    response = await client.get(
        "/api/v1/settings/ai/models",
        headers={"Authorization": f"Bearer {normal_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    cover_ids = {model["id"] for model in data["cover_image_models"]}
    assert cover_ids
    assert all(model["key_provider"] == "gemini" for model in data["cover_image_models"])
    assert "dall-e-3" not in cover_ids


@pytest.mark.asyncio
async def test_read_ai_models_catalog_ollama_live_models(
    client: AsyncClient, isolated_user_token: str, monkeypatch
):
    from app.models.ai_agent_config import AIModelOption

    async def fake_list_ollama_models(*, base_url: str):
        return [
            AIModelOption(id="qwen3:8b", label="qwen3:8b", description="5.2 GB local"),
            AIModelOption(id="gemma4:12b", label="gemma4:12b", description="7.6 GB local"),
        ]

    monkeypatch.setattr(
        "app.crud.ai_catalog.list_ollama_models",
        fake_list_ollama_models,
    )

    response = await client.get(
        "/api/v1/settings/ai/models",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    ollama = next(p for p in data["providers"] if p["slug"] == "ollama")
    assert ollama["default_model"] == "qwen3:8b"
    assert [m["id"] for m in ollama["models"]] == ["qwen3:8b", "gemma4:12b"]
    assert data["ollama"]["reachable"] is True
    assert data["ollama"]["model_count"] == 2


@pytest.mark.asyncio
async def test_update_ai_config_ollama_base_url(
    client: AsyncClient, normal_user_token: str
):
    response = await client.patch(
        "/api/v1/settings/ai",
        headers={"Authorization": f"Bearer {normal_user_token}"},
        json={
            "provider": "ollama",
            "model": "qwen3:8b",
            "ollama_base_url": "http://localhost:11434/v1",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "ollama"
    assert data["model"] == "qwen3:8b"
    assert data["ollama_base_url"] == "http://localhost:11434/v1"


@pytest.mark.asyncio
async def test_create_custom_provider_lists_models(
    client: AsyncClient, isolated_user_token: str, monkeypatch
):
    from app.models.ai_agent_config import AIModelOption

    async def fake_discover(**_kwargs):
        return [
            AIModelOption(id="model-a", label="Model A", description=None),
            AIModelOption(id="model-b", label="Model B", description=None),
        ]

    monkeypatch.setattr(
        "app.crud.ai_catalog.discover_provider_models",
        fake_discover,
    )

    response = await client.post(
        "/api/v1/settings/ai/providers",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
        json={
            "display_name": "My Local API",
            "base_url": "http://localhost:1234/v1",
            "api_adapter": "openai_compatible",
            "auth_style": "bearer",
            "api_key": "test-key",
        },
    )
    assert response.status_code == 200
    created = response.json()
    assert created["display_name"] == "My Local API"
    assert created["slug"].startswith("custom-")
    assert created["has_api_key"] is True

    catalog = await client.get(
        "/api/v1/settings/ai/models",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
    )
    assert catalog.status_code == 200
    custom = next(
        p for p in catalog.json()["providers"] if p["slug"] == created["slug"]
    )
    assert custom["is_custom"] is True
    assert [m["id"] for m in custom["models"]] == ["model-a", "model-b"]


@pytest.mark.asyncio
async def test_delete_custom_provider(
    client: AsyncClient, isolated_user_token: str, monkeypatch
):
    async def fake_discover(**_kwargs):
        from app.models.ai_agent_config import AIModelOption

        return [AIModelOption(id="only-model", label="Only", description=None)]

    monkeypatch.setattr(
        "app.crud.ai_catalog.discover_provider_models",
        fake_discover,
    )

    created = await client.post(
        "/api/v1/settings/ai/providers",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
        json={
            "display_name": "Temp Provider",
            "base_url": "http://localhost:9999/v1",
            "api_adapter": "openai_compatible",
            "auth_style": "bearer",
            "api_key": "temp-key",
        },
    )
    provider_id = created.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/settings/ai/providers/{provider_id}",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
    )
    assert delete_response.status_code == 204

    catalog = await client.get(
        "/api/v1/settings/ai/models",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
    )
    slugs = {p["slug"] for p in catalog.json()["providers"]}
    assert created.json()["slug"] not in slugs


@pytest.mark.asyncio
async def test_refresh_ollama_models(
    client: AsyncClient, isolated_user_token: str, monkeypatch
):
    from app.models.ai_agent_config import AIModelOption

    call_count = 0

    async def fake_list_ollama(*, base_url: str):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [AIModelOption(id="qwen3:8b", label="qwen3:8b", description="5.2 GB local")]
        return [
            AIModelOption(id="qwen3:8b", label="qwen3:8b", description="5.2 GB local"),
            AIModelOption(id="gemma4:12b", label="gemma4:12b", description="7.6 GB local"),
        ]

    monkeypatch.setattr("app.crud.ai_catalog.list_ollama_models", fake_list_ollama)
    monkeypatch.setattr("app.services.ai.model_discovery.list_ollama_models", fake_list_ollama)

    response = await client.post(
        "/api/v1/settings/ai/providers/ollama/refresh-models",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "ollama"
    assert data["added_count"] == 1
    assert data["total_count"] == 2
    assert any(m["id"] == "gemma4:12b" for m in data["models"])


@pytest.mark.asyncio
async def test_refresh_gemini_models(
    client: AsyncClient, isolated_user_token: str, monkeypatch
):
    from app.models.ai_agent_config import AIModelOption

    save_key = await client.patch(
        "/api/v1/settings/ai",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
        json={"provider_api_keys": {"gemini": "gemini-test-key"}},
    )
    assert save_key.status_code == 200

    async def fake_discover(**kwargs):
        assert kwargs["api_adapter"] == "gemini"
        assert kwargs["api_key"] == "gemini-test-key"
        return [
            AIModelOption(id="gemini-2.0-flash", label="Gemini 2.0 Flash", description=None),
            AIModelOption(id="gemini-2.5-pro", label="Gemini 2.5 Pro", description=None),
            AIModelOption(
                id="gemini-3-flash",
                label="Gemini 3 Flash",
                description="Released today",
            ),
        ]

    monkeypatch.setattr("app.crud.ai_catalog.discover_provider_models", fake_discover)

    response = await client.post(
        "/api/v1/settings/ai/providers/gemini/refresh-models",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "gemini"
    assert data["added_count"] == 1
    assert any(m["id"] == "gemini-3-flash" for m in data["models"])


@pytest.mark.asyncio
async def test_catalog_marks_gemini_refreshable_when_key_saved(
    client: AsyncClient, isolated_user_token: str
):
    await client.patch(
        "/api/v1/settings/ai",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
        json={"provider_api_keys": {"gemini": "gemini-test-key"}},
    )
    response = await client.get(
        "/api/v1/settings/ai/models",
        headers={"Authorization": f"Bearer {isolated_user_token}"},
    )
    assert response.status_code == 200
    gemini = next(p for p in response.json()["providers"] if p["slug"] == "gemini")
    assert gemini["can_refresh_models"] is True
