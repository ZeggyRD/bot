# OTW Music System - Estructura de Directorios

Este documento describe la estructura de directorios optimizada para el sistema OTW Music System.

## Estructura Principal

```
OTW_MUSIC_SYSTEM/
├── main.py                  # Punto de entrada principal del sistema
├── requirements.txt         # Dependencias del proyecto
├── README.md                # Documentación principal
├── test_runner.py           # Script para ejecutar pruebas automatizadas
├── config/                  # Archivos de configuración
│   └── config.json          # Configuración general del sistema
├── data/                    # Datos necesarios para el funcionamiento
│   ├── accounts.txt         # Cuentas de Spotify
│   ├── proxies.txt          # Lista de proxies
│   ├── tracks.txt           # URLs de tracks para reproducir
│   ├── playlists.txt        # URLs de playlists para reproducir
│   └── artists.txt          # URLs de artistas para reproducir
├── docs/                    # Documentación detallada
│   ├── manual.md            # Manual de usuario
│   ├── test_plan.md         # Plan de pruebas
│   └── api_reference.md     # Referencia de API interna
├── logs/                    # Directorio para archivos de log
├── modules/                 # Módulos principales del sistema
│   ├── __init__.py
│   ├── account_creator.py   # Creación de cuentas
│   ├── account_manager.py   # Gestión de cuentas
│   ├── android_device.py    # Control de dispositivos Android
│   ├── human_behavior.py    # Simulación de comportamiento humano
│   └── login_manager.py     # Gestión de inicio de sesión
├── scripts/                 # Scripts ejecutables
│   ├── artist_player.py     # Reproductor de artistas
│   ├── data_loader.py       # Cargador de datos
│   ├── install_required_apps.py # Instalador de aplicaciones requeridas
│   ├── playlist_player.py   # Reproductor de playlists
│   ├── set_proxy.py         # Configurador de proxies
│   ├── spotify_login.py     # Login en Spotify
│   └── track_player.py      # Reproductor de tracks
├── screenshots/             # Capturas de pantalla durante la ejecución
├── test_results/            # Resultados de pruebas automatizadas
└── apks/                    # APKs necesarios para el funcionamiento
    └── SocksDroid.apk       # APK de SocksDroid para proxies
```

## Descripción de Directorios

### Directorio Raíz
Contiene los archivos principales del sistema, incluyendo el punto de entrada (`main.py`), requisitos (`requirements.txt`) y documentación principal (`README.md`).

### config/
Almacena archivos de configuración del sistema, como API keys, configuraciones de conexión, etc.

### data/
Contiene los archivos de datos necesarios para el funcionamiento del sistema:
- `accounts.txt`: Lista de cuentas de Spotify (formato: email:password)
- `proxies.txt`: Lista de proxies (formato: ip:puerto:usuario:contraseña)
- `tracks.txt`: URLs de tracks para reproducir
- `playlists.txt`: URLs de playlists para reproducir
- `artists.txt`: URLs de artistas para reproducir

### docs/
Documentación detallada del sistema:
- `manual.md`: Manual de usuario con instrucciones detalladas
- `test_plan.md`: Plan de pruebas y resultados
- `api_reference.md`: Referencia de la API interna del sistema

### logs/
Directorio donde se almacenan los archivos de log generados durante la ejecución del sistema.

### modules/
Contiene los módulos principales del sistema:
- `account_creator.py`: Módulo para crear cuentas de Spotify
- `account_manager.py`: Gestión de cuentas existentes
- `android_device.py`: Control de dispositivos Android mediante ADB
- `human_behavior.py`: Simulación de comportamiento humano
- `login_manager.py`: Gestión de inicio de sesión en Spotify

### scripts/
Scripts ejecutables para diferentes funcionalidades:
- `artist_player.py`: Reproductor de artistas
- `data_loader.py`: Cargador de datos desde archivos
- `install_required_apps.py`: Instalador de aplicaciones requeridas
- `playlist_player.py`: Reproductor de playlists
- `set_proxy.py`: Configurador de proxies
- `spotify_login.py`: Login en Spotify
- `track_player.py`: Reproductor de tracks

### screenshots/
Almacena capturas de pantalla tomadas durante la ejecución del sistema para verificación y debugging.

### test_results/
Contiene los resultados de las pruebas automatizadas ejecutadas con `test_runner.py`.

### apks/
Almacena los archivos APK necesarios para el funcionamiento del sistema:
- `SocksDroid.apk`: Aplicación para configurar proxies en dispositivos Android
