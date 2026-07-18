from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QSizePolicy, QSplitter, QWidget

from store.entry_store import EntryListItem
from store.feed_store import FeedRow
from ui.entry_list import EntryListWidget
from ui.reader.reader_toolbar import ReaderToolbar
from ui.reader.summary_panel import SummaryPanel
from ui.sidebar import Sidebar


def _entry(entry_id: int) -> EntryListItem:
    return EntryListItem(
        entry_id,
        1,
        f"Article {entry_id}",
        "Summary",
        "Author",
        "now",
        False,
        False,
    )


def test_entry_list_batch_mode_emits_selected_ids(qtbot) -> None:
    view = EntryListWidget()
    qtbot.addWidget(view)
    view.set_entries([_entry(1), _entry(2), _entry(3)])

    view.batch_button.click()
    assert view.batch_toolbar.isHidden() is False
    assert view.entry_list.selectionMode() == QAbstractItemView.SelectionMode.MultiSelection

    view.entry_list.item(0).setSelected(True)
    view.entry_list.item(2).setSelected(True)
    assert view.batch_count.text() == "已选择 2 篇"

    menu = view._create_batch_context_menu()
    assert [action.text() for action in menu.actions() if not action.isSeparator()] == [
        "标记已读",
        "标记未读",
        "切换收藏",
        "删除选中文章",
    ]
    with qtbot.waitSignal(view.batch_mark_read_requested, timeout=500) as signal:
        menu.actions()[0].trigger()
    assert signal.args == [[1, 3], True]


def test_entry_list_batch_actions_exist_only_in_context_menu(qtbot) -> None:
    view = EntryListWidget()
    qtbot.addWidget(view)
    view.set_entries([_entry(1)])
    view.set_batch_mode(True)

    assert not hasattr(view, "batch_read_button")
    assert not hasattr(view, "batch_unread_button")
    assert not hasattr(view, "batch_star_button")
    assert not hasattr(view, "batch_delete_button")
    assert all(not action.isEnabled() for action in view._create_batch_context_menu().actions())


def test_entry_list_icon_controls_share_global_compact_size(qtbot) -> None:
    view = EntryListWidget()
    qtbot.addWidget(view)

    controls = (
        view.batch_button,
        view.batch_close_button,
    )
    assert all(button.width() == button.height() == 30 for button in controls)
    assert all(button.iconSize().width() == button.iconSize().height() == 18 for button in controls)


def test_entry_list_does_not_open_article_in_batch_mode(qtbot) -> None:
    view = EntryListWidget()
    qtbot.addWidget(view)
    view.set_entries([_entry(4)])
    view.set_batch_mode(True)

    with qtbot.assertNotEmitted(view.entry_selected):
        view.entry_list.setCurrentRow(0)


def test_sidebar_replaces_verbose_actions_with_icons(qtbot) -> None:
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)

    for button in (
        sidebar.add_button,
        sidebar.sync_button,
        sidebar.ai_button,
    ):
        assert button.text() == ""
        assert button.toolTip()
        assert button.accessibleName()
        assert button.icon().isNull() is False
        assert button.size().width() == button.size().height() == 30
        assert button.iconSize().width() == button.iconSize().height() == 18
        assert button.property("immediateToolTip") is True

    assert sidebar.ai_card is None


def test_sidebar_feed_items_have_collection_icon(qtbot) -> None:
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    feed = FeedRow(1, "https://example.com/rss", "Example", "", None, "now", "now")
    sidebar.set_feeds([(feed, 2)])

    assert sidebar.feed_list.item(0).icon().isNull() is False


def test_reader_toolbar_uses_compact_visual_controls(qtbot) -> None:
    toolbar = ReaderToolbar()
    qtbot.addWidget(toolbar)

    for button in (
        toolbar.reader_button,
        toolbar.web_button,
        toolbar.split_button,
        toolbar.translate_button,
        toolbar.focus_button,
    ):
        assert button.toolTip()
        assert button.accessibleName()

    assert toolbar.reader_button.text() == ""
    assert toolbar.web_button.text() == ""
    assert toolbar.split_button.text() == ""
    assert toolbar.translate_button.text() == ""
    assert toolbar.font_size.toolTip() == f"正文字号：{toolbar.font_size.currentData()}"
    assert toolbar.font_size.width() == toolbar.theme_combo.width() == 30
    assert toolbar.width_combo.width() == toolbar.theme_combo.width()
    assert toolbar.translation_mode.maximumWidth() <= 92


def test_three_column_header_controls_share_top_alignment(qtbot) -> None:
    sidebar = Sidebar()
    entries = EntryListWidget()
    toolbar = ReaderToolbar()
    for widget in (sidebar, entries):
        widget.resize(420, 300)
        qtbot.addWidget(widget)
        widget.show()
    toolbar.resize(420, 42)
    qtbot.addWidget(toolbar)
    toolbar.show()
    qtbot.wait(0)

    assert sidebar.collapse_button.geometry().top() == 6
    assert entries.batch_button.geometry().top() == 6
    assert toolbar.focus_button.geometry().top() == 6


def test_summary_content_uses_tighter_line_spacing(qtbot) -> None:
    panel = SummaryPanel()
    qtbot.addWidget(panel)
    wrapped = panel._wrap_styles("<p>Summary</p>")

    assert "line-height: 1.45" in wrapped
    assert "p { margin: 0.3em 0; }" in wrapped


def test_summary_panel_pins_header_and_fills_resized_space(qtbot) -> None:
    panel = SummaryPanel()
    qtbot.addWidget(panel)

    assert panel._header_bar.height() == panel._header_bar.maximumHeight() == 44
    assert panel.maximumHeight() == 16777215
    assert panel._body.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Expanding
    assert panel._content.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Expanding
    assert panel._collapsed_spacer.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Expanding

    panel._toggle()
    assert panel.maximumHeight() == 16777215


def test_summary_panel_remains_freely_resizable_in_splitter(qtbot) -> None:
    splitter = QSplitter(Qt.Orientation.Vertical)
    panel = SummaryPanel()
    splitter.addWidget(QWidget())
    splitter.addWidget(panel)
    splitter.setChildrenCollapsible(False)
    splitter.resize(500, 400)
    qtbot.addWidget(splitter)
    splitter.show()

    panel.set_expanded(True, notify=False)
    splitter.setSizes([270, 120])
    qtbot.wait(0)
    first_height = splitter.sizes()[1]
    splitter.setSizes([190, 200])
    qtbot.wait(0)

    assert first_height >= 110
    assert splitter.sizes()[1] > first_height
    assert panel._collapsed_spacer.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Fixed
    panel._toggle()
    assert panel.maximumHeight() == 16777215


def test_top_level_ai_menu_is_not_created(tmp_path, qtbot) -> None:
    from tests.test_ui.test_main_window import _window

    window = _window(tmp_path, qtbot)
    assert not hasattr(window, "ai_menu")
    assert window.menuBar().actions() == []

    assert window.sidebar.ai_button.toolTip() == "AI 设置"
