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
    QMainWindow, QWidget#ContentSurface, QDialog {{ background: {p.window}; }}
    QWidget#Sidebar {{ background: {p.sidebar}; color: #EAF0ED; }}
    QWidget#Sidebar QLabel {{ color: #EAF0ED; }}
    QLabel#AppTitle {{ font-size: 21px; font-weight: 700; }}
    QLabel#SidebarSection {{ color: #A7B7B1; font-weight: 600; }}
    QWidget#AIWorkspaceCard {{ background: {p.sidebar_hover}; border: 1px solid {p.sidebar_selected};
        border-radius: {RADIUS["panel"]}px; }}
    QLabel#AIWorkspaceTitle {{ color: #FFFFFF; font-size: 15px; font-weight: 700; }}
    QLabel#AIWorkspaceDescription {{ color: #BFD0CA; font-size: 12px; }}
    QPushButton#AIWorkspaceButton {{ color: {p.sidebar}; background: #E4F0EC;
        border-color: #E4F0EC; font-weight: 700; }}
    QPushButton#AIWorkspaceButton:hover {{ color: {p.sidebar}; background: #FFFFFF;
        border-color: #FFFFFF; }}
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
    QWidget#ReaderToolbar QPushButton {{ min-height: 34px; color: {p.text_muted}; background: transparent; border-color: transparent; }}
    QWidget#ReaderToolbar QPushButton:hover {{ color: {p.text}; background: {p.surface_hover}; }}
    QWidget#ReaderToolbar QPushButton:checked {{ color: {p.text_on_accent}; background: {p.accent}; border-color: {p.accent}; }}
    QWidget#ReaderToolbar QPushButton#FocusModeButton {{ padding: 0; border: 1px solid {p.border}; }}
    QWidget#ReaderToolbar QPushButton#FocusModeButton:checked {{ color: {p.text_on_accent}; background: {p.accent}; }}
    QWidget#ReaderToolbar QPushButton#SidebarRestoreButton {{ padding: 0; border: 1px solid {p.border}; }}
    QSplitter#ReaderSummarySplitter::handle {{ height: 7px; background: {p.border}; }}
    QSplitter#ReaderSummarySplitter::handle:hover {{ background: {p.accent}; }}
    QFrame#SummaryPanel {{ background: {p.surface}; border-top: 1px solid {p.border}; }}
    QPushButton#SummaryHeader {{ border: 0; background: transparent; text-align: left; font-weight: 650; }}
    QLabel#SummaryStatus {{ color: {p.text_muted}; }}
    QLabel#SummaryPlaceholder {{ color: {p.text_muted}; padding: 12px; }}
    QTextBrowser#SummaryContent {{ color: {p.text}; background: {p.surface}; border: 0; }}
    QGroupBox {{ margin-top: 12px; padding-top: 14px; border: 1px solid {p.border}; border-radius: {RADIUS["panel"]}px; font-weight: 650; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}
    QTabWidget::pane {{ border: 1px solid {p.border}; border-radius: {RADIUS["panel"]}px; background: {p.surface}; }}
    QWidget#Sidebar QPushButton {{ color: white; background: {p.sidebar_selected}; border-color: {p.sidebar_hover}; }}
    QWidget#Sidebar QPushButton#SidebarCollapseButton {{ padding: 0; background: transparent; border-color: transparent; }}
    QWidget#Sidebar QPushButton#SidebarCollapseButton:hover {{ background: {p.sidebar_hover}; border-color: {p.sidebar_selected}; }}
    QWidget#Sidebar QPushButton#AIWorkspaceButton {{ color: {p.sidebar}; background: #E4F0EC;
        border-color: #E4F0EC; font-weight: 700; }}
    QWidget#Sidebar QPushButton#AIWorkspaceButton:hover {{ color: {p.sidebar}; background: #FFFFFF;
        border-color: #FFFFFF; }}
    QLineEdit, QComboBox, QSpinBox {{ min-height: 36px; padding: 0 10px; color: {p.text};
        background: {p.control}; border: 1px solid {p.border}; border-radius: {RADIUS["control"]}px; }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{ border-color: {p.border_strong}; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 2px solid {p.focus}; }}
    QLineEdit[validationError="true"] {{ border: 1px solid {p.error}; }}
    QComboBox[readerControl="true"], QSpinBox[readerControl="true"] {{
        color: {p.text}; background: {p.control}; border-color: {p.border};
    }}
    QComboBox[readerControl="true"] QAbstractItemView {{ color: {p.text}; background: {p.control};
        selection-color: {p.text_on_accent}; selection-background-color: {p.accent}; border: 1px solid {p.border}; outline: 0; }}
    QMenu {{ background: {p.surface}; color: {p.text}; border: 1px solid {p.border}; padding: 6px; }}
    QMenu::item {{ padding: 7px 24px 7px 10px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {p.accent_soft}; }}
    QSplitter::handle {{ background: {p.border}; width: 1px; }}
    QStatusBar {{ background: {p.surface_alt}; color: {p.text_muted}; border-top: 1px solid {p.border}; }}
    QScrollBar:vertical {{ width: 10px; background: transparent; margin: 2px; }}
    QScrollBar::handle:vertical {{ min-height: 28px; border-radius: 4px; background: {p.border_strong}; }}
    QScrollBar::handle:vertical:hover {{ background: {p.text_muted}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    """
