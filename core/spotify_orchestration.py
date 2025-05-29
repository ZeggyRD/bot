# core/spotify_orchestration.py
"""
core/spotify_orchestration.py

Orchestrates a full Spotify session in four phases.
"""
import logging
import time
import os
import random

# Assuming these utilities are in core.interaction_utils
# and exceptions in core.exceptions
# The PersonalityProfile will be passed as an object.
from core.interaction_utils import open_url, human_sleep
from core.exceptions import UIFlowError
# from personalities.device_personality import PersonalityProfile # Not imported here, but type hinted

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

    try:
        if not _phase_initial_playlist(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
            logger.warning(f"[{session_id}] Phase 1 (Initial Playlist) did not complete successfully.")
            return False

        if not _phase_artist_visit(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
            logger.warning(f"[{session_id}] Phase 2 (Artist Visit) did not complete successfully.")
            return False

        if not _phase_track_sampling(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
            logger.warning(f"[{session_id}] Phase 3 (Track Sampling) did not complete successfully.")
            return False

        if not _phase_final_playlist(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
            logger.warning(f"[{session_id}] Phase 4 (Final Playlist) did not complete successfully.")
            return False

        logger.info(f"[{session_id}] All phases completed successfully for Spotify session on {device.device_id}")
        return True
    except UIFlowError as e:
        logger.error(f"[{session_id}] Session aborted due to unrecoverable UI flow error: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"[{session_id}] Session aborted due to unexpected critical error: {e}", exc_info=True)
        return False
    finally:
        logger.info(f"[{session_id}] Concluding Spotify session on {device.device_id}")

def _phase_initial_playlist(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
    logger.info(f"[{session_id}] --- Entering Phase 1: Initial Playlist ---")
    try:
        playlist_file_path = os.path.join("data", "playlists.txt")
        url_to_open = None
        logger.debug(f"[{session_id}] Attempting to read from {playlist_file_path}")
        try:
            with open(playlist_file_path, "r") as f:
                url_to_open = f.readline().strip()
        except FileNotFoundError:
            logger.error(f"[{session_id}] Playlist file not found: {playlist_file_path}")
            raise UIFlowError(f"Playlist file not found: {playlist_file_path}")

        if not url_to_open:
            logger.error(f"[{session_id}] No URL found in {playlist_file_path}.")
            raise UIFlowError(f"No URL found in {playlist_file_path}")

        logger.info(f"[{session_id}] Phase 1: Read URL '{url_to_open}' from {playlist_file_path}")

        if not open_url(device.device, url_to_open, app_package=spotify_package_name, personality=personality):
            raise UIFlowError(f"open_url failed for {url_to_open}")

        logger.debug(f"[{session_id}] Phase 1: Applying post-URL open sleep.")
        human_sleep(2.0, 4.0, personality)

        # TODO: Implement Shuffle, Like, Play logic from full plan for Phase 1 using interaction_utils.
        logger.info(f"[{session_id}] Placeholder: Shuffle, Like, Play logic for Initial Playlist not yet fully implemented beyond opening URL.")


        logger.info(f"[{session_id}] --- Initial Playlist (partially implemented) succeeded ---")
        return True
    except FileNotFoundError as e_fnf:
        logger.error(f"[{session_id}] --- Initial Playlist failed: Essential playlist file issue - {e_fnf}")
        raise UIFlowError(f"Initial playlist file error: {e_fnf}") from e_fnf
    except UIFlowError as e_ui:
        logger.error(f"[{session_id}] --- Initial Playlist failed: UI Flow Error - {e_ui}")
        raise
    except Exception as e:
        logger.exception(f"[{session_id}] --- Initial Playlist failed with unexpected error: {e}")
        raise UIFlowError(f"Unexpected error in Initial Playlist: {e}") from e

def _phase_artist_visit(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
    logger.info(f"[{session_id}] --- Entering Phase 2: Artist Visit ---")
    try:
        artist_links = [url for url in playlist_urls if "/artist/" in url.lower()]
        if not artist_links and len(playlist_urls) > 1: # Fallback: if no specific artist links, use second URL if available
             potential_artist_url = playlist_urls[1] # Assuming first is main playlist
             if "/artist/" in potential_artist_url.lower(): # Check if it's actually an artist link
                artist_links.append(potential_artist_url)

        if not artist_links:
            logger.warning(f"[{session_id}] No artist URLs found or derived for Artist Visit. Skipping phase.")
            return True

        max_artists_to_visit = 1 # As per user's typical request for N songs from *each* artist, let's simplify to 1 artist for now.
        artists_visited_count = 0

        for url in random.sample(artist_links, min(len(artist_links), max_artists_to_visit)): # Visit a sample
            if artists_visited_count >= max_artists_to_visit: break

            logger.debug(f"[{session_id}] Visiting artist URL: {url}")
            if not open_url(device.device, url, app_package=spotify_package_name, personality=personality):
                logger.warning(f"[{session_id}] open_url failed for artist URL {url}. Skipping this artist.")
                continue

            # TODO: Implement "follow if not already following" logic.
            # TODO: Implement "play N songs" logic.
            logger.info(f"[{session_id}] Placeholder: Visited artist {url}. Follow/play N songs logic TBD.")
            human_sleep(10.0, 20.0, personality) # Placeholder for interacting

            artists_visited_count +=1
        logger.info(f"[{session_id}] --- Artist Visit completed ({artists_visited_count} artists) ---")
        return True
    except UIFlowError as e_ui:
        logger.error(f"[{session_id}] --- Artist Visit failed: UI Flow Error - {e_ui}")
        raise
    except Exception as e:
        logger.exception(f"[{session_id}] --- Artist Visit failed with unexpected error: {e}")
        raise UIFlowError(f"Artist Visit unexpected error: {e}") from e

def _phase_track_sampling(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
    logger.info(f"[{session_id}] --- Entering Phase 3: Track Sampling ---")
    try:
        track_urls = [url for url in playlist_urls if "/track/" in url.lower()]
        if not track_urls:
             # Fallback: if no /track/ links, use any URLs not playlist/artist from 3rd onwards
             non_playlist_artist_urls = [u for u in playlist_urls if "/playlist/" not in u.lower() and "/artist/" not in u.lower()]
             if len(non_playlist_artist_urls) > 0 : track_urls = non_playlist_artist_urls
             elif len(playlist_urls) > 2: track_urls = playlist_urls[2:] # Absolute fallback
             else:
                logger.warning(f"[{session_id}] No track URLs available for sampling. Skipping phase.")
                return True

        if not track_urls:
             logger.warning(f"[{session_id}] Still no track URLs after fallback. Skipping phase.")
             return True

        sample_count = min(3, len(track_urls))
        sampled_tracks = random.sample(track_urls, sample_count)
        logger.info(f"[{session_id}] Will sample {len(sampled_tracks)} tracks: {sampled_tracks}")

        for url in sampled_tracks:
            logger.debug(f"[{session_id}] Sampling track URL: {url}")
            if not open_url(device.device, url, app_package=spotify_package_name, personality=personality):
                logger.warning(f"[{session_id}] open_url failed for track URL {url}. Skipping this track.")
                continue
            human_sleep(30.0, 60.0, personality)

        logger.info(f"[{session_id}] --- Track Sampling completed ---")
        return True
    except UIFlowError as e_ui:
        logger.error(f"[{session_id}] --- Track Sampling failed due to UIFlowError: {e_ui}", exc_info=True)
        raise
    except Exception as e:
        logger.exception(f"[{session_id}] --- Track Sampling failed with unexpected error: {e}")
        raise UIFlowError(f"Track Sampling unexpected error: {e}") from e

def _phase_final_playlist(device, personality, account_email, spotify_package_name, playlist_urls, session_id):
    logger.info(f"[{session_id}] --- Entering Phase 4: Final Playlist ---")
    try:
        playlist_file_path = os.path.join("data", "playlists.txt")
        first_url = None
        try:
            # Ensure we have at least one playlist URL.
            # The first URL in playlist_urls should be a playlist if initial phase worked.
            # Or re-read from file to be sure.
            if playlist_urls and "/playlist/" in playlist_urls[0].lower():
                first_url = playlist_urls[0]
            else: # Fallback to reading the file again
                with open(playlist_file_path, "r") as f:
                    first_url = f.readline().strip()
        except FileNotFoundError:
            logger.error(f"[{session_id}] Final Playlist: Playlist file not found: {playlist_file_path}")
            raise UIFlowError(f"Playlist file not found for final play: {playlist_file_path}")

        if not first_url:
            logger.error(f"[{session_id}] Final Playlist: No URL found for final play.")
            raise UIFlowError(f"No URL found for final play.")

        logger.debug(f"[{session_id}] Final Playlist – Reopening URL: {first_url}")
        if not open_url(device.device, first_url, app_package=spotify_package_name, personality=personality):
            raise UIFlowError(f"open_url failed for final playlist URL {first_url}")

        human_sleep(60.0, 120.0, personality)

        logger.info(f"[{session_id}] --- Final Playlist completed successfully ---")
        return True
    except UIFlowError as e_ui:
        logger.error(f"[{session_id}] --- Final Playlist failed: UI Flow Error - {e_ui}")
        raise
    except Exception as e:
        logger.exception(f"[{session_id}] --- Final Playlist failed with unexpected error: {e}")
        raise UIFlowError(f"Final Playlist unexpected error: {e}") from e
