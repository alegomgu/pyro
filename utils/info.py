from ib_insync import IB, LimitOrder, Contract
import pytz
import datetime
import math
import requests
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv
import os

# Cargar las variables del archivo .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

class DriverIB:
    def __init__(self, puerto):
        self.puerto = puerto
        self.ib = None

    def conectar(self):
        self.ib = IB()
        self.ib.connect('127.0.0.1', self.puerto, clientId=15)

    def cash(self):
        account = self.ib.accountSummary()
        for a in account:
            if a.tag in ("CashBalance", "TotalCashBalance", "TotalCashValue") and a.currency == "USD":
                return float(a.value)
        return 0.0

def send_telegram_message(message: str, token: str, chat_id: str):
    """
    Envía un mensaje a Telegram manejando correctamente emojis y caracteres especiales.
    """
    import requests

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    safe_message = message.encode('utf-16', 'surrogatepass').decode('utf-16')
    payload = {
        "chat_id": chat_id,
        "text": safe_message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Error al enviar mensaje por Telegram: {e}")


def resumen_driver_ib(driver):
    msg = "\ud83d\udcca *Resumen diario IB*\n\n"
    ps = driver.ib.portfolio()
    total_diff = 0

    for p in ps:
        symbol = p.contract.symbol
        position = p.position
        if position < 1:
            continue
        price = p.marketPrice
        avg_cost = p.averageCost
        pct = ((price - avg_cost) / avg_cost) * 100 if avg_cost != 0 else 0
        total_diff += (price - avg_cost) * position

        msg += (
            f"{symbol}: {position} acciones\n"
            f"  \ud83d\udfe2 Compra: ${avg_cost:.2f} | \ud83d\udcc8 Actual: ${price:.2f}\n"
            f"  \ud83d\udcca Total: ${(price - avg_cost) * position:+.2f} ({pct:+.2f}%)\n\n"
        )

    cash = driver.cash()
    msg += f"\ud83d\udcb5 Efectivo en cuenta: ${cash:.2f}\n"
    msg += f"\ud83d\udcc8 Variaci\u00f3n total (no realizada): ${total_diff:+.2f}"

    return msg

def resumen_yfinance(driver):
    ps = driver.ib.portfolio()
    portfolio = [
        {"ticker": p.contract.symbol, "shares": p.position, "cost_basis": p.averageCost}
        for p in ps if p.position > 0
    ]

    def fetch_data(entry):
        t = yf.Ticker(entry["ticker"])
        hist = t.history(period="1d", interval="1m")
        last_price = hist["Close"].iloc[-1]
        open_price = hist["Open"].iloc[0]

        total_cost = entry["cost_basis"] * entry["shares"]
        market_value = last_price * entry["shares"]
        gain = market_value - total_cost
        gain_pct = (gain / total_cost) * 100

        daily_diff = (last_price - open_price) * entry["shares"]
        daily_pct = (last_price - open_price) / open_price * 100

        return {
            "Ticker": entry["ticker"],
            "Shares": entry["shares"],
            "Last Price": round(last_price, 2),
            "Open Price": round(open_price, 2),
            "AC/Share": entry["cost_basis"],
            "Total Cost ($)": round(total_cost, 2),
            "Market Value ($)": round(market_value, 2),
            "Tot Gain UNRL ($)": round(gain, 2),
            "Tot Gain UNRL (%)": f"{gain_pct:.2f}%",
            "Daily G/P ($)": round(daily_diff, 2),
            "Daily G/P (%)": f"{daily_pct:.2f}%"
        }

    data = [fetch_data(stock) for stock in portfolio]
    df = pd.DataFrame(data)

    df.loc["TOTAL"] = {
        "Ticker": "TOTAL",
        "Shares": "",
        "Last Price": "",
        "Open Price": "",
        "AC/Share": "",
        "Total Cost ($)": df["Total Cost ($)"].sum(),
        "Market Value ($)": df["Market Value ($)"].sum(),
        "Tot Gain UNRL ($)": df["Tot Gain UNRL ($)"].sum(),
        "Tot Gain UNRL (%)": "",
        "Daily G/P ($)": df["Daily G/P ($)"].sum(),
        "Daily G/P (%)": "",
    }

    msg = "\ud83d\udcc8 *Resumen YFinance*\n\n"
    for idx, row in df.iterrows():
        if row["Ticker"] == "TOTAL":
            msg += (
                f"\ud83e\uddee *TOTAL*:\n"
                f"  \ud83d\udcb0 Costo Total: ${row['Total Cost ($)']:.2f}\n"
                f"  \ud83d\udcbc Valor Mercado: ${row['Market Value ($)']:.2f}\n"
                f"  \ud83d\udcca G/P: ${row['Tot Gain UNRL ($)']:+.2f}\n"
                f"  \ud83d\udcc5 Diario: ${row['Daily G/P ($)']:+.2f}\n\n"
            )
        else:
            msg += (
                f"{row['Ticker']} ({row['Shares']} acciones)\n"
                f"  \ud83d\udce5 Compra: ${row['AC/Share']} | \ud83d\udfe2 Open: ${row['Open Price']} | \ud83d\udcc8 Ahora: ${row['Last Price']}\n"
                f"  \ud83d\udcca G/P Total: ${row['Tot Gain UNRL ($)']} ({row['Tot Gain UNRL (%)']})\n"
                f"  \ud83d\udcc5 Diario: ${row['Daily G/P ($)']} ({row['Daily G/P (%)']})\n\n"
            )

    return msg

if __name__ == "__main__":
    d = DriverIB(4001)
    d.conectar()

    msg_ib = resumen_driver_ib(d)
    send_telegram_message(msg_ib, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

    msg_yf = resumen_yfinance(d)
    send_telegram_message(msg_yf, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
