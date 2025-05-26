# -*- coding: utf-8 -*-
"""Módulo para simular el comportamiento humano en las interacciones del bot."""

import random
import time

class DevicePersonality:
    """Define la personalidad única de un dispositivo para simular un usuario real."""
    def __init__(self, device_id):
        """Inicializa la personalidad con valores aleatorios pero fijos para el dispositivo."""
        self.device_id = device_id
        # Parámetros de personalidad (ejemplos, ajustar rangos según necesidad)
        self.patience = random.uniform(0.8, 1.2)  # Factor de velocidad/espera
        self.curiosity = random.uniform(0.1, 0.9) # Probabilidad de explorar/seguir
        self.engagement = random.uniform(0.2, 0.8) # Probabilidad de dar like/interactuar
        self.skip_rate = random.uniform(0.05, 0.3) # Probabilidad de saltar canción
        self.typing_speed = random.uniform(0.05, 0.2) * self.patience # Segundos por caracter
        self.scroll_amount = random.randint(300, 800) # Píxeles por scroll
        self.scroll_delay = random.uniform(0.5, 2.0) * self.patience # Segundos entre scrolls
        self.click_delay_base = random.uniform(0.8, 1.5) * self.patience # Segundos base antes/después de click
        self.action_delay_base = random.uniform(2.0, 5.0) * self.patience # Segundos base entre acciones

    def get_typing_delay(self):
        """Devuelve un retraso realista para simular la escritura."""
        return self.typing_speed + random.uniform(-0.02, 0.02)

    def get_scroll_delay(self):
        """Devuelve un retraso antes o después de hacer scroll."""
        return self.scroll_delay + random.uniform(-0.2, 0.2)

    def get_click_delay(self):
        """Devuelve un retraso antes o después de hacer click."""
        return self.click_delay_base + random.uniform(-0.3, 0.5)

    def get_action_delay(self):
        """Devuelve un retraso entre acciones significativas."""
        return self.action_delay_base + random.uniform(-1.0, 2.0)

    def should_follow(self):
        """Decide si seguir a un artista basado en la curiosidad."""
        return random.random() < self.curiosity

    def should_like(self):
        """Decide si dar like basado en el engagement."""
        return random.random() < self.engagement

    def should_skip(self):
        """Decide si saltar una canción."""
        return random.random() < self.skip_rate

# Funciones de utilidad que usan la personalidad

def human_sleep(min_seconds, max_seconds, personality: DevicePersonality = None):
    """Espera un tiempo aleatorio dentro de un rango, ajustado por la personalidad."""
    base_delay = random.uniform(min_seconds, max_seconds)
    patience_factor = personality.patience if personality else 1.0
    time.sleep(base_delay * patience_factor)

def human_type(element, text, personality: DevicePersonality):
    """Simula la escritura humana en un elemento web."""
    # Implementación dependerá de la librería de automatización (Selenium, Playwright, etc.)
    # Ejemplo conceptual:
    # element.clear()
    # for char in text:
    #     element.send_keys(char)
    #     time.sleep(personality.get_typing_delay())
    print(f"[HUMAN_BEHAVIOR] Simulating typing: '{text}' with delay {personality.typing_speed:.3f}s/char")
    human_sleep(0.5, 1.0, personality) # Pequeña pausa después de escribir

def human_scroll(driver, personality: DevicePersonality):
    """Simula un scroll humano."""
    # Implementación dependerá de la librería de automatización
    # Ejemplo conceptual:
    # scroll_pixels = personality.scroll_amount
    # driver.execute_script(f"window.scrollBy(0, {scroll_pixels});")
    print(f"[HUMAN_BEHAVIOR] Simulating scroll by {personality.scroll_amount}px")
    human_sleep(personality.get_scroll_delay() * 0.8, personality.get_scroll_delay() * 1.2, personality)

def human_click(element, personality: DevicePersonality):
    """Simula un click humano con retrasos antes y después."""
    # Implementación dependerá de la librería de automatización
    human_sleep(personality.get_click_delay() * 0.4, personality.get_click_delay() * 0.6, personality)
    # element.click()
    print(f"[HUMAN_BEHAVIOR] Simulating click")
    human_sleep(personality.get_click_delay() * 0.4, personality.get_click_delay() * 0.6, personality)

# Ejemplo de uso (esto iría en otros módulos)
if __name__ == '__main__':
    # Crear una personalidad para un dispositivo específico
    personality1 = DevicePersonality("device_serial_123")
    personality2 = DevicePersonality("device_serial_456")

    print(f"Personality 1 ({personality1.device_id}):")
    print(f"  Patience: {personality1.patience:.2f}")
    print(f"  Curiosity: {personality1.curiosity:.2f}")
    print(f"  Engagement: {personality1.engagement:.2f}")
    print(f"  Skip Rate: {personality1.skip_rate:.2f}")
    print(f"  Typing Speed: {personality1.typing_speed:.3f} s/char")

    print(f"\nPersonality 2 ({personality2.device_id}):")
    print(f"  Patience: {personality2.patience:.2f}")
    print(f"  Curiosity: {personality2.curiosity:.2f}")
    print(f"  Engagement: {personality2.engagement:.2f}")
    print(f"  Skip Rate: {personality2.skip_rate:.2f}")
    print(f"  Typing Speed: {personality2.typing_speed:.3f} s/char")

    print("\nSimulating actions for Personality 1:")
    human_sleep(1, 3, personality1)
    print("Slept for a bit.")
    human_type(None, "Hello World!", personality1) # Elemento es None para prueba
    human_scroll(None, personality1) # Driver es None para prueba
    human_click(None, personality1) # Elemento es None para prueba
    print(f"Should follow? {personality1.should_follow()}")
    print(f"Should like? {personality1.should_like()}")
    print(f"Should skip? {personality1.should_skip()}")

