#!/usr/bin/env python3
"""
playlist_mode.py

Central entrypoint: run Spotify sessions across all devices in parallel.
"""

import os
from concurrent.futures import ThreadPoolExecutor

from core.device_manager import DeviceManager
from core.account_orchestrator import AccountOrchestrator
from core.spotify_orchestration import run_spotify_session

DATA_DIR      = "data"
PLAYLIST_FILE = os.path.join(DATA_DIR, "playlists.txt")
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.txt")
PROXIES_FILE  = os.path.join(DATA_DIR, "proxies.txt")

def load_list(path):
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def playlist_mode():
    # 1) Load inputs
    playlist_urls = load_list(PLAYLIST_FILE)
    accounts      = load_list(ACCOUNTS_FILE)
    proxies       = load_list(PROXIES_FILE)

    # 2) Init managers
    device_manager  = DeviceManager()
    devices         = device_manager.discover_devices()
    account_manager = AccountOrchestrator(accounts, proxies)

    # 3) Worker function
    def worker(device):
        # Assign next account & proxy
        account_email, proxy = account_manager.next_account_and_proxy()
        personality         = account_manager.load_personality(account_email)

        # Run the full 4-phase Spotify session
        return run_spotify_session(
            device=device,
            personality=personality,
            account_email=account_email,
            spotify_package_name="com.spotify.music",
            playlist_urls=playlist_urls
        )

    # 4) Execute in parallel
    with ThreadPoolExecutor(max_workers=len(devices)) as executor:
        results = list(executor.map(worker, devices))

    # 5) Summary
    successes = sum(1 for ok in results if ok)
    failures  = len(results) - successes
    print(f"✅ {successes} succeeded, ❌ {failures} failed out of {len(devices)} devices.")

if __name__ == "__main__":
    playlist_mode()
