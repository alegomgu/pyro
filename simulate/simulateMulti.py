import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import numpy as np
import pandas as pd
from datetime import datetime
from market.source import Source
from market.sourcePerDay import SourcePerDay
from market.simulator import Simulator
from market.evaluacion import EstrategiaValuacionConSP500 as EstrategiaValuacion
from strategyClient import StrategyClient as Strategy
from utils.summary import save_resume
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()
EMAIL = os.getenv("EMAIL")
API_KEY = os.getenv("API_KEY")

def main(params):
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    sp500 = pd.read_html(url)[0]
    tickers = sp500['Symbol'].tolist()

    today = pd.Timestamp.now().normalize()
    stoday = today.strftime("%Y-%m-%d")

    p = {
        "fecha_inicio": "2019-01-01",
        "fecha_fin": stoday,
        "money": float(params.get("money", 100000)),
        "numberStocksInPortfolio": int(params.get("numberStocksInPortfolio", 10)),
        "orderMarginBuy": float(params.get("margen", 0.005)),
        "orderMarginSell": float(params.get("margen", 0.005)),
        "apalancamiento": float(params.get("apalancamiento", 10 / 6)),
        "ring_size": int(params.get("ring_size", 252)),
        "rlog_size": int(params.get("rlog_size", 22)),
        "cabeza": int(params.get("cabeza", 5)),
        "seeds": int(params.get("seeds", 100)),
        "percentil": int(params.get("percentil", 95)),
        "prediccion": int(params.get("prediccion", 1)),
        "key": API_KEY,
        "email": EMAIL
    }

    source = Source(tickers, p["fecha_inicio"], p["fecha_fin"], intervalo="1d")
    sp = SourcePerDay(source)
    p["tickers"] = sp.symbols

    simulator = Simulator(sp.symbols)
    simulator.money = p["money"]
    s = Strategy(p)

    while True:
        orders = s.open(sp.open)
        for order in orders["programBuy"]:
            simulator.programBuy(order["id"], order["price"], order["amount"])
        for order in orders["programSell"]:
            simulator.programSell(order["id"], order["price"], order["amount"])
        s.execute(sp.low, sp.high, sp.close, sp.current)
        tasacion = simulator.execute(sp.low, sp.high, sp.close, sp.current)
        if not sp.nextDay():
            break

    save_resume(simulator, sp, tasacion, p)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--apalancamiento", type=float, default=10/6)
    parser.add_argument("--margen", type=float, default=0.005)
    parser.add_argument("--numberStocksInPortfolio", type=int, default=10)
    parser.add_argument("--prediccion", type=int, default=1)
    parser.add_argument("--percentil", type=int, default=95)
    parser.add_argument("--rlog_size", type=int, default=24)
    parser.add_argument("--ring_size", type=int, default=240)
    parser.add_argument("--money", type=float, default=100000)

    args = vars(parser.parse_args())
    main(args)
