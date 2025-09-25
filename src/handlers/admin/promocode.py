import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.database import Session
from database.user import User, get_user, get_user_stats as db_user_stats
from database.promocodes import create_promocode
from config import config
from .states import AdminStates

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "admin:generate_promocode")
async def start_promocode_callback(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Введите промокод, скидку %, лимит и срок (YYYY-MM-DD):")
    await callback.answer()
    
@router.message(F.text.regexp(r"^\w+\s+\d+\s+\d+\s+\d{4}-\d{2}-\d{2}$"))
async def handle_promocode_data(msg: Message):
    # Проверка прав
    if msg.from_user.id not in config.ADMINS:
        return
    code, discount, uses, valid_until = msg.text.split()
    discount, uses = int(discount), int(uses)
    with Session() as session:
        try:
            await create_promocode(session, code, discount, uses, datetime.strptime(valid_until, "%Y-%m-%d"))
            await msg.answer(f"✅ Промокод {code} на {discount}% создан. До {valid_until}, использований: {uses}")
        except ValueError as e:
            logger.error(f"❌ Error create promocode: {e}")
            await msg.answer(str(e))