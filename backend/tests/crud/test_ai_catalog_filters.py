import uuid

from app.crud import ai_catalog
from app.models.ai_agent_config import AIModelOption
from app.models.ai_catalog import AIModelModality, AIModelRow


def test_filter_model_rows_excludes_low_context_models():
    provider_id = uuid.uuid4()
    rows = [
        AIModelRow(
            provider_id=provider_id,
            model_key="big-model",
            display_name="Big",
            modality=AIModelModality.TEXT,
            context_window_tokens=128000,
        ),
        AIModelRow(
            provider_id=provider_id,
            model_key="small-model",
            display_name="Small",
            modality=AIModelModality.TEXT,
            context_window_tokens=8192,
        ),
        AIModelRow(
            provider_id=provider_id,
            model_key="unknown-model",
            display_name="Unknown",
            modality=AIModelModality.TEXT,
            context_window_tokens=None,
        ),
    ]

    filtered = ai_catalog._filter_model_rows_for_draft_generation(rows)
    assert [row.model_key for row in filtered] == ["big-model"]


def test_filter_model_options_allows_unknown_for_live_providers():
    models = [
        AIModelOption(id="local-llm", label="Local LLM", description=None),
        AIModelOption(
            id="tiny-model",
            label="Tiny",
            description=None,
            context_window_tokens=4096,
        ),
    ]

    filtered = ai_catalog._filter_model_options_for_draft_generation(
        models,
        allow_unknown_context=True,
    )
    assert [model.id for model in filtered] == ["local-llm"]
