import asyncio
import json
import logging
from handlers.user.states import UserStates
import xui.public
from datetime import datetime
from aiogram import Bot, Dispatcher, Router
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import MAX_MESSAGE_LENGTH, config
from database.database import Session
from database.user import User, UserType, create_user, get_user
from .admin.base import routers as routers_admin
from .user.routers import routers as routers_user

logger = logging.getLogger(__name__)
router = Router()

def setup_handlers(dp: Dispatcher):
    dp.include_router(router)
    for r in routers_admin + routers_user:
        dp.include_router(r)
    logger.info("✅ Handlers setup completed")
    
def split_text(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list:
    """Разбивает текст на части указанной максимальной длины"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        part = text[:max_length]
        last_newline = part.rfind('\n')
        if last_newline != -1:
            part = part[:last_newline]
        parts.append(part)
        text = text[len(part):].lstrip()
    return parts

async def show_menu(bot: Bot, chat_id: int, message_id: int = None):
    """Функция для отображения меню (может как редактировать существующее сообщение, так и отправлять новое)"""
    user = await get_user(chat_id)
    if not user:
        return
    
    if user.subscription_end is None:
        status = "Неактивна"
        expire_date = "Нет"
    else:
        status = "Активна" if user.subscription_end > datetime.utcnow() else "Истекла"
        expire_date = user.subscription_end.strftime("%d-%m-%Y %H:%M") if status == "Активна" else status
    
    text = (
        f"**Профиль**: `{user.username}`\n"
        f"**id**: `{user.telegram_id}`\n"
        f"**Персональная скидка**: `{user.discount_percent}%`\n"
        f"**Подписка**: `{status}`\n"
        f"**Дата окончания подписки**: `{expire_date}`"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 Продлить" if status=="Активна" else "💵 Оплатить", callback_data="renew_sub")
    if status != "Неактивна":
        builder.button(text="✅ Подключить", callback_data="connect")
    builder.button(text="📊 Статистика", callback_data="stats")
    builder.button(text="🎁 Промокод", callback_data="user:activate_promocode")
    builder.button(text="ℹ️ Помощь", callback_data="help")
    
    if user.is_admin:
        builder.button(text="⚠️ Админ. меню", callback_data="admin_menu")
    
    builder.adjust(2, 2, 1)
    
    if message_id:
        # Редактируем существующее сообщение
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode='Markdown'
        )
    else:
        # Отправляем новое сообщение
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode='Markdown'
        )

@router.message(Command("start"))
async def start_cmd(message: Message, bot: Bot):
    logger.info(f"ℹ️  Start command from {message.from_user.id}")
    user = await get_user(message.from_user.id)
    
    # Обновляем данные пользователя если они изменились
    update_data = {}
    if user:
        if user.full_name != message.from_user.full_name:
            update_data["full_name"] = message.from_user.full_name
        if user.username != message.from_user.username:
            update_data["username"] = message.from_user.username
    else:
        is_admin = message.from_user.id in config.ADMINS
        user = await create_user(
            telegram_id=message.from_user.id, 
            full_name=message.from_user.full_name,
            username=message.from_user.username,
            is_admin=is_admin
        )
        await message.answer(f"Добро пожаловать в VPN бота `{(await bot.get_me()).full_name}`!\nВам предоставлен **бесплатный** тестовый период на **1 день**!", parse_mode='Markdown')
        await asyncio.sleep(2)
    
    # Обновляем данные если есть изменения
    if update_data:
        with Session() as session:
            db_user = session.query(User).get(user.id)
            for key, value in update_data.items():
                setattr(db_user, key, value)
            session.commit()
            logger.info(f"🔄 Updated user data: {message.from_user.id}")
    
    await show_menu(bot, message.from_user.id)

@router.message(Command("menu"))
async def menu_cmd(message: Message, bot: Bot):
    user = await get_user(message.from_user.id)
    if not user:
        await start_cmd(message, bot)
        return
    
    # Проверяем изменения данных
    update_data = {}
    if user.full_name != message.from_user.full_name:
        update_data["full_name"] = message.from_user.full_name
    if user.username != message.from_user.username:
        update_data["username"] = message.from_user.username
    
    # Обновляем данные если есть изменения
    if update_data:
        with Session() as session:
            db_user = session.query(User).get(user.id)
            for key, value in update_data.items():
                setattr(db_user, key, value)
            session.commit()
            logger.info(f"🔄 Updated user data in menu: {message.from_user.id}")
    
    await show_menu(bot, message.from_user.id)

@router.callback_query(F.data == "help")
async def help_msg(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Опишите свою проблему:")
    await state.set_state(UserStates.waiting_help_text)

@router.message(StateFilter(UserStates.waiting_help_text))
async def handle_user_help_message_text(msg: Message, state: FSMContext, bot: Bot):
    message_for_admins = (
        f"Пользователь (@{msg.from_user.username}) запросил помощь\n"
        f">{msg.text}"
    )
    for admin_id in config.ADMINS:
        try:
            await bot.send_message(admin_id, message_for_admins)
        except Exception as e:
            logger.error(f"🛑 Failed to send notification to admin {admin_id}: {e}")

@router.callback_query(F.data == "connect")
async def connect_profile(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("🛑 Ошибка профиля")
        return

    if user.type == UserType.EXPIRED or (user.subscription_end is not None and user.subscription_end < datetime.utcnow()):
        await callback.answer("⚠️ Подписка истекла! Продлите подписку.")
        return
    
    if not user.vless_profile_data:
        await callback.message.edit_text("⚙️ Создаем ваш VPN профиль...")
        profile_data = await xui.public.create_vless_profile(user.telegram_id)
        
        if profile_data:
            with Session() as session:
                db_user = session.query(User).filter_by(telegram_id=user.telegram_id).first()
                if db_user:
                    db_user.vless_profile_data = json.dumps(profile_data)
                    session.commit()
            user = await get_user(user.telegram_id)
        else:
            await callback.message.answer("🛑 Ошибка при создании профиля. Попробуйте позже.")
            return
    
    profile_data = safe_json_loads(user.vless_profile_data, default={})
    if not profile_data:
        await callback.message.answer("⚠️ У вас пока нет созданного профиля.")
        return
    vless_url = xui.public.generate_vless_url(profile_data)
    text = (
        "🎉 **Ваш VPN профиль готов!**\n\n"
        "ℹ️ **Инструкция по подключению:**\n"
        "1. Скачайте приложение для вашей платформы\n"
        "2. Скопируйте эту ссылку и импортируйте в приложение:\n\n"
        f"`{vless_url}`\n\n"
        "3. Активируйте соединение в приложении."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text='🖥️ Windows [V2RayN]', url='https://github.com/2dust/v2rayN/releases/download/7.13.8/v2rayN-windows-64-desktop.zip')
    builder.button(text='🐧 Linux [NekoBox]', url='https://github.com/MatsuriDayo/nekoray/releases/download/4.0.1/nekoray-4.0.1-2024-12-12-debian-x64.deb')
    builder.button(text='🍎 Mac [V2RayU]', url='https://github.com/yanue/V2rayU/releases/download/v4.2.6/V2rayU-64.dmg ')
    builder.button(text='🍏 iOS [V2RayTun]', url='https://apps.apple.com/ru/app/v2raytun/id6476628951')
    builder.button(text='🤖 Android [V2RayNG]', url='https://github.com/2dust/v2rayNG/releases/download/1.10.16/v2rayNG_1.10.16_arm64-v8a.apk')
    builder.button(text="⬅️ Назад", callback_data="back_to_menu")
    builder.adjust(2, 2, 1, 1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode='Markdown')

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    await show_menu(bot, callback.from_user.id, callback.message.message_id)

@router.callback_query(F.data == "stats")
async def user_stats(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.vless_profile_data:
        await callback.answer("⚠️ Профиль не создан")
        return
    await callback.message.edit_text("⚙️ Загружаем вашу статистику...")
    profile_data = safe_json_loads(user.vless_profile_data, default={})
    stats = await xui.public.get_user_stats(profile_data["email"])

    logger.debug(stats)
    upload = f"{stats.get('upload', 0) / 1024 / 1024:.2f}"
    upload_size = 'MB' if int(float(upload)) < 1024 else 'GB'
    if upload_size == "GB":
        upload = f"{int(float(upload) / 1024):.2f}"

    download = f"{stats.get('download', 0) / 1024 / 1024:.2f}"
    download_size = 'MB' if int(float(download)) < 1024 else 'GB'
    if download_size == "GB":
        download = f"{int(float(download) / 1024):.2f}"

    await callback.message.delete()
    text = (
        "📊 **Ваша статистика:**\n\n"
        f"🔼 Загружено: `{upload} {upload_size}`\n"
        f"🔽 Скачано: `{download} {download_size}`\n"
    )
    await callback.message.answer(text, parse_mode='Markdown')

def safe_json_loads(data, default=None):
    if not data:
        return default
    try:
        return json.loads(data)
    except Exception:
        return default