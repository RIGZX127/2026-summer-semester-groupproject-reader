from ui.dialogs.add_feed_dialog import AddFeedDialog


def test_invalid_url_is_rejected_inline(qtbot) -> None:
    dialog = AddFeedDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.url_edit.setText("not a url")
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


def test_submitting_state_prevents_duplicate_submission(qtbot) -> None:
    dialog = AddFeedDialog()
    qtbot.addWidget(dialog)
    dialog.set_submitting(True)
    assert not dialog.url_edit.isEnabled()
    assert not dialog.submit_button.isEnabled()
    assert dialog.cancel_button.isEnabled()
