from sqlalchemy import Column, Integer, Text, JSON, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users_quiz'
    username = Column(String, primary_key=True)
    chat_id = Column(Integer, nullable=True)
    current_question_id = Column(Integer, nullable=True)

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_question = Column(String(255), nullable=False)
    answer_options = Column(JSON, nullable=False)
    next_question_id = Column(JSON, nullable=False)
    
class Answer(Base):
    __tablename__ = 'answers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    text_answer = Column(Text, nullable=False)
    
class Image(Base):
    __tablename__ = 'image'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_quest = Column(JSON, nullable=False)
    
class Admins(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_tg = Column(Integer, nullable=False)