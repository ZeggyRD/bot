#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 1) Asegúrate de poner PROJECT_ROOT y modules/ en sys.path ANTES de nada más:
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
MODULES_DIR  = os.path.join(PROJECT_ROOT, "modules")
for p in (PROJECT_ROOT, MODULES_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

# 2) Importa UNA sola vez tu human_behavior:
from modules.human_behavior import human_behavior

# 3) Resto de imports normales:
import time
import random
import logging
import subprocess
import traceback
import re
from datetime import datetime
import uiautomator2 as u2
import shutil
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor

SLOW_MODE_FACTOR = 1.0

# … AQUÍ EMPIEZA el resto de tu código sin volver a recalcular rutas ni reimportar human_behavior.
# … y SIN volver a importar human_behavior.

# Logger principal
main_logger = logging.getLogger("PlaylistPlayerMain")
main_logger.setLevel(logging.DEBUG)
main_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Handler de consola
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(main_formatter)
main_logger.addHandler(ch)

def get_spotify_packages(device_id):
    """
    Devuelve todos los paquetes instalados que empiecen por 'com.spotify.musi'
    """
    try:
        out = subprocess.check_output(
            ["adb", "-s", device_id, "shell", "pm", "list", "packages"],
            text=True
        )
        clones = [
            line.split(":",1)[1]
            for line in out.splitlines()
            if line.startswith("package:com.spotify.musi")
        ]
        main_logger.info(f"Clones Spotify detectados en {device_id}: {clones}")
        return clones
    except subprocess.CalledProcessError as e:
        main_logger.error(f"Failed to list packages on {device_id}: {e}")
        return []

# --- Configuración de Paths ---
SCRIPT_DIR       = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT     = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DATA_DIR         = os.path.join(PROJECT_ROOT, "data")
LOG_DIR          = os.path.join(PROJECT_ROOT, "logs")
SCREENSHOTS_DIR  = os.path.join(PROJECT_ROOT, "screenshots")

for d in (DATA_DIR, LOG_DIR, SCREENSHOTS_DIR):
    os.makedirs(d, exist_ok=True)
# -------------------------------

# --- GESTIÓN DE CUENTAS Y PROXIES ---
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.txt")
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        return [tuple(line.strip().split(":", 1)) for line in f if line.strip()]
account_queue = deque(load_accounts())

PROXIES_FILE = os.path.join(DATA_DIR, "proxies.txt")
def load_proxies():
    if not os.path.exists(PROXIES_FILE):
        return []
    with open(PROXIES_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]
proxies = load_proxies()

# package_name -> proxy, and package_name -> bool (logged in or not)
proxy_map   = {}
session_map = {}
# -------------------------------

def _human_delay_wrapper(min_sec, max_sec, personality=None, use_factor=True):
    """Aplica un delay humanizado, ajustado por personalidad si se provea."""
    base_factor = SLOW_MODE_FACTOR if use_factor else 1.0
    personality_factor = personality.get_delay_factor() if personality else 1.0
    total_factor = base_factor * personality_factor

    actual_min = min_sec * total_factor
    actual_max = max_sec * total_factor
    if actual_min > actual_max:
        actual_min = actual_max
    return human_behavior.human_delay(actual_min, actual_max)

# --- Archivos de Persistencia ---
PLAYLIST_FILE         = "playlists.txt"
BACKUP_PLAYLIST_PATH  = os.path.join(DATA_DIR, f"{PLAYLIST_FILE}.bak")
PLAYLIST_PATH         = os.path.join(DATA_DIR, PLAYLIST_FILE)
FOLLOWED_ARTISTS_PATH = os.path.join(DATA_DIR, "followed_artists.txt")
FAILED_LINKS_PATH     = os.path.join(DATA_DIR, "failed_links.txt")
SESSION_SUMMARY_LOG   = os.path.join(LOG_DIR, "session_summary.log")

# --- Constantes para tipos de links ---
LINK_TYPE_PLAYLIST = "playlist"
LINK_TYPE_ARTIST   = "artist"
LINK_TYPE_TRACK    = "track"
LINK_TYPE_UNKNOWN  = "unknown"

# --- Constantes para búsquedas aleatorias ---
RANDOM_SEARCH_TERMS = [
    "lofi", "trap", "Cerame", "GameBoy", "anime", "chill", "beats",
    "relax", "focus", "study", "workout", "party", "dance", "hip hop",
    "rock", "pop", "indie", "jazz", "classical", "ambient"
]

MAX_RETRIES_ACTION    = 3
MAX_RETRIES_OPEN_URL  = 3
stop_event            = threading.Event()

# --- Clase Mejorada para Personalidad del Dispositivo ---
class DevicePersonality:
    def __init__(self, device_id):
        self.device_id = device_id
        random.seed(hash(device_id))  # Semilla inicial para consistencia base

        # —————— Horario activo aleatorio para cada “persona” ——————
        # Dos horas entre 0 y 23 que definen su turno activo
        self.active_hours = sorted(random.sample(range(0, 24), 2))
        # ————————————————————————————————————————————————

        # Niveles base de comportamiento (0.0 a 1.0)
        self._base_patience = random.uniform(0.2, 0.8)
        self._base_curiosity = random.uniform(0.3, 0.9)
        self._base_engagement = random.uniform(0.2, 0.8)
        self._base_speed_factor = random.uniform(0.7, 1.6)
        self._base_track_hopping = random.uniform(0.1, 0.7)
        self._base_artist_focus = random.uniform(0.2, 0.8)
        self._base_search_frequency = random.uniform(0.1, 0.6)

        # Rangos amplios para duraciones
        self._playlist_duration_range_minutes = (
            random.randint(20, 70),
            random.randint(80, 240)
        )
        self._artist_song_listen_range_seconds = (
            random.randint(45, 90),
            random.randint(100, 180)
        )
        self._track_listen_range_seconds = (
            random.randint(40, 85),
            random.randint(95, 170)
        )
        self._artist_explore_actions_range = (
            random.randint(1, 4),
            random.randint(5, 10)
        )
        self._artist_songs_to_listen_range = (
            random.randint(2, 5),
            random.randint(6, 12)
        )
        self._individual_tracks_to_listen_range = (
            random.randint(1, 3),
            random.randint(4, 8)
        )
        self._scrolls_per_page_range = (
            random.randint(0, 2),
            random.randint(3, 7)
        )

        self.update_dynamic_personality()
        random.seed()  # Resetear semilla para aleatoriedad normal

    def is_active_now(self):
        """Devuelve True si la hora actual está dentro del intervalo active_hours."""
        now_h = datetime.now().hour
        start, end = self.active_hours
        if start < end:
            return start <= now_h < end
        else:
            # Si el turno cruza la medianoche
            return now_h >= start or now_h < end

    def update_dynamic_personality(self):
        """Aplica pequeñas variaciones a la personalidad base para cada sesión."""
        variation_factor = lambda base: base * random.uniform(0.85, 1.15)

        self.patience = max(0.1, min(1.0, variation_factor(self._base_patience)))
        self.curiosity = max(0.1, min(1.0, variation_factor(self._base_curiosity)))
        self.engagement = max(0.1, min(1.0, variation_factor(self._base_engagement)))
        self.speed_factor = max(0.5, min(2.0, variation_factor(self._base_speed_factor)))
        self.track_hopping = max(0.05, min(0.9, variation_factor(self._base_track_hopping)))
        self.artist_focus = max(0.1, min(1.0, variation_factor(self._base_artist_focus)))
        self.search_frequency = max(0.05, min(0.8, variation_factor(self._base_search_frequency)))

        # Ajustar probabilidades basadas en niveles dinámicos
        self.like_probability = self.engagement * 0.8
        self.follow_probability = self.engagement * 0.9
        self.scroll_probability = self.curiosity * 0.95
        self.search_probability = self.search_frequency
        self.explore_artist_probability = self.artist_focus
        self.change_playlist_mid_session = self.track_hopping * 0.5

        # Ajustar cantidades basadas en niveles dinámicos
        self.artist_songs_to_listen = random.randint(
            self._artist_songs_to_listen_range[0],
            self._artist_songs_to_listen_range[1]
        )
        self.individual_tracks_to_listen = random.randint(
            self._individual_tracks_to_listen_range[0],
            self._individual_tracks_to_listen_range[1]
        )
        self.artist_explore_actions = random.randint(
            self._artist_explore_actions_range[0],
            self._artist_explore_actions_range[1]
        )
        self.scrolls_per_page = random.randint(
            self._scrolls_per_page_range[0],
            self._scrolls_per_page_range[1]
        )

    def should_like(self): return random.random() < self.like_probability
    def should_follow(self): return random.random() < self.follow_probability
    def should_scroll(self): return random.random() < self.scroll_probability
    def should_search(self): return random.random() < self.search_probability
    def should_explore_artist(self): return random.random() < self.explore_artist_probability
    def should_change_playlist(self): return random.random() < self.change_playlist_mid_session

    def get_playlist_duration(self):
        minutes = random.randint(
            self._playlist_duration_range_minutes[0],
            self._playlist_duration_range_minutes[1]
        )
        adjusted_minutes = minutes * (1 + (self.patience - 0.5) * 0.5)
        return int(max(10 * 60, adjusted_minutes * 60))

    def get_artist_song_duration(self):
        base_duration = random.randint(
            self._artist_song_listen_range_seconds[0],
            self._artist_song_listen_range_seconds[1]
        )
        adjusted_duration = base_duration * (1 - self.track_hopping * 0.4)
        return int(max(30, adjusted_duration))

    def get_track_duration(self):
        base_duration = random.randint(
            self._track_listen_range_seconds[0],
            self._track_listen_range_seconds[1]
        )
        adjusted_duration = base_duration * (1 - self.track_hopping * 0.4)
        return int(max(30, adjusted_duration))

    def get_delay_factor(self): return self.speed_factor
    def get_random_search_term(self): return random.choice(RANDOM_SEARCH_TERMS)

# --- Funciones de Utilidad para Persistencia ---
def load_set_from_file(file_path):
    if not os.path.exists(file_path):
        return set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        main_logger.error(f"Error leyendo links desde '{file_path}': {e}")
        main_logger.debug(traceback.format_exc())
        return set()

def save_set_to_file(file_path, data_set):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            for item in sorted(list(data_set)):
                f.write(f"{item}\n")
    except Exception as e:
        main_logger.error(f"Error guardando set en {file_path}: {e}")

def add_item_to_file(file_path, item):
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"{item}\n")
    except Exception as e:
        main_logger.error(f"Error añadiendo item a {file_path}: {e}")

# --- Funciones de Utilidad General ---
def backup_playlist_file(original_path, backup_path): 
    if os.path.exists(original_path):
        try: shutil.copy2(original_path, backup_path); main_logger.info(f"Backup de '{original_path}' a '{backup_path}' exitoso."); return True
        except Exception as e: main_logger.error(f"Error en backup de '{original_path}' a '{backup_path}': {e}"); return False
    main_logger.warning(f"Archivo original '{original_path}' no encontrado para backup."); return False

def restore_playlist_file_from_backup(original_path, backup_path): 
    if os.path.exists(backup_path):
        try: shutil.copy2(backup_path, original_path); main_logger.info(f"Restaurado '{original_path}' desde '{backup_path}' exitosamente."); return True
        except Exception as e: main_logger.error(f"Error restaurando '{original_path}' desde '{backup_path}': {e}"); return False
    main_logger.info(f"Archivo de backup '{backup_path}' no encontrado."); return False

def load_links_from_file(file_path, failed_links_set):
    """Carga links desde archivo, clasifica y filtra los fallidos."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        main_logger.info(f"Archivo '{file_path}' no existe o está vacío. Intentando restaurar desde backup.")
        restore_playlist_file_from_backup(file_path, BACKUP_PLAYLIST_PATH)
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            main_logger.warning(f"No se pudo restaurar '{file_path}'. Creando archivo vacío.")
            try: 
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                open(file_path, 'w', encoding='utf-8').close()
                main_logger.info(f"Creado archivo vacío '{file_path}'.")
            except Exception as e: main_logger.error(f"Fallo al crear archivo vacío '{file_path}': {e}")
            return [], [], []
    
    playlists, artists, tracks = [], [], []
    loaded_count = 0
    filtered_count = 0
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            links = [line.strip() for line in f if line.strip() and line.strip().startswith("http")]
        
        loaded_count = len(links)
        for link in links:
            if link in failed_links_set:
                filtered_count += 1
                continue # Saltar link fallido conocido
                
            link_type = classify_link(link)
            if link_type == LINK_TYPE_PLAYLIST: playlists.append(link)
            elif link_type == LINK_TYPE_ARTIST: artists.append(link)
            elif link_type == LINK_TYPE_TRACK: tracks.append(link)
        
        main_logger.info(f"Cargados {loaded_count} links desde '{file_path}'. Filtrados {filtered_count} links fallidos.")
        main_logger.info(f"Clasificados: {len(playlists)} playlists, {len(artists)} artistas, {len(tracks)} tracks")
        return playlists, artists, tracks
    except Exception as e: 
        main_logger.error(f"Error leyendo links desde '{file_path}': {e}")
        return [], [], []

def classify_link(url):
    if not url or not isinstance(url, str): return LINK_TYPE_UNKNOWN
    url = url.lower()
    if "/playlist/" in url: return LINK_TYPE_PLAYLIST
    elif "/artist/" in url: return LINK_TYPE_ARTIST
    elif "/track/" in url: return LINK_TYPE_TRACK
    else: return LINK_TYPE_UNKNOWN

def get_artist_id_from_url(url):
    match = re.search(r'/artist/([a-zA-Z0-9]+)', url)
    return match.group(1) if match else None

def get_connected_devices():
    try:
        main_logger.debug("Obteniendo dispositivos conectados vía ADB...")
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=False, timeout=10)
        if result.stderr: main_logger.error(f"Error al ejecutar 'adb devices': {result.stderr.strip()}"); return []
        lines = result.stdout.strip().split("\n")[1:]
        devices = [line.split()[0] for line in lines if line.strip() and "device" in line and "offline" not in line]
        main_logger.info(f"Dispositivos ADB conectados y listos: {devices if devices else 'Ninguno'}")
        return devices
    except subprocess.TimeoutExpired: main_logger.error("Timeout al ejecutar 'adb devices'."); return []
    except Exception as e: main_logger.error(f"Excepción al obtener dispositivos conectados: {e}"); return []

def _get_device_logger(device_id_str): 
    logger = logging.getLogger(f"PlaylistPlayer.{device_id_str}")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        logger.propagate = False # Evitar duplicar logs en el logger principal
        formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
        # Consola
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        # Archivo específico del dispositivo
        safe_device_id = re.sub(r'[^a-zA-Z0-9_-]', '_', device_id_str)
        log_file = os.path.join(LOG_DIR, f"device_{safe_device_id}_{datetime.now().strftime('%Y%m%d')}.log")
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger

def take_screenshot(device_obj, device_id_str, prefix=""):
    d_logger = _get_device_logger(device_id_str)
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
        safe_device_id_str = re.sub(r'[^a-zA-Z0-9_-]', '_', device_id_str)
        device_screenshots_dir = os.path.join(SCREENSHOTS_DIR, safe_device_id_str)
        os.makedirs(device_screenshots_dir, exist_ok=True)
        screenshot_name = f"{prefix}screenshot_{safe_device_id_str}_{timestamp}.png"
        screenshot_path = os.path.join(device_screenshots_dir, screenshot_name)
        d_logger.debug(f"Capturando pantalla en {screenshot_path}")
        device_obj.screenshot(screenshot_path)
        d_logger.info(f"Captura de pantalla guardada: {screenshot_path}")
        return screenshot_path
    except Exception as e: d_logger.error(f"Error al capturar pantalla: {e}"); return None

def get_screen_dimensions(device_obj):
    d_logger = _get_device_logger(getattr(device_obj, 'serial', 'UnknownDevice'))
    try:
        info = device_obj.info
        width, height = info["displayWidth"], info["displayHeight"]
        d_logger.debug(f"Dimensiones (u2): {width}x{height}")
        return width, height
    except Exception as e_u2:
        d_logger.warning(f"Error u2 para dimensiones: {e_u2}. Usando defecto 1080x1920.")
        return 1080, 1920 # Fallback a dimensiones comunes

# --- Funciones de Interacción con UI Mejoradas ---
def handle_open_with_dialog(device, device_id):
    """Maneja el diálogo 'Abrir con' intentando seleccionar Spotify y 'Siempre'."""
    d_logger = _get_device_logger(device_id)
    d_logger.debug("Verificando diálogo 'Abrir con'...")
    
    # Intentar detectar el diálogo por título o por la presencia de Spotify como opción
    dialog_selectors = [
        {"resourceId": "android:id/alertTitle"}, 
        {"text": "Spotify", "resourceId": "android:id/text1"}, # Opción específica
        {"description": "Spotify", "resourceId": "android:id/text1"}
    ]
    
    dialog_found = False
    for sel in dialog_selectors:
        if device(**sel).exists(timeout=2):
            dialog_found = True
            break
            
    if not dialog_found:
        d_logger.debug("No se detectó diálogo 'Abrir con'.")
        return False # No se encontró el diálogo

    d_logger.info("Diálogo 'Abrir con' detectado.")
    take_screenshot(device, device_id, "open_with_dialog_")
    
    # 1. Intentar clickear en Spotify
    spotify_clicked = False
    spotify_selectors = [
        {"text": "Spotify", "resourceId": "android:id/text1"},
        {"description": "Spotify", "resourceId": "android:id/text1"},
        {"textMatches": "(?i)Spotify"}
    ]
    for sel in spotify_selectors:
        spotify_option = device(**sel)
        if spotify_option.exists(timeout=0.5):
            try:
                d_logger.info(f"Intentando clickear Spotify con selector: {sel}")
                _human_delay_wrapper(0.7, 1.5, use_factor=True)
                spotify_option.click()
                d_logger.info("Spotify clickeado en el diálogo.")
                spotify_clicked = True
                _human_delay_wrapper(1.0, 2.0, use_factor=True)
                break
            except Exception as e:
                d_logger.warning(f"Error al clickear Spotify en diálogo: {e}")
                take_screenshot(device, device_id, "open_with_spotify_click_err_")
    
    if not spotify_clicked:
        d_logger.warning("No se pudo clickear Spotify en el diálogo.")
        # Podríamos intentar presionar back o simplemente devolver False
        return False

    # 2. Intentar clickear "Siempre" (preferido) o "Solo una vez"
    confirm_clicked = False
    confirm_selectors = [
        {"textMatches": "(?i)Always|Siempre", "className": "android.widget.Button"}, # Preferido
        {"textMatches": "(?i)Always|Siempre"},
        {"textMatches": "(?i)Just once|Solo una vez", "className": "android.widget.Button"},
        {"textMatches": "(?i)Just once|Solo una vez"}
    ]
    for sel in confirm_selectors:
        confirm_button = device(**sel)
        if confirm_button.exists(timeout=1.5):
            try:
                d_logger.info(f"Intentando clickear confirmación: {sel}")
                _human_delay_wrapper(0.6, 1.4, use_factor=True)
                confirm_button.click()
                d_logger.info("Botón de confirmación ('Siempre'/'Solo una vez') clickeado.")
                confirm_clicked = True
                _human_delay_wrapper(1.5, 3.0, use_factor=True) # Esperar a que la app cargue
                return True # Éxito al manejar el diálogo
            except Exception as e:
                d_logger.warning(f"Error al clickear botón de confirmación: {e}")
                take_screenshot(device, device_id, "open_with_confirm_click_err_")

    if spotify_clicked and not confirm_clicked:
        d_logger.info("Spotify clickeado, pero no se encontró/clickeó botón de confirmación. Asumiendo que funcionó.")
        # A veces, después de clickear la app, el diálogo desaparece solo
        return True 

    d_logger.warning("No se pudo completar el manejo del diálogo 'Abrir con'.")
    return False

def handle_spotify_popup_later(device, device_id):
    """Maneja popups comunes de Spotify como 'Later' o 'Not Now'."""
    d_logger = _get_device_logger(device_id)
    d_logger.debug("Verificando popups de Spotify ('Later', 'Not Now', etc.)...")
    
    popup_selectors = [
        {"textMatches": "(?i)Later|Más tarde", "clickable": True},
        {"textMatches": "(?i)Not now|Ahora no", "clickable": True},
        {"resourceIdMatches": ".*later.*|.*notnow.*", "clickable": True}
        # Añadir más selectores si se descubren otros popups comunes
    ]

    for sel in popup_selectors:
        popup_button = device(**sel)
        if popup_button.exists(timeout=2):
            d_logger.info(f"Popup de Spotify detectado con selector: {sel}")
            take_screenshot(device, device_id, "spotify_popup_detected_")
            try:
                _human_delay_wrapper(0.5, 1.2, use_factor=True)
                popup_button.click()
                _human_delay_wrapper(1.0, 2.5, use_factor=True)
                d_logger.info("Popup de Spotify manejado correctamente.")
                return True # Se manejó un popup
            except Exception as e:
                d_logger.warning(f"Error al clickear botón del popup de Spotify: {e}")
                take_screenshot(device, device_id, "spotify_popup_click_error_")
                return False # Hubo un error al intentar manejarlo

    d_logger.debug("No se detectaron popups conocidos de Spotify.")
    return False # No se encontraron popups

def is_spotify_foreground(device_id):
    """Verifica si Spotify está en primer plano usando ADB."""
    d_logger = _get_device_logger(device_id)
    d_logger.debug("Verificando si Spotify está en primer plano (ADB)...")
    try:
        # Usar una regex más amplia para paquetes de Spotify (incluyendo clones, lite, etc.)
        spotify_package_regex = r"com\.spotify\.music(?:\.\w+)?"
        
        # Comandos ADB para verificar la actividad en primer plano
        commands = [
            ["adb", "-s", device_id, "shell", "dumpsys", "activity", "activities"],
            ["adb", "-s", device_id, "shell", "dumpsys", "window", "windows"]
        ]
        
        output = ""
        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=7)
            if result.returncode == 0:
                output += result.stdout
            else:
                d_logger.warning(f"Comando ADB falló: {' '.join(cmd)} - {result.stderr.strip()}")

        if not output:
            d_logger.warning("No se pudo obtener salida de dumpsys.")
            return False

        # Patrones para buscar la actividad de Spotify en primer plano
        patterns = [
            re.compile(r"mResumedActivity:\s+ActivityRecord\{[^}]*?\s+(" + spotify_package_regex + r"/[\.\w]+)", re.IGNORECASE),
            re.compile(r"mFocusedActivity:\s+ActivityRecord\{[^}]*?\s+(" + spotify_package_regex + r"/[\.\w]+)", re.IGNORECASE),
            re.compile(r"mCurrentFocus=Window\{[^}]*?\s+(" + spotify_package_regex + r"/[\.\w]+)", re.IGNORECASE),
            re.compile(r"topResumedActivity=\s*ActivityRecord\{[^}]*?\s+(" + spotify_package_regex + r"/[\.\w]+)", re.IGNORECASE)
        ]

        for pattern in patterns:
            match = pattern.search(output)
            if match:
                activity = match.group(1)
                d_logger.info(f"Spotify detectado en primer plano: {activity}")
                return True
        
        d_logger.debug("Spotify no parece estar en primer plano según dumpsys.")
        return False
    except subprocess.TimeoutExpired:
        d_logger.error("Timeout al ejecutar comando ADB para verificar foreground.")
        return False
    except Exception as e:
        d_logger.error(f"Error al verificar si Spotify está en primer plano: {e}")
        return False

def open_spotify_url(device, device_id, package, url, personality, failed_links_set):
    """Abre URL de Spotify, maneja diálogos y reintentos, marca links fallidos."""
    d_logger = _get_device_logger(device_id)
    d_logger.info(f"Abriendo URL: {url}")
    
    if url in failed_links_set:
        d_logger.warning(f"Saltando URL marcada como fallida: {url}")
        return False

    # Intentar abrir directamente con el paquete de Spotify para evitar diálogo "Abrir con"
    spotify_package = package # Asumir paquete principal, podría necesitar ajuste para clones
    direct_intent_command = f"am start -n {spotify_package}/com.spotify.music.MainActivity -a android.intent.action.VIEW -d '{url}'"
    fallback_intent_command = f"am start -a android.intent.action.VIEW -d '{url}'"

    for attempt in range(MAX_RETRIES_OPEN_URL):
        d_logger.info(f"Intento {attempt + 1}/{MAX_RETRIES_OPEN_URL} para abrir URL: {url}")
        try:
            # Intentar primero con intent directo
            if attempt == 0:
                d_logger.debug(f"Ejecutando intent directo: {direct_intent_command}")
                device.shell(direct_intent_command)
            else: # Si falla, usar intent genérico
                d_logger.debug(f"Ejecutando intent genérico: {fallback_intent_command}")
                device.shell(fallback_intent_command)
            
            _human_delay_wrapper(2.0, 4.5, personality=personality)
            
            # Manejar diálogo "Abrir con" (puede aparecer incluso con intent directo si no está por defecto)
            handle_open_with_dialog(device, device_id)
            _human_delay_wrapper(0.5, 1.5, personality=personality)
            
            # Manejar popups de Spotify
            handle_spotify_popup_later(device, device_id)
            _human_delay_wrapper(1.0, 2.5, personality=personality)
            
            # Verificar si Spotify está en primer plano
            if is_spotify_foreground(device_id):
                d_logger.info(f"URL abierta correctamente y Spotify en primer plano: {url}")
                take_screenshot(device, device_id, "url_opened_")
                return True # Éxito
            else:
                d_logger.warning(f"Spotify no detectado en primer plano después del intento {attempt + 1}.")
                take_screenshot(device, device_id, f"url_open_not_foreground_attempt{attempt+1}_")
        
        except Exception as e:
            d_logger.error(f"Excepción al abrir URL {url} (Intento {attempt + 1}): {e}")
            take_screenshot(device, device_id, f"url_open_exception_attempt{attempt+1}_")
            # Si hay excepción, forzar un delay mayor antes de reintentar
            _human_delay_wrapper(5.0, 10.0, personality=personality)
        
        # Esperar antes del siguiente reintento
        if attempt < MAX_RETRIES_OPEN_URL - 1:
             _human_delay_wrapper(3.0, 6.0, personality=personality)

    # Si todos los intentos fallan
    d_logger.error(f"No se pudo abrir URL o verificar Spotify en primer plano después de {MAX_RETRIES_OPEN_URL} intentos: {url}")
    # Marcar el link como fallido
    failed_links_set.add(url)
    add_item_to_file(FAILED_LINKS_PATH, url)
    d_logger.info(f"URL marcada como fallida y añadida a {FAILED_LINKS_PATH}: {url}")
    return False

def perform_random_scroll(device, device_id, personality):
    """Realiza scrolls más naturales: longitud y velocidad variables, pausas."""
    d_logger = _get_device_logger(device_id)
    
    if not personality.should_scroll():
        d_logger.debug("Personalidad decidió no hacer scroll esta vez")
        return
    
    try:
        width, height = get_screen_dimensions(device)
        
        # Decidir dirección y magnitud del scroll
        scroll_down = random.random() < 0.7 # Más probable scroll hacia abajo
        scroll_magnitude = random.uniform(0.3, 0.8) # Qué tan largo es el scroll (porcentaje de pantalla)
        scroll_duration = random.uniform(0.2, 1.0) * personality.get_delay_factor() # Velocidad del scroll
        
        # Calcular puntos de inicio y fin
        start_x = width * random.uniform(0.4, 0.6)
        end_x = start_x + random.uniform(-width*0.05, width*0.05) # Pequeña variación horizontal
        
        if scroll_down:
            start_y = height * random.uniform(0.6, 0.9) # Empezar más abajo
            end_y = start_y - height * scroll_magnitude
            d_logger.debug(f"Scroll hacia abajo (magnitud: {scroll_magnitude:.2f}, duración: {scroll_duration:.2f}s)")
        else:
            start_y = height * random.uniform(0.1, 0.4) # Empezar más arriba
            end_y = start_y + height * scroll_magnitude
            d_logger.debug(f"Scroll hacia arriba (magnitud: {scroll_magnitude:.2f}, duración: {scroll_duration:.2f}s)")
            
        # Asegurar que los puntos estén dentro de la pantalla
        start_y = max(1, min(height - 1, start_y))
        end_y = max(1, min(height - 1, end_y))
        start_x = max(1, min(width - 1, start_x))
        end_x = max(1, min(width - 1, end_x))

        # Realizar el scroll
        device.swipe(start_x, start_y, end_x, end_y, duration=scroll_duration)
        
        # Pausa después del scroll
        _human_delay_wrapper(0.5, 2.5, personality=personality)
        
        d_logger.debug("Scroll completado")
    except Exception as e:
        d_logger.warning(f"Error al realizar scroll: {e}")

def click_like_button(device, device_id, personality):
    d_logger = _get_device_logger(device_id)
    if not personality.should_like():
        d_logger.debug("Personalidad decidió no dar like")
        return False
    d_logger.info("Intentando dar like...")
    try:
        like_selectors = [
            {"resourceIdMatches": ".*like.*|.*heart.*", "clickable": True},
            {"descriptionMatches": "(?i).*like.*|.*heart.*|.*favorit.*|.*add.*|.*guardar.*", "clickable": True}
        ]
        for selector in like_selectors:
            like_button = device(**selector)
            if like_button.exists(timeout=1):
                # Podríamos añadir una verificación para no clickear si ya está 'liked' (icono lleno vs vacío)
                # Pero por simplicidad, clickeamos si lo encontramos
                d_logger.info(f"Botón de like encontrado con selector: {selector}")
                _human_delay_wrapper(0.5, 1.5, personality=personality)
                like_button.click()
                d_logger.info("Like/Unlike presionado correctamente")
                _human_delay_wrapper(1.0, 2.0, personality=personality)
                return True
        d_logger.debug("No se encontró botón de like")
        return False
    except Exception as e:
        d_logger.warning(f"Error al intentar dar like: {e}")
        return False

def click_follow_button(device, device_id, artist_url, personality, followed_artists_set):
    d_logger = _get_device_logger(device_id)
    artist_id = get_artist_id_from_url(artist_url)
    
    if artist_id and artist_id in followed_artists_set:
        d_logger.info(f"Artista {artist_id} ya está en la lista de seguidos. No se intentará seguir.")
        return False # Ya seguido

    if not personality.should_follow():
        d_logger.debug("Personalidad decidió no seguir al artista esta vez")
        return False
    
    d_logger.info(f"Intentando seguir al artista: {artist_url}")
    try:
        follow_selectors = [
            {"textMatches": "(?i)Follow|Seguir", "clickable": True},
            {"resourceIdMatches": ".*follow.*", "clickable": True},
            {"descriptionMatches": "(?i).*follow.*|.*seguir.*", "clickable": True}
        ]
        for selector in follow_selectors:
            follow_button = device(**selector)
            if follow_button.exists(timeout=1):
                d_logger.info(f"Botón de follow encontrado con selector: {selector}")
                _human_delay_wrapper(0.5, 1.5, personality=personality)
                follow_button.click()
                d_logger.info("Botón Follow/Unfollow presionado correctamente")
                _human_delay_wrapper(1.0, 2.0, personality=personality)
                # Añadir a la lista de seguidos si se presionó y el ID es válido
                if artist_id:
                    followed_artists_set.add(artist_id)
                    add_item_to_file(FOLLOWED_ARTISTS_PATH, artist_id)
                    d_logger.info(f"Artista {artist_id} añadido a la lista de seguidos.")
                return True # Se presionó el botón
        d_logger.debug("No se encontró botón de follow (o el artista ya está seguido en la UI)")
        return False
    except Exception as e:
        d_logger.warning(f"Error al intentar seguir al artista: {e}")
        return False

def click_shuffle_button(device, device_id, personality):
    d_logger = _get_device_logger(device_id)
    # Decidir si activar shuffle basado en personalidad (curiosidad/track hopping)
    if random.random() > (personality.curiosity + personality.track_hopping) / 2:
         d_logger.debug("Personalidad decidió no tocar el botón de shuffle")
         return False
         
    d_logger.info("Intentando activar/desactivar shuffle...")
    try:
        shuffle_selectors = [
            {"resourceIdMatches": ".*shuffle.*", "clickable": True},
            {"descriptionMatches": "(?i).*shuffle.*|.*aleatorio.*", "clickable": True}
        ]
        for selector in shuffle_selectors:
            shuffle_button = device(**selector)
            if shuffle_button.exists(timeout=1):
                d_logger.info(f"Botón de shuffle encontrado con selector: {selector}")
                _human_delay_wrapper(0.5, 1.5, personality=personality)
                shuffle_button.click()
                d_logger.info("Shuffle presionado correctamente")
                _human_delay_wrapper(1.0, 2.0, personality=personality)
                return True
        d_logger.debug("No se encontró botón de shuffle")
        return False
    except Exception as e:
        d_logger.warning(f"Error al intentar activar shuffle: {e}")
        return False

def click_play_button(device, device_id, personality):
    d_logger = _get_device_logger(device_id)
    d_logger.info("Intentando presionar play/pause...")
    try:
        # Buscar botón de play/pause (suelen tener descripciones o IDs similares)
        play_pause_selectors = [
            {"resourceIdMatches": ".*play.*|.*pause.*", "clickable": True},
            {"descriptionMatches": "(?i).*play.*|.*pause.*|.*reproducir.*|.*pausar.*", "clickable": True}
        ]
        for selector in play_pause_selectors:
            play_button = device(**selector)
            if play_button.exists(timeout=1):
                d_logger.info(f"Botón de play/pause encontrado con selector: {selector}")
                _human_delay_wrapper(0.5, 1.5, personality=personality)
                play_button.click()
                d_logger.info("Play/Pause presionado correctamente")
                _human_delay_wrapper(1.0, 2.0, personality=personality)
                return True
        d_logger.debug("No se encontró botón de play/pause principal")
        return False
    except Exception as e:
        d_logger.warning(f"Error al intentar presionar play/pause: {e}")
        return False

def is_player_active_visually(device, device_id):
    """Intenta detectar si el reproductor está activo buscando elementos UI."""
    d_logger = _get_device_logger(device_id)
    d_logger.debug("Verificando visualmente si el reproductor está activo...")
    try:
        # Buscar elementos comunes en un reproductor activo:
        # 1. Botón de Pausa (indica que está reproduciendo)
        pause_selectors = [
            {"resourceIdMatches": ".*pause.*", "clickable": True},
            {"descriptionMatches": "(?i).*pause.*|.*pausar.*", "clickable": True}
        ]
        for selector in pause_selectors:
            if device(**selector).exists(timeout=0.5):
                d_logger.info("Reproductor parece activo (botón de pausa visible)")
                return True
        
        # 2. Barra de progreso o contador de tiempo (más difícil de generalizar)
        # progress_selectors = [{"resourceIdMatches": ".*progress.*|.*time.*"}]
        # for selector in progress_selectors:
        #     if device(**selector).exists(timeout=0.5):
        #         # Verificar si el texto del tiempo cambia podría ser más robusto
        #         d_logger.info("Reproductor parece activo (barra de progreso/tiempo visible)")
        #         return True

        d_logger.debug("No se encontraron indicadores visuales claros de reproducción activa.")
        return False
    except Exception as e:
        d_logger.warning(f"Error en la verificación visual del reproductor: {e}")
        return False # Asumir que no está activo si hay error

def perform_search(device, device_id, personality):
    d_logger = _get_device_logger(device_id)
    if not personality.should_search():
        d_logger.debug("Personalidad decidió no realizar búsqueda")
        return False
    
    d_logger.info("Iniciando fase de búsqueda...")
    search_summary = {"term": "", "success": False, "error": None}
    try:
        # 1. Ir a la pestaña/botón de búsqueda
        search_tab_selectors = [
            {"textMatches": "(?i)Search|Buscar", "classNameMatches": "android.widget.*Button.*"},
            {"resourceIdMatches": ".*search.*|.*tab.*", "clickable": True},
            {"descriptionMatches": "(?i).*search.*|.*buscar.*", "clickable": True}
        ]
        search_tab_clicked = False
        for selector in search_tab_selectors:
            search_button = device(**selector)
            if search_button.exists(timeout=2):
                d_logger.info(f"Botón/Tab de búsqueda encontrado: {selector}")
                _human_delay_wrapper(0.6, 1.6, personality=personality)
                search_button.click()
                d_logger.info("Click en botón/tab de búsqueda.")
                _human_delay_wrapper(1.5, 3.0, personality=personality)
                search_tab_clicked = True
                break
        if not search_tab_clicked:
            d_logger.warning("No se encontró el botón/tab de búsqueda.")
            raise Exception("Search tab not found")

        # 2. Encontrar y clickear el campo de texto de búsqueda
        search_field_selectors = [
            {"resourceIdMatches": ".*search.*|.*query.*", "className": "android.widget.EditText"},
            {"textMatches": "(?i).*search.*|.*buscar.*", "className": "android.widget.EditText"},
            # A veces es un TextView clickeable que abre el EditText
            {"resourceIdMatches": ".*search.*|.*query.*", "className": "android.widget.TextView", "clickable": True}
        ]
        search_field_focused = False
        for selector in search_field_selectors:
            search_field = device(**selector)
            if search_field.exists(timeout=2):
                d_logger.info(f"Campo de búsqueda encontrado: {selector}")
                _human_delay_wrapper(0.5, 1.5, personality=personality)
                search_field.click() # Asegurar foco
                _human_delay_wrapper(0.8, 1.8, personality=personality)
                # Verificar si el teclado apareció o si el campo es editable
                if device(focused=True).exists(timeout=1): # Verificar si hay un campo enfocado
                    search_field_focused = True
                    break
                else:
                    d_logger.warning("Campo de búsqueda clickeado pero no parece enfocado.")
        
        if not search_field_focused:
             # Intentar de nuevo con el selector de EditText si el TextView falló
             edit_text_selector = {"className": "android.widget.EditText", "focused": True}
             if device(**edit_text_selector).exists(timeout=1):
                 search_field_focused = True
             else:
                d_logger.warning("No se pudo enfocar el campo de búsqueda.")
                raise Exception("Search field not focused")

        # 3. Escribir término y buscar
        search_term = personality.get_random_search_term()
        search_summary["term"] = search_term
        d_logger.info(f"Buscando: '{search_term}'")
        # Usar set_text en el campo enfocado
        focused_field = device(focused=True)
        focused_field.set_text(search_term)
        _human_delay_wrapper(0.7, 1.7, personality=personality)
        device.press("enter")
        _human_delay_wrapper(2.5, 5.0, personality=personality) # Esperar resultados

        # 4. Interactuar con resultados (scrolls)
        num_scrolls = random.randint(1, personality.scrolls_per_page + 1)
        d_logger.info(f"Realizando {num_scrolls} scrolls en resultados de búsqueda.")
        for _ in range(num_scrolls):
            perform_random_scroll(device, device_id, personality)
            _human_delay_wrapper(1.0, 3.0, personality=personality)
        
        # 5. Volver atrás
        d_logger.info("Volviendo atrás desde la búsqueda...")
        device.press("back")
        _human_delay_wrapper(1.0, 2.5, personality=personality)
        # A veces hay que presionar back dos veces (salir de resultados, salir de teclado/página de búsqueda)
        if device(focused=True).exists(timeout=0.5): # Si el campo sigue enfocado
             device.press("back")
             _human_delay_wrapper(1.0, 2.0, personality=personality)
             
        d_logger.info("Fase de búsqueda completada")
        search_summary["success"] = True
        return True, search_summary
    except Exception as e:
        d_logger.error(f"Error en fase de búsqueda: {e}")
        search_summary["error"] = str(e)
        take_screenshot(device, device_id, "search_error_")
        # Intentar volver atrás para recuperarse
        try: device.press("back"); _human_delay_wrapper(1,2)
        except: pass
        try: device.press("back"); _human_delay_wrapper(1,2)
        except: pass
        return False, search_summary

# --- Funciones Principales de Fases (Refactorizadas) ---
def play_playlist(device, device_id, package, playlist_url, personality, failed_links_set):
    d_logger = _get_device_logger(device_id)
    d_logger.info(f"=== INICIANDO FASE PLAYLIST: {playlist_url} ===")
    phase_summary = {"url": playlist_url, "duration_planned": 0, "duration_actual": 0, "liked": False, "shuffled": False, "played": False, "visually_active": False, "actions": [], "success": False, "error": None}
    start_time = time.time()

    if not open_spotify_url(device, device_id, package, playlist_url, personality, failed_links_set):
        d_logger.error("No se pudo abrir la playlist.")
        phase_summary["error"] = "Failed to open URL"
        return False, phase_summary
    
    try:
        # Acciones iniciales
        if click_like_button(device, device_id, personality): phase_summary["liked"] = True; phase_summary["actions"].append("like")
        if click_shuffle_button(device, device_id, personality): phase_summary["shuffled"] = True; phase_summary["actions"].append("shuffle")
        if click_play_button(device, device_id, personality): phase_summary["played"] = True; phase_summary["actions"].append("play")
        else:
             # Si no se encontró play, intentar clickear el primer elemento clickeable que parezca una canción
             d_logger.info("Botón Play principal no encontrado, intentando clickear primera canción...")
             first_song = device(resourceIdMatches=".*track.*|.*row.*", clickable=True, index=0) # Selector heurístico
             if first_song.exists(timeout=1):
                 try: 
                     first_song.click(); phase_summary["played"] = True; phase_summary["actions"].append("play_first_song")
                     d_logger.info("Clickeada primera canción.")
                     _human_delay_wrapper(1.5, 3.0, personality=personality)
                 except Exception as e_click:
                     d_logger.warning(f"Error al clickear primera canción: {e_click}")
             else:
                 d_logger.warning("No se pudo iniciar la reproducción.")
                 raise Exception("Playback could not be started")

        # Verificar si está activo visualmente
        phase_summary["visually_active"] = is_player_active_visually(device, device_id)

        # Duración de reproducción
        playlist_duration = personality.get_playlist_duration()
        phase_summary["duration_planned"] = playlist_duration
        d_logger.info(f"Reproduciendo playlist durante ~{playlist_duration / 60:.1f} minutos.")
        
        listen_start_time = time.time()
        listen_end_time = listen_start_time + playlist_duration
        
        while time.time() < listen_end_time and not stop_event.is_set():
            remaining_time = listen_end_time - time.time()
            if remaining_time <= 0: break
            
            # Acciones aleatorias durante la escucha
            action_roll = random.random()
            wait_interval = min(remaining_time, random.uniform(20.0, 70.0) * personality.patience)
            
            if action_roll < 0.4 and personality.should_scroll(): # 40% chance de scroll
                d_logger.debug("Realizando scroll aleatorio durante reproducción")
                perform_random_scroll(device, device_id, personality)
                phase_summary["actions"].append("scroll")
                wait_interval = min(remaining_time, random.uniform(5.0, 15.0)) # Espera corta después de scroll
            elif action_roll < 0.5: # 10% chance de screenshot (40% a 50%)
                d_logger.debug("Tomando captura durante reproducción")
                take_screenshot(device, device_id, "playlist_playing_")
                phase_summary["actions"].append("screenshot")
            # else: 50% chance de solo esperar
            
            d_logger.debug(f"Esperando {wait_interval:.1f}s durante reproducción (restante: {remaining_time:.1f}s)")
            time.sleep(wait_interval)
        
        phase_summary["success"] = True
        d_logger.info("Fase de reproducción de playlist completada")
        
    except Exception as e:
        d_logger.error(f"Error en fase de reproducción de playlist: {e}")
        phase_summary["error"] = str(e)
        take_screenshot(device, device_id, "playlist_error_")
        phase_summary["success"] = False
    finally:
        phase_summary["duration_actual"] = time.time() - start_time
        d_logger.info(f"Duración real fase playlist: {phase_summary['duration_actual'] / 60:.1f} min")
        
    return phase_summary["success"], phase_summary

def visit_artist(device, device_id, package, artist_url, personality, followed_artists_set, failed_links_set):
    d_logger = _get_device_logger(device_id)
    d_logger.info(f"=== INICIANDO FASE ARTISTA: {artist_url} ===")
    phase_summary = {"url": artist_url, "followed": False, "songs_listened_count": 0, "explore_actions": [], "success": False, "error": None, "duration": 0}
    start_time = time.time()
    artist_id = get_artist_id_from_url(artist_url)

    if not open_spotify_url(device, device_id, artist_url, personality, failed_links_set):
        d_logger.error("No se pudo abrir el perfil del artista.")
        phase_summary["error"] = "Failed to open URL"
        return False, phase_summary

    try:
        # 1. Intentar seguir (si no está seguido ya)
        if click_follow_button(device, device_id, artist_url, personality, followed_artists_set):
             phase_summary["followed"] = True
             phase_summary["explore_actions"].append("follow")

        # 2. Exploración y escucha
        songs_to_listen = personality.artist_songs_to_listen
        actions_to_perform = personality.artist_explore_actions
        d_logger.info(f"Explorando perfil: {actions_to_perform} acciones, escuchando hasta {songs_to_listen} canciones.")

        songs_listened_count = 0
        actions_performed_count = 0

        # Realizar acciones de exploración y escucha alternadas
        while actions_performed_count < actions_to_perform and songs_listened_count < songs_to_listen and not stop_event.is_set():
            action_type = random.choice(["scroll", "explore_section", "listen_song"])
            
            if action_type == "scroll" and personality.should_scroll():
                d_logger.debug("Acción: Scroll en perfil de artista")
                perform_random_scroll(device, device_id, personality)
                phase_summary["explore_actions"].append("scroll")
                actions_performed_count += 1
            
            elif action_type == "explore_section" and personality.should_explore_artist():
                d_logger.debug("Acción: Explorar sección del artista")
                # Intentar clickear elementos como "See all", "Discography", nombres de álbumes
                explore_selectors = [
                    {"textMatches": "(?i)See all|Ver todo|Discography|Discografía", "clickable": True},
                    {"resourceIdMatches": ".*album.*|.*playlist.*|.*section.*", "clickable": True}
                ]
                clicked_explore = False
                for selector in explore_selectors:
                    explore_element = device(**selector)
                    if explore_element.exists(timeout=0.5):
                        try:
                            text = explore_element.info.get('text', 'N/A')
                            d_logger.info(f"Clickeando elemento de exploración: '{text}'")
                            _human_delay_wrapper(0.5, 1.5, personality=personality)
                            explore_element.click()
                            _human_delay_wrapper(1.5, 3.5, personality=personality)
                            # Realizar un scroll dentro de la sección explorada
                            perform_random_scroll(device, device_id, personality)
                            # Volver atrás para continuar explorando el perfil principal
                            device.press("back")
                            _human_delay_wrapper(1.0, 2.5, personality=personality)
                            phase_summary["explore_actions"].append(f"explore_{text[:15]}")
                            clicked_explore = True
                            break
                        except Exception as e_explore:
                            d_logger.warning(f"Error al explorar sección: {e_explore}")
                if clicked_explore:
                    actions_performed_count += 1
            
            elif action_type == "listen_song":
                d_logger.debug("Acción: Intentar escuchar una canción del artista")
                # Buscar elementos que parezcan canciones clickeables
                song_selectors = [
                    {"resourceIdMatches": ".*track.*|.*song.*|.*row.*", "clickable": True}
                ]
                found_song = False
                for selector in song_selectors:
                    # Buscar un elemento aleatorio que coincida
                    song_elements = device(**selector).find_all()
                    if song_elements:
                        song_element = random.choice(song_elements)
                        try:
                            text = song_element.info.get('text', 'N/A')
                            d_logger.info(f"Clickeando posible canción: '{text[:30]}...'" )
                            _human_delay_wrapper(0.5, 1.5, personality=personality)
                            song_element.click()
                            _human_delay_wrapper(1.5, 3.0, personality=personality)
                            
                            # Verificar si el reproductor se activó
                            if is_player_active_visually(device, device_id):
                                song_duration = personality.get_artist_song_duration()
                                d_logger.info(f"Escuchando canción durante ~{song_duration} segundos")
                                time.sleep(song_duration)
                                songs_listened_count += 1
                                phase_summary["explore_actions"].append(f"listen_{text[:15]}")
                                d_logger.info(f"Canción {songs_listened_count}/{songs_to_listen} completada")
                                # Volver atrás si se abrió una vista de reproducción diferente
                                # (Esto es heurístico, podría necesitar ajuste)
                                if not device(**selector).exists(timeout=0.5): # Si el selector original ya no existe
                                    d_logger.debug("Volviendo atrás después de escuchar canción...")
                                    device.press("back")
                                    _human_delay_wrapper(1.0, 2.5, personality=personality)
                                found_song = True
                                break # Salir del bucle de selectores de canción
                            else:
                                d_logger.warning("Se clickeó la canción pero el reproductor no parece activo.")
                                # Presionar back por si acaso se abrió algo inesperado
                                device.press("back")
                                _human_delay_wrapper(1.0, 2.0, personality=personality)
                                
                        except Exception as e_listen:
                            d_logger.warning(f"Error al intentar reproducir canción: {e_listen}")
                            # Intentar presionar back para recuperarse
                            try: device.press("back"); _human_delay_wrapper(1,2) 
                            except: pass
                if found_song:
                    actions_performed_count += 1 # Escuchar cuenta como acción
                else:
                    # Si no se encontró canción, hacer scroll para buscar más
                    d_logger.debug("No se encontraron canciones clickeables, haciendo scroll...")
                    perform_random_scroll(device, device_id, personality)
                    phase_summary["explore_actions"].append("scroll_for_songs")
            
            # Pequeña pausa entre acciones
            _human_delay_wrapper(0.5, 2.0, personality=personality)

        phase_summary["songs_listened_count"] = songs_listened_count
        d_logger.info(f"Fase de artista completada: {actions_performed_count} acciones, {songs_listened_count} canciones escuchadas.")
        phase_summary["success"] = True

    except Exception as e:
        d_logger.error(f"Error en fase de visita a artista: {e}")
        phase_summary["error"] = str(e)
        take_screenshot(device, device_id, "artist_error_")
        phase_summary["success"] = False
    finally:
        phase_summary["duration"] = time.time() - start_time
        d_logger.info(f"Duración real fase artista: {phase_summary['duration'] / 60:.1f} min")
        
    return phase_summary["success"], phase_summary

def play_individual_tracks(device, device_id, package, tracks, personality, failed_links_set):
    d_logger = _get_device_logger(device_id)
    d_logger.info("=== INICIANDO FASE TRACKS INDIVIDUALES ===")
    phase_summary = {"tracks_available": len(tracks), "tracks_attempted": 0, "tracks_played_count": 0, "actions": [], "success": False, "error": None, "duration": 0}
    start_time = time.time()

    if not tracks:
        d_logger.warning("No hay tracks individuales disponibles para reproducir.")
        phase_summary["error"] = "No tracks available"
        # Considerar esto un éxito si no había tracks, o un fallo si debería haberlos?
        # Por ahora, lo marcamos como éxito porque no había nada que hacer.
        phase_summary["success"] = True 
        return True, phase_summary
    
    try:
        tracks_to_play = min(len(tracks), personality.individual_tracks_to_listen)
        d_logger.info(f"Intentando reproducir hasta {tracks_to_play} canciones individuales.")
        
        # Seleccionar tracks aleatorios de la lista disponible
        selected_tracks = random.sample(tracks, min(len(tracks), tracks_to_play + 2)) # Tomar algunos extra por si fallan
        
        tracks_played_count = 0
        for i, track_url in enumerate(selected_tracks):
            if tracks_played_count >= tracks_to_play:
                break # Ya se reprodujeron suficientes
            
            d_logger.info(f"Intentando track {i+1}/{len(selected_tracks)}: {track_url}")
            phase_summary["tracks_attempted"] += 1
            
            if open_spotify_url(device, device_id, track_url, personality, failed_links_set):
                action_log = {"url": track_url, "liked": False, "played": False, "visually_active": False, "duration": 0}
                track_listen_start = time.time()
                
                if click_like_button(device, device_id, personality): action_log["liked"] = True
                if click_play_button(device, device_id, personality): action_log["played"] = True
                
                action_log["visually_active"] = is_player_active_visually(device, device_id)
                
                if action_log["played"] or action_log["visually_active"]:
                    track_duration = personality.get_track_duration()
                    d_logger.info(f"Escuchando track durante ~{track_duration} segundos")
                    time.sleep(track_duration)
                    tracks_played_count += 1
                    action_log["duration"] = time.time() - track_listen_start
                    d_logger.info(f"Track {tracks_played_count}/{tracks_to_play} completado.")
                else:
                    d_logger.warning("No se pudo iniciar la reproducción del track.")
                
                phase_summary["actions"].append(action_log)
            else:
                d_logger.warning(f"No se pudo abrir el track: {track_url}")
                phase_summary["actions"].append({"url": track_url, "error": "Failed to open"})
        
        phase_summary["tracks_played_count"] = tracks_played_count
        d_logger.info(f"Fase de tracks individuales completada: {tracks_played_count} tracks reproducidos de {phase_summary['tracks_attempted']} intentos.")
        phase_summary["success"] = True # Considerar éxito si se completó la fase, incluso si no se tocaron todos los tracks

    except Exception as e:
        d_logger.error(f"Error en fase de reproducción de tracks individuales: {e}")
        phase_summary["error"] = str(e)
        take_screenshot(device, device_id, "tracks_error_")
        phase_summary["success"] = False
    finally:
        phase_summary["duration"] = time.time() - start_time
        d_logger.info(f"Duración real fase tracks: {phase_summary['duration'] / 60:.1f} min")
        
    return phase_summary["success"], phase_summary

# --- Función Principal del Worker por Dispositivo ---
def run_device_session(device_id, package, all_playlists, all_artists, all_tracks, followed_artists_set, failed_links_set):
    d_logger = _get_device_logger(device_id)
    d_logger.info(f"***** INICIANDO NUEVA SESIÓN PARA DISPOSITIVO: {device_id} / APK: {package} *****")
    session_summary = {
        "device_id": device_id,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "duration": 0,
        "phases": [],
        "errors": [],
        "personality_snapshot": {}
    }
    session_start_time = time.time()

    try:
        # 1) Conectar al dispositivo
        d_logger.info(f"Conectando a dispositivo: {device_id}")
        device = u2.connect_usb(device_id)

        # 2) Aplicar proxy si corresponde
        proxy = proxy_map.get(package)
        if proxy:
            d_logger.info(f"Asignando proxy {proxy} a {package}")
            device.set_proxy(proxy)
        else:
            d_logger.debug(f"No hay proxy asignado para {package}")

        # 3) Arrancar la app clonada
        d_logger.info(f"Iniciando app {package}")
        device.app_start(package)

        # 4) Chequear sesión / login si es necesario
        if device(resourceId="com.spotify.music:id/home_tab").exists(timeout=3):
            session_map[package] = True
            d_logger.info(f"{package} ya está logueado.")
        else:
            d_logger.info(f"{package} no tiene sesión, intentando login…")
            if account_queue:
                email, pwd = account_queue.popleft()
                d_logger.info(f"Logueando {email} en {package}")
                # aquí va tu lógica de login, e.g. login_module.login_via_ui(device, email, pwd)
                _human_delay_wrapper(5, 8, personality=None)
                if device(resourceId="com.spotify.music:id/home_tab").exists(timeout=5):
                    session_map[package] = True
                    d_logger.info(f"✅ Login exitoso en {package}")
                else:
                    d_logger.warning(f"❌ Falló login en {package}")
            else:
                d_logger.warning("🚫 No quedan cuentas disponibles para login.")
        _human_delay_wrapper(3, 5, personality=None)
        d_logger.info(f"Conexión establecida con {package} en {device_id}.")

        # 5) Crear personalidad y chequeo de horario activo
        personality = DevicePersonality(device_id)
        personality.update_dynamic_personality()

        if hasattr(personality, 'active_hours') and not personality.is_active_now():
            start, end = personality.active_hours
            d_logger.info(f"{device_id}/{package}: fuera del turno activo {personality.active_hours}. Durmiendo 1h.")
            # duerme en bloques de 1s para respetar stop_event
            for _ in range(3600):
                if stop_event.is_set():
                    break
                time.sleep(1)
            return False, {}  # sale para reintentar más tarde

        session_summary["personality_snapshot"] = personality.__dict__
        d_logger.info("Personalidad inicializada.")
        d_logger.debug(
            f"Patience={personality.patience:.2f}, "
            f"Curiosity={personality.curiosity:.2f}, "
            f"Engagement={personality.engagement:.2f}, "
            f"Speed={personality.speed_factor:.2f}"
        )

        # 6) Verificar contenido y tomar screenshot
        if not all_playlists:
            d_logger.error("No hay playlists disponibles. Abortando sesión.")
            raise Exception("No playlists available")
        take_screenshot(device, device_id, "session_start_")

        # 7) Ejecución de fases
        phase_results = []

        # Fase 1: Initial Playlist
        playlist_url = random.choice(all_playlists)
        success, summary = play_playlist(device, device_id, package, playlist_url, personality, failed_links_set)
        summary["phase_name"] = "Initial Playlist"
        phase_results.append(summary)
        if not success:
            d_logger.warning("Initial Playlist falló.")
            session_summary["errors"].append(summary.get("error", "Playlist phase failed"))

        # Fase 2: Artist Visit
        if all_artists and personality.should_explore_artist():
            artist_url = random.choice(all_artists)
            success, summary = visit_artist(device, device_id, package, artist_url, personality, followed_artists_set, failed_links_set)
            summary["phase_name"] = "Artist Visit"
            phase_results.append(summary)
            if not success:
                d_logger.warning("Artist Visit falló.")
                session_summary["errors"].append(summary.get("error", "Artist phase failed"))
        else:
            d_logger.info("Saltando Artist Visit.")

        # Fase 3: Individual Tracks
        if all_tracks and personality.track_hopping > 0.3:
            success, summary = play_individual_tracks(device, device_id, package, all_tracks, personality, failed_links_set)
            summary["phase_name"] = "Individual Tracks"
            phase_results.append(summary)
            if not success:
                d_logger.warning("Individual Tracks falló.")
                session_summary["errors"].append(summary.get("error", "Tracks phase failed"))
        else:
            d_logger.info("Saltando Individual Tracks.")

        # Fase 4: Search
        if personality.should_search():
            success, summary = perform_search(device, device_id, personality)
            summary["phase_name"] = "Search"
            phase_results.append(summary)
            if not success:
                d_logger.warning("Search falló.")
                session_summary["errors"].append(summary.get("error", "Search phase failed"))
        else:
            d_logger.info("Saltando Search.")

        # Fase 5: Final Playlist
        final_playlist_url = random.choice(all_playlists)
        success, summary = play_playlist(device, device_id, final_playlist_url, personality, failed_links_set)
        summary["phase_name"] = "Final Playlist"
        phase_results.append(summary)
        if not success:
            d_logger.warning("Final Playlist falló.")
            session_summary["errors"].append(summary.get("error", "Final Playlist phase failed"))

        session_summary["phases"] = phase_results
        d_logger.info(f"***** SESIÓN COMPLETADA PARA {device_id} / {package} *****")

    except Exception as e:
        # only try to screenshot if `device` was successfully defined
        if 'device' in locals():
            take_screenshot(device, device_id, "session_error_")
        main_logger.error(f"Session for {device_id} failed: {e}")
        return False, session_summary

    finally:
        session_summary["end_time"] = datetime.now().isoformat()
        session_summary["duration"] = time.time() - session_start_time
        d_logger.info(f"Duración total: {session_summary['duration']/60:.1f} min")
        log_session_summary(session_summary)
        try:
            take_screenshot(device, device_id, "session_end_")
        except:
            pass

    return True, session_summary

def log_session_summary(summary):
    """Añade el resumen de la sesión al log general."""
    try:
        with open(SESSION_SUMMARY_LOG, "a", encoding="utf-8") as f:
            f.write(f"--- Session Summary for {summary['device_id']} ({summary['start_time']} to {summary['end_time']}) ---\n")
            f.write(f"Duration: {summary['duration'] / 60:.1f} minutes\n")
            f.write(f"Errors encountered: {len(summary['errors'])}\n")
            if summary['errors']: f.write(f"  Errors: {'; '.join(summary['errors'])}\n")
            f.write("Phases executed:\n")
            for phase in summary['phases']:
                f.write(f"  - {phase.get('phase_name', 'Unknown Phase')}: Success={phase.get('success', False)}")
                if 'duration' in phase: f.write(f", Duration={phase['duration']:.1f}s")
                if 'error' in phase and phase['error']: f.write(f", Error='{phase['error']}'")
                f.write("\n")
            f.write("Personality Snapshot:\n")
            # Escribir solo algunos atributos clave de la personalidad
            p_snap = summary.get('personality_snapshot', {})
            def fmt(key):
                try:
                    return f"{float(p_snap.get(key, 0)):.2f}"
                except:
                    return "N/A"

            f.write(
                "  Patience: %s, Curiosity: %s, Engagement: %s, Speed: %s\n"
                % (fmt('patience'), fmt('curiosity'), fmt('engagement'), fmt('speed_factor'))
            )
            f.write("-"*50 + "\n")
    except Exception as e:
        main_logger.error(f"Error al escribir en session_summary.log: {e}")

def device_worker(device_id, package, all_playlists, all_artists, all_tracks, followed_artists_set, failed_links_set):
    d_logger = _get_device_logger(device_id)
    d_logger.info(f"Worker iniciado para dispositivo: {device_id} / paquete: {package}")
    
    while not stop_event.is_set():
        session_success, _ = run_device_session(
            device_id,
            package,
            all_playlists,
            all_artists,
            all_tracks,
            followed_artists_set,
            failed_links_set
        )

        if stop_event.is_set():
            break

        if not session_success:
            # Retentar con pausa
            retry_wait = random.uniform(60, 120)
            d_logger.info(f"Sesión fallida, reintentando en {retry_wait:.1f}s")
            time.sleep(retry_wait)
        else:
            # Sesión OK, esperar antes de la siguiente
            temp_personality = DevicePersonality(device_id)
            next_wait = random.uniform(90, 300) * (1 + temp_personality.patience * 0.5)
            d_logger.info(f"Sesión completada, siguiente en {next_wait/60:.1f}min")
            time.sleep(next_wait)

    d_logger.info(f"Worker finalizado para dispositivo: {device_id}")

def main():
    main_logger.info("--- Iniciando Playlist Player (Enhanced) ---")

    # Load persisted state before anything else
    followed_artists_set = load_set_from_file(FOLLOWED_ARTISTS_PATH)
    failed_links_set     = load_set_from_file(FAILED_LINKS_PATH)
    backup_playlist_file(PLAYLIST_PATH, BACKUP_PLAYLIST_PATH)
    playlists, artists, tracks = load_links_from_file(PLAYLIST_PATH, failed_links_set)

    # 1) Find all connected devices
    devices = get_connected_devices()
    if not devices:
        main_logger.error("No se encontraron dispositivos conectados. El programa no puede continuar.")
        return 1

    # 2) For each device, discover installed Spotify clones
    device_packages = {}
    for dev in devices:
        pkgs = get_spotify_packages(dev)
        if not pkgs:
            main_logger.warning(f"No Spotify packages found on {dev}")
        device_packages[dev] = pkgs

    # 3) Round-robin assign proxies & init session_map
    for dev, pkgs in device_packages.items():
        for i, pkg in enumerate(pkgs):
            proxy_map[pkg]   = proxies[i % len(proxies)] if proxies else None
            session_map[pkg] = False

    # 4) Spawn sessions with a pool (max 5 concurrent ADB connections)
    with ThreadPoolExecutor(max_workers=5) as executor:
        for dev, pkgs in device_packages.items():
            for pkg in pkgs:
                executor.submit(
                    device_worker,
                    dev,
                    pkg,                  # ← este es el nuevo parámetro
                    playlists,
                    artists,
                    tracks,
                    followed_artists_set,
                    failed_links_set
                )
                _human_delay_wrapper(0.3, 1.0, use_factor=False)
    # the with-block waits for all tasks to finish

    # 6) Final persistence
    save_set_to_file(FOLLOWED_ARTISTS_PATH, followed_artists_set)
    save_set_to_file(FAILED_LINKS_PATH, failed_links_set)
    main_logger.info("--- Finalizado ---")
    return 0

if __name__ == "__main__":
    # Configurar logging principal a archivo
    main_log_file = os.path.join(LOG_DIR, f"playlist_player_MAIN_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    main_file_handler = logging.FileHandler(main_log_file, encoding='utf-8')
    main_file_handler.setFormatter(main_formatter)
    main_logger.addHandler(main_file_handler)
    
    sys.exit(main())

def playlist_mode():
    return main()