# UI Backend Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose backend-ready feed synchronization, feed management, and search scope through the existing compact UI.

**Architecture:** Sidebar and EntryListWidget emit user intentions only. MainWindow calls the already-injected FeedStore, EntryStore, and SyncService, then refreshes visible state. Backend and dependency files remain unchanged.

**Tech Stack:** Python 3.11+, PySide6, qasync, pytest-qt, Ruff.

## Global Constraints

- Modify only UI-owned production files and UI tests.
- Preserve the 30×30 control and 18×18 icon system.
- Every icon-only control keeps a tooltip and accessible name.
- Do not access SQLite or the filesystem directly from a widget.

---

### Task 1: Add regression coverage

**Files:**
- Modify: `tests/test_ui/test_components.py`
- Modify: `tests/test_ui/test_main_window.py`

- [ ] Add tests for sync menu signals, feed rename/delete intentions, search scope, and MainWindow store/service calls.
- [ ] Run focused tests and confirm the old UI lacks the new behavior.

### Task 2: Extend Sidebar intentions

**Files:**
- Modify: `ui/sidebar.py`

- [ ] Add `sync_all_requested`, `feed_rename_requested`, and `feed_delete_requested` signals.
- [ ] Replace direct sync click with a compact current/all menu.
- [ ] Add feed context menu and rename input without calling stores from Sidebar.

### Task 3: Add search scope

**Files:**
- Modify: `ui/entry_list.py`
- Modify: `app/styles.py`

- [ ] Add a narrow current/all scope selector beside the search field.
- [ ] Emit scope changes and update placeholder, accessible text, and heading.

### Task 4: Wire existing backend interfaces

**Files:**
- Modify: `ui/main_window.py`

- [ ] Connect new Sidebar and EntryListWidget signals.
- [ ] Implement sync-all, feed rename, feed deletion, and global search through injected services.
- [ ] Refresh or clear visible state after each operation and report status-bar feedback.

### Task 5: Record blocked follow-up UI

**Files:**
- Create: `UI_BACKEND_ALIGNMENT_ISSUES_2026-07-19.md`

- [ ] Document missing injection/query/file-dialog interfaces and proposed follow-up layout.
- [ ] Run compile, Ruff, focused tests where the Qt runtime permits, and package a clean ZIP.

### Task 6: Fix discoverability, localization, and wide Reader layout

**Files:**
- Modify: `ui/sidebar.py`
- Modify: `ui/entry_list.py`
- Modify: `ui/reader/theme_manager.py`
- Test: `tests/test_ui/test_components.py`
- Test: `tests/test_ui/test_reader_theme.py`

- [ ] Keep feed rename/delete in the feed-list context menu without a top-level delete button.
- [ ] Replace the platform-default search context menu with copy/paste-only localized actions.
- [ ] Center and responsively expand Reader blocks and full-width article media.

### Task 7: Consolidate destructive and batch actions into context menus

**Files:**
- Modify: `ui/entry_list.py`
- Modify: `app/styles.py`
- Test: `tests/test_ui/test_ui_cleanup.py`

- [ ] Remove batch action icon buttons while keeping selection count and exit.
- [ ] Offer batch read/unread/star/delete through the selected-article context menu.
- [ ] Keep feed deletion exclusively in the feed-list context menu.
