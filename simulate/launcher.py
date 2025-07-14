import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from utils.telegram_utils import TelegramBot
from utils.summary import paint_graphs, resume  # Importar la función corregida

# Rutas absolutas
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CONFIG_DIR = os.path.abspath(os.path.dirname(__file__))

csv_path = os.path.join(ROOT_DIR, "tests.csv")
config_file = os.path.join(CONFIG_DIR, "config_tests.json")
results_dir = os.path.join(ROOT_DIR, "results")

# Leer configuraciones
with open(config_file, "r") as f:
    configs = json.load(f)

# Crear instancia del bot
bot = TelegramBot()
bot.send_message(f"📆 *Inicio de simulaciones paralelas ({len(configs)})*")

def ejecutar_simulacion(config):
    cmd = ["python", os.path.join(ROOT_DIR, "simulate", "simulateMulti.py")]
    for key, value in config.items():
        cmd.extend([f"--{key}", str(value)])
    inicio = time.time()
    subprocess.run(cmd)
    duracion = time.time() - inicio
    return config, duracion

# Ejecutar en paralelo usando hilos (ThreadPool)
tiempos = []
with ThreadPoolExecutor(max_workers=4) as executor:
    for config, dur in executor.map(ejecutar_simulacion, configs):
        tiempos.append((config, dur))
        print(f"✔️ {config} completado en {dur/60:.2f} min")

# Mensaje final
msg = f"📆 *Fin de simulaciones {datetime.now():%H:%M}*"
msg += "\n".join([f"🔹 Simulación {i+1}: {dur:.1f} segundos" for i, (_, dur) in enumerate(tiempos)])
bot.send_message(msg)

# Resumen y gráficos
bot.send_message(resume(csv_path, ultimas_n=len(configs)))
paint_graphs(csv_path)
for file in ["tae_histograma.png", "evolucion_rentabilidad_con_regresion.png"]:
    with open(os.path.join(results_dir, file), "rb") as f:
        bot.send_photo(f)
