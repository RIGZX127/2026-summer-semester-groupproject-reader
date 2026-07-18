# Phase 3 UI Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the polished Phase 3 UI behavior into the newer main project without overwriting its backend or build configuration.

**Architecture:** Treat the first archive as the source of truth for Core, Store, application wiring, dependencies, and documentation. Port only UI-owned modules and `app/styles.py`, then adapt `MainWindow` batch actions to the current `EntryStore` interface. Preserve all main-only features and validate with focused UI tests plus the complete test suite.

**Tech Stack:** Python 3.11+, PySide6 6.5+, qasync, pytest, pytest-qt, Ruff, uv.

## Global Constraints

- Do not overwrite files under `core/`, `store/`, `tools/`, or project dependency files from the UI archive.
- Keep UI updates on the Qt main thread and preserve Signal/slot interfaces.
- All icon-only controls require tooltips and accessible names.
- Package no virtual environments, caches, databases, or temporary files.

---

### Task 1: Establish the Phase 3 UI regression tests

**Files:**
- Create: `tests/test_ui/test_ui_cleanup.py`
- Modify: existing `tests/test_ui/test_components.py`, `test_main_window.py`, `test_reader_toolbar.py`, `test_reader_view_phase2.py`, and `test_styles.py`

**Interfaces:**
- Consumes: current `SidebarWidget`, `EntryListWidget`, `ReaderToolbar`, `ReaderView`, `SummaryPanel`, and `MainWindow` public widget properties.
- Produces: executable expectations for batch mode, icon geometry, hover text, summary resizing, and header alignment.

- [ ] **Step 1: Copy the UI archive's focused tests into the main project**

```text
Copy only tests under tests/test_ui whose assertions changed for the cleanup release.
```

- [ ] **Step 2: Run the focused tests and confirm RED**

```bash
QT_QPA_PLATFORM=offscreen uv run pytest tests/test_ui/test_ui_cleanup.py -q
```

Expected: failures because the main project lacks `ui.tooltips`, batch controls, or compact popup controls.

- [ ] **Step 3: Keep failures limited to missing UI behavior**

```bash
QT_QPA_PLATFORM=offscreen uv run pytest tests/test_ui/test_ui_cleanup.py -q --tb=short
```

Expected: no syntax or test-collection errors caused by the test transfer.

### Task 2: Port compact controls, tooltips, and styling

**Files:**
- Create: `ui/tooltips.py`
- Modify: `ui/icons.py`, `ui/sidebar.py`, `ui/reader/reader_toolbar.py`, `app/styles.py`
- Test: `tests/test_ui/test_ui_cleanup.py`, `tests/test_ui/test_reader_toolbar.py`, `tests/test_ui/test_styles.py`

**Interfaces:**
- Consumes: `make_icon(name: str, ...) -> QIcon` and existing toolbar signals.
- Produces: 30×30 controls with 18×18 artwork, `install_hover_tooltip(widget, text)`, and popup menus for font/theme/width selections.

- [ ] **Step 1: Add the shared tooltip helper and expanded Qt-drawn icon set**

```python
def install_hover_tooltip(widget: QWidget, text: str) -> None:
    widget.setToolTip(text)
    widget.setAccessibleName(text)
    widget.installEventFilter(_tooltip_filter)
```

- [ ] **Step 2: Port the compact Sidebar and Reader controls**

```text
Retain every existing signal name and replace only control construction, popup selection, geometry, and descriptive metadata.
```

- [ ] **Step 3: Merge only the UI stylesheet additions**

```text
Preserve main-project selectors and add the cleanup release's compact-control, tooltip, batch-bar, and summary selectors.
```

- [ ] **Step 4: Run focused tests and confirm GREEN**

```bash
QT_QPA_PLATFORM=offscreen uv run pytest tests/test_ui/test_ui_cleanup.py tests/test_ui/test_reader_toolbar.py tests/test_ui/test_styles.py -q
```

Expected: all selected tests pass.

### Task 3: Port article batch management and window wiring

**Files:**
- Modify: `ui/entry_list.py`, `ui/main_window.py`
- Test: `tests/test_ui/test_components.py`, `tests/test_ui/test_main_window.py`, `tests/test_ui/test_ui_cleanup.py`

**Interfaces:**
- Consumes: `EntryStore.mark_read(int)`, `mark_unread(int)`, `toggle_star(int)`, and `soft_delete(int)`.
- Produces: `batch_mark_read_requested(list[int], bool)`, `batch_star_requested(list[int])`, and `batch_delete_requested(list[int])` signals.

- [ ] **Step 1: Port list multi-selection and the compact batch action bar**

```python
batch_mark_read_requested = Signal(list, bool)
batch_star_requested = Signal(list)
batch_delete_requested = Signal(list)
```

- [ ] **Step 2: Wire batch signals to current MainWindow store methods**

```python
@asyncSlot(list, bool)
async def _batch_mark_read_slot(self, entry_ids: list[int], read: bool) -> None:
    await self.batch_mark_entries_read(entry_ids, read)
```

- [ ] **Step 3: Run batch and window tests**

```bash
QT_QPA_PLATFORM=offscreen uv run pytest tests/test_ui/test_components.py tests/test_ui/test_main_window.py tests/test_ui/test_ui_cleanup.py -q
```

Expected: all selected tests pass.

### Task 4: Port summary resizing and Reader layout alignment

**Files:**
- Modify: `ui/reader/summary_panel.py`, `ui/reader/reader_view.py`
- Test: `tests/test_ui/test_reader_view_phase2.py`, `tests/test_ui/test_ui_cleanup.py`

**Interfaces:**
- Consumes: existing `SummaryPanel.set_expanded(bool)` and Reader splitter.
- Produces: draggable summary height that opens above 60 px and collapses at 50 px, with aligned 6 px top offsets.

- [ ] **Step 1: Port collapsible summary sizing behavior**

```text
Keep the 44 px collapsed header, allow unrestricted expansion, and synchronize expanded state from splitter movement.
```

- [ ] **Step 2: Port Reader top alignment and translation-control sizing**

```text
Apply the cleanup release's layout margins and compact translation control dimensions without changing Agent APIs.
```

- [ ] **Step 3: Run Reader tests**

```bash
QT_QPA_PLATFORM=offscreen uv run pytest tests/test_ui/test_reader_view_phase2.py tests/test_ui/test_ui_cleanup.py -q
```

Expected: all selected tests pass.

### Task 5: Verify, document, and package

**Files:**
- Create: `UI_MERGE_REPORT_2026-07-19.md`
- Create: final ZIP beside the working project.

**Interfaces:**
- Consumes: the integrated project tree.
- Produces: a clean Windows-runnable archive and reproducible run instructions.

- [ ] **Step 1: Compile and lint changed production files**

```bash
uv run python -m compileall app ui
uv run ruff check app/styles.py ui
```

Expected: both commands exit 0.

- [ ] **Step 2: Run the complete test suite**

```bash
QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox uv run pytest -q
```

Expected: all tests pass, or any environment/pre-existing failure is reproduced and documented separately.

- [ ] **Step 3: Run an offscreen startup smoke test**

```bash
QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox uv run python -c "from PySide6.QtWidgets import QApplication; from app.app import MercuryApp; q=QApplication.instance() or QApplication([]); app=MercuryApp(); w=app.create_main_window(); print(type(w).__name__)"
```

Expected: `MainWindow` and exit code 0.

- [ ] **Step 4: Package without generated files**

```text
Archive the project while excluding .venv, __pycache__, .pytest_cache, .ruff_cache, *.pyc, *.db, and temporary test output.
```
