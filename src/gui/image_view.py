# src/gui/image_view.py
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from PIL import Image

from PySide6.QtCore import Qt, QRect, QPoint, Signal, QSize
from PySide6.QtGui import QPainter, QPixmap, QImage, QPen
from PySide6.QtWidgets import QWidget


@dataclass
class ViewState:
    scale: float = 1.0
    offset: QPoint = QPoint(0, 0)


class ImageView(QWidget):
    sample_requested = Signal(int, int, int, str)  # x_img, y_img, spot, mode

    def __init__(self):
        super().__init__()

        self.state = ViewState()
        self._pixmap: QPixmap | None = None
        self.image_array: np.ndarray | None = None

        self._has_mouse = False
        self._mouse_pos = QPoint(0, 0)

        self._panning = False
        self._pan_anchor = QPoint(0, 0)
        self._pan_offset_anchor = QPoint(0, 0)

        self.spot_size = 31
        self.mode = "average"

        # lens
        self.lens_enabled = True
        self.lens_size = 200
        self.lens_roi = 41

        # space-pan
        self._space_down = False

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    # -------- API called by MainWindow
    def load_image(self, path: str):
        img = Image.open(path).convert("RGB")
        arr = np.array(img, dtype=np.uint8)
        self.image_array = arr

        h, w = arr.shape[:2]
        qimg = QImage(arr.data, w, h, 3 * w, QImage.Format_RGB888).copy()
        self._pixmap = QPixmap.fromImage(qimg)

        # reset view + fit
        self.state.scale = 1.0
        self.state.offset = QPoint(0, 0)
        self.fit_to_window()
        self.update()

    def set_spot_size(self, v: int):
        self.spot_size = int(v)
        self.update()

    def set_mode(self, mode: str):
        self.mode = mode
        self.update()

    def reset_view(self):
        self.state.scale = 1.0
        self.state.offset = QPoint(0, 0)
        self.update()

    # -------- Programmatic navigation (buttons / shortcuts)
    def zoom_in(self):
        self._zoom_at_view_point(self.rect().center(), 1.15)

    def zoom_out(self):
        self._zoom_at_view_point(self.rect().center(), 1 / 1.15)

    def pan_by(self, dx: int, dy: int):
        self.state.offset = self.state.offset + QPoint(int(dx), int(dy))
        self.update()

    def fit_to_window(self):
        """
        Fit dell’immagine nel widget (mantiene aspect ratio) e centra.
        """
        if self._pixmap is None:
            return
        vw, vh = self.width(), self.height()
        if vw <= 0 or vh <= 0:
            return

        iw, ih = self._pixmap.width(), self._pixmap.height()
        if iw <= 0 or ih <= 0:
            return

        scale = min(vw / iw, vh / ih)
        self.state.scale = max(0.05, min(20.0, float(scale)))

        draw_w = int(iw * self.state.scale)
        draw_h = int(ih * self.state.scale)
        self.state.offset = QPoint((vw - draw_w) // 2, (vh - draw_h) // 2)
        self.update()

    def _zoom_at_view_point(self, view_pt: QPoint, factor: float):
        """
        Zoom rispetto a un punto in coordinate view.
        """
        if self._pixmap is None:
            return

        img_pt = self._to_image(view_pt.x(), view_pt.y())
        old_scale = float(self.state.scale)
        self.state.scale = max(0.05, min(20.0, float(self.state.scale) * float(factor)))
        if self.state.scale == old_scale:
            self.update()
            return

        if img_pt is None:
            self.update()
            return

        x_img, y_img = img_pt
        new_view = self._to_view(x_img, y_img)
        self.state.offset += (view_pt - new_view)
        self.update()

    # -------- Coordinate transforms
    def _to_image(self, x_view: int, y_view: int):
        if self._pixmap is None or self.image_array is None:
            return None

        x = (x_view - self.state.offset.x())
        y = (y_view - self.state.offset.y())
        if self.state.scale <= 0:
            return None

        x_img = int(x / self.state.scale)
        y_img = int(y / self.state.scale)

        h, w = self.image_array.shape[:2]
        if x_img < 0 or y_img < 0 or x_img >= w or y_img >= h:
            return None
        return x_img, y_img

    def _to_view(self, x_img: int, y_img: int) -> QPoint:
        x_view = int(x_img * self.state.scale) + self.state.offset.x()
        y_view = int(y_img * self.state.scale) + self.state.offset.y()
        return QPoint(x_view, y_view)

    # -------- Keyboard (space-pan)
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space:
            self._space_down = True
            e.accept()
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space:
            self._space_down = False
            e.accept()
            return
        super().keyReleaseEvent(e)

    # -------- Mouse / wheel
    def mouseMoveEvent(self, e):
        self._mouse_pos = e.position().toPoint()
        self._has_mouse = True

        if self._panning:
            delta = self._mouse_pos - self._pan_anchor
            self.state.offset = self._pan_offset_anchor + delta
            self.update()
            return

        self.update()

    def mousePressEvent(self, e):
        self.setFocus(Qt.MouseFocusReason)

        # PAN: Space + left drag
        if e.button() == Qt.LeftButton and self._space_down:
            self._panning = True
            self._pan_anchor = e.position().toPoint()
            self._pan_offset_anchor = QPoint(self.state.offset)
            e.accept()
            return

        # SAMPLE: left click
        if e.button() == Qt.LeftButton:
            img_pt = self._to_image(e.position().x(), e.position().y())
            if img_pt is None:
                return
            x_img, y_img = img_pt
            self.sample_requested.emit(x_img, y_img, self.spot_size, self.mode)
            e.accept()
            return

        # PAN: right drag
        if e.button() == Qt.RightButton:
            self._panning = True
            self._pan_anchor = e.position().toPoint()
            self._pan_offset_anchor = QPoint(self.state.offset)
            e.accept()
            return

    def mouseReleaseEvent(self, e):
        if e.button() in (Qt.LeftButton, Qt.RightButton):
            self._panning = False
            e.accept()
            return

    def wheelEvent(self, e):
        if self._pixmap is None:
            return

        # Trackpad: pixelDelta spesso è più affidabile
        dy = e.pixelDelta().y()
        if dy == 0:
            dy = e.angleDelta().y()
        if dy == 0:
            return

        factor = 1.15 if dy > 0 else 1 / 1.15

        mouse = e.position().toPoint()
        img_pt = self._to_image(mouse.x(), mouse.y())

        # se fuori immagine, zoom sul centro
        anchor = mouse if img_pt is not None else self.rect().center()
        self._zoom_at_view_point(anchor, factor)

    def enterEvent(self, e):
        self._has_mouse = True
        self.update()

    def leaveEvent(self, e):
        self._has_mouse = False
        self.update()

    def resizeEvent(self, e):
        # opzionale: se vuoi mantenere un fit automatico al resize, sblocca questa riga
        # self.fit_to_window()
        super().resizeEvent(e)

    # -------- Painting
    def paintEvent(self, e):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            p.fillRect(self.rect(), Qt.black)

            if self._pixmap is None:
                p.setPen(Qt.white)
                p.drawText(self.rect(), Qt.AlignCenter, "Apri un’immagine per iniziare")
                return

            scaled = self._pixmap.scaled(
                int(self._pixmap.width() * self.state.scale),
                int(self._pixmap.height() * self.state.scale),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            p.drawPixmap(self.state.offset, scaled)

            if self._has_mouse:
                img_pt = self._to_image(self._mouse_pos.x(), self._mouse_pos.y())
                if img_pt is not None:
                    xi, yi = img_pt
                    center = self._to_view(xi, yi)

                    pen = QPen(Qt.white)
                    pen.setWidth(1)
                    p.setPen(pen)
                    p.drawLine(0, center.y(), self.width(), center.y())
                    p.drawLine(center.x(), 0, center.x(), self.height())

                    half = self.spot_size // 2
                    top_left = self._to_view(xi - half, yi - half)
                    size = int(self.spot_size * self.state.scale)
                    p.drawRect(QRect(top_left, QSize(size, size)))

                    if self.lens_enabled:
                        try:
                            self._draw_lens(p, xi, yi)
                        except Exception:
                            pass
        finally:
            p.end()

    def _draw_lens(self, p: QPainter, xi: int, yi: int):
        if self.image_array is None:
            return

        h, w = self.image_array.shape[:2]
        half = self.lens_roi // 2
        x0 = max(0, xi - half)
        y0 = max(0, yi - half)
        x1 = min(w, xi + half + 1)
        y1 = min(h, yi + half + 1)
        roi = self.image_array[y0:y1, x0:x1, :]

        roi_h, roi_w = roi.shape[:2]
        if roi_w <= 0 or roi_h <= 0:
            return

        roi = roi[:, :, :3]
        roi = np.ascontiguousarray(roi, dtype=np.uint8)
        roi_h, roi_w = roi.shape[:2]
        bytes_per_line = int(roi.strides[0])

        qimg = QImage(roi.data, roi_w, roi_h, bytes_per_line, QImage.Format_RGB888).copy()
        pm = QPixmap.fromImage(qimg).scaled(
            self.lens_size, self.lens_size, Qt.KeepAspectRatio, Qt.FastTransformation
        )

        margin = 14
        x = self.width() - pm.width() - margin
        y = margin
        p.setPen(QPen(Qt.white, 2))
        p.drawRect(QRect(x - 1, y - 1, pm.width() + 2, pm.height() + 2))
        p.drawPixmap(x, y, pm)