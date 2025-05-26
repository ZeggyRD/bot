#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import random
import string
import requests
import logging
import json
import re
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException

# Configuración del sistema de logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"account_creator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.DEBUG,  # Cambiado a DEBUG para logging más detallado
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AccountCreator")

# Constantes
INSTADDR_API_KEY = ""  # Se debe configurar en config.json
SPOTIFY_SIGNUP_URL = "https://www.spotify.com/signup"
ACCOUNTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "spotify_accounts.txt")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "config.json")
MAX_RETRIES = 3  # Número máximo de reintentos para operaciones críticas

# Simulación de comportamiento humano
HUMAN_DELAY_MIN = 0.8  # segundos
HUMAN_DELAY_MAX = 2.5  # segundos

def load_config():
    """Carga la configuración desde el archivo config.json"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                logger.debug(f"Configuración cargada correctamente desde {CONFIG_FILE}")
                return config
        else:
            logger.warning(f"Archivo de configuración no encontrado: {CONFIG_FILE}")
            # Crear archivo de configuración con valores predeterminados
            default_config = {
                "INSTADDR_API_KEY": "",
                "WEBSHARE_API_KEY": ""
            }
            save_config(default_config)
            return default_config
    except Exception as e:
        logger.error(f"Error al cargar la configuración: {e}")
        logger.debug(traceback.format_exc())
        return {}

def save_config(config):
    """Guarda la configuración en el archivo config.json"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        logger.info(f"Configuración guardada en: {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar la configuración: {e}")
        logger.debug(traceback.format_exc())
        return False

def human_delay(min_sec=None, max_sec=None):
    """Simula un retraso humano aleatorio"""
    if min_sec is None:
        min_sec = HUMAN_DELAY_MIN
    if max_sec is None:
        max_sec = HUMAN_DELAY_MAX
    
    delay = random.uniform(min_sec, max_sec)
    logger.debug(f"Esperando {delay:.2f} segundos (simulación humana)")
    time.sleep(delay)
    return delay

def generate_random_password(length=12):
    """Genera una contraseña aleatoria segura"""
    # Asegurar que la contraseña tenga al menos una letra mayúscula, una minúscula, un número y un carácter especial
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*"
    
    # Garantizar al menos uno de cada tipo
    pwd = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special)
    ]
    
    # Completar el resto de la contraseña
    remaining_length = length - len(pwd)
    all_chars = lowercase + uppercase + digits + special
    pwd.extend(random.choice(all_chars) for _ in range(remaining_length))
    
    # Mezclar la contraseña
    random.shuffle(pwd)
    password = ''.join(pwd)
    
    logger.debug(f"Contraseña generada (longitud: {length})")
    return password

def generate_random_name():
    """Genera un nombre aleatorio para el perfil"""
    first_names = [
        "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", 
        "Quinn", "Skyler", "Dakota", "Jamie", "Reese", "Finley", "Rowan",
        "Emerson", "Sage", "Blair", "Parker", "Hayden", "Harley"
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", 
        "Garcia", "Rodriguez", "Wilson", "Martinez", "Anderson", "Taylor",
        "Thomas", "Hernandez", "Moore", "Martin", "Jackson", "Thompson", "White"
    ]
    
    first = random.choice(first_names)
    last = random.choice(last_names)
    
    full_name = f"{first} {last}"
    logger.debug(f"Nombre aleatorio generado: {full_name}")
    return full_name

def get_temp_email_instaddr(retry_count=0):
    """Obtiene un correo temporal usando la API de InstAddr"""
    if retry_count >= MAX_RETRIES:
        logger.error(f"Se alcanzó el número máximo de reintentos ({MAX_RETRIES}) para obtener correo temporal")
        return None, None
    
    config = load_config()
    api_key = config.get("INSTADDR_API_KEY", INSTADDR_API_KEY)
    
    if not api_key:
        logger.error("API Key de InstAddr no configurada. Configure la API Key en config.json")
        return None, None
    
    try:
        logger.info("Solicitando correo temporal a InstAddr API")
        logger.debug(f"URL: https://api.internal.temp-mail.io/api/v3/email/new")
        
        response = requests.post(
            "https://api.internal.temp-mail.io/api/v3/email/new",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30  # Añadir timeout para evitar bloqueos indefinidos
        )
        
        logger.debug(f"Respuesta de InstAddr API: Status {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            email = data.get("email")
            token = data.get("token")
            logger.info(f"Correo temporal generado: {email}")
            return email, token
        elif response.status_code == 401:
            logger.error("API Key de InstAddr inválida o expirada")
            return None, None
        else:
            logger.error(f"Error al obtener correo temporal: {response.status_code} - {response.text}")
            # Reintentar después de un retraso
            wait_time = (retry_count + 1) * 5  # Espera incremental: 5s, 10s, 15s
            logger.info(f"Reintentando en {wait_time} segundos...")
            time.sleep(wait_time)
            return get_temp_email_instaddr(retry_count + 1)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión con la API de InstAddr: {e}")
        logger.debug(traceback.format_exc())
        # Reintentar después de un retraso
        wait_time = (retry_count + 1) * 5
        logger.info(f"Reintentando en {wait_time} segundos...")
        time.sleep(wait_time)
        return get_temp_email_instaddr(retry_count + 1)
    except Exception as e:
        logger.error(f"Error inesperado en la API de InstAddr: {e}")
        logger.debug(traceback.format_exc())
        return None, None

def check_email_instaddr(token, timeout=300, check_interval=10, retry_count=0):
    """Verifica los correos recibidos en el correo temporal de InstAddr"""
    if retry_count >= MAX_RETRIES:
        logger.error(f"Se alcanzó el número máximo de reintentos ({MAX_RETRIES}) para verificar correos")
        return None
    
    config = load_config()
    api_key = config.get("INSTADDR_API_KEY", INSTADDR_API_KEY)
    
    if not api_key or not token:
        logger.error("API Key de InstAddr o token no configurados")
        return None
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            logger.debug(f"Verificando correos recibidos (token: {token[:5]}...)")
            
            response = requests.get(
                f"https://api.internal.temp-mail.io/api/v3/email/{token}/messages",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30  # Añadir timeout para evitar bloqueos indefinidos
            )
            
            logger.debug(f"Respuesta de verificación de correos: Status {response.status_code}")
            
            if response.status_code == 200:
                messages = response.json()
                logger.debug(f"Se encontraron {len(messages)} mensajes")
                
                for message in messages:
                    subject = message.get("subject", "").lower()
                    body = message.get("body_text", "").lower() if message.get("body_text") else ""
                    body_html = message.get("body_html", "").lower() if message.get("body_html") else ""
                    
                    logger.debug(f"Analizando mensaje: {subject}")
                    
                    if "spotify" in subject and ("verification" in subject or "confirm" in subject or "verify" in subject):
                        logger.info("Correo de verificación de Spotify encontrado")
                        
                        # Buscar el enlace de verificación en texto plano y HTML
                        verification_link = None
                        
                        # Buscar en cuerpo de texto
                        if body:
                            urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', body)
                            for url in urls:
                                if "spotify" in url and ("confirm" in url or "verify" in url):
                                    verification_link = url
                                    break
                        
                        # Si no se encontró en texto plano, buscar en HTML
                        if not verification_link and body_html:
                            urls = re.findall(r'href=[\'"]?([^\'" >]+)', body_html)
                            for url in urls:
                                if "spotify" in url and ("confirm" in url or "verify" in url):
                                    verification_link = url
                                    break
                        
                        if verification_link:
                            logger.info(f"Enlace de verificación encontrado: {verification_link}")
                            return verification_link
                        else:
                            logger.warning("Correo de verificación encontrado pero no se pudo extraer el enlace")
            
            elapsed = int(time.time() - start_time)
            remaining = timeout - elapsed
            logger.info(f"Esperando correo de verificación... ({elapsed}s transcurridos, {remaining}s restantes)")
            time.sleep(check_interval)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión al verificar correos: {e}")
            logger.debug(traceback.format_exc())
            # Breve pausa antes de reintentar
            time.sleep(check_interval)
        except Exception as e:
            logger.error(f"Error inesperado al verificar correos: {e}")
            logger.debug(traceback.format_exc())
            # Reintentar con un nuevo intento
            return check_email_instaddr(token, timeout, check_interval, retry_count + 1)
    
    logger.error(f"Tiempo de espera agotado ({timeout}s). No se recibió correo de verificación.")
    return None

def handle_captcha(driver):
    """Intenta manejar CAPTCHAs si aparecen durante el registro"""
    try:
        # Verificar si hay un iframe de reCAPTCHA
        captcha_frames = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
        if captcha_frames:
            logger.warning("Se detectó un CAPTCHA. Esperando resolución manual...")
            
            # Si estamos en modo headless, no podemos resolver el CAPTCHA manualmente
            if "--headless" in driver.execute_script("return navigator.userAgent"):
                logger.error("No se puede resolver CAPTCHA en modo headless")
                return False
            
            # Esperar hasta 2 minutos para resolución manual
            for i in range(120):
                # Verificar si el CAPTCHA ya no está presente o si se ha avanzado a la siguiente página
                if not driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]"):
                    logger.info("CAPTCHA resuelto o ya no está presente")
                    return True
                
                time.sleep(1)
                if i % 10 == 0:  # Cada 10 segundos
                    logger.info(f"Esperando resolución manual del CAPTCHA... ({i}s)")
            
            logger.error("Tiempo de espera agotado para resolución de CAPTCHA")
            return False
        
        return True  # No hay CAPTCHA
    except Exception as e:
        logger.error(f"Error al manejar CAPTCHA: {e}")
        logger.debug(traceback.format_exc())
        return False

def create_spotify_account(headless=True, proxy=None, retry_count=0):
    """Crea una cuenta de Spotify usando un correo temporal"""
    if retry_count >= MAX_RETRIES:
        logger.error(f"Se alcanzó el número máximo de reintentos ({MAX_RETRIES}) para crear cuenta")
        return False
    
    logger.info(f"Iniciando creación de cuenta de Spotify (intento {retry_count + 1}/{MAX_RETRIES + 1})")
    
    # Obtener correo temporal
    email, token = get_temp_email_instaddr()
    if not email or not token:
        logger.error("No se pudo obtener un correo temporal")
        # Reintentar con un nuevo intento
        time.sleep(5)
        return create_spotify_account(headless, proxy, retry_count + 1)
    
    # Generar contraseña y nombre aleatorios
    password = generate_random_password()
    display_name = generate_random_name()
    birth_day = random.randint(1, 28)
    birth_month = random.randint(1, 12)
    birth_year = random.randint(1980, 2000)
    
    # Configurar el navegador
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")  # Nueva sintaxis para Chrome moderno
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Configurar proxy si se proporciona
    if proxy:
        logger.info(f"Configurando proxy: {proxy}")
        chrome_options.add_argument(f'--proxy-server={proxy}')
    
    driver = None
    try:
        logger.info("Iniciando navegador Chrome")
        # Usar webdriver_manager para gestionar el driver automáticamente
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(60)  # Establecer timeout de carga de página
        
        logger.info(f"Navegando a {SPOTIFY_SIGNUP_URL}")
        driver.get(SPOTIFY_SIGNUP_URL)
        
        # Esperar a que cargue la página
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            logger.info("Página de registro cargada correctamente")
        except TimeoutException:
            logger.error("Timeout esperando a que cargue la página de registro")
            # Tomar captura de pantalla para diagnóstico
            screenshot_path = os.path.join(log_dir, f"signup_timeout_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            driver.save_screenshot(screenshot_path)
            logger.info(f"Captura de pantalla guardada en: {screenshot_path}")
            
            # Reintentar con un nuevo intento
            return create_spotify_account(headless, proxy, retry_count + 1)
        
        human_delay(1, 3)
        
        # Manejar CAPTCHA si aparece
        if not handle_captcha(driver):
            logger.warning("No se pudo manejar el CAPTCHA, continuando de todos modos")
        
        # Completar formulario
        logger.info(f"Completando formulario con email: {email}")
        
        # Email
        try:
            email_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "email"))
            )
            email_field.clear()
            for char in email:  # Escribir carácter por carácter para simular comportamiento humano
                email_field.send_keys(char)
                human_delay(0.01, 0.05)
            logger.debug("Campo de email completado")
        except Exception as e:
            logger.error(f"Error al completar campo de email: {e}")
            logger.debug(traceback.format_exc())
            # Tomar captura de pantalla para diagnóstico
            screenshot_path = os.path.join(log_dir, f"email_field_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            driver.save_screenshot(screenshot_path)
            logger.info(f"Captura de pantalla guardada en: {screenshot_path}")
            raise
        
        human_delay()
        
        # Confirmar Email
        try:
            confirm_email_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "confirm"))
            )
            confirm_email_field.clear()
            for char in email:
                confirm_email_field.send_keys(char)
                human_delay(0.01, 0.05)
            logger.debug("Campo de confirmación de email completado")
        except Exception as e:
            logger.error(f"Error al completar campo de confirmación de email: {e}")
            logger.debug(traceback.format_exc())
            raise
        
        human_delay()
        
        # Contraseña
        try:
            password_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "password"))
            )
            password_field.clear()
            for char in password:
                password_field.send_keys(char)
                human_delay(0.01, 0.05)
            logger.debug("Campo de contraseña completado")
        except Exception as e:
            logger.error(f"Error al completar campo de contraseña: {e}")
            logger.debug(traceback.format_exc())
            raise
        
        human_delay()
        
        # Nombre de perfil
        try:
            name_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "displayname"))
            )
            name_field.clear()
            for char in display_name:
                name_field.send_keys(char)
                human_delay(0.01, 0.05)
            logger.debug("Campo de nombre de perfil completado")
        except Exception as e:
            logger.error(f"Error al completar campo de nombre de perfil: {e}")
            logger.debug(traceback.format_exc())
            raise
        
        human_delay()
        
        # Fecha de nacimiento
        try:
            # Día
            day_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "day"))
            )
            day_field.clear()
            day_field.send_keys(str(birth_day))
            logger.debug(f"Campo de día completado: {birth_day}")
            
            human_delay()
            
            # Mes
            month_dropdown = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "month"))
            )
            month_dropdown.click()
            human_delay()
            
            month_option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//select[@id='month']/option[@value='{birth_month}']"))
            )
            month_option.click()
            logger.debug(f"Campo de mes completado: {birth_month}")
            
            human_delay()
            
            # Año
            year_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "year"))
            )
            year_field.clear()
            year_field.send_keys(str(birth_year))
            logger.debug(f"Campo de año completado: {birth_year}")
        except Exception as e:
            logger.error(f"Error al completar campos de fecha de nacimiento: {e}")
            logger.debug(traceback.format_exc())
            raise
        
        human_delay()
        
        # Género (aleatorio)
        try:
            gender_options = ["male", "female", "nonbinary"]
            gender = random.choice(gender_options)
            
            # Intentar diferentes estrategias para encontrar el radio button
            try:
                gender_radio = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, f"//input[@id='{gender}']"))
                )
                gender_radio.click()
            except (NoSuchElementException, ElementClickInterceptedException):
                # Intentar con label en lugar de input
                gender_label = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, f"//label[@for='{gender}']"))
                )
                gender_label.click()
            
            logger.debug(f"Género seleccionado: {gender}")
        except Exception as e:
            logger.error(f"Error al seleccionar género: {e}")
            logger.debug(traceback.format_exc())
            # No es crítico, continuar
        
        human_delay()
        
        # Aceptar términos
        try:
            # Intentar diferentes estrategias para encontrar el checkbox
            try:
                terms_checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@id='terms-conditions-checkbox']"))
                )
                if not terms_checkbox.is_selected():
                    terms_checkbox.click()
            except (NoSuchElementException, ElementClickInterceptedException):
                # Intentar con label en lugar de input
                terms_label = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//label[@for='terms-conditions-checkbox']"))
                )
                terms_label.click()
            
            logger.debug("Términos y condiciones aceptados")
        except Exception as e:
            logger.warning(f"No se pudo marcar la casilla de términos y condiciones: {e}")
            logger.debug(traceback.format_exc())
            # No es crítico, continuar
        
        human_delay()
        
        # Manejar CAPTCHA nuevamente antes de enviar
        if not handle_captcha(driver):
            logger.warning("No se pudo manejar el CAPTCHA antes de enviar, continuando de todos modos")
        
        # Enviar formulario
        try:
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            submit_button.click()
            logger.info("Formulario enviado")
        except Exception as e:
            logger.error(f"Error al enviar formulario: {e}")
            logger.debug(traceback.format_exc())
            
            # Tomar captura de pantalla para diagnóstico
            screenshot_path = os.path.join(log_dir, f"submit_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            driver.save_screenshot(screenshot_path)
            logger.info(f"Captura de pantalla guardada en: {screenshot_path}")
            
            # Reintentar con un nuevo intento
            return create_spotify_account(headless, proxy, retry_count + 1)
        
        # Esperar a recibir el correo de verificación
        logger.info("Esperando correo de verificación...")
        verification_link = check_email_instaddr(token)
        
        if not verification_link:
            logger.error("No se recibió el enlace de verificación")
            # Guardar la cuenta de todos modos, podría verificarse manualmente
            with open(ACCOUNTS_FILE, "a") as f:
                f.write(f"{email}:{password}:no_verificada\n")
            logger.info(f"Cuenta guardada como no verificada en {ACCOUNTS_FILE}: {email}:{password}")
            return False
        
        # Abrir el enlace de verificación
        logger.info(f"Abriendo enlace de verificación: {verification_link}")
        driver.get(verification_link)
        
        # Esperar a que se complete la verificación
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Verified') or contains(text(), 'Confirmed') or contains(text(), 'verificada') or contains(text(), 'confirmada')]"))
            )
            logger.info("Cuenta verificada exitosamente")
            verification_status = "verificada"
        except TimeoutException:
            logger.warning("No se pudo confirmar la verificación visualmente, pero la cuenta podría haberse verificado")
            verification_status = "posiblemente_verificada"
            
            # Tomar captura de pantalla para diagnóstico
            screenshot_path = os.path.join(log_dir, f"verification_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            driver.save_screenshot(screenshot_path)
            logger.info(f"Captura de pantalla guardada en: {screenshot_path}")
        
        # Guardar la cuenta en el archivo
        try:
            os.makedirs(os.path.dirname(ACCOUNTS_FILE), exist_ok=True)
            with open(ACCOUNTS_FILE, "a") as f:
                f.write(f"{email}:{password}:{verification_status}\n")
            
            logger.info(f"Cuenta guardada en {ACCOUNTS_FILE}: {email}:{password}:{verification_status}")
            return True
        except Exception as e:
            logger.error(f"Error al guardar la cuenta en el archivo: {e}")
            logger.debug(traceback.format_exc())
            return False
        
    except WebDriverException as e:
        logger.error(f"Error del WebDriver: {e}")
        logger.debug(traceback.format_exc())
        # Reintentar con un nuevo intento
        return create_spotify_account(headless, proxy, retry_count + 1)
    except Exception as e:
        logger.error(f"Error inesperado al crear cuenta: {e}")
        logger.debug(traceback.format_exc())
        return False
    finally:
        if driver:
            try:
                driver.quit()
                logger.debug("Navegador cerrado correctamente")
            except Exception as e:
                logger.error(f"Error al cerrar el navegador: {e}")

def create_multiple_accounts(count=1, headless=True, proxy=None):
    """Crea múltiples cuentas de Spotify"""
    logger.info(f"Iniciando creación de {count} cuentas de Spotify")
    
    # Verificar API Key
    config = load_config()
    if not config.get("INSTADDR_API_KEY"):
        logger.error("API Key de InstAddr no configurada. Configure la API Key antes de crear cuentas.")
        return 0
    
    success_count = 0
    for i in range(count):
        logger.info(f"Creando cuenta {i+1}/{count}")
        if create_spotify_account(headless, proxy):
            success_count += 1
        
        # Esperar entre creaciones para evitar detección
        if i < count - 1:
            wait_time = random.randint(30, 120)
            logger.info(f"Esperando {wait_time} segundos antes de crear la siguiente cuenta")
            time.sleep(wait_time)
    
    logger.info(f"Proceso completado. {success_count}/{count} cuentas creadas exitosamente")
    return success_count

def setup_instaddr_api_key(api_key):
    """Configura la API Key de InstAddr en el archivo de configuración"""
    if not api_key or not api_key.strip():
        logger.error("API Key de InstAddr inválida (vacía)")
        return False
    
    config = load_config()
    config["INSTADDR_API_KEY"] = api_key.strip()
    success = save_config(config)
    
    if success:
        logger.info("API Key de InstAddr configurada correctamente")
        return True
    else:
        logger.error("Error al configurar API Key de InstAddr")
        return False

def verify_instaddr_api_key():
    """Verifica que la API Key de InstAddr esté configurada y sea válida"""
    config = load_config()
    api_key = config.get("INSTADDR_API_KEY", "")
    
    if not api_key:
        logger.error("API Key de InstAddr no configurada")
        return False
    
    try:
        logger.info("Verificando API Key de InstAddr")
        response = requests.post(
            "https://api.internal.temp-mail.io/api/v3/email/new",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info("API Key de InstAddr válida")
            return True
        elif response.status_code == 401:
            logger.error("API Key de InstAddr inválida o expirada")
            return False
        else:
            logger.error(f"Error al verificar API Key de InstAddr: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error al verificar API Key de InstAddr: {e}")
        logger.debug(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Ejemplo de uso
    # setup_instaddr_api_key("tu_api_key_aquí")
    # create_multiple_accounts(count=2, headless=False)
    pass
