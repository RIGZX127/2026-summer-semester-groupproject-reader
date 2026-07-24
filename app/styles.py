"""Application-wide spacing tokens and palette-driven QSS."""

from __future__ import annotations

from ui.theme import LIGHT_PALETTE, Palette

SPACING = {"unit": 8, "compact": 6, "normal": 12, "section": 20, "large": 28}
RADIUS = {"control": 8, "panel": 12}


def application_stylesheet(palette: Palette = LIGHT_PALETTE) -> str:
    """Return polished QSS for the selected semantic palette."""
    p = palette
    return f"""
    QWidget {{ color: {p.text}; font-size: 14px; selection-background-color: {p.accent}; }}
    QToolTip {{ color: {p.text}; background: {p.surface}; border: 1px solid {p.border_strong};
        padding: 6px 8px; border-radius: 6px; }}
    QMainWindow, QWidget#ContentSurface, QDialog {{ background: {p.window}; }}
    QWidget#Sidebar {{ background: {p.sidebar}; color: #EAF0ED; }}
    QWidget#Sidebar QLabel {{ color: #EAF0ED; }}
    QLabel#AppTitle {{ font-size: 21px; font-weight: 700; }}
    QLabel#SidebarSection {{ color: #A7B7B1; font-weight: 600; }}
    QLabel#SectionTitle {{ font-size: 18px; font-weight: 650; }}
    QLabel#MutedLabel, QLabel#StateMessage {{ color: {p.text_muted}; }}
    QLabel#ErrorLabel {{ color: {p.error}; }}
    QLabel#SuccessLabel {{ color: {p.success}; font-weight: 600; }}
    QLabel#StateTitle {{ font-size: 17px; font-weight: 650; }}
    QLabel#LoadingBanner {{ color: {p.accent}; background: {p.accent_soft};
        padding: 8px 12px; border-radius: {RADIUS["control"]}px; }}
    QListWidget {{ border: 0; outline: 0; background: transparent; }}
    QListWidget::item {{ padding: 12px; border-radius: {RADIUS["control"]}px; }}
    QListWidget::item:hover {{ background: {p.surface_hover}; }}
    QListWidget::item:selected {{ background: {p.accent_soft}; color: {p.text}; }}
    QWidget#Sidebar QListWidget {{ color: #DCE6E1; }}
    QWidget#Sidebar QListWidget::item:hover {{ background: {p.sidebar_hover}; }}
    QWidget#Sidebar QListWidget::item:selected {{ background: {p.sidebar_selected}; color: white; }}
    QWidget#ReaderToolbar {{ background: {p.surface_alt}; border-bottom: 1px solid {p.border}; }}
    QWidget#ReaderToolbar QLabel {{ color: {p.text_muted}; font-weight: 600; }}
    QPushButton {{ min-height: 36px; padding: 0 13px; border: 1px solid {p.border};
        border-radius: {RADIUS["control"]}px; background: {p.control}; }}
    QPushButton:hover {{ background: {p.surface_hover}; border-color: {p.border_strong}; }}
    QPushButton:pressed {{ background: {p.surface_pressed}; padding-top: 1px; }}
    QPushButton:focus {{ border: 2px solid {p.focus}; }}
    QPushButton:disabled {{ color: {p.text_disabled}; border-color: {p.border}; background: {p.surface_alt}; }}
    QPushButton#PrimaryButton, QPushButton[buttonRole="primary"] {{ color: {p.text_on_accent}; background: {p.accent}; border-color: {p.accent}; }}
    QPushButton#PrimaryButton:hover, QPushButton[buttonRole="primary"]:hover {{ background: {p.accent_hover}; border-color: {p.accent_hover}; }}
    QPushButton#PrimaryButton:pressed, QPushButton[buttonRole="primary"]:pressed {{ background: {p.accent_pressed}; border-color: {p.accent_pressed}; }}
    QPushButton#DangerButton:hover {{ color: {p.error}; background: {p.error_soft}; border-color: {p.error}; }}
    QWidget#ReaderToolbar QPushButton {{ min-width: 28px; max-width: 28px;
        min-height: 28px; max-height: 28px; padding: 0; color: {p.text_muted};
        background: transparent; border-color: transparent; }}
    QWidget#ReaderToolbar QPushButton:hover {{ color: {p.text}; background: {p.surface_hover}; }}
    QWidget#ReaderToolbar QPushButton:checked {{ color: {p.text_on_accent}; background: {p.accent}; border-color: {p.accent}; }}
    QWidget#ReaderToolbar QPushButton#FocusModeButton {{ padding: 0; background: {p.control};
        border: 1px solid {p.border}; }}
    QWidget#ReaderToolbar QPushButton#FocusModeButton:checked {{ color: {p.text_on_accent}; background: {p.accent}; }}
    QWidget#ReaderToolbar QPushButton#SidebarRestoreButton {{ padding: 0; border: 1px solid {p.border}; }}
    QWidget#ReaderToolbar QPushButton#TranslateButton {{ padding: 0; border: 1px solid {p.border}; }}
    QWidget#ReaderToolbar QComboBox, QWidget#ReaderToolbar QSpinBox {{ min-height: 32px;
        padding: 0 6px; }}
    QSplitter#ReaderSummarySplitter::handle {{ height: 7px; background: {p.border}; }}
    QSplitter#ReaderSummarySplitter::handle:hover {{ background: {p.accent}; }}
    QFrame#SummaryPanel {{ background: {p.surface}; border-top: 1px solid {p.border}; }}
    QWidget#SummaryHeaderBar {{ background: {p.surface}; border-bottom: 1px solid {p.border}; }}
    QPushButton#SummaryHeader {{ border: 0; background: transparent; text-align: left; font-weight: 650; }}
    QLabel#SummaryStatus {{ color: {p.text_muted}; }}
    QLabel#SummaryPlaceholder {{ color: {p.text_muted}; padding: 12px; }}
    QLabel#ReaderTags {{ color: {p.text_muted}; background: {p.surface_alt};
        border-bottom: 1px solid {p.border}; padding: 6px 14px; }}
    QTextBrowser#SummaryContent {{ color: {p.text}; background: {p.surface}; border: 0; }}
    QWidget#EntryBatchToolbar {{ background: {p.surface_alt}; border: 1px solid {p.border};
        border-radius: {RADIUS["control"]}px; }}
    QLabel#BatchCountLabel {{ color: {p.text_muted}; font-weight: 600; }}
    QPushButton#EntryHeaderIconButton, QPushButton#BatchActionButton {{ min-width: 28px; max-width: 28px;
        min-height: 28px; max-height: 28px; padding: 0; }}
    QGroupBox {{ margin-top: 12px; padding-top: 14px; border: 1px solid {p.border}; border-radius: {RADIUS["panel"]}px; font-weight: 650; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}
    QTabWidget::pane {{ border: 1px solid {p.border}; border-radius: {RADIUS["panel"]}px; background: {p.surface}; }}
    QTabWidget#ReaderBottomTabs QTabBar::tab {{ color: {p.text_muted};
        background: {p.surface_alt}; border: 1px solid {p.border}; border-bottom: 0;
        padding: 7px 14px; margin-right: 2px; }}
    QTabWidget#ReaderBottomTabs QTabBar::tab:selected {{ color: {p.text};
        background: {p.surface}; font-weight: 650; }}
    QTabWidget#ReaderBottomTabs QTabBar::tab:hover:!selected {{ color: {p.text};
        background: {p.surface_hover}; }}
    QPlainTextEdit#NoteTextEdit {{ color: {p.text}; background: {p.control};
        border: 1px solid {p.border}; border-radius: {RADIUS["control"]}px;
        padding: 8px; selection-color: {p.text_on_accent};
        selection-background-color: {p.accent}; }}
    QPlainTextEdit#NoteTextEdit:focus {{ border: 2px solid {p.focus}; }}
    QPlainTextEdit#NoteTextEdit:disabled {{ color: {p.text_disabled};
        background: {p.surface_alt}; }}
    QLabel#NoteSaveStatus {{ color: {p.text_muted}; }}
    QWidget#Sidebar QPushButton {{ color: white; background: {p.sidebar_selected}; border-color: {p.sidebar_hover}; }}
    QWidget#Sidebar QPushButton#SidebarCollapseButton {{ min-width: 28px; max-width: 28px;
        min-height: 28px; max-height: 28px; padding: 0; background: transparent;
        border-color: transparent; }}
    QWidget#Sidebar QPushButton#SidebarCollapseButton:hover {{ background: {p.sidebar_hover}; border-color: {p.sidebar_selected}; }}
    QWidget#Sidebar QPushButton#SidebarActionButton {{ min-width: 28px; max-width: 28px;
        min-height: 28px; max-height: 28px; padding: 0; background: transparent;
        border-color: {p.sidebar_selected}; }}
    QWidget#Sidebar QPushButton#SidebarActionButton:hover {{ background: {p.sidebar_hover};
        border-color: #8CA29A; }}
    QLineEdit, QComboBox, QSpinBox {{ min-height: 36px; padding: 0 10px; color: {p.text};
        background: {p.control}; border: 1px solid {p.border}; border-radius: {RADIUS["control"]}px; }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{ border-color: {p.border_strong}; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 2px solid {p.focus}; }}
    QLineEdit[validationError="true"] {{ border: 1px solid {p.error}; }}
    QComboBox#SearchScopeSelector {{ padding-left: 8px; padding-right: 4px; }}
    QComboBox[readerControl="true"], QSpinBox[readerControl="true"] {{
        color: {p.text}; background: {p.control}; border-color: {p.border};
    }}
    QComboBox[readerControl="true"] QAbstractItemView {{ color: {p.text}; background: {p.control};
        selection-color: {p.text_on_accent}; selection-background-color: {p.accent}; border: 1px solid {p.border}; outline: 0; }}
    QWidget#ReaderToolbar QPushButton#ReaderPopupButton {{ min-width: 28px; max-width: 28px;
        min-height: 28px; max-height: 28px; padding: 0; background: {p.control};
        border: 1px solid {p.border}; }}
    QWidget#ReaderToolbar QPushButton#ReaderPopupButton:hover {{ background: {p.surface_hover};
        border-color: {p.border_strong}; }}
    QWidget#ReaderToolbar QPushButton#ReaderPopupButton:focus {{ background: {p.surface};
        border: 1px solid {p.focus}; }}
    QMenu {{ background: {p.surface}; color: {p.text}; border: 1px solid {p.border}; padding: 6px; }}
    QMenu::item {{ padding: 7px 24px 7px 10px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {p.accent_soft}; }}
    QSplitter::handle {{ background: {p.border}; width: 1px; }}
    QStatusBar {{ background: {p.surface_alt}; color: {p.text_muted}; border-top: 1px solid {p.border}; }}
    QScrollBar:vertical {{ width: 10px; background: transparent; margin: 2px; }}
    QScrollBar::handle:vertical {{ min-height: 28px; border-radius: 4px; background: {p.border_strong}; }}
    QScrollBar::handle:vertical:hover {{ background: {p.text_muted}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

    QWidget#BulkActionBar {{ background: {p.accent_soft}; border-bottom: 1px solid {p.border}; padding: 4px 0; }}
    QLabel#BulkCountLabel {{ font-weight: 650; color: {p.text}; }}
    QPushButton#BulkDeleteButton {{ color: {p.error}; border-color: {p.error}; }}
    QPushButton#BulkDeleteButton:hover {{ background: {p.error_soft}; }}
    QPushButton[buttonRole="danger"] {{ color: {p.error}; border-color: {p.error}; }}
    QPushButton[buttonRole="danger"]:hover {{ background: {p.error_soft}; }}
    QFrame#SummarySeparator {{ color: {p.border}; }}
    QComboBox#SummaryLineHeightCombo {{ min-height: 28px; font-size: 12px; padding: 0 6px; }}
    """
