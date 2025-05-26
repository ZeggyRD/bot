# -*- coding: utf-8 -*-
"""Punto de entrada principal para ejecutar el modo playlist consolidado del bot Spotify."""

import argparse
import logging
import time
import signal
import sys
import os

# Asegurarse que los módulos del directorio actual (modules) puedan ser importados
# Esto es importante si se ejecuta playlist_mode.py directamente
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.proxy_manager import ProxyManager
from modules.device_orchestrator import DeviceOrchestrator
# La función de tarea real que ejecuta el ciclo de Spotify
from modules.spotify_actions import run_spotify_session 

# Configuración básica de logging para el script principal
# Los logs específicos de dispositivo/acción se manejan en spotify_actions
logging.basicConfig(level=logging.INFO, 
                    format=	'%(asctime)s - %(levelname)s - %(threadName)s - %(message)s	',
                    handlers=[
                        logging.StreamHandler(sys.stdout) # Log a consola
                        # Podríamos añadir un FileHandler aquí para un log general si es necesario
                    ])

# Variable global para el orquestador para poder detenerlo desde el handler de señal
orchestrator = None
stop_requested = False

def signal_handler(sig, frame):
    """Manejador para señales como SIGINT (Ctrl+C)."""
    global orchestrator, stop_requested
    if stop_requested:
        logging.warning("Forcing exit...")
        sys.exit(1) # Salir forzosamente si ya se pidió parar una vez

    logging.warning(f"Signal {sig} received. Initiating graceful shutdown...")
    stop_requested = True
    if orchestrator:
        orchestrator.stop()
    # Dar tiempo para que los hilos terminen
    # time.sleep(5) 
    # sys.exit(0)

def main():
    """Función principal para configurar e iniciar el bot."""
    global orchestrator

    parser = argparse.ArgumentParser(description="OTW Music System - Spotify Playlist Mode")
    # Añadir argumentos si son necesarios en el futuro, ej:
    # parser.add_argument("--accounts", default="data/accounts.txt", help="Path to the accounts file.")
    # parser.add_argument("--proxies", default="data/proxies.txt", help="Path to the proxies file.")
    # parser.add_argument("--workers", type=int, default=10, help="Maximum number of parallel device sessions.")
    
    # Por ahora, la Fase 1 no especifica argumentos CLI más allá de invocar el modo,
    # así que mantenemos los paths y configuraciones hardcodeados o en los módulos.
    args = parser.parse_args()

    logging.info("Initializing OTW Music System - Spotify Playlist Mode...")

    # 1. Inicializar Gestor de Proxies
    # Asume que data/proxies.txt existe en el mismo directorio o subdirectorio data
    proxy_file_path = os.path.join(os.path.dirname(__file__), "data", "proxies.txt")
    proxy_manager = ProxyManager(proxy_file=proxy_file_path)

    # 2. Inicializar Orquestador de Dispositivos
    # Pasamos el gestor de proxies y la función de tarea (run_spotify_session)
    orchestrator = DeviceOrchestrator(proxy_manager=proxy_manager, task_function=run_spotify_session)

    # 3. Registrar manejadores de señales para cierre ordenado
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 4. Iniciar el Orquestador
    try:
        orchestrator.start()

        # 5. Mantener el hilo principal vivo mientras el orquestador trabaja
        logging.info("Orchestrator started. Bot is running. Press Ctrl+C to stop.")
        while not stop_requested:
            # Aquí podríamos añadir lógica periódica si fuera necesario,
            # como verificar el estado general, recargar configuraciones, etc.
            # El orquestador ya tiene su propia lógica interna para manejar dispositivos y tareas.
            
            # Chequear si todos los hilos trabajadores han terminado inesperadamente
            if orchestrator and not any(t.is_alive() for t in orchestrator.active_threads) and not stop_requested:
                logging.warning("All worker threads seem to have stopped unexpectedly. Restarting orchestrator...")
                # Intentar reiniciar (esto podría necesitar lógica más robusta)
                orchestrator.stop() # Asegurar limpieza
                time.sleep(5)
                orchestrator.start()
                if not any(t.is_alive() for t in orchestrator.active_threads):
                     logging.error("Failed to restart worker threads. Exiting.")
                     break # Salir del bucle si el reinicio falla
            
            time.sleep(5) # Esperar un poco antes de la siguiente verificación

    except Exception as e:
        logging.critical(f"An unhandled exception occurred in the main loop: {e}", exc_info=True)
    finally:
        logging.info("Main loop finished. Ensuring orchestrator is stopped.")
        if orchestrator and not stop_requested:
            orchestrator.stop()
        logging.info("OTW Music System shutdown complete.")

if __name__ == "__main__":
    # Crear directorios necesarios si no existen
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(base_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "tests"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "modules"), exist_ok=True)
    # Crear archivos dummy si no existen (para evitar errores iniciales)
    if not os.path.exists(os.path.join(base_dir, "data", "accounts.txt")):
        with open(os.path.join(base_dir, "data", "accounts.txt"), "w") as f: f.write("dummy_user:dummy_pass\n")
    if not os.path.exists(os.path.join(base_dir, "data", "proxies.txt")):
        with open(os.path.join(base_dir, "data", "proxies.txt"), "w") as f: f.write("1.2.3.4:8080:user:pass\n")
        
    main()

