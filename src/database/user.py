from sqlalchemy import create_engine, Column, ARRAY, Integer, String, DateTime, Boolean, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

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
    applied_promocodes = Column(ARRAY(String), default=list)
    discount_percent = Column(Int, nullable=True)
    

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

async def user_apply_promocode(session: Session, telegram_id: int, code: str) {
    user = get_user(telegram_id)
    if user and code not in user.applied_promocodes:
        discount = apply_promocode(session, code)
        if discount > 0:
            user.discount_percent = discount
            user.applied_promocodes.append(code)
            logger.info(f"✅ Promocode applied for {telegram_id}: discount -{discount}%")
        session.commit()
        return discount
    return 0
}

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