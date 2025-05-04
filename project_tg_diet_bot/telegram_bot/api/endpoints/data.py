import logging
from datetime import datetime, timedelta

from omegaconf import OmegaConf
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from telegram_bot.api.endpoints.menu import menu_markup
from telegram_bot.db.crud import get_user_info, update_user, get_meals_in_date_range

app_config = OmegaConf.load("./telegram_bot/conf/app.yaml")

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def register_handlers(bot):
    @bot.callback_query_handler(func=lambda call: call.data == "input_data")
    def input_data(call):
        msg = bot.send_message(call.message.chat.id, app_config.strings.welcome)
        msg = bot.send_message(call.message.chat.id, app_config.strings.height)
        logger.info(f"Received message: {call.data} from chat {call.from_user.username} ({call.message.chat.id})")
        update_user(call.from_user.username, chat_id=call.message.chat.id)
        bot.register_next_step_handler(msg, save_height)

    @bot.callback_query_handler(func=lambda call: call.data == "get_data")
    def get_data(call):
        user = get_user_info(call.from_user.username)
        update_user(call.from_user.username, chat_id=call.message.chat.id)
        if user is None:
            bot.send_message(call.message.chat.id, app_config.strings.no_data)
        else:
            keywords = {
                'height': 'Рост',
                'weight': 'Вес',
                'age': 'Возраст',
                'activity_level': 'Активность',
                'tdee_goal': 'Цель по калориям в день',
                'proteins': 'Белки',
                'fats': 'Жиры',
                'carbs': 'Углеводы'
            }

            user_data = {key: value for key, value in user.__dict__.items() if key in keywords}
            sorted_user_data = {key: user_data[key] for key in keywords if key in user_data}

            response = "Информация о вас:"
            for key, value in sorted_user_data.items():
                if key == 'activity_level':
                    value = next((al['string'] for al in app_config['menu']['activity_level'].values() if
                                al['id'] == str(value)), value)
                response += f"\n{keywords[key]}: {value}"
            bot.send_message(call.message.chat.id, response)

    @bot.callback_query_handler(func=lambda call: call.data == "get_last_meals")
    def get_last_meals(call):
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()
        last_meals_data = get_meals_in_date_range(
            call.from_user.username,
            start_date=start_date,
            end_date=end_date
        )
        if not last_meals_data:
            bot.send_message(call.message.chat.id, "За последние 24 часа приемов пищи не найдено.")
        else:
            bot.send_message(
                call.message.chat.id,
                "Приемы пищи за период с {} по {}:\n".format(
                    start_date.strftime("%Y-%m-%d %H:%M"),
                    end_date.strftime("%Y-%m-%d %H:%M")
                )
            )
            for idx, meal in enumerate(last_meals_data):
                meal_data = {
                    "Калории": meal.calories,
                    "Белки": meal.proteins,
                    "Жиры": meal.fats,
                    "Углеводы": meal.carbs,
                    "Время": meal.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "Комментарий": meal.comment if meal.comment else "отсутствует"
                }
                response = "Прием пищи {}:\n{}".format(
                    idx+1,
                    "\n".join([f"{item[0]}: {item[1]}" for item in meal_data.items()])
                )
                bot.send_message(call.message.chat.id, response)

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
        #bot.register_next_step_handler(msg, save_gender)

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
