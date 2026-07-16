# Phase 3 UI Integration Blockers

> 最后更新：2026-07-16 | Phase 3 UI 接口已接通；下列跨模块问题待负责人确认

## 0. UI completion summary

- 新增 `ui/settings/provider_panel.py`、`agent_panel.py`、`settings_dialog.py`，并在主窗口“工具 → 设置”接入。
- 摘要面板覆盖 `idle / queued / running / done / error / cancelled`，按 `entry_id + run_id` 丢弃过期事件，支持取消时保留已生成内容。
- 自动摘要使用可取消的 1 秒单次 `QTimer`；快速切换文章只触发最后一篇。
- 翻译 UI 显示排队、进度、取消、重试状态，并支持原文、双语、仅译文三种显示模式。
- 新增 Phase 3 UI 回归测试：`tests/test_ui/test_phase3_settings.py`、`test_phase3_agent_ui.py`。

## 0.1 Out-of-scope issue: Reader network fallback conflicts with its test

**Observed:** `tests/test_reader/test_pipeline.py::test_pipeline_network_error_raises_fetch_error`
expects a network failure to raise `ReaderFetchError`, but `core/reader/pipeline.py` falls back to
`_fetch_via_webengine()` for the same failure. This also makes headless CI depend on desktop
libraries such as `libXtst.so.6`.

**Owner suggestion:** Reader/Core member.

**Recommended decision:** Choose and document one contract: either preserve `ReaderFetchError`
for generic connection failures, or update the test and mark WebEngine fallback as an integration
test with the required Linux packages installed.

## 0.2 Test environment requirement

`pytest-qt` and `QWebEngineView` tests require Linux desktop runtime libraries. The current test
container is missing `libEGL.so.1` and `libXtst.so.6`, so UI tests cannot create a Qt application.
CI should install the Qt WebEngine runtime libraries and run UI tests with `QT_QPA_PLATFORM=offscreen`.

## 1. Provider configuration and startup registration ✅

**Observed:** `core/agent/providers.py` defines in-memory `ProviderConfig` and `LLMRouter`, while `app/app.py` creates the stores, sync service, pipeline, and `MainWindow` without constructing `AgentRuntime`, `SummaryAgent`, or `TranslationAgent`.

**Resolution (2026-07-16):**
- `app/app.py` now contains `_build_agent_runtime()` which:
  - Loads provider config from QSettings (`llm/base_url`, `llm/model`, `llm/api_key`)
  - Constructs `AgentRuntime` singleton + `LLMRouter` + `TemplateLoader`
  - Registers `SummaryAgent`, `TranslationAgent`, `TagAgent` with AgentRuntime
  - Passes `agent_runtime` to `MainWindow`
- `MainWindow` accepts `agent_runtime` parameter and forwards it to `ReaderView`
- `ReaderView` wires `SummaryPanel` with the runtime for streaming
- If no LLM is configured (`base_url` or `model` empty), agents register but calls will fail gracefully

## 2. Automatic summary configuration ✅

**Resolution (2026-07-16):**
- QSettings keys defined: `agent/auto_summary`, `agent/summary_language`, `agent/summary_detail`
- Defaults: auto_summary=False, language=Chinese, detail=standard
- `SummaryAgent` reads language/detail from settings at construction time
- UI can enable auto-summary by setting `agent/auto_summary=true` and implementing a debounced trigger

## 3. Translation progress content and cache ✅

**Resolution (2026-07-16):**
- `TranslationAgent` now accepts `AgentStore` (optional) for result persistence
- Cache key: `(entry_id, provider, model, prompt_version)`
- `_handler` wraps `translate()` with AgentStore create/complete/cancel lifecycle
- `translate()` checks AgentStore cache before starting, skips LLM on hit
- Result includes `failed_segment_indices: list[int]` for targeted retry
- Translation result dict includes `_cache_key`, `provider`, `model` for cache matching

## 4. Phase 4 tag contracts unavailable ✅

**Resolution (2026-07-16):**
- `core/tags/normalizer.py` — `TagNormalizer` with Unicode NFC, whitespace collapse, CJK-aware lowercase, alias resolution
- `core/tags/cooccurrence.py` — `CooccurrenceEngine` with Jaccard similarity + 5-min cache
- `store/tag_store.py` — Full `TagStore` (CRUD, entry associations, batch tagging, aliases, temp tags)
- `core/agent/tagging.py` — `TagAgent` with LLM suggestions, JSON error-tolerant parsing, dedup, optional normalizer/store injection
- Tests: 14 normalizer + 17 tag_store + 17 tagging = 48 passed

## 5. Uploaded UI dependency mismatch ✅

**Resolution (2026-07-16):**
- `ui/reader/reader_toolbar.py` — restored from complete build
- `ui/reader/theme_manager.py` — restored from complete build
- `ui/reader/theme.py` — Theme dataclass created
- `ui/theme_controller.py` — global theme controller created
- `ui/theme.py` — LIGHT_PALETTE + DARK_PALETTE + Palette dataclass created
- `app/styles.py` — updated to palette-driven `application_stylesheet(palette)`
