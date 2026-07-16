#!/usr/bin/env python3
"""Agent CLI — 命令行验证与集成测试工具。

无需 GUI，直接测试所有 Agent 的端到端流程。

用法:
    # 列出所有文章
    python tools/agent_cli.py list

    # 测试摘要
    python tools/agent_cli.py summary <entry_id> \
        --base-url http://localhost:11434/v1 \
        --model qwen3

    # 测试翻译
    python tools/agent_cli.py translate <entry_id> \
        --base-url https://api.openai.com/v1 \
        --model gpt-4o-mini \
        --api-key sk-xxx

    # 测试标签
    python tools/agent_cli.py tagging <entry_id> \
        --base-url http://localhost:11434/v1 \
        --model qwen3

    # 一次性验证所有 Agent
    python tools/agent_cli.py verify-all <entry_id> \
        --base-url http://localhost:11434/v1 \
        --model qwen3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
import time
from dataclasses import dataclass

# 项目根目录
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))


@dataclass
class _Args:
    command: str
    entry_id: int | None
    base_url: str
    model: str
    api_key: str | None
    fallback_url: str | None
    fallback_model: str | None
    language: str
    detail: str


# QSettings key constants (must match app/app.py)
_KEY_BASE_URL = "llm/base_url"
_KEY_MODEL = "llm/model"
_KEY_API_KEY = "llm/api_key"


def _get_qsettings():
    """Get QSettings for the Mercury app (works outside Qt main loop)."""
    from PySide6.QtCore import QSettings
    return QSettings("Mercury", "Mercury")


def _read_config() -> dict[str, str]:
    """Read LLM config from QSettings, fallback to env vars."""
    settings = _get_qsettings()
    base_url = settings.value(_KEY_BASE_URL, "")
    model = settings.value(_KEY_MODEL, "")
    api_key = settings.value(_KEY_API_KEY, "")

    # Env var fallback
    import os
    if not base_url:
        base_url = os.environ.get("MERCURY_LLM_BASE_URL", "")
    if not model:
        model = os.environ.get("MERCURY_LLM_MODEL", "")
    if not api_key:
        api_key = os.environ.get("MERCURY_LLM_API_KEY", "")

    return {"base_url": base_url, "model": model, "api_key": api_key}


def parse_args() -> _Args:
    p = argparse.ArgumentParser(
        description="Mercury Agent CLI — 命令行验证 Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s list
  %(prog)s configure --base-url http://localhost:11434/v1 --model qwen3
  %(prog)s summary 1
  %(prog)s translate 1
  %(prog)s tagging 1
  %(prog)s verify-all 1
        """,
    )
    p.add_argument(
        "command",
        choices=["list", "configure", "summary", "translate", "tagging", "verify-all"],
        help="要执行的命令",
    )
    p.add_argument("entry_id", nargs="?", type=int, default=None,
                   help="文章 ID")
    p.add_argument("--base-url", default="http://localhost:11434/v1",
                   help="LLM API base URL（默认本地 Ollama）")
    p.add_argument("--model", default="qwen3",
                   help="模型名称")
    p.add_argument("--api-key", default=None,
                   help="API Key（Ollama 不需要）")
    p.add_argument("--fallback-url", default=None,
                   help="回退模型 base URL")
    p.add_argument("--fallback-model", default=None,
                   help="回退模型名称")
    p.add_argument("--language", default="Chinese",
                   help="目标语言（翻译/摘要/标签用）")
    p.add_argument("--detail", default="standard",
                   choices=["brief", "standard", "detailed"],
                   help="摘要详细程度")
    return _Args(**vars(p.parse_args()))


# ── Bootstrap ────────────────────────────────────────────────────────────


def _bootstrap(args: _Args):
    """初始化所有依赖并注册 Agent。"""
    from core.agent.providers import ProviderConfig, LLMRouter
    from core.agent.runtime import AgentRuntime
    from core.agent.summary import SummaryAgent
    from core.agent.tagging import TagAgent
    from core.agent.template_loader import TemplateLoader
    from core.agent.translation import TranslationAgent
    from core.reader.pipeline import ReaderPipeline
    from store.agent_store import AgentStore
    from store.db import DatabaseManager

    # 数据库
    db_path = str(pathlib.Path.home() / ".mercury" / "mercury.db")
    db = DatabaseManager(db_path)

    # LLM 配置：CLI 参数优先 → QSettings → 环境变量
    stored = _read_config()
    base_url = args.base_url if args.base_url != "http://localhost:11434/v1" else None
    base_url = base_url or stored["base_url"]
    model = args.model if args.model != "qwen3" else None
    model = model or stored["model"]
    api_key = args.api_key or stored["api_key"]

    if not base_url or not model:
        print("[WARN]  未配置 LLM。请先运行：")
        print("   python tools/agent_cli.py configure --base-url <URL> --model <NAME>")
        print("   或设置环境变量 MERCURY_LLM_BASE_URL / MERCURY_LLM_MODEL")
        sys.exit(1)

    # LLM 路由
    primary = ProviderConfig(
        name=model,
        base_url=base_url,
        model=model,
        is_primary=True,
    )
    if api_key:
        primary.set_api_key(api_key)

    fallback = None
    if args.fallback_url and args.fallback_model:
        fallback = ProviderConfig(
            name=args.fallback_model,
            base_url=args.fallback_url,
            model=args.fallback_model,
            is_primary=False,
        )

    router = LLMRouter(primary=primary, fallback=fallback)

    # 模板加载器
    builtin_dir = str(
        pathlib.Path(__file__).resolve().parent.parent / "resources" / "prompts"
    )
    sandbox_dir = str(pathlib.Path.home() / ".mercury" / "prompts")
    templates = TemplateLoader(builtin_dir=builtin_dir, sandbox_dir=sandbox_dir)

    # Reader 管线
    pipeline = ReaderPipeline(db)

    # Agent Store
    agent_store = AgentStore(db)

    # 运行时 + 注册
    runtime = AgentRuntime()

    summary_agent = SummaryAgent(pipeline, router, templates, agent_store)
    summary_agent.language = args.language
    summary_agent.detail_level = args.detail
    summary_agent.register(runtime)

    translation_agent = TranslationAgent(pipeline, router, templates, agent_store)
    translation_agent.target_language = args.language
    translation_agent.register(runtime)

    tagging_agent = TagAgent(pipeline, router, templates)
    tagging_agent.language = args.language
    tagging_agent.register(runtime)

    return {
        "runtime": runtime,
        "router": router,
        "templates": templates,
        "pipeline": pipeline,
        "agent_store": agent_store,
        "summary": summary_agent,
        "translation": translation_agent,
        "tagging": tagging_agent,
        "db": db,
    }


# ── Commands ──────────────────────────────────────────────────────────────


def cmd_configure(args: _Args) -> None:
    """保存 LLM 配置到 QSettings。"""
    settings = _get_qsettings()
    settings.setValue(_KEY_BASE_URL, args.base_url)
    settings.setValue(_KEY_MODEL, args.model)
    if args.api_key:
        settings.setValue(_KEY_API_KEY, args.api_key)
    else:
        settings.remove(_KEY_API_KEY)
    settings.sync()

    print("[OK] LLM 配置已保存：")
    print(f"   Base URL: {args.base_url}")
    print(f"   Model:    {args.model}")
    if args.api_key:
        print(f"   API Key:  {'*' * min(len(args.api_key), 8)}…")
    print()
    print("现在可以直接运行测试（无需 --base-url 和 --model）：")
    print(f"  python tools/agent_cli.py verify-all <ID>")


def cmd_list(ctx: dict) -> None:
    """列出数据库中所有文章。"""
    import sqlite3
    conn = ctx["db"].connection
    rows = conn.execute(
        """SELECT e.id, e.title, e.url, e.author, f.title as feed_title
           FROM entries e
           JOIN feeds f ON e.feed_id = f.id
           WHERE e.is_deleted = 0
           ORDER BY e.published_at DESC
           LIMIT 50"""
    ).fetchall()

    if not rows:
        print("[EMPTY] 数据库中没有文章。请先添加订阅源并同步。")
        return

    print(f"{'ID':<6} {'标题':<50} {'来源':<20}")
    print("-" * 80)
    for row in rows:
        eid, title, url, author, feed = row
        title = (title or "无标题")[:48]
        feed = (feed or "未知")[:18]
        print(f"{eid:<6} {title:<50} {feed:<20}")
    print(f"\n共 {len(rows)} 篇文章。用以下命令测试：")
    print(f"  python tools/agent_cli.py summary <ID> --base-url <URL> --model <NAME>")


def cmd_summary(ctx: dict, args: _Args) -> None:
    """测试 SummaryAgent。"""
    runtime = ctx["runtime"]
    entry_id = args.entry_id

    _validate_entry(ctx, entry_id)

    print(f">>> 正在为文章 #{entry_id} 生成摘要…")
    print(f"   Provider: {args.base_url}")
    print(f"   Model: {args.model}")
    print(f"   Language: {args.language}")
    print(f"   Detail: {args.detail}")
    print("-" * 60)

    # 监听信号
    chunks: list[str] = []

    def on_state(event):
        if event.entry_id != entry_id or event.agent_type != "summary":
            return
        icon = {"running": "[...]", "done": "[OK]", "error": "[FAIL]", "cancelled": "[STOP]"}
        print(f"  {icon.get(event.status, '•')} [{event.status}]", end="")
        if event.error:
            print(f" {event.error}")
        else:
            print()

    def on_chunk(event):
        if event.entry_id != entry_id or event.agent_type != "summary":
            return
        chunks.append(event.chunk)

    runtime.signals.state_changed.connect(on_state)
    runtime.signals.chunk_received.connect(on_chunk)

    start = time.time()
    run_id = runtime.submit(entry_id, "summary")

    # 等待完成
    result = asyncio.run(_wait_for_completion(runtime, run_id, timeout=120))

    elapsed = time.time() - start

    if result and result.get("summary"):
        print("-" * 60)
        print(result["summary"])
        print("-" * 60)
        print(f"⏱️  耗时 {elapsed:.1f}s | Provider: {result.get('provider')} | "
              f"Model: {result.get('model')}")
    elif result:
        print(f"[WARN]  结果为空（可能命中空缓存）。完整返回：{json.dumps(result, ensure_ascii=False)}")
    else:
        print("[FAIL] 摘要生成失败（请检查 LLM 连接）")


def cmd_translate(ctx: dict, args: _Args) -> None:
    """测试 TranslationAgent。"""
    runtime = ctx["runtime"]
    entry_id = args.entry_id

    _validate_entry(ctx, entry_id)

    print(f">>> 正在翻译文章 #{entry_id}…")
    print(f"   Provider: {args.base_url}")
    print(f"   Model: {args.model}")
    print(f"   Target: {args.language}")
    print("-" * 60)

    start = time.time()
    run_id = runtime.submit(entry_id, "translation")

    result = asyncio.run(_wait_for_completion(runtime, run_id, timeout=300))
    elapsed = time.time() - start

    if result:
        print(f"[OK] 翻译完成")
        print(f"   段落总数: {result.get('paragraphs_total', 0)}")
        print(f"   成功: {result.get('paragraphs_success', 0)}")
        print(f"   失败: {result.get('paragraphs_failed', 0)}")
        print(f"   ⏱️  耗时 {elapsed:.1f}s")
        html = result.get("html", "")
        if html:
            # 保存双语 HTML 到文件
            out_path = pathlib.Path.home() / ".mercury" / f"translation_{entry_id}.html"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(html, encoding="utf-8")
            print(f"   [FILE] 双语 HTML 已保存到: {out_path}")
    else:
        print("[FAIL] 翻译失败（请检查 LLM 连接）")


def cmd_tagging(ctx: dict, args: _Args) -> None:
    """测试 TagAgent。"""
    runtime = ctx["runtime"]
    entry_id = args.entry_id

    _validate_entry(ctx, entry_id)

    print(f">>>  正在为文章 #{entry_id} 生成标签…")
    print(f"   Provider: {args.base_url}")
    print(f"   Model: {args.model}")
    print("-" * 60)

    start = time.time()
    run_id = runtime.submit(entry_id, "tagging")

    result = asyncio.run(_wait_for_completion(runtime, run_id, timeout=120))
    elapsed = time.time() - start

    if result:
        tags = result.get("tags", [])
        raw = result.get("raw_tags", [])
        existing = result.get("existing_tags", [])
        print(f"[OK] 标签生成完成")
        print(f"   已有标签: {existing}")
        print(f"   原始建议: {raw}")
        print(f"   最终标签: {tags}")
        print(f"   ⏱️  耗时 {elapsed:.1f}s")
    else:
        print("[FAIL] 标签生成失败（请检查 LLM 连接）")


def cmd_verify_all(ctx: dict, args: _Args) -> None:
    """依次运行所有 Agent 并报告结果。"""
    print("=" * 60)
    print(">>> Mercury Agent 集成验证")
    print(f"   Provider: {args.base_url}")
    print(f"   Model: {args.model}")
    print(f"   Entry ID: {args.entry_id}")
    print("=" * 60)

    results: dict[str, bool] = {}

    # Test connection first
    router = ctx["router"]
    primary = router._primary
    print("\n>>> 测试 LLM 连接…")
    ok, models, err = asyncio.run(router.test_connection(primary))
    if ok:
        print(f"   [OK] 连接成功！可用模型: {len(models)}")
    else:
        print(f"   [FAIL] 连接失败: {err}")
        print("   请检查 --base-url 和 --model 参数")
        return

    # Summary
    print("\n" + "-" * 40)
    print("1/3 — 摘要测试")
    try:
        cmd_summary(ctx, args)
        results["summary"] = True
    except Exception as e:
        print(f"   [FAIL] 异常: {e}")
        results["summary"] = False

    # Translation
    print("\n" + "-" * 40)
    print("2/3 — 翻译测试")
    try:
        cmd_translate(ctx, args)
        results["translation"] = True
    except Exception as e:
        print(f"   [FAIL] 异常: {e}")
        results["translation"] = False

    # Tagging
    print("\n" + "-" * 40)
    print("3/3 — 标签测试")
    try:
        cmd_tagging(ctx, args)
        results["tagging"] = True
    except Exception as e:
        print(f"   [FAIL] 异常: {e}")
        results["tagging"] = False

    # Report
    print("\n" + "=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for agent, ok in results.items():
        print(f"  {'[OK]' if ok else '[FAIL]'} {agent}")
    print(f"\n--- 通过: {passed}/{total}")
    if passed == total:
        print("*** 所有 Agent 验证通过！")
    else:
        print("[WARN]  部分 Agent 失败，请检查 LLM 配置")


# ── Helpers ───────────────────────────────────────────────────────────────


def _validate_entry(ctx: dict, entry_id: int | None) -> None:
    if entry_id is None:
        print("[FAIL] 请指定文章 ID（先用 `list` 查看可用文章）")
        sys.exit(1)
    from store.entry_store import EntryStore
    entry = asyncio.run(EntryStore(ctx["db"]).get(entry_id))
    if entry is None:
        print(f"[FAIL] 文章 #{entry_id} 不存在")
        sys.exit(1)
    print(f"   --- {entry.title or '无标题'}")


async def _wait_for_completion(
    runtime, run_id: str, timeout: float = 120
) -> dict | None:
    """等待 Agent 任务完成，返回 result dict 或 None。"""
    import asyncio

    done_event = asyncio.Event()
    result: dict | None = None
    error: str | None = None

    def on_state(event):
        nonlocal result, error
        if event.run_id != run_id:
            return
        if event.status == "done" and event.result_json:
            try:
                result = json.loads(event.result_json)
            except json.JSONDecodeError:
                result = {"raw": event.result_json}
            done_event.set()
        elif event.status in ("error", "cancelled"):
            error = event.error or event.status
            done_event.set()

    runtime.signals.state_changed.connect(on_state)

    try:
        await asyncio.wait_for(done_event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        print(f"[TIMEOUT] 超时（{timeout}s），任务仍在运行")
        runtime.cancel(run_id)
        return None

    if error:
        print(f"[FAIL] {error}")
        return None

    return result


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> None:
    args = parse_args()

    if args.command == "configure":
        cmd_configure(args)
        return

    if args.command == "list":
        ctx = {"db": _bootstrap(args)["db"]}
        cmd_list(ctx)
        return

    if args.entry_id is None:
        print("[FAIL] 请指定文章 ID")
        sys.exit(1)

    ctx = _bootstrap(args)

    commands = {
        "summary": cmd_summary,
        "translate": cmd_translate,
        "tagging": cmd_tagging,
        "verify-all": cmd_verify_all,
    }

    commands[args.command](ctx, args)


if __name__ == "__main__":
    main()
