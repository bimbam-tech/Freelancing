import logging
from telebot import types

from telegram_bot.db.crud import check_id_admin

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def create_admin_markup():
    menu_markup = types.InlineKeyboardMarkup(row_width=1)
    menu_markup.add(
        types.InlineKeyboardButton("Работа с админами", callback_data="admins_work"), 
        types.InlineKeyboardButton("Работа с изображениями", callback_data="img_work") 
    )
    return menu_markup

menu_markup = create_admin_markup()

def register_handlers(bot):
    @bot.message_handler(commands=["admin"])
    def admin(message):
        if check_id_admin(message.from_user.id):
            bot.send_message(message.chat.id, "Добро пожаловать в админку!", reply_markup=menu_markup)