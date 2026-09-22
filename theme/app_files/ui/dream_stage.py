"""
Dream stage: the animated centerpiece of the main window.

Shows a QMovie (the idle star or a Yume Nikki dancer while downloading) over a
soft glow with twinkling four-point sparkles drifting upward. Downloading
("dreaming") mode uses more, brighter sparkles. Drop-in replacement for the
QLabel the UI state manager calls `setMovie` on.
"""

import math
import random
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QMovie, QPainter, QPainterPath, QPixmap, QRadialGradient
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ui.theme import mix, tokens

IDLE_SPARKLES = 10
DREAM_SPARKLES = 34


@dataclass
class Sparkle:
    x: float  # 0..1 across the widget
    y: float  # 0..1 down the widget
    size: float
    speed: float
    phase: float
    tone: int  # 0 accent, 1 dream, 2 white


def _star_path(cx: float, cy: float, r: float) -> QPainterPath:
    """Four-point sparkle with pinched sides."""
    k = r * 0.22
    path = QPainterPath(QPointF(cx, cy - r))
    path.quadTo(cx + k, cy - k, cx + r, cy)
    path.quadTo(cx + k, cy + k, cx, cy + r)
    path.quadTo(cx - k, cy + k, cx - r, cy)
    path.quadTo(cx - k, cy - k, cx, cy - r)
    return path


class DreamStage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._movie: Optional[QMovie] = None
        self._dreaming = False
        self._t = 0.0
        self._sparkles: List[Sparkle] = []
        self._reseed(IDLE_SPARKLES)

        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

    # --- QLabel-compatible surface used by the UI state manager -------------
    def setMovie(self, movie: Optional[QMovie]) -> None:
        if self._movie is movie:
            return
        if self._movie is not None:
            try:
                self._movie.frameChanged.disconnect(self._on_frame)
            except TypeError:
                pass
        self._movie = movie
        if movie is not None:
            movie.frameChanged.connect(self._on_frame)
        self.update()

    def movie(self) -> Optional[QMovie]:
        return self._movie

    def setAlignment(self, _alignment) -> None:
        """Content is always centered; kept for QLabel API compatibility."""

    # --- Dream mode ----------------------------------------------------------
    def set_dreaming(self, dreaming: bool) -> None:
        if dreaming == self._dreaming:
            return
        self._dreaming = dreaming
        self._reseed(DREAM_SPARKLES if dreaming else IDLE_SPARKLES)
        self.update()

    def is_dreaming(self) -> bool:
        return self._dreaming

    def _reseed(self, count: int) -> None:
        rnd = random.Random()
        self._sparkles = [
            Sparkle(
                x=rnd.random(),
                y=rnd.random(),
                size=rnd.uniform(3.0, 9.0 if self._dreaming else 6.0),
                speed=rnd.uniform(0.012, 0.04),
                phase=rnd.uniform(0, math.tau),
                tone=rnd.choice((0, 1, 1, 2)),
            )
            for _ in range(count)
        ]

    # --- Animation -----------------------------------------------------------
    def showEvent(self, event) -> None:
        self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def _on_frame(self, _frame: int) -> None:
        self.update()

    def _tick(self) -> None:
        dt = self._timer.interval() / 1000.0
        self._t += dt
        boost = 1.8 if self._dreaming else 1.0
        for s in self._sparkles:
            s.y -= s.speed * dt * boost
            if s.y < -0.05:
                s.y = 1.05
                s.x = random.random()
        self.update()

    # --- Painting ------------------------------------------------------------
    def _frame_pixmap(self, box: QRectF) -> Optional[QPixmap]:
        if self._movie is None or not self._movie.isValid():
            return None
        frame = self._movie.currentPixmap()
        if frame.isNull():
            return None

        fw, fh = frame.width(), frame.height()
        scale = min(box.width() / fw, box.height() / fh)
        if max(fw, fh) < 160:
            # Pixel art: integer scaling keeps the pixels crisp
            scale = max(1, math.floor(scale))
            mode = Qt.TransformationMode.FastTransformation
        else:
            mode = Qt.TransformationMode.SmoothTransformation
        return frame.scaled(
            max(1, int(fw * scale)),
            max(1, int(fh * scale)),
            Qt.AspectRatioMode.KeepAspectRatio,
            mode,
        )

    def paintEvent(self, event) -> None:
        t = tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        center = QPointF(w / 2, h / 2)

        # Soft glow behind the character
        radius = min(w, h) * (0.55 if self._dreaming else 0.45)
        pulse = 0.5 + 0.5 * math.sin(self._t * 1.6)
        glow = QRadialGradient(center, radius)
        inner = QColor(t.dream)
        inner.setAlpha(int((90 if self._dreaming else 45) + 30 * pulse))
        mid = QColor(t.accent)
        mid.setAlpha(22 if self._dreaming else 10)
        edge = QColor(t.bg)
        edge.setAlpha(0)
        glow.setColorAt(0.0, inner)
        glow.setColorAt(0.55, mid)
        glow.setColorAt(1.0, edge)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(center, radius, radius)

        # Sparkles
        tones = (t.accent, mix(t.dream, t.accent, 0.7), QColor("#FFFFFF"))
        for s in self._sparkles:
            twinkle = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(self._t * 3.0 + s.phase))
            color = QColor(tones[s.tone])
            color.setAlphaF(min(1.0, twinkle * (0.95 if self._dreaming else 0.55)))
            painter.setBrush(color)
            r = s.size * (0.75 + 0.25 * twinkle)
            painter.drawPath(_star_path(s.x * w, s.y * h, r))

        # Character / main animation
        box_h = h * (0.62 if self._dreaming else 0.9)
        box = QRectF(0, 0, w * 0.9, box_h)
        pixmap = self._frame_pixmap(box)
        if pixmap is not None:
            bob = 3.0 * math.sin(self._t * 2.2) if self._dreaming else 0.0
            x = (w - pixmap.width()) / 2
            y = (h - pixmap.height()) / 2 + bob
            painter.drawPixmap(QPointF(x, y), pixmap)

        painter.end()
