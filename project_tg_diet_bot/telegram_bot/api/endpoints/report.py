import logging
import schedule
import time
from datetime import datetime, timedelta
from telegram_bot.db.crud import get_all_users, get_meals_in_date_range


# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_daily_reports(bot):
    users = get_all_users()
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now()

    for user in users:
        logger.info(f"Sending report to {user.username} in chat {user.chat_id}")
        last_meals_data = get_meals_in_date_range(
            user.username,
            start_date=start_date,
            end_date=end_date
        )
        if not last_meals_data:
            bot.send_message(user.chat_id, "За последние 24 часа приемов пищи не найдено.")
        else:
            total_calories = sum(meal.calories for meal in last_meals_data)
            total_proteins = sum(meal.proteins for meal in last_meals_data)
            total_fats = sum(meal.fats for meal in last_meals_data)
            total_carbs = sum(meal.carbs for meal in last_meals_data)

            report = (
                f"Отчет за последние 24 часа:\n"
                f"Калории: {total_calories}\n"
                f"Белки: {total_proteins}\n"
                f"Жиры: {total_fats}\n"
                f"Углеводы: {total_carbs}"
            )
            bot.send_message(user.chat_id, report)
