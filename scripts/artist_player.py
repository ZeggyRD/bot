#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import os
import sys
import time
import random
import logging
import subprocess
import traceback
import re
from datetime import datetime
import uiautomator2 as u2

# Agregar carpeta base del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Intentar importar módulos del sistema
try:
    from modules.human_behavior import human_behavior
except ImportError:
    # Fallback si no se puede importar
    class HumanBehaviorFallback:
        @staticmethod
        def human_delay(min_sec=1.5, max_sec=3.5):
            delay = random.uniform(min_sec, max_sec)
            time.sleep(delay)
            return delay
    human_behavior = HumanBehaviorFallback()

# Configuración del sistema de logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"artist_player_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ArtistPlayer")

# Constantes
ARTIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "artists.txt")
SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
MAX_RETRIES = 3  # Número máximo de reintentos para operaciones críticas
MIN_PLAY_TIME = 180  # Tiempo mínimo de reproducción en segundos (3 minutos)
MAX_PLAY_TIME = 600  # Tiempo máximo de reproducción en segundos (10 minutos)

def get_connected_devices():
    """Obtiene la lista de dispositivos Android conectados"""
    try:
        logger.debug("Obteniendo dispositivos conectados")
        
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True
        )
        
        if result.stderr:
            logger.error(f"Error al ejecutar 'adb devices': {result.stderr}")
        
        logger.debug(f"Resultado de 'adb devices':\n{result.stdout}")
        
        lines = result.stdout.strip().split("\n")[1:]  # Ignorar la primera línea (título)
        devices = []
        
        for line in lines:
            if line.strip() and "device" in line:
                device_id = line.split()[0]
                devices.append(device_id)
        
        logger.info(f"Dispositivos conectados: {devices}")
        return devices
    except Exception as e:
        logger.error(f"Error al obtener dispositivos conectados: {e}")
        logger.debug(traceback.format_exc())
        return []

def load_artists():
    """Carga las URLs de artistas desde el archivo"""
    try:
        # Log before accessing the file
        logger.debug(f"Intentando cargar artistas desde: {ARTIST_PATH}")
        
        if not os.path.exists(ARTIST_PATH):
            logger.error(f"Archivo de artistas no encontrado: {ARTIST_PATH}")
            return []

        with open(ARTIST_PATH, "r") as f:
            artist_data = f.readlines()
            logger.debug(f"Contenido de artists.txt antes de cargar: {artist_data[:5]}")  # Log first 5 lines

        artists = [line.strip() for line in artist_data if line.strip() and line.strip().startswith("http")]
        
        logger.info(f"Artistas cargados: {len(artists)}")
        if artists:
            logger.debug(f"Ejemplos de artistas: {artists[:3] if len(artists) >= 3 else artists}")
        return artists
    except Exception as e:
        logger.error(f"Error al cargar artistas: {e}")
        logger.debug(traceback.format_exc())
        return []

def take_screenshot(device, device_id):
    """Captura la pantalla del dispositivo"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(SCREENSHOTS_DIR, f"artist_player_{device_id}_{timestamp}.png")
        
        logger.debug(f"Capturando pantalla en {screenshot_path}")
        device.screenshot(screenshot_path)
        
        logger.debug(f"Captura de pantalla guardada en {screenshot_path}")
        return screenshot_path
    except Exception as e:
        logger.error(f"Error al capturar pantalla: {e}")
        logger.debug(traceback.format_exc())
        
        # Intentar método alternativo con ADB
        try:
            logger.debug("Intentando captura alternativa con ADB")
            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"adb_screenshot_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            # Ejecutar comando ADB para capturar pantalla
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "screencap", "-p", "/sdcard/screenshot.png"],
                capture_output=True,
                text=True
            )
            logger.debug(f"ADB screencap: {result.stdout}")
            if result.stderr:
                logger.error(f"Error en ADB screencap: {result.stderr}")
            
            # Descargar la captura al PC
            result = subprocess.run(
                ["adb", "-s", device_id, "pull", "/sdcard/screenshot.png", screenshot_path],
                capture_output=True,
                text=True
            )
            logger.debug(f"ADB pull: {result.stdout}")
            if result.stderr:
                logger.error(f"Error en ADB pull: {result.stderr}")
            
            if os.path.exists(screenshot_path):
                logger.debug(f"Captura alternativa exitosa: {screenshot_path}")
                return screenshot_path
        except Exception as e2:
            logger.error(f"Error en método alternativo de captura: {e2}")
            logger.debug(traceback.format_exc())
        
        return None

def get_screen_dimensions(device_id):
    """Obtiene las dimensiones de la pantalla del dispositivo"""
    try:
        logger.debug(f"Obteniendo dimensiones de pantalla para {device_id}")
        
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "wm", "size"],
            capture_output=True,
            text=True
        )
        
        if result.stderr:
            logger.error(f"Error al obtener dimensiones: {result.stderr}")
        
        # Parsear las dimensiones (formato: "Physical size: 1080x2340")
        output = result.stdout.strip()
        logger.debug(f"Resultado de 'wm size': {output}")
        
        match = re.search(r'(\d+)x(\d+)', output)
        if match:
            width = int(match.group(1))
            height = int(match.group(2))
            logger.debug(f"Dimensiones obtenidas: {width}x{height}")
            return width, height
        else:
            logger.error(f"No se pudieron parsear las dimensiones: {output}")
            return 1080, 1920  # Valores predeterminados
    except Exception as e:
        logger.error(f"Error al obtener dimensiones de pantalla: {e}")
        logger.debug(traceback.format_exc())
        return 1080, 1920  # Valores predeterminados

def handle_open_with_dialog(device, device_id):
    """Maneja el diálogo 'Abrir con' si aparece"""
    try:
        logger.debug("Verificando si aparece diálogo 'Abrir con'")
        
        # Método 1: Buscar por texto
        for text in ["Spotify", "Abrir con", "Open with"]:
            if device(textContains=text).exists(timeout=5):
                logger.info(f"Diálogo 'Abrir con' detectado (texto: {text})")
                device(textContains="Spotify").click()
                logger.debug("Seleccionando Spotify como app predeterminada")
                time.sleep(2)
                
                # Buscar opciones "Siempre" o "Always"
                for always_text in ["Siempre", "Always", "Just once", "Solo esta vez"]:
                    if device(textContains=always_text).exists:
                        logger.debug(f"Opción '{always_text}' encontrada, seleccionando")
                        device(textContains=always_text).click()
                        time.sleep(2)
                        return True
                
                return True
        
        # Método 2: Buscar por resource-id
        for resource_id in ["android:id/resolver_list", "android:id/chooser_list"]:
            if device(resourceId=resource_id).exists:
                logger.info(f"Diálogo 'Abrir con' detectado (resource-id: {resource_id})")
                
                # Buscar Spotify en la lista
                spotify_app = device(textContains="Spotify")
                if spotify_app.exists:
                    logger.debug("Seleccionando Spotify de la lista")
                    spotify_app.click()
                    time.sleep(2)
                    
                    # Buscar opciones "Siempre" o "Always"
                    for always_text in ["Siempre", "Always", "Just once", "Solo esta vez"]:
                        if device(textContains=always_text).exists:
                            logger.debug(f"Opción '{always_text}' encontrada, seleccionando")
                            device(textContains=always_text).click()
                            time.sleep(2)
                            return True
                    
                    return True
        
        logger.debug("No se detectó diálogo 'Abrir con'")
        return False
    except Exception as e:
        logger.error(f"Error al manejar diálogo 'Abrir con': {e}")
        logger.debug(traceback.format_exc())
        return False

def is_spotify_foreground(device_id):
    """Verifica si Spotify está en primer plano"""
    try:
        logger.debug(f"Verificando si Spotify está en primer plano en {device_id}")
        
        # Usar dumpsys para verificar la actividad en primer plano
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "dumpsys", "activity", "activities"],
            capture_output=True,
            text=True
        )
        
        # Buscar mResumedActivity o mFocusedActivity
        output = result.stdout
        
        # Usar regex para encontrar la actividad en primer plano
        pattern = r'(mResumedActivity|mFocusedActivity).*?(com\.spotify\.music|com\.spotify\.music\.clone\d*)'
        match = re.search(pattern, output)
        
        if match:
            logger.info(f"Spotify está en primer plano en {device_id}")
            return True
        else:
            logger.warning(f"Spotify NO está en primer plano en {device_id}")
            return False
    except Exception as e:
        logger.error(f"Error al verificar si Spotify está en primer plano: {e}")
        logger.debug(traceback.format_exc())
        return False

def open_artist_intent(device_id, artist_url, retry_count=0):
    """Abre una URL de artista mediante intent"""
    if retry_count >= MAX_RETRIES:
        logger.error(f"Se alcanzó el número máximo de reintentos ({MAX_RETRIES}) para abrir artista")
        return False
    
    try:
        logger.info(f"Abriendo artista en {device_id}: {artist_url}")
        
        # Conectar al dispositivo
        device = u2.connect_usb(device_id)
        
        # Ir a la pantalla de inicio
        logger.debug("Presionando botón Home")
        device.press("home")
        time.sleep(1)
        
        # Abrir la URL mediante intent
        logger.debug(f"Ejecutando intent para abrir URL: {artist_url}")
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", artist_url],
            capture_output=True,
            text=True
        )
        
        logger.debug(f"Resultado del intent: {result.stdout}")
        if result.stderr:
            logger.warning(f"Error en intent: {result.stderr}")
        
        # Esperar a que se abra
        logger.debug("Esperando a que se abra la aplicación")
        time.sleep(6)
        
        # Manejar diálogo "Abrir con" si aparece
        handle_open_with_dialog(device, device_id)
        
        # Esperar a que cargue completamente
        logger.debug("Esperando a que cargue completamente")
        time.sleep(6)
        
        # Tomar captura de pantalla para verificar
        take_screenshot(device, device_id)
        
        # Verificar si Spotify está en primer plano
        if not is_spotify_foreground(device_id):
            logger.warning(f"Spotify no está en primer plano después de abrir artista, reintentando")
            
            # Reintentar
            if retry_count < MAX_RETRIES - 1:
                logger.info(f"Reintentando abrir artista (intento {retry_count + 2}/{MAX_RETRIES})")
                time.sleep(5)
                return open_artist_intent(device_id, artist_url, retry_count + 1)
            else:
                logger.error("No se pudo abrir Spotify después de múltiples intentos")
                return False
        
        logger.info(f"Artista abierto correctamente en {device_id}")
        return True
    except Exception as e:
        logger.error(f"Error al abrir artista: {e}")
        logger.debug(traceback.format_exc())
        
        # Reintentar
        if retry_count < MAX_RETRIES - 1:
            logger.info(f"Reintentando abrir artista (intento {retry_count + 2}/{MAX_RETRIES})")
            time.sleep(5)
            return open_artist_intent(device_id, artist_url, retry_count + 1)
        
        return False

def press_play(device, device_id):
    """Toca el botón de reproducción usando múltiples métodos"""
    try:
        logger.info(f"Buscando y presionando botón de reproducción en {device_id}")
        
        # Método 1: Buscar por descripción
        logger.debug("Buscando botón por descripción")
        play_found = False
        
        for desc in ["Play", "Reproducir", "play", "reproducir"]:
            if device(descriptionContains=desc).exists(timeout=8):
                logger.debug(f"Botón encontrado por descripción: {desc}")
                play_button = device(descriptionContains=desc)
                bounds = play_button.info.get('bounds', {})
                
                if bounds:
                    logger.debug(f"Presionando botón en posición: {bounds}")
                    play_button.click()
                    play_found = True
                    break
        
        # Método 2: Buscar por resource-id
        if not play_found:
            logger.debug("Buscando botón por resource-id")
            for resource_id in ["com.spotify.music:id/play_pause_button", "com.spotify.music:id/play_button"]:
                if device(resourceId=resource_id).exists(timeout=5):
                    logger.debug(f"Botón encontrado por resource-id: {resource_id}")
                    device(resourceId=resource_id).click()
                    play_found = True
                    break
        
        # Método 3: Usar coordenadas aproximadas
        if not play_found:
            logger.debug("Usando coordenadas aproximadas para botón de reproducción")
            
            # Obtener dimensiones de la pantalla
            width, height = get_screen_dimensions(device_id)
            
            # Calcular posición aproximada del botón de reproducción (centro de la pantalla, tercio superior)
            x = width // 2
            y = height // 3
            
            logger.debug(f"Presionando en coordenadas aproximadas: ({x}, {y})")
            device.click(x, y)
            play_found = True
        
        # Esperar un momento para que comience la reproducción
        time.sleep(2)
        
        # Tomar captura de pantalla para verificar
        take_screenshot(device, device_id)
        
        logger.info(f"Botón de reproducción presionado en {device_id}")
        return True
    except Exception as e:
        logger.error(f"Error al presionar botón de reproducción: {e}")
        logger.debug(traceback.format_exc())
        return False

def press_follow_if_needed(device, device_id):
    """Toca el botón de seguir artista si está disponible"""
    try:
        logger.info(f"Buscando y presionando botón de seguir en {device_id}")
        
        # Método 1: Buscar por texto
        logger.debug("Buscando botón por texto")
        follow_found = False
        
        for text in ["Follow", "Seguir", "FOLLOW", "SEGUIR"]:
            if device(textMatches=f"(?i){text}").exists(timeout=6):
                logger.debug(f"Botón encontrado por texto: {text}")
                device(textMatches=f"(?i){text}").click()
                follow_found = True
                time.sleep(2)
                break
        
        # Método 2: Buscar por resource-id
        if not follow_found:
            logger.debug("Buscando botón por resource-id")
            for resource_id in ["com.spotify.music:id/follow_button", "com.spotify.music:id/follow_artist_button"]:
                if device(resourceId=resource_id).exists(timeout=5):
                    logger.debug(f"Botón encontrado por resource-id: {resource_id}")
                    device(resourceId=resource_id).click()
                    follow_found = True
                    time.sleep(2)
                    break
        
        # Método 3: Usar coordenadas aproximadas
        if not follow_found:
            logger.debug("Usando coordenadas aproximadas para botón de seguir")
            
            # Obtener dimensiones de la pantalla
            width, height = get_screen_dimensions(device_id)
            
            # Calcular posición aproximada del botón de seguir (parte superior de la pantalla)
            x = width - 150
            y = 150
            
            logger.debug(f"Presionando en coordenadas aproximadas: ({x}, {y})")
            device.click(x, y)
            follow_found = True
            time.sleep(2)
        
        if follow_found:
            logger.info(f"Botón de seguir presionado en {device_id}")
        else:
            logger.info(f"No se encontró botón de seguir o ya se sigue al artista en {device_id}")
        
        return True
    except Exception as e:
        logger.error(f"Error al presionar botón de seguir: {e}")
        logger.debug(traceback.format_exc())
        return False

def activate_shuffle(device, device_id):
    """Activa el modo aleatorio (shuffle)"""
    try:
        logger.info(f"Intentando activar modo aleatorio en {device_id}")
        
        # Método 1: Buscar por descripción
        logger.debug("Buscando botón shuffle por descripción")
        shuffle_found = False
        
        for desc in ["Shuffle", "Aleatorio", "shuffle", "aleatorio"]:
            if device(descriptionContains=desc).exists(timeout=5):
                logger.debug(f"Botón shuffle encontrado por descripción: {desc}")
                device(descriptionContains=desc).click()
                shuffle_found = True
                time.sleep(2)
                break
        
        # Método 2: Buscar por texto
        if not shuffle_found:
            logger.debug("Buscando botón shuffle por texto")
            for text in ["Shuffle", "Aleatorio", "SHUFFLE", "ALEATORIO"]:
                if device(textContains=text).exists(timeout=5):
                    logger.debug(f"Botón shuffle encontrado por texto: {text}")
                    device(textContains=text).click()
                    shuffle_found = True
                    time.sleep(2)
                    break
        
        # Método 3: Buscar por resource-id
        if not shuffle_found:
            logger.debug("Buscando botón shuffle por resource-id")
            for resource_id in ["com.spotify.music:id/shuffle_button", "com.spotify.music:id/shuffle"]:
                if device(resourceId=resource_id).exists(timeout=5):
                    logger.debug(f"Botón shuffle encontrado por resource-id: {resource_id}")
                    device(resourceId=resource_id).click()
                    shuffle_found = True
                    time.sleep(2)
                    break
        
        # Método 4: Usar coordenadas aproximadas
        if not shuffle_found:
            logger.debug("Usando coordenadas aproximadas para botón shuffle")
            
            # Obtener dimensiones de la pantalla
            width, height = get_screen_dimensions(device_id)
            
            # Calcular posición aproximada del botón shuffle (parte inferior de la pantalla)
            x = width // 4
            y = height - 150
            
            logger.debug(f"Presionando en coordenadas aproximadas: ({x}, {y})")
            device.click(x, y)
            shuffle_found = True
            time.sleep(2)
        
        if shuffle_found:
            logger.info(f"Modo aleatorio activado en {device_id}")
        else:
            logger.warning(f"No se pudo activar modo aleatorio en {device_id}")
        
        return shuffle_found
    except Exception as e:
        logger.error(f"Error al activar modo aleatorio: {e}")
        logger.debug(traceback.format_exc())
        return False

def simulate_human_interaction(device, device_id):
    """Simula interacción humana durante la reproducción"""
    try:
        logger.debug(f"Simulando interacción humana en {device_id}")
        
        # Obtener dimensiones de la pantalla
        width, height = get_screen_dimensions(device_id)
        
        # Realizar acciones aleatorias
        actions = [
            # Scroll hacia abajo
            lambda: device.swipe(width/2, height*0.7, width/2, height*0.3),
            # Scroll hacia arriba
            lambda: device.swipe(width/2, height*0.3, width/2, height*0.7),
            # Tap aleatorio en la pantalla
            lambda: device.click(random.randint(width//4, width*3//4), random.randint(height//4, height*3//4)),
            # No hacer nada (solo esperar)
            lambda: None
        ]
        
        # Ejecutar 1-3 acciones aleatorias
        num_actions = random.randint(1, 3)
        for _ in range(num_actions):
            action = random.choice(actions)
            logger.debug(f"Ejecutando acción aleatoria")
            action()
            human_behavior.human_delay(1, 3)
        
        logger.debug(f"Interacción humana simulada en {device_id}")
        return True
    except Exception as e:
        logger.error(f"Error al simular interacción humana: {e}")
        logger.debug(traceback.format_exc())
        return False

def artist_mode():
    """Función principal para el modo de reproducción de artistas"""
    logger.info("Iniciando modo de reproducción de artistas")
    
    # Cargar artistas
    artists = load_artists()
    if not artists:
        logger.error("No hay artistas disponibles para reproducir")
        return False
    
    # Obtener dispositivos conectados
    devices = get_connected_devices()
    if not devices:
        logger.error("No hay dispositivos conectados")
        return False
    
    # Crear orden aleatorio de artistas para cada dispositivo
    device_orders = {device_id: random.sample(artists, len(artists)) for device_id in devices}
    
    # Bucle principal
    try:
        while True:
            logger.info("Iniciando ciclo de reproducción de artistas")
            
            for device_id in devices:
                try:
                    logger.info(f"Procesando dispositivo: {device_id}")
                    
                    # Conectar al dispositivo
                    device = u2.connect_usb(device_id)
                    
                    # Obtener la cola de artistas para este dispositivo
                    artist_queue = device_orders.get(device_id, [])
                    
                    # Si la cola está vacía, recargarla con un nuevo orden aleatorio
                    if not artist_queue:
                        logger.info(f"Recargando cola de artistas para {device_id}")
                        artist_queue = random.sample(artists, len(artists))
                        device_orders[device_id] = artist_queue
                    
                    # Obtener el siguiente artista
                    artist_url = artist_queue.pop()
                    logger.info(f"Artista seleccionado para {device_id}: {artist_url}")
                    
                    # Abrir el artista
                    if open_artist_intent(device_id, artist_url):
                        # Intentar seguir al artista
                        press_follow_if_needed(device, device_id)
                        
                        # Activar modo aleatorio
                        activate_shuffle(device, device_id)
                        
                        # Presionar play
                        press_play(device, device_id)
                        
                        # Determinar tiempo de reproducción aleatorio
                        play_time = random.randint(MIN_PLAY_TIME, MAX_PLAY_TIME)
                        logger.info(f"Reproduciendo artista durante {play_time} segundos")
                        
                        # Durante la reproducción, simular interacción humana ocasionalmente
                        start_time = time.time()
                        while time.time() - start_time < play_time:
                            # Cada ~30 segundos, realizar alguna interacción
                            if random.random() < 0.3:  # 30% de probabilidad
                                simulate_human_interaction(device, device_id)
                            

                            # Esperar un poco
                            time.sleep(10)
                        
                        logger.info(f"Reproducción completada para {device_id}")
                    else:
                        logger.error(f"No se pudo abrir el artista en {device_id}")
                
                except Exception as e:
                    logger.error(f"Error procesando dispositivo {device_id}: {e}")
                    logger.debug(traceback.format_exc())
            
            # Esperar antes del siguiente ciclo
            wait_minutes = random.randint(1, 3)
            logger.info(f"Esperando {wait_minutes} minutos antes del siguiente ciclo")
            time.sleep(wait_minutes * 60)
    
    except KeyboardInterrupt:
        logger.info("Proceso interrumpido por el usuario")
        return False
    except Exception as e:
        logger.error(f"Error en el bucle principal: {e}")
        logger.debug(traceback.format_exc())
        return False

def main():
    """Función principal para ejecutar el módulo de forma independiente"""
    logger.info("Iniciando ArtistPlayer")
    artist_mode()

if __name__ == "__main__":
    main()
