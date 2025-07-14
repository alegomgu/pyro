from market.source import Source
from market.sourcePerDay import SourcePerDay
import numpy as np
import pandas as pd
from market.simulator import Simulator
from market.evaluacion import EstrategiaValuacionConSP500 as EstrategiaValuacion
from strategyClient import StrategyClient as Strategy
from utils.telegram_utils import TelegramBot
import time
from datetime import datetime
from utils.summary import paint_graphs, resume,save_resume  # Importar la función corregida
import os
import csv
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LOG_FILE = "intraday_log.csv"
HORA_LIMITE = 18  # Hora límite para salir del loop (18:00)

# === FUNCIONES AUXILIARES ===

def formatear_ordenes(orders, symbols, driver):
    msg = f"📆 *Órdenes detectadas a las {datetime.now().strftime('%H:%M:%S')}*\n\n"
    hay_ordenes = False
    ordenes_detalle = []

    if orders["programBuy"]:
        msg += "🟢 *COMPRAR*\n"
        for order in orders["programBuy"]:
            precio = round(order['price'], 2)
            cantidad = int(round(order['amount'] / precio))
            symbol = symbols[order['id']]
            msg += f"• {cantidad} acciones de {symbol} a ${precio:.2f}\n"
            driver.buy_limit(symbol, cantidad, precio)
            ordenes_detalle.append((symbol, "BUY", cantidad, precio))
        hay_ordenes = True

    if orders["programSell"]:
        msg += "\n🔴 *VENDER*\n"
        for order in orders["programSell"]:
            precio = round(order['price'], 2)
            cantidad = round(order['amount'] / precio, 2)
            symbol = symbols[order['id']]
            msg += f"• {cantidad:.2f} acciones de {symbol} a ${precio:.2f}\n"
            driver.sell_limit(symbol, cantidad, precio)
            ordenes_detalle.append((symbol, "SELL", cantidad, precio))
        hay_ordenes = True

    return msg, hay_ordenes, ordenes_detalle

def log_ordenes_csv(ordenes):
    if not ordenes:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        for symbol, action, qty, price in ordenes:
            writer.writerow([now, symbol, action, qty, price])



bot = TelegramBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

try:
    bot.send_message("💵 *Lanzando estrategia en entorno real...*")

    # === CARGA DE DATOS ===
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tablas = pd.read_html(url)
    sp500 = tablas[0]
    tickers = sp500['Symbol'].tolist()

    today = pd.Timestamp.now().normalize()
    stoday = today.strftime("%Y-%m-%d")

    p = {
        "fecha_inicio": "2019-01-01",
        "fecha_fin": stoday,
        "money": 2500,
        "numberStocksInPortfolio": 10,
        "orderMarginBuy": 0.005,
        "orderMarginSell": 0.005,
        "apalancamiento": 0.3,
        "ring_size": 240,
        "rlog_size": 24,
        "cabeza": 5,
        "seeds": 100,
        "percentil": 95,
        "prediccion": 1,
        "key": "165eb9a080b54584a4a0e8d789c4a8ca",
        "email": "alegomgu@outlook.com",
    }

    source = Source(
        lista_instrumentos=tickers,
        fecha_inicio=p["fecha_inicio"],
        fecha_fin=p["fecha_fin"],
        intervalo="1d"
    )

    sp = SourcePerDay(source)
    p["tickers"] = sp.symbols

    simulator = Simulator(sp.symbols)
    simulator.money = p["money"]
    s = Strategy(p)

    # === BACKTEST ===
    ev = EstrategiaValuacion()
    while True:
        orders = s.open(sp.open)
        for order in orders["programBuy"]:
            simulator.programBuy(order["id"], order["price"], order["amount"])
        for order in orders["programSell"]:
            simulator.programSell(order["id"], order["price"], order["amount"])
        s.execute(sp.low, sp.high, sp.close, sp.current)
        tasacion = simulator.execute(sp.low, sp.high, sp.close, sp.current)
        ev.add(sp.current, tasacion)
        if not sp.nextDay():
            break

    # === CONEXIÓN IB ===
    bot.send_message("📡 *Conectando a IB Gateway...*")
    from driver.driverIB import DriverIB as Driver
    d = Driver(4001)
    d.conectar()
    d.clearOrders()

    bot.send_message("✅ *Conectado a IB Gateway.*")

    s.set_portfolio(d.cash(), d.profolio(sp.symbols))

    # === INICIAR LOG SI NO EXISTE ===
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "symbol", "action", "quantity", "price"])

    # === LOOP CADA 10 MINUTOS ===
    hora_limite = datetime.now().replace(hour=HORA_LIMITE, minute=0, second=0, microsecond=0)

    while datetime.now() < hora_limite:
        orders = s.open(source.realTime(sp.symbols))

        msg, hay_ordenes, ordenes_detalle = formatear_ordenes(orders, sp.symbols, d)
        log_ordenes_csv(ordenes_detalle)

        if hay_ordenes:
            bot.send_message(msg)
            break
        else:
            bot.send_message(f"🕒 {datetime.now().strftime('%H:%M:%S')} – Sin señales aún. Reintentando en 10 minutos...")
            time.sleep(600)

    # === RESUMEN POST OPERATIVA ===
    save_resume(simulator, sp, tasacion, p)
    bot.send_message("✅ *🟢 Operativa completada exitosamente*")

    base_dir = os.path.abspath(os.path.dirname(__file__))
    csv_path = os.path.join(base_dir, "tests.csv")
    results_dir = os.path.join(base_dir, "results")

    msg = resume(csv_path, ultimas_n=1)
    bot.send_message(msg)

    paint_graphs(csv_path)

    for filename in ["tae_histograma.png", "evolucion_rentabilidad_con_regresion.png"]:
        full_path = os.path.join(results_dir, filename)
        try:
            with open(full_path, "rb") as f:
                bot.send_photo(f)
        except Exception as e:
            print(f"❌ Error enviando gráfico {filename}: {e}")

except Exception as e:
    error_msg = f"❌ *Error durante la ejecución:* `{str(e)}`"
    bot.send_message(error_msg)
    raise


