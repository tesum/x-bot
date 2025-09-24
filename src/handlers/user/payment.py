from aiogram import Router

router = Router()

@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    
    try:
        months = int(callback.data.split("_")[1])
        if months not in config.PRICES:
            await callback.message.answer("❌ Неверный период подписки")
            return
            
        final_price = config.calculate_price(months)
        suffix = "месяц" if months == 1 else "месяца" if months in (2,3,4) else "месяцев"
        # Создаем инвойс для оплаты
        prices = [LabeledPrice(label=f"VPN подписка на {months} мес.", amount=final_price * 100)]
        if config.PAYMENT_TOKEN:
            await bot.send_invoice(
                chat_id=callback.from_user.id,
                title=f"VPN подписка на {months} месяцев",
                description=f"Доступ к VPN сервису на {months} {suffix}",
                payload=f"subscription_{months}",
                provider_token=config.PAYMENT_TOKEN,
                currency="RUB",
                prices=prices,
                start_parameter="create_subscription",
                need_email=True,
                need_phone_number=False
            )
        else:
            await callback.message.answer("❌ Оплата временно недоступна")
    except Exception as e:
        logger.error(f"🛑 Payment error: {e}")
        await callback.message.answer("❌ Ошибка при создании счета на оплату")

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot):
    try:
        # Извлекаем информацию из payload
        payload = message.successful_payment.invoice_payload
        if payload.startswith("subscription_"):
            months = int(payload.split("_")[1])
            final_price = config.calculate_price(months)  # Переводим обратно в рубли
            
            # Получаем информацию о пользователе
            user = await get_user(message.from_user.id)
            if not user:
                await message.answer("❌ Ошибка: пользователь не найден")
                return
            
            # Определяем тип действия (покупка или продление)
            action_type = "куплена" if user.type == UserType.NEW else "продлена"
            
            # Обновляем подписку
            success = await update_subscription(message.from_user.id, months)
            suffix = "месяц" if months == 1 else "месяца" if months in (2,3,4) else "месяцев"
            if success:
                await message.answer(
                    f"✅ Оплата прошла успешно! Ваша подписка {action_type} на {months} {suffix}.\n\n"
                    "Спасибо за покупку! 🎉"
                )
                
                # Отправляем уведомление администраторам
                admin_message = (
                    f"{action_type.capitalize()} подписка пользователем "
                    f"`{user.full_name}` | `{user.telegram_id}` "
                    f"на {months} {suffix} - {final_price}₽"
                )
                
                for admin_id in config.ADMINS:
                    try:
                        await bot.send_message(admin_id, admin_message, parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"🛑 Failed to send notification to admin {admin_id}: {e}")
            else:
                await message.answer("❌ Ошибка при обновлении подписки")
    except Exception as e:
        logger.error(f"🛑 Successful payment processing error: {e}")
        await message.answer("❌ Ошибка при обработке платежа")

@router.callback_query(F.data == "renew_sub")
async def renew_subscription(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки для каждого варианта подписки
    for months in sorted(config.PRICES.keys()):
        price_info = config.PRICES[months]
        final_price = config.calculate_price(months)
        
        discount_text = ""
        if price_info["discount_percent"] > 0:
            discount_text = f" (-{price_info['discount_percent']}%)"
            
        button_text = f"{months} мес. - {final_price} руб.{discount_text}"
        builder.button(text=button_text, callback_data=f"pay_{months}")
    
    builder.button(text="⬅️ Назад", callback_data="back_to_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "💵 **Выберите период подписки:**",
        reply_markup=builder.as_markup(),
        parse_mode='Markdown'
    )