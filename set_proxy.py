
import uiautomator2 as u2
import subprocess
import time
import sys
import os

# Agregar la raíz del proyecto al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.data_loader import load_data

def get_connected_devices():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")[1:]
    return [line.split()[0] for line in lines if "device" in line]

def fill_field(d, label, value, max_swipes=3):
    for _ in range(max_swipes):
        if d(text=label).exists:
            break
        d.swipe(0.5, 0.8, 0.5, 0.2)
        time.sleep(0.5)

    if not d(text=label).wait(timeout=5):
        print(f"❌ No se encontró el campo {label}")
        return False

    print(f"⌨️ Escribiendo {label}...")
    d(text=label).click()
    time.sleep(0.4)
    d.clear_text()
    time.sleep(0.3)
    d.send_keys(value)
    time.sleep(0.3)

    if d(text="OK").exists:
        d(text="OK").click()
        time.sleep(0.3)

    return True

def force_turn_on_proxy(d):
    try:
        toggle_btn = d(resourceId="net.typeblog.socks:id/switch_action_button")
        if toggle_btn.exists:
            print("⚡ Intentando encender el proxy...")
            toggle_btn.click()
            time.sleep(2)
            print("✅ Botón presionado para encender proxy.")
        else:
            print("❌ No se encontró el botón de encendido del proxy.")
    except Exception as e:
        print(f"⚠️ Error al intentar encender el proxy: {e}")

def go_to_fast_com(d):
    try:
        print("🌐 Abriendo fast.com para verificar conexión...")
        d.app_start("com.android.chrome")
        time.sleep(5)
        d.send_keys("https://fast.com/es/")
        d.press("enter")
        time.sleep(10)
    except Exception as e:
        print(f"⚠️ Error al abrir fast.com: {e}")

def set_proxy():
    proxies, _, _, _, _ = load_data(".")
    print("🔍 Proxies cargados:")
    for p in proxies:
        print("  -", p)

    if not proxies:
        print("❌ No hay proxies en proxy_pool.txt")
        return

    device_ids = get_connected_devices()
    if not device_ids:
        print("❌ No hay dispositivos conectados")
        return

    for i, device_id in enumerate(device_ids):
        print(f"\n🚀 Configurando proxy en {device_id}…")

        if i >= len(proxies):
            print("⚠️ No hay suficientes proxies para este dispositivo.")
            continue

        try:
            ip, port, user, passwd = proxies[i].strip().split(":")

            d = u2.connect_usb(device_id)
            print(f"✅ Conectado: {device_id} | Proxy: {ip}:{port}")

            d.app_start("net.typeblog.socks")
            time.sleep(3)

            fill_field(d, "Server IP", ip)
            fill_field(d, "Server Port", port)
            fill_field(d, "Username", user)
            fill_field(d, "Password", passwd)

            force_turn_on_proxy(d)
            print(f"✅ Proxy {ip}:{port} aplicado en {device_id}")

            go_to_fast_com(d)

        except Exception as e:
            print(f"❌ Error en {device_id}: {e}")

if __name__ == '__main__':
    set_proxy()
