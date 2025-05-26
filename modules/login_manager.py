#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import random
import logging
import json
import cv2
import numpy as np
import traceback
from datetime import datetime
import subprocess
import uiautomator2 as u2
import re

# Importar módulos del sistema
from modules.account_manager import account_manager
from modules.human_behavior import human_behavior
from modules.android_device import AndroidDevice

# Configuración del sistema de logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"login_manager_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.DEBUG,  # Cambiado a DEBUG para logging más detallado
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LoginManager")

# Constantes
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")
SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots")
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Definir las rutas de las imágenes de referencia
TEMPLATE_LOGIN_BUTTON = os.path.join(TEMPLATES_DIR, "login_button.png")
TEMPLATE_CONTINUE_EMAIL = os.path.join(TEMPLATES_DIR, "continue_with_email.png")
TEMPLATE_EMAIL_FIELD = os.path.join(TEMPLATES_DIR, "email_field.png")
TEMPLATE_PASSWORD_FIELD = os.path.join(TEMPLATES_DIR, "password_field.png")
TEMPLATE_LOGIN_SUBMIT = os.path.join(TEMPLATES_DIR, "login_submit.png")
TEMPLATE_HOME_ICON = os.path.join(TEMPLATES_DIR, "home_icon.png")
TEMPLATE_LIBRARY_ICON = os.path.join(TEMPLATES_DIR, "library_icon.png")

# Número máximo de reintentos para operaciones críticas
MAX_RETRIES = 3

class LoginManager:
    def __init__(self):
        """Inicializa el gestor de inicio de sesión"""
        self.devices = {}  # Mapeo de device_id a objetos AndroidDevice
        self.login_history = {}  # Historial de inicios de sesión
        self.session_db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "sessions.json")
        self.sessions = self._load_sessions()
        
        logger.info("LoginManager inicializado")
        logger.debug(f"Ruta de sesiones: {self.session_db_file}")
        logger.debug(f"Ruta de plantillas: {TEMPLATES_DIR}")
        
        # Verificar existencia de plantillas
        self._check_templates()
    
    def _check_templates(self):
        """Verifica que todas las plantillas existan"""
        templates = [
            TEMPLATE_LOGIN_BUTTON,
            TEMPLATE_CONTINUE_EMAIL,
            TEMPLATE_EMAIL_FIELD,
            TEMPLATE_PASSWORD_FIELD,
            TEMPLATE_LOGIN_SUBMIT,
            TEMPLATE_HOME_ICON,
            TEMPLATE_LIBRARY_ICON
        ]
        
        missing_templates = []
        for template in templates:
            if not os.path.exists(template):
                missing_templates.append(os.path.basename(template))
        
        if missing_templates:
            logger.warning(f"Plantillas faltantes: {', '.join(missing_templates)}")
            logger.warning("Algunas funciones de reconocimiento visual pueden fallar")
        else:
            logger.debug("Todas las plantillas están disponibles")
    
    def _load_sessions(self):
        """Carga las sesiones guardadas desde el archivo JSON"""
        try:
            if os.path.exists(self.session_db_file):
                with open(self.session_db_file, 'r') as f:
                    sessions = json.load(f)
                    logger.debug(f"Sesiones cargadas: {len(sessions)} entradas")
                    return sessions
            else:
                logger.warning(f"Archivo de sesiones no encontrado: {self.session_db_file}")
                return {}
        except Exception as e:
            logger.error(f"Error al cargar sesiones: {e}")
            logger.debug(traceback.format_exc())
            return {}
    
    def _save_sessions(self):
        """Guarda las sesiones en el archivo JSON"""
        try:
            os.makedirs(os.path.dirname(self.session_db_file), exist_ok=True)
            with open(self.session_db_file, 'w') as f:
                json.dump(self.sessions, f, indent=4)
            logger.debug(f"Sesiones guardadas: {len(self.sessions)} entradas")
            return True
        except Exception as e:
            logger.error(f"Error al guardar sesiones: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def get_device(self, device_id):
        """Obtiene o crea un objeto AndroidDevice para el dispositivo especificado"""
        try:
            if device_id not in self.devices:
                logger.debug(f"Creando nuevo objeto AndroidDevice para {device_id}")
                self.devices[device_id] = AndroidDevice(device_id)
            
            # Verificar conexión
            if not self.devices[device_id].connected:
                logger.warning(f"Dispositivo {device_id} no conectado, intentando reconectar")
                self.devices[device_id].connect(device_id)
            
            return self.devices[device_id]
        except Exception as e:
            logger.error(f"Error al obtener dispositivo {device_id}: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def capture_screen(self, device_id, filename=None):
        """Captura la pantalla del dispositivo y la convierte en imagen de OpenCV"""
        try:
            device = self.get_device(device_id)
            if not device or not device.connected:
                logger.error(f"Dispositivo {device_id} no conectado")
                return None
            
            # Generar nombre de archivo si no se proporciona
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"login_screenshot_{device_id}_{timestamp}.png"
            
            screenshot_path = os.path.join(SCREENSHOTS_DIR, filename)
            
            # Capturar la pantalla usando uiautomator2
            logger.debug(f"Capturando pantalla en {screenshot_path}")
            device.device.screenshot(screenshot_path)
            
            # Cargar la imagen con OpenCV
            img = cv2.imread(screenshot_path)
            if img is None:
                logger.error(f"No se pudo cargar la imagen capturada: {screenshot_path}")
                return None
            
            logger.debug(f"Captura de pantalla exitosa: {screenshot_path}")
            return img
        except Exception as e:
            logger.error(f"Error capturando pantalla del dispositivo {device_id}: {e}")
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
                
                # Cargar la imagen con OpenCV
                img = cv2.imread(screenshot_path)
                if img is not None:
                    logger.debug(f"Captura alternativa exitosa: {screenshot_path}")
                    return img
            except Exception as e2:
                logger.error(f"Error en método alternativo de captura: {e2}")
                logger.debug(traceback.format_exc())
            
            return None
    
    def find_element(self, image, template_path, threshold=0.7):
        """Encuentra un elemento en la pantalla usando template matching"""
        try:
            # Carga la plantilla
            template = cv2.imread(template_path, cv2.IMREAD_COLOR)
            if template is None:
                logger.error(f"No se pudo cargar la plantilla: {template_path}")
                return None
            
            # Verificar que las imágenes tengan el mismo número de canales
            if image.shape[2] != template.shape[2]:
                logger.error(f"Diferente número de canales: imagen {image.shape[2]}, plantilla {template.shape[2]}")
                return None
            
            # Realiza la coincidencia de plantillas
            logger.debug(f"Buscando coincidencia con plantilla: {os.path.basename(template_path)}")
            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            logger.debug(f"Mejor coincidencia: {max_val:.4f} (umbral: {threshold:.4f})")
            
            if max_val >= threshold:
                # Calcula la posición central del elemento
                w, h = template.shape[1], template.shape[0]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                logger.debug(f"Elemento encontrado en ({center_x}, {center_y}) con confianza {max_val:.4f}")
                return center_x, center_y, max_val
            else:
                logger.debug(f"No se encontró coincidencia por encima del umbral ({threshold})")
                return None
        except Exception as e:
            logger.error(f"Error en la búsqueda de elementos: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def wait_for_element(self, device_id, template_path, max_attempts=10, delay=1, threshold=0.7):
        """Espera a que aparezca un elemento en la pantalla"""
        logger.debug(f"Esperando elemento: {os.path.basename(template_path)}")
        
        for attempt in range(max_attempts):
            logger.debug(f"Intento {attempt + 1}/{max_attempts}")
            
            screen = self.capture_screen(device_id)
            if screen is None:
                logger.warning(f"No se pudo capturar pantalla en intento {attempt + 1}")
                time.sleep(delay)
                continue
            
            element_pos = self.find_element(screen, template_path, threshold)
            if element_pos:
                logger.debug(f"Elemento encontrado en intento {attempt + 1}")
                return element_pos
            
            logger.debug(f"Elemento no encontrado, esperando {delay}s antes del siguiente intento")
            time.sleep(delay)
        
        logger.warning(f"Elemento no encontrado después de {max_attempts} intentos")
        return None
    
    def find_element_by_text(self, device_id, text, exact=False):
        """Encuentra un elemento por su texto usando uiautomator2"""
        try:
            device = self.get_device(device_id)
            if not device or not device.connected:
                logger.error(f"Dispositivo {device_id} no conectado")
                return None
            
            logger.debug(f"Buscando elemento con texto: '{text}'")
            
            if exact:
                element = device.device(text=text)
            else:
                element = device.device(textContains=text)
            
            if element.exists:
                bounds = element.info['bounds']
                center_x = (bounds['left'] + bounds['right']) // 2
                center_y = (bounds['top'] + bounds['bottom']) // 2
                logger.debug(f"Elemento con texto '{text}' encontrado en ({center_x}, {center_y})")
                return center_x, center_y
            else:
                logger.debug(f"Elemento con texto '{text}' no encontrado")
                return None
        except Exception as e:
            logger.error(f"Error al buscar elemento por texto: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def find_element_by_resource_id(self, device_id, resource_id):
        """Encuentra un elemento por su resource-id usando uiautomator2"""
        try:
            device = self.get_device(device_id)
            if not device or not device.connected:
                logger.error(f"Dispositivo {device_id} no conectado")
                return None
            
            logger.debug(f"Buscando elemento con resource-id: '{resource_id}'")
            
            element = device.device(resourceId=resource_id)
            
            if element.exists:
                bounds = element.info['bounds']
                center_x = (bounds['left'] + bounds['right']) // 2
                center_y = (bounds['top'] + bounds['bottom']) // 2
                logger.debug(f"Elemento con resource-id '{resource_id}' encontrado en ({center_x}, {center_y})")
                return center_x, center_y
            else:
                logger.debug(f"Elemento con resource-id '{resource_id}' no encontrado")
                return None
        except Exception as e:
            logger.error(f"Error al buscar elemento por resource-id: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def open_spotify(self, device_id, package_name, retry_count=0):
        """Abre la aplicación de Spotify en el dispositivo"""
        if retry_count >= MAX_RETRIES:
            logger.error(f"Se alcanzó el número máximo de reintentos ({MAX_RETRIES}) para abrir Spotify")
            return False
        
        try:
            device = self.get_device(device_id)
            if not device or not device.connected:
                logger.error(f"Dispositivo {device_id} no conectado")
                return False
            
            # Primero intentamos cerrar la app si ya está abierta
            logger.debug(f"Cerrando {package_name} si está abierto")
            device.stop_app(package_name)
            human_behavior.human_delay(1, 2)
            
            # Ahora abrimos la aplicación
            logger.info(f"Abriendo Spotify ({package_name}) en dispositivo {device_id}")
            
            # Método 1: Usar AndroidDevice.start_app
            success = device.start_app(package_name)
            
            # Si falla, intentar método alternativo con ADB
            if not success:
                logger.warning(f"Método principal falló, intentando abrir con ADB intent")
                try:
                    # Método 2: Usar ADB intent
                    result = subprocess.run(
                        ["adb", "-s", device_id, "shell", "am", "start", "-n", f"{package_name}/com.spotify.music.MainActivity"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    logger.debug(f"Resultado de ADB intent: {result.stdout}")
                    if result.stderr:
                        logger.warning(f"Error en ADB intent: {result.stderr}")
                    
                    success = "Starting" in result.stdout and "Error" not in result.stdout
                except Exception as e:
                    logger.error(f"Error al abrir con ADB intent: {e}")
                    logger.debug(traceback.format_exc())
                    success = False
                
                # Si ambos métodos fallan, intentar con monkey
                if not success:
                    logger.warning("Ambos métodos fallaron, intentando con monkey")
                    try:
                        # Método 3: Usar monkey
                        result = subprocess.run(
                            ["adb", "-s", device_id, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"],
                            capture_output=True,
                            text=True
                        )
                        logger.debug(f"Resultado de monkey: {result.stdout}")
                        if result.stderr:
                            logger.warning(f"Error en monkey: {result.stderr}")
                        
                        success = "Events injected" in result.stdout
                    except Exception as e:
                        logger.error(f"Error al abrir con monkey: {e}")
                        logger.debug(traceback.format_exc())
                        success = False
            
            if not success:
                logger.error(f"No se pudo abrir Spotify ({package_name}) en dispositivo {device_id}")
                # Reintentar después de un retraso
                time.sleep(5)
                return self.open_spotify(device_id, package_name, retry_count + 1)
            
            logger.info(f"Spotify ({package_name}) abierto en dispositivo {device_id}")
            
            # Esperar a que la aplicación se cargue completamente
            logger.debug("Esperando 5 segundos para que la aplicación se inicie completamente")
            time.sleep(5)
            
            # Verificar que la aplicación está en primer plano
            if not self._is_app_in_foreground(device_id, package_name):
                logger.warning(f"Spotify no está en primer plano después de abrirlo")
                # Reintentar
                time.sleep(2)
                return self.open_spotify(device_id, package_name, retry_count + 1)
            
            return True
        except Exception as e:
            logger.error(f"Error al abrir Spotify en {device_id}: {e}")
            logger.debug(traceback.format_exc())
            
            # Reintentar después de un retraso
            time.sleep(5)
            return self.open_spotify(device_id, package_name, retry_count + 1)
    
    def _is_app_in_foreground(self, device_id, package_name):
        """Verifica si la aplicación está en primer plano"""
        try:
            # Usar dumpsys para verificar la actividad en primer plano
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "dumpsys", "activity", "activities"],
                capture_output=True,
                text=True
            )
            
            # Buscar mResumedActivity o mFocusedActivity
            pattern = r'(mResumedActivity|mFocusedActivity).*?({})'.format(package_name)
            match = re.search(pattern, result.stdout)
            
            if match:
                logger.debug(f"Aplicación {package_name} está en primer plano")
                return True
            else:
                logger.debug(f"Aplicación {package_name} NO está en primer plano")
                return False
        except Exception as e:
            logger.error(f"Error al verificar si la app está en primer plano: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def login_to_spotify(self, device_id, email, password, package_name, retry_count=0):
        """Realiza el proceso de login en Spotify para un dispositivo específico"""
        if retry_count >= MAX_RETRIES:
            logger.error(f"Se alcanzó el número máximo de reintentos ({MAX_RETRIES}) para login")
            return False
        
        logger.info(f"Iniciando proceso de login en dispositivo {device_id} con cuenta {email}")
        
        device = self.get_device(device_id)
        if not device or not device.connected:
            logger.error(f"Dispositivo {device_id} no conectado")
            return False
        
        # Verificar si ya existe una sesión guardada para esta cuenta en este dispositivo
        session_key = f"{device_id}_{email}_{package_name}"
        if session_key in self.sessions:
            logger.info(f"Sesión existente encontrada para {email} en {device_id}")
            # Verificar si la sesión sigue siendo válida
            if self._validate_session(device_id, email, package_name):
                logger.info(f"Sesión válida para {email} en {device_id}")
                return True
            else:
                logger.info(f"Sesión inválida para {email} en {device_id}, iniciando nuevo login")
        
        # Paso 1: Abrir Spotify
        if not self.open_spotify(device_id, package_name):
            logger.error(f"No se pudo abrir Spotify en dispositivo {device_id}")
            return False
        
        # Tomar captura de pantalla para diagnóstico
        self.capture_screen(device_id, f"login_start_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        # Paso 2: Buscar y presionar el botón "Log In" usando múltiples métodos
        login_button_found = False
        
        # Método 1: Buscar por plantilla
        logger.debug("Buscando botón 'Log In' por plantilla")
        login_pos = self.wait_for_element(device_id, TEMPLATE_LOGIN_BUTTON, max_attempts=5)
        if login_pos:
            logger.debug(f"Botón 'Log In' encontrado por plantilla en ({login_pos[0]}, {login_pos[1]})")
            device.tap(login_pos[0], login_pos[1])
            login_button_found = True
        
        # Método 2: Buscar por texto
        if not login_button_found:
            logger.debug("Buscando botón 'Log In' por texto")
            for text in ["Log In", "Iniciar sesión", "Login", "Sign In"]:
                login_pos = self.find_element_by_text(device_id, text)
                if login_pos:
                    logger.debug(f"Botón '{text}' encontrado por texto en ({login_pos[0]}, {login_pos[1]})")
                    device.tap(login_pos[0], login_pos[1])
                    login_button_found = True
                    break
        
        # Método 3: Buscar por resource-id
        if not login_button_found:
            logger.debug("Buscando botón 'Log In' por resource-id")
            for resource_id in ["com.spotify.music:id/login_button", "com.spotify.music:id/log_in_button"]:
                login_pos = self.find_element_by_resource_id(device_id, resource_id)
                if login_pos:
                    logger.debug(f"Botón 'Log In' encontrado por resource-id en ({login_pos[0]}, {login_pos[1]})")
                    device.tap(login_pos[0], login_pos[1])
                    login_button_found = True
                    break
        
        if not login_button_found:
            logger.error(f"No se pudo encontrar el botón 'Log In' en dispositivo {device_id}")
            
            # Tomar captura de pantalla para diagnóstico
            self.capture_screen(device_id, f"login_button_not_found_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            # Reintentar desde el principio
            time.sleep(5)
            return self.login_to_spotify(device_id, email, password, package_name, retry_count + 1)
        
        human_behavior.human_delay()
        
        # Paso 3: Esperar y presionar "Continue with Email" usando múltiples métodos
        continue_email_found = False
        
        # Método 1: Buscar por plantilla
        logger.debug("Buscando botón 'Continue with Email' por plantilla")
        continue_email_pos = self.wait_for_element(device_id, TEMPLATE_CONTINUE_EMAIL, max_attempts=5)
        if continue_email_pos:
            logger.debug(f"Botón 'Continue with Email' encontrado por plantilla en ({continue_email_pos[0]}, {continue_email_pos[1]})")
            device.tap(continue_email_pos[0], continue_email_pos[1])
            continue_email_found = True
        
        # Método 2: Buscar por texto
        if not continue_email_found:
            logger.debug("Buscando botón 'Continue with Email' por texto")
            for text in ["Continue with Email", "Continuar con correo", "Email", "Correo electrónico"]:
                continue_email_pos = self.find_element_by_text(device_id, text)
                if continue_email_pos:
                    logger.debug(f"Botón '{text}' encontrado por texto en ({continue_email_pos[0]}, {continue_email_pos[1]})")
                    device.tap(continue_email_pos[0], continue_email_pos[1])
                    continue_email_found = True
                    break
        
        # Método 3: Buscar por resource-id
        if not continue_email_found:
            logger.debug("Buscando botón 'Continue with Email' por resource-id")
            for resource_id in ["com.spotify.music:id/email_button", "com.spotify.music:id/continue_with_email"]:
                continue_email_pos = self.find_element_by_resource_id(device_id, resource_id)
                if continue_email_pos:
                    logger.debug(f"Botón 'Continue with Email' encontrado por resource-id en ({continue_email_pos[0]}, {continue_email_pos[1]})")
                    device.tap(continue_email_pos[0], continue_email_pos[1])
                    continue_email_found = True
                    break
        
        # Si no se encuentra, es posible que ya estemos en la pantalla de login
        if not continue_email_found:
            logger.warning("No se encontró 'Continue with Email', verificando si ya estamos en pantalla de login")
            
            # Tomar captura de pantalla para diagnóstico
            self.capture_screen(device_id, f"continue_email_not_found_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            # Verificar si ya estamos en la pantalla de login buscando campos de email/password
            email_field_found = self.find_element_by_text(device_id, "Email") or self.find_element_by_text(device_id, "Correo")
            password_field_found = self.find_element_by_text(device_id, "Password") or self.find_element_by_text(device_id, "Contraseña")
            
            if not (email_field_found and password_field_found):
                logger.error("No se pudo encontrar 'Continue with Email' ni campos de login")
                # Reintentar desde el principio
                time.sleep(5)
                return self.login_to_spotify(device_id, email, password, package_name, retry_count + 1)
            else:
                logger.info("Ya estamos en la pantalla de login")
        
        human_behavior.human_delay()
        
        # Paso 4: Detectar campo de email, limpiarlo y completarlo usando múltiples métodos
        email_field_found = False
        
        # Método 1: Buscar por plantilla
        logger.debug("Buscando campo de email por plantilla")
        email_field_pos = self.wait_for_element(device_id, TEMPLATE_EMAIL_FIELD, max_attempts=5)
        if email_field_pos:
            logger.debug(f"Campo de email encontrado por plantilla en ({email_field_pos[0]}, {email_field_pos[1]})")
            # Hacer tap para seleccionar el campo
            device.tap(email_field_pos[0], email_field_pos[1])
            email_field_found = True
        
        # Método 2: Buscar por texto
        if not email_field_found:
            logger.debug("Buscando campo de email por texto")
            for text in ["Email", "Correo electrónico", "Username", "Usuario"]:
                email_field_pos = self.find_element_by_text(device_id, text)
                if email_field_pos:
                    logger.debug(f"Campo '{text}' encontrado por texto en ({email_field_pos[0]}, {email_field_pos[1]})")
                    # Ajustar posición para hacer clic en el campo, no en la etiqueta
                    device.tap(email_field_pos[0], email_field_pos[1] + 50)
                    email_field_found = True
                    break
        
        # Método 3: Buscar por resource-id
        if not email_field_found:
            logger.debug("Buscando campo de email por resource-id")
            for resource_id in ["com.spotify.music:id/username", "com.spotify.music:id/email_input"]:
                email_field_pos = self.find_element_by_resource_id(device_id, resource_id)
                if email_field_pos:
                    logger.debug(f"Campo de email encontrado por resource-id en ({email_field_pos[0]}, {email_field_pos[1]})")
                    device.tap(email_field_pos[0], email_field_pos[1])
                    email_field_found = True
                    break
        
        if not email_field_found:
            logger.error(f"No se pudo encontrar el campo de email en dispositivo {device_id}")
            
            # Tomar captura de pantalla para diagnóstico
            self.capture_screen(device_id, f"email_field_not_found_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            # Reintentar desde el principio
            time.sleep(5)
            return self.login_to_spotify(device_id, email, password, package_name, retry_count + 1)
        
        human_behavior.human_delay()
        
        # Limpiar el campo (seleccionar todo y borrar)
        logger.debug("Limpiando campo de email")
        device.press_key("ctrl a")  # Seleccionar todo
        human_behavior.human_delay(0.3, 0.7)
        device.press_key("del")  # Borrar
        human_behavior.human_delay(0.3, 0.7)
        
        # Ingresar el email
        logger.debug(f"Ingresando email: {email}")
        device.input_text(email)
        human_behavior.human_delay()
        
        # Paso 5: Detectar campo de contraseña, limpiarlo y completarlo usando múltiples métodos
        password_field_found = False
        
        # Método 1: Buscar por plantilla
        logger.debug("Buscando campo de contraseña por plantilla")
        password_field_pos = self.wait_for_element(device_id, TEMPLATE_PASSWORD_FIELD, max_attempts=5)
        if password_field_pos:
            logger.debug(f"Campo de contraseña encontrado por plantilla en ({password_field_pos[0]}, {password_field_pos[1]})")
            # Hacer tap para seleccionar el campo
            device.tap(password_field_pos[0], password_field_pos[1])
            password_field_found = True
        
        # Método 2: Buscar por texto
        if not password_field_found:
            logger.debug("Buscando campo de contraseña por texto")
            for text in ["Password", "Contraseña", "Clave"]:
                password_field_pos = self.find_element_by_text(device_id, text)
                if password_field_pos:
                    logger.debug(f"Campo '{text}' encontrado por texto en ({password_field_pos[0]}, {password_field_pos[1]})")
                    # Ajustar posición para hacer clic en el campo, no en la etiqueta
                    device.tap(password_field_pos[0], password_field_pos[1] + 50)
                    password_field_found = True
                    break
        
        # Método 3: Buscar por resource-id
        if not password_field_found:
            logger.debug("Buscando campo de contraseña por resource-id")
            for resource_id in ["com.spotify.music:id/password", "com.spotify.music:id/password_input"]:
                password_field_pos = self.find_element_by_resource_id(device_id, resource_id)
                if password_field_pos:
                    logger.debug(f"Campo de contraseña encontrado por resource-id en ({password_field_pos[0]}, {password_field_pos[1]})")
                    device.tap(password_field_pos[0], password_field_pos[1])
                    password_field_found = True
                    break
        
        if not password_field_found:
            logger.error(f"No se pudo encontrar el campo de contraseña en dispositivo {device_id}")
            
            # Tomar captura de pantalla para diagnóstico
            self.capture_screen(device_id, f"password_field_not_found_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            # Reintentar desde el principio
            time.sleep(5)
            return self.login_to_spotify(device_id, email, password, package_name, retry_count + 1)
        
        human_behavior.human_delay()
        
        # Limpiar el campo
        logger.debug("Limpiando campo de contraseña")
        device.press_key("ctrl a")  # Seleccionar todo
        human_behavior.human_delay(0.3, 0.7)
        device.press_key("del")  # Borrar
        human_behavior.human_delay(0.3, 0.7)
        
        # Ingresar la contraseña
        logger.debug("Ingresando contraseña")
        device.input_text(password)
        human_behavior.human_delay()
        
        # Paso 6: Presionar el botón "Log In" para iniciar sesión usando múltiples métodos
        login_submit_found = False
        
        # Método 1: Buscar por plantilla
        logger.debug("Buscando botón 'Log In' (submit) por plantilla")
        login_submit_pos = self.wait_for_element(device_id, TEMPLATE_LOGIN_SUBMIT, max_attempts=5)
        if login_submit_pos:
            logger.debug(f"Botón 'Log In' (submit) encontrado por plantilla en ({login_submit_pos[0]}, {login_submit_pos[1]})")
            device.tap(login_submit_pos[0], login_submit_pos[1])
            login_submit_found = True
        
        # Método 2: Buscar por texto
        if not login_submit_found:
            logger.debug("Buscando botón 'Log In' (submit) por texto")
            for text in ["Log In", "Iniciar sesión", "Login", "Sign In"]:
                login_submit_pos = self.find_element_by_text(device_id, text)
                if login_submit_pos:
                    logger.debug(f"Botón '{text}' (submit) encontrado por texto en ({login_submit_pos[0]}, {login_submit_pos[1]})")
                    device.tap(login_submit_pos[0], login_submit_pos[1])
                    login_submit_found = True
                    break
        
        # Método 3: Buscar por resource-id
        if not login_submit_found:
            logger.debug("Buscando botón 'Log In' (submit) por resource-id")
            for resource_id in ["com.spotify.music:id/login_button", "com.spotify.music:id/submit"]:
                login_submit_pos = self.find_element_by_resource_id(device_id, resource_id)
                if login_submit_pos:
                    logger.debug(f"Botón 'Log In' (submit) encontrado por resource-id en ({login_submit_pos[0]}, {login_submit_pos[1]})")
                    device.tap(login_submit_pos[0], login_submit_pos[1])
                    login_submit_found = True
                    break
        
        if not login_submit_found:
            logger.error(f"No se pudo encontrar el botón 'Log In' (submit) en dispositivo {device_id}")
            
            # Tomar captura de pantalla para diagnóstico
            self.capture_screen(device_id, f"login_submit_not_found_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            # Intentar presionar Enter como último recurso
            logger.debug("Intentando presionar Enter como último recurso")
            device.press_key("enter")
        
        # Esperar a que se procese el login
        logger.debug("Esperando a que se procese el login (5-10 segundos)")
        human_behavior.human_delay(5, 10)
        
        # Tomar captura de pantalla para diagnóstico
        self.capture_screen(device_id, f"login_result_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        # Verificar si el login fue exitoso
        if self._verify_login_success(device_id):
            logger.info(f"Login exitoso para {email} en dispositivo {device_id}")
            
            # Guardar la sesión
            self.sessions[session_key] = {
                "email": email,
                "device_id": device_id,
                "package_name": package_name,
                "timestamp": datetime.now().isoformat(),
                "status": "active"
            }
            self._save_sessions()
            
            # Registrar el éxito en el account_manager
            try:
                account_manager.report_login_success(email, device_id)
            except Exception as e:
                logger.error(f"Error al reportar login exitoso a account_manager: {e}")
                logger.debug(traceback.format_exc())
            
            # Asignar la cuenta a la aplicación en el dispositivo
            try:
                device.assign_account_to_app(package_name, email)
            except Exception as e:
                logger.error(f"Error al asignar cuenta a la aplicación: {e}")
                logger.debug(traceback.format_exc())
            
            return True
        else:
            logger.error(f"Login fallido para {email} en dispositivo {device_id}")
            
            # Registrar el fallo en el account_manager
            try:
                account_manager.report_login_failure(email, device_id, "login_verification_failed")
            except Exception as e:
                logger.error(f"Error al reportar login fallido a account_manager: {e}")
                logger.debug(traceback.format_exc())
            
            # Reintentar si no hemos alcanzado el límite
            if retry_count < MAX_RETRIES - 1:
                logger.info(f"Reintentando login (intento {retry_count + 2}/{MAX_RETRIES})")
                time.sleep(10)  # Esperar más tiempo antes de reintentar
                return self.login_to_spotify(device_id, email, password, package_name, retry_count + 1)
            
            return False
    
    def _verify_login_success(self, device_id):
        """Verifica si el inicio de sesión fue exitoso usando múltiples métodos"""
        logger.debug("Verificando si el login fue exitoso")
        
        # Esperar un tiempo para que se complete el proceso
        time.sleep(5)
        
        success_indicators = 0
        
        # Método 1: Buscar elementos de la interfaz principal (Home, Library)
        logger.debug("Buscando elementos de la interfaz principal")
        
        # Verificar Home icon
        if os.path.exists(TEMPLATE_HOME_ICON):
            home_icon = self.wait_for_element(device_id, TEMPLATE_HOME_ICON, max_attempts=3)
            if home_icon:
                logger.debug("Icono Home encontrado")
                success_indicators += 1
        
        # Verificar Library icon
        if os.path.exists(TEMPLATE_LIBRARY_ICON):
            library_icon = self.wait_for_element(device_id, TEMPLATE_LIBRARY_ICON, max_attempts=3)
            if library_icon:
                logger.debug("Icono Library encontrado")
                success_indicators += 1
        
        # Método 2: Buscar textos de la interfaz principal
        for text in ["Home", "Search", "Your Library", "Inicio", "Buscar", "Tu biblioteca"]:
            if self.find_element_by_text(device_id, text):
                logger.debug(f"Texto '{text}' encontrado")
                success_indicators += 1
        
        # Método 3: Verificar que NO estamos en la pantalla de login
        login_button = self.find_element_by_text(device_id, "Log In") or self.find_element_by_text(device_id, "Iniciar sesión")
        if not login_button:
            logger.debug("No se encontró botón de login (positivo)")
            success_indicators += 1
        
        # Método 4: Verificar actividad actual con dumpsys
        try:
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "dumpsys", "activity", "activities"],
                capture_output=True,
                text=True
            )
            
            # Buscar actividades que indiquen que estamos en la interfaz principal
            main_activities = [
                "com.spotify.music.MainActivity",
                "com.spotify.music.HomeActivity",
                "com.spotify.music.features.home.HomeActivity"
            ]
            
            for activity in main_activities:
                if activity in result.stdout:
                    logger.debug(f"Actividad principal encontrada: {activity}")
                    success_indicators += 2  # Dar más peso a este indicador
            
            # Verificar que NO estamos en actividades de login
            login_activities = [
                "com.spotify.music.login",
                "com.spotify.music.features.login",
                "LoginActivity"
            ]
            
            login_activity_found = False
            for activity in login_activities:
                if activity in result.stdout:
                    logger.debug(f"Actividad de login encontrada: {activity}")
                    login_activity_found = True
            
            if not login_activity_found:
                logger.debug("No se encontraron actividades de login (positivo)")
                success_indicators += 1
            
        except Exception as e:
            logger.error(f"Error al verificar actividad actual: {e}")
            logger.debug(traceback.format_exc())
        
        # Determinar resultado final
        logger.debug(f"Indicadores de éxito: {success_indicators}")
        return success_indicators >= 3  # Consideramos exitoso si tenemos al menos 3 indicadores
    
    def _validate_session(self, device_id, email, package_name):
        """Valida si una sesión guardada sigue siendo válida"""
        logger.debug(f"Validando sesión para {email} en {device_id}")
        
        # Abrir la aplicación
        if not self.open_spotify(device_id, package_name):
            logger.error(f"No se pudo abrir Spotify para validar sesión en dispositivo {device_id}")
            return False
        
        # Esperar a que cargue
        time.sleep(5)
        
        # Tomar captura de pantalla para diagnóstico
        self.capture_screen(device_id, f"session_validation_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        # Usar el mismo método de verificación que para el login exitoso
        return self._verify_login_success(device_id)
    
    def logout_from_spotify(self, device_id, package_name):
        """Cierra la sesión de Spotify en el dispositivo"""
        try:
            device = self.get_device(device_id)
            if not device or not device.connected:
                logger.error(f"Dispositivo {device_id} no conectado")
                return False
            
            logger.info(f"Cerrando sesión de Spotify ({package_name}) en dispositivo {device_id}")
            
            # Cerrar la aplicación
            logger.debug(f"Deteniendo aplicación {package_name}")
            device.stop_app(package_name)
            time.sleep(2)
            
            # Limpiar los datos de la aplicación para forzar el cierre de sesión
            logger.debug(f"Limpiando datos de la aplicación {package_name}")
            device.clear_app_data(package_name)
            time.sleep(2)
            
            # Actualizar las sesiones guardadas
            updated_count = 0
            for session_key in list(self.sessions.keys()):
                if session_key.startswith(f"{device_id}_") and self.sessions[session_key]["package_name"] == package_name:
                    self.sessions[session_key]["status"] = "closed"
                    updated_count += 1
            
            logger.debug(f"Actualizadas {updated_count} sesiones a estado 'closed'")
            self._save_sessions()
            
            logger.info(f"Logout completado para {package_name} en dispositivo {device_id}")
            return True
        except Exception as e:
            logger.error(f"Error al cerrar sesión en {device_id}: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def process_login_for_device(self, device_id):
        """Procesa el inicio de sesión para un dispositivo específico"""
        try:
            logger.info(f"Procesando login para dispositivo {device_id}")
            
            # Obtener una cuenta para este dispositivo
            try:
                email, password = account_manager.get_account_for_device(device_id)
                if not email or not password:
                    logger.error(f"No se pudo obtener una cuenta para el dispositivo {device_id}")
                    return False
                logger.info(f"Cuenta obtenida para dispositivo {device_id}: {email}")
            except Exception as e:
                logger.error(f"Error al obtener cuenta para dispositivo {device_id}: {e}")
                logger.debug(traceback.format_exc())
                return False
            
            # Obtener un proxy para esta cuenta
            try:
                proxy = account_manager.get_proxy_for_account(email, device_id)
                if not proxy:
                    logger.warning(f"No se pudo obtener un proxy para la cuenta {email}")
                else:
                    logger.info(f"Proxy obtenido para cuenta {email}: {proxy}")
            except Exception as e:
                logger.error(f"Error al obtener proxy para cuenta {email}: {e}")
                logger.debug(traceback.format_exc())
                proxy = None
            
            # Obtener o registrar aplicaciones Spotify en el dispositivo
            device = self.get_device(device_id)
            if not device or not device.connected:
                logger.error(f"No se pudo obtener dispositivo {device_id}")
                return False
            
            try:
                apps = device.get_registered_spotify_apps()
                logger.debug(f"Aplicaciones Spotify registradas: {apps}")
                
                if not apps:
                    logger.warning(f"No hay aplicaciones Spotify registradas en el dispositivo {device_id}")
                    # Registrar la aplicación Spotify original
                    logger.info("Registrando aplicación Spotify original")
                    device.register_spotify_app("com.spotify.music", "Spotify Original")
                    apps = device.get_registered_spotify_apps()
                    if not apps:
                        logger.error("No se pudo registrar la aplicación Spotify")
                        return False
            except Exception as e:
                logger.error(f"Error al obtener aplicaciones Spotify: {e}")
                logger.debug(traceback.format_exc())
                return False
            
            # Seleccionar una aplicación para esta cuenta
            try:
                app = device.get_app_for_account(email)
                if not app:
                    # Si no hay una aplicación asignada, seleccionar una aleatoria
                    app_info = random.choice(apps)
                    app = app_info["package"]
                    logger.info(f"Seleccionada aplicación aleatoria para cuenta {email}: {app}")
                else:
                    logger.info(f"Aplicación ya asignada para cuenta {email}: {app}")
            except Exception as e:
                logger.error(f"Error al seleccionar aplicación para cuenta {email}: {e}")
                logger.debug(traceback.format_exc())
                # Usar la aplicación original como fallback
                app = "com.spotify.music"
                logger.info(f"Usando aplicación original como fallback: {app}")
            
            # Configurar el proxy si está disponible
            if proxy:
                try:
                    from scripts.set_proxy import configure_proxy_for_device
                    if not configure_proxy_for_device(device_id, proxy):
                        logger.warning(f"No se pudo configurar el proxy {proxy} en el dispositivo {device_id}")
                except Exception as e:
                    logger.error(f"Error al configurar proxy: {e}")
                    logger.debug(traceback.format_exc())
            
            # Realizar el inicio de sesión
            success = self.login_to_spotify(device_id, email, password, app)
            
            if success:
                logger.info(f"Login exitoso para {email} en dispositivo {device_id}")
            else:
                logger.error(f"Login fallido para {email} en dispositivo {device_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error procesando login para dispositivo {device_id}: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def process_all_devices(self):
        """Procesa el inicio de sesión para todos los dispositivos conectados"""
        try:
            devices = AndroidDevice.get_connected_devices()
            if not devices:
                logger.error("No hay dispositivos conectados")
                return False
            
            logger.info(f"Procesando login para {len(devices)} dispositivos: {devices}")
            
            success_count = 0
            for device_id in devices:
                logger.info(f"Procesando dispositivo {device_id}")
                if self.process_login_for_device(device_id):
                    success_count += 1
            
            logger.info(f"Proceso completado. {success_count}/{len(devices)} dispositivos con login exitoso")
            return success_count > 0
        except Exception as e:
            logger.error(f"Error en process_all_devices: {e}")
            logger.debug(traceback.format_exc())
            return False

# Instancia global para uso en otros módulos
login_manager = LoginManager()

def configure_proxy_for_device(device_id, proxy_string):
    """Configura un proxy en un dispositivo usando SocksDroid"""
    try:
        from scripts.set_proxy import set_proxy
        return set_proxy(device_id, proxy_string)
    except Exception as e:
        logger.error(f"Error al configurar proxy: {e}")
        logger.debug(traceback.format_exc())
        return False

def main():
    """Función principal para ejecutar el módulo de forma independiente"""
    logger.info("Iniciando LoginManager")
    
    # Procesar todos los dispositivos conectados
    login_manager.process_all_devices()

if __name__ == "__main__":
    main()
