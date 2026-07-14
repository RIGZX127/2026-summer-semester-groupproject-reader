"""Application-wide design tokens and QSS."""
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
    """Return the centralized application stylesheet."""
    return f"""
    QWidget {{ color: {COLORS['text']}; font-size: 14px; }}
    QMainWindow, QWidget#ContentSurface {{ background: {COLORS['surface']}; }}
    QWidget#Sidebar {{ background: {COLORS['sidebar']}; color: #EEF3F6; }}
    QWidget#Sidebar QLabel {{ color: #EEF3F6; }}
    QLabel#AppTitle {{ font-size: 20px; font-weight: 700; }}
    QLabel#SidebarSection {{ color: #9EB0BE; font-weight: 600; }}
    QLabel#SectionTitle {{ font-size: 17px; font-weight: 650; }}
    QLabel#MutedLabel {{ color: {COLORS['muted']}; }}
    QLabel#ErrorLabel {{ color: {COLORS['error']}; }}
    QLabel#StateTitle {{ font-size: 17px; font-weight: 650; color: {COLORS['text']}; }}
    QLabel#StateMessage {{ color: {COLORS['muted']}; }}
    QLabel#LoadingBanner {{
        color: {COLORS['accent']}; background: {COLORS['accent_soft']};
        padding: 7px 12px; border-bottom: 1px solid {COLORS['border']};
    }}
    QListWidget {{ border: 0; outline: 0; background: transparent; }}
    QListWidget::item {{ padding: 11px 12px; border-radius: {RADIUS['control']}px; }}
    QListWidget::item:hover {{ background: #EDF2F4; }}
    QListWidget::item:selected {{ background: {COLORS['accent_soft']}; color: {COLORS['text']}; }}
    QWidget#Sidebar QListWidget {{ color: #DDE7EC; }}
    QWidget#Sidebar QListWidget::item:hover {{ background: {COLORS['sidebar_hover']}; }}
    QWidget#Sidebar QListWidget::item:selected {{
        background: {COLORS['sidebar_selected']}; color: white;
    }}
    QPushButton {{
        min-height: 34px; padding: 0 12px; border: 1px solid {COLORS['border']};
        border-radius: {RADIUS['control']}px; background: {COLORS['surface']};
    }}
    QPushButton:hover {{ background: {COLORS['surface_alt']}; }}
    QPushButton#PrimaryButton {{
        color: white; background: {COLORS['accent']}; border-color: {COLORS['accent']};
    }}
    QWidget#Sidebar QPushButton {{ color: white; background: {COLORS['sidebar_selected']};
        border-color: #416579; }}
    QPushButton:focus, QLineEdit:focus, QListWidget:focus {{
        border: 2px solid {COLORS['focus']};
    }}
    QLineEdit {{
        min-height: 36px; padding: 0 10px; background: white;
        border: 1px solid {COLORS['border']}; border-radius: {RADIUS['control']}px;
    }}
    QLineEdit[validationError="true"] {{ border: 1px solid {COLORS['error']}; }}
    QSplitter::handle {{ background: {COLORS['border']}; width: 1px; }}
    QStatusBar {{ background: {COLORS['surface_alt']}; color: {COLORS['muted']}; }}
    """
