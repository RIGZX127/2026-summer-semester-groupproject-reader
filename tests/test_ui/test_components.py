from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QInputDialog, QStyleOptionViewItem

from store.entry_store import EntryListItem, EntryRow
from store.feed_store import FeedRow
from ui.entry_list import EntryListWidget
from ui.icons import theme_icon
from ui.reader.reader_view import ReaderView
from ui.sidebar import Sidebar


def _feed(feed_id: int = 1, title: str = "A very long feed title") -> FeedRow:
    return FeedRow(feed_id, "https://example.com/rss", title, "", None, "now", "now")


def _entry(entry_id: int = 2, *, is_read: bool = False) -> EntryListItem:
    return EntryListItem(entry_id, 1, "Article title", "Summary", "Author", "now", is_read, False)


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


def test_sidebar_exposes_compact_ai_settings_entry(qtbot) -> None:
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    assert sidebar.ai_button.text() == ""
    assert sidebar.ai_button.toolTip() == "AI 设置"
    assert sidebar.ai_button.accessibleName() == "AI 设置"
    agent_image = sidebar.ai_button.icon().pixmap(QSize(20, 20)).toImage()
    theme_image = theme_icon(mode="light").pixmap(QSize(20, 20)).toImage()
    assert any(
        agent_image.pixelColor(x, y) != theme_image.pixelColor(x, y)
        for x in range(agent_image.width())
        for y in range(agent_image.height())
    )
    with qtbot.waitSignal(sidebar.ai_settings_requested, timeout=500):
        sidebar.ai_button.click()


def test_sidebar_exposes_opml_import_and_export_icons(qtbot) -> None:
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)

    assert sidebar.import_opml_button.text() == ""
    assert sidebar.import_opml_button.toolTip() == "导入 OPML"
    assert sidebar.import_opml_button.accessibleName() == "导入 OPML"
    assert sidebar.export_opml_button.text() == ""
    assert sidebar.export_opml_button.toolTip() == "导出 OPML"
    assert sidebar.export_opml_button.accessibleName() == "导出 OPML"

    with qtbot.waitSignal(sidebar.import_opml_requested, timeout=500):
        sidebar.import_opml_button.click()
    with qtbot.waitSignal(sidebar.export_opml_requested, timeout=500):
        sidebar.export_opml_button.click()


def test_sidebar_header_has_icon_only_collapse_control(qtbot) -> None:
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    assert sidebar.collapse_button.text() == ""
    assert sidebar.collapse_button.accessibleName() == "隐藏订阅源栏"
    with qtbot.waitSignal(sidebar.collapse_requested, timeout=500):
        sidebar.collapse_button.click()


def test_sidebar_sync_menu_exposes_current_and_all_actions(qtbot) -> None:
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    sidebar.set_feeds([(_feed(), 0)])

    assert sidebar.sync_current_action.isEnabled() is False
    with qtbot.waitSignal(sidebar.sync_all_requested, timeout=500):
        sidebar.sync_all_action.trigger()

    sidebar.feed_list.setCurrentRow(0)
    assert sidebar.sync_current_action.isEnabled() is True
    with qtbot.waitSignal(sidebar.sync_requested, timeout=500) as signal:
        sidebar.sync_current_action.trigger()
    assert signal.args == [1]


def test_sidebar_feed_management_emits_intentions(qtbot, monkeypatch) -> None:
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    sidebar.set_feeds([(_feed(title="Original"), 0)])
    sidebar.feed_list.setCurrentRow(0)
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("Renamed", True))

    with qtbot.waitSignal(sidebar.feed_rename_requested, timeout=500) as rename_signal:
        sidebar._rename_current_feed()
    assert rename_signal.args == [1, "Renamed"]

    with qtbot.waitSignal(sidebar.feed_delete_requested, timeout=500) as delete_signal:
        sidebar._request_delete_current_feed()
    assert delete_signal.args == [1]


def test_sidebar_feed_context_menu_has_rename_and_delete_only(qtbot) -> None:
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    assert [action.text() for action in sidebar.feed_menu.actions()] == [
        "重命名订阅",
        "删除订阅",
    ]
    assert not hasattr(sidebar, "delete_button")


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


def test_entry_search_scope_updates_visible_context(qtbot) -> None:
    view = EntryListWidget()
    qtbot.addWidget(view)

    assert view.search_scope.currentData() == "feed"
    assert "当前订阅" in view.search_edit.placeholderText()
    with qtbot.waitSignal(view.search_scope_changed, timeout=500) as signal:
        view.search_scope.setCurrentIndex(view.search_scope.findData("all"))

    assert signal.args == ["all"]
    assert view.heading.text() == "全部文章"
    assert "全部订阅" in view.search_edit.placeholderText()


def test_entry_search_context_menu_is_localized(qtbot) -> None:
    view = EntryListWidget()
    qtbot.addWidget(view)
    menu = view._create_search_context_menu()

    labels = [action.text() for action in menu.actions() if not action.isSeparator()]
    assert labels == ["复制", "粘贴"]


def test_entry_list_uses_dark_bold_unread_and_gray_regular_read_text(qtbot) -> None:
    view = EntryListWidget()
    qtbot.addWidget(view)
    view.set_entries([_entry(1), _entry(2, is_read=True)])
    delegate = view.entry_list.itemDelegate()

    unread_option = QStyleOptionViewItem()
    read_option = QStyleOptionViewItem()
    delegate.initStyleOption(unread_option, view.entry_list.model().index(0, 0))
    delegate.initStyleOption(read_option, view.entry_list.model().index(1, 0))

    assert unread_option.palette.color(QPalette.ColorRole.Text) != read_option.palette.color(
        QPalette.ColorRole.Text
    )
    assert unread_option.font.weight() > read_option.font.weight()
    assert "未读" not in view.entry_list.item(0).text()
    assert "已读" not in view.entry_list.item(1).text()
    assert view.entry_list.item(0).data(Qt.ItemDataRole.AccessibleTextRole).startswith("未读：")
    assert view.entry_list.item(1).data(Qt.ItemDataRole.AccessibleTextRole).startswith("已读：")


def test_reader_starts_with_instruction_and_escapes_entry(qtbot) -> None:
    view = ReaderView()
    qtbot.addWidget(view)
    assert "选择一篇文章" in view.empty_label.text()
    entry = EntryRow(
        2,
        1,
        "g",
        None,
        "<script>alert(1)</script>",
        "<b>safe</b>",
        "A",
        None,
        False,
        False,
        False,
        "now",
    )
    view.show_entry(entry)
    assert "&lt;script&gt;" in view.last_html
    assert "<script>" not in view.last_html
