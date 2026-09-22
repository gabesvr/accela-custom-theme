"""
Theme Manager.

Dreamy Y2K theme for ACCELA: every color is derived from the two user
settings (accent + background), bundled fonts are registered at startup and
one global stylesheet styles the main window and every dialog.

Widgets that paint themselves (player, titlebar, download scene) read the
current tokens through `tokens()`.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PyQt6.QtWidgets import QApplication

from utils.paths import Paths

logger = logging.getLogger(__name__)

BODY_FONT = "Nunito"
DISPLAY_FONT = "Silkscreen"
# Soft status colors that sit well on the pastel theme
STATUS_OK = "#3E9E6E"
STATUS_BUSY = "#D98A3A"
STATUS_ERROR = "#D0445C"

BUNDLED_FONTS = (
    # Static instances of the Nunito variable font: Qt picks the variable
    # font's ExtraLight default instance and ignores CSS weights otherwise.
    "fonts/Nunito-Regular.ttf",
    "fonts/Nunito-SemiBold.ttf",
    "fonts/Nunito-Bold.ttf",
    "fonts/Nunito-ExtraBold.ttf",
    "fonts/Silkscreen-Regular.ttf",
    "fonts/Silkscreen-Bold.ttf",
    "TrixieCyrG-Plain Regular.otf",  # upstream default, still selectable
)


def mix(a: QColor, b: QColor, amount: float) -> QColor:
    """Blend `a` into `b` (0 = pure b, 1 = pure a)."""
    return QColor(
        round(b.red() + (a.red() - b.red()) * amount),
        round(b.green() + (a.green() - b.green()) * amount),
        round(b.blue() + (a.blue() - b.blue()) * amount),
    )


def rgba(color: QColor, alpha: float) -> str:
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"


@dataclass(frozen=True)
class Tokens:
    """Design tokens for the current accent/background pair."""

    accent: QColor
    bg: QColor
    accent_hover: QColor
    accent_press: QColor
    dream: QColor  # lilac companion color, derived from the accent hue
    bg_top: QColor
    bg_bottom: QColor
    surface: QColor
    surface_alt: QColor
    border: QColor
    text: QColor
    text_muted: QColor
    on_accent: QColor
    is_dark: bool

    @classmethod
    def from_colors(cls, accent: str, background: str) -> "Tokens":
        a = QColor(accent)
        bg = QColor(background)
        is_dark = bg.lightness() < 110
        white = QColor("#FFFFFF")

        h, s, _, _ = a.getHsl()
        dream = QColor.fromHsl((h - 60) % 360, min(255, int(s * 0.55) + 40), 150 if is_dark else 200)

        if is_dark:
            surface = mix(white, bg, 0.07)
            bg_top = mix(a, bg, 0.10)
            bg_bottom = mix(dream, bg, 0.12)
        else:
            surface = mix(white, bg, 0.55)
            bg_top = mix(white, bg, 0.35)
            bg_bottom = mix(dream, mix(a, bg, 0.05), 0.16)

        return cls(
            accent=a,
            bg=bg,
            accent_hover=a.lighter(115),
            accent_press=a.darker(115),
            dream=dream,
            bg_top=bg_top,
            bg_bottom=bg_bottom,
            surface=surface,
            surface_alt=mix(a, surface, 0.07),
            border=mix(a, bg, 0.20),
            text=a if not is_dark else mix(white, a, 0.35),
            text_muted=mix(a, bg, 0.55),
            on_accent=bg if not is_dark else white,
            is_dark=is_dark,
        )

    def window_gradient(self) -> str:
        return (
            "qlineargradient(x1:0, y1:0, x2:0.35, y2:1, "
            f"stop:0 {self.bg_top.name()}, stop:0.55 {self.bg.name()}, stop:1 {self.bg_bottom.name()})"
        )

    def accent_gradient(self) -> str:
        return (
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {self.accent.name()}, stop:1 {mix(self.dream, self.accent, 0.55).name()})"
        )


_tokens = Tokens.from_colors("#8E3B56", "#F5F2EB")


def tokens() -> Tokens:
    """Tokens for the palette applied most recently."""
    return _tokens


def normal_palette_colors(t: Tokens) -> Dict[QPalette.ColorRole, QColor]:
    """Define colors for the normal palette state."""
    return {
        QPalette.ColorRole.Window: t.bg,
        QPalette.ColorRole.WindowText: t.text,
        QPalette.ColorRole.Base: t.surface,
        QPalette.ColorRole.AlternateBase: t.surface_alt,
        QPalette.ColorRole.ToolTipBase: t.surface,
        QPalette.ColorRole.ToolTipText: t.text,
        QPalette.ColorRole.Text: t.text,
        QPalette.ColorRole.Button: t.surface,
        QPalette.ColorRole.ButtonText: t.text,
        QPalette.ColorRole.BrightText: t.accent_hover,
        QPalette.ColorRole.Link: t.accent_hover,
        QPalette.ColorRole.Highlight: t.accent,
        QPalette.ColorRole.HighlightedText: t.on_accent,
        QPalette.ColorRole.PlaceholderText: t.text_muted,
    }


def disabled_palette_colors(t: Tokens) -> Dict[QPalette.ColorRole, QColor]:
    """Define colors for the disabled palette state."""
    faded = mix(t.text, t.bg, 0.4)
    return {
        QPalette.ColorRole.Button: t.surface_alt,
        QPalette.ColorRole.ButtonText: faded,
        QPalette.ColorRole.Text: faded,
        QPalette.ColorRole.WindowText: faded,
        QPalette.ColorRole.Base: t.bg,
    }


def apply_palette(app: QApplication, accent: str, background: str) -> None:
    """Apply the Fusion style, palette and global stylesheet."""
    global _tokens
    _tokens = Tokens.from_colors(accent, background)

    app.setStyle("Fusion")
    palette = QPalette()
    for role, color in normal_palette_colors(_tokens).items():
        palette.setColor(role, color)
    for role, color in disabled_palette_colors(_tokens).items():
        palette.setColor(QPalette.ColorGroup.Disabled, role, color)

    app.setPalette(palette)
    app.setStyleSheet(build_stylesheet(_tokens))


def build_stylesheet(t: Tokens) -> str:
    """Global stylesheet: soft rounded surfaces, pill buttons, dreamy accents."""
    accent = t.accent.name()
    text = t.text.name()
    muted = t.text_muted.name()
    surface = t.surface.name()
    surface_alt = t.surface_alt.name()
    border = t.border.name()
    on_accent = t.on_accent.name()
    faded = mix(t.text, t.bg, 0.4).name()
    tint = rgba(t.accent, 0.10)
    tint_strong = rgba(t.accent, 0.18)
    dream_tint = rgba(t.dream, 0.35)

    return f"""
        * {{
            outline: 0;
        }}

        QMainWindow, QWidget#central_widget, QWidget#main_container {{
            background: {t.window_gradient()};
        }}

        QWidget#drop_zone_container {{
            background: transparent;
        }}

        QDialog {{
            background: {t.window_gradient()};
            color: {text};
        }}

        QLabel {{
            color: {text};
            background: transparent;
        }}

        QToolTip {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 6px 10px;
        }}

        /* Buttons: soft pills */
        QPushButton {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 14px;
            padding: 6px 16px;
            font-weight: 700;
        }}

        QPushButton:hover {{
            background-color: {surface_alt};
            border-color: {accent};
        }}

        QPushButton:pressed {{
            background-color: {tint_strong};
        }}

        QPushButton:checked, QPushButton:default {{
            background: {t.accent_gradient()};
            color: {on_accent};
            border: 1px solid {accent};
        }}

        QPushButton:disabled {{
            background-color: {surface_alt};
            color: {faded};
            border: 1px dashed {border};
            font-weight: 400;
        }}

        /* Text inputs */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 12px;
            padding: 6px 10px;
            selection-background-color: {accent};
            selection-color: {on_accent};
        }}

        QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover,
        QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
            border-color: {muted};
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
        QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border: 1px solid {accent};
            background-color: {surface};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 22px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 10px;
            selection-background-color: {tint_strong};
            selection-color: {text};
            padding: 4px;
        }}

        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            border: none;
            width: 16px;
        }}

        /* Checkboxes & radios */
        QCheckBox, QRadioButton {{
            color: {text};
            spacing: 8px;
            padding: 4px;
            background: transparent;
        }}

        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            background: {surface};
            border: 1.5px solid {muted};
        }}

        QCheckBox::indicator {{
            border-radius: 6px;
        }}

        QRadioButton::indicator {{
            border-radius: 9px;
        }}

        QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
            border-color: {accent};
            background: {surface_alt};
        }}

        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background: {t.accent_gradient()};
            border-color: {accent};
        }}

        /* Lists */
        QListWidget, QListView, QTreeView, QTableView {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 14px;
            padding: 4px;
        }}

        QListWidget::item, QListView::item {{
            color: {text};
            border-radius: 10px;
            padding: 6px 8px;
            margin: 1px 0;
        }}

        QListWidget::item:hover, QListView::item:hover {{
            background-color: {tint};
        }}

        QListWidget::item:selected, QListView::item:selected {{
            background-color: {tint_strong};
            color: {text};
        }}

        QListWidget::item:checked {{
            background-color: {dream_tint};
            font-weight: 700;
        }}

        QListWidget::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 6px;
            border: 1.5px solid {muted};
            background: {surface};
        }}

        QListWidget::indicator:checked {{
            background: {t.accent_gradient()};
            border-color: {accent};
        }}

        QHeaderView::section {{
            background: {surface_alt};
            color: {text};
            border: none;
            padding: 6px;
            font-weight: 700;
        }}

        /* Group boxes become soft cards */
        QGroupBox {{
            background-color: {rgba(t.surface, 0.75)};
            border: 1px solid {border};
            border-radius: 16px;
            margin-top: 18px;
            padding: 14px 10px 10px 10px;
            font-weight: 700;
            color: {text};
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 14px;
            padding: 0 6px;
            color: {accent};
        }}

        /* Tabs as pills */
        QTabWidget::pane {{
            border: 1px solid {border};
            border-radius: 16px;
            background: {rgba(t.surface, 0.6)};
            top: -1px;
        }}

        QTabBar::tab {{
            background: transparent;
            color: {muted};
            border-radius: 12px;
            padding: 6px 14px;
            margin: 4px 2px;
            font-weight: 700;
        }}

        QTabBar::tab:hover {{
            background: {tint};
            color: {text};
        }}

        QTabBar::tab:selected {{
            background: {t.accent_gradient()};
            color: {on_accent};
        }}

        /* Progress bars: rounded with an accent -> lilac glow */
        QProgressBar {{
            background-color: {surface_alt};
            border: 1px solid {border};
            border-radius: 8px;
            color: {text};
            text-align: center;
            min-height: 14px;
            font-weight: 700;
        }}

        QProgressBar::chunk {{
            background: {t.accent_gradient()};
            border-radius: 7px;
        }}

        /* Sliders */
        QSlider::groove:horizontal {{
            height: 4px;
            background: {tint_strong};
            border-radius: 2px;
        }}

        QSlider::sub-page:horizontal {{
            background: {t.accent_gradient()};
            border-radius: 2px;
        }}

        QSlider::handle:horizontal {{
            width: 12px;
            height: 12px;
            margin: -4px 0;
            border-radius: 6px;
            background: {surface};
            border: 2px solid {accent};
        }}

        /* Slim rounded scrollbars */
        QScrollArea {{
            background: transparent;
            border: none;
        }}

        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 4px 2px;
        }}

        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
            margin: 2px 4px;
        }}

        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            background: {rgba(t.accent, 0.35)};
            border-radius: 3px;
            min-height: 24px;
            min-width: 24px;
        }}

        QScrollBar::handle:hover {{
            background: {rgba(t.accent, 0.6)};
        }}

        QScrollBar::add-line, QScrollBar::sub-line,
        QScrollBar::add-page, QScrollBar::sub-page {{
            background: none;
            width: 0;
            height: 0;
        }}

        /* Menus */
        QMenu {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 12px;
            padding: 6px;
        }}

        QMenu::item {{
            padding: 6px 14px;
            border-radius: 8px;
        }}

        QMenu::item:selected {{
            background-color: {tint_strong};
        }}

        QMessageBox QLabel {{
            color: {text};
        }}
    """


def _resolve_font_path(font_resource: Union[str, Path]) -> Path:
    """Resolve the provided font resource to a concrete Path object."""
    try:
        if isinstance(font_resource, str):
            candidate = Path(font_resource)
            if candidate.is_absolute() and candidate.exists():
                return candidate
            return Paths.resource(font_resource)

        if isinstance(font_resource, Path):
            return font_resource

        return Paths.resource(str(font_resource))
    except TypeError:
        # Fallback for unexpected types
        return Paths.resource(str(font_resource))


def register_bundled_fonts() -> None:
    """Make the theme fonts available to QFont/QFontDatabase by family name."""
    for resource in BUNDLED_FONTS:
        path = _resolve_font_path(resource)
        if not path.exists():
            logger.warning(f"Bundled font missing: {path}")
            continue
        if QFontDatabase.addApplicationFont(str(path)) == -1:
            logger.warning(f"QFontDatabase failed to load bundled font: {path}")


def display_font(pixel_size: int = 16, bold: bool = False) -> QFont:
    """Pixel display font; multiples of 8px keep the pixels crisp."""
    font = QFont(DISPLAY_FONT)
    font.setPixelSize(pixel_size)
    font.setBold(bold)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return font


def _load_and_set_font(
    app: QApplication, font_path: Path, current_font: Optional[QFont]
) -> Tuple[bool, str]:
    """Load a font file from disk and set it to the application."""
    logger.debug(f"Attempting to load font from: {font_path}")

    if not font_path.exists():
        logger.warning(f"Font file not found at: {font_path}")
        return False, str(font_path)

    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id == -1:
        logger.warning(f"QFontDatabase failed to load font: {font_path}")
        return False, str(font_path)

    families = QFontDatabase.applicationFontFamilies(font_id)
    if not families:
        logger.warning(f"No font families returned for: {font_path}")
        return False, str(font_path)

    font_name = families[0]

    if current_font:
        # Update existing font object with new family
        current_font.setFamily(font_name)
        new_font = current_font
    else:
        # Create new default font
        new_font = QFont(font_name, 10)

    app.setFont(new_font)
    return True, font_name


def apply_font(
    app: QApplication,
    font: Optional[QFont],
    font_file: Optional[Union[str, Path]],
) -> Tuple[bool, Union[str, Path]]:
    """
    Applies the font to the application.

    If font_file is provided, loads that font file and applies it.
    If font is provided (with a family name), uses it when it is installed or
    bundled. Otherwise falls back to the theme's body font.
    """
    register_bundled_fonts()

    # Case 1: Specific font file provided
    if font_file:
        path = _resolve_font_path(font_file)
        return _load_and_set_font(app, path, font)

    # Case 2: Installed or bundled font provided
    if font and font.family():
        font_family = font.family()
        if font_family in QFontDatabase.families():
            logger.debug(f"Using font: {font_family}")
            app.setFont(font)
            return True, font_family

        logger.debug(f"Font family '{font_family}' not available, using {BODY_FONT}")

    # Case 3: Fallback to the theme body font
    fallback = QFont(font) if font else QFont()
    fallback.setFamily(BODY_FONT)
    if fallback.pointSize() <= 0:
        fallback.setPointSize(10)
    app.setFont(fallback)
    return BODY_FONT in QFontDatabase.families(), BODY_FONT


def update_appearance(
    app: QApplication,
    accent: str = "#8E3B56",
    background: str = "#F5F2EB",
    font: Optional[QFont] = None,
    font_file: Optional[Union[str, Path]] = None,
) -> Tuple[bool, Union[str, Path]]:
    """
    Apply a dynamic palette and custom font to the application.

    Args:
        app: The QApplication instance.
        accent: Hex string for accent color.
        background: Hex string for background color.
        font: Optional QFont object for settings.
        font_file: Relative resource path to load custom font.
    """
    apply_palette(app, accent, background)
    return apply_font(app, font, font_file)
