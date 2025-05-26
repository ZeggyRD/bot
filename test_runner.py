#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import logging
import subprocess
import traceback
from datetime import datetime
import json
import argparse

# Configuración del sistema de logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"test_runner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TestRunner")

# Constantes
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Módulos disponibles para pruebas
MODULES = {
    "login": "spotify_login.py",
    "proxy": "set_proxy.py",
    "track": "track_player.py",
    "artist": "artist_player.py",
    "playlist": "playlist_player.py"
}

def get_connected_devices():
    """Obtiene la lista de dispositivos Android conectados"""
    try:
        logger.debug("Obteniendo dispositivos conectados")
        
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True
        )
        
        if result.stderr:
            logger.error(f"Error al ejecutar 'adb devices': {result.stderr}")
        
        logger.debug(f"Resultado de 'adb devices':\n{result.stdout}")
        
        lines = result.stdout.strip().split("\n")[1:]  # Ignorar la primera línea (título)
        devices = []
        
        for line in lines:
            if line.strip() and "device" in line and not "offline" in line:
                device_id = line.split()[0]
                devices.append(device_id)
        
        logger.info(f"Dispositivos conectados: {devices}")
        return devices
    except Exception as e:
        logger.error(f"Error al obtener dispositivos conectados: {e}")
        logger.debug(traceback.format_exc())
        return []

def get_device_info(device_id):
    """Obtiene información detallada del dispositivo"""
    try:
        logger.debug(f"Obteniendo información del dispositivo {device_id}")
        
        # Obtener modelo
        model_result = subprocess.run(
            ["adb", "-s", device_id, "shell", "getprop", "ro.product.model"],
            capture_output=True,
            text=True
        )
        model = model_result.stdout.strip()
        
        # Obtener versión de Android
        android_version_result = subprocess.run(
            ["adb", "-s", device_id, "shell", "getprop", "ro.build.version.release"],
            capture_output=True,
            text=True
        )
        android_version = android_version_result.stdout.strip()
        
        # Obtener fabricante
        manufacturer_result = subprocess.run(
            ["adb", "-s", device_id, "shell", "getprop", "ro.product.manufacturer"],
            capture_output=True,
            text=True
        )
        manufacturer = manufacturer_result.stdout.strip()
        
        device_info = {
            "id": device_id,
            "model": model,
            "manufacturer": manufacturer,
            "android_version": android_version
        }
        
        logger.info(f"Información del dispositivo {device_id}: {device_info}")
        return device_info
    except Exception as e:
        logger.error(f"Error al obtener información del dispositivo {device_id}: {e}")
        logger.debug(traceback.format_exc())
        return {"id": device_id, "model": "Unknown", "manufacturer": "Unknown", "android_version": "Unknown"}

def run_module_test(module_name, device_id, run_number, duration=30):
    """Ejecuta una prueba de un módulo específico en un dispositivo"""
    try:
        if module_name not in MODULES:
            logger.error(f"Módulo no válido: {module_name}")
            return False
        
        script_path = os.path.join(SCRIPTS_DIR, MODULES[module_name])
        if not os.path.exists(script_path):
            logger.error(f"Script no encontrado: {script_path}")
            return False
        
        logger.info(f"Iniciando prueba de {module_name} en dispositivo {device_id} (corrida {run_number})")
        
        # Crear directorio para resultados de esta prueba
        test_dir = os.path.join(RESULTS_DIR, f"{module_name}_{device_id}_run{run_number}")
        os.makedirs(test_dir, exist_ok=True)
        
        # Archivo para guardar la salida
        output_file = os.path.join(test_dir, "output.log")
        
        # Comando para ejecutar el script con timeout
        cmd = ["python", script_path]
        
        # Iniciar el proceso
        logger.debug(f"Ejecutando comando: {' '.join(cmd)}")
        
        with open(output_file, 'w') as f:
            process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Esperar el tiempo especificado
            logger.info(f"Esperando {duration} segundos para la prueba")
            time.sleep(duration)
            
            # Terminar el proceso
            logger.debug("Terminando proceso")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("El proceso no terminó, forzando finalización")
                process.kill()
        
        # Guardar información de la prueba
        test_info = {
            "module": module_name,
            "device_id": device_id,
            "run_number": run_number,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "output_file": output_file
        }
        
        with open(os.path.join(test_dir, "test_info.json"), 'w') as f:
            json.dump(test_info, f, indent=4)
        
        logger.info(f"Prueba completada: {module_name} en {device_id} (corrida {run_number})")
        return True
    except Exception as e:
        logger.error(f"Error al ejecutar prueba de {module_name} en {device_id}: {e}")
        logger.debug(traceback.format_exc())
        return False

def run_all_tests(devices, runs_per_module=5, duration_per_run=30):
    """Ejecuta todas las pruebas en todos los dispositivos"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "devices": [],
        "modules": {},
        "success_rate": {}
    }
    
    # Obtener información de los dispositivos
    for device_id in devices:
        device_info = get_device_info(device_id)
        results["devices"].append(device_info)
    
    # Inicializar contadores de éxito
    for module in MODULES:
        results["modules"][module] = {
            "total_runs": len(devices) * runs_per_module,
            "successful_runs": 0,
            "failed_runs": 0
        }
        results["success_rate"][module] = 0
    
    # Ejecutar pruebas para cada módulo en cada dispositivo
    for module in MODULES:
        logger.info(f"Iniciando pruebas del módulo {module}")
        
        for device_id in devices:
            logger.info(f"Probando {module} en dispositivo {device_id}")
            
            for run in range(1, runs_per_module + 1):
                success = run_module_test(module, device_id, run, duration_per_run)
                
                if success:
                    results["modules"][module]["successful_runs"] += 1
                else:
                    results["modules"][module]["failed_runs"] += 1
    
    # Calcular tasas de éxito
    for module in MODULES:
        total = results["modules"][module]["total_runs"]
        successful = results["modules"][module]["successful_runs"]
        
        if total > 0:
            success_rate = (successful / total) * 100
        else:
            success_rate = 0
        
        results["success_rate"][module] = success_rate
    
    # Guardar resultados
    results_file = os.path.join(RESULTS_DIR, f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=4)
    
    logger.info(f"Resultados de pruebas guardados en {results_file}")
    return results

def generate_markdown_report(results):
    """Genera un informe en formato Markdown con los resultados de las pruebas"""
    try:
        report = f"""# Informe de Pruebas - OTW Music System

## Resumen de Pruebas
- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Dispositivos probados: {len(results["devices"])}
- Módulos probados: {len(MODULES)}

## Dispositivos

| ID | Fabricante | Modelo | Versión Android |
|----|------------|--------|----------------|
"""
        
        for device in results["devices"]:
            report += f"| {device['id']} | {device['manufacturer']} | {device['model']} | {device['android_version']} |\n"
        
        report += """
## Resultados por Módulo

| Módulo | Ejecuciones Totales | Ejecuciones Exitosas | Ejecuciones Fallidas | Tasa de Éxito |
|--------|---------------------|---------------------|---------------------|--------------|
"""
        
        for module, data in results["modules"].items():
            report += f"| {module} | {data['total_runs']} | {data['successful_runs']} | {data['failed_runs']} | {results['success_rate'][module]:.2f}% |\n"
        
        report += """
## Análisis de Resultados

"""
        
        # Analizar resultados
        all_success = True
        for module, rate in results["success_rate"].items():
            if rate < 90:
                all_success = False
                report += f"- ⚠️ El módulo **{module}** tiene una tasa de éxito baja ({rate:.2f}%). Se recomienda revisión.\n"
        
        if all_success:
            report += "✅ Todos los módulos tienen tasas de éxito aceptables (>90%).\n"
        
        report += """
## Conclusiones y Recomendaciones

"""
        
        # Generar conclusiones basadas en los resultados
        if all_success:
            report += """- El sistema muestra un rendimiento estable en todos los dispositivos probados.
- Se recomienda continuar con la fase de implementación.
- Monitorear el rendimiento en producción para detectar posibles problemas no identificados en pruebas."""
        else:
            report += """- Se han detectado problemas en algunos módulos que requieren atención.
- Se recomienda revisar los logs detallados de las pruebas fallidas.
- Corregir los problemas identificados antes de avanzar a producción."""
        
        # Guardar el informe
        report_file = os.path.join(RESULTS_DIR, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Informe de pruebas generado en {report_file}")
        return report_file
    except Exception as e:
        logger.error(f"Error al generar informe de pruebas: {e}")
        logger.debug(traceback.format_exc())
        return None

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Ejecutor de pruebas para OTW Music System")
    parser.add_argument("--module", choices=list(MODULES.keys()) + ["all"], default="all", help="Módulo a probar")
    parser.add_argument("--runs", type=int, default=5, help="Número de corridas por módulo")
    parser.add_argument("--duration", type=int, default=30, help="Duración de cada prueba en segundos")
    args = parser.parse_args()
    
    logger.info("Iniciando ejecutor de pruebas")
    
    # Obtener dispositivos conectados
    devices = get_connected_devices()
    if not devices:
        logger.error("No hay dispositivos conectados. Abortando.")
        return 1
    
    if args.module == "all":
        # Ejecutar todas las pruebas
        results = run_all_tests(devices, args.runs, args.duration)
        
        # Generar informe
        report_file = generate_markdown_report(results)
        if report_file:
            logger.info(f"Proceso completado. Informe disponible en: {report_file}")
        else:
            logger.error("No se pudo generar el informe de pruebas")
    else:
        # Ejecutar pruebas para un módulo específico
        for device_id in devices:
            for run in range(1, args.runs + 1):
                run_module_test(args.module, device_id, run, args.duration)
        
        logger.info(f"Pruebas completadas para el módulo {args.module}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
