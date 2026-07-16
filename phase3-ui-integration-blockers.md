# Phase 3 UI Integration Blockers

> 最后更新：2026-07-16 | 状态：全部已解决 ✅

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
