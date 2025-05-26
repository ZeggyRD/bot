# OTWMusicSystem - Spotify Bot (Phase 1 Refactored)

Este README describe la versión refactorizada del módulo de streaming de Spotify, correspondiente a la Fase 1.

## Descripción General

El sistema ha sido refactorizado para mejorar la modularidad, implementar un comportamiento humano simulado, gestionar proxies de forma avanzada (incluyendo integración con Webshare API) y orquestar múltiples dispositivos ADB para ejecutar sesiones de streaming en paralelo.

Se ha eliminado la funcionalidad de creación de cuentas y resolución de CAPTCHAs, centrándose únicamente en el login mediante UI con cuentas existentes y la ejecución de un ciclo de streaming consolidado.

## Estructura de Módulos Principales

- `playlist_mode.py`: Punto de entrada principal para iniciar el bot.
- `modules/`: Directorio que contiene los componentes lógicos:
    - `human_behavior.py`: Define la personalidad del dispositivo y simula interacciones humanas (retrasos, clics, scrolls).
    - `proxy_manager.py`: Gestiona el pool de proxies (carga desde `data/proxies.txt`, rotación, chequeo de salud, integración Webshare API).
    - `device_orchestrator.py`: Detecta dispositivos ADB, gestiona un pool de hilos para sesiones paralelas y asigna proxies.
    - `spotify_actions.py`: Contiene la lógica simulada para interactuar con la UI de Spotify (login, abrir URLs, reproducir playlists/artistas/pistas) y el logging específico por dispositivo.
- `data/`: Contiene archivos de datos:
    - `accounts.txt`: Lista de cuentas de Spotify (formato: `usuario:contraseña`).
    - `proxies.txt`: Lista de proxies (formato: `ip:puerto:usuario:contraseña` o `ip:puerto`).
- `logs/`: Directorio donde se guardan los logs JSON por dispositivo, rotados diariamente.
- `tests/`: Directorio para futuras pruebas unitarias (actualmente vacío).

## Requisitos

- Python 3.x
- ADB (Android Debug Bridge) instalado y en el PATH del sistema.
- Dispositivos Android conectados vía USB con depuración USB habilitada y autorizada.
- Librerías Python (instalar con `pip install requests`, aunque idealmente se usaría un `requirements.txt` completo).

## Uso

1.  **Configurar Cuentas y Proxies:**
    - Edite el archivo `data/accounts.txt` y añada las credenciales de las cuentas de Spotify, una por línea (`usuario:contraseña`).
    - Edite el archivo `data/proxies.txt` y añada los proxies, uno por línea (`ip:puerto:usuario:contraseña` o `ip:puerto`).

2.  **Ejecutar el Bot:**
    - Abra una terminal o símbolo del sistema.
    - Navegue hasta el directorio `OTW_MUSIC_SYSTEM`.
    - Ejecute el script principal:
      ```bash
      python playlist_mode.py
      ```

3.  **Monitorización:**
    - El bot mostrará logs generales en la consola.
    - Los logs detallados de cada sesión de dispositivo se guardarán en archivos JSON dentro de la carpeta `logs/`, nombrados como `device_<serial>_<fecha>.log.json`.

4.  **Detener el Bot:**
    - Presione `Ctrl+C` en la terminal donde se está ejecutando el bot. El sistema intentará un cierre ordenado.

## Pruebas

Actualmente, las interacciones con la UI de Spotify y ADB están simuladas dentro de `spotify_actions.py` y `device_orchestrator.py`. Se requiere implementar la lógica real utilizando una librería como `uiautomator2` o comandos ADB.

El directorio `tests/` está preparado para añadir pruebas unitarias (especialmente mock-ADB) para validar:
- Asignación y rotación de proxies.
- Flujo de login simulado.
- Interacciones UI simuladas.
- Lógica de retrasos y recuperación de errores.

## Notas Importantes (Fase 1)

- La integración con Webshare API (`proxy_manager.py`) utiliza la clave proporcionada y realiza llamadas reales para chequeo y obtención de proxies.
- El logging por dispositivo está implementado para generar archivos JSON en `logs/`.
- El manejo de errores y reintentos está incorporado en `device_orchestrator.py` y `spotify_actions.py`.
- El comportamiento humano (retrasos, probabilidades) se gestiona mediante `DevicePersonality` en `human_behavior.py`.
- **No** se incluye código de creación de cuentas ni resolución de CAPTCHA.

