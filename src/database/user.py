import logging
from sqlalchemy import create_engine, Column, ARRAY, Integer, String, DateTime, Boolean, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
from enum import Enum
from config import config
from .database import Base, Session
from database.promocodes import apply_promocode

logger = logging.getLogger(__name__)

class UserType(str, Enum):
    NEW = "new"
    ACTIVE = "active"
    EXPIRED = "expired"

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    type = Column(SAEnum(UserType), default=UserType.NEW)
    telegram_id = Column(Integer, unique=True)
    full_name = Column(String)
    username = Column(String)
    registration_date = Column(DateTime, default=datetime.utcnow)
    subscription_end = Column(DateTime)
    vless_profile_id = Column(String)
    vless_profile_data = Column(String)
    is_admin = Column(Boolean, default=False)
    notified = Column(Boolean, default=False)
    discount_percent = Column(Integer, default=0)
    

async def get_user(telegram_id: int):
    with Session() as session:
        return session.query(User).filter_by(telegram_id=telegram_id).first()

async def create_user(telegram_id: int, full_name: str, username: str = None, is_admin: bool = False):
    with Session() as session:
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            subscription_end=datetime.utcnow() + timedelta(days=3),
            is_admin=is_admin
        )
        session.add(user)
        session.commit()
        logger.info(f"✅ New user created: {telegram_id}")
        return user

async def delete_user_profile(telegram_id: int):
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.vless_profile_data = None
            user.notified = False
            user.type = UserType.EXPIRED
            session.commit()
            logger.info(f"✅ User vless-profile deleted: {telegram_id}")

async def update_subscription(telegram_id: int, months: int):
    """Обновляет подписку с учетом текущего состояния"""
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            now = datetime.utcnow()
            # Если подписка активна, добавляем к текущей дате окончания
            if  user.type == UserType.ACTIVE and user.subscription_end > now:
                user.subscription_end += timedelta(days=months * 30)
            else:
                # Если подписка истекла, начинаем с текущей даты
                user.subscription_end = now + timedelta(days=months * 30)
                user.type = UserType.ACTIVE
            
            # Сбрасываем флаг уведомления
            user.notified = False
            session.commit()
            logger.info(f"✅ Subscription updated for {telegram_id}: +{months} months")
            return True
        return False

async def user_apply_promocode(telegram_id: int, code: str):
    with Session() as session:
        user = await get_user(telegram_id)
        if user:
            discount = await apply_promocode(session, code)
            if discount > 0:
                user.discount_percent = discount
                session.commit()
                logger.info(f"✅ Promocode applied for {telegram_id}: discount -{discount}%")
            else:
                logger.info(f"✅ User {telegram_id} tried use promocode {code} and get discount {discount}%")
            return discount
        return 0

async def get_all_users(with_subscription: bool = None):
    with Session() as session:
        query = session.query(User)
        if with_subscription is not None:
            if with_subscription:
                query = query.filter(User.subscription_end > datetime.utcnow())
            else:
                query = query.filter(User.subscription_end <= datetime.utcnow())
        return query.all()

async def get_user_stats():
    with Session() as session:
        total = session.query(func.count(User.id)).scalar()
        with_sub = session.query(func.count(User.id)).filter(User.subscription_end > datetime.utcnow()).scalar()
        without_sub = total - with_sub
        return total, with_sub, without_sub
    
async def calculate_price(telegram_id: int, months: int) -> int:
    """Вычисляет итоговую стоимость с учетом скидки"""
    user = await get_user(telegram_id)

    if months not in config.PRICES:
        return 0
    
    price_info = config.PRICES[months]
    base_price = price_info["base_price"]
    discount_percent = price_info["discount_percent"]
    personal_discount = user.discount_percent
    total_discount = 1 - (discount_percent + personal_discount) / 100
    final_price = round(base_price * max(total_discount, 0))
    logger.debug(f"Calculate price with personal_discount: {personal_discount}% total sum: {total_discount}, base_price: {base_price}, final price: {final_price}")
    return final_price
