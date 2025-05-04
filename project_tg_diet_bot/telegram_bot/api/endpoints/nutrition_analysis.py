import logging
import os
import json
from datetime import datetime, timedelta
import sqlite3

from omegaconf import OmegaConf
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from telegram_bot.api.endpoints.menu import menu_markup
from telegram_bot.db.crud import add_meal, get_user_info, update_user, validate_user, get_aggregate_last_24_hours
from telegram_bot.service.calculator import Calculator
from telegram_bot.service.openai import OpenAiService
from telegram_bot.service.utils import extract_json_from_text
from telegram_bot.api.endpoints.photo_response import photo_editing_main_par

app_config = OmegaConf.load("./telegram_bot/conf/app.yaml")

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

calculator = Calculator()

json_template = """
{
    "ingredients": [
        {
            "name": "ингредиент1",
            "weight": 100
        },
        {
            "name": "ингредиент2",
            "weight": 150
        },
        {
            "name": "ингредиент3",
            "weight": 300
        }
    "calories": 3000,
    "proteins": 100,
    "fats": 50,
    "carbs": 210
}
"""

recalculate_instruction = (f"Пересчитай значения составляющих при изменении "
                           f"веса ингредиента и оформи только в виде JSON, без текста: {json_template}.\nИнгредиент")

template_for_one_ingredient = """
    {
        "name": "название ингредиента",
        "weight: 300,
        "calories": 3000,
        "proteins": 100,
        "fats": 50,
        "carbs": 210
    }
"""

basic_instruction = (f"Опиши блюдо, оцени ингредиенты и примерный вес каждого ингредиента в граммах. Опиши пищевую "
                     f"ценность блюда в калориях, белках, жирах и углеводах. Дополнительно оформи результат в виде "
                     f"json {json_template}. Отправь только корректный json документ.")

instruction = (f'Опиши пищевую ценность ингредиента в калориях, белках, жирах и углеводах, используя его вес. '
               f'Оформи результат только в виде json: {template_for_one_ingredient}')

openai_service = OpenAiService()

TOKEN = os.getenv("BOT_TOKEN")

buffer = dict()

# Создание таблицы для хранения истории сообщений
def create_table():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
    (user_id INTEGER, business_connection_id TEXT, message_role TEXT, message_content TEXT)''')
    conn.commit()
    conn.close()

# Сохранение сообщения в базу данных
def save_message(user_id, business_connection_id, message_role, message_content):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (user_id, business_connection_id, message_role, message_content) VALUES (?, ?, ?, ?)",
    (user_id, business_connection_id, message_role, message_content))
    conn.commit()
    conn.close()

# Получение истории сообщений для определенного пользователя и бизнес-соединения
def get_chat_history(user_id, business_connection_id):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT message_role, message_content FROM chat_history WHERE user_id=? AND business_connection_id=? ORDER BY rowid",
    (user_id, business_connection_id))
    chat_history = c.fetchall()
    conn.close()
    return chat_history

# Путь к файлу JSON для хранения данных о бизнес-соединениях
json_db_path = 'business_connections.json'

# Загрузка данных о бизнес-соединениях
def load_business_connections():
    if os.path.exists(json_db_path):
        with open(json_db_path, 'r') as file:
            return json.load(file)
    else:
        logging.warning("Business connections file not found. Creating a new one.")
    return {}

# Сохранение данных о бизнес-соединениях
def save_business_connections(business_connections):
    logging.debug(f"Saving business connections: {business_connections}")
    try:
        with open(json_db_path, 'w') as file:
            json.dump(business_connections, file, indent=2)
    except Exception as e:
        logging.error(f"Error saving business connections: {e}")

# Обновление бизнес-соединения
def update_business_connection(business_connection):
    business_connection_id = business_connection.id
    user_chat_id = business_connection.user_chat_id
    can_reply = business_connection.can_reply
    is_enabled = business_connection.is_enabled
    date = business_connection.date
    logging.debug(f"Updating business connection: {business_connection_id}")
    business_connections = load_business_connections()
    business_connections[business_connection_id] = {
    'user_chat_id': user_chat_id,
    'can_reply': can_reply,
    'is_enabled': is_enabled,
    'date': date
    }
    save_business_connections(business_connections)

# Получение бизнес-соединения
def get_business_connection(business_connection_id):
    business_connections = load_business_connections()
    return business_connections.get(business_connection_id)

create_table()

def register_handlers(bot):
    @bot.message_handler(func = lambda message: message.text == 'Новый приём пищи')
    def nutrition_analysis(message):
        username = message.from_user.username

        if not validate_user(username):
            bot.send_message(message.chat.id, "Пожалуйста, укажите ваши данные через меню.")
            logger.error(f"Missing data for username: {username}")
            return None
        else:
            user = get_user_info(username)

        if user.tdee is None or user.tdee_goal is None:
            tdee = calculator.tdee(user.weight, user.height, user.age, user.activity_level, user.gender)
            tdee_goal = calculator.tdee_with_goal(tdee, user.goal)
            update_user(username, tdee=tdee, tdee_goal=tdee_goal)
            user = get_user_info(username)

        if None in {user.carbs, user.proteins, user.fats}:
            macros = calculator.macros(user.tdee)
            update_user(username, proteins=macros['proteins'], fats=macros['fats'],
                        carbs=macros['carbs'])

        options_menu = InlineKeyboardMarkup(row_width=2)
        bot.send_message(
            message.chat.id, "Опишите ваше блюдо и/или добавьте его фотографию.",
            reply_markup=options_menu
        )
        bot.register_next_step_handler(message, process_user_input)

    @bot.message_handler(content_types=['photo'])
    def group_an(message):
        if message.chat.type in ['group', 'supergroup']:
            user = get_user_info(message.from_user.username)

            user_input_image_path = None
            user_input_text = None
            try:
                # Get the file ID of the image
                file_id = message.photo[-1].file_id  # Get the highest resolution photo
                # Get the file path
                file_info = bot.get_file(file_id)
                file_path = file_info.file_path

                # Download the image and convert it into binary
                downloaded_file = bot.download_file(file_path)

                if not os.path.exists("./telegram_bot/tmp/photos"):
                    os.mkdir("./telegram_bot/tmp/photos")

                user_input_image_path = f"./telegram_bot/tmp/{file_path}"
                with open(user_input_image_path, "wb") as file:
                    file.write(downloaded_file)

                user_input_text = message.caption
            except:
                pass

            try:
                if user_input_text is None:
                    user_input_text = message.text
            except:
                pass

            logger.info(f"User input text: {user_input_text}")
            logger.info(f"User input image path: {user_input_image_path}")

            if user_input_text is None or '#отчёт' not in user_input_text:
                pass
            else:
                response = openai_service.invoke(
                    basic_instruction,
                    user_input_text=user_input_text,
                    user_input_image_path=user_input_image_path
                )


                nutrition_data = extract_json_from_text(response)

                # add meal to database
                if user_input_text:
                    nutrition_data['comment'] = user_input_text
                else:
                    nutrition_data['comment'] = ', '.join([ingredient["name"] for ingredient in nutrition_data["ingredients"]])

                buffer[message.from_user.username] = {
                    "nutrition_data": nutrition_data,
                    "user_input_text": user_input_text,
                    "user_input_image_path": user_input_image_path,
                    "quantity_ingredient": None,
                    "num_ing_weight": None,
                    "add_ingredient": {
                        "name": None,
                        "weight": None,
                        "new_weight": None
                    }
                }

                if user_input_image_path:
                    # remove the image
                    os.remove(user_input_image_path)

                response = response.replace("`", "")
                response = response.replace("json", "")
                
                # photo_editing_main_par(json.loads(response), user.username)
                # photo = open(f'./telegram_bot/tmp/photo_response/{user.username}.jpg', 'rb')

                response_gpt = json.loads(response)


                response_new = f'Килокалории - {response_gpt["calories"]}\nБелки - {response_gpt["proteins"]} г.\nЖиры - {response_gpt["fats"]} г.\nУглеводы - {response_gpt["carbs"]} г.\n\n'

                for ingredient in response_gpt['ingredients']:
                    response_new += f'{ingredient["name"]} - {ingredient["weight"]} г.\n'
                response_new+='\nℹ️На данный момент технология анализа по фото находится в разработке, поэтому иногда результаты могут быть неточными.'
                
                # bot.send_photo(message.chat.id, photo)

                bot.send_message(message.chat.id, response_new)

    @bot.business_connection_handler(func=lambda business_connection: True)
    def handle_business_connection(business_connection):
        update_business_connection(business_connection)
        logging.info(f"Business connection updated: {business_connection.id}")

    @bot.business_message_handler(func=lambda message: True, content_types=['photo'])
    def handle_business_message(message):
        user_id = message.chat.id
        business_connection_id = message.business_connection_id
        logging.info(f"Received business message from {user_id}: {message.text}")

        # Обновляем информацию о бизнес-соединении
        business_connection = get_business_connection(business_connection_id)
        if business_connection:
            business_connection['can_reply'] = True
            business_connection['is_enabled'] = True
            save_business_connections(load_business_connections())
        else:
            business_connection = {
            'user_chat_id': message.chat.id,
            'can_reply': True,
            'is_enabled': True,
            'date': message.date
            }
        business_connections = load_business_connections()
        business_connections[business_connection_id] = business_connection
        save_business_connections(business_connections)

        if business_connection and business_connection.get('is_enabled') and business_connection.get('can_reply'):
            try:
                # Сохранение входящего сообщения в базу данных
                save_message(user_id, business_connection_id, 'user', message.text)
                # Получение истории сообщений из базы данных
                chat_history = get_chat_history(user_id, business_connection_id)
                messages = [
                {"role": "system", "content": "Привет! Ты - ИИ-помощник для бизнеса в Telegram. Отвечай на вопросы пользователей, основываясь на контексте переписки."},
                *[{"role": role, "content": content} for role, content in chat_history]
                ]
                user = get_user_info(message.from_user.username)

                user_input_image_path = None
                user_input_text = None
                try:
                    # Get the file ID of the image
                    file_id = message.photo[-1].file_id  # Get the highest resolution photo
                    # Get the file path
                    file_info = bot.get_file(file_id)
                    file_path = file_info.file_path

                    # Download the image and convert it into binary
                    downloaded_file = bot.download_file(file_path)

                    if not os.path.exists("./telegram_bot/tmp/photos"):
                        os.mkdir("./telegram_bot/tmp/photos")

                    user_input_image_path = f"./telegram_bot/tmp/{file_path}"
                    with open(user_input_image_path, "wb") as file:
                        file.write(downloaded_file)

                    user_input_text = message.caption
                except:
                    pass

                try:
                    if user_input_text is None:
                        user_input_text = message.text
                except:
                    pass

                logger.info(f"User input text: {user_input_text}")
                logger.info(f"User input image path: {user_input_image_path}")

                if user_input_text is None or '#отчёт' not in user_input_text:
                    pass
                else:
                    response = openai_service.invoke(
                        basic_instruction,
                        user_input_text=user_input_text,
                        user_input_image_path=user_input_image_path
                    )


                    nutrition_data = extract_json_from_text(response)

                    # add meal to database
                    if user_input_text:
                        nutrition_data['comment'] = user_input_text
                    else:
                        nutrition_data['comment'] = ', '.join([ingredient["name"] for ingredient in nutrition_data["ingredients"]])

                    buffer[message.from_user.username] = {
                        "nutrition_data": nutrition_data,
                        "user_input_text": user_input_text,
                        "user_input_image_path": user_input_image_path,
                        "quantity_ingredient": None,
                        "num_ing_weight": None,
                        "add_ingredient": {
                            "name": None,
                            "weight": None,
                            "new_weight": None
                        }
                    }

                    if user_input_image_path:
                        # remove the image
                        os.remove(user_input_image_path)

                    response = response.replace("`", "")
                    response = response.replace("json", "")
                    
                    # photo_editing_main_par(json.loads(response), user.username)
                    # photo = open(f'./telegram_bot/tmp/photo_response/{user.username}.jpg', 'rb')

                    response_gpt = json.loads(response)


                    response_new = f'Килокалории - {response_gpt["calories"]}\nБелки - {response_gpt["proteins"]} г.\nЖиры - {response_gpt["fats"]} г.\nУглеводы - {response_gpt["carbs"]} г.\n\n'

                    for ingredient in response_gpt['ingredients']:
                        response_new += f'{ingredient["name"]} - {ingredient["weight"]} г.\n'
                    response_new+='\nℹ️На данный момент технология анализа по фото находится в разработке, поэтому иногда результаты могут быть неточными.'
                
                    # bot.send_photo(message.chat.id, photo)

                    # bot.send_message(message.chat.id, response_new)
                    bot.send_message(message.chat.id, response_new, reply_to_message_id=message.id, business_connection_id=business_connection_id)
                # Сохранение ответа бота в базу данных
                logging.info("Response sent to business chat")
            except Exception as e:
                logging.error(f"Error generating or sending response to business chat: {e}")
        else:
            logging.warning(f"Business connection not found or not enabled: {business_connection_id}")

    @bot.message_handler(content_types=['photo'])
    def process_user_input(message):
        user = get_user_info(message.from_user.username)

        user_input_image_path = None
        user_input_text = None
        try:
            # Get the file ID of the image
            file_id = message.photo[-1].file_id  # Get the highest resolution photo
            # Get the file path
            file_info = bot.get_file(file_id)
            file_path = file_info.file_path

            # Download the image and convert it into binary
            downloaded_file = bot.download_file(file_path)

            if not os.path.exists("./telegram_bot/tmp/photos"):
                os.mkdir("./telegram_bot/tmp/photos")

            user_input_image_path = f"./telegram_bot/tmp/{file_path}"
            with open(user_input_image_path, "wb") as file:
                file.write(downloaded_file)

            user_input_text = message.caption
        except:
            pass

        try:
            if user_input_text is None:
                user_input_text = message.text
        except:
            pass

        logger.info(f"User input text: {user_input_text}")
        logger.info(f"User input image path: {user_input_image_path}")

        response = openai_service.invoke(
            basic_instruction,
            user_input_text=user_input_text,
            user_input_image_path=user_input_image_path
        )


        nutrition_data = extract_json_from_text(response)

        # add meal to database
        if user_input_text:
            nutrition_data['comment'] = user_input_text
        else:
            nutrition_data['comment'] = ', '.join([ingredient["name"] for ingredient in nutrition_data["ingredients"]])

        buffer[message.from_user.username] = {
            "nutrition_data": nutrition_data,
            "user_input_text": user_input_text,
            "user_input_image_path": user_input_image_path,
            "quantity_ingredient": None,
            "num_ing_weight": None,
            "add_ingredient": {
                "name": None,
                "weight": None,
                "new_weight": None
            }
        }

        if user_input_image_path:
            # remove the image
            os.remove(user_input_image_path)

        response = response.replace("`", "")
        response = response.replace("json", "")
        
        # photo_editing_main_par(json.loads(response), user.username)
        # photo = open(f'./telegram_bot/tmp/photo_response/{user.username}.jpg', 'rb')

        response_gpt = json.loads(response)


        response_new = f'Килокалории - {response_gpt["calories"]}\nБелки - {response_gpt["proteins"]} г.\nЖиры - {response_gpt["fats"]} г.\nУглеводы - {response_gpt["carbs"]} г.\n\n'

        for ingredient in response_gpt['ingredients']:
            response_new += f'{ingredient["name"]} - {ingredient["weight"]} г.\n'
        response_new+='\nℹ️На данный момент технология анализа по фото находится в разработке, поэтому иногда результаты могут быть неточными.'
        # bot.send_photo(message.chat.id, photo)

        bot.send_message(message.chat.id, response_new)
        
        yes_no_menu = InlineKeyboardMarkup(row_width=2)
        yes_no_menu.add(
            InlineKeyboardButton("Подтвердить", callback_data="confirm_result.yes"),
            InlineKeyboardButton("Изменить", callback_data="confirm_result.no")
        )

        bot.send_message(message.chat.id, "Подтверждаете результат анализа?", reply_markup=yes_no_menu)

    @bot.callback_query_handler(func=lambda call: call.data == "confirm_result.no")
    def confirm_result_no(call):
        user = get_user_info(call.from_user.username)
        nutrition_data = buffer[user.username]["nutrition_data"]
        
        list_ingredient = []
        
        for ingredient in nutrition_data['ingredients']:
            list_ingredient.append(ingredient['name'])

        change_menu = InlineKeyboardMarkup(row_width=2)
        change_menu.add(
            InlineKeyboardButton("Назад", callback_data="yes_no_menu"),
            InlineKeyboardButton("+Ингредиент", callback_data="add_ingredient")
        )

        num_ing = 0
        for ingredient in list_ingredient:
            num_ing += 1
            change_menu.add(InlineKeyboardButton(f"{ingredient}", callback_data=f"ing_{num_ing}"))

        buffer[user.username]["quantity_ingredient"] = num_ing

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            text="Изменение ингредиентов:",
            reply_markup=change_menu
        )

    @bot.callback_query_handler(func=lambda call: call.data == "yes_no_menu")
    def yes_no_menu(call):
        yes_no_menu = InlineKeyboardMarkup(row_width=2)
        yes_no_menu.add(
            InlineKeyboardButton("Подтвердить", callback_data="confirm_result.yes"),
            InlineKeyboardButton("Изменить", callback_data="confirm_result.no")
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id,
                              text="Подтверждаете результат анализа?", reply_markup=yes_no_menu)

    @bot.callback_query_handler(func=lambda call: call.data == "add_ingredient")
    def add_ingredient(call):
        msg = bot.send_message(call.message.chat.id, 'Введите название ингредиента.')
        bot.register_next_step_handler(msg, name_ingredient)

    def name_ingredient(message):
        name_ingredient = message.text
        buffer[message.from_user.username]["add_ingredient"]["name"] = name_ingredient
 
        msg = bot.send_message(message.chat.id, "Введите вес ингредиента (в граммах).")
        bot.register_next_step_handler(msg, weight_ingredient)

    def analyze_ingredient(name: str, weight: float):
        response = openai_service.invoke(instruction, f"Ингредиент: {name}, вес: {weight} грамм")
        return extract_json_from_text(response)

    def summarize_components_weight(user, ingredient_data, is_decreasing: bool = False):
        components = ['calories', 'proteins', 'fats', 'carbs']
        multiplier = -1 if is_decreasing else 1
        for component in components:
            buffer[user]["nutrition_data"][component] += ingredient_data[component] * multiplier
            if is_decreasing and buffer[user]["nutrition_data"][component] < 0:
                buffer[user]["nutrition_data"][component] = 0

    def weight_ingredient(message):
        user = get_user_info(message.from_user.username)
        
        weight_ingredient = int(message.text)
        buffer[message.from_user.username]["add_ingredient"]["weight"] = weight_ingredient

        ingredient_data = analyze_ingredient(
            buffer[message.from_user.username]["add_ingredient"]["name"],
            buffer[message.from_user.username]["add_ingredient"]["weight"]
        )

        buffer[message.from_user.username]["nutrition_data"]["ingredients"].append(
            {"name": ingredient_data["name"], "weight": ingredient_data["weight"]}
        )
        buffer[message.from_user.username]["quantity_ingredient"] += 1

        summarize_components_weight(message.from_user.username, ingredient_data)

        json_nutrition_output = json.dumps(
            buffer[message.from_user.username]['nutrition_data'],
            ensure_ascii=False,
            indent=4
        )
        

        # photo_editing_main_par(json.loads(json_nutrition_output), user.username)
        # photo = open(f'./telegram_bot/tmp/photo_response/{user.username}.jpg', 'rb')
        
        response_gpt = json.loads(json_nutrition_output)
        
        response_new = f'Килокалории - {response_gpt["calories"]}\nБелки - {response_gpt["proteins"]} г.\nЖиры - {response_gpt["fats"]} г.\nУглеводы - {response_gpt["carbs"]} г.\n\n'
        
        for ingredient in response_gpt['ingredients']:
            response_new += f'{ingredient["name"]} - {ingredient["weight"]} г.\n'
        response_new+='\nℹ️На данный момент технология анализа по фото находится в разработке, поэтому иногда результаты могут быть неточными.'
        # bot.send_photo(message.chat.id, photo)
        
        bot.send_message(message.chat.id, response_new)
    
        yes_no_menu = InlineKeyboardMarkup(row_width=2)
        yes_no_menu.add(
            InlineKeyboardButton("Подтвердить", callback_data="confirm_result.yes"),
            InlineKeyboardButton("Изменить", callback_data="confirm_result.no")
        )

        bot.send_message(message.chat.id, "Подтверждаете результат анализа?", reply_markup=yes_no_menu)

    @bot.callback_query_handler(func=lambda call: call.data)
    def change_del_ingredient(call):
        user = get_user_info(call.from_user.username)

        if call.data == "confirm_result.yes":
                nutrition_data = buffer[user.username]["nutrition_data"]

                add_meal(
                    user.username,
                    timestamp=datetime.now(),
                    calories=nutrition_data["calories"],
                    carbs=nutrition_data["carbs"],
                    proteins=nutrition_data["proteins"],
                    fats=nutrition_data["fats"],
                    comment=nutrition_data['comment']
                )
                
                last_meals_data = get_aggregate_last_24_hours(
                    user.username
                )
                
                # compute how many calories and macros left to the user after the meal
                calories_left = user.tdee_goal - last_meals_data["calories"]
                protein_left = user.proteins - last_meals_data["proteins"]
                fat_left = user.fats - last_meals_data["fats"]
                carbs_left = user.carbs - last_meals_data["carbs"]
                
                bot.send_message(call.message.chat.id,
                                f"Осталось калорий: {calories_left:.0f} ккал\n"
                                f"Осталось белка: {protein_left:.0f} г\n"
                                f"Осталось жира: {fat_left:.0f} г\n"
                                f"Осталось углеводов: {carbs_left:.0f} г\n"
                                )

                bot.send_message(call.message.chat.id, "Результат сохранен в дневник питания.")
                bot.send_message(call.message.chat.id, "Посчитай сколько калорий! Отправь фотографию еды.", reply_markup=menu_markup)
        else:
            for num in range(1, buffer[user.username]["quantity_ingredient"]+1):
                if call.data == f'ing_{num}':
                    change_del_menu = InlineKeyboardMarkup(row_width=2)
                    change_del_menu.add(
                        InlineKeyboardButton("Изменить вес", callback_data=f"change_weight_{num}"),
                        InlineKeyboardButton("Удалить", callback_data=f"delete_ingredient_{num}")
                    )
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id,
                                        text="Изменение ингредиентов:", reply_markup=change_del_menu)
                
                if call.data == f'delete_ingredient_{num}':
                    ingredient_data = analyze_ingredient(
                        buffer[user.username]["nutrition_data"]["ingredients"][num-1]['name'],
                        buffer[user.username]["nutrition_data"]["ingredients"][num-1]['weight']
                    )
                    
                    
                    summarize_components_weight(user.username, ingredient_data, is_decreasing=True)
                    
                    del buffer[user.username]["nutrition_data"]["ingredients"][num-1]
                    
                    buffer[user.username]["quantity_ingredient"] -= 1
                   
                    json_nutrition_output = json.dumps(
                        buffer[user.username]['nutrition_data'],
                        ensure_ascii=False,
                        indent=4
                    )
                    
                    response_gpt = json.loads(json_nutrition_output)
                    # photo_editing_main_par(json.loads(json_nutrition_output), user.username)
                    # photo = open(f'./telegram_bot/tmp/photo_response/{user.username}.jpg', 'rb')
                    
                    response_new = f'Килокалории - {response_gpt["calories"]}\nБелки - {response_gpt["proteins"]} г.\nЖиры - {response_gpt["fats"]} г.\nУглеводы - {response_gpt["carbs"]} г.\n\n'
                    
                    for ingredient in response_gpt['ingredients']:
                        response_new += f'{ingredient["name"]} - {ingredient["weight"]} г.\n'
                    response_new+='\nℹ️На данный момент технология анализа по фото находится в разработке, поэтому иногда результаты могут быть неточными.'
                    bot.send_message(call.message.chat.id, response_new)
                    # bot.send_photo(call.message.chat.id, photo)  
                    
                    yes_no_menu = InlineKeyboardMarkup(row_width=2)
                    yes_no_menu.add(
                        InlineKeyboardButton("Подтвердить", callback_data="confirm_result.yes"),
                        InlineKeyboardButton("Изменить", callback_data="confirm_result.no")
                    )

                    bot.send_message(call.message.chat.id, "Подтверждаете результат анализа?", reply_markup=yes_no_menu)
                
                def make_recalc_instruction(dish_data, ingredient, old_weight, new_weight):
                    return ("{}: {}:\n {} гр -> {} гр\n\nИнформация о блюде до: {}".
                            format(recalculate_instruction,
                                   ingredient,
                                   old_weight,
                                   new_weight,
                                   dish_data))                
                
                def zero_components_if_negative(username):
                    components = ['calories', 'proteins', 'fats', 'carbs']
                    for component in components:
                        if buffer[username]["nutrition_data"][component]["weight"] < 0:
                            buffer[username]["nutrition_data"][component]["weight"] = 0

                def save_weight(message):
                    num = buffer[user.username]["num_ing_weight"]
                    new_weight = int(message.text)
                    buffer[user.username]["nutrition_data"]["ingredients"][num - 1]["new_weight"] = new_weight
                    prompt = make_recalc_instruction(
                        json.dumps(buffer[user.username]["nutrition_data"], ensure_ascii=False, indent=4),
                        buffer[user.username]["nutrition_data"]["ingredients"][num-1]["name"],
                        buffer[user.username]["nutrition_data"]["ingredients"][num-1]["weight"],
                        buffer[user.username]["nutrition_data"]["ingredients"][num-1]["new_weight"]
                    )
                    buffer[user.username]["nutrition_data"]["ingredients"][num-1]["weight"] = new_weight
                    ingredients_json = json.dumps(buffer[user.username]["nutrition_data"]["ingredients"])
                    response = openai_service.invoke(prompt, user_input_text=ingredients_json)

                    new_nutrition_data = extract_json_from_text(response)
                    new_nutrition_data["comment"] = buffer[user.username]["nutrition_data"]['comment']
                                                    
                    buffer[user.username]["nutrition_data"] = new_nutrition_data       
                    # zero_components_if_negative(user.username)        
                    json_nutrition_output = json.dumps(
                        buffer[user.username]['nutrition_data'],
                        ensure_ascii=False,
                        indent=4
                    )

                    response_gpt = json.loads(json_nutrition_output)
                    # photo_editing_main_par(json.loads(json_nutrition_output), user.username)
                    # photo = open(f'./telegram_bot/tmp/photo_response/{user.username}.jpg', 'rb')

                    # bot.send_photo(call.message.chat.id, photo)  

                    response_new = f'Килокалории - {response_gpt["calories"]}\nБелки - {response_gpt["proteins"]} г.\nЖиры - {response_gpt["fats"]} г.\nУглеводы - {response_gpt["carbs"]} г.\n\n'
                    
                    for ingredient in response_gpt['ingredients']:
                        response_new += f'{ingredient["name"]} - {ingredient["weight"]} г.\n'
                    response_new+='\nℹ️На данный момент технология анализа по фото находится в разработке, поэтому иногда результаты могут быть неточными.'
                    bot.send_message(call.message.chat.id, response_new)
                    
                    yes_no_menu = InlineKeyboardMarkup(row_width=2)
                    yes_no_menu.add(
                        InlineKeyboardButton("Подтвердить", callback_data="confirm_result.yes"),
                        InlineKeyboardButton("Изменить", callback_data="confirm_result.no")
                    )

                    bot.send_message(call.message.chat.id, "Подтверждаете результат анализа?", reply_markup=yes_no_menu)


                
                if call.data == f"change_weight_{num}":
                    buffer[user.username]["num_ing_weight"] = num
                    msg = bot.send_message(call.message.chat.id, "Введите новый вес для данного ингредиента (в граммах).")
                    bot.register_next_step_handler(msg, save_weight)
