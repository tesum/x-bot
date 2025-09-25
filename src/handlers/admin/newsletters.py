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
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config
from database.database import Session
from database.user import User, UserType, create_user, get_all_users, get_user, get_user_by_username

logger = logging.getLogger(__name__)
router = Router()

# Обработчики для рассылки сообщений
@router.callback_query(F.data == "admin_send_message")
async def admin_send_message_start(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ С подпиской", callback_data="admin:send_message:active")
    builder.button(text="🛑 Без подписки", callback_data="admin:send_message:inactive")
    builder.button(text="👥 Одному пользователю", callback_data="admin:send_personal_newsletter")
    builder.button(text="👥 Всем пользователям", callback_data="admin:send_message:all")
    builder.button(text="↩️ Назад", callback_data="admin_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "Выберите целевую аудиторию для рассылки:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("admin:send_message:"))
async def admin_send_message_target(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Снимаем анимацию
    target = callback.data.split(":")[2]
    await state.update_data(target=target)
    await callback.message.answer("Введите сообщение для рассылки:")
    await state.set_state(AdminStates.SEND_MESSAGE)

@router.callback_query(lambda c: c.data == "admin:send_personal_newsletter")
async def ask_username(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введи юзернейм пользователя, которому нужно отправить рассылку:")
    await state.set_state(AdminStates.send_message_waiting_username)
    await callback.answer()

@router.message(StateFilter(AdminStates.send_message_waiting_username))
async def ask_message_text(msg: Message, state: FSMContext):
    await state.update_data(username=msg.text.strip())
    await state.update_data(target="single")
    await msg.answer("Введи текст рассылки:")
    await state.set_state(AdminStates.send_message_waiting_text)

@router.message(StateFilter(AdminStates.send_message_waiting_text))
async def send_newsletter_now(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    username = data['username']
    target = data['target']
    text = msg.text.strip()

    users = []
    if target == "active":
        users = await get_all_users(with_subscription=True)
    elif target == "inactive":
        users = await get_all_users(with_subscription=False)
    elif target == "single":
        user = await get_user_by_username(username)
        if user:
            users.append(user)
        else:
            await msg.answer("Пользователь не найден или не запускал бота.")
            await state.clear()
            return
    else:
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
    
    await msg.answer(
        f"📨 Результаты рассылки:\n\n"
        f"• Успешно: {success}\n"
        f"• Не удалось: {failed}\n"
        f"• Всего: {len(users)}"
    )
    await state.clear()
