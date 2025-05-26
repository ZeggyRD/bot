# spotify_login.py
import subprocess
import time
import random
import threading
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from data_loader import accounts

def tap(device, x, y, pause=0.5):
    subprocess.run(["adb", "-s", device, "shell", "input", "tap", str(int(x)), str(int(y))])
    time.sleep(pause)

def clear_field(device):
    subprocess.run(["adb", "-s", device, "shell", "input", "keyevent", "123"])  # mover al final
    for _ in range(15):
        subprocess.run(["adb", "-s", device, "shell", "input", "keyevent", "67"])  # borrar
    time.sleep(0.2)

def type_text(device, text):
    subprocess.run(["adb", "-s", device, "shell", "input", "text", text])
    time.sleep(0.3)

def login(device, email, pwd):
    print(f"\n📲 [{device}] Login con {email}")
    
    # 1. Abrir Spotify
    subprocess.run([
        "adb", "-s", device, "shell", "monkey",
        "-p", "com.spotify.music",
        "-c", "android.intent.category.LAUNCHER", "1"
    ])
    time.sleep(3)

    # 2. Tap Log In
    tap(device, 236, 780, pause=1)

    # 3. Tap Continue with email
    tap(device, 238, 538, pause=1)

    # 4. Escribir email
    tap(device, 169, 223, pause=0.5)
    clear_field(device)
    type_text(device, email)

    # 5. Tap Next
    tap(device, 247, 522, pause=1)

    # 6. Escribir password
    tap(device, 207, 389, pause=0.5)
    clear_field(device)
    type_text(device, pwd)

    # 7. Tap Log In final
    tap(device, 247, 522, pause=3)

    print(f"✅ [{device}] Login intentado con {email}")

def get_devices():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")[1:]  # omit header
    devices = [line.split()[0] for line in lines if "device" in line]
    return devices

def main():
    device_list = get_devices()
    account_list = accounts()

    if not device_list:
        print("❌ No hay dispositivos conectados")
        return
    if not account_list:
        print("❌ No hay cuentas disponibles")
        return

    threads = []
    for i, device in enumerate(device_list):
        if i >= len(account_list):
            print(f"⚠️ No hay suficientes cuentas para {device}")
            continue

        email, pwd = account_list[i]
        t = threading.Thread(target=login, args=(device, email, pwd))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
