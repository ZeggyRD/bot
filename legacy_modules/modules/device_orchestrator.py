# -*- coding: utf-8 -*-
"""Módulo para orquestar múltiples dispositivos ADB y sesiones de bot."""

import subprocess
import threading
import time
import logging
import queue

from .proxy_manager import ProxyManager, Proxy
from .human_behavior import DevicePersonality
# Asumiremos que existe un módulo `spotify_actions` que contiene la lógica de interacción
# from .spotify_actions import run_spotify_session # Importar la función principal de la sesión

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s")

MAX_PARALLEL_SESSIONS = 10
ADB_COMMAND = "adb" # Asegurarse que ADB esté en el PATH o usar ruta absoluta
DEVICE_RETRY_LIMIT = 3

class Device:
    """Representa un dispositivo ADB conectado."""
    def __init__(self, serial):
        self.serial = serial
        self.status = "idle" # idle, running, failed
        self.fail_count = 0
        self.personality = DevicePersonality(serial) # Cada dispositivo tiene su personalidad
        self.current_proxy: Proxy | None = None
        self.thread: threading.Thread | None = None

    def __str__(self):
        return f"Device(Serial: {self.serial}, Status: {self.status}, Fails: {self.fail_count})"

def detect_adb_devices() -> list[str]:
    """Detecta dispositivos ADB conectados y devuelve sus números de serie."""
    devices = []
    try:
        # Ejecutar 'adb devices' y capturar la salida
        result = subprocess.run([ADB_COMMAND, "devices"], capture_output=True, text=True, check=True, timeout=15)
        lines = result.stdout.strip().split("\n")

        # La primera línea es "List of devices attached", la saltamos
        if len(lines) > 1:
            for line in lines[1:]:
                parts = line.split("\t")
                if len(parts) == 2 and parts[1] == "device":
                    devices.append(parts[0])
                    logging.info(f"Detected ADB device: {parts[0]}")
                elif len(parts) == 2 and parts[1] == "unauthorized":
                    logging.warning(f"Detected unauthorized ADB device: {parts[0]}. Please authorize on the device.")
                elif len(parts) == 2:
                    logging.warning(f"Detected ADB device with status 	'{parts[1]}': {parts[0]}")

    except FileNotFoundError:
        logging.error(f"'{ADB_COMMAND}' command not found. Please ensure ADB is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running '{ADB_COMMAND} devices': {e}")
        logging.error(f"ADB stderr: {e.stderr}")
    except subprocess.TimeoutExpired:
        logging.error(f"'{ADB_COMMAND} devices' command timed out.")
    except Exception as e:
        logging.error(f"An unexpected error occurred during ADB device detection: {e}")

    if not devices:
        logging.warning("No active ADB devices detected.")
    return devices

class DeviceOrchestrator:
    """Gestiona la ejecución de tareas en múltiples dispositivos ADB."""
    def __init__(self, proxy_manager: ProxyManager, task_function):
        """Inicializa el orquestador.

        Args:
            proxy_manager: Instancia del ProxyManager.
            task_function: La función que se ejecutará para cada sesión/dispositivo.
                         Debe aceptar (device: Device, proxy: Proxy) como argumentos.
        """
        self.proxy_manager = proxy_manager
        self.task_function = task_function # La función que define el trabajo de una sesión
        self.devices: dict[str, Device] = {}
        self.active_threads: list[threading.Thread] = []
        self.lock = threading.Lock()
        self.task_queue = queue.Queue() # Cola para gestionar qué dispositivos necesitan ejecutar tarea
        self.stop_event = threading.Event()

    def _update_device_list(self):
        """Actualiza la lista de dispositivos detectados."""
        detected_serials = detect_adb_devices()
        with self.lock:
            # Añadir nuevos dispositivos
            for serial in detected_serials:
                if serial not in self.devices:
                    logging.info(f"Adding new device: {serial}")
                    self.devices[serial] = Device(serial)
                    # Añadir a la cola para que se le asigne una tarea si hay slots libres
                    if self.devices[serial].status == "idle":
                         self.task_queue.put(self.devices[serial])

            # Marcar dispositivos desconectados (opcional, podríamos simplemente dejarlos)
            current_serials = set(self.devices.keys())
            disconnected_serials = current_serials - set(detected_serials)
            for serial in disconnected_serials:
                if self.devices[serial].status != "running": # No eliminar si está corriendo una tarea
                    logging.warning(f"Device {serial} seems disconnected. Removing from active pool.")
                    # Podríamos moverlo a una lista de inactivos en lugar de eliminarlo
                    del self.devices[serial]
                else:
                    logging.warning(f"Device {serial} seems disconnected but is still marked as running. Waiting for task completion.")

    def _worker(self):
        """Función ejecutada por cada hilo trabajador."""
        while not self.stop_event.is_set():
            try:
                device: Device = self.task_queue.get(timeout=1) # Espera 1 segundo por una tarea
            except queue.Empty:
                continue # No hay tareas, volver a esperar

            proxy = None
            try:
                with self.lock:
                    if device.status != "idle" or device.fail_count >= DEVICE_RETRY_LIMIT:
                        logging.warning(f"Skipping task for device {device.serial} (Status: {device.status}, Fails: {device.fail_count})")
                        self.task_queue.task_done()
                        continue

                    # Intentar obtener un proxy
                    proxy = self.proxy_manager.get_proxy()
                    if not proxy:
                        logging.warning(f"No proxy available for device {device.serial}. Re-queueing device.")
                        # Devolver a la cola para intentarlo más tarde
                        self.task_queue.put(device)
                        self.task_queue.task_done()
                        time.sleep(5) # Esperar un poco antes de reintentar
                        continue

                    # Marcar dispositivo como ocupado y asignar proxy
                    device.status = "running"
                    device.current_proxy = proxy
                    device.thread = threading.current_thread()
                    logging.info(f"Starting task for device {device.serial} with proxy {proxy.address}")

                # Ejecutar la tarea asignada fuera del lock
                success = False
                try:
                    # Aquí se llama a la función que realmente hace el trabajo (ej. run_spotify_session)
                    self.task_function(device, proxy)
                    success = True
                    logging.info(f"Task completed successfully for device {device.serial}")
                    device.fail_count = 0 # Resetear contador de fallos en éxito
                except Exception as e:
                    logging.error(f"Task failed for device {device.serial}: {e}", exc_info=True)
                    device.fail_count += 1
                finally:
                    # Liberar el proxy y el dispositivo independientemente del resultado
                    with self.lock:
                        self.proxy_manager.release_proxy(proxy, success)
                        device.current_proxy = None
                        device.thread = None
                        if device.fail_count >= DEVICE_RETRY_LIMIT:
                            device.status = "failed"
                            logging.error(f"Device {device.serial} reached retry limit ({DEVICE_RETRY_LIMIT}). Marking as failed.")
                        else:
                            device.status = "idle"
                            # Si no falló permanentemente, volver a poner en cola para la siguiente tarea
                            self.task_queue.put(device)
                        self.task_queue.task_done()

            except Exception as e:
                logging.error(f"Unexpected error in worker thread: {e}", exc_info=True)
                # Asegurarse de liberar recursos si algo falló catastróficamente
                with self.lock:
                    if proxy and proxy.in_use:
                        self.proxy_manager.release_proxy(proxy, success=False)
                    if device:
                        device.status = "idle" # O "failed" si es grave
                        device.current_proxy = None
                        device.thread = None
                        if not self.stop_event.is_set(): # Evitar re-encolar si nos estamos deteniendo
                             self.task_queue.put(device) # Reintentar más tarde
                    if not self.stop_event.is_set():
                         self.task_queue.task_done() # Marcar como hecha incluso si falló para evitar bloqueo

    def start(self):
        """Inicia el orquestador y los hilos trabajadores."""
        logging.info(f"Starting Device Orchestrator with max {MAX_PARALLEL_SESSIONS} sessions.")
        self.stop_event.clear()
        self._update_device_list() # Detectar dispositivos iniciales

        # Llenar la cola inicial con dispositivos idle
        with self.lock:
            for device in self.devices.values():
                if device.status == "idle":
                    self.task_queue.put(device)

        # Crear e iniciar hilos trabajadores
        for i in range(min(MAX_PARALLEL_SESSIONS, len(self.devices))):
            thread = threading.Thread(target=self._worker, name=f"Worker-{i+1}", daemon=True)
            thread.start()
            self.active_threads.append(thread)

        # Podríamos tener un hilo adicional para detectar dispositivos periódicamente
        # O hacerlo bajo demanda cuando la cola se vacíe

    def stop(self):
        """Detiene el orquestador y espera a que los hilos terminen."""
        logging.info("Stopping Device Orchestrator...")
        self.stop_event.set()

        # Esperar a que la cola se vacíe (opcional, podríamos querer terminar tareas activas)
        # self.task_queue.join()

        # Esperar a que los hilos terminen
        for thread in self.active_threads:
            thread.join(timeout=30) # Esperar máximo 30s por hilo
            if thread.is_alive():
                logging.warning(f"Thread {thread.name} did not finish gracefully.")

        logging.info("Device Orchestrator stopped.")
        self.active_threads = []

# --- Ejemplo de función de tarea --- (Esto iría en spotify_actions.py o similar)
def example_task_function(device: Device, proxy: Proxy):
    logging.info(f"Running example task on {device.serial} using proxy {proxy.address}")
    # Simular trabajo con la personalidad del dispositivo
    personality = device.personality
    base_duration = random.uniform(5, 15) # Duración base de la tarea
    task_duration = base_duration * personality.patience

    logging.info(f"[{device.serial}] Personality Patience: {personality.patience:.2f}, Task duration: {task_duration:.2f}s")
    time.sleep(task_duration)

    # Simular fallo ocasional
    if random.random() < 0.1: # 10% de probabilidad de fallo
        raise Exception("Simulated task failure!")

    logging.info(f"[{device.serial}] Example task finished.")
# --- Fin Ejemplo --- 

if __name__ == '__main__':
    print("Device Orchestrator Module - Example Usage")
    print("Please ensure ADB is running and devices are connected/authorized.")

    # Crear archivos dummy para prueba si no existen
    import os
    if not os.path.exists("data"): os.makedirs("data")
    if not os.path.exists("data/proxies.txt"):
        with open("data/proxies.txt", "w") as f:
            # Añadir proxies de prueba (no funcionales, solo para la lógica)
            for i in range(20):
                f.write(f"10.0.0.{i+1}:8080:user{i+1}:pass{i+1}\n")

    proxy_mgr = ProxyManager(proxy_file="data/proxies.txt")
    orchestrator = DeviceOrchestrator(proxy_manager=proxy_mgr, task_function=example_task_function)

    try:
        orchestrator.start()
        # Mantener el script principal vivo mientras los trabajadores operan
        # En una aplicación real, esto podría ser un bucle principal o un servicio
        while True:
            # Podríamos añadir lógica para refrescar dispositivos aquí si no hay un hilo dedicado
            if orchestrator.task_queue.empty() and all(d.status != 'running' for d in orchestrator.devices.values()):
                 logging.info("Task queue is empty and all devices are idle. Checking for new devices or tasks...")
                 orchestrator._update_device_list() # Buscar nuevos dispositivos
                 # Si se detectan nuevos y están idle, se añadirán a la cola automáticamente
                 # Si no hay nada nuevo, esperar un poco
                 if orchestrator.task_queue.empty():
                     logging.info("No new devices or tasks found. Waiting...")

            time.sleep(10) # Esperar antes de volver a chequear

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received. Stopping orchestrator...")
    finally:
        orchestrator.stop()
        print("Orchestrator example finished.")

