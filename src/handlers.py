import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config
from database import get_user, create_user, update_subscription, get_all_users, create_static_profile, get_static_profiles, delete_static_profile, User, Session, get_user_stats as db_user_stats
from functions import create_vless_profile, generate_vless_url, get_user_stats

logger = logging.getLogger(__name__)

router = Router()

class AdminStates(StatesGroup):
    ADD_TIME = State()
    REMOVE_TIME = State()
    CREATE_STATIC_PROFILE = State()
    SEND_MESSAGE = State()

@router.message(Command("start"))
async def start_cmd(message: Message):
    logger.info(f"Start command from {message.from_user.id}")
    user = await get_user(message.from_user.id)
    if not user:
        is_admin = message.from_user.id in config.ADMINS
        user = await create_user(message.from_user.id, message.from_user.full_name, is_admin)
        await message.answer("Добро пожаловать! Вам предоставлен бесплатный тестовый период на 1 день.")
        await asyncio.sleep(2)
    
    await menu_cmd(message)

@router.message(Command("menu"))
async def menu_cmd(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await start_cmd(message)
        return
    
    status = "active" if user.subscription_end > datetime.utcnow() else "expired"
    expire_date = user.subscription_end.strftime("%Y-%m-%d %H:%M") if status == "active" else "Истекла"
    
    text = (
        f"**Имя профиля**: `{user.full_name}`{' [ADMIN]' if user.is_admin else ''}\n"
        f"**Id**: `{user.telegram_id}`\n"
        f"**Подписка**: `{status}`\n"
        f"**Дата окончания подписки**: `{expire_date}`"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Продлить", callback_data="renew_sub")
    builder.button(text="Подключить", callback_data="connect")
    builder.button(text="Статистика", callback_data="stats")
    builder.button(text="Помощь", callback_data="help")
    
    if user.is_admin:
        builder.button(text="Админ. меню", callback_data="admin_menu")
    
    builder.adjust(2, 2, 1)
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.is_admin:
        await callback.answer("Доступ запрещен!")
        return
    
    total, with_sub, without_sub = await db_user_stats()
    online_count = 0  # Заглушка для онлайн-статуса
    
    text = (
        "**Административное меню**\n\n"
        f"**Всего пользователей**: `{total}`\n"
        f"**С подпиской/Без подписки**: `{with_sub}`/`{without_sub}`\n"
        f"**Онлайн**: `{online_count}` | **Офлайн**: `{total - online_count}`"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="+ время", callback_data="admin_add_time")
    builder.button(text="- время", callback_data="admin_remove_time")
    builder.button(text="Список пользователей", callback_data="admin_user_list")
    builder.button(text="Статистика исп. сети", callback_data="admin_network_stats")
    builder.button(text="<-- Назад", callback_data="back_to_menu")
    builder.adjust(2, 1, 1, 1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "renew_sub")
async def renew_subscription(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    for months, price in config.PRICES.items():
        discount_price = price * (100 - config.DISCOUNT_PERCENT) / 100
        builder.button(
            text=f"{months} мес. - {discount_price:.0f}₽ (-{config.DISCOUNT_PERCENT}%)", 
            callback_data=f"pay_{months}"
        )
    builder.button(text="<-- Назад", callback_data="back_to_menu")
    builder.adjust(1)
    await callback.message.edit_text("Выберите тариф:", reply_markup=builder.as_markup())

@router.callback_query(F.data == "admin_user_list")
async def admin_user_list(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="С подпиской", callback_data="user_list_active")
    builder.button(text="Без подписки", callback_data="user_list_inactive")
    builder.button(text="Статические профили", callback_data="static_profiles_menu")
    builder.button(text="<-- Назад", callback_data="admin_menu")
    builder.adjust(1, 1, 1)
    await callback.message.edit_text("**Выберите фильтр**", reply_markup=builder.as_markup())

@router.callback_query(F.data == "static_profiles_menu")
async def static_profiles_menu(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить статический профиль", callback_data="static_profile_add")
    builder.button(text="Вывести статические профили", callback_data="static_profile_list")
    builder.button(text="<-- Назад", callback_data="admin_user_list")
    builder.adjust(1)
    await callback.message.edit_text("**Выберите действие**", reply_markup=builder.as_markup())

@router.callback_query(F.data == "static_profile_add")
async def static_profile_add(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите имя для статического профиля:")
    await state.set_state(AdminStates.CREATE_STATIC_PROFILE)

@router.message(AdminStates.CREATE_STATIC_PROFILE)
async def process_static_profile_name(message: Message, state: FSMContext):
    profile_name = message.text
    vless_url = await generate_vless_url("static_profile", 0)
    await create_static_profile(profile_name, vless_url)
    await message.answer(f"Профиль создан!\nVLESS: `{vless_url}`")
    await state.clear()

@router.callback_query(F.data == "static_profile_list")
async def static_profile_list(callback: CallbackQuery):
    profiles = await get_static_profiles()
    if not profiles:
        await callback.answer("Нет статических профилей")
        return
    
    for profile in profiles:
        builder = InlineKeyboardBuilder()
        builder.button(text="Удалить", callback_data=f"delete_static_{profile.id}")
        await callback.message.answer(
            f"**{profile.name}**\n`{profile.vless_url}`", 
            reply_markup=builder.as_markup()
        )

@router.callback_query(F.data.startswith("delete_static_"))
async def delete_static_profile(callback: CallbackQuery):
    profile_id = int(callback.data.split("_")[-1])
    await delete_static_profile(profile_id)
    await callback.answer("Профиль удален!")
    await callback.message.delete()

@router.callback_query(F.data == "connect")
async def connect_profile(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка профиля")
        return
    
    # Проверяем активность подписки
    if user.subscription_end < datetime.utcnow():
        await callback.answer("Подписка истекла! Продлите подписку.")
        return
    
    if not user.vless_profile_id:
        # Показываем пользователю, что идет создание профиля
        await callback.message.edit_text("Создаем ваш VPN профиль...")
        profile_id = await create_vless_profile(user.telegram_id)
        if profile_id:
            # Обновляем профиль в базе данных
            with Session() as session:
                db_user = session.query(User).filter_by(telegram_id=user.telegram_id).first()
                if db_user:
                    db_user.vless_profile_id = profile_id
                    session.commit()
        else:
            await callback.message.answer("Ошибка при создании профиля. Попробуйте позже.")
            return
    
    if user.vless_profile_id:
        vless_url = await generate_vless_url(user.vless_profile_id, user.telegram_id, config.XUI_HOST)
        text = (
            "**Ваш VPN профиль готов!**\n\n"
            "**Инструкция по подключению:**\n"
            "1. Скачайте приложение для вашей платформы:\n"
            "   - Windows: [V2RayN](https://github.com/2dust/v2rayN/releases)\n"
            "   - Android: [V2RayNG](https://github.com/2dust/v2rayNG/releases)\n"
            "   - iOS: [Shadowrocket](https://apps.apple.com/app/shadowrocket/id932747118)\n"
            "   - Mac: [V2RayU](https://github.com/yanue/V2rayU/releases)\n\n"
            "2. Скопируйте эту ссылку и импортируйте в приложение:\n"
            f"`{vless_url}`\n\n"
            "3. Активируйте соединение в приложении."
        )
        await callback.message.edit_text(text)
    else:
        await callback.answer("Ошибка создания профиля")

@router.callback_query(F.data == "stats")
async def user_stats(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.vless_profile_id:
        await callback.answer("Профиль не создан")
        return
    
    stats = await get_user_stats(user.vless_profile_id)
    text = (
        "**Ваша статистика:**\n\n"
        f"Загружено: `{stats.get('upload', 0) / 1024 / 1024:.2f} MB`\n"
        f"Скачано: `{stats.get('download', 0) / 1024 / 1024:.2f} MB`"
    )
    await callback.message.answer(text)

@router.callback_query(F.data == "admin_network_stats")
async def network_stats(callback: CallbackQuery):
    # Заглушка для статистики сети
    text = (
        "**Статистика использования сети:**\n\n"
        "За месяц:\n"
        "Upload - `15.2 GB` | Download - `42.7 GB`\n\n"
        "За всё время:\n"
        "Upload - `152.3 GB` | Download - `427.8 GB`"
    )
    await callback.message.answer(text)

@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery):
    months = int(callback.data.split("_")[1])
    # Заглушка для платежной системы
    await callback.answer("Оплата временно недоступна")
    await update_subscription(callback.from_user.id, months * 30)
    await menu_cmd(callback.message)

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await menu_cmd(callback.message)

def setup_handlers(dp: Dispatcher):
    dp.include_router(router)
    logger.info("Handlers setup completed")