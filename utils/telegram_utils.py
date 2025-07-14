import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import requests
import asyncio
import itertools
from telegram.ext import Updater, CommandHandler
from telegram import ParseMode, Update
from ib_insync import IB
from utils.summary import paint_graphs, resume  # Importar la función corregida
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

class TelegramBot:
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.ib = IB()
        self.IB_PORT = 4001
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.CSV = os.path.join(base_dir, "tests.csv")

    def send_message(self, message: str, markdown: bool = True):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown" if markdown else None
        }
        try:
            resp = requests.post(url, data=payload)
            if not resp.ok:
                print(f"⚠️ Error en la respuesta de Telegram: {resp.text}")
        except Exception as e:
            print(f"❌ Error al enviar mensaje: {e}")

    def send_photo(self, photo_file):
        url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
        files = {'photo': photo_file}
        data = {'chat_id': self.chat_id}
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()

    # def resumen_command(self, update, context):
    #     try:
    #         asyncio.get_running_loop()
    #     except RuntimeError:
    #         loop = asyncio.new_event_loop()
    #         asyncio.set_event_loop(loop)

    #     if not self.ib.isConnected():
    #         try:
    #             self.ib.connect("127.0.0.1", self.IB_PORT, clientId=2)
    #         except Exception as e:
    #             context.bot.send_message(chat_id=update.effective_chat.id,
    #                                      text=f"❌ No se pudo conectar con IB: {e}")
    #             return

    #     if not self.ib.isConnected():
    #         context.bot.send_message(chat_id=update.effective_chat.id,
    #                                  text="❌ No se pudo conectar con IB. Intenta más tarde.")
    #         return

    #     msg = "📊 *Resumen diario IB*\n\n"
    #     ps = self.ib.portfolio()
    #     total_diff = 0

    #     for p in ps:
    #         symbol = p.contract.symbol
    #         position = p.position
    #         if position < 1:
    #             continue
    #         price = p.marketPrice
    #         avg_cost = p.averageCost
    #         diff = (price - avg_cost) * position
    #         pct = ((price - avg_cost) / avg_cost) * 100 if avg_cost != 0 else 0
    #         total_diff += diff
    #         msg += (
    #             f"{symbol}: {position} acciones\n"
    #             f"  🟢 Compra: ${avg_cost:.2f} | 📈 Actual: ${price:.2f}\n"
    #             f"  📊 Variación: ${diff:+.2f} ({pct:+.2f}%)\n\n"
    #         )

    #     cash = self.get_cash()
    #     msg += f"💵 Efectivo en cuenta: ${cash:.2f}\n"
    #     msg += f"📈 Variación total (no realizada): ${total_diff:+.2f}"

    #     update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    # def estadisticas(self, update, context):
    #     chat_id = update.effective_chat.id
    #     resumen = resume(self.CSV, ultimas_n=10)
    #     context.bot.send_message(chat_id=chat_id, text=resumen, parse_mode=ParseMode.MARKDOWN)

    #     paint_graphs(self.CSV)
    #     base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    #     results_dir = os.path.join(base_dir, "results")

    #     for filename in ["tae_histograma.png", "evolucion_rentabilidad_con_regresion.png"]:
    #         filepath = os.path.join(results_dir, filename)
    #         try:
    #             with open(filepath, 'rb') as f:
    #                 context.bot.send_photo(chat_id=chat_id, photo=f)
    #         except Exception as e:
    #             context.bot.send_message(chat_id=chat_id, text=f"❌ Error enviando gráfico {filename}: {e}")

    # def generar_config_command(self, update: Update, context):
    #     base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    #     config_path = os.path.join(base_dir, "config_tests.json")

    #     if not context.args:
    #         update.message.reply_text("❌ Debes enviar al menos una configuración. Usa /ayuda_config para ver el formato.")
    #         return

    #     try:
    #         combinaciones = {}
    #         for raw in context.args:
    #             if "(" not in raw or ")" not in raw:
    #                 update.message.reply_text(f"⚠️ Formato incorrecto en: {raw}")
    #                 return

    #             key, values_raw = raw.split("(", 1)
    #             values = values_raw.strip(")").split(",")
    #             values = [float(v) if "." in v else int(v) for v in values]
    #             combinaciones[key] = values

    #         claves = list(combinaciones.keys())
    #         valores = list(combinaciones.values())
    #         combinaciones_resultado = [dict(zip(claves, v)) for v in itertools.product(*valores)]

    #         with open(config_path, "w") as f:
    #             json.dump(combinaciones_resultado, f, indent=2)

    #         update.message.reply_text(
    #             f"✅ Se han guardado *{len(combinaciones_resultado)}* combinaciones en `config_tests.json`.",
    #             parse_mode=ParseMode.MARKDOWN
    #         )

    #     except Exception as e:
    #         update.message.reply_text(f"❌ Error procesando combinaciones: {e}")

    # def ayuda_config_command(self, update: Update, context):
    #     msg = (
    #         "ℹ️ *Uso del comando /generar_config*\n\n"
    #         "Permite generar combinaciones de simulaciones automáticamente.\n\n"
    #         "🧾 *Ejemplo:*\n"
    #         "`/generar_config apalancamiento(0.2,0.3,0.4) money(2000,2500)`\n\n"
    #         "🛠 Esto generará todas las combinaciones posibles entre los valores dados y las guardará en `config_tests.json`.\n"
    #         "👉 Puedes combinar cualquier parámetro definido en el script."
    #     )
    #     update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    # def get_cash(self):
    #     account = self.ib.accountSummary()
    #     for a in account:
    #         if a.tag in {"CashBalance", "TotalCashBalance", "TotalCashValue"} and a.currency == "USD":
    #             return float(a.value)
    #     return 0.0

    # def start_bot(self):
    #     updater = Updater(token=self.token, use_context=True)

    #     updates = updater.bot.get_updates()
    #     if updates:
    #         last_update_id = updates[-1].update_id
    #         updater.bot.get_updates(offset=last_update_id + 1)
    #         print(f"ℹ️ {len(updates)} mensajes antiguos descartados")

    #     dp = updater.dispatcher
    #     dp.add_handler(CommandHandler("resume", self.resumen_command))
    #     dp.add_handler(CommandHandler("stats", self.estadisticas))
    #     dp.add_handler(CommandHandler("generar_config", self.generar_config_command))
    #     dp.add_handler(CommandHandler("ayuda_config", self.ayuda_config_command))
    #     dp.add_handler(CommandHandler("ayuda_config", self.ejecutar_simulaciones_command))
    #     dp.add_handler(CommandHandler("ejecutar_simulaciones", self.ejecutar_simulaciones_command))


    #     print("✅ Bot activo esperando comandos: /resume /stats /generar_config /ayuda_config /ejecutar_simulaciones" )
    #     updater.start_polling()
    #     updater.idle()
    #     self.ib.disconnect()
    
    # def ejecutar_simulaciones_command(self, update: Update, context):
    #     update.message.reply_text("🚀 Iniciando simulaciones. Esto puede tardar varios minutos...", parse_mode=ParseMode.MARKDOWN)

    #     try:
    #         base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    #         launcher_path = os.path.join(base_dir, "simulate", "launchJSON.py")

    #         import subprocess
    #         subprocess.run(["python", launcher_path], check=True)

    #         update.message.reply_text("✅ Simulaciones completadas y resultados enviados.", parse_mode=ParseMode.MARKDOWN)

    #     except subprocess.CalledProcessError as e:
    #         update.message.reply_text(f"❌ Error al ejecutar las simulaciones:\n{e}", parse_mode=ParseMode.MARKDOWN)
    #     except Exception as e:
    #         update.message.reply_text(f"❌ Error inesperado:\n{e}", parse_mode=ParseMode.MARKDOWN)


# Ejecutar si se lanza como script directamente
if __name__ == '__main__':
    bot = TelegramBot()
    bot.start_bot()
