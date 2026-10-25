"""Zoomable and pannable image viewer with interactive card bounding-box overlays."""

from __future__ import annotations
from typing import List, Optional, Tuple
import cv2
import numpy as np
from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import QFrame, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QWidget

from app.vision.card_recognizer import DetectedCard


class ZoomableImageViewer(QGraphicsView):
    """High-performance graphics view supporting smooth zooming, panning, and card bounding box overlays."""

    box_clicked = Signal(int)  # Emits index of clicked card bounding box

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._detected_cards: List[DetectedCard] = []
        self._current_image: Optional[np.ndarray] = None
        self._zoom_factor: float = 1.0

        # UI Styling
        self.setFrameShape(QFrame.NoFrame)
        self.setBackgroundBrush(QColor("#141414"))
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def set_image(self, bgr_image: np.ndarray, detected_cards: List[DetectedCard] | None = None) -> None:
        """Loads and displays an OpenCV BGR image with optional detected card boxes."""
        self._current_image = bgr_image
        self._detected_cards = detected_cards or []
        self._scene.clear()

        h, w, ch = bgr_image.shape
        bytes_per_line = ch * w
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(0, 0, w, h)

        # Draw bounding boxes if any
        self._draw_bounding_boxes()

        # Fit image comfortably inside view initially
        self.fit_in_view()

    def _draw_bounding_boxes(self) -> None:
        """Overlays detected card polygons/rectangles, IDs, and dual confidence badges."""
        font = QFont(".AppleSystemUIFont", 11, QFont.Bold)

        for idx, det in enumerate(self._detected_cards):
            x, y, w, h = det.bbox

            # Color coding based on status and confidence
            if det.is_verified or det.is_reference_match:
                border_color = QColor("#0A84FF")  # Apple Blue
                fill_color = QColor(10, 132, 255, 35)
            elif det.is_uncertain or det.confidence < 0.65:
                border_color = QColor("#FF9F0A")  # Apple Orange
                fill_color = QColor(255, 159, 10, 35)
            else:
                border_color = QColor("#30D158")  # Apple Green
                fill_color = QColor(48, 209, 88, 35)

            pen = QPen(border_color, 2)

            # Draw 4-point polygon if available, else rectangle
            if len(det.polygon) == 4:
                from PySide6.QtGui import QPolygonF
                from PySide6.QtCore import QPointF
                poly_item = self._scene.addPolygon(
                    QPolygonF([QPointF(pt[0], pt[1]) for pt in det.polygon]),
                    pen,
                    fill_color,
                )
            else:
                self._scene.addRect(x, y, w, h, pen, fill_color)

            # Build label text: [ID] CardName (det: X%, rec: Y%)
            tag_text = det.card.unicode_name if det.card else "?"
            det_pct = int(det.detection_confidence * 100)
            rec_pct = int(det.confidence * 100)
            det_label = f"#{idx+1} {tag_text} (det:{det_pct}% rec:{rec_pct}%)"

            # Background pill for badge readability
            badge_bg = self._scene.addRect(
                x, max(0, y - 22), max(110, w), 20,
                QPen(Qt.NoPen),
                QColor(20, 20, 20, 210),
            )
            badge_text = self._scene.addSimpleText(det_label, font)
            badge_text.setBrush(border_color)
            badge_text.setPos(x + 4, max(1, y - 20))

    def mousePressEvent(self, event) -> None:
        """Emits box_clicked with card index when user clicks on a detected card overlay."""
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            sx, sy = scene_pos.x(), scene_pos.y()

            # Check if clicked point is inside any detected card bbox
            for idx, det in enumerate(self._detected_cards):
                x, y, w, h = det.bbox
                if x <= sx <= x + w and y <= sy <= y + h:
                    self.box_clicked.emit(idx)
                    event.accept()
                    return

        super().mousePressEvent(event)

    def fit_in_view(self) -> None:
        """Scales view to fit image within the current viewport."""
        if self._pixmap_item:
            self.resetTransform()
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
            self._zoom_factor = 1.0

    def zoom_in(self) -> None:
        """Zooms into the image by 25%."""
        self.scale(1.25, 1.25)
        self._zoom_factor *= 1.25

    def zoom_out(self) -> None:
        """Zooms out of the image by 20%."""
        self.scale(0.8, 0.8)
        self._zoom_factor *= 0.8

    def zoom_actual_size(self) -> None:
        """Resets zoom to 100% 1:1 pixel mapping."""
        self.resetTransform()
        self._zoom_factor = 1.0

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Smooth mouse-wheel and trackpad pinch zooming."""
        if event.modifiers() & Qt.ControlModifier or True:
            angle = event.angleDelta().y()
            if angle > 0:
                self.zoom_in()
            elif angle < 0:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)
