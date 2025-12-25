import sys
import subprocess
import math
import random
import json
import inspect
from PySide6.QtGui import QPainterPath, QLinearGradient
from PySide6.QtCore import QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from typing import Optional
from pathlib import Path


from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QPen,
    QBrush,
    QColor,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSlider,
    QSizePolicy,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QProgressBar,
)
from PySide6.QtCore import Qt, QTimer

import webbrowser
import api_client


# ---------- Backend launcher ----------

def start_backend():
    """
    Start the FastAPI backend (uvicorn) as a separate process.
    Returns the Popen object so we can later terminate it.
    """
    project_root = Path(__file__).resolve().parent.parent
    backend_dir = project_root / "backend"

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]

    proc = subprocess.Popen(cmd, cwd=str(backend_dir))
    return proc


# ---------- Simple EQ bars widget (vertical spikes) ----------

class EqBarsWidget(QWidget):
    def __init__(self, parent=None, bar_color: QColor = QColor("#ff8844")):
        super().__init__(parent)
        self.num_bars = 18
        self.values = [0.2 for _ in range(self.num_bars)]
        self.bar_color = bar_color
        self.setMinimumHeight(26)

    def set_bar_color(self, color: QColor):
        self.bar_color = color
        self.update()

    def random_step(self):
        """Randomly jiggle bar heights a bit, then repaint."""
        for i in range(self.num_bars):
            delta = random.uniform(-0.15, 0.2)
            self.values[i] = min(1.0, max(0.05, self.values[i] + delta))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        bar_width = w / (self.num_bars * 1.5)
        spacing = bar_width * 0.5

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.bar_color))

        for i, val in enumerate(self.values):
            x = i * (bar_width + spacing)
            bar_height = h * val
            y = h - bar_height
            painter.drawRoundedRect(
                int(x),
                int(y),
                int(bar_width),
                int(bar_height),
                2,
                2,
            )

        painter.end()

class AnimatedCassetteFrame(QFrame):
    """
    A QFrame that paints a soft animated RGB glow/gradient INSIDE the cassette.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hue = 0.0           # 0..360
        self._radius = 16

        # We paint our own background
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def set_hue(self, hue: float):
        self._hue = hue % 360.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        r = self.rect()
        if r.width() <= 0 or r.height() <= 0:
            return

        radius = self._radius

        # Rounded clip path
        path = QPainterPath()
        path.addRoundedRect(r.adjusted(1, 1, -1, -1), radius, radius)
        p.setClipPath(path)

        # --- Animated gradient fill (soft) ---
        w, h = r.width(), r.height()
        hue1 = self._hue
        hue2 = (hue1 + 120) % 360
        hue3 = (hue1 + 240) % 360

        c1 = QColor.fromHsv(int(hue1), 180, 50)   # darkish
        c2 = QColor.fromHsv(int(hue2), 200, 55)
        c3 = QColor.fromHsv(int(hue3), 180, 45)

        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(0.5, c2)
        grad.setColorAt(1.0, c3)

        p.fillRect(r, grad)

        # Dark overlay so elements stay readable
        p.fillRect(r, QColor(0, 0, 0, 150))

        # --- subtle inner glow ---
        glow = QColor.fromHsv(int(hue1), 255, 255)
        glow.setAlpha(45)
        p.fillRect(r, glow)

        p.end()

# ---------- Cassette-style now playing widget ----------

class CassetteNowPlayingWidget(QWidget):
    """
    Cassette-style now-playing panel inspired by classic tapes:

    - Title + artist/album above
    - Cassette body:
        * top label strip
        * left & right reels
        * center panel with album art and EQ bars
    - Audiophile line under the cassette
    - Song progress bar + time below
    """
    def set_accent_color(self, accent: QColor):
        """
        Called by the RGB background to update cassette highlight colors.
        """
        if accent is None:
            self._accent = None
            return

        self._accent = accent
        accent_hex = accent.lighter(120).name()

        # Avoid hammering styles if color hasn't really changed
        if accent_hex == self._last_accent_hex:
            return
        self._last_accent_hex = accent_hex

        # Use current theme as base, but override highlights with accent
        colors = dict(self._current_colors)
        colors["frame_border"] = accent_hex
        colors["reel_border"] = accent_hex
        colors["progress"] = accent_hex
        colors["eq"] = accent_hex

        # Optional: tint the top strip slightly
        colors["top_strip"] = accent.lighter(160).name()

        self.setStyleSheet(self._base_stylesheet.format(**colors))

        # EQ bars update
        self.eq_widget.set_bar_color(QColor(colors["eq"]))

        # Rebuild reel pixmap so ring matches accent (see next step)
        self._reel_base_pixmap = self._create_reel_pixmap(72, ring_color=QColor(accent_hex))
        self._apply_reel_pixmap(self._reel_angle)

    def __init__(self, parent=None):
        super().__init__(parent)

        # ---------- labels ----------
        self.title_label = QLabel("No track playing")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.info_label = QLabel("")  # "Artist — Album"
        self.info_label.setAlignment(Qt.AlignCenter)

        self.tech_label = QLabel("🎧 Spotify • Streaming")
        self.tech_label.setAlignment(Qt.AlignCenter)

        # ---------- cassette frame ----------
        self.cassette_frame = AnimatedCassetteFrame()
        self.cassette_frame.setObjectName("cassetteFrame")
        self.cassette_frame.setMinimumHeight(210)  # tweak if you want


        # top strip (label area)
        self.cassette_top = QFrame()
        self.cassette_top.setObjectName("cassetteTop")
        self.cassette_top.setFixedHeight(26)

        # reels
        self.left_reel = QLabel()
        self.right_reel = QLabel()
        self.left_reel.setObjectName("reel")
        self.right_reel.setObjectName("reel")
        self.left_reel.setFixedSize(72, 72)
        self.right_reel.setFixedSize(72, 72)

        # center panel: album art + EQ bars
        self.center_panel = QFrame()
        self.center_panel.setObjectName("centerPanel")

        self.album_label = QLabel()
        self.album_label.setObjectName("albumArt")
        self.album_label.setAlignment(Qt.AlignCenter)
        # not strictly fixed; but min/preferred so the layout can grow a bit
        self.album_label.setMinimumSize(120, 120)
        self.album_label.setMaximumSize(180, 180)
        self.album_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.eq_widget = EqBarsWidget(self)

        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(10, 10, 10, 6)
        center_layout.setSpacing(6)
        center_layout.addWidget(self.album_label, alignment=Qt.AlignCenter)
        center_layout.addWidget(self.eq_widget)
        self.center_panel.setLayout(center_layout)

        # layout inside cassette
        mid_row = QHBoxLayout()
        mid_row.setContentsMargins(28, 26, 28, 26)
        mid_row.setSpacing(24)
        mid_row.addWidget(self.left_reel, 0, Qt.AlignVCenter)
        mid_row.addWidget(self.center_panel, 1)
        mid_row.addWidget(self.right_reel, 0, Qt.AlignVCenter)


        cassette_main = QVBoxLayout()
        cassette_main.setContentsMargins(0, 0, 0, 0)
        cassette_main.setSpacing(0)
        cassette_main.addWidget(self.cassette_top)
        cassette_main.addLayout(mid_row)
        self.cassette_frame.setLayout(cassette_main)

        # ---------- progress ----------
        self.mini_progress = QProgressBar()
        self.mini_progress.setObjectName("songProgress")
        self.mini_progress.setRange(0, 1000)
        self.mini_progress.setTextVisible(False)

        self.time_label = QLabel("--:-- / --:--")
        self.time_label.setAlignment(Qt.AlignCenter)

        # ---------- layout ----------
        root = QVBoxLayout()
        root.setContentsMargins(5, 5, 5, 5)
        root.addWidget(self.title_label)
        root.addWidget(self.info_label)
        root.addWidget(self.cassette_frame)
        root.addWidget(self.tech_label)
        root.addWidget(self.mini_progress)
        root.addWidget(self.time_label)
        self.setLayout(root)

        # ---------- themes ----------
        self.themes = {
            "rock": {
                "bg": "#141018",
                "top_strip": "#f4e4cc",
                "frame_border": "#aa3344",
                "reel_border": "#ff4a4a",
                "progress": "#ff8844",
                "text": "#f0f0f0",
                "eq": "#ff8a4a",
            },
            "edm": {
                "bg": "#081018",
                "top_strip": "#102430",
                "frame_border": "#1dd1ff",
                "reel_border": "#00e5ff",
                "progress": "#00ffa3",
                "text": "#eafcff",
                "eq": "#00ffa3",
            },
            "chill": {
                "bg": "#101418",
                "top_strip": "#e1edf8",
                "frame_border": "#6ca0dc",
                "reel_border": "#9bbff5",
                "progress": "#8fe0ff",
                "text": "#f5f7fb",
                "eq": "#8fe0ff",
            },
            "jazz": {
                "bg": "#181010",
                "top_strip": "#f9e6c6",
                "frame_border": "#d4a05a",
                "reel_border": "#f7b85c",
                "progress": "#f7d25c",
                "text": "#fdf6e3",
                "eq": "#f7d25c",
            },
            "default": {
                "bg": "#151515",
                "top_strip": "#e6e2da",
                "frame_border": "#333333",
                "reel_border": "#ff4a4a",
                "progress": "#ff8844",
                "text": "#f0f0f0",
                "eq": "#ff8844",
            },
        }
        self._current_theme_name = "default"
        self._current_colors = self.themes["default"]

        self._base_stylesheet = """
        QLabel {{
            color: {text};
        }}
        #cassetteFrame {{
            background-color: {bg};
            border-radius: 16px;
            border: 1px solid {frame_border};
        }}
        #cassetteTop {{
            background-color: {top_strip};
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
        }}
        #reel {{
            min-width: 72px;
            min-height: 72px;
            max-width: 72px;
            max-height: 72px;
            border-radius: 36px;
            border: 3px solid {reel_border};
            background-color: #202020;
        }}
        #centerPanel {{
            background-color: #050505;
            border-radius: 10px;
            border: 1px solid #222222;
        }}
        #albumArt {{
            border-radius: 8px;
            border: 1px solid #444444;
            background-color: #000000;
        }}
        QProgressBar#songProgress {{
            background-color: #111111;
            border: 1px solid #333333;
            border-radius: 3px;
        }}
        QProgressBar#songProgress::chunk {{
            background-color: {progress};
        }}
        """
        self.apply_theme("default")
        self._accent: Optional[QColor] = None
        self._last_accent_hex: Optional[str] = None

        self._rgb_accent: Optional[QColor] = None
        self._rgb_hue: float = 0.0
        self._reel_base_pixmap = self._create_reel_pixmap(72, ring_color=QColor(self._current_colors["reel_border"]))
        self._reel_angle = 0
        self._is_playing = False

        self.reel_timer = QTimer(self)
        self.reel_timer.setInterval(50)
        self.reel_timer.timeout.connect(self._update_animation)

        self._apply_reel_pixmap(0)

    def set_rgb_sync(self, accent: QColor, hue: float):
        """
        Called from the window so cassette stays in sync with buttons/background.
        """
        self._rgb_accent = accent
        self._rgb_hue = hue % 360.0

        # Animate cassette body glow
        if isinstance(self.cassette_frame, AnimatedCassetteFrame):
            self.cassette_frame.set_hue(self._rgb_hue)

        # Apply accent to cassette borders/progress/eq/reels (without breaking theme)
        self._apply_cassette_accent()

    def _apply_cassette_accent(self):
        if not self._rgb_accent:
            return

        accent_hex = self._rgb_accent.lighter(120).name()
        if accent_hex == self._last_accent_hex:
            return
        self._last_accent_hex = accent_hex
        # Base theme colors + override highlights with RGB accent
        colors = dict(self._current_colors)
        colors["frame_border"] = accent_hex
        colors["reel_border"] = accent_hex
        colors["progress"] = accent_hex
        colors["eq"] = accent_hex

        # optional top strip tint
        colors["top_strip"] = self._rgb_accent.lighter(170).name()

        self.setStyleSheet(self._base_stylesheet.format(**colors))
        self.eq_widget.set_bar_color(QColor(colors["eq"]))

        # rebuild reel pixmap ring to match accent
        self._reel_base_pixmap = self._create_reel_pixmap(72, ring_color=QColor(accent_hex))
        self._apply_reel_pixmap(self._reel_angle)


    # ---------- theme handling ----------

    def apply_theme(self, theme_name: str):
        if theme_name not in self.themes:
            theme_name = "default"

        # ✅ don't repolish if nothing changed
        if theme_name == self._current_theme_name:
            return

        self._current_theme_name = theme_name
        self._current_colors = self.themes[theme_name]

        # Apply base theme
        self.setStyleSheet(self._base_stylesheet.format(**self._current_colors))
        self.eq_widget.set_bar_color(QColor(self._current_colors["eq"]))

        # If RGB sync is active, re-apply accent overrides ONCE
        if getattr(self, "_rgb_accent", None):
            self._apply_cassette_accent()



    # ---------- reel drawing & animation ----------

    def _create_reel_pixmap(self, size: int, ring_color: QColor = QColor("#ff4a4a")) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        center = size / 2
        radius_outer = size / 2 - 4
        radius_inner = size / 4

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # outer ring (use ring_color instead of hardcoded)
        painter.setPen(QPen(ring_color, 3))
        painter.setBrush(QBrush(QColor("#202020")))
        painter.drawEllipse(
            int(center - radius_outer),
            int(center - radius_outer),
            int(radius_outer * 2),
            int(radius_outer * 2),
        )

        # inner hub
        painter.setPen(QPen(QColor("#555555"), 2))
        painter.setBrush(QBrush(QColor("#303030")))
        painter.drawEllipse(
            int(center - radius_inner),
            int(center - radius_inner),
            int(radius_inner * 2),
            int(radius_inner * 2),
        )

        # spokes
        painter.setPen(QPen(QColor("#dddddd"), 2))
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = center + radius_inner * 0.5 * math.cos(rad)
            y1 = center + radius_inner * 0.5 * math.sin(rad)
            x2 = center + (radius_outer - 4) * math.cos(rad)
            y2 = center + (radius_outer - 4) * math.sin(rad)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        painter.end()
        return pix


    def _apply_reel_pixmap(self, angle_degrees: float):
        base = self._reel_base_pixmap
        if base is None:
            return

        size = base.size()
        out = QPixmap(size)
        out.fill(Qt.transparent)

        p = QPainter(out)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # rotate around center, but always draw into same-size canvas
        p.translate(size.width() / 2, size.height() / 2)
        p.rotate(angle_degrees)
        p.translate(-size.width() / 2, -size.height() / 2)
        p.drawPixmap(0, 0, base)
        p.end()

        self.left_reel.setPixmap(out)
        self.right_reel.setPixmap(out)


    def _update_animation(self):
        if not self._is_playing:
            return

        # spin reels
        self._reel_angle = (self._reel_angle + 6) % 360
        self._apply_reel_pixmap(self._reel_angle)

        # jiggle EQ bars
        self.eq_widget.random_step()

    def set_playing_state(self, is_playing: bool):
        self._is_playing = is_playing
        if is_playing:
            if not self.reel_timer.isActive():
                self.reel_timer.start()
        else:
            self.reel_timer.stop()
            self._apply_reel_pixmap(0)

    # ---------- album art helpers ----------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # reapply scaling on resize
        if hasattr(self, "_album_pixmap") and self._album_pixmap is not None:
            self._apply_album_pixmap()

    def set_album_art(self, pixmap: Optional[QPixmap]):
        self._album_pixmap = pixmap
        self._apply_album_pixmap()

    def _apply_album_pixmap(self):
        if not hasattr(self, "_album_pixmap") or self._album_pixmap is None:
            self.album_label.clear()
            return
        target_size = self.album_label.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            self.album_label.setPixmap(self._album_pixmap)
            return
        scaled = self._album_pixmap.scaled(
            target_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.album_label.setPixmap(scaled)

    # ---------- helpers ----------

    @staticmethod
    def ms_to_mmss(ms: Optional[int]) -> str:
        if ms is None or ms <= 0:
            return "--:--"
        seconds = int(ms / 1000)
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def update_track(
        self,
        title: str,
        artists: str,
        album: Optional[str],
        progress_ms: int,
        duration_ms: int,
        genre_hint: Optional[str] = None,
    ):
        """
        Update basic info + theme + progress.
        genre_hint: simple string like 'rock', 'edm', 'chill', 'jazz'
        """
        # title & info
        self.title_label.setText(title or "Unknown track")
        info_parts = []
        if artists:
            info_parts.append(artists)
        if album:
            info_parts.append(album)
        self.info_label.setText(" — ".join(info_parts) if info_parts else "")

        # theme based on hint
        theme_map = {
            "rock": "rock",
            "metal": "rock",
            "punk": "rock",
            "edm": "edm",
            "dance": "edm",
            "house": "edm",
            "chill": "chill",
            "lofi": "chill",
            "jazz": "jazz",
        }
        theme_name = "default"
        if genre_hint:
            key = genre_hint.lower()
            theme_name = theme_map.get(key, "default")

        # ✅ only re-style if theme actually changed
        if theme_name != self._current_theme_name:
            self.apply_theme(theme_name)


        # audiophile line
        mood_label = {
            "rock": "⚡ Rock Mode",
            "edm": "🎛 EDM / Club",
            "chill": "🌙 Chill / Lofi",
            "jazz": "🎷 Jazz Lounge",
            "default": "🎧 Spotify • Streaming",
        }[theme_name]
        self.tech_label.setText(f"{mood_label}  •  44.1kHz • 320kbps (virtual)")

        # time / progress
        elapsed_str = self.ms_to_mmss(progress_ms)
        total_str = self.ms_to_mmss(duration_ms)
        self.time_label.setText(f"{elapsed_str} / {total_str}")

        if duration_ms and duration_ms > 0:
            fraction = progress_ms / float(duration_ms)
            self.mini_progress.setValue(int(fraction * 1000))
        else:
            self.mini_progress.setValue(0)

class RgbBackground(QWidget):
    """
    A QWidget that paints a smooth animated RGB gradient like a gaming keyboard.
    Put your whole UI layout inside it.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._t = 0.0
        self._speed = 0.6  # lower = slower, smoother

        self._timer = QTimer(self)
        self._timer.setInterval(33)  # ~30 FPS
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        # Make sure we actually paint the background
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.accentChanged = None  # callback you can set from outside

    def _tick(self):
        self._t += self._speed * 0.02
        self.update()

        if self.accentChanged:
            hue = (self._t * 60) % 360
            accent = QColor.fromHsv(int(hue), 255, 255)

            # Call with 2 args if callback supports it, else 1 arg
            try:
                if len(inspect.signature(self.accentChanged).parameters) >= 2:
                    self.accentChanged(accent, hue)
                else:
                    self.accentChanged(accent)
            except Exception:
                self.accentChanged(accent)



    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        # Rotate colors through HSV for smooth cycling
        hue1 = (self._t * 60) % 360
        hue2 = (hue1 + 120) % 360
        hue3 = (hue1 + 240) % 360

        c1 = QColor.fromHsv(int(hue1), 200, 50)   # darker, not neon-blinding
        c2 = QColor.fromHsv(int(hue2), 220, 55)
        c3 = QColor.fromHsv(int(hue3), 200, 45)

        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(0.5, c2)
        grad.setColorAt(1.0, c3)

        p.fillRect(self.rect(), grad)

        # Add a subtle dark overlay so text stays readable
        p.fillRect(self.rect(), QColor(0, 0, 0, 140))

        p.end()

# ---------- Main window ----------

class SpotifyPlayerWindow(QMainWindow):    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spotify Desktop Control")
        self.setMinimumWidth(800)

        # State
        self.current_track_duration_ms = 0
        self.progress_slider_is_dragging = False
        self.current_track_uri: Optional[str] = None
        self.current_playlist_id: Optional[str] = None
        self.current_playlist_url: Optional[str] = None
        self.shuffle_state: bool = False
        self.last_track_id: Optional[str] = None

        # --- Async playback polling (prevents UI freezing) ---
        self.playback_net = QNetworkAccessManager(self)
        self.playback_net.finished.connect(self._on_playback_reply)
        self._pending_album_url = None
        self._playback_in_flight = False
        self._last_is_playing = False  # keep last state so play/pause doesn't need a blocking GET

        # --- Async album art (prevents freezes on track change) ---
        self.album_net = QNetworkAccessManager(self)
        self.album_net.finished.connect(self._on_album_art_reply)

        # --- Cassette-style now playing with album art inside ---
        self.cassette_widget = CassetteNowPlayingWidget()

        # --- Queue (beside cassette) ---
        self.queue_list = QListWidget()
        self.clear_queue_button = QPushButton("Clear Queue")
        self.clear_queue_button.clicked.connect(self.on_clear_queue)

        # --- Track info (extra text) ---
        self.track_label = QLabel("No track playing")
        self.track_label.setAlignment(Qt.AlignCenter)

        # --- Time label ---
        self.time_label = QLabel("--:-- / --:--")
        self.time_label.setAlignment(Qt.AlignCenter)

        # --- Progress slider (0–1000 = 0–100%) ---
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setSingleStep(1)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)

        # --- Playback buttons ---
        self.prev_button = QPushButton("⏮ Previous")
        self.play_pause_button = QPushButton("▶ Play")
        self.next_button = QPushButton("⏭ Next")

        self.prev_button.clicked.connect(self.on_prev_clicked)
        self.play_pause_button.clicked.connect(self.on_play_pause_clicked)
        self.next_button.clicked.connect(self.on_next_clicked)

        # --- Volume slider ---
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setSingleStep(1)
        self.volume_slider.sliderReleased.connect(self.on_volume_released)

        # --- Shuffle & Repeat ---
        self.shuffle_button = QPushButton("Shuffle: Off")
        self.shuffle_button.setCheckable(True)
        self.shuffle_button.clicked.connect(self.on_shuffle_clicked)

        self.repeat_combo = QComboBox()
        self.repeat_combo.addItem("Repeat: Off", userData="off")
        self.repeat_combo.addItem("Repeat: Track", userData="track")
        self.repeat_combo.addItem("Repeat: Context", userData="context")
        self.repeat_combo.currentIndexChanged.connect(self.on_repeat_changed)

        # --- Devices ---
        self.device_combo = QComboBox()
        self.refresh_devices_button = QPushButton("Refresh Devices")
        self.refresh_devices_button.clicked.connect(self.load_devices)
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)

        # --- Playlists UI ---
        self.playlist_list = QListWidget()
        self.playlist_tracks = QListWidget()

        self.playlist_list.itemSelectionChanged.connect(self.on_playlist_selected)

        self.play_playlist_button = QPushButton("Play Playlist")
        self.play_playlist_button.clicked.connect(self.on_play_playlist)

        self.open_playlist_button = QPushButton("Open in Spotify")
        self.open_playlist_button.clicked.connect(self.on_open_playlist)

        self.add_current_to_playlist_button = QPushButton("Add Current Track")
        self.add_current_to_playlist_button.clicked.connect(
            self.on_add_current_to_playlist
        )

        self.remove_track_button = QPushButton("Remove Selected Track")
        self.remove_track_button.clicked.connect(self.on_remove_selected_track)

        # --- Status label ---
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignLeft)

        # ---------- Layout ----------

        # Top row: cassette (left) + queue (right)
        top_row = QHBoxLayout()
        top_row.addWidget(self.cassette_widget, stretch=3)

        queue_col = QVBoxLayout()
        queue_col.addWidget(QLabel("Queue"))
        queue_col.addWidget(self.queue_list)
        queue_col.addWidget(self.clear_queue_button)
        top_row.addLayout(queue_col, stretch=2)

        # Playback buttons row
        playback_row = QHBoxLayout()
        playback_row.addWidget(self.prev_button)
        playback_row.addWidget(self.play_pause_button)
        playback_row.addWidget(self.next_button)

        # Controls row: shuffle / repeat / volume / devices
        controls_row = QHBoxLayout()
        controls_row.addWidget(self.shuffle_button)
        controls_row.addWidget(self.repeat_combo)
        controls_row.addSpacing(20)
        controls_row.addWidget(QLabel("Volume"))
        controls_row.addWidget(self.volume_slider)
        controls_row.addSpacing(20)
        controls_row.addWidget(QLabel("Device"))
        controls_row.addWidget(self.device_combo)
        controls_row.addWidget(self.refresh_devices_button)

        # Playlist area
        playlist_row = QHBoxLayout()

        # Left: playlists
        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("Playlists"))
        left_col.addWidget(self.playlist_list)
        left_buttons_row = QHBoxLayout()
        left_buttons_row.addWidget(self.play_playlist_button)
        left_buttons_row.addWidget(self.open_playlist_button)
        left_col.addLayout(left_buttons_row)

        # Right: tracks
        right_col = QVBoxLayout()
        right_col.addWidget(QLabel("Tracks"))
        right_col.addWidget(self.playlist_tracks)
        right_buttons_row = QHBoxLayout()
        right_buttons_row.addWidget(self.add_current_to_playlist_button)
        right_buttons_row.addWidget(self.remove_track_button)
        right_col.addLayout(right_buttons_row)

        playlist_row.addLayout(left_col, stretch=1)
        playlist_row.addLayout(right_col, stretch=2)

        # Root layout
        root_layout = QVBoxLayout()
        root_layout.addLayout(top_row)
        root_layout.addWidget(self.track_label)
        root_layout.addWidget(self.time_label)
        root_layout.addWidget(self.progress_slider)
        root_layout.addLayout(playback_row)
        root_layout.addLayout(controls_row)
        root_layout.addLayout(playlist_row)
        root_layout.addWidget(self.status_label)

        container = RgbBackground()
        container.setLayout(root_layout)
        self.setCentralWidget(container)

        # ---- RGB accent hookup (paste this right here) ----
        def _apply_accent(accent: QColor, hue: float = 0.0):
            accent_hex = accent.lighter(120).name()

            # Apply globally so it doesn't get "lost"
            QApplication.instance().setStyleSheet(f"""
            QPushButton {{
                background: rgba(30,30,30,180);
                border: 1px solid {accent_hex};
                border-radius: 8px;
                padding: 6px 10px;
                color: #eee;
            }}
            QPushButton:hover {{
                background: rgba(50,50,50,210);
            }}
            QProgressBar#songProgress::chunk {{
                background-color: {accent_hex};
            }}
            QSlider::handle:horizontal {{
                background: {accent_hex};
                border: 1px solid #111;
                width: 14px;
                margin: -6px 0;
                border-radius: 7px;
            }}
            """)

            # ✅ Keep cassette in sync with exact same RGB phase
            self.cassette_widget.set_rgb_sync(accent, hue)

        container.accentChanged = _apply_accent



        bg = self.centralWidget()
        if isinstance(bg, RgbBackground):
            bg.accentChanged = _apply_accent
        # -----------------------------------------------


        # Timer to refresh playback info every 2 seconds
        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.fetch_playback_state)
        self.timer.start()

        # Initial loads
        self.fetch_playback_state()
        self.load_devices()
        self.load_playlists()
        self.load_queue()




    def fetch_playback_state(self):
        # Don't stack requests if the backend/Spotify is slow
        if self._playback_in_flight:
            return

        self._playback_in_flight = True
        url = f"{api_client.BASE_URL}/playback/state"
        req = QNetworkRequest(QUrl(url))
        req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        self.playback_net.get(req)


    def _on_playback_reply(self, reply):
        self._playback_in_flight = False
        try:
            # IMPORTANT: never do "if reply.error():" (can crash with NetworkError)
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self._apply_playback_error(str(reply.errorString()))
                return

            raw = bytes(reply.readAll())
            if not raw:
                # backend returned empty body; treat as "no playback"
                self.apply_playback_state({})
                return

            playback = json.loads(raw.decode("utf-8"))
            if playback is None:
                playback = {}
            self.apply_playback_state(playback)

        except Exception as e:
            self._apply_playback_error(str(e))
        finally:
            reply.deleteLater()

    def _on_album_art_reply(self, reply):
        try:
            url = reply.url().toString()
            if url != self._pending_album_url:
                return

            if reply.error() != QNetworkReply.NetworkError.NoError:
                self.cassette_widget.set_album_art(None)
                return

            data = bytes(reply.readAll())
            pixmap = QPixmap()
            if not pixmap.loadFromData(data):
                self.cassette_widget.set_album_art(None)
                return

            self.cassette_widget.set_album_art(pixmap)

        finally:
            reply.deleteLater()



    # ---------- Album art helper (now feeds cassette) ----------

    def set_album_art_from_url(self, url: Optional[str]):
        if not url:
            self._pending_album_url = None
            self.cassette_widget.set_album_art(None)
            return

        if url == self._pending_album_url:
            return

        self._pending_album_url = url
        req = QNetworkRequest(QUrl(url))
        self.album_net.get(req)



    def _apply_playback_error(self, msg: str):
        self.track_label.setText("Error talking to backend")
        self.time_label.setText("--:-- / --:--")
        self.progress_slider.setValue(0)
        self.play_pause_button.setText("▶ Play")

        # cassette animations off
        self.cassette_widget.set_playing_state(False)
        self.cassette_widget.update_track(
            title="",
            artists="",
            album=None,
            progress_ms=0,
            duration_ms=0,
            genre_hint=None,
        )

        self.status_label.setText(f"Backend error: {msg}")


    # ---------- Queue helpers ----------

    def load_queue(self):
        try:
            data = api_client.get_queue()
            queue_items = data.get("queue", []) if data else []
        except Exception as e:
            self.status_label.setText(f"Error loading queue: {e}")
            return

        self.queue_list.clear()
        for tr in queue_items:
            text = f"{tr.get('artists', '')} — {tr.get('name', '')}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, tr.get("uri"))
            self.queue_list.addItem(item)

    def on_clear_queue(self):
        try:
            api_client.clear_queue()
            self.status_label.setText(
                "Tried to clear queue (Spotify API may not fully support this)."
            )
        except Exception as e:
            self.status_label.setText(f"Error clearing queue: {e}")
        self.load_queue()

    # ---------- UI callbacks: playback ----------

    def on_prev_clicked(self):
        try:
            api_client.previous_track()
            self.status_label.setText("Previous track")
        except Exception as e:
            self.status_label.setText(f"Error previous: {e}")
        self.fetch_playback_state()

    def on_play_pause_clicked(self):
        try:
            if self._last_is_playing:
                api_client.pause()
                self.status_label.setText("Pause")
            else:
                api_client.play()
                self.status_label.setText("Play")
        except Exception as e:
            self.status_label.setText(f"Error play/pause: {e}")

        # Ask for fresh state (async)
        self.fetch_playback_state()


    def on_next_clicked(self):
        try:
            api_client.next_track()
            self.status_label.setText("Next track")
        except Exception as e:
            self.status_label.setText(f"Error next: {e}")
        self.fetch_playback_state()

    def on_slider_pressed(self):
        self.progress_slider_is_dragging = True

    def on_slider_released(self):
        self.progress_slider_is_dragging = False
        if self.current_track_duration_ms <= 0:
            return

        value = self.progress_slider.value()  # 0–1000
        fraction = value / 1000.0
        new_pos_ms = int(self.current_track_duration_ms * fraction)

        try:
            api_client.seek(new_pos_ms)
            self.status_label.setText("Seek")
        except Exception as e:
            self.status_label.setText(f"Error seek: {e}")

        self.fetch_playback_state()

    # ---------- Volume / shuffle / repeat ----------

    def on_volume_released(self):
        value = self.volume_slider.value()
        try:
            api_client.set_volume(value)
            self.status_label.setText(f"Volume set to {value}%")
        except Exception as e:
            self.status_label.setText(f"Error volume: {e}")


    def on_shuffle_clicked(self, checked: bool):
        self.shuffle_state = checked
        try:
            api_client.set_shuffle(self.shuffle_state)
            self.shuffle_button.setText(
                "Shuffle: On" if self.shuffle_state else "Shuffle: Off"
            )
            self.status_label.setText(
                "Shuffle on" if self.shuffle_state else "Shuffle off"
            )
        except Exception as e:
            self.status_label.setText(f"Error shuffle: {e}")

    def on_repeat_changed(self, index: int):
        mode = self.repeat_combo.itemData(index)  # "off", "track", "context"
        try:
            api_client.set_repeat(mode)
            self.status_label.setText(f"Repeat mode: {mode}")
        except Exception as e:
            self.status_label.setText(f"Error repeat: {e}")

    # ---------- Devices ----------

    def load_devices(self):
        try:
            data = api_client.get_devices()
            devices = data.get("devices", []) if data else []
        except Exception as e:
            self.status_label.setText(f"Error loading devices: {e}")
            return

        self.device_combo.blockSignals(True)
        self.device_combo.clear()

        for d in devices:
            name = d.get("name") or "Unknown device"
            device_id = d.get("id")
            label = name
            if d.get("is_active"):
                label += " (active)"
            self.device_combo.addItem(label, userData=device_id)

        self.device_combo.blockSignals(False)

    def on_device_changed(self, index: int):
        device_id = self.device_combo.itemData(index)
        if not device_id:
            return
        try:
            api_client.transfer_playback(device_id)
            self.status_label.setText("Switched device")
        except Exception as e:
            self.status_label.setText(f"Error switching device: {e}")

    # ---------- Playlists ----------

    def load_playlists(self):
        try:
            data = api_client.get_playlists()
            playlists = data.get("playlists", []) if data else []
        except Exception as e:
            self.status_label.setText(f"Error loading playlists: {e}")
            return

        self.playlist_list.clear()
        for pl in playlists:
            name = pl.get("name") or "Unnamed"
            total = pl.get("tracks_total") or 0
            item = QListWidgetItem(f"{name} ({total})")
            item.setData(Qt.UserRole, pl.get("id"))
            item.setData(Qt.UserRole + 1, pl.get("external_url"))
            self.playlist_list.addItem(item)

    def on_playlist_selected(self):
        items = self.playlist_list.selectedItems()
        if not items:
            self.current_playlist_id = None
            self.current_playlist_url = None
            self.playlist_tracks.clear()
            return

        item = items[0]
        playlist_id = item.data(Qt.UserRole)
        playlist_url = item.data(Qt.UserRole + 1)
        self.current_playlist_id = playlist_id
        self.current_playlist_url = playlist_url
        self.load_playlist_tracks(playlist_id)

    def load_playlist_tracks(self, playlist_id: str):
        try:
            data = api_client.get_playlist_tracks(playlist_id)
            tracks = data.get("tracks", []) if data else []
        except Exception as e:
            self.status_label.setText(f"Error loading tracks: {e}")
            return

        self.playlist_tracks.clear()
        for tr in tracks:
            text = f"{tr.get('artists', '')} — {tr.get('name', '')}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, tr.get("uri"))
            self.playlist_tracks.addItem(item)

    def on_play_playlist(self):
        if not self.current_playlist_id:
            self.status_label.setText("Select a playlist first")
            return
        device_id = self.device_combo.currentData()
        try:
            api_client.play_playlist(self.current_playlist_id, device_id=device_id)
            self.status_label.setText("Playing playlist")
        except Exception as e:
            self.status_label.setText(f"Error playing playlist: {e}")

    def on_open_playlist(self):
        if not self.current_playlist_url:
            self.status_label.setText("No playlist URL")
            return
        try:
            webbrowser.open(self.current_playlist_url)
            self.status_label.setText("Opened playlist in Spotify")
        except Exception as e:
            self.status_label.setText(f"Error opening playlist: {e}")

    def on_add_current_to_playlist(self):
        if not self.current_playlist_id:
            self.status_label.setText("Select a playlist first")
            return
        if not self.current_track_uri:
            self.status_label.setText("No current track")
            return
        try:
            api_client.add_track_to_playlist(
                self.current_playlist_id,
                self.current_track_uri,
            )
            self.status_label.setText("Added current track to playlist")
            self.load_playlist_tracks(self.current_playlist_id)
        except Exception as e:
            self.status_label.setText(f"Error adding track: {e}")

    def on_remove_selected_track(self):
        if not self.current_playlist_id:
            self.status_label.setText("Select a playlist first")
            return
        items = self.playlist_tracks.selectedItems()
        if not items:
            self.status_label.setText("Select a track to remove")
            return
        item = items[0]
        track_uri = item.data(Qt.UserRole)
        if not track_uri:
            self.status_label.setText("No track URI")
            return
        try:
            api_client.remove_track_from_playlist(self.current_playlist_id, track_uri)
            self.status_label.setText("Removed track from playlist")
            self.load_playlist_tracks(self.current_playlist_id)
        except Exception as e:
            self.status_label.setText(f"Error removing track: {e}")

    # ---------- State refresh ----------

    def apply_playback_state(self, playback: dict):
        if not playback or not playback.get("item"):
            self.track_label.setText("Nothing playing. Start playback in Spotify.")
            self.time_label.setText("--:-- / --:--")
            self.progress_slider.setValue(0)
            self.play_pause_button.setText("▶ Play")
            self.current_track_duration_ms = 0
            self.current_track_uri = None

            self.cassette_widget.set_playing_state(False)
            self.cassette_widget.update_track(
                title="",
                artists="",
                album=None,
                progress_ms=0,
                duration_ms=0,
                genre_hint=None,
            )
            return

        is_playing = playback.get("is_playing", False)
        self._last_is_playing = is_playing
        track = playback["item"]
        track_id = track.get("id")
        name = track.get("name", "Unknown")
        artists = ", ".join(a.get("name", "") for a in track.get("artists", []))
        album_name = (track.get("album") or {}).get("name")
        self.track_label.setText(f"{name} — {artists}")
        self.current_track_uri = track.get("uri")

        progress_ms = playback.get("progress_ms") or 0
        duration_ms = track.get("duration_ms") or 0
        self.current_track_duration_ms = duration_ms

        # crude genre hint from text (purely for theming)
        text_blob = f"{name} {album_name or ''}".lower()
        genre_hint = None
        if any(word in text_blob for word in ["rock", "metal", "punk"]):
            genre_hint = "rock"
        elif any(word in text_blob for word in ["edm", "dance", "club", "remix"]):
            genre_hint = "edm"
        elif any(word in text_blob for word in ["chill", "lofi", "sleep", "study"]):
            genre_hint = "chill"
        elif any(word in text_blob for word in ["jazz", "swing", "bossa"]):
            genre_hint = "jazz"

        # update cassette widget
        self.cassette_widget.update_track(
            title=name,
            artists=artists,
            album=album_name,
            progress_ms=progress_ms,
            duration_ms=duration_ms,
            genre_hint=genre_hint,
        )
        self.cassette_widget.set_playing_state(is_playing)

        # Only update album art + queue if track changed
        if track_id != self.last_track_id:
            images = (track.get("album") or {}).get("images") or []
            image_url = images[0]["url"] if images else None
            self.set_album_art_from_url(image_url)
            self.load_queue()
            self.last_track_id = track_id

        # Update play/pause button
        self.play_pause_button.setText("⏸ Pause" if is_playing else "▶ Play")

        # Time label
        elapsed_str = self.ms_to_mmss(progress_ms)
        total_str = self.ms_to_mmss(duration_ms)
        self.time_label.setText(f"{elapsed_str} / {total_str}")

        # Progress slider (unless user is dragging it)
        if not self.progress_slider_is_dragging and duration_ms > 0:
            fraction = progress_ms / float(duration_ms)
            self.progress_slider.setValue(int(fraction * 1000))

        # Volume from device
        device = playback.get("device") or {}
        vol = device.get("volume_percent")
        if vol is not None and 0 <= vol <= 100:
            self.volume_slider.blockSignals(True)
            self.volume_slider.setValue(int(vol))
            self.volume_slider.blockSignals(False)

    @staticmethod
    def ms_to_mmss(ms: Optional[int]) -> str:
        if ms is None or ms <= 0:
            return "--:--"
        seconds = int(ms / 1000)
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"


# ---------- main ----------

def main():
    backend_proc = start_backend()

    app = QApplication(sys.argv)
    window = SpotifyPlayerWindow()
    window.show()
    exit_code = app.exec()

    try:
        backend_proc.terminate()
    except Exception:
        pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
