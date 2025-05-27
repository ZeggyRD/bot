#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import random
import time
import logging
from datetime import datetime, timedelta

# Configuración del sistema de logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"account_manager_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AccountManager")

# Constantes
ACCOUNTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "spotify_accounts.txt")
ACCOUNTS_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "accounts_db.json")
PROXIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "proxy_pool.txt")
PROXIES_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "proxies_db.json")
MAX_ACCOUNTS_PER_DEVICE = 10  # Máximo de cuentas por dispositivo por día

class AccountManager:
    def __init__(self):
        """Inicializa el gestor de cuentas y proxies"""
        self.accounts_db = self._load_accounts_db()
        self.proxies_db = self._load_proxies_db()
        self.device_assignments = {}  # Mapeo de dispositivos a cuentas asignadas hoy
        self.today = datetime.now().strftime('%Y-%m-%d')
        
        # Cargar cuentas y proxies si no existen en la base de datos
        self._load_accounts_from_file()
        self._load_proxies_from_file()
        
        # Guardar cambios
        self._save_accounts_db()
        self._save_proxies_db()
        
        logger.info(f"AccountManager inicializado con {len(self.accounts_db)} cuentas y {len(self.proxies_db)} proxies")

    def _load_accounts_db(self):
        """Carga la base de datos de cuentas desde el archivo JSON"""
        if os.path.exists(ACCOUNTS_DB_FILE):
            try:
                with open(ACCOUNTS_DB_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error al cargar la base de datos de cuentas: {e}")
                return {}
        return {}

    def _save_accounts_db(self):
        """Guarda la base de datos de cuentas en el archivo JSON"""
        try:
            os.makedirs(os.path.dirname(ACCOUNTS_DB_FILE), exist_ok=True)
            with open(ACCOUNTS_DB_FILE, 'w') as f:
                json.dump(self.accounts_db, f, indent=4)
        except Exception as e:
            logger.error(f"Error al guardar la base de datos de cuentas: {e}")

    def _load_proxies_db(self):
        """Carga la base de datos de proxies desde el archivo JSON"""
        if os.path.exists(PROXIES_DB_FILE):
            try:
                with open(PROXIES_DB_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error al cargar la base de datos de proxies: {e}")
                return {}
        return {}

    def _save_proxies_db(self):
        """Guarda la base de datos de proxies en el archivo JSON"""
        try:
            os.makedirs(os.path.dirname(PROXIES_DB_FILE), exist_ok=True)
            with open(PROXIES_DB_FILE, 'w') as f:
                json.dump(self.proxies_db, f, indent=4)
        except Exception as e:
            logger.error(f"Error al guardar la base de datos de proxies: {e}")

    def _load_accounts_from_file(self):
        """Carga las cuentas desde el archivo de texto y las añade a la base de datos"""
        if not os.path.exists(ACCOUNTS_FILE):
            logger.warning(f"Archivo de cuentas no encontrado: {ACCOUNTS_FILE}")
            return
        
        try:
            with open(ACCOUNTS_FILE, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if ":" in line:
                    email, password = line.split(":", 1)
                    if email not in self.accounts_db:
                        self.accounts_db[email] = {
                            "password": password,
                            "last_used": None,
                            "usage_count": 0,
                            "last_proxy": None,
                            "last_device": None,
                            "status": "active",
                            "history": []
                        }
            
            logger.info(f"Cargadas {len(lines)} cuentas desde el archivo")
        except Exception as e:
            logger.error(f"Error al cargar cuentas desde el archivo: {e}")

    def _load_proxies_from_file(self):
        """Carga los proxies desde el archivo de texto y los añade a la base de datos"""
        if not os.path.exists(PROXIES_FILE):
            logger.warning(f"Archivo de proxies no encontrado: {PROXIES_FILE}")
            return
        
        try:
            with open(PROXIES_FILE, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if ":" in line and len(line.split(":")) >= 4:
                    proxy_id = line  # Usamos la línea completa como ID
                    if proxy_id not in self.proxies_db:
                        self.proxies_db[proxy_id] = {
                            "last_used": None,
                            "usage_count": 0,
                            "last_account": None,
                            "last_device": None,
                            "status": "active",
                            "history": []
                        }
            
            logger.info(f"Cargados {len(lines)} proxies desde el archivo")
        except Exception as e:
            logger.error(f"Error al cargar proxies desde el archivo: {e}")

    def get_account_for_device(self, device_id):
        """
        Obtiene una cuenta para un dispositivo específico, respetando la rotación diaria
        y el límite de cuentas por dispositivo
        """
        # Inicializar asignación del dispositivo si no existe
        if device_id not in self.device_assignments:
            self.device_assignments[device_id] = {
                "date": self.today,
                "accounts": []
            }
        
        # Si la fecha de asignación es antigua, resetear
        if self.device_assignments[device_id]["date"] != self.today:
            self.device_assignments[device_id] = {
                "date": self.today,
                "accounts": []
            }
        
        # Verificar si ya se alcanzó el límite diario
        if len(self.device_assignments[device_id]["accounts"]) >= MAX_ACCOUNTS_PER_DEVICE:
            logger.warning(f"Dispositivo {device_id} ya alcanzó el límite diario de {MAX_ACCOUNTS_PER_DEVICE} cuentas")
            # Devolver una cuenta ya asignada (reutilización)
            assigned_accounts = self.device_assignments[device_id]["accounts"]
            if assigned_accounts:
                email = random.choice(assigned_accounts)
                return email, self.accounts_db[email]["password"]
            return None, None
        
        # Filtrar cuentas activas que no se han usado hoy en este dispositivo
        available_accounts = []
        for email, data in self.accounts_db.items():
            if data["status"] == "active" and email not in self.device_assignments[device_id]["accounts"]:
                # Priorizar cuentas menos usadas o que no se han usado recientemente
                priority = 100 - data["usage_count"]
                if data["last_used"]:
                    days_since_use = (datetime.now() - datetime.fromisoformat(data["last_used"])).days
                    priority += min(days_since_use, 30)  # Máximo bonus de 30 puntos por antigüedad
                available_accounts.append((email, priority))
        
        if not available_accounts:
            logger.warning("No hay cuentas disponibles para asignar")
            return None, None
        
        # Ordenar por prioridad y seleccionar con algo de aleatoriedad
        available_accounts.sort(key=lambda x: x[1], reverse=True)
        top_accounts = available_accounts[:min(5, len(available_accounts))]
        selected_email, _ = random.choice(top_accounts)
        
        # Actualizar la información de la cuenta
        self.accounts_db[selected_email]["last_used"] = datetime.now().isoformat()
        self.accounts_db[selected_email]["usage_count"] += 1
        self.accounts_db[selected_email]["last_device"] = device_id
        
        # Registrar en el historial
        self.accounts_db[selected_email]["history"].append({
            "date": datetime.now().isoformat(),
            "device": device_id,
            "action": "assigned"
        })
        
        # Añadir a las asignaciones del día
        self.device_assignments[device_id]["accounts"].append(selected_email)
        
        # Guardar cambios
        self._save_accounts_db()
        
        logger.info(f"Cuenta {selected_email} asignada al dispositivo {device_id}")
        return selected_email, self.accounts_db[selected_email]["password"]

    def get_proxy_for_account(self, email, device_id):
        """
        Obtiene un proxy para una cuenta específica, manteniendo la asociación
        cuenta-proxy cuando es posible
        """
        if email not in self.accounts_db:
            logger.error(f"Cuenta {email} no encontrada en la base de datos")
            return None
        
        # Si la cuenta ya tenía un proxy asignado y está disponible, reutilizarlo
        last_proxy = self.accounts_db[email]["last_proxy"]
        if last_proxy and last_proxy in self.proxies_db and self.proxies_db[last_proxy]["status"] == "active":
            logger.info(f"Reutilizando proxy {last_proxy} para la cuenta {email}")
            
            # Actualizar información del proxy
            self.proxies_db[last_proxy]["last_used"] = datetime.now().isoformat()
            self.proxies_db[last_proxy]["usage_count"] += 1
            self.proxies_db[last_proxy]["last_account"] = email
            self.proxies_db[last_proxy]["last_device"] = device_id
            
            # Registrar en el historial
            self.proxies_db[last_proxy]["history"].append({
                "date": datetime.now().isoformat(),
                "account": email,
                "device": device_id,
                "action": "assigned"
            })
            
            # Actualizar información de la cuenta
            self.accounts_db[email]["last_proxy"] = last_proxy
            
            # Guardar cambios
            self._save_proxies_db()
            self._save_accounts_db()
            
            return last_proxy
        
        # Filtrar proxies activos
        available_proxies = []
        for proxy_id, data in self.proxies_db.items():
            if data["status"] == "active":
                # Priorizar proxies menos usados
                priority = 100 - data["usage_count"]
                available_proxies.append((proxy_id, priority))
        
        if not available_proxies:
            logger.warning("No hay proxies disponibles para asignar")
            return None
        
        # Ordenar por prioridad y seleccionar con algo de aleatoriedad
        available_proxies.sort(key=lambda x: x[1], reverse=True)
        top_proxies = available_proxies[:min(5, len(available_proxies))]
        selected_proxy, _ = random.choice(top_proxies)
        
        # Actualizar información del proxy
        self.proxies_db[selected_proxy]["last_used"] = datetime.now().isoformat()
        self.proxies_db[selected_proxy]["usage_count"] += 1
        self.proxies_db[selected_proxy]["last_account"] = email
        self.proxies_db[selected_proxy]["last_device"] = device_id
        
        # Registrar en el historial
        self.proxies_db[selected_proxy]["history"].append({
            "date": datetime.now().isoformat(),
            "account": email,
            "device": device_id,
            "action": "assigned"
        })
        
        # Actualizar información de la cuenta
        self.accounts_db[email]["last_proxy"] = selected_proxy
        
        # Guardar cambios
        self._save_proxies_db()
        self._save_accounts_db()
        
        logger.info(f"Proxy {selected_proxy} asignado a la cuenta {email} en dispositivo {device_id}")
        return selected_proxy

    def report_login_success(self, email, device_id):
        """Registra un inicio de sesión exitoso"""
        if email not in self.accounts_db:
            logger.error(f"Cuenta {email} no encontrada en la base de datos")
            return
        
        # Registrar en el historial
        self.accounts_db[email]["history"].append({
            "date": datetime.now().isoformat(),
            "device": device_id,
            "action": "login_success"
        })
        
        # Guardar cambios
        self._save_accounts_db()
        
        logger.info(f"Inicio de sesión exitoso registrado para {email} en dispositivo {device_id}")

    def report_login_failure(self, email, device_id, reason="unknown"):
        """Registra un fallo de inicio de sesión"""
        if email not in self.accounts_db:
            logger.error(f"Cuenta {email} no encontrada en la base de datos")
            return
        
        # Registrar en el historial
        self.accounts_db[email]["history"].append({
            "date": datetime.now().isoformat(),
            "device": device_id,
            "action": "login_failure",
            "reason": reason
        })
        
        # Si hay demasiados fallos consecutivos, marcar la cuenta como problemática
        failures = 0
        for event in reversed(self.accounts_db[email]["history"]):
            if event["action"] == "login_failure":
                failures += 1
            else:
                break
        
        if failures >= 3:
            logger.warning(f"Cuenta {email} marcada como problemática después de {failures} fallos consecutivos")
            self.accounts_db[email]["status"] = "problem"
        
        # Guardar cambios
        self._save_accounts_db()
        
        logger.info(f"Fallo de inicio de sesión registrado para {email} en dispositivo {device_id}: {reason}")

    def report_proxy_failure(self, proxy_id, reason="unknown"):
        """Registra un fallo de proxy"""
        if proxy_id not in self.proxies_db:
            logger.error(f"Proxy {proxy_id} no encontrado en la base de datos")
            return
        
        # Registrar en el historial
        self.proxies_db[proxy_id]["history"].append({
            "date": datetime.now().isoformat(),
            "action": "failure",
            "reason": reason
        })
        
        # Si hay demasiados fallos consecutivos, marcar el proxy como problemático
        failures = 0
        for event in reversed(self.proxies_db[proxy_id]["history"]):
            if event["action"] == "failure":
                failures += 1
            else:
                break
        
        if failures >= 3:
            logger.warning(f"Proxy {proxy_id} marcado como problemático después de {failures} fallos consecutivos")
            self.proxies_db[proxy_id]["status"] = "problem"
        
        # Guardar cambios
        self._save_proxies_db()
        
        logger.info(f"Fallo de proxy registrado para {proxy_id}: {reason}")

    def get_account_stats(self, email):
        """Obtiene estadísticas de una cuenta específica"""
        if email not in self.accounts_db:
            logger.error(f"Cuenta {email} no encontrada en la base de datos")
            return None
        
        account_data = self.accounts_db[email]
        
        # Calcular estadísticas adicionales
        stats = {
            "email": email,
            "usage_count": account_data["usage_count"],
            "status": account_data["status"],
            "last_used": account_data["last_used"],
            "last_device": account_data["last_device"],
            "last_proxy": account_data["last_proxy"],
            "history_length": len(account_data["history"]),
            "login_success_count": sum(1 for event in account_data["history"] if event["action"] == "login_success"),
            "login_failure_count": sum(1 for event in account_data["history"] if event["action"] == "login_failure")
        }
        
        return stats

    def get_proxy_stats(self, proxy_id):
        """Obtiene estadísticas de un proxy específico"""
        if proxy_id not in self.proxies_db:
            logger.error(f"Proxy {proxy_id} no encontrado en la base de datos")
            return None
        
        proxy_data = self.proxies_db[proxy_id]
        
        # Calcular estadísticas adicionales
        stats = {
            "proxy_id": proxy_id,
            "usage_count": proxy_data["usage_count"],
            "status": proxy_data["status"],
            "last_used": proxy_data["last_used"],
            "last_device": proxy_data["last_device"],
            "last_account": proxy_data["last_account"],
            "history_length": len(proxy_data["history"]),
            "failure_count": sum(1 for event in proxy_data["history"] if event["action"] == "failure")
        }
        
        return stats

    def get_all_accounts_summary(self):
        """Obtiene un resumen de todas las cuentas"""
        active_count = sum(1 for data in self.accounts_db.values() if data["status"] == "active")
        problem_count = sum(1 for data in self.accounts_db.values() if data["status"] == "problem")
        
        # Cuentas más y menos utilizadas
        usage_counts = [(email, data["usage_count"]) for email, data in self.accounts_db.items()]
        most_used = sorted(usage_counts, key=lambda x: x[1], reverse=True)[:5]
        least_used = sorted(usage_counts, key=lambda x: x[1])[:5]
        
        summary = {
            "total_accounts": len(self.accounts_db),
            "active_accounts": active_count,
            "problem_accounts": problem_count,
            "most_used_accounts": most_used,
            "least_used_accounts": least_used
        }
        
        return summary

    def get_all_proxies_summary(self):
        """Obtiene un resumen de todos los proxies"""
        active_count = sum(1 for data in self.proxies_db.values() if data["status"] == "active")
        problem_count = sum(1 for data in self.proxies_db.values() if data["status"] == "problem")
        
        # Proxies más y menos utilizados
        usage_counts = [(proxy_id, data["usage_count"]) for proxy_id, data in self.proxies_db.items()]
        most_used = sorted(usage_counts, key=lambda x: x[1], reverse=True)[:5]
        least_used = sorted(usage_counts, key=lambda x: x[1])[:5]
        
        summary = {
            "total_proxies": len(self.proxies_db),
            "active_proxies": active_count,
            "problem_proxies": problem_count,
            "most_used_proxies": most_used,
            "least_used_proxies": least_used
        }
        
        return summary

    def reset_problem_status(self, days_threshold=7):
        """
        Resetea el estado de cuentas y proxies problemáticos después de un período de tiempo
        para darles otra oportunidad
        """
        threshold_date = datetime.now() - timedelta(days=days_threshold)
        threshold_iso = threshold_date.isoformat()
        
        # Resetear cuentas problemáticas
        for email, data in self.accounts_db.items():
            if data["status"] == "problem" and data["last_used"]:
                if data["last_used"] < threshold_iso:
                    logger.info(f"Reseteando estado de cuenta problemática: {email}")
                    self.accounts_db[email]["status"] = "active"
        
        # Resetear proxies problemáticos
        for proxy_id, data in self.proxies_db.items():
            if data["status"] == "problem" and data["last_used"]:
                if data["last_used"] < threshold_iso:
                    logger.info(f"Reseteando estado de proxy problemático: {proxy_id}")
                    self.proxies_db[proxy_id]["status"] = "active"
        
        # Guardar cambios
        self._save_accounts_db()
        self._save_proxies_db()
        
        logger.info("Reset de estados problemáticos completado")

# Instancia global para uso en otros módulos
account_manager = AccountManager()

if __name__ == "__main__":
    # Ejemplo de uso
    manager = AccountManager()
    
    # Obtener cuenta y proxy para un dispositivo
    device_id = "test_device_001"
    email, password = manager.get_account_for_device(device_id)
    if email:
        proxy = manager.get_proxy_for_account(email, device_id)
        print(f"Cuenta asignada: {email}:{password}")
        print(f"Proxy asignado: {proxy}")
        
        # Simular inicio de sesión exitoso
        manager.report_login_success(email, device_id)
    else:
        print("No hay cuentas disponibles")
