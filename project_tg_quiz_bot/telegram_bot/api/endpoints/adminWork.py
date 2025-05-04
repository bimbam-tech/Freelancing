import logging
from telebot import types

from telegram_bot.db.crud import get_user_info, check_id_admin, get_all_admin_ids, delete_admin_by_id_tg, add_admin_by_id_tg

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def create_admin_markup():
    menu_markup = types.InlineKeyboardMarkup(row_width=1)
    menu_markup.add(
            types.InlineKeyboardButton("Удалить админа", callback_data="del_admin"), 
            types.InlineKeyboardButton("Добавить админа", callback_data="add_admin") 
    )
    return menu_markup

menu_markup = create_admin_markup()

def register_handlers(bot):       
    @bot.callback_query_handler(func=lambda call: call.data == 'admins_work')
    def admins_check(call):
        chat_id = call.message.chat.id
        bot.send_message(chat_id, f'Список админов: {get_all_admin_ids()}', reply_markup=menu_markup)
        
    @bot.callback_query_handler(func=lambda call: call.data == 'del_admin')
    def del_admin(call):
        user = get_user_info(call.message.from_user.username)
        msg = bot.send_message(call.message.chat.id, 'Укажите id админа')
        bot.register_next_step_handler(msg, get_id_admin_for_del)
        
    def get_id_admin_for_del(message):
        id_admin = int(message.text)
        
        if check_id_admin(id_admin):
            if delete_admin_by_id_tg(id_admin):
                bot.send_message(message.chat.id, f'Админ {id_admin} успешно удален.')
            else:
                bot.send_message(message.chat.id, f'Админ {id_admin} не удалён, какая та ошибка.')
        else:
            bot.send_message(message.chat.id, f'Админ {id_admin} не найден в списке. Попробуйте заново, введите команду /admin')

    @bot.callback_query_handler(func=lambda call: call.data == 'add_admin')
    def add_admin(call):
        user = get_user_info(call.message.from_user.username)
        msg = bot.send_message(call.message.chat.id, 'Укажите id админа')
        bot.register_next_step_handler(msg, get_id_admin_for_add)
        
    def get_id_admin_for_add(message):
        id_admin = int(message.text)
      
        if add_admin_by_id_tg(id_admin):
            bot.send_message(message.chat.id, f'Админ {id_admin} успешно добавлен.')
        else:
            bot.send_message(message.chat.id, f'Админ {id_admin} не добавлен.')