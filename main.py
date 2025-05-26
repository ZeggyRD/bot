#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ── ENSURE modules/ IS ON sys.path ──
import os, sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 1) Añade la raíz del proyecto
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# 2) Añade la carpeta modules
MODULES_DIR = os.path.join(SCRIPT_DIR, "modules")
if MODULES_DIR not in sys.path:
    sys.path.insert(0, MODULES_DIR)

import json                           # for load_config / save_config
import time
import random
import logging
from datetime import datetime
import uiautomator2 as u2
import shutil
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import subprocess
import traceback
import re

# ── IMPORTS DE PyQt5 ──
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QFileDialog,
    QFrame,
    QComboBox,
    QTextEdit,
    QMessageBox,
    QInputDialog
)
from PyQt5.QtGui  import QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# ── BASE SCRIPT DIR & SLOW MODE ──
SLOW_MODE_FACTOR = 1.0

# ── ONLY import the instance from your modules folder ──
from modules.human_behavior import human_behavior

# ── other module imports ──
from modules.login_manager   import login_manager
from modules.account_manager import account_manager
from modules.android_device  import AndroidDevice
from modules.account_creator import create_multiple_accounts

# ── main_logger setup ──
main_logger = logging.getLogger("PlaylistPlayerMain")
main_logger.setLevel(logging.DEBUG)
fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(fmt)
main_logger.addHandler(ch)

# ── wrap human_delay ──
def _human_delay_wrapper(min_sec, max_sec, personality=None, use_factor=True):
    # calcula factores de ralentización
    base_factor = SLOW_MODE_FACTOR if use_factor else 1.0
    personality_factor = getattr(personality, "get_delay_factor", lambda: 1.0)()
    total_min = min_sec * base_factor * personality_factor
    total_max = max_sec * base_factor * personality_factor
    # llama a la función de tu módulo
    return human_behavior.human_delay(total_min, total_max)

# ── root logger for your app ──
log_dir = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"main_{datetime.now():%Y%m%d_%H%M%S}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("OTWMusicSystem")
main_logger = logger

# ── inject into sub-modules ──
import importlib
for mod in (
    "login_manager",
    "account_manager",
    "android_device",
    "scripts.track_player",
    "scripts.artist_player",
    "scripts.playlist_mode",
    "scripts.set_proxy",
):
    pkg = mod.startswith("scripts.") and mod or f"modules.{mod}"
    m = importlib.import_module(pkg)
    setattr(m, "main_logger", logger)

# ── finally inject into your human_behavior instance ──
import modules.human_behavior as _hb_mod
_hb_mod.human_behavior.main_logger = logger  

# Global style variables
BACKGROUND_COLOR = "#121212"  # Dark background
TEXT_COLOR = "#FFFFFF"  # White text
BUTTON_COLOR = "#1DB954"  # Spotify green
SECONDARY_COLOR = "#282828"  # Dark gray for panels

# Constantes
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "config.json")

def load_config():
    """Carga la configuración desde el archivo config.json"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config
        else:
            logger.warning(f"Archivo de configuración no encontrado: {CONFIG_FILE}")
            return {}
    except Exception as e:
        logger.error(f"Error al cargar la configuración: {e}")
        return {}

def save_config(config):
    """Guarda la configuración en el archivo config.json"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        logger.info(f"Configuración guardada en: {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Error al guardar la configuración: {e}")

class WorkerThread(QThread):
    """Clase para ejecutar tareas en segundo plano"""
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, task_type, params=None):
        super().__init__()
        self.task_type = task_type
        self.params = params if params else {}
    
    def run(self):
        try:
            if self.task_type == "login":
                self.update_signal.emit("Iniciando proceso de login en dispositivos...")
                success = login_manager.process_all_devices()
                if success:
                    self.finished_signal.emit(True, "Login completado exitosamente")
                else:
                    self.finished_signal.emit(False, "Error en el proceso de login")
            
            elif self.task_type == "play_tracks":
                self.update_signal.emit("Iniciando reproducción de tracks...")
                from scripts.track_player import track_mode
                track_mode()
                self.finished_signal.emit(True, "Reproducción de tracks completada")
            
            elif self.task_type == "play_artists":
                self.update_signal.emit("Iniciando reproducción de artistas...")
                from scripts.artist_player import artist_mode
                artist_mode()
                self.finished_signal.emit(True, "Reproducción de artistas completada")
            
            elif self.task_type == "play_playlists":
                self.update_signal.emit("Iniciando reproducción de playlists...")
                from scripts.playlist_mode import playlist_mode
                playlist_mode()
                self.finished_signal.emit(True, "Reproducción de playlists completada")
            
            elif self.task_type == "set_proxy":
                self.update_signal.emit("Configurando proxies en dispositivos...")
                from scripts.set_proxy import set_proxy
                success = set_proxy()
                if success:
                    self.finished_signal.emit(True, "Proxies configurados exitosamente")
                else:
                    self.finished_signal.emit(False, "Error al configurar proxies")
            
            elif self.task_type == "create_accounts":
                count = self.params.get("count", 1)
                headless = self.params.get("headless", True)
                self.update_signal.emit(f"Creando {count} cuentas de Spotify...")
                success_count = create_multiple_accounts(count, headless)
                if success_count > 0:
                    self.finished_signal.emit(True, f"Se crearon {success_count} cuentas exitosamente")
                else:
                    self.finished_signal.emit(False, "Error al crear cuentas")
            
            else:
                self.update_signal.emit(f"Tarea desconocida: {self.task_type}")
                self.finished_signal.emit(False, f"Tarea desconocida: {self.task_type}")
        
        except Exception as e:
            logger.error(f"Error en worker thread: {e}")
            self.update_signal.emit(f"Error: {str(e)}")
            self.finished_signal.emit(False, f"Error: {str(e)}")

class LoginScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BACKGROUND_COLOR}; color: {TEXT_COLOR};")
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        
        # Title and subtitle
        title_label = QLabel("OTW")
        title_label.setFont(QFont("Segoe UI", 40, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        
        subtitle_label = QLabel("OTW Music Login")
        subtitle_label.setFont(QFont("Segoe UI", 16))
        subtitle_label.setAlignment(Qt.AlignCenter)
        
        # Login button
        self.login_button = QPushButton("ACCEDER")
        self.login_button.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; border-radius: 20px; padding: 10px;")
        self.login_button.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.login_button.setMinimumHeight(50)
        self.login_button.setMinimumWidth(200)
        
        # Add widgets to layout
        main_layout.addStretch(1)
        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)
        main_layout.addSpacing(40)
        main_layout.addWidget(self.login_button, 0, Qt.AlignCenter)
        main_layout.addStretch(1)
        
        # Set layout margins
        main_layout.setContentsMargins(50, 50, 50, 50)
        
        self.setLayout(main_layout)


class MainScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BACKGROUND_COLOR}; color: {TEXT_COLOR};")
        self.current_mode = "PLAY TRACKS"
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        
        # User info section
        user_frame = QFrame()
        user_frame.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px;")
        user_layout = QHBoxLayout()
        
        # User icon placeholder
        user_icon = QLabel()
        # In a real implementation, you would load an actual user icon
        user_icon.setFixedSize(40, 40)
        user_icon.setStyleSheet("background-color: #555555; border-radius: 20px;")
        
        # User info
        user_info = QVBoxLayout()
        username_label = QLabel("ROCKSTAR")
        username_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        email_label = QLabel("SonOfGod@Holy.com")
        email_label.setFont(QFont("Segoe UI", 10))
        
        user_info.addWidget(username_label)
        user_info.addWidget(email_label)
        
        user_layout.addWidget(user_icon)
        user_layout.addLayout(user_info)
        user_layout.addStretch()
        
        user_frame.setLayout(user_layout)
        
        # Logo section
        logo_frame = QFrame()
        logo_frame.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px;")
        logo_layout = QVBoxLayout()
        
        logo_label = QLabel("OTWMUSIC")  # Using OTWMUSIC as shown in the screenshots
        logo_label.setFont(QFont("Segoe UI", 28, QFont.Bold))
        logo_label.setAlignment(Qt.AlignCenter)
        
        logo_layout.addWidget(logo_label)
        logo_frame.setLayout(logo_layout)
        
        # Mode section
        mode_layout = QVBoxLayout()
        mode_text = QLabel("MODE")
        mode_text.setFont(QFont("Segoe UI", 12))
        mode_text.setAlignment(Qt.AlignCenter)
        
        self.mode_label = QPushButton(self.current_mode)
        self.mode_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.mode_label.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px; padding: 5px;")
        self.mode_label.setEnabled(False)
        
        mode_layout.addWidget(mode_text)
        mode_layout.addWidget(self.mode_label)
        
        # Mode buttons
        modes_layout = QHBoxLayout()
        
        self.play_tracks_btn = QPushButton("PLAY TRACKS")
        self.login_btn = QPushButton("LOG IN")
        self.play_artist_btn = QPushButton("PLAY ARTIST")
        self.play_playlists_btn = QPushButton("PLAY PLAYLISTS")
        
        for btn in [self.play_tracks_btn, self.login_btn, self.play_artist_btn, self.play_playlists_btn]:
            btn.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 5px; padding: 5px;")
            btn.setFont(QFont("Segoe UI", 10))
            btn.setFixedHeight(30)
            btn.clicked.connect(self.change_mode)
        
        modes_layout.addWidget(self.play_tracks_btn)
        modes_layout.addWidget(self.login_btn)
        modes_layout.addWidget(self.play_artist_btn)
        modes_layout.addWidget(self.play_playlists_btn)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("⏮")
        self.play_button = QPushButton("▶️")
        self.next_button = QPushButton("⏭")
        
        for btn in [self.prev_button, self.play_button, self.next_button]:
            btn.setStyleSheet(f"background-color: #3D5AFE; color: {TEXT_COLOR}; border-radius: 20px;")
            btn.setFixedSize(60, 60)
            btn.setFont(QFont("Segoe UI", 16))
        
        controls_layout.addStretch()
        controls_layout.addWidget(self.prev_button)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.next_button)
        controls_layout.addStretch()
        
        # Log section
        log_frame = QFrame()
        log_frame.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px;")
        log_layout = QVBoxLayout()
        
        log_title = QLabel("Activity Log")
        log_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet(f"background-color: #1A1A1A; color: {TEXT_COLOR}; border-radius: 5px;")
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMinimumHeight(100)
        
        log_layout.addWidget(log_title)
        log_layout.addWidget(self.log_text)
        
        log_frame.setLayout(log_layout)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.home_button = QPushButton("🏠")
        self.resource_button = QPushButton("➕")
        self.settings_button = QPushButton("⚙")
        
        for btn in [self.home_button, self.resource_button, self.settings_button]:
            btn.setStyleSheet(f"background-color: {SECONDARY_COLOR}; color: #3D5AFE; border-radius: 5px;")
            btn.setFixedSize(80, 50)
            btn.setFont(QFont("Segoe UI", 14))
        
        nav_layout.addWidget(self.home_button)
        nav_layout.addWidget(self.resource_button)
        nav_layout.addWidget(self.settings_button)
        
        # Developer attribution
        developer_label = QLabel("Developed by GALAXIBYTE")
        developer_label.setFont(QFont("Segoe UI", 8))
        developer_label.setAlignment(Qt.AlignCenter)
        
        # Add all sections to main layout
        main_layout.addWidget(user_frame)
        main_layout.addSpacing(10)
        main_layout.addWidget(logo_frame)
        main_layout.addSpacing(10)
        main_layout.addLayout(mode_layout)
        main_layout.addLayout(modes_layout)
        main_layout.addSpacing(10)
        main_layout.addLayout(controls_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(log_frame)
        main_layout.addStretch()
        main_layout.addLayout(nav_layout)
        main_layout.addWidget(developer_label)
        
        self.setLayout(main_layout)
    
    def change_mode(self):
        sender = self.sender()
        self.current_mode = sender.text()
        self.mode_label.setText(self.current_mode)
        self.log_message(f"Modo cambiado a: {self.current_mode}")
    
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.ensureCursorVisible()


class ResourceFilesScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BACKGROUND_COLOR}; color: {TEXT_COLOR};")
        
        # Store loaded file paths
        self.tracks_file = ""
        self.playlists_file = ""
        self.artists_file = ""
        self.accounts_file = ""
        self.proxies_file = ""
        
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        
        # User info section - same as in MainScreen
        user_frame = QFrame()
        user_frame.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px;")
        user_layout = QHBoxLayout()
        
        user_icon = QLabel()
        user_icon.setFixedSize(40, 40)
        user_icon.setStyleSheet("background-color: #555555; border-radius: 20px;")
        
        user_info = QVBoxLayout()
        username_label = QLabel("ROCKSTAR")
        username_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        email_label = QLabel("SonOfGod@Holy.com")
        email_label.setFont(QFont("Segoe UI", 10))
        
        user_info.addWidget(username_label)
        user_info.addWidget(email_label)
        
        user_layout.addWidget(user_icon)
        user_layout.addLayout(user_info)
        user_layout.addStretch()
        
        user_frame.setLayout(user_layout)
        
        # Resources title
        resources_title = QLabel("Resources files")
        resources_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        resources_title.setAlignment(Qt.AlignLeft)
        
        # Resource sections
        # Tracks section
        tracks_frame = QFrame()
        tracks_frame.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px;")
        tracks_layout = QHBoxLayout()
        
        tracks_icon = QLabel("📂")
        tracks_icon.setFont(QFont("Segoe UI", 16))
        tracks_icon.setStyleSheet("color: #3D5AFE;")
        
        tracks_info = QVBoxLayout()
        tracks_label = QLabel("Tracks")
        tracks_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.tracks_path_label = QLabel("Track file: No file loaded")
        self.tracks_path_label.setFont(QFont("Segoe UI", 10))
        
        tracks_info.addWidget(tracks_label)
        tracks_info.addWidget(self.tracks_path_label)
        
        self.tracks_play_btn = QPushButton("▶")
        self.tracks_play_btn.setStyleSheet(f"background-color: #3D5AFE; color: {TEXT_COLOR}; border-radius: 15px;")
        self.tracks_play_btn.setFixedSize(30, 30)
        
        tracks_layout.addWidget(tracks_icon)
        tracks_layout.addLayout(tracks_info)
        tracks_layout.addStretch()
        tracks_layout.addWidget(self.tracks_play_btn)
        
        tracks_frame.setLayout(tracks_layout)
        tracks_frame.mousePressEvent = lambda event: self.open_file_dialog("tracks")
        
        # Playlists section
        playlists_frame = QFrame()
        playlists_frame.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px;")
        playlists_layout = QHBoxLayout()
        
        playlists_icon = QLabel("📂")
        playlists_icon.setFont(QFont("Segoe UI", 16))
        playlists_icon.setStyleSheet("color: #3D5AFE;")
        
        playlists_info = QVBoxLayout()
        playlists_label = QLabel("Playlists")
        playlists_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.playlists_path_label = QLabel("Playlist file: No file loaded")
        self.playlists_path_label.setFont(QFont("Segoe UI", 10))
        
        playlists_info.addWidget(playlists_label)
        playlists_info.addWidget(self.playlists_path_label)
        
        self.playlists_play_btn = QPushButton("▶")
        self.playlists_play_btn.setStyleSheet(f"background-color: #3D5AFE; color: {TEXT_COLOR}; border-radius: 15px;")
        self.playlists_play_btn.setFixedSize(30, 30)
        
        playlists_layout.addWidget(playlists_icon)
        playlists_layout.addLayout(playlists_info)
        playlists_layout.addStretch()
        playlists_layout.addWidget(self.playlists_play_btn)
        
        playlists_frame.setLayout(playlists_layout)
        playlists_frame.mousePressEvent = lambda event: self.open_file_dialog("playlists")
        
        # Artists section
        artists_frame = QFrame()
        artists_frame.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px;")
        artists_layout = QHBoxLayout()
        
        artists_icon = QLabel("📂")
        artists_icon.setFont(QFont("Segoe UI", 16))
        artists_icon.setStyleSheet("color: #3D5AFE;")
        
        artists_info = QVBoxLayout()
        artists_label = QLabel("Artists")
        artists_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.artists_path_label = QLabel("Artist file: No file loaded")
        self.artists_path_label.setFont(QFont("Segoe UI", 10))
        
        artists_info.addWidget(artists_label)
        artists_info.addWidget(self.artists_path_label)
        
        self.artists_play_btn = QPushButton("▶")
        self.artists_play_btn.setStyleSheet(f"background-color: #3D5AFE; color: {TEXT_COLOR}; border-radius: 15px;")
        self.artists_play_btn.setFixedSize(30, 30)
        
        artists_layout.addWidget(artists_icon)
        artists_layout.addLayout(artists_info)
        artists_layout.addStretch()
        artists_layout.addWidget(self.artists_play_btn)
        
        artists_frame.setLayout(artists_layout)
        artists_frame.mousePressEvent = lambda event: self.open_file_dialog("artists")
        
        # Accounts section
        accounts_frame = QFrame()
        accounts_frame.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px;")
        accounts_layout = QHBoxLayout()
        
        accounts_icon = QLabel("📂")
        accounts_icon.setFont(QFont("Segoe UI", 16))
        accounts_icon.setStyleSheet("color: #3D5AFE;")
        
        accounts_info = QVBoxLayout()
        accounts_label = QLabel("Accounts")
        accounts_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.accounts_path_label = QLabel("Accounts file: No file loaded")
        self.accounts_path_label.setFont(QFont("Segoe UI", 10))
        
        accounts_info.addWidget(accounts_label)
        accounts_info.addWidget(self.accounts_path_label)
        
        self.accounts_create_btn = QPushButton("+")
        self.accounts_create_btn.setStyleSheet(f"background-color: #3D5AFE; color: {TEXT_COLOR}; border-radius: 15px;")
        self.accounts_create_btn.setFixedSize(30, 30)
        self.accounts_create_btn.setToolTip("Create new accounts")
        
        accounts_layout.addWidget(accounts_icon)
        accounts_layout.addLayout(accounts_info)
        accounts_layout.addStretch()
        accounts_layout.addWidget(self.accounts_create_btn)
        
        accounts_frame.setLayout(accounts_layout)
        accounts_frame.mousePressEvent = lambda event: self.open_file_dialog("accounts")
        
        # Proxies section
        proxies_frame = QFrame()
        proxies_frame.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px;")
        proxies_layout = QHBoxLayout()
        
        proxies_icon = QLabel("📂")
        proxies_icon.setFont(QFont("Segoe UI", 16))
        proxies_icon.setStyleSheet("color: #3D5AFE;")
        
        proxies_info = QVBoxLayout()
        proxies_label = QLabel("Proxies")
        proxies_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.proxies_path_label = QLabel("Proxies file: No file loaded")
        self.proxies_path_label.setFont(QFont("Segoe UI", 10))
        
        proxies_info.addWidget(proxies_label)
        proxies_info.addWidget(self.proxies_path_label)
        
        self.proxies_set_btn = QPushButton("▶")
        self.proxies_set_btn.setStyleSheet(f"background-color: #3D5AFE; color: {TEXT_COLOR}; border-radius: 15px;")
        self.proxies_set_btn.setFixedSize(30, 30)
        self.proxies_set_btn.setToolTip("Set proxies")
        
        proxies_layout.addWidget(proxies_icon)
        proxies_layout.addLayout(proxies_info)
        proxies_layout.addStretch()
        proxies_layout.addWidget(self.proxies_set_btn)
        
        proxies_frame.setLayout(proxies_layout)
        proxies_frame.mousePressEvent = lambda event: self.open_file_dialog("proxies")
        
        # Navigation buttons - same as in MainScreen
        nav_layout = QHBoxLayout()
        
        self.home_button = QPushButton("🏠")
        self.resource_button = QPushButton("➕")
        self.settings_button = QPushButton("⚙")
        
        for btn in [self.home_button, self.resource_button, self.settings_button]:
            btn.setStyleSheet(f"background-color: {SECONDARY_COLOR}; color: #3D5AFE; border-radius: 5px;")
            btn.setFixedSize(80, 50)
            btn.setFont(QFont("Segoe UI", 14))
        
        nav_layout.addWidget(self.home_button)
        nav_layout.addWidget(self.resource_button)
        nav_layout.addWidget(self.settings_button)
        
        # Developer attribution
        developer_label = QLabel("Developed by GALAXIBYTE")
        developer_label.setFont(QFont("Segoe UI", 8))
        developer_label.setAlignment(Qt.AlignCenter)
        
        # Add all sections to main layout
        main_layout.addWidget(user_frame)
        main_layout.addSpacing(10)
        main_layout.addWidget(resources_title)
        main_layout.addSpacing(10)
        main_layout.addWidget(tracks_frame)
        main_layout.addSpacing(10)
        main_layout.addWidget(playlists_frame)
        main_layout.addSpacing(10)
        main_layout.addWidget(artists_frame)
        main_layout.addSpacing(10)
        main_layout.addWidget(accounts_frame)
        main_layout.addSpacing(10)
        main_layout.addWidget(proxies_frame)
        main_layout.addStretch()
        main_layout.addLayout(nav_layout)
        main_layout.addWidget(developer_label)
        
        self.setLayout(main_layout)
    
    def open_file_dialog(self, file_type):
        file_path, _ = QFileDialog.getOpenFileName(self, f"Select {file_type.capitalize()} File", "", "Text Files (*.txt)")

        if file_path:
            # Update local label
            if file_type == "tracks":
                self.tracks_file = file_path
                self.tracks_path_label.setText(f"Track file: {file_path}")
            elif file_type == "playlists":
                self.playlists_file = file_path
                self.playlists_path_label.setText(f"Playlist file: {file_path}")
            elif file_type == "artists":
                self.artists_file = file_path
                self.artists_path_label.setText(f"Artist file: {file_path}")
            elif file_type == "accounts":
                self.accounts_file = file_path
                self.accounts_path_label.setText(f"Accounts file: {file_path}")
            elif file_type == "proxies":
                self.proxies_file = file_path
                self.proxies_path_label.setText(f"Proxies file: {file_path}")

            # Update global config
            config = load_config()
            config[file_type.upper()] = file_path
            save_config(config)
            
            # Copy file to data directory
            try:
                data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
                os.makedirs(data_dir, exist_ok=True)
                
                target_file = os.path.join(data_dir, f"{file_type}.txt")
                with open(file_path, 'r') as src, open(target_file, 'w') as dst:
                    dst.write(src.read())
                
                logger.info(f"Archivo {file_type} copiado a {target_file}")
            except Exception as e:
                logger.error(f"Error al copiar archivo {file_type}: {e}")


class SettingsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BACKGROUND_COLOR}; color: {TEXT_COLOR};")
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        
        # User info section - same as in MainScreen
        user_frame = QFrame()
        user_frame.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px;")
        user_layout = QHBoxLayout()
        
        user_icon = QLabel()
        user_icon.setFixedSize(40, 40)
        user_icon.setStyleSheet("background-color: #555555; border-radius: 20px;")
        
        user_info = QVBoxLayout()
        username_label = QLabel("ROCKSTAR")
        username_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        email_label = QLabel("SonOfGod@Holy.com")
        email_label.setFont(QFont("Segoe UI", 10))
        
        user_info.addWidget(username_label)
        user_info.addWidget(email_label)
        
        user_layout.addWidget(user_icon)
        user_layout.addLayout(user_info)
        user_layout.addStretch()
        
        user_frame.setLayout(user_layout)
        
        # Settings title
        settings_title = QLabel("Settings")
        settings_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        settings_title.setAlignment(Qt.AlignLeft)
        
        # Settings sections
        # InstAddr API Key
        instaddr_frame = QFrame()
        instaddr_frame.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px;")
        instaddr_layout = QVBoxLayout()
        
        instaddr_label = QLabel("InstAddr API Key")
        instaddr_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        
        self.instaddr_key_input = QLineEdit()
        self.instaddr_key_input.setStyleSheet(f"background-color: #1A1A1A; color: {TEXT_COLOR}; border-radius: 5px; padding: 5px;")
        self.instaddr_key_input.setPlaceholderText("Enter your InstAddr API Key")
        
        self.instaddr_save_btn = QPushButton("Save")
        self.instaddr_save_btn.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; border-radius: 5px; padding: 5px;")
        
        instaddr_layout.addWidget(instaddr_label)
        instaddr_layout.addWidget(self.instaddr_key_input)
        instaddr_layout.addWidget(self.instaddr_save_btn)
        
        instaddr_frame.setLayout(instaddr_layout)
        
        # Webshare API Key
        webshare_frame = QFrame()
        webshare_frame.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px;")
        webshare_layout = QVBoxLayout()
        
        webshare_label = QLabel("Webshare API Key")
        webshare_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        
        self.webshare_key_input = QLineEdit()
        self.webshare_key_input.setStyleSheet(f"background-color: #1A1A1A; color: {TEXT_COLOR}; border-radius: 5px; padding: 5px;")
        self.webshare_key_input.setPlaceholderText("Enter your Webshare API Key")
        
        self.webshare_save_btn = QPushButton("Save")
        self.webshare_save_btn.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; border-radius: 5px; padding: 5px;")
        
        webshare_layout.addWidget(webshare_label)
        webshare_layout.addWidget(self.webshare_key_input)
        webshare_layout.addWidget(self.webshare_save_btn)
        
        webshare_frame.setLayout(webshare_layout)
        
        # Device Management
        device_frame = QFrame()
        device_frame.setStyleSheet(f"background-color: {SECONDARY_COLOR}; border-radius: 10px;")
        device_layout = QVBoxLayout()
        
        device_label = QLabel("Device Management")
        device_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        
        self.device_list = QComboBox()
        self.device_list.setStyleSheet(f"background-color: #1A1A1A; color: {TEXT_COLOR}; border-radius: 5px; padding: 5px;")
        
        device_buttons_layout = QHBoxLayout()
        
        self.device_refresh_btn = QPushButton("Refresh")
        self.device_refresh_btn.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; border-radius: 5px; padding: 5px;")
        
        self.device_info_btn = QPushButton("Info")
        self.device_info_btn.setStyleSheet(f"background-color: {BUTTON_COLOR}; color: {TEXT_COLOR}; border-radius: 5px; padding: 5px;")
        
        device_buttons_layout.addWidget(self.device_refresh_btn)
        device_buttons_layout.addWidget(self.device_info_btn)
        
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_list)
        device_layout.addLayout(device_buttons_layout)
        
        device_frame.setLayout(device_layout)
        
        # Navigation buttons - same as in MainScreen
        nav_layout = QHBoxLayout()
        
        self.home_button = QPushButton("🏠")
        self.resource_button = QPushButton("➕")
        self.settings_button = QPushButton("⚙")
        
        for btn in [self.home_button, self.resource_button, self.settings_button]:
            btn.setStyleSheet(f"background-color: {SECONDARY_COLOR}; color: #3D5AFE; border-radius: 5px;")
            btn.setFixedSize(80, 50)
            btn.setFont(QFont("Segoe UI", 14))
        
        nav_layout.addWidget(self.home_button)
        nav_layout.addWidget(self.resource_button)
        nav_layout.addWidget(self.settings_button)
        
        # Developer attribution
        developer_label = QLabel("Developed by GALAXIBYTE")
        developer_label.setFont(QFont("Segoe UI", 8))
        developer_label.setAlignment(Qt.AlignCenter)
        
        # Add all sections to main layout
        main_layout.addWidget(user_frame)
        main_layout.addSpacing(10)
        main_layout.addWidget(settings_title)
        main_layout.addSpacing(10)
        main_layout.addWidget(instaddr_frame)
        main_layout.addSpacing(10)
        main_layout.addWidget(webshare_frame)
        main_layout.addSpacing(10)
        main_layout.addWidget(device_frame)
        main_layout.addStretch()
        main_layout.addLayout(nav_layout)
        main_layout.addWidget(developer_label)
        
        self.setLayout(main_layout)
        
        # Load settings
        self.load_settings()
        
        # Connect signals
        self.instaddr_save_btn.clicked.connect(self.save_instaddr_key)
        self.webshare_save_btn.clicked.connect(self.save_webshare_key)
        self.device_refresh_btn.clicked.connect(self.refresh_devices)
        self.device_info_btn.clicked.connect(self.show_device_info)
    
    def load_settings(self):
        """Carga la configuración desde el archivo config.json"""
        config = load_config()
        
        # InstAddr API Key
        if "INSTADDR_API_KEY" in config:
            self.instaddr_key_input.setText(config["INSTADDR_API_KEY"])
        
        # Webshare API Key
        if "WEBSHARE_API_KEY" in config:
            self.webshare_key_input.setText(config["WEBSHARE_API_KEY"])
        
        # Refresh devices
        self.refresh_devices()
    
    def save_instaddr_key(self):
        """Guarda la API Key de InstAddr"""
        api_key = self.instaddr_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter a valid API Key")
            return
        
        # Guardar en la configuración
        config = load_config()
        config["INSTADDR_API_KEY"] = api_key
        save_config(config)
        
        # Configurar en el módulo
        setup_instaddr_api_key(api_key)
        
        QMessageBox.information(self, "Success", "InstAddr API Key saved successfully")
    
    def save_webshare_key(self):
        """Guarda la API Key de Webshare"""
        api_key = self.webshare_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter a valid API Key")
            return
        
        # Guardar en la configuración
        config = load_config()
        config["WEBSHARE_API_KEY"] = api_key
        save_config(config)
        
        QMessageBox.information(self, "Success", "Webshare API Key saved successfully")
    
    def refresh_devices(self):
        """Actualiza la lista de dispositivos conectados"""
        self.device_list.clear()
        
        devices = AndroidDevice.get_connected_devices()
        if devices:
            for device_id in devices:
                self.device_list.addItem(device_id)
        else:
            self.device_list.addItem("No devices connected")
    
    def show_device_info(self):
        """Muestra información detallada del dispositivo seleccionado"""
        device_id = self.device_list.currentText()
        if not device_id or device_id == "No devices connected":
            QMessageBox.warning(self, "Error", "No device selected")
            return
        
        try:
            device = AndroidDevice(device_id)
            if not device.connected:
                QMessageBox.warning(self, "Error", f"Could not connect to device {device_id}")
                return
            
            info = device.device_info
            apps = device.get_registered_spotify_apps()
            
            info_text = f"Device ID: {device_id}\n"
            info_text += f"Brand: {info.get('brand', 'Unknown')}\n"
            info_text += f"Model: {info.get('model', 'Unknown')}\n"
            info_text += f"Android Version: {info.get('android_version', 'Unknown')}\n"
            info_text += f"SDK Version: {info.get('sdk_version', 'Unknown')}\n\n"
            
            info_text += f"Registered Spotify Apps: {len(apps)}\n"
            for i, app in enumerate(apps):
                info_text += f"{i+1}. {app.get('name', 'Unknown')}: {app.get('package', 'Unknown')}\n"
                if app.get('account'):
                    info_text += f"   Account: {app.get('account')}\n"
            
            QMessageBox.information(self, "Device Info", info_text)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error getting device info: {str(e)}")


class OTWMusicApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OTW Music System")
        self.setMinimumSize(400, 600)
        
        # Initialize stacked widget for multiple screens
        self.stacked_widget = QStackedWidget()
        
        # Create screens
        self.login_screen = LoginScreen()
        self.main_screen = MainScreen()
        self.resource_screen = ResourceFilesScreen()
        self.settings_screen = SettingsScreen()
        
        # Add screens to stacked widget
        self.stacked_widget.addWidget(self.login_screen)
        self.stacked_widget.addWidget(self.main_screen)
        self.stacked_widget.addWidget(self.resource_screen)
        self.stacked_widget.addWidget(self.settings_screen)
        
        # Set central widget
        self.setCentralWidget(self.stacked_widget)
        
        # Connect signals
        self.login_screen.login_button.clicked.connect(self.go_to_main)
        
        self.main_screen.home_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.main_screen))
        self.main_screen.resource_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.resource_screen))
        self.main_screen.settings_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.settings_screen))
        
        self.resource_screen.home_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.main_screen))
        self.resource_screen.resource_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.resource_screen))
        self.resource_screen.settings_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.settings_screen))
        
        self.settings_screen.home_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.main_screen))
        self.settings_screen.resource_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.resource_screen))
        self.settings_screen.settings_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.settings_screen))
        
        # Connect control buttons
        self.main_screen.play_button.clicked.connect(self.start_current_mode)
        self.main_screen.prev_button.clicked.connect(self.previous_action)
        self.main_screen.next_button.clicked.connect(self.next_action)
        
        # Connect resource buttons
        self.resource_screen.tracks_play_btn.clicked.connect(lambda: self.start_mode("PLAY TRACKS"))
        self.resource_screen.playlists_play_btn.clicked.connect(lambda: self.start_mode("PLAY PLAYLISTS"))
        self.resource_screen.artists_play_btn.clicked.connect(lambda: self.start_mode("PLAY ARTIST"))
        self.resource_screen.proxies_set_btn.clicked.connect(self.set_proxies)
        self.resource_screen.accounts_create_btn.clicked.connect(self.create_accounts)
        
        # Initialize worker thread
        self.worker_thread = None
        
        # Start with login screen
        self.stacked_widget.setCurrentWidget(self.login_screen)
    
    def go_to_main(self):
        """Cambia a la pantalla principal"""
        self.stacked_widget.setCurrentWidget(self.main_screen)
    
    def start_current_mode(self):
        """Inicia el modo actual seleccionado"""
        mode = self.main_screen.current_mode
        self.start_mode(mode)
    
    def start_mode(self, mode):
        """Inicia un modo específico"""
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.warning(self, "Warning", "A task is already running")
            return
        
        if mode == "LOG IN":
            self.worker_thread = WorkerThread("login")
            self.worker_thread.update_signal.connect(self.update_log)
            self.worker_thread.finished_signal.connect(self.task_finished)
            self.worker_thread.start()
        
        elif mode == "PLAY TRACKS":
            self.worker_thread = WorkerThread("play_tracks")
            self.worker_thread.update_signal.connect(self.update_log)
            self.worker_thread.finished_signal.connect(self.task_finished)
            self.worker_thread.start()
        
        elif mode == "PLAY ARTIST":
            self.worker_thread = WorkerThread("play_artists")
            self.worker_thread.update_signal.connect(self.update_log)
            self.worker_thread.finished_signal.connect(self.task_finished)
            self.worker_thread.start()
        
        elif mode == "PLAY PLAYLISTS":
            self.worker_thread = WorkerThread("play_playlists")
            self.worker_thread.update_signal.connect(self.update_log)
            self.worker_thread.finished_signal.connect(self.task_finished)
            self.worker_thread.start()
    
    def previous_action(self):
        """Acción para el botón anterior"""
        self.update_log("Previous button pressed")
    
    def next_action(self):
        """Acción para el botón siguiente"""
        self.update_log("Next button pressed")
    
    def set_proxies(self):
        """Configura los proxies en los dispositivos"""
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.warning(self, "Warning", "A task is already running")
            return
        
        self.worker_thread = WorkerThread("set_proxy")
        self.worker_thread.update_signal.connect(self.update_log)
        self.worker_thread.finished_signal.connect(self.task_finished)
        self.worker_thread.start()
    
    def create_accounts(self):
        """Crea nuevas cuentas de Spotify"""
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.warning(self, "Warning", "A task is already running")
            return
        
        # Mostrar diálogo para configurar la creación de cuentas
        count, ok = QInputDialog.getInt(self, "Create Accounts", "Number of accounts to create:", 1, 1, 100, 1)
        if not ok:
            return
        
        headless = QMessageBox.question(self, "Create Accounts", "Run in headless mode?", 
                                       QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes
        
        self.worker_thread = WorkerThread("create_accounts", {"count": count, "headless": headless})
        self.worker_thread.update_signal.connect(self.update_log)
        self.worker_thread.finished_signal.connect(self.task_finished)
        self.worker_thread.start()
    
    def update_log(self, message):
        """Actualiza el log en la pantalla principal"""
        self.main_screen.log_message(message)
    
    def task_finished(self, success, message):
        """Maneja la finalización de una tarea"""
        if success:
            self.update_log(f"✅ {message}")
            QMessageBox.information(self, "Success", message)
        else:
            self.update_log(f"❌ {message}")
            QMessageBox.warning(self, "Error", message)


def main():
    # Crear directorios necesarios
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"), exist_ok=True)
    
    # Iniciar la aplicación
    app = QApplication(sys.argv)
    window = OTWMusicApp()
    window.show()
    sys.exit(app.exec_())

# 👇 ESTA FUNCIÓN DEBE IR **ANTES** del __main__
def playlist_mode():
    return main()

if __name__ == "__main__":
    main()