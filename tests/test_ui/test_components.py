from store.entry_store import EntryListItem, EntryRow
from store.feed_store import FeedRow
from ui.entry_list import EntryListWidget
from ui.reader.reader_view import ReaderView
from ui.sidebar import Sidebar


def _feed(feed_id: int = 1, title: str = "A very long feed title") -> FeedRow:
    return FeedRow(feed_id, "https://example.com/rss", title, "", None, "now", "now")


def _entry(entry_id: int = 2) -> EntryListItem:
    return EntryListItem(entry_id, 1, "Article title", "Summary", "Author", "now", False, False)


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


def test_entry_list_keeps_content_while_loading(qtbot) -> None:
    view = EntryListWidget()
    qtbot.addWidget(view)
    view.set_entries([_entry()])
    view.set_state("loading")
    assert view.entry_list.count() == 1
    assert view.loading_banner.isVisibleTo(view)


def test_entry_list_emits_selected_entry_id(qtbot) -> None:
    view = EntryListWidget()
    qtbot.addWidget(view)
    view.set_entries([_entry()])
    with qtbot.waitSignal(view.entry_selected, timeout=500) as signal:
        view.entry_list.setCurrentRow(0)
    assert signal.args == [2]


def test_reader_starts_with_instruction_and_escapes_entry(qtbot) -> None:
    view = ReaderView()
    qtbot.addWidget(view)
    assert "选择一篇文章" in view.empty_label.text()
    entry = EntryRow(
        2, 1, "g", None, "<script>alert(1)</script>", "<b>safe</b>",
        "A", None, False, False, False, "now",
    )
    view.show_entry(entry)
    assert "&lt;script&gt;" in view.last_html
    assert "<script>" not in view.last_html
