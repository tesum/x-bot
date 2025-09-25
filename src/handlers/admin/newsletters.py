import asyncio
import json
import logging
import xui.public
from .states import AdminStates
from datetime import datetime
from aiogram import Bot, Router
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config
from database.database import Session
from database.user import User, UserType, create_user, get_all_users, get_user

logger = logging.getLogger(__name__)
router = Router()

# Обработчики для рассылки сообщений
@router.callback_query(F.data == "admin_send_message")
async def admin_send_message_start(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ С подпиской", callback_data="target_active")
    builder.button(text="🛑 Без подписки", callback_data="target_inactive")
    builder.button(text="👥 Всем пользователям", callback_data="target_all")
    builder.button(text="↩️ Назад", callback_data="admin_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "Выберите целевую аудиторию для рассылки:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("target_"))
async def admin_send_message_target(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Снимаем анимацию
    target = callback.data.split("_")[1]
    await state.update_data(target=target)
    await callback.message.answer("Введите сообщение для рассылки:")
    await state.set_state(AdminStates.SEND_MESSAGE)

@router.message(AdminStates.SEND_MESSAGE)
async def admin_send_message(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    target = data['target']
    text = message.text
    
    users = []
    if target == "active":
        users = await get_all_users(with_subscription=True)
    elif target == "inactive":
        users = await get_all_users(with_subscription=False)
    else:  # all
        users = await get_all_users()
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            await bot.send_message(user.telegram_id, text)
            success += 1
        except Exception as e:
            logger.error(f"🛑 Ошибка отправки сообщения {user.telegram_id}: {e}")
            failed += 1
    
    await message.answer(
        f"📨 Результаты рассылки:\n\n"
        f"• Успешно: {success}\n"
        f"• Не удалось: {failed}\n"
        f"• Всего: {len(users)}"
    )
    await state.clear()