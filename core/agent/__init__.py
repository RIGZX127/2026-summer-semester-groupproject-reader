"""Core Agent layer — AI-powered features.

Public API surface (G3.1 + G3.2 + G3.3 frozen):

    runtime:
        AgentRuntime       — Singleton agent runtime (queue, signals, lifecycle)
        AgentUIEvent       — Immutable event passed to UI via Qt signals
        AgentSignals       — Qt Signal collection (state_changed, chunk_received)
        AgentStatus        — Literal type alias

    providers:
        ProviderConfig     — Single LLM provider configuration
        LLMRouter          — Primary → fallback routing with streaming
        LLMRouterError     — All providers exhausted

    summary:
        SummaryAgent       — AI article summary (caching, streaming)
        SummaryAgentError  — Summary generation failure

    translation:
        TranslationAgent   — AI article translation (segmented, concurrent)
        TranslationAgentError

    tagging:
        TagAgent           — AI tag suggestions (dedup, normalization)
        TagAgentError

    template_loader:
        TemplateLoader     — Two-layer prompt template loader (builtin + sandbox)
        PromptTemplate     — Parsed template dataclass

    stream_buffer:
        StreamBuffer       — 80ms chunk merger for streaming UI output
"""
