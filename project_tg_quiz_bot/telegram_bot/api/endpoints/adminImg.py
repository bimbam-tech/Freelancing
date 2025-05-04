import logging, os
from telebot import types

from telegram_bot.db.crud import get_data_img, del_img_db, get_last_image_id, add_image_with_id

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def create_admin_markup():
    menu_markup = types.InlineKeyboardMarkup(row_width=1)
    menu_markup.add(
        types.InlineKeyboardButton("Просмотреть изображение", callback_data="get_img"), 
        types.InlineKeyboardButton("Удалить изображение", callback_data="del_img"),
        types.InlineKeyboardButton("Добавить изображение", callback_data="add_img") 
    )
    return menu_markup

menu_markup = create_admin_markup()

def register_handlers(bot):            
    @bot.callback_query_handler(func=lambda call: call.data == 'img_work')
    def img_check(call):
        chat_id = call.message.chat.id
        bot.send_message(chat_id, 'Что хотите сделать?', reply_markup=menu_markup)
    
    @bot.callback_query_handler(func=lambda call: call.data == 'get_img')
    def get_img(call):
        chat_id = call.message.chat.id
        msg = bot.send_message(chat_id, 'Введите id изображения')
        bot.register_next_step_handler(msg, get_id_img_for_get)
        
    def get_id_img_for_get(message):
        id_img = int(message.text)
        
        data = str(get_data_img(id_img))
        
        result_text = f'Вопросы, в которых выводится это изображение:\n{data}'
        
        photo = open(f'./telegram_bot/tmp/img/{id_img}.jpg', 'rb')
        
        bot.send_photo(message.chat.id, photo, caption=result_text)
        
        photo.close()
        
    @bot.callback_query_handler(func=lambda call: call.data == 'del_img')
    def del_img(call):
        chat_id = call.message.chat.id
        msg = bot.send_message(chat_id, 'Введите id изображения')
        bot.register_next_step_handler(msg, get_id_img_for_del)
        
    def get_id_img_for_del(message):
        id_img = int(message.text)
        
        data = str(get_data_img(id_img))
        
        result_text = f'Вопросы, в которых выводится это изображение:\n{data}\n\nВы уверены, что хотите удалить это фото?'
        
        photo = open(f'./telegram_bot/tmp/img/{id_img}.jpg', 'rb')
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton('Да', callback_data=f'yes_del_{id_img}'),
            types.InlineKeyboardButton('Нет', callback_data=f'img_work')
        )
        
        bot.send_photo(message.chat.id, photo)
        bot.send_message(message.chat.id, result_text, reply_markup=markup)
        
        photo.close()
        
    @bot.callback_query_handler(func=lambda call: call.data.startswith('yes_del_'))
    def del_yes(call):

        img_id = int(call.data.split('_')[2])

        image_name = f'{img_id}.jpg'
        folder_path = './telegram_bot/tmp/img'

        image_path = os.path.join(folder_path, image_name)

        if os.path.exists(image_path):
            os.remove(image_path)
            del_img_db(img_id)    
            bot.send_message(call.message.chat.id, f"Изображение '{image_name}' успешно удалено.")
            
    @bot.callback_query_handler(func=lambda call: call.data == 'add_img')
    def add_img(call):
        chat_id = call.message.chat.id
        msg = bot.send_message(chat_id, 'Загрузите изображение')
        bot.register_next_step_handler(msg, save_img)
        
    def save_img(message):
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            last_id_db = int(get_last_image_id())
            file_name = f"{last_id_db+1}.jpg"
            save_path = os.path.join('./telegram_bot/tmp/img', file_name)
            with open(save_path, 'wb') as new_file:
                new_file.write(downloaded_file)

            msg = bot.send_message(message.chat.id, 'Укажите id вопросов, в которых должно быть это изображение через запятую.\nПример: 1, 2, 3, 4, 5, 6')
            bot.register_next_step_handler(msg, save_img_db)
        else:
            bot.reply_to(message, "Пожалуйста, загрузите изображение.")
            
    def save_img_db(message):
        numbers_list = [int(num.strip()) for num in (message.text).split(',')]
        
        add_image_with_id(numbers_list)
        
        bot.send_message(message.chat.id, 'Изображение успешно добавлено!')
        
