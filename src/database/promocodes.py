from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
import datetime
from .database import Base, Session

class PromoCode(Base):
    __tablename__ = 'promocodes'
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    discount_percent = Column(Integer, default=0)
    uses_left = Column(Integer, default=1)  # сколько раз еще можно использовать
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)

async def create_promocode(session: Session, code: str, discount_percent: int, uses_left: int = 1, valid_until: datetime = None) -> PromoCode:
    if await get_promocode(session, code) is not None:
        raise ValueError(f"Промокод '{code}' уже существует!")

    promo = PromoCode(
        code=code,
        discount_percent=discount_percent,
        uses_left=uses_left,
        is_active=True,
        valid_until=valid_until
    )
    session.add(promo)
    session.commit()
    return promo

async def get_promocode(session: Session, code: str) -> PromoCode:
    return session.query(PromoCode).filter_by(code=code).first()

def check_promocode_valid(promo: PromoCode) -> bool:
    if not promo or not promo.is_active:
        return False
    if promo.valid_until and promo.valid_until < datetime.datetime.utcnow():
        return False
    if promo.uses_left is not None and promo.uses_left <= 0:
        return False
    return True

async def apply_promocode(session: Session, code: str) -> int:
    promo = await get_promocode(session, code)
    if not check_promocode_valid(promo):
        return 0  # невалиден

    if promo.uses_left is not None:
        promo.uses_left -= 1
        if promo.uses_left <= 0:
            promo.is_active = False
    session.commit()
    return promo.discount_percent

async def disable_promocode(session: Session, code: str):
    promo = get_promocode(session, code)
    if promo:
        promo.is_active = False
        session.commit()
