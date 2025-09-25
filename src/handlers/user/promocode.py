import asyncio
import json
import logging
import xui.public
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
from .states import UserStates
from database.user import User, UserType, create_user, get_user, user_apply_promocode

router = Router()

@router.callback_query(F.data == "user:activate_promocode")
async def user_start_promocode_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Введите промокод:")
    await state.set_state(UserStates.waiting_promocode)
    await callback.answer()

@router.message(StateFilter(UserStates.waiting_promocode))
async def user_handle_promocode_input(msg: Message, state: FSMContext):
    code = msg.text.strip().upper()
    discount = await user_apply_promocode(msg.from_user.id, code)
    if discount > 0:
        await msg.answer(f"✅ Промокод активирован! Ваша скидка: {discount}%")
        await state.clear()
        
    else:
        await msg.answer("Промокод не найден, уже использован или истёк.")
        # Оставить state, чтобы попросить повторить