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

from app.paths import ensure_user_data_dir
from app.state import state
from app.styles import application_stylesheet
from core.digest.controller import DigestController
from core.feed.opml_controller import OPMLController
from core.feed.sync import SyncService
from core.reader.pipeline import ReaderPipeline
from store.collection_store import CollectionStore
from store.db import DatabaseManager
from store.entry_store import EntryStore
from store.feed_store import FeedStore
from store.note_store import NoteStore
from store.tag_store import TagStore
from ui.main_window import MainWindow

_logger = logging.getLogger(__name__)

# ── QSettings keys for provider configuration ───────────────────────────
_PROVIDER_BASE_URL = "llm/base_url"
_PROVIDER_MODEL = "llm/model"
_PROVIDER_API_KEY = "llm/api_key"
_AUTO_SUMMARY = "agent/auto_summary"  # bool: 切换文章后自动生成摘要
_SUMMARY_LANG = "agent/summary_language"  # 摘要语言
_SUMMARY_DETAIL = "agent/summary_detail"  # brief | standard | detailed
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


async def _get_entry_tag_names(tag_store, entry_id: int) -> list[str]:
    """Async helper：获取指定文章的标签名称列表，供 TagAgent 依赖注入。"""
    tags = await tag_store.get_entry_tags(entry_id)
    return [t.tag_name for t in tags]


def _default_data_path() -> str:
    """返回平台默认数据库路径。"""
    return str(ensure_user_data_dir() / "mercury.db")


def _build_agent_runtime(
    db: DatabaseManager,
    settings: QSettings,
) -> tuple:
    """构建 AgentRuntime 并注册所有 Agent。

    Returns:
        (AgentRuntime, has_llm_configured: bool)
        若 LLM 未配置，AgentRuntime 仍然可用，但 submit() 会返回错误。
    """
    from core.agent.providers import LLMRouter, ProviderConfig
    from core.agent.runtime import AgentRuntime
    from core.agent.summary import SummaryAgent
    from core.agent.tagging import TagAgent
    from core.agent.template_loader import TemplateLoader
    from core.agent.translation import TranslationAgent
    from core.reader.pipeline import ReaderPipeline
    from core.tags.normalizer import TagNormalizer
    from store.agent_store import AgentStore

    runtime = AgentRuntime()
    pipeline = ReaderPipeline(db)
    agent_store = AgentStore(db)
    tag_store = TagStore(db)
    normalizer = TagNormalizer()

    # ── 模板加载器 ──────────────────────────────────────────────────
    builtin_dir = str(pathlib.Path(__file__).resolve().parent.parent / "resources" / "prompts")
    sandbox_dir = str(ensure_user_data_dir() / "prompts")
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
    summary_agent.language = str(settings.value(_SUMMARY_LANG, _DEFAULTS[_SUMMARY_LANG]))
    summary_agent.detail_level = str(settings.value(_SUMMARY_DETAIL, _DEFAULTS[_SUMMARY_DETAIL]))
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
    tagging_agent.set_tag_dependencies(
        normalizer=normalizer.normalize,
        existing_tags_fn=lambda eid: _get_entry_tag_names(tag_store, eid),
    )

    _logger.info(
        "AgentRuntime ready: summary=%s translation=%s tagging=%s llm=%s",
        summary_agent,
        translation_agent,
        tagging_agent,
        f"{model}@{base_url}" if has_llm else "unconfigured",
    )

    state.agent_runtime = runtime
    state.has_llm = has_llm
    return runtime, has_llm


def reconfigure_agent_runtime(settings: QSettings) -> bool:
    """根据当前 QSettings 热重配 Agent 的 LLM router。

    当用户在 AI 工作台中保存 LLM 配置后调用，无需重启应用即可让
    摘要/翻译/标签 Agent 使用新的 LLM 后端。

    Returns:
        True 如果 LLM 配置有效且 Agent 已重建，False 如果配置不完整。
    """
    if state.db is None:
        return False

    from core.agent.providers import LLMRouter, ProviderConfig
    from core.agent.runtime import AgentRuntime
    from core.agent.summary import SummaryAgent
    from core.agent.tagging import TagAgent
    from core.agent.template_loader import TemplateLoader
    from core.agent.translation import TranslationAgent
    from core.reader.pipeline import ReaderPipeline
    from core.tags.normalizer import TagNormalizer
    from store.agent_store import AgentStore
    from store.tag_store import TagStore

    base_url = settings.value(_PROVIDER_BASE_URL, "")
    model = settings.value(_PROVIDER_MODEL, "")
    api_key = settings.value(_PROVIDER_API_KEY, "")

    if not (base_url and model):
        state.has_llm = False
        _logger.warning("LLM reconfigure skipped: base_url or model missing")
        return False

    # ── 构建新 router ─────────────────────────────────────────────────
    primary = ProviderConfig(
        name=model,
        base_url=base_url,
        model=model,
        is_primary=True,
    )
    if api_key:
        primary.set_api_key(api_key)
    router = LLMRouter(primary=primary)

    # ── 模板加载器 ────────────────────────────────────────────────────
    builtin_dir = str(pathlib.Path(__file__).resolve().parent.parent / "resources" / "prompts")
    sandbox_dir = str(ensure_user_data_dir() / "prompts")
    templates = TemplateLoader(builtin_dir=builtin_dir, sandbox_dir=sandbox_dir)

    pipeline = ReaderPipeline(state.db)
    agent_store = AgentStore(state.db)
    tag_store = TagStore(state.db)
    normalizer = TagNormalizer()
    runtime = AgentRuntime()

    # ── 重建并重新注册 Agent（同名 agent_type 覆盖旧 handler）───────
    summary_agent = SummaryAgent(pipeline, router, templates, agent_store)
    summary_agent.language = str(settings.value(_SUMMARY_LANG, _DEFAULTS[_SUMMARY_LANG]))
    summary_agent.detail_level = str(settings.value(_SUMMARY_DETAIL, _DEFAULTS[_SUMMARY_DETAIL]))
    summary_agent.register(runtime)

    translation_agent = TranslationAgent(pipeline, router, templates, agent_store)
    translation_agent.target_language = str(
        settings.value(_TRANSLATION_LANG, _DEFAULTS[_TRANSLATION_LANG])
    )
    translation_agent.degree = int(
        settings.value(_TRANSLATION_DEGREE, _DEFAULTS[_TRANSLATION_DEGREE])
    )
    translation_agent.register(runtime)

    tagging_agent = TagAgent(pipeline, router, templates)
    tagging_agent.language = summary_agent.language
    tagging_agent.register(runtime)
    tagging_agent.set_tag_dependencies(
        normalizer=normalizer.normalize,
        existing_tags_fn=lambda eid: _get_entry_tag_names(tag_store, eid),
    )

    state.has_llm = True
    _logger.info(
        "AgentRuntime reconfigured: summary=%s translation=%s tagging=%s llm=%s@%s",
        summary_agent,
        translation_agent,
        tagging_agent,
        model,
        base_url,
    )
    return True


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
            tag_store=TagStore(state.db),
            note_store=NoteStore(state.db),
            digest_controller=DigestController(state.db),
            opml_controller=OPMLController(state.db),
            collection_store=CollectionStore(state.db),
        )

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(application_stylesheet())

        return window
