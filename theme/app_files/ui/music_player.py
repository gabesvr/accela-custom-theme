"""
Aesthetic Frameless Music Player Widget for ACCELA
Features:
- Frameless, seamless integration with pastel Macintosh theme (no container box)
- Real-time CAVA spectrum visualizer with terminal-style sharp rectangular bars
- 100% SVG vector icons (no emojis)
- Dancing Yume Nikki pixel mascot (synchronized with playback, click to switch)
- Scrubber, track navigation, loop toggle, and volume control with mute
"""

import os
import glob
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QByteArray, QRectF
from PyQt6.QtGui import QMovie, QFont, QCursor, QColor, QPainter, QLinearGradient, QIcon, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSizePolicy,
)
from just_playback import Playback

from ui.theme import mix, rgba, tokens

logger = logging.getLogger(__name__)


def make_svg_icon(svg_xml: str, size: int = 24) -> QIcon:
    """Generate a crisp QIcon from an SVG XML string."""
    renderer = QSvgRenderer(QByteArray(svg_xml.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


# Clean, vector SVG definitions (stroke and fills formatted dynamically)
SVG_ICONS = {
    "play": lambda col: f"""<svg viewBox="0 0 24 24" fill="{col}">
        <polygon points="8,4 20,12 8,20" fill="{col}"/>
    </svg>""",

    "pause": lambda col: f"""<svg viewBox="0 0 24 24" fill="{col}">
        <rect x="6" y="4" width="3.5" height="16" rx="1" fill="{col}"/>
        <rect x="14.5" y="4" width="3.5" height="16" rx="1" fill="{col}"/>
    </svg>""",

    "prev": lambda col: f"""<svg viewBox="0 0 24 24" fill="{col}">
        <polygon points="18,19 8,12 18,5" fill="{col}"/>
        <rect x="5" y="5" width="2.2" height="14" rx="0.5" fill="{col}"/>
    </svg>""",

    "next": lambda col: f"""<svg viewBox="0 0 24 24" fill="{col}">
        <polygon points="6,5 16,12 6,19" fill="{col}"/>
        <rect x="16.8" y="5" width="2.2" height="14" rx="0.5" fill="{col}"/>
    </svg>""",

    "loop": lambda col: f"""<svg viewBox="0 0 24 24" fill="none" stroke="{col}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17 2l4 4-4 4"/>
        <path d="M3 11V9a4 4 0 0 1 4-4h14"/>
        <path d="M7 22l-4-4 4-4"/>
        <path d="M21 13v2a4 4 0 0 1-4 4H3"/>
    </svg>""",

    "volume": lambda col: f"""<svg viewBox="0 0 24 24" fill="none" stroke="{col}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" fill="{col}"/>
        <path d="M15.5 8.5a5 5 0 0 1 0 7"/>
        <path d="M19 5a10 10 0 0 1 0 14"/>
    </svg>""",

    "mute": lambda col: f"""<svg viewBox="0 0 24 24" fill="none" stroke="{col}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" fill="{col}"/>
        <line x1="22" y1="9" x2="16" y2="15"/>
        <line x1="16" y1="9" x2="22" y2="15"/>
    </svg>""",
}


class CavaThread(QThread):
    """Background thread reading real-time frequency data from CAVA via PipeWire."""
    bars_updated = pyqtSignal(list)

    def __init__(self, bar_count: int = 54):
        super().__init__()
        self.bar_count = bar_count
        self.running = True
        self.proc = None
        self.cfg_path = None

    def run(self):
        cava_cfg = f"""[general]
bars = {self.bar_count}
framerate = 55

[input]
method = pipewire

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 100
bar_delimiter = 59
frame_delimiter = 10

[smoothing]
monstercat = 1
noise_reduction = 40
"""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".cava") as f:
            f.write(cava_cfg)
            self.cfg_path = f.name

        try:
            self.proc = subprocess.Popen(
                ["cava", "-p", self.cfg_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )

            for line in self.proc.stdout:
                if not self.running:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    raw_vals = [float(x) / 100.0 for x in line.split(";") if x]
                    if len(raw_vals) == self.bar_count:
                        self.bars_updated.emit(raw_vals)
                except ValueError:
                    pass

        except Exception as e:
            logger.warning(f"Could not start CAVA process: {e}")
        finally:
            if self.proc:
                try:
                    self.proc.terminate()
                    self.proc.wait(timeout=0.5)
                except Exception:
                    pass
            if self.cfg_path and os.path.exists(self.cfg_path):
                try:
                    os.remove(self.cfg_path)
                except Exception:
                    pass

    def stop(self):
        self.running = False
        if self.proc:
            try:
                self.proc.terminate()
            except Exception:
                pass
        self.wait(800)


class CavaVisualizerWidget(QWidget):
    """
    CAVA spectrum analyzer drawn as soft rounded bars.
    CAVA and the animation timer only run while music is playing; when paused
    the bars fall to zero and painting stops.
    """
    def __init__(self, parent=None, bar_count: int = 54, accent_color: str = "#8E3B56"):
        super().__init__(parent)
        self.bar_count = bar_count
        self.accent_color = QColor(accent_color)
        self.is_playing = False
        self.cava_thread: Optional[CavaThread] = None

        self.current_heights = [0.0] * bar_count
        self.target_heights = [0.0] * bar_count

        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Physics interpolation timer (40 FPS), only active while bars move
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(25)
        self.anim_timer.timeout.connect(self._step_physics)

    def set_accent_color(self, accent_color: str) -> None:
        self.accent_color = QColor(accent_color)
        self.update()

    def set_playing(self, playing: bool) -> None:
        if playing == self.is_playing:
            return
        self.is_playing = playing
        if playing:
            self._start_cava()
        else:
            self._stop_cava()
        # Keep animating so bars rise or fall smoothly; the timer stops itself at rest
        self.anim_timer.start()

    def _start_cava(self) -> None:
        if self.cava_thread is not None:
            return
        self.cava_thread = CavaThread(bar_count=self.bar_count)
        self.cava_thread.bars_updated.connect(self._on_cava_bars)
        self.cava_thread.start()

    def _stop_cava(self) -> None:
        if self.cava_thread is None:
            return
        self.cava_thread.bars_updated.disconnect(self._on_cava_bars)
        self.cava_thread.stop()
        self.cava_thread = None
        self.target_heights = [0.0] * self.bar_count

    def _on_cava_bars(self, vals: list) -> None:
        """Receive actual audio spectrum from CAVA."""
        for i in range(min(len(vals), self.bar_count)):
            self.target_heights[i] = max(0.0, min(1.0, vals[i]))

    def _step_physics(self) -> None:
        """Smooth interpolation and gravity falloff for terminal cava feel."""
        for i in range(self.bar_count):
            target = self.target_heights[i] if self.is_playing else 0.0
            if target > self.current_heights[i]:
                self.current_heights[i] += (target - self.current_heights[i]) * 0.65
            else:
                self.current_heights[i] += (target - self.current_heights[i]) * 0.25

        if not self.is_playing and max(self.current_heights) < 0.01:
            self.current_heights = [0.0] * self.bar_count
            self.anim_timer.stop()
        self.update()

    def paintEvent(self, event) -> None:
        """Draw crisp rectangular terminal bars with sharp flat tops."""
        if max(self.current_heights) <= 0.0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        w = self.width()
        h = self.height()
        gap = 3
        total_gaps = (self.bar_count - 1) * gap
        bar_w = max(2, int((w - total_gaps) / self.bar_count))
        used_w = self.bar_count * bar_w + total_gaps
        start_x = int((w - used_w) / 2)

        # Accent at the base fading up into the theme's lilac
        grad = QLinearGradient(0, h, 0, 0)
        grad.setColorAt(0.0, self.accent_color)
        grad.setColorAt(1.0, mix(tokens().dream, self.accent_color, 0.6))
        painter.setBrush(grad)

        radius = bar_w / 2
        for i in range(self.bar_count):
            bar_h = self.current_heights[i] * (h - 2)
            if bar_h < 1:
                continue
            x = start_x + i * (bar_w + gap)
            painter.drawRoundedRect(QRectF(x, h - bar_h, bar_w, bar_h), radius, radius)

    def close(self):
        self._stop_cava()
        self.anim_timer.stop()
        super().close()


class MusicPlayerWidget(QWidget):
    """
    Clean, frameless aesthetic music player.
    Seamlessly integrates into ACCELA's pastel background without any container box.
    """
    def __init__(self, parent=None, accent_color: str = "#8E3B56", bg_color: str = "#F5F2EB"):
        super().__init__(parent)
        self.accent_color = accent_color
        self.bg_color = bg_color
        self.setObjectName("musicPlayerWidget")
        # Set when a track starts so the tick loop can detect when it finishes
        self._track_running = False

        # Audio engine
        self.playback = Playback()
        self.playlist: List[str] = []
        self.current_track_idx = 0
        self.is_user_scrubbing = False
        self.loop_mode = True
        self.volume = 0.50
        self.is_muted = False
        self.prev_volume = 0.50
        self.playback.set_volume(self.volume)

        # Mascot GIFs
        self.gif_files: List[str] = []
        self.current_gif_idx = 0
        self.dance_movie: Optional[QMovie] = None

        # Load media files
        self._load_playlist()
        self._load_dance_gifs()

        # Build UI
        self._setup_ui()

        # Timer for track progress updates
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self._on_timer_tick)
        self.update_timer.start()

        # Auto-rotate mascot GIF during playback
        self.gif_rotate_timer = QTimer(self)
        self.gif_rotate_timer.setInterval(20000)
        self.gif_rotate_timer.timeout.connect(self._on_auto_rotate_gif)
        self.gif_rotate_timer.start()

        # Prepare first track
        if self.playlist:
            self._prepare_track(0, autoplay=False)

    def _rgba(self, alpha: float) -> str:
        """Accent color as a CSS rgba() string with the given alpha."""
        c = QColor(self.accent_color)
        return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"

    def _faded(self, amount: float) -> str:
        """Accent color blended into the background (0 = background, 1 = accent)."""
        a, b = QColor(self.accent_color), QColor(self.bg_color)
        mix = lambda x, y: round(y + (x - y) * amount)
        return QColor(mix(a.red(), b.red()), mix(a.green(), b.green()), mix(a.blue(), b.blue())).name()

    def _icon(self, name: str, size: int, color: Optional[str] = None) -> QIcon:
        return make_svg_icon(SVG_ICONS[name](color or self.accent_color), size)

    def _set_play_icon(self, playing: bool) -> None:
        self.play_btn.setIcon(self._icon("pause" if playing else "play", 16, self.bg_color))

    def _load_playlist(self) -> None:
        """Scan music directory for tracks (MP3, FLAC, WAV, OGG, M4A)."""
        music_dir = Path.home() / ".local/share/ACCELA/music"
        music_dir.mkdir(parents=True, exist_ok=True)
        user_music_accela = Path.home() / "Music/ACCELA"

        extensions = ("*.mp3", "*.flac", "*.wav", "*.ogg", "*.m4a")
        candidates = []

        for ext in extensions:
            candidates.extend(glob.glob(str(music_dir / ext)))
            if user_music_accela.exists():
                candidates.extend(glob.glob(str(user_music_accela / ext)))

        candidates.sort()
        seen = set()
        self.playlist = []
        for f in candidates:
            basename = os.path.basename(f)
            if basename not in seen:
                seen.add(basename)
                self.playlist.append(f)

    def _load_dance_gifs(self) -> None:
        """Scan gifs directory for Yume Nikki dancing GIFs."""
        yumi_dir = Path.home() / ".local/share/ACCELA/gifs/yumi"

        candidates = []
        if yumi_dir.exists():
            candidates.extend(sorted(glob.glob(str(yumi_dir / "*.gif"))))

        seen = set()
        self.gif_files = []
        for f in candidates:
            basename = os.path.basename(f)
            if basename not in seen:
                seen.add(basename)
                self.gif_files.append(f)

    def _clean_track_title(self, path: str) -> str:
        """Format filename into a clean, aesthetic song title."""
        name = Path(path).stem
        name = name.replace("_", " ").strip()
        return name

    def _setup_ui(self) -> None:
        """Setup frameless, clean, organized player layout."""
        self.setFixedHeight(122)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Floating translucent card with a soft accent shadow
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 8)
        self.card = QFrame()
        self.card.setObjectName("playerCard")
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 4)
        shadow_color = QColor(self.accent_color)
        shadow_color.setAlpha(45)
        shadow.setColor(shadow_color)
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)

        main_layout = QHBoxLayout(self.card)
        main_layout.setContentsMargins(14, 8, 18, 8)
        main_layout.setSpacing(14)

        # 1. Left: Dancing Yumi Mascot (pure pixel art, no text, interactive)
        self.dance_label = QLabel()
        self.dance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dance_label.setScaledContents(True)
        self.dance_label.setFixedSize(60, 60)
        self.dance_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dance_label.setToolTip("Clique para trocar a dança")
        self.dance_label.mousePressEvent = lambda e: self.next_dance_gif()

        mascot_container = QFrame()
        mascot_container.setObjectName("mascotBubble")
        mascot_container.setFixedSize(76, 76)
        mascot_layout = QVBoxLayout(mascot_container)
        mascot_layout.setContentsMargins(8, 8, 8, 8)
        mascot_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mascot_layout.addWidget(self.dance_label)

        main_layout.addWidget(mascot_container)

        # 2. Right: Content area (Track info, CAVA bars, Scrubber, Controls)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(3)

        # Row 1: Title and Time
        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel("Nenhuma música carregada")
        self.title_label.setObjectName("trackTitle")
        info_row.addWidget(self.title_label, 1)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("trackTime")
        info_row.addWidget(self.time_label)

        right_layout.addLayout(info_row)

        # Row 2: CAVA Terminal Visualizer Bars (54 rectangular vertical bars)
        self.visualizer = CavaVisualizerWidget(self, bar_count=44, accent_color=self.accent_color)
        right_layout.addWidget(self.visualizer)

        # Row 3: Scrubber slider
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setObjectName("trackScrubber")
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.progress_slider.sliderPressed.connect(self._on_scrub_start)
        self.progress_slider.sliderReleased.connect(self._on_scrub_end)
        self.progress_slider.sliderMoved.connect(self._on_scrub_move)
        right_layout.addWidget(self.progress_slider)

        # Row 4: Controls & Volume
        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 2, 0, 0)
        controls_row.setSpacing(8)
        controls_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Playback navigation
        self.prev_btn = QPushButton()
        self.prev_btn.setObjectName("actionBtn")
        self.prev_btn.setIcon(make_svg_icon(SVG_ICONS["prev"](self.accent_color), 18))
        self.prev_btn.setFixedSize(28, 28)
        self.prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.prev_btn.setToolTip("Faixa anterior")
        self.prev_btn.clicked.connect(self.prev_track)
        controls_row.addWidget(self.prev_btn)

        self.play_btn = QPushButton()
        self.play_btn.setObjectName("playBtn")
        self.play_btn.setIcon(self._icon("play", 16, self.bg_color))
        self.play_btn.setFixedSize(32, 32)
        self.play_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.play_btn.setToolTip("Reproduzir / Pausar")
        self.play_btn.clicked.connect(self.toggle_play)
        controls_row.addWidget(self.play_btn)

        self.next_btn = QPushButton()
        self.next_btn.setObjectName("actionBtn")
        self.next_btn.setIcon(make_svg_icon(SVG_ICONS["next"](self.accent_color), 18))
        self.next_btn.setFixedSize(28, 28)
        self.next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.next_btn.setToolTip("Próxima faixa")
        self.next_btn.clicked.connect(self.next_track)
        controls_row.addWidget(self.next_btn)

        # Repeat toggle
        self.loop_btn = QPushButton()
        self.loop_btn.setObjectName("actionBtn")
        self.loop_btn.setIcon(make_svg_icon(SVG_ICONS["loop"](self.accent_color), 16))
        self.loop_btn.setFixedSize(28, 28)
        self.loop_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.loop_btn.setToolTip("Repetir playlist")
        self._update_loop_button()
        self.loop_btn.clicked.connect(self._toggle_loop)
        controls_row.addWidget(self.loop_btn)

        # Spacer pushes volume to the right
        controls_row.addStretch()

        # Volume toggle & slider
        self.vol_btn = QPushButton()
        self.vol_btn.setObjectName("actionBtn")
        self.vol_btn.setIcon(make_svg_icon(SVG_ICONS["volume"](self.accent_color), 16))
        self.vol_btn.setFixedSize(26, 26)
        self.vol_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.vol_btn.setToolTip("Mutar / Desmutar")
        self.vol_btn.clicked.connect(self._toggle_mute)
        controls_row.addWidget(self.vol_btn)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setObjectName("volumeSlider")
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(int(self.volume * 100))
        self.vol_slider.setFixedWidth(75)
        self.vol_slider.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.vol_slider.valueChanged.connect(self._on_volume_changed)
        controls_row.addWidget(self.vol_slider)

        right_layout.addLayout(controls_row)

        main_layout.addWidget(right_container, 1)

        # Apply clean stylesheet
        self._apply_styles()

        # Load first GIF
        self._update_dance_gif()

    def _apply_styles(self) -> None:
        """Card, bubble and control styles derived from the theme tokens."""
        t = tokens()
        accent = t.accent.name()
        style = f"""
            QWidget#musicPlayerWidget {{
                background: transparent;
                border: none;
            }}

            QFrame#playerCard {{
                background-color: {rgba(t.surface, 0.72)};
                border: 1px solid {t.border.name()};
                border-radius: 20px;
            }}

            QFrame#mascotBubble {{
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.6, fx:0.5, fy:0.4,
                    stop:0 {rgba(t.dream, 0.55)}, stop:1 {rgba(t.accent, 0.10)});
                border: 1px solid {rgba(t.accent, 0.15)};
                border-radius: 38px;
            }}

            QLabel#trackTitle {{
                color: {accent};
                font-size: 10pt;
                font-weight: 800;
            }}

            QLabel#trackTime {{
                color: {t.text_muted.name()};
                font-size: 9pt;
                font-weight: 600;
            }}

            QPushButton#actionBtn {{
                background-color: transparent;
                border: none;
                border-radius: 14px;
                padding: 0px;
            }}

            QPushButton#actionBtn:hover {{
                background-color: {self._rgba(0.12)};
            }}

            QPushButton#playBtn {{
                background: {t.accent_gradient()};
                border: none;
                border-radius: 16px;
                padding: 0px;
            }}

            QPushButton#playBtn:hover {{
                background: {t.accent_hover.name()};
            }}

            QSlider#trackScrubber::groove:horizontal,
            QSlider#volumeSlider::groove:horizontal {{
                height: 4px;
                background: {self._rgba(0.15)};
                border-radius: 2px;
            }}

            QSlider#trackScrubber::sub-page:horizontal,
            QSlider#volumeSlider::sub-page:horizontal {{
                background: {t.accent_gradient()};
                border-radius: 2px;
            }}

            QSlider#trackScrubber::handle:horizontal,
            QSlider#volumeSlider::handle:horizontal {{
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
                background: {t.surface.name()};
                border: 2px solid {accent};
            }}

            QSlider#trackScrubber::handle:horizontal:hover {{
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
                background: {accent};
            }}
        """
        self.setStyleSheet(style)

    def _update_dance_gif(self) -> None:
        """Update the dancing Yumi mascot GIF."""
        if not self.gif_files:
            return

        gif_path = self.gif_files[self.current_gif_idx % len(self.gif_files)]
        if self.dance_movie:
            self.dance_movie.stop()

        self.dance_movie = QMovie(gif_path)
        self.dance_label.setMovie(self.dance_movie)

        if self.playback.playing and not self.playback.paused:
            self.dance_movie.start()
        else:
            self.dance_movie.jumpToFrame(0)
            self.dance_movie.stop()

    def next_dance_gif(self) -> None:
        """Cycle to next dancing GIF."""
        if len(self.gif_files) > 1:
            self.current_gif_idx = (self.current_gif_idx + 1) % len(self.gif_files)
            self._update_dance_gif()

    def _on_auto_rotate_gif(self) -> None:
        """Auto cycle GIF every 20s while playing."""
        if self.playback.playing and not self.playback.paused:
            self.next_dance_gif()

    def _set_playing_state(self, playing: bool) -> None:
        """Sync play button, visualizer and mascot with the playback state."""
        self._set_play_icon(playing)
        self.visualizer.set_playing(playing)
        if self.dance_movie:
            if playing:
                self.dance_movie.start()
            else:
                self.dance_movie.stop()

    def _prepare_track(self, index: int, autoplay: bool = True) -> None:
        """Load track at given index."""
        if not self.playlist:
            return

        self.current_track_idx = index % len(self.playlist)
        track_path = self.playlist[self.current_track_idx]

        title = self._clean_track_title(track_path)
        self.title_label.setText(title)
        self.title_label.setToolTip(f"Faixa {self.current_track_idx + 1}/{len(self.playlist)}: {title}")

        try:
            self.playback.load_file(track_path)
            self.playback.set_volume(self.volume if not self.is_muted else 0.0)
            self.progress_slider.setValue(0)
            self._update_time_label(0, self.playback.duration)

            if autoplay:
                self.playback.play()
                self._track_running = True
            else:
                self._track_running = False
            self._set_playing_state(autoplay)
        except Exception as e:
            logger.warning(f"Could not load track {track_path}: {e}")
            self._track_running = False
            self.title_label.setText(f"Erro ao carregar: {title}")

    def toggle_play(self) -> None:
        """Toggle play/pause state."""
        if not self.playlist:
            return

        if self.playback.active and not self.playback.paused:
            self.playback.pause()
            self._set_playing_state(False)
        elif self.playback.active:
            self.playback.resume()
            self._set_playing_state(True)
        else:
            self.playback.play()
            self._track_running = True
            self._set_playing_state(True)

    def next_track(self) -> None:
        """Play next track and switch dance animation."""
        if not self.playlist:
            return
        self.next_dance_gif()
        self._prepare_track(self.current_track_idx + 1, autoplay=True)

    def prev_track(self) -> None:
        """Play previous track (or restart current if > 3s)."""
        if not self.playlist:
            return
        if self.playback.curr_pos > 3.0:
            self.playback.seek(0)
        else:
            self.next_dance_gif()
            self._prepare_track(self.current_track_idx - 1, autoplay=True)

    def _toggle_loop(self) -> None:
        """Toggle playlist loop mode."""
        self.loop_mode = not self.loop_mode
        self._update_loop_button()

    def _update_loop_button(self) -> None:
        """Highlight the loop button when on; fade its icon when off."""
        if self.loop_mode:
            self.loop_btn.setIcon(self._icon("loop", 16))
            self.loop_btn.setStyleSheet(f"background-color: {self._rgba(0.15)};")
        else:
            self.loop_btn.setIcon(self._icon("loop", 16, self._faded(0.35)))
            self.loop_btn.setStyleSheet("background-color: transparent;")

    def _toggle_mute(self) -> None:
        """Toggle mute / unmute."""
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.prev_volume = self.volume
            self.playback.set_volume(0.0)
            self.vol_btn.setIcon(make_svg_icon(SVG_ICONS["mute"](self.accent_color), 16))
        else:
            self.playback.set_volume(self.prev_volume)
            self.vol_btn.setIcon(make_svg_icon(SVG_ICONS["volume"](self.accent_color), 16))

    def _on_volume_changed(self, value: int) -> None:
        """Update volume from slider."""
        self.volume = value / 100.0
        if self.is_muted and self.volume > 0:
            self.is_muted = False
            self.vol_btn.setIcon(make_svg_icon(SVG_ICONS["volume"](self.accent_color), 16))
        self.playback.set_volume(self.volume)

    def _on_scrub_start(self) -> None:
        self.is_user_scrubbing = True

    def _on_scrub_move(self, value: int) -> None:
        if self.playback.duration > 0:
            secs = (value / 1000.0) * self.playback.duration
            self._update_time_label(secs, self.playback.duration)

    def _on_scrub_end(self) -> None:
        if self.playback.duration > 0:
            value = self.progress_slider.value()
            target_secs = (value / 1000.0) * self.playback.duration
            self.playback.seek(target_secs)
        self.is_user_scrubbing = False

    def _format_time(self, seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def _update_time_label(self, current: float, total: float) -> None:
        cur_str = self._format_time(max(0, current))
        tot_str = self._format_time(max(0, total))
        self.time_label.setText(f"{cur_str} / {tot_str}")

    def _on_track_finished(self) -> None:
        """Advance the playlist, or stop at the end when loop is off."""
        if self.loop_mode or self.current_track_idx + 1 < len(self.playlist):
            self.next_track()
        else:
            self._set_playing_state(False)
            self.progress_slider.setValue(0)
            self._update_time_label(0, self.playback.duration)

    def _on_timer_tick(self) -> None:
        """Check playback status and update slider."""
        # just_playback drops `active` back to False once a track plays to the end
        if not self.playback.active:
            if self._track_running:
                self._track_running = False
                self._on_track_finished()
            return

        duration = self.playback.duration
        curr_pos = self.playback.curr_pos

        if duration > 0 and not self.is_user_scrubbing:
            fraction = min(1.0, max(0.0, curr_pos / duration))
            self.progress_slider.setValue(int(fraction * 1000))
            self._update_time_label(curr_pos, duration)

    def close(self):
        """Clean up threads and audio."""
        self.update_timer.stop()
        self.gif_rotate_timer.stop()
        if hasattr(self, "visualizer"):
            self.visualizer.close()
        if self.playback.playing:
            self.playback.stop()
        super().close()
