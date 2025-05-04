import datetime
import logging

from sqlalchemy import and_

from .database import get_session
from .models import Base, MealsDiary, Message, User

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def log_message(username, message_text):
    session = get_session()
    new_message = Message(
        timestamp=datetime.datetime.now(),
        username=username,
        message_text=message_text
    )
    session.add(new_message)
    session.commit()
    session.close()


def update_user(username: str, **kwargs):
    session = get_session()
    user = session.query(User).filter(User.username == username).first()
    if user:
        for attr, value in kwargs.items():
            if value is not None:
                setattr(user, attr, value)
        logger.info(f"User {username} updated with values {kwargs}")
        print(f"User {username} updated with values {kwargs}")
        session.commit()
        session.close()
    else:
        new_user = User(username=username)
        session.add(new_user)
        logger.info(f"New user {username} added")
        print(f"New user {username} added")
        session.commit()
        session.close()


def validate_user(username: str) -> bool:
    session = get_session()
    user = session.query(User).filter(User.username == username).first()
    session.close()
    if not user:
        return False
    else:
        # check that all required fields are filled
        if None in [user.height, user.weight, user.age, user.activity_level, user.goal]:
            return False
        else:
            return True


def get_user_info(username: str) -> User:
    session = get_session()
    user = session.query(User).filter(User.username == username).first()
    session.close()
    if user:
        return user
    else:
        return None


def add_meal(
        username: str, timestamp: datetime.datetime,
        calories: float, carbs: float, proteins: float, fats: float, comment: str
):
    session = get_session()
    new_meal = MealsDiary(
        username=username,
        timestamp=timestamp,
        calories=calories,
        carbs=carbs,
        proteins=proteins,
        fats=fats,
        comment=comment
    )
    session.add(new_meal)
    session.commit()
    session.close()


def get_meals_in_date_range(username: str, start_date: datetime.datetime, end_date: datetime.datetime):
    session = get_session()
    meals = session.query(MealsDiary).filter(
        and_(
            MealsDiary.username == username,
            MealsDiary.timestamp >= start_date,
            MealsDiary.timestamp <= end_date
        )
    ).all()
    session.close()
    return meals


def get_aggregate_last_24_hours(username: str):
    session = get_session()
    one_day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
    from sqlalchemy import func
    aggregate_data = session.query(
        func.sum(MealsDiary.calories),
        func.sum(MealsDiary.carbs),
        func.sum(MealsDiary.proteins),
        func.sum(MealsDiary.fats)
    ).filter(
        and_(
            MealsDiary.username == username,
            MealsDiary.timestamp >= one_day_ago
        )
    ).first()
    session.close()

    data = {}
    data["calories"] = aggregate_data[0] if aggregate_data[0] else 0
    data["carbs"] = aggregate_data[1] if aggregate_data[1] else 0
    data["proteins"] = aggregate_data[2] if aggregate_data[2] else 0
    data["fats"] = aggregate_data[3] if aggregate_data[3] else 0

    return data


def get_all_users():
    session = get_session()
    try:
        users = session.query(User).all()
        session.close()
        return users
    finally:
        session.close()