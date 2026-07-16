from PySide6.QtCore import QSettings

from ui.reader.reader_view import ReaderView


def test_reader_modes_keep_current_content(tmp_path, qtbot) -> None:
    settings = QSettings(str(tmp_path / "reader.ini"), QSettings.Format.IniFormat)
    view = ReaderView(settings=settings)
    qtbot.addWidget(view)
    view.show_content("<h1>Full article</h1>", "https://example.com/article")

    view.set_mode("web")
    assert view.current_mode == "web"
    assert "Full article" in view.last_html

    view.set_mode("split")
    assert view.current_mode == "split"
    assert view.content_stack.currentWidget() is view.splitter


def test_web_mode_without_url_shows_explanation(tmp_path, qtbot) -> None:
    settings = QSettings(str(tmp_path / "reader.ini"), QSettings.Format.IniFormat)
    view = ReaderView(settings=settings)
    qtbot.addWidget(view)
    view.show_content("<p>Reader content</p>", None)
    view.set_mode("web")
    assert view.web_stack.currentWidget() is view.no_url_page
