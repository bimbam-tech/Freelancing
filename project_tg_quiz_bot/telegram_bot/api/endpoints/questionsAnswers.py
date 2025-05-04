import telebot, logging, os
from telebot import types
from telegram_bot.db.crud import update_question_id, get_current_question_id, get_question, get_answer, get_id_image, update_user

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

user_question_history = {}

def current_quest_id(username):
    return get_current_question_id(username)

def update_quest_id(username, quest_id):
    new_id = {'current_question_id': quest_id}
    update_question_id(username, new_id)
    logger.info(f"Updated quest_id for chat_id {username}: {quest_id}")

def create_quest_markup(data, has_previous=False):
    quest_markup = types.InlineKeyboardMarkup()
    for key, value in data['Answers_quest'].items():
        callback_data = f"quest_id_{data['Id_answer_quest'][key]}"
        button = types.InlineKeyboardButton(text=value, callback_data=callback_data)
        quest_markup.add(button)
    
    if has_previous:
        back_button = types.InlineKeyboardButton(text="Назад", callback_data="back")
        quest_markup.add(back_button)
    
    return quest_markup

def create_list_img(list_id_img):
    result = []
    
    for photo_name in list_id_img:
        
        photo_path = os.path.join('./telegram_bot/tmp/img', f"{photo_name}.jpg")
        
        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                result.append(telebot.types.InputMediaPhoto(photo.read()))
                
    return result

def split_text(text, max_length=4096):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def register_handlers(bot):
    @bot.message_handler(commands=["start"])
    def start(message):
        update_user(message.from_user.username, chat_id=message.chat.id, current_question_id=1)
        chat_id = message.chat.id
        username = message.from_user.username
        first_quest_id = 1

        user_question_history[username] = [first_quest_id]

        update_quest_id(username, first_quest_id)
        data = get_question(first_quest_id)
        if data:
            media = create_list_img(get_id_image(1))
            markup = create_quest_markup(data)
            bot.send_media_group(chat_id, media)
            bot.send_message(chat_id, data['Quest'], reply_markup=markup)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('quest_id_'))
    def question(call):
        chat_id = call.message.chat.id
        username = call.from_user.username
        quest_id = int(call.data.split('_')[2])
        if quest_id > 1000:
            media = create_list_img(get_id_image(quest_id))
            try:
                bot.send_media_group(chat_id, media)
            except Exception as e:
                print(e)        
            answer = get_answer(quest_id)
            answer_parts = split_text(answer)
            markup = types.ReplyKeyboardMarkup(resize_keyboard = True)
            markup.add(types.KeyboardButton(text = '/start'))
            for part in answer_parts:
                bot.send_message(chat_id, part, reply_markup = markup)
        else:
            if username not in user_question_history:
                user_question_history[username] = []
            user_question_history[username].append(quest_id)
            update_quest_id(username, quest_id)
            logger.info(f"User {chat_id} selected quest_id: {quest_id}")
            data = get_question(quest_id)
            if data:
                media = create_list_img(get_id_image(quest_id))
                has_previous = len(user_question_history[username]) > 1
                markup = create_quest_markup(data, has_previous)
                try:
                    bot.send_media_group(chat_id, media)
                except Exception as e:
                    print(e)
                bot.send_message(chat_id, data['Quest'], reply_markup=markup)
                
    @bot.callback_query_handler(func=lambda call: call.data == 'back')
    def back(call):
        chat_id = call.message.chat.id
        username = call.from_user.username

        if username in user_question_history and len(user_question_history[username]) > 1:
            user_question_history[username].pop()
            previous_quest_id = user_question_history[username][-1]

            update_quest_id(username, previous_quest_id)
            data = get_question(previous_quest_id)
            if data:
                media = create_list_img(get_id_image(previous_quest_id))
                has_previous = len(user_question_history[username]) > 1
                markup = create_quest_markup(data, has_previous)
                bot.send_media_group(chat_id, media)
                bot.send_message(chat_id, data['Quest'], reply_markup=markup)
        else:
            bot.send_message(chat_id, "Это первый вопрос, назад нельзя.")