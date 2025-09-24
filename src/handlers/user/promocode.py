from aiogram import Router

router = Router()

@router.callback_query(F.data.startswith("use_promocode:"))
async def use_promocode_callback(callback: CallbackQuery):
    code = callback.data.split(":", 1)[1]  # получаем промокод из callback_data

    with Session() as session:
        discount = user_apply_promocode(session, telegram_id: callback.from_user.id, code)
        if discount:
            await callback.message.answer(f"Промокод применён! Скидка {discount}% 🎉")
        else:
            await callback.message.answer("Промокод неактивен или истёк!")

    await callback.answer()  # чтобы скрыть "часики"