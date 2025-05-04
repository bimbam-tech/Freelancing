import logging

from omegaconf import OmegaConf

from telegram_bot.api.endpoints.menu import menu_markup
from telegram_bot.db.crud import get_user_info, update_user, validate_user
from telegram_bot.service.calculator import Calculator

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

calculator = Calculator()


def register_handlers(bot):
    @bot.callback_query_handler(func=lambda call: call.data == "calculate_bmr")
    def calculate_bmr(call):
        username = call.from_user.username

        if validate_user(username) == False:
            bot.send_message(call.message.chat.id, "Пожалуйста, укажите ваши данные через меню.")
            logger.error(f"Missing data for username: {username}")
            return None
        else:
            user = get_user_info(username)

        bmr = calculator.bmr(
            weight=user.weight,
            height=user.height,
            gender=user.gender,
            age=user.age
        )

        update_user(call.from_user.username, bmr=bmr)

        response = f"Ваш базовый метаболизм: {bmr:.0f} ккал"
        bot.send_message(call.message.chat.id, response)
        bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=menu_markup)


    @bot.callback_query_handler(func=lambda call: call.data == "calculate_tdee")
    def calculate_tdee(call):
        username = call.from_user.username

        if validate_user(username) == False:
            bot.send_message(call.message.chat.id, "Пожалуйста, укажите ваши данные через меню.")
            logger.error(f"Missing data for username: {username}")
            return None
        else:
            user = get_user_info(username)

        tdee = calculator.tdee(user.weight, user.height, user.age, user.activity_level, user.gender)
        tdee_goal = calculator.tdee_with_goal(tdee, user.goal)

        update_user(call.from_user.username, tdee=tdee, tdee_goal=tdee_goal)

        response = f"Ваш общий расход калорий: {tdee:.0f} ккал. \n" \
                      f"Для достижения вашей цели вам нужно потреблять {tdee_goal:.0f} ккал в день."
        bot.send_message(call.message.chat.id, response)
        bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=menu_markup)


    @bot.callback_query_handler(func=lambda call: call.data == "calculate_macros")
    def calculate_macros(call):
        username = call.from_user.username

        if validate_user(username) == False:
            bot.send_message(call.message.chat.id, "Пожалуйста, укажите ваши данные через меню.")
            logger.error(f"Missing data for username: {username}")
            return None
        else:
            user = get_user_info(username)

        tdee = calculator.tdee(user.weight, user.height, user.age, user.activity_level, user.gender)
        macros = calculator.macros(tdee)

        update_user(call.from_user.username, proteins=macros['proteins'], fats=macros['fats'], carbs=macros['carbs'])

        response = f"Ваша суточная норма БЖУ: \n" \
                     f"Белки: {macros['proteins']:.0f} гр\n" \
                     f"Жиры: {macros['fats']:.0f} гр\n" \
                     f"Углеводы: {macros['carbs']:.0f} гр"
        bot.send_message(call.message.chat.id, response)
        bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=menu_markup)
