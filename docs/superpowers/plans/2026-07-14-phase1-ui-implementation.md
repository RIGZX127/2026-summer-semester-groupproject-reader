# Mercury Phase 1 UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the role C Phase 1 PySide6 UI: a comfortable three-column RSS reader shell with feed addition, synchronization, article selection, explicit page states, persistence, and tests.

**Architecture:** `MercuryApp` creates the existing stable `FeedStore`, `EntryStore`, and `SyncService` dependencies and injects them into `ui.main_window.MainWindow`. The main window coordinates async use of those interfaces while `Sidebar`, `EntryListWidget`, `ReaderView`, and `AddFeedDialog` remain focused presentation components. Styling is centralized in `app/styles.py`; request IDs guard asynchronous article-list refreshes.

**Tech Stack:** Python 3.11+, PySide6 6.5+, Qt Widgets, QWebEngineView, qasync, QSettings, pytest, pytest-qt, ruff.

## Global Constraints

- Keep the exact Phase 1 filenames from `PLAN.md`; do not rename or relocate UI responsibilities.
- Use `QListWidget` for Phase 1 feed and article lists.
- User-visible source strings are Chinese and must use `self.tr()` or `QCoreApplication.translate()`.
- Custom signals use `PySide6.QtCore.Signal`, never `pyqtSignal`.
- UI code never executes SQL, HTTP, feed parsing, or other blocking I/O.
- Use only the locked APIs in `INTERFACE.md`: `FeedStore`, `EntryStore`, `SyncService`, and `AppState`.
- Async UI slots use `qasync.asyncSlot`; Qt widgets are updated only on the main thread.
- Operations exceeding 200 ms show non-blocking feedback; existing content is retained on errors.
- All icon-only controls require a tooltip and accessible name; state must not be communicated by color alone.
- Window geometry and splitter sizes persist through `QSettings`.
- Do not implement Phase 2 Reader pipeline, AI, tags, notes, settings, or OPML UI in this plan.

## File Structure

| Path | Change | Responsibility |
|---|---|---|
| `app/styles.py` | Create | Design tokens and the single application QSS string |
| `ui/sidebar.py` | Create | Feed list, unread badges, navigation and user-intent signals |
| `ui/entry_list.py` | Create | Article list and explicit page states |
| `ui/reader/reader_view.py` | Create | QWebEngineView wrapper and safe Phase 1 empty/summary rendering |
| `ui/dialogs/add_feed_dialog.py` | Create | URL validation, submitting state and inline errors |
| `ui/main_window.py` | Create | Three-column layout, dependency orchestration, async flows and QSettings |
| `app/app.py` | Modify | Remove placeholder window, construct locked dependencies and return UI MainWindow |
| `tests/test_ui/test_styles.py` | Create | Token and QSS smoke tests |
| `tests/test_ui/test_components.py` | Create | Sidebar, entry list and reader state tests |
| `tests/test_ui/test_add_feed_dialog.py` | Create | Validation and dialog-state tests |
| `tests/test_ui/test_main_window.py` | Create | Layout, async flow, stale request and persistence tests |

---

### Task 1: Centralized Visual System

**Files:**
- Create: `app/styles.py`
- Create: `tests/test_ui/__init__.py`
- Create: `tests/test_ui/test_styles.py`

**Interfaces:**
- Produces: `COLORS: dict[str, str]`, `SPACING: dict[str, int]`, `RADIUS: dict[str, int]`, `application_stylesheet() -> str`.
- Consumes: none.

- [ ] **Step 1: Write the failing style contract test**

```python
# tests/test_ui/test_styles.py
from app.styles import COLORS, RADIUS, SPACING, application_stylesheet


def test_design_tokens_match_modern_focus_direction() -> None:
    assert COLORS["sidebar"] == "#192838"
    assert COLORS["accent"] == "#4B7F92"
    assert COLORS["surface"] == "#FCFBF8"
    assert SPACING["unit"] == 8
    assert RADIUS["control"] == 7


def test_application_stylesheet_contains_accessible_states() -> None:
    qss = application_stylesheet()
    assert "QWidget#Sidebar" in qss
    assert "QListWidget::item:selected" in qss
    assert "QPushButton:focus" in qss
    assert "QLineEdit[validationError=\"true\"]" in qss
```

- [ ] **Step 2: Run the test and verify the missing module failure**

Run: `pytest tests/test_ui/test_styles.py -v`

Expected: collection fails with `ModuleNotFoundError: No module named 'app.styles'`.

- [ ] **Step 3: Implement tokens and the centralized QSS**

```python
# app/styles.py
from __future__ import annotations

COLORS = {
    "sidebar": "#192838",
    "sidebar_hover": "#24394B",
    "sidebar_selected": "#2D5267",
    "surface": "#FCFBF8",
    "surface_alt": "#F3F5F6",
    "border": "#DDE3E8",
    "text": "#1E2A34",
    "muted": "#687986",
    "accent": "#4B7F92",
    "accent_soft": "#E8F1F4",
    "error": "#B44A4A",
    "warning": "#A36A25",
    "focus": "#76A9BD",
}
SPACING = {"unit": 8, "compact": 6, "normal": 12, "section": 20, "large": 28}
RADIUS = {"control": 7, "panel": 8}


def application_stylesheet() -> str:
    return f"""
    QWidget {{ color: {COLORS['text']}; font-size: 14px; }}
    QMainWindow, QWidget#ContentSurface {{ background: {COLORS['surface']}; }}
    QWidget#Sidebar {{ background: {COLORS['sidebar']}; color: #EEF3F6; }}
    QListWidget {{ border: 0; outline: 0; background: transparent; }}
    QListWidget::item {{ padding: 10px 12px; border-radius: {RADIUS['control']}px; }}
    QListWidget::item:selected {{ background: {COLORS['accent_soft']}; color: {COLORS['text']}; }}
    QPushButton {{ min-height: 34px; padding: 0 12px; border-radius: {RADIUS['control']}px; }}
    QPushButton:focus, QLineEdit:focus, QListWidget:focus {{ border: 2px solid {COLORS['focus']}; }}
    QLineEdit[validationError=\"true\"] {{ border: 1px solid {COLORS['error']}; }}
    QLabel#MutedLabel {{ color: {COLORS['muted']}; }}
    QLabel#ErrorLabel {{ color: {COLORS['error']}; }}
    """
```

- [ ] **Step 4: Run the style tests and lint**

Run: `pytest tests/test_ui/test_styles.py -v && ruff check app/styles.py tests/test_ui/test_styles.py`

Expected: two tests pass and ruff reports no errors.

- [ ] **Step 5: Commit the visual system**

```bash
git add app/styles.py tests/test_ui/__init__.py tests/test_ui/test_styles.py
git commit -m "feat(ui): add centralized visual system"
```

### Task 2: Sidebar Presentation Component

**Files:**
- Create: `ui/sidebar.py`
- Create: `tests/test_ui/test_components.py`

**Interfaces:**
- Consumes: immutable `store.feed_store.FeedRow` values.
- Produces: `Sidebar.feed_selected = Signal(int)`, `add_feed_requested = Signal()`, `sync_requested = Signal(int)`; methods `set_feeds(list[tuple[FeedRow, int]])`, `set_syncing(int, bool)`, `set_feed_error(int, str | None)`.

- [ ] **Step 1: Write failing sidebar behavior tests**

```python
# tests/test_ui/test_components.py
from store.feed_store import FeedRow
from ui.sidebar import Sidebar


def _feed(feed_id: int = 1, title: str = "A very long feed title") -> FeedRow:
    return FeedRow(feed_id, "https://example.com/rss", title, "", None, "now", "now")


def test_sidebar_emits_feed_id_and_exposes_full_title(qtbot) -> None:
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    sidebar.set_feeds([(_feed(), 12)])
    item = sidebar.feed_list.item(0)
    assert item.toolTip() == "A very long feed title"
    with qtbot.waitSignal(sidebar.feed_selected, timeout=500) as signal:
        sidebar.feed_list.setCurrentRow(0)
    assert signal.args == [1]


def test_sidebar_sync_state_has_text_not_only_color(qtbot) -> None:
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    sidebar.set_feeds([(_feed(), 12)])
    sidebar.set_syncing(1, True)
    assert "同步中" in sidebar.feed_list.item(0).text()
```

- [ ] **Step 2: Run tests and verify import failure**

Run: `pytest tests/test_ui/test_components.py -v`

Expected: collection fails because `ui.sidebar` does not exist.

- [ ] **Step 3: Implement Sidebar with QListWidget data roles**

Implement `Sidebar(QWidget)` with object name `Sidebar`, a product header, an accessible “添加订阅” button, quick-view rows, `feed_list: QListWidget`, and an accessible sync button. Store each `feed_id` in `Qt.ItemDataRole.UserRole`; store the clean title and unread count in higher custom roles so `set_syncing()` and `set_feed_error()` rebuild display text without mutating `FeedRow`. Connect `currentItemChanged` to a private slot that emits only valid positive feed IDs.

```python
class Sidebar(QWidget):
    feed_selected = Signal(int)
    add_feed_requested = Signal()
    sync_requested = Signal(int)

    def set_feeds(self, rows: list[tuple[FeedRow, int]]) -> None: ...
    def set_syncing(self, feed_id: int, syncing: bool) -> None: ...
    def set_feed_error(self, feed_id: int, message: str | None) -> None: ...
```

Every icon-only control must call both `setToolTip(self.tr("…"))` and `setAccessibleName(self.tr("…"))`.

- [ ] **Step 4: Run component tests**

Run: `pytest tests/test_ui/test_components.py -v`

Expected: both sidebar tests pass.

- [ ] **Step 5: Commit Sidebar**

```bash
git add ui/sidebar.py tests/test_ui/test_components.py
git commit -m "feat(ui): add feed sidebar component"
```

### Task 3: Article List and Reader State Components

**Files:**
- Create: `ui/entry_list.py`
- Create: `ui/reader/reader_view.py`
- Modify: `tests/test_ui/test_components.py`

**Interfaces:**
- Consumes: `list[EntryListItem]` and `EntryRow` from the locked Store API.
- Produces: `EntryListWidget.entry_selected = Signal(int)`, `retry_requested = Signal()`, `set_state(state: str, message: str = "")`, `set_entries(list[EntryListItem])`; `ReaderView.show_empty()`, `show_loading()`, `show_entry(EntryRow)`, `show_error(str)`.

- [ ] **Step 1: Add failing state and selection tests**

Add tests that instantiate `EntryListWidget`, verify `set_state("loading")` shows the translated loading label without clearing existing list items, verify `set_entries()` stores entry IDs in `UserRole`, and verify selection emits the integer ID. Add `ReaderView` tests confirming the initial page contains an instructional empty-state phrase and `show_entry()` safely renders a title containing `<script>` as text rather than executable markup.

- [ ] **Step 2: Run tests and verify missing modules**

Run: `pytest tests/test_ui/test_components.py -v`

Expected: import failures for `ui.entry_list` and `ui.reader.reader_view`.

- [ ] **Step 3: Implement EntryListWidget**

Use a `QStackedWidget` with named pages for `empty`, `content`, `error`, `offline`, and `disabled`; place a non-modal loading banner above the stack so old content stays visible during refresh. Validate state names and raise `ValueError` for unknown states. Render title, source/author, time, unread symbol, and star symbol in list text; keep the full title in Tooltip.

```python
class EntryListWidget(QWidget):
    entry_selected = Signal(int)
    retry_requested = Signal()
    VALID_STATES = frozenset({"empty", "loading", "content", "error", "offline", "disabled"})

    def set_state(self, state: str, message: str = "") -> None: ...
    def set_entries(self, entries: list[EntryListItem]) -> None: ...
```

- [ ] **Step 4: Implement ReaderView**

Wrap `QWebEngineView` inside a `QStackedWidget`. Disable JavaScript on its `QWebEngineSettings`, keep local-content access disabled, and build Phase 1 HTML with `html.escape()` for every value originating in `EntryRow`. `show_loading()` must use a native placeholder page and must not call the network.

```python
class ReaderView(QWidget):
    retry_requested = Signal()

    def show_empty(self) -> None: ...
    def show_loading(self) -> None: ...
    def show_entry(self, entry: EntryRow) -> None: ...
    def show_error(self, message: str) -> None: ...
```

- [ ] **Step 5: Run state component tests under headless Qt**

Run: `QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox pytest tests/test_ui/test_components.py -v`

Expected: all component tests pass; no network access occurs.

- [ ] **Step 6: Commit article and Reader components**

```bash
git add ui/entry_list.py ui/reader/reader_view.py tests/test_ui/test_components.py
git commit -m "feat(ui): add article and reader state views"
```

### Task 4: Add Feed Dialog

**Files:**
- Create: `ui/dialogs/add_feed_dialog.py`
- Create: `tests/test_ui/test_add_feed_dialog.py`

**Interfaces:**
- Produces: `AddFeedDialog.url_submitted = Signal(str)`; `url() -> str`, `set_submitting(bool)`, `show_error(str)`, `clear_error()`.
- Consumes: no Store/Core modules.

- [ ] **Step 1: Write validation and state tests**

```python
from ui.dialogs.add_feed_dialog import AddFeedDialog


def test_invalid_url_is_rejected_inline(qtbot) -> None:
    dialog = AddFeedDialog()
    qtbot.addWidget(dialog)
    dialog.url_edit.setText("not-a-url")
    dialog.submit_button.click()
    assert dialog.error_label.isVisible()
    assert dialog.url_edit.property("validationError") is True


def test_valid_url_is_normalized_and_emitted(qtbot) -> None:
    dialog = AddFeedDialog()
    qtbot.addWidget(dialog)
    dialog.url_edit.setText(" example.com/feed.xml ")
    with qtbot.waitSignal(dialog.url_submitted, timeout=500) as signal:
        dialog.submit_button.click()
    assert signal.args == ["https://example.com/feed.xml"]
```

- [ ] **Step 2: Run tests and verify missing module**

Run: `pytest tests/test_ui/test_add_feed_dialog.py -v`

Expected: collection fails because the dialog module does not exist.

- [ ] **Step 3: Implement the dialog without business I/O**

Validate with `urllib.parse.urlparse`: prepend `https://` when no scheme exists; accept only `http`/`https` with a nonempty host. `set_submitting(True)` disables the input and submit button, changes button text to the translated “正在添加…”, and leaves Cancel available. `show_error()` retains the URL, sets the dynamic `validationError` property, refreshes style polish/unpolish, and focuses the input.

- [ ] **Step 4: Run dialog tests and lint**

Run: `pytest tests/test_ui/test_add_feed_dialog.py -v && ruff check ui/dialogs/add_feed_dialog.py tests/test_ui/test_add_feed_dialog.py`

Expected: both tests pass and lint is clean.

- [ ] **Step 5: Commit the dialog**

```bash
git add ui/dialogs/add_feed_dialog.py tests/test_ui/test_add_feed_dialog.py
git commit -m "feat(ui): add accessible feed dialog"
```

### Task 5: Main Window Layout, Persistence, and Async Orchestration

**Files:**
- Create: `ui/main_window.py`
- Create: `tests/test_ui/test_main_window.py`

**Interfaces:**
- Consumes: injected `FeedStore`, `EntryStore`, and `SyncService` exact APIs from `INTERFACE.md`; `Sidebar`, `EntryListWidget`, `ReaderView`, `AddFeedDialog` from Tasks 2–4.
- Produces: `MainWindow(feed_store, entry_store, sync_service, settings: QSettings | None = None)`; async methods `load_feeds()`, `add_feed(url)`, `select_feed(feed_id)`, `select_entry(entry_id)`, `sync_feed(feed_id)`.

- [ ] **Step 1: Write dependency fakes and failing layout tests**

Define small async fake classes inside `tests/test_ui/test_main_window.py` with recorded calls and fixed `FeedRow`, `EntryListItem`, and `EntryRow` outputs. Use a temporary INI-backed `QSettings` so tests never touch user settings. Verify `window.splitter.count() == 3`, initial sizes are close to 240/360/remainder, minimum size is 1024 × 640 or greater, and Reader begins in its instructional empty state.

- [ ] **Step 2: Write failing async flow tests**

Cover:

- `load_feeds()` calls `FeedStore.list_all()` and `unread_count()` and populates Sidebar.
- submitting a new URL calls only `FeedStore.add()`, then `SyncService.sync_feed(feed.id)`; duplicate errors remain inline.
- selecting a Feed updates `state.selected_feed_id`, calls `EntryStore.list_by_feed(feed_id)`, and displays entries.
- two rapid selections use monotonically increasing string request IDs; completion of the older request cannot overwrite the newer Feed's articles.
- sync error signal preserves articles, marks the Feed row, and exposes Retry.

- [ ] **Step 3: Run tests and verify missing MainWindow**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_ui/test_main_window.py -v`

Expected: collection fails because `ui.main_window` does not exist.

- [ ] **Step 4: Implement the three-column MainWindow**

Construct the `QSplitter(Qt.Horizontal)` and add Sidebar, EntryListWidget, ReaderView in that order. Apply minimum widths without forcing fixed widths. Set first-run sizes `[240, 360, 680]`; use a 1280 × 800 default and minimum 1024 × 640. Connect only user-intent signals here.

Inject dependencies rather than constructing them in `ui/`:

```python
class MainWindow(QMainWindow):
    def __init__(
        self,
        feed_store: FeedStore,
        entry_store: EntryStore,
        sync_service: SyncService,
        settings: QSettings | None = None,
    ) -> None: ...
```

- [ ] **Step 5: Implement guarded async flows**

Use `@asyncSlot()` for signal entry points. Increment a private sequence for each Feed selection and compare the captured sequence before displaying returned entries. Catch only expected exceptions at the boundary: `DuplicateFeedError` becomes `self.tr("已订阅该源")`; other add/load exceptions become a translated short error plus Retry. Never clear valid content when a refresh starts or fails.

- [ ] **Step 6: Connect the locked SyncSignals**

Connect `sync_started(int)`, `sync_finished(int, int)`, `sync_error(int, str)`, and `sync_all_done(int, int)` once in `__init__`. Update Sidebar row status and status bar. On successful sync of the selected Feed, reload its entries using the same stale-request guard.

- [ ] **Step 7: Persist and restore geometry safely**

Use keys `ui/main_window/geometry`, `ui/main_window/state`, and `ui/main_window/splitter`. Restore only when byte arrays are present; otherwise use defaults. On `closeEvent`, save all three values and call `settings.sync()`. If restored geometry has no intersection with any `QGuiApplication.screens()` available geometry, recenter the default window.

- [ ] **Step 8: Run MainWindow tests**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_ui/test_main_window.py -v`

Expected: layout, flow, stale-result, error-retention and persistence tests all pass.

- [ ] **Step 9: Commit MainWindow**

```bash
git add ui/main_window.py tests/test_ui/test_main_window.py
git commit -m "feat(ui): implement phase 1 main window"
```

### Task 6: Application Wiring and Full Verification

**Files:**
- Modify: `app/app.py`
- Modify: `tests/test_ui/test_main_window.py`

**Interfaces:**
- Consumes: `MainWindow` constructor from Task 5 and existing `state.db` lifecycle.
- Produces: `MercuryApp.create_main_window() -> ui.main_window.MainWindow`.

- [ ] **Step 1: Add a failing wiring test**

Patch `_default_data_path()` to a temporary path, instantiate `MercuryApp`, call `create_main_window()`, and assert the result is `ui.main_window.MainWindow`, uses the injected `state.db`, and has the application stylesheet available for installation.

- [ ] **Step 2: Run the wiring test and verify the placeholder failure**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_ui/test_main_window.py -k wiring -v`

Expected: failure because `app.app.MainWindow` is still the placeholder class.

- [ ] **Step 3: Replace only the placeholder wiring in app/app.py**

Keep `_default_data_path()` and database initialization intact. Import `application_stylesheet`, `SyncService`, `EntryStore`, `FeedStore`, and `ui.main_window.MainWindow`. Construct one `SyncService` instance so its connected signals remain alive. Return the injected MainWindow and set the stylesheet on `QApplication.instance()` when available.

```python
def create_main_window(self) -> MainWindow:
    if state.db is None:
        raise RuntimeError("Database is not initialized")
    window = MainWindow(
        feed_store=FeedStore(state.db),
        entry_store=EntryStore(state.db),
        sync_service=SyncService(state.db),
    )
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(application_stylesheet())
    return window
```

- [ ] **Step 4: Run all UI tests**

Run: `QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox pytest tests/test_ui/ -v`

Expected: all UI tests pass with no network, persistent user settings, or disk database access.

- [ ] **Step 5: Run the full regression and lint suites**

Run: `ruff check .`

Expected: no lint errors.

Run: `QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox pytest -v`

Expected: all existing Store, Feed, Reader and Agent tests plus new UI tests pass.

- [ ] **Step 6: Perform the manual Phase 1 smoke test**

Run: `python main.py`.

Verify: comfortable B visual direction; no blank panel; keyboard can add/select/sync; invalid URL is inline; offline/sync errors retain old content; a restart restores geometry and splitter sizes; 125%, 150%, and 200% scaling keeps key controls visible.

- [ ] **Step 7: Commit application integration**

```bash
git add app/app.py tests/test_ui/test_main_window.py
git commit -m "feat(ui): wire phase 1 feed workflow"
```

## Final Acceptance Checklist

- [ ] `ui/main_window.py`, `ui/sidebar.py`, `ui/entry_list.py`, `ui/reader/reader_view.py`, and `ui/dialogs/add_feed_dialog.py` exist with exactly these names.
- [ ] `app/styles.py` is the only source of application-level QSS and visual tokens.
- [ ] UI dependencies match `INTERFACE.md`; no locked dataclass or core/store signature is modified.
- [ ] The three-column application starts and supports add → sync → feed selection → article list → Phase 1 summary display.
- [ ] Empty/loading/content/error/offline/disabled states are explicit and never become blank panels.
- [ ] Stale async results cannot overwrite the current Feed selection.
- [ ] Geometry and splitter sizes restore after restart.
- [ ] Keyboard focus, tooltips, accessible names, truncation and non-color state cues are verified.
- [ ] `ruff check .` and the complete `pytest` suite pass.
