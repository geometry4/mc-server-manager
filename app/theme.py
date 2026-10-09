from __future__ import annotations

FONT_FAMILY = '"SF Pro Text", "Segoe UI Variable Text", "Segoe UI", "Microsoft YaHei UI", sans-serif'
MONO_FAMILY = '"SF Mono", "Cascadia Mono", "Consolas", "Courier New", monospace'

SURFACE = "#f5f5f7"
CARD = "#ffffff"
TEXT_PRIMARY = "#1d1d1f"
TEXT_SECONDARY = "#86868b"
ACCENT = "#0071e3"
ACCENT_HOVER = "#0077ed"
ACCENT_PRESSED = "#006edb"
DANGER_TEXT = "#d70015"
LOG_BACKGROUND = "#1c1c1e"
LOG_TEXT = "#f5f5f7"

STATUS_COLORS = {
    "running": "#34c759",
    "starting": "#ff9f0a",
    "stopping": "#ff9f0a",
    "stopped": "#c7c7cc",
    "crashed": "#ff3b30",
    "unknown-external-process": "#ff9f0a",
}


def status_color(state: str) -> str:
    return STATUS_COLORS.get(state, STATUS_COLORS["stopped"])


def build_stylesheet() -> str:
    return f"""
QMainWindow, QWidget#Root {{
    background-color: {SURFACE};
}}

QWidget {{
    font-family: {FONT_FAMILY};
    font-size: 13px;
    color: {TEXT_PRIMARY};
}}

QFrame[card="true"] {{
    background-color: {CARD};
    border: 1px solid rgba(0, 0, 0, 0.07);
    border-radius: 16px;
}}

QFrame#StatusPill {{
    background-color: {CARD};
    border: 1px solid rgba(0, 0, 0, 0.07);
    border-radius: 999px;
}}

QFrame#StatusDot {{
    border: none;
    border-radius: 5px;
    background-color: {STATUS_COLORS['stopped']};
}}

QLabel[role="appTitle"] {{
    font-size: 20px;
    font-weight: 600;
}}

QLabel[role="appSubtitle"] {{
    font-size: 12px;
    color: {TEXT_SECONDARY};
}}

QLabel[role="cardTitle"] {{
    font-size: 11px;
    font-weight: 500;
    color: {TEXT_SECONDARY};
}}

QLabel[role="cardValue"] {{
    font-size: 24px;
    font-weight: 600;
}}

QLabel[role="cardUnit"] {{
    font-size: 12px;
    color: {TEXT_SECONDARY};
}}

QLabel[role="statusText"] {{
    font-size: 13px;
    font-weight: 600;
}}

QLabel[role="detailKey"] {{
    font-size: 11px;
    color: {TEXT_SECONDARY};
}}

QLabel[role="detailValue"] {{
    font-size: 13px;
    font-weight: 500;
}}

QLabel[role="sectionTitle"] {{
    font-size: 13px;
    font-weight: 600;
}}

QLabel[role="message"] {{
    background-color: {CARD};
    border: 1px solid rgba(0, 0, 0, 0.07);
    border-radius: 12px;
    padding: 10px 14px;
    font-size: 12px;
    color: #3a3a3c;
}}

QPushButton {{
    border: none;
    border-radius: 999px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton[kind="primary"] {{
    background-color: {ACCENT};
    color: #ffffff;
}}

QPushButton[kind="primary"]:hover {{
    background-color: {ACCENT_HOVER};
}}

QPushButton[kind="primary"]:pressed {{
    background-color: {ACCENT_PRESSED};
}}

QPushButton[kind="primary"]:disabled {{
    background-color: #e8e8ed;
    color: #a1a1a6;
}}

QPushButton[kind="secondary"] {{
    background-color: {CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid rgba(0, 0, 0, 0.12);
}}

QPushButton[kind="secondary"]:hover {{
    background-color: #fbfbfd;
}}

QPushButton[kind="secondary"]:pressed {{
    background-color: #f0f0f3;
}}

QPushButton[kind="secondary"]:disabled {{
    background-color: #f2f2f5;
    color: #a1a1a6;
    border: 1px solid rgba(0, 0, 0, 0.06);
}}

QPushButton[kind="danger"] {{
    background-color: rgba(255, 59, 48, 0.10);
    color: {DANGER_TEXT};
}}

QPushButton[kind="danger"]:hover {{
    background-color: rgba(255, 59, 48, 0.18);
}}

QPushButton[kind="danger"]:pressed {{
    background-color: rgba(255, 59, 48, 0.24);
}}

QPushButton[kind="danger"]:disabled {{
    background-color: #f2f2f5;
    color: #a1a1a6;
}}

QPlainTextEdit#LogView {{
    background-color: {LOG_BACKGROUND};
    color: {LOG_TEXT};
    border: none;
    border-radius: 14px;
    padding: 14px;
    font-family: {MONO_FAMILY};
    font-size: 12px;
    selection-background-color: #0a84ff;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: rgba(0, 0, 0, 0.20);
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(0, 0, 0, 0.34);
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: rgba(0, 0, 0, 0.20);
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    height: 0;
}}

QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

QPlainTextEdit#LogView QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.24);
}}

QPlainTextEdit#LogView QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.40);
}}
"""
