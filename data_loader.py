import os

def accounts():
    """
    Lee cuentas de Spotify desde data/spotify_accounts.txt
    Formato: correo:contraseña
    """
    file_path = os.path.join("data", "spotify_accounts.txt")
    
    if not os.path.exists(file_path):
        print("❌ No se encontró el archivo de cuentas:", file_path)
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    result = []
    for line in lines:
        if ":" in line:
            email, pwd = line.strip().split(":", 1)
            result.append((email, pwd))

    return result


def load_data(folder):
    """
    Lee proxies desde data/proxy_pool.txt
    Formato: ip:port:user:password
    """
    proxies = []
    proxy_path = os.path.join(folder, "proxy_pool.txt")

    if os.path.exists(proxy_path):
        with open(proxy_path, "r", encoding="utf-8") as f:
            proxies = [line.strip() for line in f if line.strip()]
    else:
        print("❌ No se encontró el archivo de proxies:", proxy_path)

    return proxies, [], [], [], []
