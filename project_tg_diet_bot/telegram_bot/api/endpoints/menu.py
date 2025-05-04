import logging.config
from omegaconf import OmegaConf
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from telegram_bot.db.crud import get_user_info, update_user


app_config = OmegaConf.load("./telegram_bot/conf/app.yaml")

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def create_menu_markup():
    menu_markup = InlineKeyboardMarkup(row_width=1)
    menu_markup.add(
        InlineKeyboardButton("Внести данные", callback_data="input_data"),
        InlineKeyboardButton("Внести прием пищи", callback_data="enter_meal"),
        InlineKeyboardButton("Просмотр данных", callback_data="get_data"),
        InlineKeyboardButton("Приемы пищи за последние 24 часа", callback_data="get_last_meals"),
        InlineKeyboardButton("Расчет базового метаболизма (BMR)", callback_data="calculate_bmr"),
        InlineKeyboardButton("Расчет общего расхода калорий (TDEE)", callback_data="calculate_tdee"),
        InlineKeyboardButton("Расчет суточной нормы БЖУ", callback_data="calculate_macros"),
        InlineKeyboardButton("Ввод и анализ питания", callback_data="nutrition_analysis"),
    )
    return menu_markup

menu_markup = create_menu_markup()

def register_handlers(bot):
    @bot.message_handler(commands=["start", "menu"])
    def menu(message):
        user = get_user_info(message.from_user.username)
        if user is None:
            msg = bot.send_message(message.chat.id, app_config.strings.welcome)
            msg = bot.send_message(message.chat.id, app_config.strings.height)
            # logger.info(f"Received message: {call.data} from chat {message.from_user.username} ({message.chat.id})")
            update_user(message.from_user.username, chat_id=message.chat.id)
            bot.register_next_step_handler(msg, save_height)
        else:        
            logger.info(f"Received message: {message.text} from chat {message.from_user.username} ({message.chat.id})")
            bot.send_message(message.chat.id, "Выберите действие:", reply_markup=menu_markup)
            
    def save_height(message):
        height = int(message.text)
        update_user(message.from_user.username, height=height)
        msg = bot.send_message(message.chat.id, app_config.strings.weight)
        bot.register_next_step_handler(msg, save_weight)

    def save_weight(message):
        weight = int(message.text)
        update_user(message.from_user.username, weight=weight)

        msg = bot.send_message(message.chat.id, app_config.strings.age)
        bot.register_next_step_handler(msg, save_age)

    def save_age(message):
        age = int(message.text)
        update_user(message.from_user.username, age=age)

        gender_markup = InlineKeyboardMarkup(row_width=2)
        gender_markup.add(
            InlineKeyboardButton(
                app_config.menu.gender.male.string,
                callback_data=f"gender.{app_config.menu.gender.male.id}"
            ),
            InlineKeyboardButton(
                app_config.menu.gender.female.string,
                callback_data=f"gender.{app_config.menu.gender.female.id}"
            )
        )
        msg = bot.send_message(message.chat.id, app_config.strings.gender, reply_markup=gender_markup)
        # bot.register_next_step_handler(msg, save_gender)
    
    @bot.callback_query_handler(
        func=lambda call: call.data in [
            f"gender.{item[1].id}"
            for item in app_config.menu.gender.items()
        ]
    )
    def save_gender(call):
        gender = int(call.data.split(".")[1])
        update_user(call.from_user.username, gender=gender)

        activity_level_markup = InlineKeyboardMarkup(row_width=2)
        activity_level_markup.add(
            InlineKeyboardButton(app_config.menu.activity_level.sedentary.string,
                                 callback_data=f"activity_level.{app_config.menu.activity_level.sedentary.id}"),
            InlineKeyboardButton(app_config.menu.activity_level.low.string,
                                 callback_data=f"activity_level.{app_config.menu.activity_level.low.id}"),
            InlineKeyboardButton(app_config.menu.activity_level.moderate.string,
                                 callback_data=f"activity_level.{app_config.menu.activity_level.moderate.id}"),
            InlineKeyboardButton(app_config.menu.activity_level.high.string,
                                 callback_data=f"activity_level.{app_config.menu.activity_level.high.id}"),
        )
        msg = bot.send_message(call.message.chat.id, app_config.strings.activity_level,
                               reply_markup=activity_level_markup)
    
    @bot.callback_query_handler(
        func=lambda call: call.data in [
            f"activity_level.{item[1].id}"
            for item in app_config.menu.activity_level.items()
        ]
    )
    def save_activity_level(call):
        activity_level = int(call.data.split(".")[1])
        update_user(call.from_user.username, activity_level=activity_level)

        goal_markup = InlineKeyboardMarkup(row_width=2)
        goal_markup.add(
            InlineKeyboardButton(app_config.menu.goal.gain.string,
                                 callback_data=f"goal.{app_config.menu.goal.gain.id}"),
            InlineKeyboardButton(app_config.menu.goal.lose.string,
                                 callback_data=f"goal.{app_config.menu.goal.lose.id}"),
            InlineKeyboardButton(app_config.menu.goal.maintain.string,
                                 callback_data=f"goal.{app_config.menu.goal.maintain.id}")
        )
        msg = bot.send_message(call.message.chat.id, app_config.strings.goal, reply_markup=goal_markup)

    @bot.callback_query_handler(
        func=lambda call: call.data in [
            f"goal.{item[1].id}"
            for item in app_config.menu.goal.items()
        ]
    )
    def save_goal(call):

        goal = int(call.data.split(".")[1])
        update_user(call.from_user.username, goal=goal)

        bot.send_message(call.message.chat.id, app_config.strings.confirmation)
        bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=menu_markup)