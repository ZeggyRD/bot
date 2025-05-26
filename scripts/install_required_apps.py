#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import time
import random
import logging
from datetime import datetime

# Configuración del sistema de logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"requirements_installer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RequirementsInstaller")

def check_adb():
    """Verifica si ADB está instalado y disponible"""
    try:
        result = subprocess.run(["adb", "version"], capture_output=True, text=True)
        if "Android Debug Bridge" in result.stdout:
            logger.info("ADB está instalado y disponible")
            return True
        else:
            logger.error("ADB está instalado pero no funciona correctamente")
            return False
    except Exception as e:
        logger.error(f"ADB no está instalado o no está en el PATH: {e}")
        return False

def install_python_requirements():
    """Instala las dependencias de Python"""
    try:
        logger.info("Instalando dependencias de Python...")
        requirements = [
            "uiautomator2",
            "opencv-python",
            "numpy",
            "requests",
            "pillow",
            "selenium",
            "webdriver-manager",
            "PyQt5"
        ]
        
        for req in requirements:
            logger.info(f"Instalando {req}...")
            subprocess.run([sys.executable, "-m", "pip", "install", req], check=True)
        
        logger.info("Dependencias de Python instaladas correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al instalar dependencias de Python: {e}")
        return False

def create_requirements_file():
    """Crea el archivo requirements.txt"""
    try:
        requirements = [
            "uiautomator2==2.16.3",
            "opencv-python==4.7.0.72",
            "numpy==1.24.3",
            "requests==2.31.0",
            "pillow==10.0.0",
            "selenium==4.10.0",
            "webdriver-manager==3.8.6",
            "PyQt5==5.15.9"
        ]
        
        requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements.txt")
        with open(requirements_path, "w") as f:
            f.write("\n".join(requirements))
        
        logger.info(f"Archivo requirements.txt creado en {requirements_path}")
        return True
    except Exception as e:
        logger.error(f"Error al crear archivo requirements.txt: {e}")
        return False

def check_android_devices():
    """Verifica los dispositivos Android conectados"""
    try:
        logger.info("Verificando dispositivos Android conectados...")
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        
        devices = []
        for line in result.stdout.strip().split('\n')[1:]:
            if line and not line.startswith('*') and 'device' in line:
                device_id = line.split()[0]
                devices.append(device_id)
        
        if devices:
            logger.info(f"Dispositivos Android conectados: {devices}")
            return devices
        else:
            logger.warning("No hay dispositivos Android conectados")
            return []
    except Exception as e:
        logger.error(f"Error al verificar dispositivos Android: {e}")
        return []

def check_spotify_installed(device_id):
    """Verifica si Spotify está instalado en el dispositivo"""
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "pm", "list", "packages", "spotify"],
            capture_output=True,
            text=True
        )
        
        if "spotify" in result.stdout.lower():
            logger.info(f"Spotify está instalado en el dispositivo {device_id}")
            return True
        else:
            logger.warning(f"Spotify no está instalado en el dispositivo {device_id}")
            return False
    except Exception as e:
        logger.error(f"Error al verificar Spotify en el dispositivo {device_id}: {e}")
        return False

def check_socksdroid_installed(device_id):
    """Verifica si SocksDroid está instalado en el dispositivo"""
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "pm", "list", "packages", "net.typeblog.socks"],
            capture_output=True,
            text=True
        )
        
        if "net.typeblog.socks" in result.stdout:
            logger.info(f"SocksDroid está instalado en el dispositivo {device_id}")
            return True
        else:
            logger.warning(f"SocksDroid no está instalado en el dispositivo {device_id}")
            return False
    except Exception as e:
        logger.error(f"Error al verificar SocksDroid en el dispositivo {device_id}: {e}")
        return False

def create_directory_structure():
    """Crea la estructura de directorios necesaria"""
    try:
        logger.info("Creando estructura de directorios...")
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.join(base_dir, "..")
        
        directories = [
            os.path.join(root_dir, "data"),
            os.path.join(root_dir, "config"),
            os.path.join(root_dir, "logs"),
            os.path.join(root_dir, "templates"),
            os.path.join(root_dir, "screenshots")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Directorio creado: {directory}")
        
        return True
    except Exception as e:
        logger.error(f"Error al crear estructura de directorios: {e}")
        return False

def create_config_files():
    """Crea los archivos de configuración iniciales"""
    try:
        logger.info("Creando archivos de configuración iniciales...")
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(base_dir, "..", "config")
        
        # Crear config.json
        import json
        config = {
            "INSTADDR_API_KEY": "",
            "WEBSHARE_API_KEY": "",
            "TRACKS": "",
            "PLAYLISTS": "",
            "ARTISTS": "",
            "ACCOUNTS": "",
            "PROXY": ""
        }
        
        with open(os.path.join(config_dir, "config.json"), "w") as f:
            json.dump(config, f, indent=4)
        
        # Crear behavior_profiles.json
        behavior_profiles = {
            "casual_listener": {
                "listen_duration_min": 30,
                "listen_duration_max": 120,
                "skip_probability": 0.3,
                "like_probability": 0.1,
                "follow_probability": 0.05,
                "playlist_save_probability": 0.02,
                "interaction_delay_min": 10,
                "interaction_delay_max": 60,
                "session_duration_min": 30,
                "session_duration_max": 120
            },
            "power_user": {
                "listen_duration_min": 60,
                "listen_duration_max": 180,
                "skip_probability": 0.15,
                "like_probability": 0.25,
                "follow_probability": 0.15,
                "playlist_save_probability": 0.1,
                "interaction_delay_min": 5,
                "interaction_delay_max": 30,
                "session_duration_min": 60,
                "session_duration_max": 240
            },
            "explorer": {
                "listen_duration_min": 20,
                "listen_duration_max": 90,
                "skip_probability": 0.4,
                "like_probability": 0.2,
                "follow_probability": 0.1,
                "playlist_save_probability": 0.15,
                "interaction_delay_min": 5,
                "interaction_delay_max": 20,
                "session_duration_min": 45,
                "session_duration_max": 150
            },
            "passive": {
                "listen_duration_min": 60,
                "listen_duration_max": 240,
                "skip_probability": 0.1,
                "like_probability": 0.05,
                "follow_probability": 0.02,
                "playlist_save_probability": 0.01,
                "interaction_delay_min": 30,
                "interaction_delay_max": 120,
                "session_duration_min": 60,
                "session_duration_max": 300
            }
        }
        
        with open(os.path.join(config_dir, "behavior_profiles.json"), "w") as f:
            json.dump(behavior_profiles, f, indent=4)
        
        logger.info("Archivos de configuración creados correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al crear archivos de configuración: {e}")
        return False

def create_example_data_files():
    """Crea archivos de datos de ejemplo"""
    try:
        logger.info("Creando archivos de datos de ejemplo...")
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "..", "data")
        
        # Ejemplo de tracks.txt
        tracks = [
            "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
            "https://open.spotify.com/track/0HUTL8i4y4MiGCPId7M7wb",
            "https://open.spotify.com/track/7qiZfU4dY1lWllzX7mPBI3"
        ]
        
        with open(os.path.join(data_dir, "tracks.txt"), "w") as f:
            f.write("\n".join(tracks))
        
        # Ejemplo de playlists.txt
        playlists = [
            "https://open.spotify.com/playlist/37i9dQZEVXcJZyENOWUFo7",
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
            "https://open.spotify.com/playlist/37i9dQZF1DX0XUsuxWHRQd"
        ]
        
        with open(os.path.join(data_dir, "playlists.txt"), "w") as f:
            f.write("\n".join(playlists))
        
        # Ejemplo de artists.txt
        artists = [
            "https://open.spotify.com/artist/06HL4z0CvFAxyc27GXpf02",
            "https://open.spotify.com/artist/1Xyo4u8uXC1ZmMpatF05PJ",
            "https://open.spotify.com/artist/3TVXtAsR1Inumwj472S9r4"
        ]
        
        with open(os.path.join(data_dir, "artists.txt"), "w") as f:
            f.write("\n".join(artists))
        
        # Ejemplo de spotify_accounts.txt (vacío por seguridad)
        with open(os.path.join(data_dir, "spotify_accounts.txt"), "w") as f:
            f.write("# Formato: email:password\n# Ejemplo: user@example.com:password123\n")
        
        # Ejemplo de proxy_pool.txt (vacío por seguridad)
        with open(os.path.join(data_dir, "proxy_pool.txt"), "w") as f:
            f.write("# Formato: ip:puerto:usuario:contraseña\n# Ejemplo: 192.168.1.1:8080:user:pass\n")
        
        logger.info("Archivos de datos de ejemplo creados correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al crear archivos de datos de ejemplo: {e}")
        return False

def main():
    """Función principal"""
    logger.info("Iniciando instalación de requisitos...")
    
    # Verificar ADB
    if not check_adb():
        logger.error("ADB no está disponible. Por favor, instala Android SDK y asegúrate de que ADB esté en el PATH.")
        return False
    
    # Instalar dependencias de Python
    if not install_python_requirements():
        logger.error("Error al instalar dependencias de Python.")
        return False
    
    # Crear archivo requirements.txt
    create_requirements_file()
    
    # Crear estructura de directorios
    if not create_directory_structure():
        logger.error("Error al crear estructura de directorios.")
        return False
    
    # Crear archivos de configuración
    if not create_config_files():
        logger.error("Error al crear archivos de configuración.")
        return False
    
    # Crear archivos de datos de ejemplo
    if not create_example_data_files():
        logger.error("Error al crear archivos de datos de ejemplo.")
        return False
    
    # Verificar dispositivos Android
    devices = check_android_devices()
    if devices:
        for device_id in devices:
            check_spotify_installed(device_id)
            check_socksdroid_installed(device_id)
    
    logger.info("Instalación de requisitos completada correctamente.")
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Instalación completada correctamente.")
        print("Puedes iniciar el sistema ejecutando: python main.py")
    else:
        print("\n❌ La instalación no se completó correctamente.")
        print("Por favor, revisa los logs para más información.")
