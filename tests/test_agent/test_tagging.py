"""Tests for TagAgent — tag suggestion, parsing, normalization, dedup."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agent.tagging import TagAgent, TagAgentError


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_pipeline() -> MagicMock:
    pipeline = MagicMock()
    rendered = MagicMock()
    rendered.markdown = "# Test Article\n\nThis is a test article about machine learning."
    rendered.html = "<h1>Test Article</h1><p>This is a test article about ML.</p>"
    pipeline.build = AsyncMock(return_value=rendered)
    return pipeline


@pytest.fixture
def mock_router() -> MagicMock:
    router = MagicMock()
    router.active_provider_name = "test-provider"
    router.active_model_name = "test-model"

    async def mock_stream(messages, temperature=0.5, max_tokens=256):
        yield '["machine learning", "AI", "testing"]'

    router.chat_stream = mock_stream
    return router


@pytest.fixture
def mock_templates() -> MagicMock:
    tpl_loader = MagicMock()
    tpl = MagicMock()
    tpl.version = 1
    tpl.config = {"temperature": 0.5, "max_tokens": 256}
    tpl_loader.load.return_value = tpl
    tpl_loader.render.return_value = ("System prompt", "User prompt")
    return tpl_loader


@pytest.fixture
def agent(mock_pipeline, mock_router, mock_templates) -> TagAgent:
    return TagAgent(mock_pipeline, mock_router, mock_templates)


# ── Parse tests ───────────────────────────────────────────────────────────


def test_parse_tags_direct_json_array() -> None:
    result = TagAgent._parse_tags('["tag1", "tag2", "tag3"]')
    assert result == ["tag1", "tag2", "tag3"]


def test_parse_tags_code_block_wrapped() -> None:
    result = TagAgent._parse_tags('```json\n["AI", "Machine Learning"]\n```')
    assert result == ["AI", "Machine Learning"]


def test_parse_tags_with_explanatory_text() -> None:
    result = TagAgent._parse_tags(
        'Here are some tags: ["Python", "async", "FastAPI"] that I recommend.'
    )
    assert result == ["Python", "async", "FastAPI"]


def test_parse_tags_fallback_to_quoted_strings() -> None:
    result = TagAgent._parse_tags("tag1, tag2, tag3")
    assert result == []


def test_parse_tags_empty_input() -> None:
    assert TagAgent._parse_tags("") == []


def test_parse_tags_invalid_json() -> None:
    assert TagAgent._parse_tags("not a json array at all") == []


# ── Normalize + Dedup tests ───────────────────────────────────────────────


def test_normalize_one_fallback_lowercase(agent) -> None:
    assert agent._normalize_one("  Machine Learning  ") == "machine learning"


def test_normalize_one_with_custom_normalizer(agent) -> None:
    def norm(tag: str) -> str:
        return tag.strip().lower().replace(" ", "-")

    agent.set_tag_dependencies(normalizer=norm)
    assert agent._normalize_one("Machine Learning") == "machine-learning"


def test_dedup_removes_existing_tags(agent) -> None:
    result = agent._normalize_and_dedup(
        ["AI", "Python", "testing"],
        ["ai", "existing"],
    )
    # "AI" should be filtered (matches "ai" after normalization)
    assert "AI" not in result
    assert "Python" in result
    assert "testing" in result


def test_dedup_removes_internal_duplicates(agent) -> None:
    result = agent._normalize_and_dedup(
        ["AI", "ai", "Python", "AI"],
        [],
    )
    assert len(result) == 2  # AI + Python
    assert "Python" in result


def test_dedup_respects_max_tags(agent) -> None:
    agent.max_tags = 2
    result = agent._normalize_and_dedup(
        ["Python", "AI", "ML", "Data"],
        [],
    )
    assert len(result) == 2


# ── Integration tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_suggest_returns_tag_dict(agent) -> None:
    result = await agent.suggest(entry_id=1, run_id="test-run-1")
    assert "tags" in result
    assert "raw_tags" in result
    assert "existing_tags" in result
    assert "provider" in result
    assert "model" in result


@pytest.mark.asyncio
async def test_suggest_uses_existing_tags_fn(agent, mock_pipeline, mock_router, mock_templates) -> None:
    # Replace router to return different tags on second call
    call_count = 0

    async def mock_stream(messages, temperature=0.5, max_tokens=256):
        nonlocal call_count
        call_count += 1
        yield '["new tag"]'

    mock_router.chat_stream = mock_stream

    existing_tags = ["existing", "ai"]

    agent.set_tag_dependencies(
        existing_tags_fn=lambda: existing_tags,
    )
    result = await agent.suggest(entry_id=1, run_id="test-run-2")
    assert len(result["existing_tags"]) == 2


@pytest.mark.asyncio
async def test_suggest_no_content_raises_error(agent, mock_pipeline) -> None:
    rendered = MagicMock()
    rendered.markdown = ""
    rendered.html = ""
    mock_pipeline.build = AsyncMock(return_value=rendered)

    with pytest.raises(TagAgentError, match="No content"):
        await agent.suggest(entry_id=1, run_id="test-run-3")


@pytest.mark.asyncio
async def test_register_adds_handler() -> None:
    from core.agent.runtime import AgentRuntime

    # Need a fresh runtime for test isolation
    runtime = AgentRuntime()
    # Reset singleton for test
    AgentRuntime._instance = None
    runtime2 = AgentRuntime()
    try:
        agent = TagAgent(
            MagicMock(), MagicMock(), MagicMock()
        )
        agent.register(runtime2)
        # Handler should be registered under "tagging"
        assert "tagging" in runtime2._handlers
    finally:
        AgentRuntime._instance = None


def test_tag_agent_default_config(agent) -> None:
    assert agent.max_tags == 5
    assert agent.language == "Chinese"


def test_set_tag_dependencies_stores_callables(agent) -> None:
    norm_called = []

    def my_norm(tag: str) -> str:
        norm_called.append(tag)
        return tag.upper()

    def my_existing() -> list[str]:
        return ["a", "b"]

    agent.set_tag_dependencies(normalizer=my_norm, existing_tags_fn=my_existing)
    assert agent._normalizer is not None
    assert agent._existing_tags_fn is not None

    result = agent._normalize_one("hello")
    assert result == "HELLO"
    assert norm_called == ["hello"]
