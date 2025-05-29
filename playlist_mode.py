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
from proxies.proxy_handler import ProxyHandler
from personalities.device_personality import PersonalityProfile

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
    # AccountOrchestrator reads accounts/proxies itself
    account_manager = AccountOrchestrator()

    # 2) Init DeviceManager
    device_manager = DeviceManager()
    device_manager.update_devices()           # scan ADB devices
    devices = device_manager.get_active_devices()

    # 3) Worker function
    def worker(device):
        # Assign per-device account & proxy
        account_email, account_password = account_manager.get_account_for_session(device.device_id)
        proxy = ProxyHandler().get_proxy()

        # Load personality profile
        username = account_email.split('@')[0]
        personality = PersonalityProfile(username=username, profile_directory='personalities/')

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
    failures = len(results) - successes
    print(f"✅ {successes} succeeded, ❌ {failures} failed out of {len(devices)} devices.")

if __name__ == "__main__":
    playlist_mode()
