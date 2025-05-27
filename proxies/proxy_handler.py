# -*- coding: utf-8 -*-
"""Módulo para gestionar el pool de proxies, incluyendo carga, rotación y chequeos de salud."""

import time
import threading
import requests
import logging
from datetime import datetime, timedelta
from core.config import WEBSHARE_API_KEY # Import from config

# Setup logger
logger = logging.getLogger("ProxyHandler")
if not logger.handlers: # Ensure handlers are not added multiple times if module is reloaded
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) # Or logging.DEBUG for more verbosity

# Constantes
# WEBSHARE_API_KEY = "m9je2zfmnjbvgo6ye5zvmho0o7nxqizo8wk94sel" # Clave API proporcionada - REMOVED
WEBSHARE_API_URL = "https://proxy.webshare.io/api/v2/proxy/list/"
PROXY_CHECK_URL = "https://httpbin.org/ip" # URL para verificar si el proxy funciona
PROXY_CHECK_TIMEOUT = 10 # Segundos
MIN_PROXY_POOL_PERCENTAGE = 0.20 # 20%
PROXY_REUSE_DELAY_SECONDS = 60 * 5 # Esperar 5 minutos antes de reusar un proxy (ejemplo)

class Proxy:
    """Representa un proxy individual con su estado."""
    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.address = f"{host}:{port}"
        self.auth_string = f"{user}:{password}" if user and password else None
        self.proxy_url = f"http://{self.auth_string}@{self.address}" if self.auth_string else f"http://{self.address}"
        self.in_use = False
        self.last_used = None
        self.last_checked = None
        self.healthy = None # None = no chequeado, True = sano, False = fallido
        self.fail_count = 0

    def mark_as_used(self):
        self.in_use = True
        self.last_used = datetime.now()

    def mark_as_free(self):
        self.in_use = False

    def __str__(self):
        return f"Proxy({self.address}, Healthy: {self.healthy}, InUse: {self.in_use})"

class ProxyManager:
    """Gestiona un pool de proxies, incluyendo carga, rotación, chequeos y API de Webshare."""
    def __init__(self, proxy_file="data/proxies.txt"):
        self.proxy_file = proxy_file
        self.proxies = []
        self.lock = threading.Lock()
        self.load_proxies()
        self.current_index = 0 # Para rotación round-robin
        self.min_pool_size = 0
        # Iniciar hilo para chequeo de salud y pre-obtención (opcional, podría hacerse bajo demanda)
        # self.health_check_thread = threading.Thread(target=self._background_tasks, daemon=True)
        # self.health_check_thread.start()

    def load_proxies(self):
        """Carga proxies desde el archivo especificado."""
        logger.info(f"Loading proxies from {self.proxy_file}") # Changed logging to logger
        loaded_count = 0
        try:
            with open(self.proxy_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(':')
                    if len(parts) == 4:
                        host, port, user, password = parts
                        self.proxies.append(Proxy(host, int(port), user, password))
                        loaded_count += 1
                    elif len(parts) == 2: # ip:port sin autenticación
                        host, port = parts
                        self.proxies.append(Proxy(host, int(port), None, None))
                        loaded_count += 1
                    else:
                        logger.warning(f"Skipping invalid proxy line: {line}") # Changed logging to logger
            logger.info(f"Loaded {loaded_count} proxies.") # Changed logging to logger
            self.min_pool_size = int(len(self.proxies) * MIN_PROXY_POOL_PERCENTAGE)
        except FileNotFoundError:
            logger.error(f"Proxy file not found: {self.proxy_file}") # Changed logging to logger
        except Exception as e:
            logger.error(f"Error loading proxies: {e}") # Changed logging to logger

    def _fetch_webshare_proxies(self, limit=50):
        """Obtiene proxies desde la API de Webshare."""
        if not WEBSHARE_API_KEY or WEBSHARE_API_KEY == "YOUR_API_KEY_HERE":
            logger.warning("Webshare API key is not configured or is a placeholder. Skipping Webshare proxy fetching.")
            return []
            
        logger.info("Fetching new proxies from Webshare API...") # Changed logging to logger
        headers = {"Authorization": f"Token {WEBSHARE_API_KEY}"}
        params = {"limit": limit}
        new_proxies = []
        try:
            response = requests.get(WEBSHARE_API_URL, headers=headers, params=params, timeout=20)
            response.raise_for_status() # Lanza excepción para códigos 4xx/5xx
            data = response.json()
            for p in data.get("results", []):
                if p.get("valid") and p.get("proxy_address") and p.get("port"):
                    # Asume que la API devuelve proxies con usuario/contraseña si están configurados
                    new_proxy = Proxy(p["proxy_address"], p["port"], p.get("username"), p.get("password"))
                    # Evitar duplicados basados en la dirección
                    if not any(existing_proxy.address == new_proxy.address for existing_proxy in self.proxies):
                        new_proxies.append(new_proxy)
                        logger.info(f"Fetched new proxy from Webshare: {new_proxy.address}") # Changed logging to logger
            logger.info(f"Fetched {len(new_proxies)} new unique proxies from Webshare.") # Changed logging to logger
            return new_proxies
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching proxies from Webshare API: {e}") # Changed logging to logger
            return []
        except Exception as e:
            logger.error(f"Unexpected error processing Webshare API response: {e}") # Changed logging to logger
            return []

    def _check_proxy_health(self, proxy: Proxy):
        """Verifica la salud de un proxy individual."""
        logger.debug(f"Checking health for proxy: {proxy.address}") # Changed logging to logger
        proxy_dict = {
            "http": proxy.proxy_url,
            "https": proxy.proxy_url
        }
        try:
            response = requests.get(PROXY_CHECK_URL, proxies=proxy_dict, timeout=PROXY_CHECK_TIMEOUT)
            response.raise_for_status()
            # Podríamos verificar si la IP devuelta es la del proxy, pero la comprobación de estado es suficiente
            # print(response.json())
            proxy.healthy = True
            proxy.fail_count = 0
            logger.debug(f"Proxy {proxy.address} is healthy.") # Changed logging to logger
        except requests.exceptions.RequestException as e:
            proxy.healthy = False
            proxy.fail_count += 1
            logger.warning(f"Proxy {proxy.address} check failed: {e}") # Changed logging to logger
        except Exception as e:
            proxy.healthy = False
            proxy.fail_count += 1
            logger.error(f"Unexpected error checking proxy {proxy.address}: {e}") # Changed logging to logger
        finally:
            proxy.last_checked = datetime.now()

    def _maintain_pool(self):
        """Realiza chequeos de salud y obtiene nuevos proxies si es necesario."""
        with self.lock:
            healthy_proxies = [p for p in self.proxies if p.healthy and not p.in_use]
            num_healthy_available = len(healthy_proxies)

            logger.info(f"Maintaining proxy pool. Total: {len(self.proxies)}, Healthy & Available: {num_healthy_available}, Min Required: {self.min_pool_size}") # Changed logging to logger

            # Obtener nuevos si estamos por debajo del mínimo
            if num_healthy_available < self.min_pool_size:
                logger.warning(f"Healthy proxy pool ({num_healthy_available}) is below minimum ({self.min_pool_size}). Fetching more...") # Changed logging to logger
                new_proxies = self._fetch_webshare_proxies()
                if new_proxies:
                    self.proxies.extend(new_proxies)
                    self.min_pool_size = int(len(self.proxies) * MIN_PROXY_POOL_PERCENTAGE)
                    logger.info(f"Added {len(new_proxies)} new proxies. Total pool size: {len(self.proxies)}") # Changed logging to logger
                else:
                    logger.error("Failed to fetch new proxies from Webshare.") # Changed logging to logger

            # Chequear salud de proxies no chequeados o viejos (ej. cada hora)
            now = datetime.now()
            for proxy in self.proxies:
                if proxy.healthy is None or (proxy.last_checked and now - proxy.last_checked > timedelta(hours=1)):
                    self._check_proxy_health(proxy)
                    time.sleep(0.1) # Pequeña pausa entre chequeos

            # Eliminar proxies que fallan consistentemente (ej. > 5 fallos)
            initial_count = len(self.proxies)
            self.proxies = [p for p in self.proxies if p.fail_count <= 5]
            removed_count = initial_count - len(self.proxies)
            if removed_count > 0:
                logger.warning(f"Removed {removed_count} consistently failing proxies.") # Changed logging to logger
                self.min_pool_size = int(len(self.proxies) * MIN_PROXY_POOL_PERCENTAGE)

    def get_proxy(self) -> Proxy | None:
        """Obtiene el siguiente proxy disponible usando rotación round-robin."""
        with self.lock:
            if not self.proxies:
                logger.error("Proxy pool is empty.") # Changed logging to logger
                return None

            # Intentar mantener el pool antes de buscar
            self._maintain_pool()

            initial_index = self.current_index
            now = datetime.now()

            while True:
                proxy = self.proxies[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.proxies)

                # Verificar si está disponible y saludable
                is_available = not proxy.in_use
                is_healthy = proxy.healthy is True # Solo usar si se confirmó saludable
                is_reusable = proxy.last_used is None or (now - proxy.last_used > timedelta(seconds=PROXY_REUSE_DELAY_SECONDS))

                if is_available and is_healthy and is_reusable:
                    proxy.mark_as_used()
                    logger.info(f"Assigning proxy: {proxy.address}") # Changed logging to logger
                    return proxy

                # Si hemos dado una vuelta completa y no encontramos nada
                if self.current_index == initial_index:
                    logger.warning("No suitable proxy available currently. All might be in use, unhealthy, or recently used.") # Changed logging to logger
                    # Podríamos esperar un poco y reintentar, o devolver None
                    # Intentar obtener nuevos proxies si fallamos aquí
                    logger.info("Attempting to fetch new proxies due to unavailability...") # Changed logging to logger
                    new_proxies = self._fetch_webshare_proxies()
                    if new_proxies:
                        self.proxies.extend(new_proxies)
                        self.min_pool_size = int(len(self.proxies) * MIN_PROXY_POOL_PERCENTAGE)
                        logger.info(f"Added {len(new_proxies)} new proxies. Retrying get_proxy().") # Changed logging to logger
                        # Reiniciar búsqueda desde el principio después de añadir
                        self.current_index = 0
                        initial_index = 0 # Resetear para evitar loop infinito si los nuevos tampoco sirven
                        continue # Reintentar la búsqueda
                    else:
                        logger.error("Failed to fetch new proxies. No proxy assigned.") # Changed logging to logger
                        return None # No hay proxies disponibles ni pudimos obtener nuevos

    def release_proxy(self, proxy: Proxy, success: bool):
        """Libera un proxy y actualiza su estado basado en el éxito de la operación."""
        with self.lock:
            proxy.mark_as_free()
            if not success:
                logger.warning(f"Operation failed with proxy {proxy.address}. Marking for re-check.") # Changed logging to logger
                # Marcar como no saludable para forzar un chequeo la próxima vez
                proxy.healthy = None
                proxy.fail_count += 1
            else:
                # Si tuvo éxito, reseteamos el contador de fallos (si aplica)
                # proxy.fail_count = 0 # Opcional: resetear solo si estaba fallando antes
                pass
            logger.info(f"Released proxy: {proxy.address}") # Changed logging to logger

    # def _background_tasks(self):
    #     """Tareas periódicas de mantenimiento en segundo plano."""
    #     while True:
    #         try:
    #             self._maintain_pool()
    #         except Exception as e:
    #             logger.error(f"Error in background proxy maintenance: {e}") # Changed logging to logger
    #         time.sleep(60 * 10) # Ejecutar cada 10 minutos

# Ejemplo de uso
if __name__ == '__main__':
    # Crear archivos dummy para prueba
    with open("data/proxies.txt", "w") as f:
        f.write("1.1.1.1:8080:user1:pass1\n")
        f.write("2.2.2.2:8080:user2:pass2\n")
        f.write("3.3.3.3:8080 # Comentario\n") # Proxy sin auth
        f.write("4.4.4.4:9000:user4:pass4\n")

    manager = ProxyManager(proxy_file="data/proxies.txt")

    # Simular obtención y liberación de proxies
    proxy1 = manager.get_proxy()
    if proxy1:
        print(f"Got proxy 1: {proxy1}")
        # Simular uso exitoso
        time.sleep(2)
        manager.release_proxy(proxy1, success=True)
    else:
        print("Failed to get proxy 1")

    proxy2 = manager.get_proxy()
    if proxy2:
        print(f"Got proxy 2: {proxy2}")
        # Simular uso fallido
        time.sleep(1)
        manager.release_proxy(proxy2, success=False)
    else:
        print("Failed to get proxy 2")

    proxy3 = manager.get_proxy()
    if proxy3:
        print(f"Got proxy 3: {proxy3}")
        manager.release_proxy(proxy3, success=True)
    else:
        print("Failed to get proxy 3")

    proxy4 = manager.get_proxy()
    if proxy4:
        print(f"Got proxy 4: {proxy4}")
        manager.release_proxy(proxy4, success=True)
    else:
        print("Failed to get proxy 4")

    # Intentar obtener uno más (debería rotar)
    proxy5 = manager.get_proxy()
    if proxy5:
        print(f"Got proxy 5 (rotated): {proxy5}")
        manager.release_proxy(proxy5, success=True)
    else:
        # Podría fallar si el chequeo de salud inicial falló para todos
        # o si el delay de reuso es muy largo
        print("Failed to get proxy 5")

    print("\nCurrent Pool Status:")
    for p in manager.proxies:
        print(f"  - {p}")

