# tests/test_agent/test_summary.py
"""SummaryAgent 单元测试（mock AsyncOpenAI，无真实 LLM 调用）。"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.agent.summary import SummaryAgent, SummaryAgentError

# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
async def entry_id(db) -> int:
    """在内存数据库中创建 feed + entry，返回 entry ID 用于外键约束。"""
    from store.entry_store import EntryStore
    from store.feed_store import FeedStore

    feed = await FeedStore(db).add("https://example.com/feed")
    entry = await EntryStore(db).add(
        feed.id, "guid-summary-test", "https://example.com/article",
        "Test Article", "Summary text", "Author", None,
    )
    return entry.id


@pytest.fixture
def mock_pipeline(entry_id: int) -> MagicMock:
    """返回模拟的 ReaderPipeline，提供 markdown 内容。"""
    pipeline = MagicMock()
    rendered = MagicMock()
    rendered.markdown = "# Test Article\n\nThis is test content for summarization."
    rendered.html = "<h1>Test Article</h1>"
    rendered.title = "Test Article"
    pipeline.build = AsyncMock(return_value=rendered)
    return pipeline


@pytest.fixture
def mock_router() -> MagicMock:
    """返回模拟的 LLMRouter，流式输出预定义 chunks。"""
    router = MagicMock()
    router.active_provider_name = "ollama-local"
    router.active_model_name = "qwen3"
    router.chat_stream = MagicMock()

    async def _fake_stream(*args, **kwargs):
        for chunk in ["Summary: ", "This is ", "a test ", "summary."]:
            yield chunk

    router.chat_stream.side_effect = _fake_stream
    return router


@pytest.fixture
def mock_templates() -> MagicMock:
    """返回模拟的 TemplateLoader。"""
    from core.agent.template_loader import PromptTemplate

    templates = MagicMock()
    tpl = PromptTemplate(
        agent_type="summary",
        version=1,
        system_prompt="You are a summarizer.",
        user_prompt_template="Summarize: {{ content }}",
        config={"temperature": 0.3, "max_tokens": 1024},
        source="builtin",
    )
    templates.load = MagicMock(return_value=tpl)
    templates.render = MagicMock(
        return_value=(
            "You are a summarizer.",
            "Summarize: # Test Article\n\nThis is test content.",
        )
    )
    return templates


@pytest.fixture
def mock_runtime() -> MagicMock:
    """返回模拟的 AgentRuntime。"""
    runtime = MagicMock()
    runtime.register = MagicMock()
    runtime.broadcast_chunk = MagicMock()
    return runtime


@pytest.fixture
def agent(
    db, mock_pipeline, mock_router, mock_templates
) -> SummaryAgent:
    from store.agent_store import AgentStore

    return SummaryAgent(
        pipeline=mock_pipeline,
        router=mock_router,
        templates=mock_templates,
        agent_store=AgentStore(db),
    )


# ── Tests ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_summary_agent_registers_handler(
    agent, mock_runtime
) -> None:
    """验证 register() 向 AgentRuntime 注册 'summary' handler。"""
    agent.register(mock_runtime)
    mock_runtime.register.assert_called_once()
    call_args = mock_runtime.register.call_args
    assert call_args[0][0] == "summary"
    assert callable(call_args[0][1])


@pytest.mark.asyncio
async def test_summary_generates_and_persists_result(
    agent, mock_runtime, entry_id
) -> None:
    """验证流式生成摘要并持久化到 AgentStore。"""
    agent.register(mock_runtime)
    agent.detail_level = "standard"
    agent.language = "Chinese"

    # 获取注册的 handler
    handler = mock_runtime.register.call_args[0][1]
    result = await handler(entry_id=entry_id, run_id="test-run-001")

    assert result is not None
    assert "summary" in result
    assert "Summary: This is a test summary." == result["summary"]
    assert result["provider"] == "ollama-local"


@pytest.mark.asyncio
async def test_summary_broadcasts_chunks_to_runtime(
    agent, mock_runtime, entry_id
) -> None:
    """验证每个 chunk 通过 runtime.broadcast_chunk() 发送给 UI。"""
    agent.register(mock_runtime)
    handler = mock_runtime.register.call_args[0][1]
    await handler(entry_id=entry_id, run_id="run-002")

    # StreamBuffer 合并后的 flush 调用
    calls = mock_runtime.broadcast_chunk.call_args_list
    assert len(calls) >= 1  # 至少有一次 flush
    # 最后一个 chunk 包含完整文本
    assert calls[-1][0][0] == "run-002"
    assert calls[-1][0][1] == entry_id
    assert calls[-1][0][2] == "summary"


@pytest.mark.asyncio
async def test_summary_no_markdown_raises_error(
    db, mock_pipeline, mock_router, mock_templates, entry_id
) -> None:
    """验证文章无 markdown 时抛出 SummaryAgentError。"""
    from store.agent_store import AgentStore

    # 使 pipeline 返回空 markdown
    rendered = MagicMock()
    rendered.markdown = ""
    rendered.html = "<p>empty</p>"
    mock_pipeline.build = AsyncMock(return_value=rendered)

    agent = SummaryAgent(
        pipeline=mock_pipeline,
        router=mock_router,
        templates=mock_templates,
        agent_store=AgentStore(db),
    )

    mock_rt = MagicMock()
    agent.register(mock_rt)
    handler = mock_rt.register.call_args[0][1]

    with pytest.raises(SummaryAgentError, match="No markdown content"):
        await handler(entry_id=entry_id, run_id="run-err")


@pytest.mark.asyncio
async def test_summary_cache_hit_skips_llm_call(
    agent, mock_runtime, mock_router, entry_id
) -> None:
    """验证缓存命中时跳过 LLM 调用，直接返回缓存结果。"""
    agent.register(mock_runtime)
    handler = mock_runtime.register.call_args[0][1]

    # 第一次调用：生成并缓存
    await handler(entry_id=entry_id, run_id="run-001")
    llm_call_count = mock_router.chat_stream.call_count

    # 第二次调用：应命中缓存，不再调用 LLM
    await handler(entry_id=entry_id, run_id="run-002")
    assert mock_router.chat_stream.call_count == llm_call_count  # 未新增 LLM 调用


@pytest.mark.asyncio
async def test_summary_error_persisted_in_agent_store(
    agent, mock_runtime, mock_router, entry_id
) -> None:
    """验证 LLM 调用失败时错误信息持久化到 AgentStore。"""
    from core.agent.providers import LLMRouterError

    # 使 router 抛出异常
    mock_router.chat_stream.side_effect = LLMRouterError("Connection refused")

    agent.register(mock_runtime)
    handler = mock_runtime.register.call_args[0][1]

    with pytest.raises(LLMRouterError, match="Connection refused"):
        await handler(entry_id=entry_id, run_id="run-fail")

    # 检查 AgentStore 中记录了错误
    store = agent._agent_store
    latest = await store.get_latest(entry_id, "summary")
    assert latest is not None
    assert latest.status == "error"
    assert "Connection refused" in (latest.error or "")
