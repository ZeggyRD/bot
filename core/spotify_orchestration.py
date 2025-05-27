"""
core/spotify_orchestration.py

Orchestrates a full Spotify session in four phases.
"""
import logging
import time
import os
import random

from core.interaction_utils import open_url, human_sleep
from core.exceptions import UIFlowError

logger = logging.getLogger(__name__)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def run_spotify_session(device, personality, account_email, spotify_package_name, playlist_urls):
    """Orchestrates one full Spotify session across four phases."""
    session_id = f"{device.device_id}_{account_email.split('@')[0]}_{time.strftime('%H%M%S')}"
    logger.info(f"[{session_id}] Starting Spotify session on {device.device_id}")

    _phase_initial_playlist(device, personality, account_email, spotify_package_name, playlist_urls, session_id)
    _phase_artist_visit(device, personality, account_email, spotify_package_name, playlist_urls, session_id)
    _phase_track_sampling(device, personality, account_email, spotify_package_name, playlist_urls, session_id)
    _phase_final_playlist(device, personality, account_email, spotify_package_name, playlist_urls, session_id)

    logger.info(f"[{session_id}] Completed Spotify session on {device.device_id}")


def _phase_initial_playlist(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
    # ... existing Phase 1 implementation ...


def _phase_artist_visit(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
    # ... existing Phase 2 implementation ...


def _phase_track_sampling(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
    logger.info(f"[{session_id}] --- Entering Phase 3: Track Sampling ---")
    try:
        # 1) Skip first two entries (playlist + artists), take the rest as track URLs
        track_urls = playlist_urls[2:]
        if not track_urls:
            raise UIFlowError("No track URLs available for sampling")

        # 2) Sample up to 3 random tracks
        sample_count = min(3, len(track_urls))
        sampled_tracks = random.sample(track_urls, sample_count)

        # 3) Open each sampled track and wait
        for url in sampled_tracks:
            logger.debug(f"[{session_id}] Sampling track URL: {url}")
            if not open_url(device.device, url, app_package=spotify_package_name, personality=personality):
                raise UIFlowError(f"open_url failed for track URL {url}")
            # Simulating listening time: 30–60 seconds
            human_sleep(30.0, 60.0, personality)

        logger.info(f"[{session_id}] --- Track Sampling completed ---")
        return True

    except UIFlowError:
        raise
    except Exception as e:
        logger.exception(f"[{session_id}] --- Track Sampling failed: {e}")
        raise UIFlowError(f"Track Sampling error: {e}") from e


def _phase_final_playlist(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
    logger.info(f"[{session_id}] --- Entering Phase 4: Final Playlist ---")
    # TODO: implement final playlist playback
    logger.info(f"[{session_id}] --- Exiting Phase 4: Final Playlist (Placeholder) ---")
    return True
    return True
