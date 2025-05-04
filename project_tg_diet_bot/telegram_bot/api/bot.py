import logging.config
import threading
import os
import schedule
import time
from datetime import datetime, timedelta
import telebot
from dotenv import find_dotenv, load_dotenv
from omegaconf import OmegaConf

from telegram_bot.api.endpoints import calculate, data, menu, nutrition_analysis, meal, report

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

load_dotenv(find_dotenv(usecwd=True))  # Load environment variables from .env file
TOKEN = os.getenv("BOT_TOKEN")

if TOKEN is None:
    logger.error("BOT_TOKEN is not set in the environment variables.")
    exit(1)

app_config = OmegaConf.load("./telegram_bot/conf/app.yaml")
bot = telebot.TeleBot(TOKEN, parse_mode=None)
bot.set_chat_menu_button()

menu.register_handlers(bot)
data.register_handlers(bot)
calculate.register_handlers(bot)
meal.register_handlers(bot)
nutrition_analysis.register_handlers(bot)

def start_bot():
    
    # Schedule the report function to run at 03:00 every night
    schedule.every(1440).minutes.do(report.send_daily_reports, bot)

    # Function to keep the script running
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)

    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    logger.info(f"bot `{str(bot.get_me().username)}` has started")
    bot.infinity_polling()
