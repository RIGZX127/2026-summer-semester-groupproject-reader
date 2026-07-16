# app/app.py
"""Mercury application lifecycle and dependency wiring.

启动流程：
  1. 初始化数据库
  2. 从 QSettings 加载 LLM provider 配置
  3. 构建 AgentRuntime + 注册所有 Agent（Summary / Translation / Tagging）
  4. 注入 MainWindow
"""
from __future__ import annotations

import logging
import pathlib

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.state import state
from app.styles import application_stylesheet
from core.feed.sync import SyncService
from core.reader.pipeline import ReaderPipeline
from store.db import DatabaseManager
from store.entry_store import EntryStore
from store.feed_store import FeedStore
from ui.main_window import MainWindow

_logger = logging.getLogger(__name__)

# ── QSettings keys for provider configuration ───────────────────────────
_PROVIDER_BASE_URL = "llm/base_url"
_PROVIDER_MODEL = "llm/model"
_PROVIDER_API_KEY = "llm/api_key"
_AUTO_SUMMARY = "agent/auto_summary"       # bool: 切换文章后自动生成摘要
_SUMMARY_LANG = "agent/summary_language"    # 摘要语言
_SUMMARY_DETAIL = "agent/summary_detail"    # brief | standard | detailed
_TRANSLATION_LANG = "agent/translation_language"  # 翻译目标语言
_TRANSLATION_DEGREE = "agent/translation_degree"  # 并发度 1–5

# 默认值
_DEFAULTS = {
    _AUTO_SUMMARY: False,
    _SUMMARY_LANG: "Chinese",
    _SUMMARY_DETAIL: "standard",
    _TRANSLATION_LANG: "Chinese",
    _TRANSLATION_DEGREE: 3,
}


def _default_data_path() -> str:
    """返回平台默认数据库路径。"""
    base = pathlib.Path.home() / ".mercury"
    base.mkdir(parents=True, exist_ok=True)
    return str(base / "mercury.db")


def _build_agent_runtime(
    db: DatabaseManager,
    settings: QSettings,
) -> tuple:
    """构建 AgentRuntime 并注册所有 Agent。

    Returns:
        (AgentRuntime, has_llm_configured: bool)
        若 LLM 未配置，AgentRuntime 仍然可用，但 submit() 会返回错误。
    """
    from core.agent.runtime import AgentRuntime
    from core.agent.providers import ProviderConfig, LLMRouter
    from core.agent.template_loader import TemplateLoader
    from core.agent.summary import SummaryAgent
    from core.agent.translation import TranslationAgent
    from core.agent.tagging import TagAgent
    from core.reader.pipeline import ReaderPipeline
    from store.agent_store import AgentStore

    runtime = AgentRuntime()
    pipeline = ReaderPipeline(db)
    agent_store = AgentStore(db)

    # ── 模板加载器 ──────────────────────────────────────────────────
    builtin_dir = str(pathlib.Path(__file__).resolve().parent.parent
                      / "resources" / "prompts")
    sandbox_dir = str(pathlib.Path.home() / ".mercury" / "prompts")
    templates = TemplateLoader(builtin_dir=builtin_dir, sandbox_dir=sandbox_dir)

    # ── LLM 配置 ────────────────────────────────────────────────────
    base_url = settings.value(_PROVIDER_BASE_URL, "")
    model = settings.value(_PROVIDER_MODEL, "")
    api_key = settings.value(_PROVIDER_API_KEY, "")

    has_llm = bool(base_url and model)

    if has_llm:
        primary = ProviderConfig(
            name=model,
            base_url=base_url,
            model=model,
            is_primary=True,
        )
        if api_key:
            primary.set_api_key(api_key)
        router = LLMRouter(primary=primary)
    else:
        # 用一个占位 router——Agent 注册了但调用时会报错
        router = LLMRouter(
            primary=ProviderConfig(
                name="unconfigured",
                base_url="http://localhost:11434/v1",
                model="unconfigured",
            )
        )

    # ── SummaryAgent ─────────────────────────────────────────────────
    summary_agent = SummaryAgent(pipeline, router, templates, agent_store)
    summary_agent.language = str(
        settings.value(_SUMMARY_LANG, _DEFAULTS[_SUMMARY_LANG])
    )
    summary_agent.detail_level = str(
        settings.value(_SUMMARY_DETAIL, _DEFAULTS[_SUMMARY_DETAIL])
    )
    summary_agent.register(runtime)

    # ── TranslationAgent ─────────────────────────────────────────────
    translation_agent = TranslationAgent(pipeline, router, templates, agent_store)
    translation_agent.target_language = str(
        settings.value(_TRANSLATION_LANG, _DEFAULTS[_TRANSLATION_LANG])
    )
    translation_agent.degree = int(
        settings.value(_TRANSLATION_DEGREE, _DEFAULTS[_TRANSLATION_DEGREE])
    )
    translation_agent.register(runtime)

    # ── TagAgent ─────────────────────────────────────────────────────
    tagging_agent = TagAgent(pipeline, router, templates)
    tagging_agent.language = summary_agent.language
    tagging_agent.register(runtime)

    _logger.info(
        "AgentRuntime ready: summary=%s translation=%s tagging=%s llm=%s",
        summary_agent, translation_agent, tagging_agent,
        f"{model}@{base_url}" if has_llm else "unconfigured",
    )

    state.agent_runtime = runtime
    state.has_llm = has_llm
    return runtime, has_llm


class MercuryApp:
    """应用生命周期管理器。"""

    def __init__(self) -> None:
        db_path = _default_data_path()
        state.db = DatabaseManager(db_path)
        self._settings = QSettings()

    def create_main_window(self) -> MainWindow:
        """创建主窗口并注入所有依赖。"""
        if state.db is None:
            raise RuntimeError("Database is not initialized")

        # ── Agent runtime (may be unconfigured) ────────────────────
        runtime, has_llm = _build_agent_runtime(state.db, self._settings)

        # ── MainWindow ─────────────────────────────────────────────
        window = MainWindow(
            feed_store=FeedStore(state.db),
            entry_store=EntryStore(state.db),
            sync_service=SyncService(state.db),
            reader_pipeline=ReaderPipeline(state.db),
            agent_runtime=runtime,
            settings=self._settings,
        )

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(application_stylesheet())

        return window
