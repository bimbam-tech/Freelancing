from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    username = Column(Integer)
    message_text = Column(String)


class User(Base):
    __tablename__ = 'users_diet_bot'
    username = Column(String, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    chat_id = Column(Integer)
    phone_number = Column(String)
    height = Column(Integer)
    weight = Column(Integer)
    age = Column(Integer)
    gender = Column(Integer)
    activity_level = Column(Integer)
    goal = Column(Integer)
    bmr = Column(Integer)
    tdee = Column(Integer)
    tdee_goal = Column(Integer)
    proteins = Column(Integer)
    fats = Column(Integer)
    carbs = Column(Integer)


class MealsDiary(Base):
    __tablename__ = 'meals_diary'

    username = Column(String, primary_key=True)
    timestamp = Column(DateTime, primary_key=True)
    calories = Column(Integer)
    carbs = Column(Integer)
    proteins = Column(Integer)
    fats = Column(Integer)
    comment = Column(String)
