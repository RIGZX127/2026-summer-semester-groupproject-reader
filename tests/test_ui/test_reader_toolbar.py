from ui.reader.reader_toolbar import ReaderToolbar


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
