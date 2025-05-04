import logging
from datetime import datetime

from omegaconf import OmegaConf

from telegram_bot.api.endpoints.menu import menu_markup
from telegram_bot.db.crud import add_meal, get_aggregate_last_24_hours, get_user_info

app_config = OmegaConf.load("./telegram_bot/conf/app.yaml")

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

buffer = {}

def register_handlers(bot):
    @bot.callback_query_handler(func=lambda call: call.data == "enter_meal")
    def enter_meal(call):
        bot.send_message(call.message.chat.id, app_config.strings.enter_meal)
        buffer[call.message.chat.id] = {}
        msg = bot.send_message(call.message.chat.id, app_config.strings.enter_calories)
        bot.register_next_step_handler(msg, save_calories)

    def save_calories(message):
        calories = int(message.text)
        buffer[message.chat.id]["calories"] = calories
        msg = bot.send_message(message.chat.id, app_config.strings.enter_proteins)
        bot.register_next_step_handler(msg, save_proteins)

    def save_proteins(message):
        proteins = int(message.text)
        buffer[message.chat.id]["proteins"] = proteins
        msg = bot.send_message(message.chat.id, app_config.strings.enter_fats)
        bot.register_next_step_handler(msg, save_fats)

    def save_fats(message):
        fats = int(message.text)
        buffer[message.chat.id]["fats"] = fats
        msg = bot.send_message(message.chat.id, app_config.strings.enter_carbs)
        bot.register_next_step_handler(msg, save_carbs)

    def save_carbs(message):
        carbs = int(message.text)
        buffer[message.chat.id]["carbs"] = carbs
        msg = bot.send_message(message.chat.id, app_config.strings.enter_comment)
        bot.register_next_step_handler(msg, save_comment)

    def save_comment(message):
        user = get_user_info(message.from_user.username)
        comment = message.text
        buffer[message.chat.id]["comment"] = comment
        meal_data = buffer[message.chat.id]
        add_meal(
            username=message.from_user.username,
            calories=meal_data["calories"],
            proteins=meal_data["proteins"],
            fats=meal_data["fats"],
            carbs=meal_data["carbs"],
            comment=meal_data["comment"],
            timestamp=datetime.now()
        )
        bot.send_message(message.chat.id, "Прием пищи сохранен.")

        last_meals_data = get_aggregate_last_24_hours(
            user.username
        )

        # compute how much calories and macros left to the user after the meal
        calories_left = user.tdee_goal - last_meals_data["calories"]
        protein_left = user.proteins - last_meals_data["proteins"]
        fat_left = user.fats - last_meals_data["fats"]
        carbs_left = user.carbs - last_meals_data["carbs"]


        bot.send_message(message.chat.id,
                         f"Осталось калорий: {calories_left:.0f} ккал\n"
                         f"Осталось белка: {protein_left:.0f} г\n"
                         f"Осталось жира: {fat_left:.0f} г\n"
                         f"Осталось углеводов: {carbs_left:.0f} г\n"
        )

        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=menu_markup)
        buffer[message.chat.id] = {}
