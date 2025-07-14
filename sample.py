from market.source import Source
from market.sourcePerDay import SourcePerDay
import numpy as np
import pandas as pd
from market.simulator import Simulator
from market.evaluacion import EstrategiaValuacionConSP500 as EstrategiaValuacion
from strategyClient import StrategyClient as Strategy
from utils.telegram_utils import TelegramBot
import time
from datetime import datetime, timedelta
from utils.summary import paint_graphs, resume, save_resume  # Importar la función corregida
import os
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()
EMAIL = os.getenv("EMAIL")
API_KEY = os.getenv("API_KEY")

bot = TelegramBot()

try:

    bot.send_message("💵 *Lanzando estrategia en entorno real...*")
    # Leer la tabla de Wikipedia
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
        "orderMarginBuy": 0.008,
        "orderMarginSell": 0.008,
        "apalancamiento": 1.5,
        "ring_size": 252,
        "rlog_size": 22,
        "cabeza": 5,
        "seeds": 100,
        "percentil": 95,
        "prediccion": 5,
        "key": API_KEY,
        "email": EMAIL
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
        hay = sp.nextDay()
        if not hay:
            break

    # ev.print()
    bot.send_message("📡 *Conectando a IB Gateway...*")

    from driver.driverIB import DriverIB as Driver
    d = Driver(4001)
    d.conectar()
    bot.send_message("✅ *Conectado a IB Gateway.*")

    s.set_profolio(d.cash(), d.profolio(sp.symbols))
    orders = s.open(source.realTime(sp.symbols))
    d.clearOrders()

    msg = f"📆 *Órdenes del día {datetime.now().strftime('%Y-%m-%d')}*\n\n"

    if not orders["programBuy"] and not orders["programSell"]:
        msg += "ℹ️ *No se han generado órdenes para hoy.*"
        bot.send_message(msg)
    else:
        # 8. Enviar órdenes BUY
        msg += "🟢 *COMPRAR*\n"
        for order in orders["programBuy"]:
            precio = round(order['price'], 2)
            cantidad = int(round(order['amount'] / precio))
            msg += f"• {cantidad} acciones de {sp.symbols[order['id']]} a ${precio:.2f}\n"
            d.buy_limit(sp.symbols[order['id']], cantidad, precio)

        # 9. Enviar órdenes SELL
        msg += "\n🔴 *VENDER*\n"
        for order in orders["programSell"]:
            precio = round(order['price'], 2)
            cantidad = order['amount'] / precio
            msg += f"• {cantidad:.2f} acciones de {sp.symbols[order['id']]} a ${precio:.2f}\n"
            d.sell_limit(sp.symbols[order['id']], cantidad, precio)

        bot.send_message(msg)


    save_resume(simulator, sp, tasacion, p)
    bot.send_message("✅ *🟢 Operativa completada exitosamente*")

    base_dir = os.path.abspath(os.path.dirname(__file__))
    csv_path = os.path.join(base_dir, "tests.csv")
    results_dir = os.path.join(base_dir, "results")

    # Generar y enviar resumen
    msg = resume(csv_path, ultimas_n=1)
    bot.send_message(msg)

    # Generar y enviar gráficos
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
