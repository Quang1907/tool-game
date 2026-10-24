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
        """Overlays detected card rectangles and text tags on top of image."""
        font = QFont("SF Pro Text", 12, QFont.Bold)

        for idx, det in enumerate(self._detected_cards):
            x, y, w, h = det.bbox
            rect_item = self._scene.addRect(
                x, y, w, h,
                QPen(QColor("#30D158") if det.confidence >= 0.70 else QColor("#FF9F0A"), 2),
                QColor(48, 209, 88, 30) if det.confidence >= 0.70 else QColor(255, 159, 10, 30),
            )

            # Label text
            tag_text = det.card.unicode_name if det.card else "?"
            tag_item = self._scene.addSimpleText(f"#{idx+1} {tag_text}", font)
            tag_item.setBrush(QColor("#FFFFFF"))
            tag_item.setPos(x + 4, max(0, y - 20))

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
