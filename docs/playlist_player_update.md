# Documentación de Actualización: playlist_player.py

## Resumen de Cambios

El módulo `playlist_player.py` ha sido completamente actualizado para cumplir con los requisitos de reproducción real, bucle infinito, y comportamiento humano simulado en dispositivos Android. A continuación se detallan los cambios realizados y las nuevas funcionalidades implementadas.

## Cambios Principales

### 1. Sistema de Logging Mejorado
- Implementación de logging estructurado con rotación de archivos
- Registro detallado de todas las acciones y errores
- Almacenamiento de logs en la carpeta `/logs` con timestamp

### 2. Reproducción Real Funcional
- Apertura de playlists mediante intent de Android:
  ```python
  subprocess.run([
      "adb", "-s", device_id, "shell", 
      "am", "start", "-a", "android.intent.action.VIEW", 
      "-d", playlist_url
  ], check=True)
  ```
- Simulación de taps en coordenadas específicas para botones:
  - Botón PLAY: `width // 2, height // 3`
  - Botón Seguir: `width - 50, 150`

### 3. Detección de Spotify en Primer Plano
- Reemplazo del comando con `grep` por una solución compatible con Windows:
  ```python
  result = subprocess.run(
      ["adb", "-s", device_id, "shell", "dumpsys", "activity", "activities"],
      capture_output=True, 
      text=True
  )
  match = re.search(r'mResumedActivity.*?(com\.spotify\.music|com\.spotify\.music\.clone\d*)', result.stdout)
  ```

### 4. Captura de Screenshots para Verificación
- Implementación de función `take_screenshot()` para verificar visualmente el estado
- Almacenamiento de capturas en la carpeta `/screenshots` con timestamp

### 5. Rotación de Playlists Sin Repetición
- Sistema que asegura que no se repita el mismo playlist hasta agotar la lista
- Reinicio con nuevo orden aleatorio cuando se han reproducido todos los playlists
- Seguimiento independiente por dispositivo

### 6. Simulación de Comportamiento Humano
- Interacciones aleatorias durante la reproducción:
  - Scroll hacia arriba y abajo
  - Taps en posiciones de "like"
  - Esperas de duración variable
- Integración con el módulo `human_behavior` si está disponible
- Fallback a comportamiento básico si el módulo no está disponible

### 7. Bucle Infinito Robusto
- Implementación de bucle eterno con manejo de excepciones
- Duración aleatoria de reproducción entre 7 y 15 minutos
- Continuación del bucle incluso si hay errores en un dispositivo específico

## Estructura del Código

El código está organizado en funciones modulares:

- `get_connected_devices()`: Detecta dispositivos Android conectados
- `load_playlists()`: Carga la lista de playlists desde el archivo
- `human_sleep()`: Genera pausas aleatorias para simular comportamiento humano
- `take_screenshot()`: Captura la pantalla del dispositivo
- `get_screen_dimensions()`: Obtiene las dimensiones de la pantalla
- `handle_open_with_dialog()`: Maneja el diálogo de "Abrir con" si aparece
- `is_spotify_foreground()`: Verifica si Spotify está en primer plano
- `open_playlist_intent()`: Abre una playlist mediante intent
- `tap_play_button()`: Toca el botón de reproducción
- `tap_follow_button()`: Toca el botón de seguir playlist
- `simulate_human_interaction()`: Simula interacción humana durante la reproducción
- `playlist_mode()`: Función principal que implementa el bucle de reproducción

## Uso del Módulo

Para ejecutar el módulo directamente:

```bash
python scripts/playlist_player.py
```

Para integrarlo con el sistema principal:

```python
from scripts.playlist_player import playlist_mode
playlist_mode()
```

## Requisitos

- Dispositivo Android conectado por USB con depuración habilitada
- ADB instalado y configurado
- Spotify instalado en el dispositivo
- Archivo de playlists en `data/playlists.txt` con URLs de Spotify

## Notas Adicionales

- El módulo ahora es compatible con Windows al no depender de comandos Unix como `grep`
- Se ha mejorado la robustez ante errores para garantizar la operación continua
- La simulación de comportamiento humano es más natural y variada
- Se mantiene un registro detallado de todas las acciones para facilitar el diagnóstico
