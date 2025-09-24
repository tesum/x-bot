import asyncio
import logging
import json
from datetime import datetime, timedelta
from aiogram import Dispatcher, Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config
from database import (
    StaticProfile, get_user, create_user, update_subscription, 
    get_all_users, create_static_profile, get_static_profiles, 
    User, Session, get_user_stats as db_user_stats
)
from database import UserType
from functions import create_vless_profile, delete_client_by_email, generate_vless_url, get_user_stats, create_static_client, get_global_stats, get_online_users

logger = logging.getLogger(__name__)

def setup_handlers(dp: Dispatcher):
    dp.include_router(router)
    logger.info("✅ Handlers setup completed")