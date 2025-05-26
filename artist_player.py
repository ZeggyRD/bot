import uiautomator2 as u2
import subprocess
import time
import random
import sys
import os

# Ruta de artistas
ARTIST_PATH = "data/artists.txt"

# Agregar carpeta base del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def get_connected_devices():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")[1:]
    return [line.split()[0] for line in lines if "device" in line]

def load_artists():
    with open(ARTIST_PATH, "r") as f:
        return [line.strip() for line in f if line.strip()]

def human_sleep(min_sec=1.5, max_sec=3.5):
    time.sleep(random.uniform(min_sec, max_sec))

def handle_open_with_dialog(d):
    if d(textContains="Spotify").exists(timeout=5):
        print("📲 Seleccionando Spotify como app predeterminada")
        d(textContains="Spotify").click()
        time.sleep(2)
        if d(textContains="Siempre").exists:
            d(textContains="Siempre").click()
            time.sleep(2)

def open_artist_intent(d, artist_url):
    print("🎤 Abriendo Spotify por intent con URL del artista")
    d.press("home")
    time.sleep(1)
    subprocess.run(["adb", "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", artist_url])
    time.sleep(6)
    handle_open_with_dialog(d)
    time.sleep(6)

def press_play(d):
    try:
        if d(descriptionContains="Play").exists(timeout=8):
            green_play = d(descriptionContains="Play")
            bounds = green_play.info.get('bounds', {})
            if bounds:
                print("▶️ Presionando el botón verde de Play")
                green_play.click()
    except Exception as e:
        print(f"⚠️ Error dando play: {e}")
    time.sleep(2)

def artist_mode():
    print("🎶 Modo Artistas Iniciado")
    artists = load_artists()
    if not artists:
        print("❌ No hay artistas en el archivo")
        return

    devices = get_connected_devices()
    if not devices:
        print("❌ No hay dispositivos conectados")
        return

    device_orders = {device_id: random.sample(artists, len(artists)) for device_id in devices}

    while True:
        for device_id in devices:
            try:
                d = u2.connect_usb(device_id)
                print(f"📱 Dispositivo: {device_id}")

                artist_queue = device_orders[device_id]
                if not artist_queue:
                    artist_queue = random.sample(artists, len(artists))
                    device_orders[device_id] = artist_queue
                artist_url = artist_queue.pop()

                open_artist_intent(d, artist_url)
                time.sleep(5)
                press_play(d)

            except Exception as e:
                print(f"❌ Error con el dispositivo {device_id}: {e}")

        print("⏱️ Esperando antes de reproducir nuevos artistas")
        wait_minutes = random.randint(3, 5)
        time.sleep(wait_minutes * 60)

if __name__ == "__main__":
    artist_mode()
