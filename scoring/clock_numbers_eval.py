from __future__ import annotations

import math

from dataclasses import dataclass
from typing import Dict, Tuple, Optional

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QIntValidator, QFont
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsProxyWidget,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QLineEdit,
)


def _fa_to_en_digits(s: str) -> str:
    # Convert Persian/Arabic-Indic digits to ASCII digits
    persian = "\u06F0\u06F1\u06F2\u06F3\u06F4\u06F5\u06F6\u06F7\u06F8\u06F9"
    arabic = "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669"
    trans = {ord(ch): str(i) for i, ch in enumerate(persian)}
    trans.update({ord(ch): str(i) for i, ch in enumerate(arabic)})
    return s.translate(trans)


@dataclass
class PlacedNumberItem:
    # Stores both the scene center point and the graphics item
    center: QPointF
    text_item: QGraphicsTextItem


class ClockCanvas(QGraphicsView):
    """
    A clock drawing canvas for placing numbers on a pre-drawn circle.

    Behavior:
    - Draw a circle (blank clock face).
    - On left click: open an inline QLineEdit exactly where clicked.
    - Accept only integers 1..12 (max two digits).
    - After commit: place a text item centered at the click position.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Fixed logical coordinate system for stable evaluation
        self._center = QPointF(0.0, 0.0)
        self._radius = 200.0

        # Draw base circle
        self._circle_item = QGraphicsEllipseItem(
            self._center.x() - self._radius,
            self._center.y() - self._radius,
            self._radius * 2.0,
            self._radius * 2.0,
        )
        self._scene.addItem(self._circle_item)

        # Keep the view clean
        self.setRenderHints(self.renderHints())
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Editor state
        self._active_editor: Optional[QLineEdit] = None
        self._active_proxy: Optional[QGraphicsProxyWidget] = None
        self._active_click_pos: Optional[QPointF] = None
        self._committed: bool = False

        # Placed numbers (unique by value). Re-entering a number moves it.
        self._placed: Dict[int, PlacedNumberItem] = {}

        # Fit the logical scene in the view
        self._scene.setSceneRect(-260, -260, 520, 520)
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def mousePressEvent(self, event) -> None:
        # If an editor is active, let it handle focus changes first
        if self._active_editor is not None:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.open_editor_at(scene_pos)
            return

        super().mousePressEvent(event)

    def open_editor_at(self, scene_pos: QPointF) -> None:
        # Create an inline editor at the exact clicked position
        if self._active_editor is not None:
            return

        editor = QLineEdit()
        editor.setMaxLength(2)
        editor.setAlignment(Qt.AlignCenter)

        # Allow only 1..12; still validate on commit
        editor.setValidator(QIntValidator(1, 12, editor))
        editor.setFont(QFont("Segoe UI", 12))

        w, h = 44, 30
        editor.setFixedSize(w, h)

        proxy = self._scene.addWidget(editor)
        proxy.setZValue(10)

        # Position the editor centered at click position
        proxy.setPos(scene_pos.x() - w / 2.0, scene_pos.y() - h / 2.0)

        self._active_editor = editor
        self._active_proxy = proxy
        self._active_click_pos = scene_pos
        self._committed = False

        editor.returnPressed.connect(self.commit_editor)
        editor.editingFinished.connect(self.commit_editor)

        editor.setFocus()

    def commit_editor(self) -> None:
        # Commit the active editor into a placed number item
        if self._active_editor is None or self._active_proxy is None or self._active_click_pos is None:
            return
        if self._committed:
            return
        self._committed = True

        raw = self._active_editor.text().strip()
        raw = _fa_to_en_digits(raw)

        # Remove editor no matter what
        self._scene.removeItem(self._active_proxy)
        self._active_proxy = None
        self._active_editor = None

        click_pos = self._active_click_pos
        self._active_click_pos = None

        if raw == "":
            return

        try:
            value = int(raw)
        except ValueError:
            return

        if value < 1 or value > 12:
            return

        # Create or update the text item for this number
        if value in self._placed:
            item = self._placed[value].text_item
            item.setPlainText(str(value))
        else:
            item = QGraphicsTextItem(str(value))
            item.setZValue(5)
            item.setFont(QFont("Segoe UI", 14))
            self._scene.addItem(item)

        # Center the text on the click position
        br = item.boundingRect()
        item.setPos(click_pos.x() - br.width() / 2.0, click_pos.y() - br.height() / 2.0)

        self._placed[value] = PlacedNumberItem(center=click_pos, text_item=item)

    def clear_numbers(self) -> None:
        # Remove all placed numbers from the scene
        for v in list(self._placed.keys()):
            self._scene.removeItem(self._placed[v].text_item)
        self._placed.clear()

    def get_center_and_radius(self) -> Tuple[Tuple[float, float], float]:
        # Return the circle center and radius used by this canvas
        return (self._center.x(), self._center.y()), float(self._radius)

    def get_placed_numbers(self) -> Dict[int, Tuple[float, float]]:
        # Return {number: (x,y)} for evaluation; (x,y) is the intended center point
        return {n: (item.center.x(), item.center.y()) for n, item in self._placed.items()}

    def mark_incorrect(self, incorrect_numbers: list[int]) -> None:
        # Simple visual feedback: underline incorrect numbers
        incorrect_set = set(incorrect_numbers)
        for n, item in self._placed.items():
            font = item.text_item.font()
            font.setUnderline(n in incorrect_set)
            item.text_item.setFont(font)


_ANCHOR_NUMBERS = {3, 6, 9, 12}


@dataclass(frozen=True)
class ClockEvalConfig:
    r_min_ratio: float
    r_max_ratio: float
    tol_anchor_deg: float
    tol_other_deg: float
    require_all_numbers: bool
    require_all_correct: bool
    enable_quadrant_check: bool


@dataclass
class ClockEvalResult:
    pass_layout: bool
    anchors_ok: bool
    invalid: list[int]
    missing: list[int]
    incorrect: list[int]


def _expected_angle_for_number(number: int) -> float:
    # 12 is at 90°, other numbers follow every -30° clockwise.
    return (90 - (number - 12) * 30) % 360


def _angle_diff(a: float, b: float) -> float:
    diff = abs((a - b + 180) % 360 - 180)
    return diff


def evaluate_clock_numbers(
    placed: Dict[int, Tuple[float, float]],
    center: Tuple[float, float],
    radius: float,
    config: ClockEvalConfig,
) -> ClockEvalResult:
    cx, cy = center
    invalid: list[int] = []
    incorrect: list[int] = []
    anchor_issues: list[int] = []

    for number, (x, y) in placed.items():
        dx = x - cx
        dy = y - cy
        dist = math.hypot(dx, dy)
        ratio = dist / radius if radius > 0 else float("inf")

        if ratio < config.r_min_ratio or ratio > config.r_max_ratio:
            invalid.append(number)
            incorrect.append(number)
            continue

        angle = math.degrees(math.atan2(-dy, dx)) % 360
        expected = _expected_angle_for_number(number)
        diff = _angle_diff(angle, expected)
        tol = config.tol_anchor_deg if number in _ANCHOR_NUMBERS else config.tol_other_deg

        if diff > tol:
            incorrect.append(number)
            if number in _ANCHOR_NUMBERS:
                anchor_issues.append(number)

    missing = [n for n in range(1, 13) if n not in placed]
    anchors_ok = not anchor_issues

    pass_layout = True
    if config.require_all_numbers and missing:
        pass_layout = False
    if config.require_all_correct and incorrect:
        pass_layout = False
    if invalid:
        pass_layout = False

    return ClockEvalResult(
        pass_layout=pass_layout,
        anchors_ok=anchors_ok,
        invalid=invalid,
        missing=missing,
        incorrect=incorrect,
    )
