from __future__ import annotations

import math

from dataclasses import dataclass
from typing import Dict, Tuple, Optional

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QIntValidator, QFont, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
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


@dataclass
class HistoryAction:
    action: str
    number: int
    prev_center: Optional[QPointF]
    prev_index: Optional[int]


_CLOCK_NUMBER_FONT = QFont("Segoe UI", 28, QFont.Bold)


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
        self._order: list[int] = []
        self._history: list[HistoryAction] = []
        self._erase_mode: bool = False
        self._mode: str = "numbers"
        self._hand_target: str = "minute"
        self._minute_angle: Optional[float] = None
        self._hour_angle: Optional[float] = None
        self._minute_item: Optional[QGraphicsLineItem] = None
        self._hour_item: Optional[QGraphicsLineItem] = None

        # Fit the logical scene in the view
        self._scene.setSceneRect(-260, -260, 520, 520)
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def mousePressEvent(self, event) -> None:
        if self._mode == "hands" and event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self._set_hand_at(scene_pos)
            return

        if self._erase_mode and self._mode == "numbers" and event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            number = self._find_number_at(scene_pos)
            if number is not None:
                self._remove_number(number, record=True)
            return

        # If an editor is active, allow quick reposition and continue entry
        if self._active_editor is not None:
            if event.button() == Qt.LeftButton:
                text = self._active_editor.text().strip()
                if text == "":
                    scene_pos = self.mapToScene(event.pos())
                    self._discard_active_editor()
                    self.open_editor_at(scene_pos)
                    return
                scene_pos = self.mapToScene(event.pos())
                self._commit_active_editor()
                self.open_editor_at(scene_pos)
                return
            super().mousePressEvent(event)
            return

        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            if not self._erase_mode:
                self.open_editor_at(scene_pos)
            return

        super().mousePressEvent(event)

    def open_editor_at(self, scene_pos: QPointF) -> None:
        # Create an inline editor at the exact clicked position
        if self._active_editor is not None or self._erase_mode or self._mode != "numbers":
            return

        editor = QLineEdit()
        editor.setMaxLength(2)
        editor.setAlignment(Qt.AlignCenter)

        # Allow only 1..12; still validate on commit
        editor.setValidator(QIntValidator(1, 12, editor))
        editor.setFont(QFont(_CLOCK_NUMBER_FONT))

        w, h = 72, 52
        editor.setStyleSheet(
            "QLineEdit { font-size: 28pt; font-weight: 600; qproperty-alignment: AlignCenter; }"
        )
        editor.setFixedSize(w, h)

        proxy = self._scene.addWidget(editor)
        proxy.setZValue(10)

        # Position the editor centered at click position
        proxy.setPos(scene_pos.x() - w / 2.0, scene_pos.y() - h / 2.0)

        self._active_editor = editor
        self._active_proxy = proxy
        self._active_click_pos = scene_pos
        self._committed = False

        editor.returnPressed.connect(self.commit_and_reopen)
        editor.editingFinished.connect(self.commit_editor)

        editor.setFocus()

    def _discard_active_editor(self) -> None:
        # Close the editor without committing a number
        if self._active_proxy is not None:
            self._scene.removeItem(self._active_proxy)
        self._active_proxy = None
        self._active_editor = None
        self._active_click_pos = None
        self._committed = True

    def _commit_active_editor(self) -> Optional[QPointF]:
        # Commit the active editor into a placed number item
        if self._active_editor is None or self._active_proxy is None or self._active_click_pos is None:
            return None
        if self._committed:
            return None
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
            return click_pos

        try:
            value = int(raw)
        except ValueError:
            return click_pos

        if value < 1 or value > 12:
            return click_pos

        self._place_number(value=value, click_pos=click_pos, record=True)
        return click_pos

    def commit_editor(self) -> None:
        sender = self.sender()
        if sender is not None and sender is not self._active_editor:
            return
        self._commit_active_editor()

    def commit_and_reopen(self) -> None:
        click_pos = self._commit_active_editor()
        if click_pos is not None:
            self.open_editor_at(click_pos)

    def _create_text_item(self, value: int) -> QGraphicsTextItem:
        item = QGraphicsTextItem(str(value))
        item.setZValue(5)
        font = QFont(_CLOCK_NUMBER_FONT)
        item.setFont(font)
        self._scene.addItem(item)
        return item

    def _set_item_center(self, item: QGraphicsTextItem, center: QPointF) -> None:
        br = item.boundingRect()
        item.setPos(center.x() - br.width() / 2.0, center.y() - br.height() / 2.0)

    def _place_number(self, value: int, click_pos: QPointF, record: bool) -> None:
        prev_center = None
        prev_index = None
        if value in self._placed:
            prev_center = self._placed[value].center
            prev_index = self._order.index(value) if value in self._order else None
            item = self._placed[value].text_item
            item.setPlainText(str(value))
        else:
            item = self._create_text_item(value)

        self._set_item_center(item, click_pos)
        self._placed[value] = PlacedNumberItem(center=click_pos, text_item=item)

        if value in self._order:
            self._order.remove(value)
        self._order.append(value)

        if record:
            self._history.append(
                HistoryAction(
                    action="place",
                    number=value,
                    prev_center=prev_center,
                    prev_index=prev_index,
                )
            )

    def _remove_number(self, value: int, record: bool) -> None:
        if value not in self._placed:
            return
        prev_center = self._placed[value].center
        prev_index = self._order.index(value) if value in self._order else None

        self._scene.removeItem(self._placed[value].text_item)
        del self._placed[value]
        if value in self._order:
            self._order.remove(value)

        if record:
            self._history.append(
                HistoryAction(
                    action="delete",
                    number=value,
                    prev_center=prev_center,
                    prev_index=prev_index,
                )
            )

    def _find_number_at(self, scene_pos: QPointF) -> Optional[int]:
        # Find a placed number text item under the cursor, if any
        for item in self._scene.items(scene_pos):
            if not isinstance(item, QGraphicsTextItem):
                continue
            for number, placed in self._placed.items():
                if placed.text_item is item:
                    return number
        return None

    def set_erase_mode(self, enabled: bool) -> None:
        if self._erase_mode == enabled:
            return
        self._erase_mode = enabled
        if enabled:
            self._discard_active_editor()

    def toggle_erase_mode(self) -> bool:
        self.set_erase_mode(not self._erase_mode)
        return self._erase_mode

    def is_erase_mode(self) -> bool:
        return self._erase_mode

    def set_mode(self, mode: str) -> None:
        if mode not in ("numbers", "hands"):
            raise ValueError(f"Unsupported mode: {mode}")
        if self._mode == mode:
            return
        self._mode = mode
        if mode == "hands":
            self.set_erase_mode(False)
            self._discard_active_editor()
            self._hand_target = "minute"

    def get_mode(self) -> str:
        return self._mode

    def reset_hands(self) -> None:
        if self._minute_item is not None:
            self._scene.removeItem(self._minute_item)
        if self._hour_item is not None:
            self._scene.removeItem(self._hour_item)
        self._minute_item = None
        self._hour_item = None
        self._minute_angle = None
        self._hour_angle = None
        self._hand_target = "minute"

    def get_hand_angles(self) -> Tuple[Optional[float], Optional[float]]:
        return self._minute_angle, self._hour_angle

    def _set_hand_at(self, scene_pos: QPointF) -> None:
        dx = scene_pos.x() - self._center.x()
        dy = scene_pos.y() - self._center.y()
        if dx == 0 and dy == 0:
            return

        angle = math.degrees(math.atan2(-dy, dx)) % 360
        if self._hand_target == "minute":
            self._minute_angle = angle
            self._minute_item = self._draw_hand(angle, length_ratio=0.85, width=3, item=self._minute_item)
            self._hand_target = "hour"
        else:
            self._hour_angle = angle
            self._hour_item = self._draw_hand(angle, length_ratio=0.6, width=5, item=self._hour_item)
            self._hand_target = "minute"

    def _draw_hand(
        self,
        angle_deg: float,
        length_ratio: float,
        width: int,
        item: Optional[QGraphicsLineItem],
    ) -> QGraphicsLineItem:
        r = self._radius * length_ratio
        rad = math.radians(angle_deg)
        end_x = self._center.x() + math.cos(rad) * r
        end_y = self._center.y() - math.sin(rad) * r
        if item is None:
            item = QGraphicsLineItem()
            self._scene.addItem(item)
        pen = QPen(Qt.black)
        pen.setWidth(width)
        item.setPen(pen)
        item.setLine(self._center.x(), self._center.y(), end_x, end_y)
        item.setZValue(6)
        return item

    def remove_last(self) -> None:
        # Remove the most recently placed number
        if not self._order:
            return
        self._remove_number(self._order[-1], record=True)

    def undo_last(self) -> None:
        # Undo the most recent placement or deletion
        if not self._history:
            return
        action = self._history.pop()

        if action.action == "place":
            if action.prev_center is None:
                self._remove_number(action.number, record=False)
                return

            if action.number not in self._placed:
                item = self._create_text_item(action.number)
                self._placed[action.number] = PlacedNumberItem(center=action.prev_center, text_item=item)

            self._set_item_center(self._placed[action.number].text_item, action.prev_center)
            self._placed[action.number].center = action.prev_center

            if action.number in self._order:
                self._order.remove(action.number)
            if action.prev_index is None or action.prev_index >= len(self._order):
                self._order.append(action.number)
            else:
                self._order.insert(action.prev_index, action.number)
            return

        if action.action == "delete":
            if action.prev_center is None:
                return
            if action.number in self._placed:
                return
            item = self._create_text_item(action.number)
            self._set_item_center(item, action.prev_center)
            self._placed[action.number] = PlacedNumberItem(center=action.prev_center, text_item=item)
            if action.prev_index is None or action.prev_index >= len(self._order):
                self._order.append(action.number)
            else:
                self._order.insert(action.prev_index, action.number)

    def clear_numbers(self) -> None:
        # Remove all placed numbers from the scene
        for v in list(self._placed.keys()):
            self._scene.removeItem(self._placed[v].text_item)
        self._placed.clear()
        self._order.clear()
        self._history.clear()
        self.reset_hands()

    def get_center_and_radius(self) -> Tuple[Tuple[float, float], float]:
        # Return the circle center and radius used by this canvas
        return (self._center.x(), self._center.y()), float(self._radius)

    def get_placed_numbers(self) -> Dict[int, Tuple[float, float]]:
        # Return {number: (x,y)} for evaluation; (x,y) is the intended center point
        return {n: (item.center.x(), item.center.y()) for n, item in self._placed.items()}

    def export_state(self) -> Dict[str, object]:
        # Serialize current drawing state (numbers + hands) for persistence
        placed = self.get_placed_numbers()
        return {
            "mode": self._mode,
            "center": (self._center.x(), self._center.y()),
            "radius": float(self._radius),
            "numbers": placed,
            "minute_angle": self._minute_angle,
            "hour_angle": self._hour_angle,
        }

    def mark_incorrect(self, incorrect_numbers: list[int]) -> None:
        # Simple visual feedback: underline incorrect numbers
        incorrect_set = set(incorrect_numbers)
        for n, item in self._placed.items():
            font = item.text_item.font()
            font.setUnderline(n in incorrect_set)
            item.text_item.setFont(font)
