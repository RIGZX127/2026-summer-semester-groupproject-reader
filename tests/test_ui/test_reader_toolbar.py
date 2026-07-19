from PySide6.QtCore import QEvent, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QToolTip

from ui.reader.reader_toolbar import PopupIconButton, ReaderToolbar
from ui.reader.theme import Theme


def test_toolbar_emits_mode_and_setting_changes(qtbot) -> None:
    toolbar = ReaderToolbar()
    qtbot.addWidget(toolbar)

    with qtbot.waitSignal(toolbar.mode_changed, timeout=500) as mode:
        toolbar.web_button.click()
    assert mode.args == ["web"]

    with qtbot.waitSignal(toolbar.theme_preference_changed, timeout=500) as scheme:
        toolbar.theme_combo.setCurrentIndex(2)
    assert scheme.args == ["dark"]


def test_toolbar_controls_are_accessible(qtbot) -> None:
    toolbar = ReaderToolbar()
    qtbot.addWidget(toolbar)
    assert toolbar.reader_button.accessibleName()
    assert toolbar.font_size.accessibleName()
    assert toolbar.width_combo.accessibleName()


def test_toolbar_exposes_stable_style_hooks(qtbot) -> None:
    toolbar = ReaderToolbar()
    qtbot.addWidget(toolbar)

    assert toolbar.objectName() == "ReaderToolbar"
    assert toolbar.font_size.property("readerControl") is True
    assert toolbar.theme_combo.property("readerControl") is True
    assert toolbar.width_combo.property("readerControl") is True


def test_layout_icon_buttons_request_sidebar_restore_and_focus_modes(qtbot) -> None:
    toolbar = ReaderToolbar()
    qtbot.addWidget(toolbar)
    assert toolbar.sidebar_restore_button.text() == ""
    assert toolbar.focus_button.text() == ""
    with qtbot.waitSignal(toolbar.sidebar_restore_requested, timeout=500):
        toolbar.sidebar_restore_button.click()

    with qtbot.waitSignal(toolbar.focus_mode_changed, timeout=500) as focus_signal:
        toolbar.focus_button.click()
    assert focus_signal.args == [True]


def test_mode_icons_have_high_contrast_checked_state(qtbot) -> None:
    toolbar = ReaderToolbar()
    qtbot.addWidget(toolbar)

    for button in (toolbar.reader_button, toolbar.web_button, toolbar.split_button):
        normal = button.icon().pixmap(QSize(20, 20), QIcon.Mode.Normal, QIcon.State.Off).toImage()
        checked = button.icon().pixmap(QSize(20, 20), QIcon.Mode.Normal, QIcon.State.On).toImage()
        assert any(
            normal.pixelColor(x, y) != checked.pixelColor(x, y)
            for x in range(normal.width())
            for y in range(normal.height())
        )


def test_font_size_control_is_icon_only_with_numeric_popup(qtbot) -> None:
    toolbar = ReaderToolbar()
    qtbot.addWidget(toolbar)

    assert toolbar.font_size.property("compactIcon") is True
    assert toolbar.font_size.width() == toolbar.font_size.height() == 30
    assert [
        toolbar.font_size.itemData(index) for index in range(toolbar.font_size.count())
    ] == list(range(14, 25))
    assert [toolbar.font_size.itemText(index) for index in range(11)] == [
        str(value) for value in range(14, 25)
    ]
    assert all(toolbar.font_size.itemIcon(index).isNull() for index in range(11))
    assert toolbar.font_size.currentData() == Theme().font_size


def test_theme_and_width_controls_use_clean_icon_style(qtbot) -> None:
    toolbar = ReaderToolbar()
    qtbot.addWidget(toolbar)

    for control in (toolbar.font_size, toolbar.theme_combo, toolbar.width_combo):
        assert isinstance(control, PopupIconButton)
        assert control.property("compactIcon") is True
        assert control.width() == control.height() == 30
        assert control.objectName() == "ReaderPopupButton"

    assert [toolbar.theme_combo.itemText(index) for index in range(3)] == [
        "跟随系统",
        "浅色",
        "深色",
    ]
    assert [toolbar.width_combo.itemText(index) for index in range(3)] == ["窄", "中", "宽"]
    assert all(not toolbar.width_combo.itemIcon(index).isNull() for index in range(3))


def test_toolbar_icon_controls_share_one_size(qtbot) -> None:
    toolbar = ReaderToolbar()
    qtbot.addWidget(toolbar)

    controls = (
        toolbar.sidebar_restore_button,
        toolbar.reader_button,
        toolbar.web_button,
        toolbar.split_button,
        toolbar.translate_button,
        toolbar.font_size,
        toolbar.theme_combo,
        toolbar.width_combo,
        toolbar.focus_button,
    )
    assert all(control.size() == QSize(30, 30) for control in controls)
    assert all(control.iconSize() == QSize(18, 18) for control in controls)


def test_toolbar_icon_hover_shows_name_immediately(qtbot) -> None:
    toolbar = ReaderToolbar()
    qtbot.addWidget(toolbar)

    QApplication.sendEvent(toolbar.font_size, QEvent(QEvent.Type.Enter))
    assert QToolTip.text() == toolbar.font_size.toolTip()
    assert toolbar.font_size.property("immediateToolTip") is True
    QToolTip.hideText()
