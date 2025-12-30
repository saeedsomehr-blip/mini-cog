from __future__ import annotations


def build_stylesheet(rtl: bool = False) -> str:
    # Global palette (light, neutral, clean)
    colors = {
        "bg": "#f5f6f8",
        "surface": "#ffffff",
        "text": "#1f2430",
        "muted": "#5f6b7a",
        "primary": "#2f6fed",
        "primary_hover": "#255fda",
        "primary_pressed": "#1f51c1",
        "border": "#d9dde5",
        "shadow": "#00000020",
        "success": "#22a06b",
        "danger": "#d64545",
    }

    line_edit_alignment = "AlignLeading"
    return f"""
    /* Base */
    QWidget {{
        color: {colors["text"]};
        background: transparent;
        font-size: 13px;
    }}
    QMainWindow {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 {colors["bg"]},
            stop: 1 #eef1f6
        );
    }}

    /* Containers */
    QFrame, QGroupBox {{
        background: {colors["surface"]};
        border: 1px solid {colors["border"]};
        border-radius: 10px;
    }}
    QGroupBox {{
        margin-top: 8px;
        padding: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 6px;
        color: {colors["muted"]};
    }}

    /* Buttons */
    QPushButton {{
        background: {colors["primary"]};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 6px 12px;
    }}
    QPushButton:hover {{
        background: {colors["primary_hover"]};
    }}
    QPushButton:pressed {{
        background: {colors["primary_pressed"]};
    }}
    QPushButton:disabled {{
        background: #a9b6cf;
        color: #f4f6fb;
    }}

    /* Inputs */
    QLineEdit {{
        background: {colors["surface"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
        padding: 6px 8px;
        selection-background-color: {colors["primary"]};
        qproperty-alignment: {line_edit_alignment};
    }}
    QLineEdit:focus {{
        border-color: {colors["primary"]};
    }}

    /* Labels */
    QLabel {{
        color: {colors["text"]};
    }}
    QLabel#muted {{
        color: {colors["muted"]};
    }}

    /* Scrollbars (subtle) */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: #c9d0dd;
        border-radius: 5px;
        min-height: 20px;
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """
