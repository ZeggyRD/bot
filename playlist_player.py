import uiautomator2 as u2
import subprocess
import time
import random
import sys
import os

# Ruta de playlists
PLAYLIST_PATH = "data/playlists.txt"
FAVORITE_ARTISTS = ["Cerame", "Kairo la Sinfonia", "G Many", "Zeggy Beats"]

# Agregar carpeta base del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def get_connected_devices():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")[1:]
    return [line.split()[0] for line in lines if "device" in line]

def load_playlists():
    with open(PLAYLIST_PATH, "r") as f:
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

def open_playlist_intent(d, playlist_url):
    print("🎵 Abriendo Spotify por intent con URL")
    d.press("home")
    time.sleep(1)
    subprocess.run(["adb", "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", playlist_url])
    time.sleep(6)
    handle_open_with_dialog(d)
    time.sleep(6)

def like_playlist_if_needed(d):
    try:
        if d(descriptionContains="Add to Your Library").exists(timeout=5):
            d(descriptionContains="Add to Your Library").click()
            print("❤️ Playlist guardada")
    except Exception as e:
        print(f"⚠️ Error al dar like a la playlist: {e}")
    time.sleep(2)

def activate_shuffle(d):
    try:
        if d(descriptionContains="Shuffle").exists(timeout=6):
            d(descriptionContains="Shuffle").click()
            time.sleep(3)
            if d(textContains="Smart Shuffle").exists(timeout=3):
                d(textContains="Shuffle").click()
                print("🔀 Shuffle activado (modo simple)")
            else:
                print("🔀 Shuffle activado")
    except Exception as e:
        print(f"⚠️ Error activando shuffle: {e}")
    time.sleep(2)

def press_play(d):
    try:
        # Busca específicamente el botón VERDE de Play
        if d(descriptionContains="Play").exists(timeout=6):
            green_play = d(descriptionContains="Play")
            bounds = green_play.info.get('bounds', {})
            if bounds:
                print("▶️ Presionando el botón verde de Play")
                green_play.click()
    except Exception as e:
        print(f"⚠️ Error dando play: {e}")
    time.sleep(2)

def scroll_and_interact(d):
    print("👆 Explorando como fan")
    for _ in range(random.randint(3, 5)):
        d.swipe(0.5, 0.9, 0.5, 0.2)
        time.sleep(random.uniform(2, 4))
        if d(descriptionContains="Like").exists:
            d(descriptionContains="Like").click_exists(timeout=2)
            print("💚 Like a canción")
        time.sleep(random.uniform(2, 5))

def playlist_mode():
    print("🎶 Modo Playlist Iniciado")
    playlists = load_playlists()
    if not playlists:
        print("❌ No hay playlists en el archivo")
        return

    devices = get_connected_devices()
    if not devices:
        print("❌ No hay dispositivos conectados")
        return

    device_orders = {device_id: random.sample(playlists, len(playlists)) for device_id in devices}

    while True:
        for device_id in devices:
            try:
                d = u2.connect_usb(device_id)
                print(f"📱 Dispositivo: {device_id}")

                playlist_queue = device_orders[device_id]
                if not playlist_queue:
                    playlist_queue = random.sample(playlists, len(playlists))
                    device_orders[device_id] = playlist_queue
                playlist_url = playlist_queue.pop()

                open_playlist_intent(d, playlist_url)
                time.sleep(5)

                action_order = random.sample([like_playlist_if_needed, activate_shuffle, press_play], 3)
                for action in action_order:
                    action(d)
                    human_sleep(1, 3)

                print("🧠 Simulando comportamiento humano por 10 minutos")
                scroll_and_interact(d)
                time.sleep(random.randint(600, 660))

                print("🧘‍♂️ Esperando 30 minutos antes de repetir...")
                time.sleep(random.randint(1800, 2100))

            except Exception as e:
                print(f"❌ Error con el dispositivo {device_id}: {e}")

if __name__ == "__main__":
    playlist_mode()
