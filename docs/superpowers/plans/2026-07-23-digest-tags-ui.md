# Digest and Tags UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the existing Markdown/Digest export and tag backends through the article UI.

**Architecture:** `EntryListWidget` emits user intent without accessing stores. `MainWindow` coordinates dialogs and injected controllers, while `ReaderView` renders tag state.

**Tech Stack:** Python 3.11+, PySide6, pytest-qt, qasync

## Global Constraints

- Modify UI and wiring only; do not change database schema or backend behavior.
- All visible controls use translated Chinese strings and accessible labels.
- AI work must go through the shared `AgentRuntime`.
- Tests must not access the network, real user database, or LLM.

---

### Task 1: Export actions

**Files:**
- Modify: `ui/entry_list.py`
- Modify: `ui/main_window.py`
- Test: `tests/test_ui/test_digest_tags_ui.py`

**Interfaces:**
- Produces: `export_markdown_requested: Signal(int)` and `batch_export_digest_requested: Signal(list)`
- Consumes: `DigestController.export_single()` and `DigestController.export_multi()`

- [ ] Write failing signal and controller-call tests.
- [ ] Run the focused tests and confirm the missing signals fail.
- [ ] Add the single-entry and batch menu actions.
- [ ] Add folder selection, controller calls, and status feedback.
- [ ] Re-run focused tests.

### Task 2: Tag actions and Reader display

**Files:**
- Modify: `ui/entry_list.py`
- Modify: `ui/main_window.py`
- Modify: `ui/reader/reader_view.py`
- Test: `tests/test_ui/test_digest_tags_ui.py`

**Interfaces:**
- Produces: `manage_tags_requested: Signal(int)`, `generate_tags_requested: Signal(int)`, and `ReaderView.set_tags(list[str])`
- Consumes: `TagStore.get_entry_tags()`, `TagStore.create()`, `TagStore.set_entry_tags()`, and `AgentRuntime.submit(entry_id, "tagging")`

- [ ] Write failing tests for tag signals, rendering, persistence, and AI submission.
- [ ] Run focused tests and confirm failure is caused by missing UI behavior.
- [ ] Implement tag label rendering and manual tag replacement.
- [ ] Submit AI tagging through the runtime and validate matching completion events.
- [ ] Re-run focused tests.

### Task 3: Verification and package

**Files:**
- Modify: `AGENTS.md`

- [ ] Run focused UI tests.
- [ ] Run Ruff on changed Python files.
- [ ] Run Python compilation on changed Python files.
- [ ] Update the project status milestone.
- [ ] Create a clean ZIP excluding environments, caches, and local databases.
