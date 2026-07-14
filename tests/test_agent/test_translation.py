# tests/test_agent/test_translation.py
"""TranslationAgent 单元测试（mock AsyncOpenAI，无真实 LLM 调用）。"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.agent.translation import TranslationAgent, TranslationAgentError

# ── HTML Fixture ─────────────────────────────────────────────────────────

TEST_HTML = """<h1>Test Title</h1>
<p>This is the first paragraph of the article. It introduces the topic.</p>
<p>This is the second paragraph with more details about the subject matter.</p>
<ul>
<li>Key point one</li>
<li>Key point two</li>
</ul>
<p>This is the concluding paragraph that wraps up the discussion.</p>"""


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
async def entry_id(db) -> int:
    """在内存数据库中创建 feed + entry。"""
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore

    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(
        feed.id, "guid-trans-test", "https://example.com/article",
        "Test Article", "Summary text", "Author", None,
    )
    return entry.id


@pytest.fixture
def mock_pipeline(entry_id: int) -> MagicMock:
    """返回模拟的 ReaderPipeline。"""
    pipeline = MagicMock()
    rendered = MagicMock()
    rendered.html = TEST_HTML
    rendered.markdown = "# Test\n\nContent"
    rendered.title = "Test Article"
    pipeline.build = AsyncMock(return_value=rendered)
    return pipeline


@pytest.fixture
def mock_router() -> MagicMock:
    """返回模拟的 LLMRouter，返回预设译文。"""
    router = MagicMock()
    router.active_provider_name = "ollama-local"
    router.active_model_name = "qwen3"
    router.chat_stream = MagicMock()

    async def _fake_stream(*args, **kwargs):
        messages = kwargs.get("messages", args[0] if args else [])
        user_content = ""
        for m in messages:
            if isinstance(m, dict) and m.get("role") == "user":
                user_content = m.get("content", "")
        # 从 user prompt 提取 paragraph 关键词做简单 mock
        if "first paragraph" in user_content:
            yield "[ZH] 这是文章的第一段。它介绍了主题。"
        elif "second paragraph" in user_content:
            yield "[ZH] 这是第二段，包含更多细节。"
        elif "concluding" in user_content:
            yield "[ZH] 这是总结段。"
        elif "Key point" in user_content:
            yield "[ZH] 要点：第一项和第二项。"
        else:
            yield "[ZH] 已翻译。"

    router.chat_stream.side_effect = _fake_stream
    return router


@pytest.fixture
def mock_templates() -> MagicMock:
    """返回模拟的 TemplateLoader。"""
    from core.agent.template_loader import PromptTemplate

    templates = MagicMock()
    tpl = PromptTemplate(
        agent_type="translation",
        version=1,
        system_prompt="You are a translator.",
        user_prompt_template="Translate to {{ target_language }}: {{ paragraph }}",
        config={"temperature": 0.1, "max_tokens": 2048},
        source="builtin",
    )
    templates.load = MagicMock(return_value=tpl)
    templates.render = MagicMock(
        return_value=("You are a translator.", "Translate to Chinese: text here")
    )
    return templates


@pytest.fixture
def mock_runtime() -> MagicMock:
    """返回模拟的 AgentRuntime。"""
    runtime = MagicMock()
    runtime.register = MagicMock()
    runtime.broadcast_chunk = MagicMock()
    runtime.signals = MagicMock()
    runtime.signals.state_changed = MagicMock()
    return runtime


@pytest.fixture
def agent(mock_pipeline, mock_router, mock_templates) -> TranslationAgent:
    return TranslationAgent(
        pipeline=mock_pipeline,
        router=mock_router,
        templates=mock_templates,
    )


# ── Tests ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_translation_agent_registers_handler(
    agent, mock_runtime
) -> None:
    """验证 register() 向 AgentRuntime 注册 'translation' handler。"""
    agent.register(mock_runtime)
    mock_runtime.register.assert_called_once()
    call_args = mock_runtime.register.call_args
    assert call_args[0][0] == "translation"
    assert callable(call_args[0][1])


@pytest.mark.asyncio
async def test_split_html_into_segments(agent) -> None:
    """验证 HTML 按顶级块元素正确分段。"""
    segments = agent._split_html(TEST_HTML)
    # h1 + 3 p + 1 ul = 5 segments
    assert len(segments) == 5
    assert segments[0].text == "Test Title"
    assert "first paragraph" in segments[1].text
    assert "second paragraph" in segments[2].text
    assert "Key point one" in segments[3].text
    assert "concluding" in segments[4].text


@pytest.mark.asyncio
async def test_split_html_skips_nested(
    agent,
) -> None:
    """验证跳过嵌套块元素（ul 内的 li 不被重复提取）。"""
    segments = agent._split_html(TEST_HTML)
    # li 文本虽有 "Key point"，但 li 不是顶级块，不单独成段
    # ul segment 应包含其所有子元素的文本
    ul_seg = [s for s in segments if "Key point one" in s.text]
    assert len(ul_seg) == 1
    assert "Key point two" in ul_seg[0].text


@pytest.mark.asyncio
async def test_translation_empty_html_raises_error(
    mock_pipeline, mock_router, mock_templates, entry_id
) -> None:
    """验证无 HTML 内容时抛出 TranslationAgentError。"""
    rendered = MagicMock()
    rendered.html = ""
    rendered.markdown = ""
    mock_pipeline.build = AsyncMock(return_value=rendered)

    agent = TranslationAgent(
        pipeline=mock_pipeline,
        router=mock_router,
        templates=mock_templates,
    )

    with pytest.raises(TranslationAgentError, match="No HTML content"):
        await agent.translate(entry_id, "run-empty")


@pytest.mark.asyncio
async def test_translation_assembles_bilingual_html(
    agent, mock_runtime, entry_id
) -> None:
    """验证翻译结果组装为双语 HTML 格式。"""
    agent.register(mock_runtime)
    agent.target_language = "Chinese"

    handler = mock_runtime.register.call_args[0][1]
    result = await handler(entry_id, "run-bilingual")

    assert result is not None
    assert "html" in result
    assert result["paragraphs_total"] == 5
    assert result["target_language"] == "Chinese"

    html = result["html"]
    # 包含双语标记
    assert "mercury-trans-block" in html
    assert "mercury-original" in html
    assert "mercury-translated" in html


@pytest.mark.asyncio
async def test_translation_broadcasts_progress(
    agent, mock_runtime, entry_id
) -> None:
    """验证翻译过程中广播进度信号。"""
    agent.register(mock_runtime)
    handler = mock_runtime.register.call_args[0][1]
    await handler(entry_id, "run-progress")

    # 验证 progress emit 被调用
    emit_calls = mock_runtime.signals.state_changed.emit.call_args_list
    # 至少应有起始+完成事件
    assert len(emit_calls) >= 2


@pytest.mark.asyncio
async def test_translation_concurrency_degree(
    agent, mock_runtime, entry_id
) -> None:
    """验证并发度配置生效。"""
    agent.degree = 2
    assert agent.degree == 2

    with pytest.raises(ValueError, match="between 1 and 5"):
        agent.degree = 0

    with pytest.raises(ValueError, match="between 1 and 5"):
        agent.degree = 6


@pytest.mark.asyncio
async def test_translation_retries_failed_segments(
    agent, mock_runtime, mock_router, entry_id
) -> None:
    """验证失败段落重试机制。"""
    from core.agent.providers import LLMRouterError

    call_count = 0

    async def _fail_then_recover(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:  # 前两次失败
            raise LLMRouterError("Temporary failure")
        yield "[ZH] Recovered translation."

    mock_router.chat_stream = MagicMock(side_effect=_fail_then_recover)

    agent.register(mock_runtime)
    handler = mock_runtime.register.call_args[0][1]
    result = await handler(entry_id, "run-retry")

    # 应触发重试逻辑，最终成功
    assert result is not None
    # 检查有成功段落
    assert result["paragraphs_success"] >= 1
