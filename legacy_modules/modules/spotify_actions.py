# -*- coding: utf-8 -*-
"""Módulo para manejar las interacciones específicas con la UI de Spotify en el dispositivo."""

import time
import random
import logging
import json
from datetime import datetime

# Asumiendo que estos módulos existen y están en el path correcto
from .human_behavior import DevicePersonality, human_sleep, human_click, human_scroll, human_type
from .proxy_manager import Proxy
# Necesitaríamos una librería para interactuar con la UI del dispositivo via ADB
# Por ejemplo, uiautomator2, appium, o comandos ADB directos + screen parsing
# Aquí simularemos las interacciones

# Configuración del logger específico para acciones de Spotify
# Se configurará un handler por dispositivo en el flujo principal
spotify_logger = logging.getLogger("SpotifyActions")
# Remover handlers por defecto para evitar duplicados si se configura en otro lado
if spotify_logger.hasHandlers():
    spotify_logger.handlers.clear()
spotify_logger.propagate = False # Evitar que suba al root logger si no queremos
spotify_logger.setLevel(logging.INFO)
# El handler específico (FileHandler, JSON) se añadirá dinámicamente por dispositivo

def setup_device_logger(device_serial):
    """Configura un logger JSON específico para un dispositivo."""
    log_dir = "logs"
    # Crear directorio si no existe (idealmente se hace al inicio)
    import os
    os.makedirs(log_dir, exist_ok=True)

    # Nombre de archivo con fecha para rotación diaria
    log_file = os.path.join(log_dir, f"device_{device_serial}_{datetime.now().strftime("%Y%m%d")}.log.json")

    # Crear handler JSON
    # Usar Formatter personalizado si es necesario para estructura JSON exacta
    # Aquí un ejemplo simple:
    # formatter = logging.Formatter(	'{ "timestamp": "%(asctime)s", "level": "%(levelname)s", "device": "' + device_serial + '", "message": "%(message)s" }')
    # file_handler = logging.FileHandler(log_file)
    # file_handler.setFormatter(formatter)

    # Simplificado: Usaremos un logger estándar y formatearemos el mensaje como JSON
    # NOTA: Una librería como python-json-logger sería más robusta
    file_handler = logging.FileHandler(log_file)
    formatter = logging.Formatter(	'%(asctime)s | %(levelname)s | %(message)s') # Formato temporal
    file_handler.setFormatter(formatter)

    # Limpiar handlers existentes para este logger específico si se reconfigura
    logger_name = f"Device_{device_serial}"
    device_logger = logging.getLogger(logger_name)
    if device_logger.hasHandlers():
        device_logger.handlers.clear()

    device_logger.addHandler(file_handler)
    device_logger.setLevel(logging.INFO)
    device_logger.propagate = False # No propagar a otros loggers
    return device_logger

def log_action(device_logger, action, success, details=None):
    """Registra una acción en formato JSON."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "success": success,
        "details": details or {}
    }
    # Convertir a string JSON para el logger simple
    # Con un JSON formatter, esto sería automático
    device_logger.info(json.dumps(log_entry))


def check_spotify_logged_in(device_serial, personality: DevicePersonality) -> bool:
    """Verifica si Spotify ya está logueado (simulado)."""
    # TODO: Implementar lógica real usando ADB/UI Automator
    # Ejemplo: Buscar elementos específicos de la pantalla de inicio de Spotify
    spotify_logger.info(f"[{device_serial}] Checking Spotify login status...")
    human_sleep(1, 3, personality)
    # Simulación: Asumir que a veces no está logueado
    is_logged_in = random.choice([True, True, False])
    spotify_logger.info(f"[{device_serial}] Spotify logged in status: {is_logged_in}")
    return is_logged_in

def perform_spotify_login(device_serial, account_details, personality: DevicePersonality):
    """Realiza el login en Spotify usando UI (simulado)."""
    # TODO: Implementar lógica real usando ADB/UI Automator
    username, password = account_details.split(":") # Asumiendo formato user:pass
    spotify_logger.info(f"[{device_serial}] Attempting Spotify login for user {username}...")

    # Simular pasos: abrir app, encontrar campos, escribir, clickear login
    human_sleep(2, 5, personality)
    # Simular escritura de usuario
    spotify_logger.info(f"[{device_serial}] Typing username...")
    human_type(None, username, personality) # Elemento simulado
    human_sleep(0.5, 1.5, personality)
    # Simular escritura de contraseña
    spotify_logger.info(f"[{device_serial}] Typing password...")
    human_type(None, password, personality) # Elemento simulado
    human_sleep(0.5, 1.5, personality)
    # Simular click en botón de login
    spotify_logger.info(f"[{device_serial}] Clicking login button...")
    human_click(None, personality) # Elemento simulado
    human_sleep(3, 6, personality) # Esperar carga post-login

    # Simular manejo de popups post-login ("Abrir con", "Más tarde")
    if random.random() < 0.3: # 30% de probabilidad de popup
        spotify_logger.info(f"[{device_serial}] Handling post-login popup...")
        human_sleep(1, 3, personality)
        human_click(None, personality) # Click en "Más tarde" o similar
        human_sleep(1, 2, personality)

    # Verificar si el login fue exitoso (simulado)
    login_success = random.choice([True, True, True, False]) # 75% éxito
    if not login_success:
        spotify_logger.error(f"[{device_serial}] Spotify login failed for user {username}.")
        raise Exception("Simulated login failure")

    spotify_logger.info(f"[{device_serial}] Spotify login successful for user {username}.")
    return True

def open_spotify_url(device_serial, url, personality: DevicePersonality):
    """Abre una URL específica en Spotify (simulado)."""
    # TODO: Implementar lógica real usando ADB (am start -a android.intent.action.VIEW -d <url>)
    spotify_logger.info(f"[{device_serial}] Opening URL: {url}")
    human_sleep(2, 4, personality)
    # Simular posible diálogo "Abrir con"
    if random.random() < 0.2:
        spotify_logger.info(f"[{device_serial}] Handling 'Open with' dialog...")
        human_sleep(1, 2, personality)
        human_click(None, personality) # Click en Spotify
        human_sleep(1, 3, personality)

    # Simular carga de la página/playlist/artista
    human_sleep(3, 7, personality)
    spotify_logger.info(f"[{device_serial}] URL opened successfully (simulated).")
    return True

def play_initial_playlist(device_serial, playlist_url, personality: DevicePersonality):
    """Abre una playlist, la reproduce y realiza acciones humanas."""
    device_logger = logging.getLogger(f"Device_{device_serial}")
    action = "play_initial_playlist"
    log_action(device_logger, action, True, {"url": playlist_url, "status": "started"})
    try:
        open_spotify_url(device_serial, playlist_url, personality)

        # Simular acciones: scroll, like, shuffle, play
        human_scroll(None, personality)
        human_sleep(1, 3, personality)

        if personality.should_like():
            spotify_logger.info(f"[{device_serial}] Liking playlist...")
            human_click(None, personality) # Click en botón Like
            human_sleep(1, 2, personality)

        # Simular click en Shuffle/Play
        spotify_logger.info(f"[{device_serial}] Clicking Play/Shuffle...")
        human_click(None, personality)
        human_sleep(2, 4, personality)

        # Simular tiempo de escucha
        listen_duration = random.uniform(30, 120) # 30-120 segundos (reducido para prueba)
        spotify_logger.info(f"[{device_serial}] Listening to playlist for {listen_duration:.1f}s...")
        human_sleep(listen_duration, listen_duration, personality) # Usar personalidad para ajustar espera

        log_action(device_logger, action, True, {"url": playlist_url, "status": "completed", "duration_seconds": listen_duration})
        return True
    except Exception as e:
        log_action(device_logger, action, False, {"url": playlist_url, "error": str(e)})
        spotify_logger.error(f"[{device_serial}] Error in play_initial_playlist: {e}")
        raise # Re-lanzar para que el orquestador maneje el fallo

def visit_artist_profile(device_serial, artist_url, personality: DevicePersonality):
    """Visita un perfil de artista, opcionalmente sigue y escucha canciones."""
    device_logger = logging.getLogger(f"Device_{device_serial}")
    action = "visit_artist_profile"
    log_action(device_logger, action, True, {"url": artist_url, "status": "started"})
    try:
        open_spotify_url(device_serial, artist_url, personality)

        # Simular scroll
        human_scroll(None, personality)
        human_sleep(1, 3, personality)

        # Decidir si seguir
        if personality.should_follow():
            spotify_logger.info(f"[{device_serial}] Following artist...")
            human_click(None, personality) # Click en botón Follow
            human_sleep(1, 2, personality)
        else:
            spotify_logger.info(f"[{device_serial}] Decided not to follow artist.")

        # Escuchar X canciones del artista
        songs_to_listen = random.randint(1, 5)
        total_listen_duration = 0
        spotify_logger.info(f"[{device_serial}] Listening to {songs_to_listen} songs from artist...")
        for i in range(songs_to_listen):
            spotify_logger.info(f"[{device_serial}] Playing song {i+1}/{songs_to_listen}...")
            human_click(None, personality) # Click en una canción
            human_sleep(1, 3, personality)
            song_duration = random.uniform(20, 60) # Duración reducida para prueba
            human_sleep(song_duration, song_duration, personality)
            total_listen_duration += song_duration
            # Simular like/skip ocasional
            if personality.should_like():
                 spotify_logger.info(f"[{device_serial}] Liking song {i+1}...")
                 human_click(None, personality)
                 human_sleep(0.5, 1.5, personality)
            if personality.should_skip() and i < songs_to_listen - 1: # No saltar la última
                 spotify_logger.info(f"[{device_serial}] Skipping song {i+1}...")
                 human_click(None, personality) # Click en skip
                 human_sleep(1, 2, personality)
                 continue # Pasar a la siguiente canción

        log_action(device_logger, action, True, {"url": artist_url, "status": "completed", "followed": personality.should_follow(), "songs_listened": songs_to_listen, "total_duration_seconds": total_listen_duration})
        return True
    except Exception as e:
        log_action(device_logger, action, False, {"url": artist_url, "error": str(e)})
        spotify_logger.error(f"[{device_serial}] Error in visit_artist_profile: {e}")
        raise

def play_individual_tracks(device_serial, track_urls: list, personality: DevicePersonality):
    """Reproduce una selección aleatoria de pistas individuales."""
    device_logger = logging.getLogger(f"Device_{device_serial}")
    action = "play_individual_tracks"
    log_action(device_logger, action, True, {"track_count": len(track_urls), "status": "started"})
    played_count = 0
    total_listen_duration = 0
    try:
        if not track_urls:
            spotify_logger.warning(f"[{device_serial}] No individual track URLs provided.")
            log_action(device_logger, action, True, {"status": "skipped", "reason": "No tracks"})
            return True

        # Seleccionar algunas pistas aleatorias para reproducir (ej. 1 a 3)
        num_to_play = random.randint(1, min(len(track_urls), 3))
        tracks_to_play = random.sample(track_urls, num_to_play)
        spotify_logger.info(f"[{device_serial}] Playing {num_to_play} individual tracks...")

        for i, track_url in enumerate(tracks_to_play):
            track_action = "play_single_track"
            log_action(device_logger, track_action, True, {"url": track_url, "status": "started", "index": i+1})
            try:
                open_spotify_url(device_serial, track_url, personality)
                # Simular click en Play si es necesario (a veces auto-play)
                if random.random() < 0.5:
                    human_click(None, personality)
                human_sleep(1, 3, personality)
                # Simular tiempo de escucha
                listen_duration = random.uniform(20, 90) # Duración reducida
                spotify_logger.info(f"[{device_serial}] Listening to track {i+1}/{num_to_play} for {listen_duration:.1f}s...")
                human_sleep(listen_duration, listen_duration, personality)
                total_listen_duration += listen_duration
                played_count += 1
                # Simular like
                if personality.should_like():
                    spotify_logger.info(f"[{device_serial}] Liking track {i+1}...")
                    human_click(None, personality)
                    human_sleep(0.5, 1.5, personality)
                log_action(device_logger, track_action, True, {"url": track_url, "status": "completed", "duration_seconds": listen_duration})
            except Exception as track_e:
                log_action(device_logger, track_action, False, {"url": track_url, "error": str(track_e)})
                spotify_logger.error(f"[{device_serial}] Error playing individual track {track_url}: {track_e}")
                # Continuar con la siguiente pista si una falla
                continue

        log_action(device_logger, action, True, {"status": "completed", "played_count": played_count, "total_duration_seconds": total_listen_duration})
        return True
    except Exception as e:
        log_action(device_logger, action, False, {"error": str(e)})
        spotify_logger.error(f"[{device_serial}] Error in play_individual_tracks: {e}")
        raise

def play_final_playlist(device_serial, playlist_url, personality: DevicePersonality):
    """Reproduce una playlist final."""
    # Similar a play_initial_playlist, podría reutilizarse o tener ligeras variaciones
    device_logger = logging.getLogger(f"Device_{device_serial}")
    action = "play_final_playlist"
    log_action(device_logger, action, True, {"url": playlist_url, "status": "started"})
    try:
        open_spotify_url(device_serial, playlist_url, personality)
        spotify_logger.info(f"[{device_serial}] Clicking Play/Shuffle on final playlist...")
        human_click(None, personality)
        human_sleep(2, 4, personality)
        listen_duration = random.uniform(20, 60) # Duración más corta para la final?
        spotify_logger.info(f"[{device_serial}] Listening to final playlist for {listen_duration:.1f}s...")
        human_sleep(listen_duration, listen_duration, personality)
        log_action(device_logger, action, True, {"url": playlist_url, "status": "completed", "duration_seconds": listen_duration})
        return True
    except Exception as e:
        log_action(device_logger, action, False, {"url": playlist_url, "error": str(e)})
        spotify_logger.error(f"[{device_serial}] Error in play_final_playlist: {e}")
        raise

# --- Función principal que ejecuta el ciclo completo para un dispositivo --- 
# Esta función será llamada por el DeviceOrchestrator

def run_spotify_session(device, proxy: Proxy):
    """Ejecuta el ciclo completo de acciones de Spotify para un dispositivo."""
    device_serial = device.serial
    personality = device.personality
    device_logger = setup_device_logger(device_serial)
    log_action(device_logger, "session_start", True, {"proxy": proxy.address})

    # TODO: Cargar URLs desde un archivo (ej. data/playlists.txt)
    # Asumiendo que tenemos listas separadas por tipo por ahora
    # En la versión final, leer un archivo y clasificar URLs
    playlists = ["spotify:playlist:37i9dQZF1DXcBWIGoYBM5M", "spotify:playlist:37i9dQZF1DX0XUfTFmNBRM"]
    artists = ["spotify:artist:06HL4z0CvFAxyc27GXpf02", "spotify:artist:1uNFoZAHBGtllmzznpCI3s"]
    tracks = ["spotify:track:0e7ipj03S05BNilyu5bRzt", "spotify:track:7qiZfU4dY1lWllzX7mPBI3", "spotify:track:1r9xUipOqoNwggBpENDsvJ"]

    account_file = "data/accounts.txt"
    accounts = []
    try:
        with open(account_file, 'r') as f:
            accounts = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        log_action(device_logger, "session_error", False, {"error": f"Account file not found: {account_file}"})
        raise Exception(f"Account file not found: {account_file}")

    if not accounts:
        log_action(device_logger, "session_error", False, {"error": "No accounts found in file"})
        raise Exception("No accounts found in account file")

    # Seleccionar una cuenta (podría ser rotativa o asignada)
    account = random.choice(accounts)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 1. Verificar/Realizar Login
            if not check_spotify_logged_in(device_serial, personality):
                perform_spotify_login(device_serial, account, personality)
                log_action(device_logger, "login", True, {"account": account.split(':')[0]})
            else:
                log_action(device_logger, "login_check", True, {"status": "already_logged_in"})

            # 2. Playlist Inicial
            initial_playlist = random.choice(playlists)
            play_initial_playlist(device_serial, initial_playlist, personality)
            human_sleep(personality.get_action_delay() * 0.8, personality.get_action_delay() * 1.2, personality)

            # 3. Visita de Artista
            artist_to_visit = random.choice(artists)
            visit_artist_profile(device_serial, artist_to_visit, personality)
            human_sleep(personality.get_action_delay() * 0.8, personality.get_action_delay() * 1.2, personality)

            # 4. Pistas Individuales
            play_individual_tracks(device_serial, tracks, personality)
            human_sleep(personality.get_action_delay() * 0.8, personality.get_action_delay() * 1.2, personality)

            # 5. Playlist Final
            final_playlist = random.choice([p for p in playlists if p != initial_playlist] or playlists)
            play_final_playlist(device_serial, final_playlist, personality)

            log_action(device_logger, "session_end", True, {"status": "completed"})
            break # Salir del bucle de reintentos si todo fue exitoso

        except Exception as e:
            log_action(device_logger, "session_attempt_failed", False, {"attempt": attempt + 1, "error": str(e)})
            spotify_logger.error(f"[{device_serial}] Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt + 1 == max_retries:
                log_action(device_logger, "session_end", False, {"status": "failed_after_retries"})
                raise Exception(f"Session failed after {max_retries} attempts") from e
            else:
                # Esperar antes de reintentar (podría incluir rotación de proxy si el orquestador lo soporta)
                human_sleep(10, 20, personality)

