"""
core/spotify_orchestration.py

Orchestrates a full Spotify session in four phases.
"""
import logging
import time
import os

from core.interaction_utils import open_url, human_sleep
from core.exceptions import UIFlowError

logger = logging.getLogger(__name__)

# Configure logger if not already done
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
    logger.info(f"[{session_id}] --- Entering Phase 1: Initial Playlist ---")
    try:
        # 1) Load first URL from data/playlists.txt
        playlist_file_path = os.path.join("data", "playlists.txt")
        logger.debug(f"[{session_id}] Reading playlist file: {playlist_file_path}")
        try:
            with open(playlist_file_path, "r") as f:
                url_to_open = f.readline().strip()
        except FileNotFoundError as e:
            logger.error(f"[{session_id}] Playlist file not found: {playlist_file_path}")
            raise UIFlowError(f"Playlist file not found: {playlist_file_path}") from e

        if not url_to_open:
            logger.error(f"[{session_id}] No URL found in {playlist_file_path}")
            raise UIFlowError("No URL found in playlist file")

        logger.info(f"[{session_id}] Phase 1: opening URL '{url_to_open}'")
        if not open_url(device.device, url_to_open, app_package=spotify_package_name, personality=personality):
            raise UIFlowError(f"open_url failed for {url_to_open}")

        logger.debug(f"[{session_id}] Phase 1: pausing after URL open")
        human_sleep(personality)

        logger.info(f"[{session_id}] --- Initial Playlist succeeded ---")
        return True

    except UIFlowError:
        raise
    except Exception as e:
        logger.exception(f"[{session_id}] --- Initial Playlist unexpected error: {e}")
        raise UIFlowError(f"Unexpected error in Initial Playlist: {e}") from e


def _phase_artist_visit(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
    logger.info(f"[{session_id}] --- Entering Phase 2: Artist Visit ---")
    try:
        # Treat all URLs after the first as artist profile links
        artist_links = playlist_urls[1:]
        for url in artist_links:
            logger.debug(f"[{session_id}] Visiting artist URL: {url}")
            if not open_url(device.device, url, app_package=spotify_package_name, personality=personality):
                raise UIFlowError(f"open_url failed for artist URL {url}")
            human_sleep(personality)

        logger.info(f"[{session_id}] --- Artist Visit completed ---")
        return True

    except UIFlowError:
        raise
    except Exception as e:
        logger.exception(f"[{session_id}] --- Artist Visit failed: {e}")
        raise UIFlowError(f"Artist Visit error: {e}") from e


def _phase_track_sampling(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
    logger.info(f"[{session_id}] --- Entering Phase 3: Track Sampling ---")
    # TODO: implement sampling a few random tracks from playlist_urls
    logger.info(f"[{session_id}] --- Exiting Phase 3: Track Sampling (Placeholder) ---")
    return True


def _phase_final_playlist(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
    logger.info(f"[{session_id}] --- Entering Phase 4: Final Playlist ---")
    # TODO: implement final playlist playback
    logger.info(f"[{session_id}] --- Exiting Phase 4: Final Playlist (Placeholder) ---")
    return True
