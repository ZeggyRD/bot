#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import random
import subprocess
import logging
import json
import uiautomator2 as u2
from datetime import datetime

# Configuración del sistema de logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"android_device_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.DEBUG,      # antes era INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Device")

# Constantes
DEVICE_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "devices_db.json")
SPOTIFY_PREFIX = "com.spotify.mus"
SOCKSDROID_PACKAGE = "net.typeblog.socks"

class Device:
    def __init__(self, device_id=None):
        """Inicializa un objeto para controlar un dispositivo Android"""
        self.device_id = device_id
        self.device = None
        self.connected = False
        self.current_app = None
        self.device_info = {}
        self.devices_db = self._load_devices_db()
        
        # if device_id:  # Connection is no longer automatic
        #     self.connect(device_id)
    
    def _load_devices_db(self):
        """Carga la base de datos de dispositivos desde el archivo JSON"""
        if os.path.exists(DEVICE_DB_FILE):
            try:
                with open(DEVICE_DB_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error al cargar la base de datos de dispositivos: {e}")
                return {}
        return {}
    
    def _save_devices_db(self):
        """Guarda la base de datos de dispositivos en el archivo JSON"""
        try:
            os.makedirs(os.path.dirname(DEVICE_DB_FILE), exist_ok=True)
            with open(DEVICE_DB_FILE, 'w') as f:
                json.dump(self.devices_db, f, indent=4)
        except Exception as e:
            logger.error(f"Error al guardar la base de datos de dispositivos: {e}")
    
    @staticmethod
    def get_connected_device_ids():
        """Obtiene la lista de IDs de dispositivos Android conectados por USB"""
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
    
    def connect(self, device_id=None):
        """Conecta al dispositivo Android"""
        if device_id:
            self.device_id = device_id

        if not self.device_id:
            logger.error("No se especificó ID de dispositivo")
            return False

        try:
            logger.info(f"Conectando al dispositivo {self.device_id}")
            # 1) Conectar vía uiautomator2
            self.device = u2.connect_usb(self.device_id)
            self.connected = True

            # 2) Actualizar info local y en BD
            self._update_device_info()

            # 3) Detectar y registrar todos los clones de Spotify
            self.register_all_spotify()

            logger.info(f"Conectado al dispositivo {self.device_id}")
            return True

        except Exception as e:
            logger.error(f"Error al conectar al dispositivo {self.device_id}: {e}")
            self.connected = False
            return False
    
    def _update_device_info(self):
        """Actualiza la información del dispositivo"""
        if not self.connected or not self.device:
            logger.error("Dispositivo no conectado")
            return
        
        try:
            # Obtener información básica
            info = self.device.info
            
            # Obtener información adicional mediante ADB
            brand = self._get_prop("ro.product.brand")
            model = self._get_prop("ro.product.model")
            android_version = self._get_prop("ro.build.version.release")
            sdk_version = self._get_prop("ro.build.version.sdk")
            
            self.device_info = {
                "id": self.device_id,
                "brand": brand,
                "model": model,
                "android_version": android_version,
                "sdk_version": sdk_version,
                "display": info.get("display", ""),
                "battery": info.get("battery", {})
            }
            
            # Actualizar en la base de datos
            if self.device_id not in self.devices_db:
                self.devices_db[self.device_id] = {}
            
            self.devices_db[self.device_id].update({
                "info": self.device_info,
                "last_connected": datetime.now().isoformat(),
                "apps": self.devices_db.get(self.device_id, {}).get("apps", [])
            })
            
            self._save_devices_db()
            
            logger.info(f"Información del dispositivo actualizada: {self.device_info['brand']} {self.device_info['model']}")
        except Exception as e:
            logger.error(f"Error al actualizar información del dispositivo: {e}")
    
    def _get_prop(self, prop):
        """Obtiene una propiedad del sistema Android"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.device_id, "shell", f"getprop {prop}"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except Exception:
            return ""
        
    def _adb_shell(self, args):
        """Ejecuta un comando adb shell y devuelve stdout."""
        try:
            cmd = ["adb", "-s", self.device_id, "shell"] + args
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Error al ejecutar adb shell {' '.join(args)}: {e}")
            return ""    
        
    def detect_spotify_clones(self):
        """Lista todos los paquetes que empiecen por SPOTIFY_PREFIX."""
        out = self._adb_shell(["pm", "list", "packages"])
        clones = []
        for line in out.splitlines():
            if line.startswith("package:" + SPOTIFY_PREFIX):
                clones.append(line.split("package:")[1])
        logger.info(f"Clones Spotify detectados: {clones}")
        return clones

    def register_all_spotify(self):
        """Detecta y registra todos los clones Spotify en la DB."""
        clones = self.detect_spotify_clones()
        db = self.devices_db.setdefault(self.device_id, {"apps": []})
        for pkg in clones:
            if not any(app["package"] == pkg for app in db["apps"]):
                db["apps"].append({
                    "package": pkg,
                    "registered_date": datetime.now().isoformat(),
                    "last_used": None,
                    "account": None
                })
                logger.info(f"✅ Registrado clone Spotify: {pkg}")
        self._save_devices_db()
        logger.debug("<<< register_all_spotify() ha terminado >>>")
    def install_app(self, apk_path):
        """Instala una aplicación en el dispositivo"""
        if not self.connected:
            logger.error("Dispositivo no conectado")
            return False
        
        try:
            logger.info(f"Instalando APK: {apk_path}")
            result = subprocess.run(
                ["adb", "-s", self.device_id, "install", "-r", apk_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            if "Success" in result.stdout:
                logger.info(f"APK instalado correctamente: {apk_path}")
                return True
            else:
                logger.error(f"Error al instalar APK: {result.stdout}")
                return False
        except Exception as e:
            logger.error(f"Error al instalar APK: {e}")
            return False
    
    def uninstall_app(self, package_name):
        """Desinstala una aplicación del dispositivo"""
        if not self.connected:
            logger.error("Dispositivo no conectado")
            return False
        
        try:
            logger.info(f"Desinstalando aplicación: {package_name}")
            result = subprocess.run(
                ["adb", "-s", self.device_id, "uninstall", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            if "Success" in result.stdout:
                logger.info(f"Aplicación desinstalada correctamente: {package_name}")
                return True
            else:
                logger.error(f"Error al desinstalar aplicación: {result.stdout}")
                return False
        except Exception as e:
            logger.error(f"Error al desinstalar aplicación: {e}")
            return False
    
    def start_app(self, package_name, activity=None):
        """Inicia una aplicación en el dispositivo"""
        if not self.connected:
            logger.error("Dispositivo no conectado")
            return False
        
        try:
            if activity:
                start_cmd = f"am start -n {package_name}/{activity}"
            else:
                start_cmd = f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
            
            logger.info(f"Iniciando aplicación: {package_name}")
            subprocess.run(
                ["adb", "-s", self.device_id, "shell", start_cmd],
                check=True
            )
            
            self.current_app = package_name
            time.sleep(3)  # Esperar a que la aplicación se inicie
            
            logger.info(f"Aplicación iniciada: {package_name}")
            return True
        except Exception as e:
            logger.error(f"Error al iniciar aplicación: {e}")
            return False
    
    def stop_app(self, package_name=None):
        """Detiene una aplicación en el dispositivo"""
        if not self.connected:
            logger.error("Dispositivo no conectado")
            return False
        
        if not package_name:
            package_name = self.current_app
        
        if not package_name:
            logger.error("No se especificó aplicación para detener")
            return False
        
        try:
            logger.info(f"Deteniendo aplicación: {package_name}")
            subprocess.run(
                ["adb", "-s", self.device_id, "shell", f"am force-stop {package_name}"],
                check=True
            )
            
            if self.current_app == package_name:
                self.current_app = None
            
            logger.info(f"Aplicación detenida: {package_name}")
            return True
        except Exception as e:
            logger.error(f"Error al detener aplicación: {e}")
            return False
    
    def clear_app_data(self, package_name):
        """Limpia los datos de una aplicación"""
        if not self.connected:
            logger.error("Dispositivo no conectado")
            return False
        
        try:
            logger.info(f"Limpiando datos de aplicación: {package_name}")
            subprocess.run(
                ["adb", "-s", self.device_id, "shell", f"pm clear {package_name}"],
                check=True
            )
            
            logger.info(f"Datos de aplicación limpiados: {package_name}")
            return True
        except Exception as e:
            logger.error(f"Error al limpiar datos de aplicación: {e}")
            return False
    
    def capture_screenshot(self, output_path=None):
        """Captura una captura de pantalla del dispositivo"""
        if not self.connected or not self.device:
            logger.error("Dispositivo no conectado")
            return None
        
        try:
            if not output_path:
                screenshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots")
                os.makedirs(screenshots_dir, exist_ok=True)
                output_path = os.path.join(screenshots_dir, f"screenshot_{self.device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            logger.info(f"Capturando pantalla en: {output_path}")
            self.device.screenshot(output_path)
            
            logger.info(f"Captura de pantalla guardada en: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error al capturar pantalla: {e}")
            return None
    
    def tap(self, x, y, jitter=10):
        """Toca un punto en la pantalla con un ligero jitter para simular un toque humano"""
        if not self.connected or not self.device:
            logger.error("Dispositivo no conectado")
            return False
        
        try:
            # Añadir jitter para simular comportamiento humano
            jitter_x = random.randint(-jitter, jitter)
            jitter_y = random.randint(-jitter, jitter)
            
            x += jitter_x
            y += jitter_y
            
            logger.debug(f"Tocando en ({x}, {y})")
            self.device.click(x, y)
            
            return True
        except Exception as e:
            logger.error(f"Error al tocar pantalla: {e}")
            return False
    
    def swipe(self, sx, sy, ex, ey, duration=None):
        """Realiza un deslizamiento en la pantalla"""
        if not self.connected or not self.device:
            logger.error("Dispositivo no conectado")
            return False
        
        try:
            if duration is None:
                # Duración aleatoria para simular comportamiento humano
                duration = random.uniform(0.3, 0.8)
            
            logger.debug(f"Deslizando de ({sx}, {sy}) a ({ex}, {ey})")
            self.device.swipe(sx, sy, ex, ey, duration=duration)
            
            return True
        except Exception as e:
            logger.error(f"Error al deslizar pantalla: {e}")
            return False
    
    def input_text(self, text):
        """Introduce texto en el campo de entrada activo"""
        if not self.connected or not self.device:
            logger.error("Dispositivo no conectado")
            return False
        
        try:
            logger.debug(f"Introduciendo texto: {text}")
            self.device.send_keys(text)
            
            return True
        except Exception as e:
            logger.error(f"Error al introducir texto: {e}")
            return False
    
    def press_key(self, keycode):
        """Presiona una tecla específica"""
        if not self.connected or not self.device:
            logger.error("Dispositivo no conectado")
            return False
        
        try:
            logger.debug(f"Presionando tecla: {keycode}")
            self.device.press(keycode)
            
            return True
        except Exception as e:
            logger.error(f"Error al presionar tecla: {e}")
            return False
    
    def wait_for_element(self, selector, timeout=10):
        """Espera a que aparezca un elemento en la pantalla"""
        if not self.connected or not self.device:
            logger.error("Dispositivo no conectado")
            return None
        
        try:
            logger.debug(f"Esperando elemento: {selector}")
            element = self.device.wait(selector, timeout=timeout)
            
            if element:
                logger.debug(f"Elemento encontrado: {selector}")
                return element
            else:
                logger.warning(f"Elemento no encontrado: {selector}")
                return None
        except Exception as e:
            logger.error(f"Error al esperar elemento: {e}")
            return None
    
    def register_spotify_app(self, package_name, app_name=None):
        """Registra una aplicación Spotify clonada en la base de datos"""
        if not self.connected:
            logger.error("Dispositivo no conectado")
            return False
        
        if not app_name:
            app_name = f"Spotify Clone {len(self.devices_db.get(self.device_id, {}).get('apps', []))}"
        
        try:
            # Verificar si la aplicación está instalada
            result = subprocess.run(
                ["adb", "-s", self.device_id, "shell", f"pm list packages | grep {package_name}"],
                capture_output=True,
                text=True
            )
            
            if package_name not in result.stdout:
                logger.error(f"La aplicación {package_name} no está instalada en el dispositivo")
                return False
            
            # Actualizar la base de datos
            if self.device_id not in self.devices_db:
                self.devices_db[self.device_id] = {
                    "info": {},
                    "apps": []
                }
            
            # Verificar si la aplicación ya está registrada
            for app in self.devices_db[self.device_id].get("apps", []):
                if app["package"] == package_name:
                    logger.info(f"La aplicación {package_name} ya está registrada")
                    return True
            
            # Registrar la aplicación
            self.devices_db[self.device_id].setdefault("apps", []).append({
                "package": package_name,
                "name": app_name,
                "registered_date": datetime.now().isoformat(),
                "last_used": None,
                "account": None
            })
            
            self._save_devices_db()
            
            logger.info(f"Aplicación Spotify registrada: {package_name} como {app_name}")
            return True
        except Exception as e:
            logger.error(f"Error al registrar aplicación Spotify: {e}")
            return False
    
    def get_registered_spotify_apps(self):
        """Obtiene la lista de aplicaciones Spotify registradas para este dispositivo"""
        if not self.device_id:
            logger.error("No se especificó ID de dispositivo")
            return []
        
        return self.devices_db.get(self.device_id, {}).get("apps", [])
    
    def assign_account_to_app(self, package_name, email):
        """Asigna una cuenta a una aplicación Spotify específica"""
        if not self.device_id:
            logger.error("No se especificó ID de dispositivo")
            return False
        
        try:
            # Buscar la aplicación en la base de datos
            apps = self.devices_db.get(self.device_id, {}).get("apps", [])
            for i, app in enumerate(apps):
                if app["package"] == package_name:
                    # Actualizar la información de la cuenta
                    self.devices_db[self.device_id]["apps"][i]["account"] = email
                    self.devices_db[self.device_id]["apps"][i]["last_used"] = datetime.now().isoformat()
                    
                    self._save_devices_db()
                    
                    logger.info(f"Cuenta {email} asignada a la aplicación {package_name}")
                    return True
            
            logger.error(f"Aplicación {package_name} no encontrada en la base de datos")
            return False
        except Exception as e:
            logger.error(f"Error al asignar cuenta a aplicación: {e}")
            return False
    
    def get_app_for_account(self, email):
        """Obtiene la aplicación Spotify asignada a una cuenta específica"""
        if not self.device_id:
            logger.error("No se especificó ID de dispositivo")
            return None
        
        try:
            apps = self.devices_db.get(self.device_id, {}).get("apps", [])
            for app in apps:
                if app.get("account") == email:
                    return app["package"]
            
            return None
        except Exception as e:
            logger.error(f"Error al obtener aplicación para cuenta: {e}")
            return None
    
    def human_delay(self, min_sec=0.5, max_sec=2.0):
        """Genera un retraso aleatorio para simular comportamiento humano"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        return delay

class DeviceManager:
    def __init__(self):
        """Inicializa el administrador de dispositivos."""
        self.managed_devices: dict[str, Device] = {}
        logger.info("DeviceManager initialized.")

    def update_devices(self):
        """Actualiza la lista de dispositivos gestionados y su estado de conexión."""
        logger.info("Updating devices...")
        connected_device_ids = Device.get_connected_device_ids()
        
        # Check currently connected devices
        for device_id in connected_device_ids:
            if device_id in self.managed_devices:
                device_instance = self.managed_devices[device_id]
                if not device_instance.connected:
                    logger.info(f"Device {device_id} was managed but disconnected. Attempting to reconnect.")
                    if device_instance.connect(): # connect() already updates self.connected
                        logger.info(f"Successfully reconnected to device {device_id}.")
                    else:
                        logger.warning(f"Failed to reconnect to device {device_id}.")
                # If already connected and managed, do nothing
            else:
                logger.info(f"New device found: {device_id}. Adding to managed devices.")
                new_device = Device(device_id=device_id)
                if new_device.connect():
                    self.managed_devices[device_id] = new_device
                    logger.info(f"Successfully connected to and managed new device {device_id}.")
                else:
                    logger.warning(f"Failed to connect to new device {device_id}.")

        # Check for disconnected devices among managed ones
        managed_ids = list(self.managed_devices.keys()) # Avoid issues with dict size change during iteration
        for device_id in managed_ids:
            if device_id not in connected_device_ids:
                if self.managed_devices[device_id].connected:
                    logger.info(f"Managed device {device_id} is no longer connected.")
                    self.managed_devices[device_id].connected = False # Mark as disconnected
                    # Optionally, call a device.disconnect() method if it exists
                    # For now, we might remove it or keep it as inactive
                    # logger.info(f"Removing device {device_id} from managed list for now.")
                    # del self.managed_devices[device_id] 
                else:
                    # If it was already marked as disconnected and still not in connected_ids,
                    # we can choose to remove it or just log.
                    logger.debug(f"Previously disconnected device {device_id} remains disconnected.")

    def get_active_devices(self) -> list[Device]:
        """Devuelve una lista de dispositivos gestionados que están actualmente conectados."""
        active_devices = [
            dev for dev in self.managed_devices.values() if dev.connected
        ]
        logger.info(f"Found {len(active_devices)} active devices.")
        return active_devices


if __name__ == "__main__":
    manager = DeviceManager()
    manager.update_devices() # Initial scan
    
    # Potentially show devices after first scan
    active_devices_initial = manager.get_active_devices()
    if active_devices_initial:
        print(f"Found {len(active_devices_initial)} active devices initially:")
        for dev_instance in active_devices_initial:
            print(f"  Device ID: {dev_instance.device_id}, Model: {dev_instance.device_info.get('model', 'N/A')}, Connected: {dev_instance.connected}")
    else:
        print("No active devices found initially.")

    # Simulate some time passing and update again
    print("\nSimulating a delay and updating devices again...\n")
    time.sleep(2) # Simulate time for potential device changes
    manager.update_devices()
    
    active_devices_updated = manager.get_active_devices()
    if active_devices_updated:
        print(f"Found {len(active_devices_updated)} active devices after update:")
        for dev_instance in active_devices_updated:
            print(f"  Device ID: {dev_instance.device_id}, Model: {dev_instance.device_info.get('model', 'N/A')}, Connected: {dev_instance.connected}")
            # Further example: Register Spotify apps for the first active device
            if dev_instance == active_devices_updated[0] and dev_instance.connected: # Ensure it's connected before using
                print(f"    Attempting to register Spotify apps for {dev_instance.device_id}...")
                dev_instance.register_all_spotify()
                apps = dev_instance.get_registered_spotify_apps()
                print(f"    Registered Spotify Apps on {dev_instance.device_id}: {apps}")
                
                # Example of capturing a screenshot
                screenshot_path = dev_instance.capture_screenshot()
                if screenshot_path:
                    print(f"    Screenshot saved to: {screenshot_path}")
                else:
                    print(f"    Failed to capture screenshot for {dev_instance.device_id}")
            elif not dev_instance.connected:
                 print(f"    Device {dev_instance.device_id} is not connected, skipping further actions.")

    else:
        print("No active devices found after update.")
