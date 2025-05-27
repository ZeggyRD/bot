# -*- coding: utf-8 -*-
"""Módulo para definir y gestionar perfiles de personalidad para simular usuarios."""

import random
import time
import json
import os
import logging

logger = logging.getLogger("PersonalityProfile")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class PersonalityProfile:
    """Define un perfil de personalidad para un usuario (cuenta)."""
    def __init__(self, username: str, profile_directory: str = "personalities/"):
        """
        Inicializa el perfil, cargándolo desde un archivo JSON si existe,
        o creando uno nuevo con valores predeterminados aleatorios.
        """
        self.username = username
        self.profile_directory = profile_directory
        self.profile_path = os.path.join(self.profile_directory, f"{self.username}.json")

        # --- Default values (some will be overridden by load_profile) ---
        self.patience_factor = random.uniform(0.8, 1.2)
        self.curiosity_factor = random.uniform(0.1, 0.9)
        self.engagement_factor = random.uniform(0.2, 0.8)
        self.skip_rate_playlist = random.uniform(0.05, 0.3)
        self.skip_rate_track_sampling = random.uniform(0.1, 0.5)
        
        # Base speeds/amounts - factors will modify these
        self._base_typing_speed_char_per_sec = random.uniform(5, 10) # Chars per second
        self._base_scroll_pixels_min = 300
        self._base_scroll_pixels_max = 800
        self._base_scroll_delay_sec = random.uniform(0.5, 1.5)
        self._base_click_delay_sec = random.uniform(0.2, 0.7) # Shorter for click itself
        self._base_action_delay_sec = random.uniform(1.5, 4.0)

        # Factors to modify base speeds/delays (1.0 is average)
        self.typing_speed_factor = random.uniform(0.8, 1.2) # Slower or faster than base
        self.scroll_amount_pixels_min = self._base_scroll_pixels_min
        self.scroll_amount_pixels_max = self._base_scroll_pixels_max
        self.scroll_delay_factor = random.uniform(0.8, 1.2)
        self.click_delay_factor = random.uniform(0.8, 1.2)
        self.action_delay_factor = random.uniform(0.8, 1.2)

        self.wake_hours = [[8, 12], [13, 17], [19,22]] # Default wake hours
        self.sleep_hours = [] # Can be derived or explicitly set

        self.fandom_artists = ["Cerame", "Kairo la Sinfonía", "Gmany"] # Default fandom artists
        self.fandom_urls = [] # To be populated, e.g., from data/playlists.txt

        self.load_profile()

    def load_profile(self):
        """Carga el perfil desde un archivo JSON o crea uno nuevo con valores predeterminados."""
        os.makedirs(self.profile_directory, exist_ok=True)
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, 'r') as f:
                    data = json.load(f)
                # Update attributes from loaded data, keeping defaults if keys are missing
                for key, value in data.items():
                    setattr(self, key, value)
                logger.info(f"Loaded personality profile for {self.username} from {self.profile_path}")
            except Exception as e:
                logger.error(f"Error loading profile for {self.username} from {self.profile_path}: {e}. Using defaults and attempting to save.")
                # If loading fails, it will proceed to save defaults.
                self._save_profile() # Attempt to save defaults if loading failed
        else:
            logger.info(f"No profile found for {self.username}. Creating new profile at {self.profile_path} with defaults.")
            self._save_profile() # Save initial default values

    def _save_profile(self):
        """Guarda el perfil actual en un archivo JSON."""
        profile_data = {
            key: value for key, value in self.__dict__.items() 
            if not key.startswith('_') and key not in ['username', 'profile_directory', 'profile_path']
        }
        try:
            with open(self.profile_path, 'w') as f:
                json.dump(profile_data, f, indent=4)
            logger.info(f"Saved personality profile for {self.username} to {self.profile_path}")
        except Exception as e:
            logger.error(f"Error saving profile for {self.username} to {self.profile_path}: {e}")
            
    def get_typing_delay(self):
        """Devuelve un retraso realista por caracter para simular la escritura."""
        # Higher factor = slower typing (more delay)
        delay_per_char = (1.0 / self._base_typing_speed_char_per_sec) * self.typing_speed_factor * self.patience_factor
        return delay_per_char + random.uniform(-0.01, 0.01) * self.patience_factor

    def get_scroll_amount_pixels(self):
        return random.randint(self.scroll_amount_pixels_min, self.scroll_amount_pixels_max)

    def get_scroll_delay(self):
        """Devuelve un retraso antes o después de hacer scroll."""
        return (self._base_scroll_delay_sec * self.scroll_delay_factor * self.patience_factor) + random.uniform(-0.1, 0.1)

    def get_click_delay(self):
        """Devuelve un retraso antes o después de hacer click."""
        return (self._base_click_delay_sec * self.click_delay_factor * self.patience_factor) + random.uniform(-0.05, 0.1)

    def get_action_delay(self):
        """Devuelve un retraso entre acciones significativas."""
        return (self._base_action_delay_sec * self.action_delay_factor * self.patience_factor) + random.uniform(-0.5, 1.0)

    def should_follow(self):
        """Decide si seguir a un artista basado en la curiosidad."""
        return random.random() < self.curiosity_factor

    def should_like(self):
        """Decide si dar like basado en el engagement."""
        return random.random() < self.engagement_factor

    def should_skip_playlist_track(self):
        """Decide si saltar una canción en una playlist."""
        return random.random() < self.skip_rate_playlist
        
    def should_skip_sampled_track(self):
        """Decide si saltar una canción durante el muestreo/descubrimiento."""
        return random.random() < self.skip_rate_track_sampling


# Funciones de utilidad que usan la personalidad (pueden moverse a un módulo de utils si es necesario)
# Estas funciones necesitarán acceso a un objeto PersonalityProfile

def human_sleep(min_seconds, max_seconds, personality: PersonalityProfile = None):
    """Espera un tiempo aleatorio dentro de un rango, ajustado por la personalidad."""
    base_delay = random.uniform(min_seconds, max_seconds)
    patience_factor = personality.patience_factor if personality else 1.0
    time.sleep(base_delay * patience_factor)

def human_type(element, text, personality: PersonalityProfile):
    """Simula la escritura humana en un elemento web."""
    logger.debug(f"Simulating typing: '{text}' for user {personality.username}")
    # Actual implementation would depend on the UI automation library
    for char in text:
        # element.send_keys(char) # Example
        time.sleep(personality.get_typing_delay())
    human_sleep(0.3 * personality.patience_factor, 0.7 * personality.patience_factor, personality)

def human_scroll(driver, personality: PersonalityProfile):
    """Simula un scroll humano."""
    scroll_pixels = personality.get_scroll_amount_pixels()
    logger.debug(f"Simulating scroll by {scroll_pixels}px for user {personality.username}")
    # driver.execute_script(f"window.scrollBy(0, {scroll_pixels});") # Example
    time.sleep(personality.get_scroll_delay())

def human_click(element, personality: PersonalityProfile):
    """Simula un click humano con retrasos antes y después."""
    time.sleep(personality.get_click_delay() * 0.5) # Pre-click delay
    # element.click() # Example
    logger.debug(f"Simulating click for user {personality.username}")
    time.sleep(personality.get_click_delay() * 0.5) # Post-click delay

if __name__ == '__main__':
    test_username = "test_user_profile"
    profile_dir = "personalities_test_cache" # Use a test directory
    
    # Clean up previous test file if it exists
    test_profile_path = os.path.join(profile_dir, f"{test_username}.json")
    if os.path.exists(test_profile_path):
        os.remove(test_profile_path)
    if not os.path.exists(profile_dir):
         os.makedirs(profile_dir)

    print(f"--- Creating or Loading profile for {test_username} ---")
    profile1 = PersonalityProfile(test_username, profile_directory=profile_dir)
    
    print(f"\nProfile for {profile1.username} (loaded/created):")
    for key, value in profile1.__dict__.items():
        if not key.startswith('_') and key not in ['username', 'profile_directory', 'profile_path']:
            print(f"  {key}: {value}")

    # Modify a value and save
    profile1.patience_factor = 1.5 
    profile1.fandom_urls.append("http://example.com/playlist1")
    profile1._save_profile() # Manually save to see changes reflected if loaded again
    
    print(f"\n--- Loading profile for {test_username} again to check persistence ---")
    profile1_reloaded = PersonalityProfile(test_username, profile_directory=profile_dir)
    print(f"\nReloaded profile for {profile1_reloaded.username}:")
    for key, value in profile1_reloaded.__dict__.items():
        if not key.startswith('_') and key not in ['username', 'profile_directory', 'profile_path']:
            print(f"  {key}: {value}")
    
    assert profile1_reloaded.patience_factor == 1.5
    assert "http://example.com/playlist1" in profile1_reloaded.fandom_urls

    print("\n--- Simulating actions with the profile ---")
    human_sleep(0.1, 0.2, profile1_reloaded)
    print("Slept for a bit.")
    # These would require a mock element/driver for real testing
    human_type(None, "Hello!", profile1_reloaded) 
    human_scroll(None, profile1_reloaded) 
    human_click(None, profile1_reloaded)
    print(f"Should follow? {profile1_reloaded.should_follow()}")
    print(f"Should like? {profile1_reloaded.should_like()}")
    print(f"Should skip playlist track? {profile1_reloaded.should_skip_playlist_track()}")
    print(f"Should skip sampled track? {profile1_reloaded.should_skip_sampled_track()}")

    # Cleanup test directory and file
    if os.path.exists(test_profile_path):
        os.remove(test_profile_path)
    if os.path.exists(profile_dir) and not os.listdir(profile_dir): # only remove if empty
        os.rmdir(profile_dir)
    print("\nTest complete and cleanup done.")

