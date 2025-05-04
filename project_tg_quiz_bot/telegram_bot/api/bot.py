import logging.config
import os
import telebot
from dotenv import find_dotenv, load_dotenv

from telegram_bot.api.endpoints import questionsAnswers, adminMenu, adminWork, adminImg

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

load_dotenv(find_dotenv(usecwd=True))
TOKEN = os.getenv("BOT_TOKEN")

if TOKEN is None:
    logger.error("BOT_TOKEN is not set in the environment variables.")
    exit(1)

bot = telebot.TeleBot(TOKEN, parse_mode=None)
bot.set_chat_menu_button()

questionsAnswers.register_handlers(bot)
adminMenu.register_handlers(bot)
adminWork.register_handlers(bot)
adminImg.register_handlers(bot)

def start_bot():
    logger.info(f"bot `{str(bot.get_me().username)}` has started")
    bot.infinity_polling()