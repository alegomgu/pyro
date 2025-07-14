import os
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
import numpy as np
import csv
from datetime import datetime

def paint_graphs(csv_path: str):
    print("📥 Iniciando generación de gráficos...")

    # Asegurar ruta absoluta al CSV (en raíz del proyecto)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    print(f"🔍 Base directory: {base_dir}")

    csv_path = os.path.join(base_dir, csv_path)
    print(f"📄 Ruta al CSV: {csv_path}")

    # Carpeta de salida para gráficos
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    print(f"📂 Carpeta para resultados: {results_dir}")

    # Cargar CSV
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ Error cargando CSV: {e}")
        return

    df['tae'] = pd.to_numeric(df['tae'], errors='coerce')
    df['rentabilidad_total'] = pd.to_numeric(df['rentabilidad_total'], errors='coerce')
    df['fecha_simulacion'] = pd.to_datetime(df['fecha_simulacion'], errors='coerce')
    df = df.dropna(subset=['tae', 'rentabilidad_total', 'fecha_simulacion'])

    print(f"✅ CSV cargado: {len(df)} registros válidos")

    # --- Gráfico 1: Histograma de TAE ---
    tae = df['tae'].dropna()
    media = tae.mean()
    std = tae.std()

    print(f"📊 Histograma TAE -> media: {media:.4f}, std: {std:.4f}")

    plt.figure(figsize=(10, 6))
    plt.hist(tae, bins=20, density=True, alpha=0.6, color='skyblue', edgecolor='black')
    x = np.linspace(tae.min(), tae.max(), 100)
    plt.plot(x, norm.pdf(x, media, std), 'r--', linewidth=2, label=f"N(μ={media:.3f}, σ={std:.3f})")
    plt.title("📊 Distribución de TAE con Curva Normal")
    plt.xlabel("TAE")
    plt.ylabel("Densidad")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    hist_path = os.path.join(results_dir, "tae_histograma.png")
    plt.savefig(hist_path)
    print(f"✅ Histograma guardado en: {hist_path}")
    plt.close()

    # --- Gráfico 2: Rentabilidad temporal con regresión ---
    df_sorted = df.sort_values("fecha_simulacion")
    x_dates = df_sorted["fecha_simulacion"]
    y_rent = df_sorted["rentabilidad_total"]
    x_num = (x_dates - x_dates.min()).dt.total_seconds()

    # Validación antes del ajuste
    mask = np.isfinite(x_num) & np.isfinite(y_rent)
    x_num_clean = x_num[mask]
    y_rent_clean = y_rent[mask]

    if len(x_num_clean) < 2:
        print("⚠️ Datos insuficientes para regresión lineal. Gráfico 2 no generado.")
        return

    coef = np.polyfit(x_num_clean, y_rent_clean, 1)
    poly1d_fn = np.poly1d(coef)

    print(f"📈 Regresión lineal: pendiente = {coef[0]:.6f}, intersección = {coef[1]:.2f}")

    plt.figure(figsize=(12, 6))
    plt.plot(x_dates.values, y_rent.values, marker='o', linestyle='-', markersize=3, label="Rentabilidad")
    plt.plot(x_dates.values, poly1d_fn(x_num), color='red', linestyle='--', label="Tendencia (Regresión lineal)")
    plt.title("📈 Evolución Temporal de la Rentabilidad Total")
    plt.xlabel("Fecha de simulación")
    plt.ylabel("Rentabilidad total")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    reg_path = os.path.join(results_dir, "evolucion_rentabilidad_con_regresion.png")
    plt.savefig(reg_path)
    print(f"✅ Gráfico de regresión guardado en: {reg_path}")
    plt.close()

    print("✅ Todos los gráficos fueron generados exitosamente.")

def resume(csv_path: str, ultimas_n: int = 10) -> str:
    df = pd.read_csv(csv_path)

    if "tae" not in df.columns:
        return "❌ No se encontró la columna 'tae' en el CSV."

    df = df.dropna(subset=["tae"])

    # Estadísticas generales
    media_tae = df["tae"].mean()
    std_tae = df["tae"].std()
    max_tae = df["tae"].max()
    min_tae = df["tae"].min()

    # Últimas N simulaciones
    ultimos = df.tail(ultimas_n)
    media_tae_ult = ultimos["tae"].mean()
    std_tae_ult = ultimos["tae"].std()

    # Rentabilidad y comisión media
    rentabilidad_media = df["rentabilidad_total"].mean()
    comision_media = df["comision_total"].mean()

    resumen = f"""
📈 *Resumen de Simulaciones*
📊 Simulaciones totales: {len(df)}

🔹 *TAE (todas):*
   - Media: {media_tae:.4f}
   - Desviación: {std_tae:.4f}
   - Máx: {max_tae:.4f}
   - Mín: {min_tae:.4f}

🔹 *TAE (últimas {ultimas_n}):*
   - Media: {media_tae_ult:.4f}
   - Desviación: {std_tae_ult:.4f}

🔹 Rentabilidad total promedio: {rentabilidad_media:.4f}
🔹 Comisión promedio: ${comision_media:.2f}
""".strip()

    return resumen


def save_resume(simulator, sp, tasacion, p, archivo= None):
    if archivo is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        archivo = os.path.join(base_dir, "tests.csv")
    fecha_inicio = simulator.initialDate.strftime("%Y-%m-%d")
    fecha_fin = sp.current.strftime("%Y-%m-%d")
    dinero_inicial = simulator.initialMoney
    dinero_final = tasacion
    dias = (sp.current - simulator.initialDate).days + 1
    tae = (dinero_final / dinero_inicial) ** (365 / dias) - 1
    rentabilidad_total = dinero_final / dinero_inicial - 1

    headers = [
        "fecha_simulacion", "fecha_inicio", "fecha_fin", "dinero_inicial", "dinero_final",
        "rentabilidad_total", "tae", "apalancamiento", "margen", "comision_total",
        "numberStocksInPortfolio", "prediccion", "percentil", "rlog_size"
    ]

    try:
        with open(archivo, "x", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
    except FileExistsError:
        pass

    with open(archivo, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writerow({
            "fecha_simulacion": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "dinero_inicial": round(dinero_inicial, 2),
            "dinero_final": round(dinero_final, 2),
            "rentabilidad_total": round(rentabilidad_total, 4),
            "tae": round(tae, 4),
            "apalancamiento": p["apalancamiento"],
            "margen": p["orderMarginBuy"],
            "comision_total": round(simulator.totalComision, 2),
            "numberStocksInPortfolio": p["numberStocksInPortfolio"],
            "prediccion": p["prediccion"],
            "percentil": p["percentil"],
            "rlog_size": p["rlog_size"],
        })
