import logging
import os
import shutil
import subprocess
import sys
import webbrowser

from datetime import datetime
from typing import Any, Optional, Tuple

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QColor, QFont, QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QFileDialog,
    QFontDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core import morrenus_api
from ui.dialogs.custom_gifs import CustomGifsDialog
from ui.dialogs.dialog_helpers import create_standard_buttons
from utils.helpers import (
    create_checkbox_setting,
    create_font_setting,
    create_slider_setting,
    get_base_path,
    get_slscheevo_path,
    get_slscheevo_save_path,
    get_venv_python,
)
from utils.paths import Paths
from utils.settings import get_settings
from utils.yaml_config_manager import is_slssteam_mode_enabled

logger = logging.getLogger(__name__)


class MorrenusStatsWidget(QWidget):
    """Widget displaying Morrenus API user statistics."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.settings = get_settings()
        self.username_label = None
        self.daily_usage_bar = None
        self.expiration_label = None
        self.total_calls_label = None
        self.status_label = None
        self.refresh_button = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 0, 5)

        # Row 1: Username
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self.username_label = QLabel("User: --")
        self.username_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row1.addWidget(self.username_label)
        main_layout.addLayout(row1)

        # Progress Bar
        self.daily_usage_bar = QProgressBar()
        self.daily_usage_bar.setRange(0, 100)
        self.daily_usage_bar.setValue(0)
        self.daily_usage_bar.setFormat("Daily: --")
        self.daily_usage_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        accent_color = self.settings.value("accent_color", "#C06C84")
        self.daily_usage_bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid #444;
                border-radius: 0px;
                text-align: center;
                color: #fff;
                background-color: #222;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {accent_color};
            }}
        """
        )
        main_layout.addWidget(self.daily_usage_bar)

        # Row 2: Stats
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        self.expiration_label = QLabel("Expires: --")
        self.expiration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row2.addWidget(self.expiration_label)

        self.total_calls_label = QLabel("Total: --")
        self.total_calls_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row2.addWidget(self.total_calls_label)

        self.status_label = QLabel("Status: --")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row2.addWidget(self.status_label)

        main_layout.addLayout(row2)

        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.refresh_button.clicked.connect(self.refresh_stats)
        main_layout.addWidget(self.refresh_button)

    def refresh_stats(self) -> None:
        """Fetch and display latest stats from the API."""
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Loading...")

        stats = morrenus_api.get_user_stats()

        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh")

        if stats.get("error"):
            self._display_error_state()
        else:
            self._display_stats(stats)

    def _display_error_state(self) -> None:
        """Update UI to show error state."""
        self.username_label.setText("User: Error")
        self.total_calls_label.setText("Total: --")
        self.daily_usage_bar.setFormat("Daily: Error")
        self.daily_usage_bar.setValue(0)
        self.expiration_label.setText("Expires: --")
        self.status_label.setText("Status: Error")

    def _display_stats(self, stats: dict) -> None:
        """Update UI with fetched statistics."""
        self.username_label.setText(f"User: {stats.get('username', 'Unknown')}")
        self.total_calls_label.setText(f"Total: {stats.get('api_key_usage_count', 0)}")

        daily_usage = MorrenusStatsWidget._parse_int(stats.get("daily_usage", 0))
        daily_limit = MorrenusStatsWidget._parse_int(stats.get("daily_limit", 100))
        if daily_limit == 0:
            daily_limit = 100

        self.daily_usage_bar.setRange(0, daily_limit)
        self.daily_usage_bar.setValue(daily_usage)
        self.daily_usage_bar.setFormat(f"Daily: {daily_usage}/{daily_limit}")

        self._update_expiration_label(stats.get("api_key_expires_at", ""))

        status = "Active" if stats.get("can_make_requests", False) else "Blocked"
        self.status_label.setText(f"Status: {status}")

    @staticmethod
    def _parse_int(value: Any, default: int = 0) -> int:
        """Safely parse an integer value."""
        try:
            return int(value or default)
        except (TypeError, ValueError):
            return default

    def _update_expiration_label(self, expires_at: str) -> None:
        """Format and update the expiration label."""
        if not expires_at:
            self.expiration_label.setText("Expires: Never")
            return

        try:
            dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            self.expiration_label.setText(f"Expires: {dt.strftime('%d/%m/%Y')}")
        except ValueError:
            self.expiration_label.setText(f"Expires: {expires_at[:10]}")


class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(525)
        self.setMinimumHeight(650)
        self.resize(525, 650)
        self.settings = get_settings()
        self.main_window = parent
        self.accent_color = self.settings.value("accent_color", "#C06C84")
        self.main_layout = None
        self.tab_widget = None
        self.library_mode_checkbox = None
        self.auto_skip_single_choice_checkbox = None
        self.max_downloads_spinbox = None
        self.steamless_checkbox = None
        self.achievements_checkbox = None
        self.auto_apply_goldberg_checkbox = None
        self.application_shortcuts_checkbox = None
        self.sls_mode_checkbox = None
        self.sls_config_management_checkbox = None
        self.prompt_steam_restart_checkbox = None
        self.block_steam_updates_checkbox = None
        self.download_slssteam_button = None
        self.slssteam_status_label = None
        self.slssteam_hash_warning_label = None
        self.play_etw_checkbox = None
        self.play_lall_checkbox = None
        self.play_50hz_hum_checkbox = None
        self.test_etw_button = None
        self.test_lall_button = None
        self.accent_color_button = None
        self.accent_reset_button = None
        self.bg_color_button = None
        self.bg_reset_button = None
        self.titlebar_position_checkbox = None
        self.sonic_mode_checkbox = None
        self.gif_display_checkbox = None
        self.ignore_color_warnings_checkbox = None
        self.current_font = QFont()
        self.sgdb_api_key_input = None
        self.morrenus_stats_widget = None
        self.morrenus_tab_initialized = False

        # Save original API keys for restore on cancel
        self._original_morrenus_key = self.settings.value(
            "morrenus_api_key", "", type=str
        )
        self._original_sgdb_key = self.settings.value("sgdb_api_key", "", type=str)

        self._user_accent_color = self.settings.value(
            "user_accent_color",
            self.settings.value("accent_color", "#C06C84"),
            type=str,
        )
        self._user_background_color = self.settings.value(
            "user_background_color",
            self.settings.value("background_color", "#000000"),
            type=str,
        )
        self._original_titlebar_position = self.settings.value(
            "titlebar_position", "bottom", type=str
        )
        self._original_gif_display_enabled = self.settings.value(
            "gif_display_enabled", True, type=bool
        )

        logger.debug("Opening SettingsDialog.")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the UI layout."""
        self.main_layout = QVBoxLayout(self)

        self._create_tab_widget()
        self._setup_tabs()
        self.main_layout.addWidget(self.tab_widget)

        # Sync audio preview values
        if self.main_window and hasattr(self.main_window, "audio_manager"):
            # noinspection PyUnresolvedReferences
            self.main_window.audio_manager.sync_preview_values_from_settings()

        self._create_dialog_buttons()

    def _create_tab_widget(self) -> None:
        """Create and style the tab widget."""
        self.tab_widget = QTabWidget()
        bg_color = self.settings.value("background_color", "#1E1E1E")
        self.tab_widget.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: none;
            }}
            QTabBar::tab {{
                background: {bg_color};
                color: #888888;
                padding: 8px 16px;
                border: none;
            }}
            QTabBar::tab:selected {{
                color: {self.accent_color};
                border-bottom: 2px solid {self.accent_color};
            }}
            QTabBar::tab:!selected {{
                color: #888888;
            }}
        """
        )

    def _setup_tabs(self) -> None:
        """Initialize and add all settings tabs."""
        self._create_downloads_tab()
        self._create_morrenus_tab()
        self._create_steam_tab()
        self._create_tools_tab()
        self._create_audio_tab()
        self._create_style_tab()

    def _create_dialog_buttons(self) -> None:
        """Create standard Ok/Cancel buttons."""
        buttons = create_standard_buttons(self.accept, self.reject)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.main_layout.addWidget(buttons)

    def _create_api_key_setting(
        self,
        label: str,
        placeholder: str,
        setting_key: str,
        help_url: Optional[str] = None,
        help_text: Optional[str] = None,
    ) -> Tuple[QVBoxLayout, QLineEdit]:
        """Create an API key input field with password toggle and help link."""
        layout = QVBoxLayout()
        layout.setSpacing(5)

        layout.addWidget(QLabel(label))

        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)

        api_key_input = QLineEdit()
        api_key_input.setPlaceholderText(placeholder)
        api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        current_key = self.settings.value(setting_key, "", type=str)
        api_key_input.setText(current_key)

        toggle_btn = QPushButton("Show")
        toggle_btn.clicked.connect(
            lambda: SettingsDialog._toggle_api_key_visibility(api_key_input, toggle_btn)
        )

        input_layout.addWidget(api_key_input)
        input_layout.addWidget(toggle_btn)
        layout.addLayout(input_layout)

        accent_color = self.settings.value("accent_color", "#C06C84")
        if help_url:
            help_label = QLabel(
                f'<a href="{help_url}" style="color: {accent_color};">Get API key</a>'
            )
            help_label.setOpenExternalLinks(True)
            layout.addWidget(help_label)
        elif help_text:
            help_label = QLabel(help_text)
            help_label.setStyleSheet("color: #888888; font-size: 11px;")
            layout.addWidget(help_label)

        return layout, api_key_input

    @staticmethod
    def _toggle_api_key_visibility(
        input_field: QLineEdit, toggle_btn: QPushButton
    ) -> None:
        """Toggle API key visibility."""
        if input_field.echoMode() == QLineEdit.EchoMode.Password:
            input_field.setEchoMode(QLineEdit.EchoMode.Normal)
            toggle_btn.setText("Hide")
        else:
            input_field.setEchoMode(QLineEdit.EchoMode.Password)
            toggle_btn.setText("Show")

    def _create_downloads_tab(self) -> None:
        """Create the Downloads settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)

        # Download Settings Group
        dl_group = QGroupBox("Download Settings")
        dl_layout = QVBoxLayout()

        library_tooltip = "Detect Steam libraries and let you choose where to install games."
        if sys.platform == "linux":
            library_tooltip += (
                " On Linux, this also enables SLSsteam integration for those installs."
            )

        self.library_mode_checkbox = create_checkbox_setting(
            "Limit Downloads to Steam Libraries",
            "library_mode",
            False,
            self,
            library_tooltip,
        )
        dl_layout.addWidget(self.library_mode_checkbox)

        self.auto_skip_single_choice_checkbox = create_checkbox_setting(
            "Skip single-choice selection",
            "auto_skip_single_choice",
            False,
            self,
            "Automatically skip selection when only one option exists.",
        )
        dl_layout.addWidget(self.auto_skip_single_choice_checkbox)

        # Max Downloads
        max_dl_layout = QHBoxLayout()
        max_dl_label = QLabel("Maximum concurrent downloads")
        max_dl_label.setToolTip("Set maximum concurrent downloads (0-255)")

        self.max_downloads_spinbox = QSpinBox()
        self.max_downloads_spinbox.setRange(0, 255)
        current_max = self.settings.value("max_downloads", 255, type=int)
        self.max_downloads_spinbox.setValue(current_max)

        max_dl_layout.addWidget(max_dl_label)
        max_dl_layout.addWidget(self.max_downloads_spinbox)
        dl_layout.addLayout(max_dl_layout)

        dl_group.setLayout(dl_layout)
        layout.addWidget(dl_group)

        # Post-Processing Group
        pp_group = QGroupBox("Post-Processing")
        pp_layout = QVBoxLayout()

        self.achievements_checkbox = create_checkbox_setting(
            "Generate Steam Achievements",
            "generate_achievements",
            False,
            self,
            "Generate achievement files for your games after downloads.",
        )
        pp_layout.addWidget(self.achievements_checkbox)

        self.steamless_checkbox = create_checkbox_setting(
            "Remove Steam DRM with Steamless",
            "use_steamless",
            False,
            self,
            "Remove DRM from game executables after downloading.",
        )
        pp_layout.addWidget(self.steamless_checkbox)


        if sys.platform == "linux":
            self.application_shortcuts_checkbox = create_checkbox_setting(
                "Create Application Shortcuts",
                "create_application_shortcuts",
                False,
                self,
                "Create desktop shortcuts and install icons from SteamGridDB.",
            )
            pp_layout.addWidget(self.application_shortcuts_checkbox)
        else:
            self.application_shortcuts_checkbox = None

        pp_group.setLayout(pp_layout)
        layout.addWidget(pp_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Downloads")

    def goldberg_checked_warning(self) -> None:
        """Warn when Goldberg is enabled alongside Steam integration."""
        checkbox = self.auto_apply_goldberg_checkbox
        if not checkbox.isChecked():
            return

        integration_enabled = (
            self.sls_mode_checkbox.isChecked()
            if self.sls_mode_checkbox is not None
            else is_slssteam_mode_enabled()
        )
        if not integration_enabled:
            return

        warning = "You are about to enable Goldberg integration which is meant to be able to play your downloaded games WITHOUT Steam. If you are going to use Steam to play your games keep this disabled, otherwise things will break. You have been warned. Continue?"

        if self.goldberg_warning_box(checkbox, warning):
            return

    def goldberg_checked_warning_from_mode(self, type) -> None:
        """Warn when Steam integration is enabled while Goldberg is active."""
        checkbox = self.sls_mode_checkbox
        if not checkbox.isChecked():
            return
        try:
            if not self.auto_apply_goldberg_checkbox.isChecked():
                return
        except:
            if not self.settings.value("auto_apply_goldberg", False):
                return

        warning = f"You are about to enable {type} integration which is meant to be able to play your downloaded games WITH Steam. But you have Goldberg enabled, which is meant to be able to play your games WITHOUT Steam, if you are going to use Steam to play your games disable Goldberg in settings."

        if self.goldberg_warning_box(checkbox, warning):
            return

    def goldberg_warning_box(self, checkbox, warning) -> bool:
        # First
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Warning")
        msg_box.setText(warning)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.No:
            checkbox.setChecked(False)
            checkbox.checkbox.setCheckState(Qt.CheckState.Unchecked)
            return True

        # Second
        confirm_box = QMessageBox(self)
        confirm_box.setWindowTitle("Warning")
        confirm_box.setText(warning + " \n\nAre you sure?")
        confirm_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        confirm_box.setDefaultButton(QMessageBox.StandardButton.No)
        second_reply = confirm_box.exec()

        if second_reply == QMessageBox.StandardButton.No:
            checkbox.setChecked(False)
            checkbox.checkbox.setCheckState(Qt.CheckState.Unchecked)
            return True

        return False

    def _create_morrenus_tab(self) -> None:
        """Create the Morrenus API settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)

        # API Keys Group
        key_group = QGroupBox("API Keys")
        key_layout = QVBoxLayout()
        key_layout.setSpacing(10)

        morrenus_layout, self.api_key_input = self._create_api_key_setting(
            "Hubcap API Key:",
            "Paste your Hubcap API key",
            "morrenus_api_key",
            help_url="https://hubcapmanifest.com/",
        )
        key_layout.addLayout(morrenus_layout)

        if sys.platform == "linux":
            sgdb_layout, self.sgdb_api_key_input = self._create_api_key_setting(
                "SteamGridDB API Key:",
                "Paste your SteamGridDB API key",
                "sgdb_api_key",
                help_url="https://www.steamgriddb.com/profile/account",
            )
            key_layout.addLayout(sgdb_layout)
        else:
            self.sgdb_api_key_input = None

        key_group.setLayout(key_layout)
        layout.addWidget(key_group)

        # Stats Group
        stats_group = QGroupBox("Hubcap Stats")
        stats_layout = QVBoxLayout()
        stats_layout.setContentsMargins(5, 10, 5, 10)

        self.morrenus_stats_widget = MorrenusStatsWidget()
        stats_layout.addWidget(self.morrenus_stats_widget)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        layout.addStretch()

        # Connect tab change for lazy loading stats
        self.morrenus_tab_initialized = False
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        self.tab_widget.addTab(tab, "Integrations")

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change events."""
        if (
            self.tab_widget.tabText(index) == "Integrations"
            and not self.morrenus_tab_initialized
        ):
            self.morrenus_tab_initialized = True
            QTimer.singleShot(100, self.morrenus_stats_widget.refresh_stats)

    def _create_steam_tab(self) -> None:
        """Create the Steam settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)

        # Integration Group
        int_group = QGroupBox("Steam Integration")
        int_layout = QVBoxLayout()

        if sys.platform == "linux":
            wrapper_name = "SLSsteam"
            self.sls_mode_checkbox = None
            linux_hint = QLabel(
                "SLSsteam is enabled automatically for Steam library installs on Linux."
            )
            linux_hint.setWordWrap(True)
            int_layout.addWidget(linux_hint)
        else:
            wrapper_name = "GreenLuma"
            wrapper_full = "GreenLuma Wrapper Mode"
            tooltip = (
                "Integrate games with Steam using GreenLuma.\n"
                "Games appear in your Steam library automatically."
            )
            self.sls_mode_checkbox = create_checkbox_setting(
                wrapper_full, "slssteam_mode", False, self, tooltip
            )
            self.sls_mode_checkbox.stateChanged.connect(
                lambda: self.goldberg_checked_warning_from_mode(wrapper_name)
            )
            int_layout.addWidget(self.sls_mode_checkbox)

        self.sls_config_management_checkbox = create_checkbox_setting(
            f"{wrapper_name} Config Management",
            "sls_config_management",
            True,
            self,
            f"Allow ACCELA to manage {wrapper_name} configuration files.",
        )
        int_layout.addWidget(self.sls_config_management_checkbox)

        int_group.setLayout(int_layout)
        layout.addWidget(int_group)

        # Settings Group
        settings_group = QGroupBox("Steam Settings ")
        settings_layout = QVBoxLayout()

        self.prompt_steam_restart_checkbox = create_checkbox_setting(
            "Prompt Steam Restart",
            "prompt_steam_restart",
            True,
            self,
            "Show prompt to restart Steam after Steam-integrated downloads.",
        )
        settings_layout.addWidget(self.prompt_steam_restart_checkbox)


        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Steam")

    def _create_tools_tab(self) -> None:
        """Create the Tools settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)

        # Tools Group
        tools_group = QGroupBox("Tools")
        tools_layout = QVBoxLayout()

        SettingsDialog._add_tool_button(
            tools_layout,
            "Configure Achievements",
            "Launch SLScheevo to setup achievement credentials.",
            self.run_slscheevo,
        )

        SettingsDialog._add_tool_button(
            tools_layout,
            "Remove DRM",
            "Run Steamless manually on a game .exe.",
            self.run_steamless_manually,
        )

        self.download_slssteam_button = QPushButton("Open SLSsteam installer")
        self.download_slssteam_button.setToolTip(
            "Open the recommended SLSsteam installer page (GitHub)."
        )
        self.download_slssteam_button.clicked.connect(self.download_slssteam)

        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)

        # Windows Registry Group
        if sys.platform == "win32":
            reg_group = QGroupBox("Windows Registry")
            reg_layout = QVBoxLayout()

            SettingsDialog._add_tool_button(
                reg_layout,
                "Register Registry Entries",
                "Register accela:// URL protocol and .zip context menu entries.",
                SettingsDialog.register_registry_entries,
            )

            SettingsDialog._add_tool_button(
                reg_layout,
                "Remove Registry Entries",
                "Remove accela:// URL protocol and .zip context menu entries.",
                SettingsDialog.remove_registry_entries,
            )

            reg_group.setLayout(reg_layout)
            layout.addWidget(reg_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Tools")

    @staticmethod
    def _add_tool_button(layout: QVBoxLayout, text: str, tooltip: str, slot) -> None:
        """Helper to add a tool button with explanation text."""
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.clicked.connect(slot)
        layout.addWidget(btn)
        SettingsDialog._add_tool_explanation(layout, tooltip)

    @staticmethod
    def _add_tool_explanation(layout: QVBoxLayout, text: str) -> None:
        """Helper to add explanation label."""
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #888888; font-size: 11px;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

    def _create_audio_tab(self) -> None:
        """Create the Audio settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)

    def _create_style_tab(self) -> None:
        """Create the Style settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)

        # Color Group
        color_group = QGroupBox("Color Settings")
        color_layout = QVBoxLayout()

        # Accent
        acc_layout = QHBoxLayout()
        self.accent_color_button = QPushButton()
        self.accent_color_button.setStyleSheet(
            f"background-color: {self._user_accent_color};"
        )
        self.accent_reset_button = QPushButton("Reset")
        acc_layout.addWidget(QLabel("Accent Color:"))
        acc_layout.addWidget(self.accent_color_button)
        acc_layout.addWidget(self.accent_reset_button)
        acc_layout.addStretch()
        self.accent_color_button.clicked.connect(self.choose_accent_color)
        self.accent_reset_button.clicked.connect(self.reset_accent_color)
        color_layout.addLayout(acc_layout)

        # Background
        bg_layout = QHBoxLayout()
        self.bg_color_button = QPushButton()
        self.bg_color_button.setStyleSheet(
            f"background-color: {self._user_background_color};"
        )
        self.bg_reset_button = QPushButton("Reset")
        bg_layout.addWidget(QLabel("Background Color:"))
        bg_layout.addWidget(self.bg_color_button)
        bg_layout.addWidget(self.bg_reset_button)
        bg_layout.addStretch()
        self.bg_color_button.clicked.connect(self.choose_bg_color)
        self.bg_reset_button.clicked.connect(self.reset_bg_color)
        color_layout.addLayout(bg_layout)

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        # Font Group
        font_group = QGroupBox("Font Settings")
        font_layout = QVBoxLayout()
        font_children, self.font_button, self.font_reset_button = create_font_setting(
            self
        )
        self.font_button.clicked.connect(self.choose_font)
        self.font_reset_button.clicked.connect(self.reset_font)
        font_layout.addLayout(font_children)
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)

        # Display Group
        disp_group = QGroupBox("Display Settings")
        disp_layout = QVBoxLayout()

        self.titlebar_position_checkbox = QCheckBox("Move Titlebar to Top")
        is_top = self.settings.value("titlebar_position", "bottom", type=str) == "top"
        self.titlebar_position_checkbox.setChecked(is_top)
        self.titlebar_position_checkbox.setToolTip("Move the titlebar to the top.")
        self.titlebar_position_checkbox.stateChanged.connect(
            self.on_titlebar_position_changed
        )
        disp_layout.addWidget(self.titlebar_position_checkbox)
        SettingsDialog._add_checkbox_explanation(
            disp_layout, "Move the titlebar to the top of the window."
        )

        self.gif_display_checkbox = create_checkbox_setting(
            "Show GIF Display",
            "gif_display_enabled",
            True,
            self,
            "Show animated GIF in the main window.",
        )
        self.gif_display_checkbox.stateChanged.connect(self.on_gif_display_changed)
        disp_layout.addWidget(self.gif_display_checkbox)

        self.ignore_color_warnings_checkbox = create_checkbox_setting(
            "Ignore color warnings",
            "ignore_color_warnings",
            False,
            self,
            "Allow any color combination.",
        )
        disp_layout.addWidget(self.ignore_color_warnings_checkbox)

        disp_group.setLayout(disp_layout)
        layout.addWidget(disp_group)

        # Custom GIFs
        gif_layout = QHBoxLayout()
        custom_gifs_btn = QPushButton("Custom Gifs")
        custom_gifs_btn.clicked.connect(self.open_custom_gifs_dialog)
        gif_layout.addWidget(custom_gifs_btn)

        clear_cache_btn = QPushButton("Clear GIF Cache")
        clear_cache_btn.clicked.connect(self.clear_gif_cache)
        clear_cache_btn.setToolTip("Regenerate all GIFs.")
        gif_layout.addWidget(clear_cache_btn)
        layout.addLayout(gif_layout)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Style")

    @staticmethod
    def _add_checkbox_explanation(layout: QVBoxLayout, text: str) -> None:
        """Add indented explanation text for checkboxes."""
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #888888; font-size: 11px;")
        lbl.setWordWrap(True)
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.addSpacing(14)
        h_layout.addWidget(lbl)
        layout.addLayout(h_layout)

    # Color Handlers
    def choose_accent_color(self) -> None:
        color = QColorDialog.getColor()
        if not color.isValid():
            return
        if (
            not self.ignore_color_warnings_checkbox.isChecked()
            and SettingsDialog._is_too_dark(color)
        ):
            SettingsDialog._show_color_warning()
            return
        hex_c = color.name()
        self.accent_color_button.setStyleSheet(f"background-color: {hex_c};")

    def reset_accent_color(self) -> None:
        default = "#C06C84"
        self.settings.setValue("accent_color", default)
        self.accent_color_button.setStyleSheet(f"background-color: {default};")

    def choose_bg_color(self) -> None:
        color = QColorDialog.getColor()
        if not color.isValid():
            return
        hex_c = color.name()
        self.bg_color_button.setStyleSheet(f"background-color: {hex_c};")

    def reset_bg_color(self) -> None:
        default = "#000000"
        self.settings.setValue("background_color", default)
        self.bg_color_button.setStyleSheet(f"background-color: {default};")

    @staticmethod
    def _is_too_dark(color: QColor) -> bool:
        brightness = color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114
        return brightness < 15

    @staticmethod
    def _is_too_close(accent: QColor, bg: QColor, threshold: int = 100) -> bool:
        r_diff = bg.red() - accent.red()
        g_diff = bg.green() - accent.green()
        b_diff = bg.blue() - accent.blue()
        return (r_diff**2 + g_diff**2 + b_diff**2) ** 0.5 < threshold

    @staticmethod
    def _show_color_warning() -> None:
        QMessageBox.warning(
            None,
            "Invalid Color",
            "This color is too dark and will make the interface unusable.",
        )

    # Font Handlers
    def choose_font(self) -> None:
        font, ok = QFontDialog.getFont(self.current_font, self)
        if ok:
            self.current_font = font
            self.update_font_button_text()

    def reset_font(self) -> None:
        default = QFont("TrixieCyrG-Plain", 10)
        default.setBold(False)
        default.setItalic(False)
        self.current_font = default
        self.update_font_button_text()

    def update_font_button_text(self) -> None:
        if hasattr(self, "font_button") and hasattr(self, "current_font"):
            fam = self.current_font.family()
            size = self.current_font.pointSize()
            text = f"{fam} {size}pt"
            if self.current_font.bold():
                text += " Bold"
            if self.current_font.italic():
                text += " Italic"
            self.font_button.setText(text)
            self.font_button.setFont(self.current_font)

    # Display Handlers
    def on_titlebar_position_changed(self, state: int) -> None:
        pos = "top" if state == 2 else "bottom"
        self.settings.setValue("titlebar_position", pos)
        if self.main_window and hasattr(self.main_window, "reposition_titlebar"):
            # noinspection PyUnresolvedReferences
            self.main_window.reposition_titlebar(pos)

    def on_gif_display_changed(self, state: int) -> None:
        enabled = state == 2
        self.settings.setValue("gif_display_enabled", enabled)
        if self.main_window and hasattr(self.main_window, "update_gif_display"):
            # noinspection PyUnresolvedReferences
            self.main_window.update_gif_display(enabled)

    def accept(self) -> None:
        """Save all settings and close."""
        self._save_general_settings()
        self._save_download_settings()
        if not self._save_style_settings():
            return  # Style validation failed
        logger.info("All settings saved.")
        super().accept()

    def _save_general_settings(self) -> None:
        api_key = self.api_key_input.text().strip()
        self.settings.setValue("morrenus_api_key", api_key)
        if self.sgdb_api_key_input:
            sgdb_key = self.sgdb_api_key_input.text().strip()
            self.settings.setValue("sgdb_api_key", sgdb_key)

    def _save_download_settings(self) -> None:
        if self.sls_mode_checkbox is not None:
            self.settings.setValue("slssteam_mode", self.sls_mode_checkbox.isChecked())
        self.settings.setValue(
            "sls_config_management",
            self.sls_config_management_checkbox.isChecked(),
        )
        self.settings.setValue("library_mode", self.library_mode_checkbox.isChecked())
        self.settings.setValue(
            "auto_skip_single_choice",
            self.auto_skip_single_choice_checkbox.isChecked(),
        )
        self.settings.setValue(
            "prompt_steam_restart",
            self.prompt_steam_restart_checkbox.isChecked(),
        )
        self.settings.setValue(
            "generate_achievements", self.achievements_checkbox.isChecked()
        )
        self.settings.setValue(
            "use_steamless", self.steamless_checkbox.isChecked()
        )

        if self.application_shortcuts_checkbox:
            self.settings.setValue(
                "create_application_shortcuts",
                self.application_shortcuts_checkbox.isChecked(),
            )

        val = 255
        if hasattr(self, "max_downloads_spinbox"):
            try:
                val = max(0, min(255, int(self.max_downloads_spinbox.value())))
            except (ValueError, TypeError):
                pass
        self.settings.setValue("max_downloads", val)

    def _save_audio_settings(self) -> None:
        self.settings.setValue("play_etw", self.play_etw_checkbox.isChecked())
        self.settings.setValue("play_lall", self.play_lall_checkbox.isChecked())
        self.settings.setValue("play_50hz_hum", self.play_50hz_hum_checkbox.isChecked())
        self.settings.setValue("master_volume", self.master_volume_slider.value())
        self.settings.setValue("effects_volume", self.effects_volume_slider.value())
        self.settings.setValue("hum_volume", self.hum_volume_slider.value())
        if self.main_window and hasattr(self.main_window, "audio_manager"):
            # noinspection PyUnresolvedReferences
            self.main_window.audio_manager.apply_audio_settings()

    def _save_style_settings(self) -> bool:
        acc_s = self.accent_color_button.styleSheet()
        bg_s = self.bg_color_button.styleSheet()
        u_accent = acc_s.split("background-color: ")[1].split(";")[0]
        u_bg = bg_s.split("background-color: ")[1].split(";")[0]

        self.settings.setValue("user_accent_color", u_accent)
        self.settings.setValue("user_background_color", u_bg)

        prev_mode = self.settings.value("ui_mode", "default")
        applied_accent = u_accent
        applied_bg = u_bg
        self.settings.setValue("font-file", "")

        ignore = self.ignore_color_warnings_checkbox.isChecked()
        self.settings.setValue("ignore_color_warnings", ignore)
        if SettingsDialog._is_too_close(QColor(u_accent), QColor(u_bg)):
                QMessageBox.warning(
                    self,
                    "Invalid Color",
                    "Background too similar to accent color.",
                )
                return False

        self.settings.setValue("accent_color", applied_accent)
        self.settings.setValue("background_color", applied_bg)

        self.settings.setValue("font", self.current_font.family())
        self.settings.setValue("font-size", self.current_font.pointSize())

        style = "Normal"
        if self.current_font.bold():
            style = "Bold"
        if self.current_font.italic():
            style = "Italic"
        if self.current_font.bold() and self.current_font.italic():
            style = "Bold Italic"
        self.settings.setValue("font-style", style)

        if self.main_window and hasattr(self.main_window, "ui_state"):
            # noinspection PyUnresolvedReferences
            self.main_window.ui_state.apply_style_settings()

        return True

    def reject(self) -> None:
        """Revert settings on cancel."""
        self.settings.setValue("morrenus_api_key", self._original_morrenus_key)
        if self.sgdb_api_key_input:
            self.settings.setValue("sgdb_api_key", self._original_sgdb_key)

        # Revert live-previewed settings that were saved immediately
        self.settings.setValue("titlebar_position", self._original_titlebar_position)
        if self.main_window and hasattr(self.main_window, "reposition_titlebar"):
            # noinspection PyUnresolvedReferences
            self.main_window.reposition_titlebar(self._original_titlebar_position)

        self.settings.setValue(
            "gif_display_enabled", self._original_gif_display_enabled
        )
        if self.main_window and hasattr(self.main_window, "update_gif_display"):
            # noinspection PyUnresolvedReferences
            self.main_window.update_gif_display(self._original_gif_display_enabled)

        if self.main_window and hasattr(self.main_window, "audio_manager"):
            # noinspection PyUnresolvedReferences
            self.main_window.audio_manager.apply_audio_settings()
        super().reject()

    @staticmethod
    def _is_steam_updates_blocked() -> bool:
        """Check if steam.cfg exists."""
        try:
            from core.steam_helpers import find_steam_install

            path = find_steam_install()
            if not path:
                return False
            return os.path.exists(os.path.join(path, "steam.cfg"))
        except ImportError:
            return False

    @staticmethod
    def _apply_steam_updates_block(enabled: bool) -> None:
        """Manage steam.cfg file."""
        try:
            from core.steam_helpers import find_steam_install

            path = find_steam_install()
            if not path:
                logger.warning("Steam not found, skipping steam.cfg")
                return

            dest = os.path.join(path, "steam.cfg")
            src = Paths.deps("steam.cfg")

            if enabled:
                if not src.exists():
                    logger.error(f"Source steam.cfg missing: {src}")
                    return
                shutil.copy2(str(src), dest)
                logger.info(f"Copied steam.cfg to {dest}")
            elif os.path.exists(dest):
                os.remove(dest)
                logger.info(f"Removed steam.cfg from {dest}")

        except (ImportError, IOError) as e:
            logger.error(f"Failed to apply steam.cfg: {e}", exc_info=True)

    def _update_slssteam_status(self) -> None:
        """Check status update in background."""
        from core.tasks.download_slssteam_task import DownloadSLSsteamTask

        vf = get_base_path() / "SLSsteam" / "VERSION"
        if not vf.exists():
            self._set_label_viz("slssteam_status_label", False)
            self._set_label_viz("slssteam_hash_warning_label", False)
            return

        self._set_label_viz("slssteam_status_label", True)
        self._set_label_viz("slssteam_hash_warning_label", True)

        import threading

        def check() -> None:
            st = DownloadSLSsteamTask.check_update_available()
            if hasattr(self, "slssteam_status_label"):
                self.slssteam_status_label.setText(
                    SettingsDialog._format_status_text(st)
                )
            if hasattr(self, "slssteam_hash_warning_label"):
                self._update_slssteam_hash_warning(st)

        threading.Thread(target=check, daemon=True).start()

    def _set_label_viz(self, name: str, viz: bool) -> None:
        if hasattr(self, name):
            getattr(self, name).setVisible(viz)

    def _update_slssteam_hash_warning(self, status: dict) -> None:
        """Update hash warning text."""
        if not hasattr(self, "slssteam_hash_warning_label"):
            return

        lbl = self.slssteam_hash_warning_label
        mis = status.get("steamclient_mismatch")
        fnd = status.get("steamclient_found")
        err = status.get("steamclient_error")
        pink = "color: #C06C84; font-size: 11px;"
        green = "color: #7FC97F; font-size: 11px;"

        if mis:
            lbl.setText("Your Steam client is not compatible.")
            lbl.setStyleSheet(pink)
        elif err and fnd:
            lbl.setText("Could not verify compatibility.")
            lbl.setStyleSheet(pink)
        elif not fnd:
            lbl.setText("Steam client not found.")
            lbl.setStyleSheet(pink)
        elif mis is False:
            lbl.setText("Your Steam client is compatible.")
            lbl.setStyleSheet(green)
        lbl.setVisible(True)

    @staticmethod
    def _format_status_text(status: dict) -> str:
        if status.get("error"):
            return "Status unknown (error checking)"
        ver = status.get("latest_version", "Unknown")
        if not status.get("installed", False):
            return f"Not installed • Latest: {ver}"
        if status.get("update_available", False):
            return f"Update available • Latest: {ver}"
        return f"Up to date • Version: {status.get('installed_version', '?')}"

    def download_slssteam(self):
        """Open external recommended SLSsteam installer page instead of installing."""
        url = "https://github.com/Deadboy666/h3adcr-b?tab=readme-ov-file#headcrab"
        opened = False

        if sys.platform == "linux" and shutil.which("xdg-open"):
            try:
                result = subprocess.run(
                    ["xdg-open", url],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                opened = result.returncode == 0
            except Exception as e:
                logger.error(f"xdg-open failed: {e}")

        if not opened:
            try:
                browser = webbrowser.get()
                opened = browser.open_new_tab(url)
                logger.info("webbrowser.open_new_tab returned: %s", opened)
            except Exception as e:
                logger.warning(f"Webbrowser fallback failed: {e}")

        if not opened:
            try:
                opened = QDesktopServices.openUrl(QUrl(url))
                logger.info("QDesktopServices.openUrl returned: %s", opened)
            except Exception as e:
                logger.warning(f"QDesktopServices failed: {e}")

        if opened:
            try:
                self.accept()
            except Exception:
                pass
        else:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open external installer page. Please visit:\n{url}",
            )

    def run_slscheevo(self) -> None:
        """Launch SLScheevo."""
        path = get_slscheevo_path()
        if not os.path.exists(path):
            QMessageBox.critical(self, "Error", f"SLScheevo missing: {path}")
            return

        save = get_slscheevo_save_path()
        cmd = []
        if str(path).endswith(".py"):
            py = get_venv_python()
            cmd.append(
                py if py else ("python" if sys.platform == "win32" else "python3")
            )
        cmd.extend(
            [str(path), "--save-dir", str(save), "--noclear", "--max-tries", "101"]
        )

        SettingsDialog._launch_terminal_command(cmd, os.path.dirname(path))

    @staticmethod
    def _launch_terminal_command(
        cmd: list[str], cwd: str, needs_env: bool = False
    ) -> None:
        """Try to launch a command in a visible terminal."""
        cmd: list[str] = [str(part) for part in cmd]
        cwd = str(cwd)
        if sys.platform == "win32":
            q_cmd = " ".join([f'"{c}"' if " " in str(c) else str(c) for c in cmd])
            try:
                subprocess.Popen(
                    f'start cmd /k "cd /d {cwd} && {q_cmd}"',
                    shell=True,
                )
                return
            except OSError:
                pass
        else:
            terms = [
                ["wezterm", "start", "--always-new-process", "--"] + cmd,
                ["konsole", "-e"] + cmd,
                ["gnome-terminal", "--"] + cmd,
                ["ptyxis", "--"] + cmd,
                ["alacritty", "-e"] + cmd,
                ["tilix", "-e"] + cmd,
                ["xfce4-terminal", "-e"] + cmd,
                ["terminator", "-x"] + cmd,
                ["mate-terminal", "-e"] + cmd,
                ["lxterminal", "-e"] + cmd,
                ["xterm", "-e"] + cmd,
                ["kitty", "-e"] + cmd,
            ]
            for t in terms:
                try:
                    t_cmd: list[str] = [str(part) for part in t]
                    subprocess.Popen(t_cmd, cwd=cwd)
                    return
                except FileNotFoundError:
                    continue

        # Fallback dialog
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Terminal Not Found")
        msg_box.setText(
            "Could not automatically launch a terminal.\n"
            "Please open a terminal and run:\n"
        )
        msg_box.setInformativeText(" ".join(cmd))
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg_box.exec()

    def run_steamless_manually(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Executable", os.path.expanduser("~"), "*.exe"
        )
        if path and self.main_window:
            # noinspection PyUnresolvedReferences
            self.main_window.task_manager.run_steamless_manually(path)

    def open_custom_gifs_dialog(self) -> None:
        try:
            CustomGifsDialog(self.main_window).exec()
        except Exception as e:
            logger.error(f"Error opening GIF dialog: {e}")

    def clear_gif_cache(self) -> None:
        if (
            QMessageBox.question(
                self,
                "Clear Cache",
                "Regenerate all GIFs?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            if self.main_window:
                # noinspection PyUnresolvedReferences
                self.main_window.gif_manager.regenerate_anyway = True
                # noinspection PyUnresolvedReferences
                self.main_window.ui_state.update_gifs()

    @staticmethod
    def register_registry_entries() -> None:
        SettingsDialog._manage_registry("ACCELA.reg", "Registered successfully")

    @staticmethod
    def remove_registry_entries() -> None:
        SettingsDialog._manage_registry("ACCELA_uninstall.reg", "Removed successfully")

    @staticmethod
    def _manage_registry(filename: str, success_msg: str) -> None:
        if sys.platform != "win32":
            return

        # Locate registry file
        base = (
            os.path.join(getattr(sys, "_MEIPASS"), "deps")
            if getattr(sys, "frozen", False)
            else os.path.join(os.path.dirname(__file__), "..", "..", "deps")
        )
        reg_path = os.path.join(base, filename)

        if not os.path.exists(reg_path):
            QMessageBox.critical(None, "Error", f"Missing {filename}")
            return

        try:
            # Process template
            with open(reg_path, "r", encoding="utf-8-sig") as f:
                content = f.read().replace(
                    "[INSTALL_PATH]", sys.executable.replace("\\", "\\\\")
                )

            # Write temp file
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".reg", delete=False
            ) as tmp:
                tmp.write(content)
                tmp_name = tmp.name

            # Import
            subprocess.run(["regedit", "/s", str(tmp_name)], check=True, shell=True)
            os.unlink(tmp_name)
            QMessageBox.information(None, "Success", success_msg)

        except (IOError, OSError, subprocess.SubprocessError) as e:
            QMessageBox.critical(None, "Error", f"Registry error: {e}")
