import logging

from sqlalchemy import update, select, exists, delete
from sqlalchemy.sql import func

from .database import get_session
from .models import Base, User, Question, Answer, Image, Admins

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

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

def update_question_id(username, quest_id):
    session = get_session()
    stmt = update(User).where(User.username == username).values(**quest_id)
        
    session.execute(stmt)
    
    session.commit()
    session.close()

def get_current_question_id(username: str) -> User:
    session = get_session()
    last_current_question_id = session.query(User).filter(User.username == username).first()
    session.close()
    return last_current_question_id.current_question_id

def get_question(id_quest: int) -> Question:
    data = {
        'Quest': '',
        'Answers_quest': {},
        'Id_answer_quest': {}
    }
    
    session = get_session()
    data_quest = session.query(Question).filter(Question.id == id_quest).first()
    print(data_quest)
    data['Quest'] = data_quest.data_question
    data['Answers_quest'] = data_quest.answer_options
    data['Id_answer_quest'] = data_quest.next_question_id

    return data

def get_answer(id_answ):
    session = get_session()
    
    result = session.query(Answer).filter(Answer.id == id_answ).first()
    
    return result.text_answer
    
def get_id_image(id_quest):
    session = get_session()
    
    list_id = session.execute(
        select(Image.id).where(func.json_contains(Image.id_quest, str([id_quest])))
    ).scalars().all()

    return list(list_id)

def get_data_img(id_img):
    session = get_session()
    
    data = session.query(Image).filter(Image.id == id_img).first()

    return data.id_quest

def del_img_db(id_img):
    session = get_session()

    image = session.query(Image).filter(Image.id == id_img).first()

    if image:
        image.id_quest = None
        session.commit()

def get_last_image_id():
    session = get_session()
    
    last_id = session.query(func.max(Image.id)).scalar()
    return last_id

def add_image_with_id(id_quest):
    image_id = get_last_image_id()+1
    
    session = get_session()
    
    new_image = Image(id=image_id, id_quest=id_quest)
    
    session.add(new_image)
    
    session.commit()
    
    session.close()

def check_id_admin(id_tg):
    session = get_session()
    
    return session.query(exists().where(Admins.id_tg == id_tg)).scalar()

def get_all_admin_ids() -> list[int]:
    session = get_session()
    admin_ids = session.query(Admins.id_tg).all()
    
    return [admin_id[0] for admin_id in admin_ids]

def delete_admin_by_id_tg(id_tg: int) -> bool:
    session = get_session()
    
    result = session.execute(
        delete(Admins).where(Admins.id_tg == id_tg)
    )
    
    session.commit()
    
    return result.rowcount > 0

def add_admin_by_id_tg(id_tg: int) -> bool:
    session = get_session()
    
    if session.query(Admins).filter(Admins.id_tg == id_tg).first():
        return False

    new_admin = Admins(id_tg=id_tg)

    session.add(new_admin)

    session.commit()

    return True