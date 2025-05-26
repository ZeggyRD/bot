import uiautomator2 as u2
import subprocess
import time
import sys
import os
import threading  # Import threading module

# Add the root of the project to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.data_loader import load_data

def get_connected_devices():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")[1:]
    return [line.split()[0] for line in lines if "device" in line]

def fill_field(d, label, value, max_swipes=3):
    """Ensure that fields are filled properly"""
    for _ in range(max_swipes):
        if d(text=label).exists:
            break
        d.swipe(0.5, 0.8, 0.5, 0.2)  # Swipe up to reveal fields
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

def launch_ping_test_app(d):
    try:
        print("🌐 Intentando abrir la app Ping Test...")

        # Reemplaza com.HBuild.PingTest con el package name real de la app Ping Test
        d.app_start("com.HBuild.PingTest")  # Iniciar la app Ping Test
        time.sleep(5)  # Esperar que la app se inicie

        # Verificar si la app se abrió correctamente
        if d(text="Ping Test").exists:
            print("✅ La app Ping Test se abrió exitosamente.")
        else:
            print("❌ La app Ping Test no se ha abierto. Reintentando...")
            d.app_start("com.HBuild.PingTest")  # Intentar abrirla nuevamente
            time.sleep(10)

            if d(text="Ping Test").exists:
                print("✅ La app Ping Test se abrió exitosamente después del reintento.")
            else:
                print("❌ No se pudo abrir la app Ping Test después del reintento.")

    except Exception as e:
        print(f"⚠️ Error al abrir Ping Test: {e}")
        print("🔴 Reintentando...")

        # Si todo falla, forzamos la entrada nuevamente
        d.app_start("com.HBuild.PingTest")  # Forzar la apertura de la app
        time.sleep(10)  # Esperar más tiempo
        print("🔴 Intento final para abrir Ping Test.")

def set_proxy_for_device(device_id, proxy, proxies):
    """Set up proxy for a given device"""
    ip, port, user, passwd = proxy.strip().split(":")
    d = u2.connect_usb(device_id)
    print(f"✅ Conectado: {device_id} | Proxy: {ip}:{port}")

    d.app_start("net.typeblog.socks")
    time.sleep(3)

    # Fill the proxy fields
    fill_field(d, "Server IP", ip)
    fill_field(d, "Server Port", port)
    fill_field(d, "Username", user)
    fill_field(d, "Password", passwd)

    force_turn_on_proxy(d)
    print(f"✅ Proxy {ip}:{port} aplicado en {device_id}")

    # Launch the Ping Test app instead of fast.com
    launch_ping_test_app(d)

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

    threads = []
    for i, device_id in enumerate(device_ids):
        print(f"\n🚀 Configurando proxy en {device_id}…")

        if i >= len(proxies):
            print("⚠️ No hay suficientes proxies para este dispositivo.")
            continue

        # Create a thread for each device to run concurrently
        thread = threading.Thread(target=set_proxy_for_device, args=(device_id, proxies[i], proxies))
        threads.append(thread)

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

if __name__ == '__main__':
    set_proxy()