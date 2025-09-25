import logging
from aiogram import Router
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "admin:enable_market")
async def admin_enable_market(callback: CallbackQuery):
    config.IS_STOP_MARKET = not config.IS_STOP_MARKET
    text = f"Успешно изменено. Продажи выключены: {config.IS_STOP_MARKET}"

    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="back_to_menu")
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode='Markdown')