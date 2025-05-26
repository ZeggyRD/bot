#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import threading
import random
import cv2
import numpy as np
from PIL import Image
import io
import re
import logging
from datetime import datetime

# Configuración del sistema de logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"spotify_login_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SpotifyLogin")

# Ruta al archivo de cuentas
ACCOUNTS_FILE = r"C:\Users\ceram\Music\OTW_MUSIC_SYSTEM\scripts\accounts.txt"

# Constantes para la interacción con la UI
SPOTIFY_PACKAGE = "com.spotify.music"
MAX_RETRIES = 5
RETRY_DELAY = 2  # segundos
HUMAN_DELAY_MIN = 0.8  # segundos
HUMAN_DELAY_MAX = 2.0  # segundos

# Templates para reconocimiento de imagen
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Definir las rutas de las imágenes de referencia
TEMPLATE_LOGIN_BUTTON = os.path.join(TEMPLATES_DIR, "login_button.png")
TEMPLATE_CONTINUE_EMAIL = os.path.join(TEMPLATES_DIR, "continue_with_email.png")
TEMPLATE_EMAIL_FIELD = os.path.join(TEMPLATES_DIR, "email_field.png")
TEMPLATE_PASSWORD_FIELD = os.path.join(TEMPLATES_DIR, "password_field.png")
TEMPLATE_LOGIN_SUBMIT = os.path.join(TEMPLATES_DIR, "login_submit.png")

def human_delay():
    """Simula un retraso humano aleatorio"""
    delay = random.uniform(HUMAN_DELAY_MIN, HUMAN_DELAY_MAX)
    time.sleep(delay)

def get_connected_devices():
    """Obtiene la lista de dispositivos Android conectados por USB"""
    try:
        result = subprocess.run(
            ["adb", "devices"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        devices = []
        for line in result.stdout.strip().split('\n')[1:]:
            if line and not line.startswith('*') and 'device' in line:
                device_id = line.split()[0]
                devices.append(device_id)
        
        logger.info(f"Dispositivos detectados: {devices}")
        return devices
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al obtener dispositivos conectados: {e}")
        return []

def read_accounts():
    """Lee las cuentas desde el archivo accounts.txt"""
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            content = f.read().strip()
            # Separar por espacios o saltos de línea
            accounts = re.split(r'\s+', content)
            
            # Filtrar entradas vacías y validar formato correo:contraseña
            valid_accounts = []
            for acc in accounts:
                if ':' in acc:
                    email, password = acc.split(':', 1)
                    if email and password:
                        valid_accounts.append((email, password))
            
            logger.info(f"Se leyeron {len(valid_accounts)} cuentas válidas")
            return valid_accounts
    except Exception as e:
        logger.error(f"Error al leer el archivo de cuentas: {e}")
        return []

def capture_screen(device_id):
    """Captura la pantalla del dispositivo y la convierte en imagen de OpenCV"""
    try:
        # Captura la pantalla usando ADB
        screen_bytes = subprocess.run(
            ["adb", "-s", device_id, "exec-out", "screencap -p"],
            capture_output=True,
            check=True
        ).stdout
        
        # Convierte la imagen a formato OpenCV
        img_array = np.frombuffer(screen_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        logger.error(f"Error capturando pantalla del dispositivo {device_id}: {e}")
        return None

def find_element(image, template_path, threshold=0.7):
    """Encuentra un elemento en la pantalla usando template matching"""
    try:
        # Carga la plantilla
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            logger.error(f"No se pudo cargar la plantilla: {template_path}")
            return None
        
        # Realiza la coincidencia de plantillas
        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            # Calcula la posición central del elemento
            w, h = template.shape[1], template.shape[0]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return center_x, center_y, max_val
        else:
            return None
    except Exception as e:
        logger.error(f"Error en la búsqueda de elementos: {e}")
        return None

def tap_element(device_id, position, jitter=10):
    """Toca un elemento en la pantalla con un ligero jitter para simular un toque humano"""
    try:
        x, y = position
        
        # Añade un pequeño jitter para hacer que el toque parezca más humano
        jitter_x = random.randint(-jitter, jitter)
        jitter_y = random.randint(-jitter, jitter)
        
        x += jitter_x
        y += jitter_y
        
        subprocess.run(
            ["adb", "-s", device_id, "shell", f"input tap {x} {y}"],
            check=True
        )
        logger.info(f"Tocando elemento en ({x}, {y}) en dispositivo {device_id}")
        return True
    except Exception as e:
        logger.error(f"Error al tocar elemento en {device_id}: {e}")
        return False

def clear_text_field(device_id):
    """Borra el contenido de un campo de texto seleccionado"""
    try:
        # Seleccionar todo el texto (CTRL+A)
        subprocess.run(
            ["adb", "-s", device_id, "shell", "input keyevent KEYCODE_CTRL_LEFT KEYCODE_A"],
            check=True
        )
        human_delay()
        
        # Borrar el texto seleccionado
        subprocess.run(
            ["adb", "-s", device_id, "shell", "input keyevent KEYCODE_DEL"],
            check=True
        )
        logger.info(f"Campo de texto borrado en dispositivo {device_id}")
        return True
    except Exception as e:
        logger.error(f"Error al borrar texto en {device_id}: {e}")
        
        # Método alternativo: intentar borrar con múltiples pulsaciones de borrado
        try:
            for _ in range(30):  # Intentar borrar hasta 30 caracteres
                subprocess.run(
                    ["adb", "-s", device_id, "shell", "input keyevent KEYCODE_DEL"],
                    check=True
                )
            logger.info(f"Campo de texto borrado usando método alternativo en dispositivo {device_id}")
            return True
        except Exception as e2:
            logger.error(f"Error al borrar texto usando método alternativo en {device_id}: {e2}")
            return False

def input_text(device_id, text):
    """Introduce texto en un campo de entrada"""
    try:
        # Escapar caracteres especiales
        text = text.replace(' ', '%s').replace('"', '\\"').replace("'", "\\'")
        
        subprocess.run(
            ["adb", "-s", device_id, "shell", f"input text '{text}'"],
            check=True
        )
        logger.info(f"Texto ingresado en dispositivo {device_id}")
        return True
    except Exception as e:
        logger.error(f"Error al introducir texto en {device_id}: {e}")
        return False

def open_spotify(device_id):
    """Abre la aplicación de Spotify en el dispositivo"""
    try:
        # Primero intentamos cerrar la app si ya está abierta
        try:
            subprocess.run(
                ["adb", "-s", device_id, "shell", f"am force-stop {SPOTIFY_PACKAGE}"],
                check=True
            )
            logger.info(f"Cerrando Spotify en dispositivo {device_id} (si estaba abierto)")
            time.sleep(1)  # Pequeña pausa para asegurar que se cierre correctamente
        except Exception as e:
            logger.warning(f"No se pudo cerrar Spotify en {device_id}: {e}")
        
        # Ahora abrimos la aplicación
        subprocess.run(
            ["adb", "-s", device_id, "shell", f"am start -n {SPOTIFY_PACKAGE}/.MainActivity"],
            check=True
        )
        logger.info(f"Spotify abierto en dispositivo {device_id}")
        
        # Esperar a que la aplicación se cargue completamente
        time.sleep(5)  # Esperar 5 segundos para que la app se inicie
        
        return True
    except Exception as e:
        logger.error(f"Error al abrir Spotify en {device_id}: {e}")
        return False

def wait_for_element(device_id, template_path, max_attempts=10, delay=1, threshold=0.7):
    """Espera a que aparezca un elemento en la pantalla"""
    for attempt in range(max_attempts):
        screen = capture_screen(device_id)
        if screen is None:
            time.sleep(delay)
            continue
            
        element_pos = find_element(screen, template_path, threshold)
        if element_pos:
            return element_pos
        
        time.sleep(delay)
    
    return None

def login_to_spotify(device_id, email, password):
    """Realiza el proceso de login en Spotify para un dispositivo específico"""
    logger.info(f"Iniciando proceso de login en dispositivo {device_id} con cuenta {email}")
    
    # Paso 1: Abrir Spotify
    if not open_spotify(device_id):
        logger.error(f"No se pudo abrir Spotify en dispositivo {device_id}")
        return False
    
    # Paso 2: Buscar y presionar el botón "Log In"
    for attempt in range(MAX_RETRIES):
        screen = capture_screen(device_id)
        if screen is None:
            time.sleep(RETRY_DELAY)
            continue
            
        # Buscar el botón de login
        login_pos = find_element(screen, TEMPLATE_LOGIN_BUTTON)
        if login_pos:
            logger.info(f"Botón 'Log In' encontrado en dispositivo {device_id}")
            tap_element(device_id, login_pos[:2])
            human_delay()
            break
        else:
            logger.warning(f"Botón 'Log In' no encontrado en dispositivo {device_id}. Intento {attempt+1}/{MAX_RETRIES}")
            time.sleep(RETRY_DELAY)
    else:
        logger.error(f"No se pudo encontrar el botón 'Log In' en dispositivo {device_id}")
        return False
    
    # Paso 3 y 4: Esperar a que cargue y presionar "Continue with Email"
    for attempt in range(MAX_RETRIES):
        screen = capture_screen(device_id)
        if screen is None:
            time.sleep(RETRY_DELAY)
            continue
            
        # Buscar el botón de continuar con email
        continue_email_pos = find_element(screen, TEMPLATE_CONTINUE_EMAIL)
        if continue_email_pos:
            logger.info(f"Botón 'Continue with Email' encontrado en dispositivo {device_id}")
            tap_element(device_id, continue_email_pos[:2])
            human_delay()
            break
        else:
            logger.warning(f"Botón 'Continue with Email' no encontrado en dispositivo {device_id}. Intento {attempt+1}/{MAX_RETRIES}")
            time.sleep(RETRY_DELAY)
    else:
        logger.error(f"No se pudo encontrar el botón 'Continue with Email' en dispositivo {device_id}")
        return False
    
    # Paso 5 y 6: Detectar campo de email, limpiarlo y completarlo
    for attempt in range(MAX_RETRIES):
        screen = capture_screen(device_id)
        if screen is None:
            time.sleep(RETRY_DELAY)
            continue
            
        # Buscar el campo de email
        email_field_pos = find_element(screen, TEMPLATE_EMAIL_FIELD)
        if email_field_pos:
            logger.info(f"Campo de email encontrado en dispositivo {device_id}")
            
            # Hacer doble tap para seleccionar todo el texto existente
            tap_element(device_id, email_field_pos[:2])
            human_delay()
            
            # Limpiar el campo
            clear_text_field(device_id)
            human_delay()
            
            # Ingresar el nuevo email
            input_text(device_id, email)
            human_delay()
            break
        else:
            logger.warning(f"Campo de email no encontrado en dispositivo {device_id}. Intento {attempt+1}/{MAX_RETRIES}")
            time.sleep(RETRY_DELAY)
    else:
        logger.error(f"No se pudo encontrar el campo de email en dispositivo {device_id}")
        return False
    
    # Paso 7 y 8: Detectar campo de contraseña, limpiarlo y completarlo
    for attempt in range(MAX_RETRIES):
        screen = capture_screen(device_id)
        if screen is None:
            time.sleep(RETRY_DELAY)
            continue
            
        # Buscar el campo de contraseña
        password_field_pos = find_element(screen, TEMPLATE_PASSWORD_FIELD)
        if password_field_pos:
            logger.info(f"Campo de contraseña encontrado en dispositivo {device_id}")
            
            # Hacer tap para seleccionar el campo
            tap_element(device_id, password_field_pos[:2])
            human_delay()
            
            # Limpiar el campo
            clear_text_field(device_id)
            human_delay()
            
            # Ingresar la nueva contraseña
            input_text(device_id, password)
            human_delay()
            break
        else:
            logger.warning(f"Campo de contraseña no encontrado en dispositivo {device_id}. Intento {attempt+1}/{MAX_RETRIES}")
            time.sleep(RETRY_DELAY)
    else:
        logger.error(f"No se pudo encontrar el campo de contraseña en dispositivo {device_id}")
        return False
    
    # Paso 9: Presionar el botón "Log In" para iniciar sesión
    for attempt in range(MAX_RETRIES):
        screen = capture_screen(device_id)
        if screen is None:
            time.sleep(RETRY_DELAY)
            continue
            
        # Buscar el botón de login final
        login_submit_pos = find_element(screen, TEMPLATE_LOGIN_SUBMIT)
        if login_submit_pos:
            logger.info(f"Botón 'Log In' (submit) encontrado en dispositivo {device_id}")
            tap_element(device_id, login_submit_pos[:2])
            human_delay()
            logger.info(f"Proceso de login completado en dispositivo {device_id}")
            return True
        else:
            logger.warning(f"Botón 'Log In' (submit) no encontrado en dispositivo {device_id}. Intento {attempt+1}/{MAX_RETRIES}")
            time.sleep(RETRY_DELAY)
    
    logger.error(f"No se pudo completar el proceso de login en dispositivo {device_id}")
    return False

def process_device(device_id, email, password):
    """Procesa un dispositivo específico para iniciar sesión"""
    try:
        success = login_to_spotify(device_id, email, password)
        return device_id, success
    except Exception as e:
        logger.error(f"Error procesando dispositivo {device_id}: {e}")
        return device_id, False

def save_template_images(device_id):
    """Función para capturar y guardar imágenes de plantilla desde un dispositivo"""
    try:
        # Esta función es útil para generar las plantillas iniciales
        # Capture la pantalla y guarde las secciones relevantes como plantillas
        
        logger.info(f"Iniciando captura de plantillas en dispositivo {device_id}")
        
        # Abrir Spotify
        open_spotify(device_id)
        time.sleep(5)
        
        # Capturar pantalla inicial
        screen = capture_screen(device_id)
        if screen is not None:
            cv2.imwrite(TEMPLATE_LOGIN_BUTTON, screen)  # Guarda la pantalla completa primero
            logger.info(f"Plantilla guardada en {TEMPLATE_LOGIN_BUTTON}")
            
            # Puedes recortar las áreas relevantes manualmente después
        
        logger.info("Proceso de captura de plantillas completo. Por favor, recorte manualmente las áreas relevantes.")
        return True
    except Exception as e:
        logger.error(f"Error al capturar plantillas: {e}")
        return False

def main():
    """Función principal que coordina el proceso de login en múltiples dispositivos"""
    logger.info("Iniciando proceso de login en múltiples dispositivos")
    
    # Obtener dispositivos conectados
    devices = get_connected_devices()
    if not devices:
        logger.error("No se encontraron dispositivos Android conectados")
        return
    
    logger.info(f"Dispositivos conectados: {len(devices)}")
    
    # Leer las cuentas
    accounts = read_accounts()
    if not accounts:
        logger.error("No se encontraron cuentas válidas en el archivo")
        return
    
    # Verificar si existen las plantillas
    templates_missing = not all(os.path.exists(t) for t in [
        TEMPLATE_LOGIN_BUTTON,
        TEMPLATE_CONTINUE_EMAIL,
        TEMPLATE_EMAIL_FIELD,
        TEMPLATE_PASSWORD_FIELD,
        TEMPLATE_LOGIN_SUBMIT
    ])
    
    if templates_missing:
        logger.warning("Faltan algunas plantillas para el reconocimiento visual.")
        logger.warning("Asegúrese de que las imágenes de plantilla estén en la carpeta 'templates'.")
        
        # Opcionalmente, podría capturar plantillas aquí si no existen
        # save_template_images(devices[0])
    
    # Verificar que tengamos suficientes cuentas
    if len(accounts) < len(devices):
        logger.warning(f"Hay más dispositivos ({len(devices)}) que cuentas disponibles ({len(accounts)})")
    
    # Asignar cuentas a dispositivos
    device_accounts = []
    for i, device_id in enumerate(devices):
        if i < len(accounts):
            email, password = accounts[i]
            device_accounts.append((device_id, email, password))
        else:
            logger.warning(f"Dispositivo {device_id} no tiene cuenta asignada")
    
    # Crear hilos para procesar dispositivos en paralelo
    threads = []
    results = []
    
    for device_id, email, password in device_accounts:
        thread = threading.Thread(
            target=lambda d, e, p, r: r.append(process_device(d, e, p)),
            args=(device_id, email, password, results)
        )
        threads.append(thread)
        thread.start()
    
    # Esperar a que todos los hilos terminen
    for thread in threads:
        thread.join()
    
    # Contar éxitos y fallos
    successes = sum(1 for _, success in results if success)
    failures = len(results) - successes
    
    logger.info(f"Proceso completado: {successes} dispositivos con login exitoso, {failures} fallos")

if __name__ == "__main__":
    main()