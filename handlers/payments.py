from aiogram import Router, F
from aiogram.types import Message, PreCheckoutQuery, CallbackQuery, LabeledPrice, FSInputFile
from aiogram.fsm.context import FSMContext
from database.methods import update_balance, check_promo_code, use_promo_code, create_payment, has_used_any_promo, activate_promo_code
from config.config import config
from keyboards.inline import (
    get_start_keyboard, 
    get_payment_methods_keyboard, 
    get_back_to_menu_keyboard,
    get_profile_keyboard
)
from states.states import Form, PaymentStates
from aiogram.fsm.state import State, default_state
from utils.logger import log_user_action, log_error
from utils.misc import format_money

router = Router()

PAYMENT_METHODS = {
    "pay_sber": {
        "name": "Сбербанк",
        "number": "2202 2024 2222 2222"
    },
    "pay_tinkoff": {
        "name": "Тинькофф",
        "number": "5536 9137 9999 9999"
    },
    "pay_ozon": {
        "name": "OZON",
        "number": "2222 2222 2222 2222"
    }
}

MIN_AMOUNT = 50
MAX_AMOUNT = 50000

@router.callback_query(F.data == "card_payment")
async def process_card_payment(callback: CallbackQuery):
    if not callback.message or not callback.bot:
        return
        
    try:
        log_user_action(callback, "initiated card payment")
        await callback.bot.send_invoice(
            chat_id=callback.message.chat.id,
            title="Пополнение баланса",
            description="Пополнение баланса через платежную систему",
            payload="payment_balance",
            provider_token=config.PAYMENT_TOKEN,
            currency="RUB",
            prices=[
                LabeledPrice(label="Пополнение", amount=5000)
            ]
        )
    except Exception as e:
        log_error(e, "process_card_payment")
        await callback.message.answer(
            "Произошла ошибка при создании платежа. Попробуйте позже.",
            reply_markup=get_start_keyboard()
        )

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext):
    if not message.successful_payment or not message.from_user:
        return
        
    payment_amount = message.successful_payment.total_amount / 100
    bonus_amount = 0
    
    state_data = await state.get_data()
    active_promo = state_data.get('active_promo')
    
    if active_promo:
        if active_promo['is_percentage']:
            bonus_amount = payment_amount * (active_promo['amount'] / 100)
        else:
            bonus_amount = active_promo['amount']
        payment_amount += bonus_amount
        
        # Используем промокод
        await use_promo_code(message.from_user.id, active_promo['code'])

    # Сздаем запись о платеже
    await create_payment(message.from_user.id, payment_amount)
    
    # Обновляем баланс пользователя
    await update_balance(message.from_user.id, payment_amount)
    await state.clear()
    
    success_message = f"✅ Платеж на сумму {payment_amount} RUB успешно выполнен!"
    if bonus_amount > 0:
        success_message += f"\n💎 Бонус: {bonus_amount} RUB"
    
    await message.answer(
        success_message,
        reply_markup=get_start_keyboard()
    )

@router.callback_query(F.data == "replenish")
async def show_payment_methods(callback: CallbackQuery):
    if not callback.message or not callback.bot:
        return
        
    await callback.bot.edit_message_text(
        text="Выберите способ оплаты:",
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=get_payment_methods_keyboard()
    )

@router.callback_query(F.data.startswith("pay_"))
async def request_payment_amount(callback: CallbackQuery, state: FSMContext):
    if not callback.message or not callback.bot:
        return
        
    payment_method = callback.data
    await state.update_data(payment_method=payment_method)
    
    await callback.bot.edit_message_text(
        text=f"Введите сумму для пополнения баланса в RUB\n\n"
        f"💵 Минимальная сумма: {MIN_AMOUNT} RUB\n"
        f"💰 Максимальная сумма: {MAX_AMOUNT} RUB",
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=get_back_to_menu_keyboard()
    )
    await state.set_state(PaymentStates.waiting_for_amount)

@router.message(PaymentStates.waiting_for_amount)
async def process_payment_amount(message: Message, state: FSMContext):
    if not message.text:
        return
        
    try:
        amount = float(message.text.replace(",", "."))
        if amount < MIN_AMOUNT or amount > MAX_AMOUNT:
            await message.answer(
                f"❌ Сумма должна быть от {MIN_AMOUNT} до {MAX_AMOUNT} RUB",
                reply_markup=get_back_to_menu_keyboard()
            )
            return
            
        # Сохраняем сумму в состоянии
        await state.update_data(payment_amount=amount)
        
        # Проверяем активный промокод
        state_data = await state.get_data()
        active_promo = state_data.get('active_promo')
        
        if active_promo:
            # Рассчитываем бонус
            if active_promo['is_percentage']:
                bonus = amount * (active_promo['amount'] / 100)
                bonus_text = f"{active_promo['amount']}% ({bonus} RUB)"
            else:
                bonus = active_promo['amount']
                bonus_text = f"{bonus} RUB"
                
            total_amount = amount + bonus
            promo_info = f"\n🎁 Бонус по промокоду: {bonus_text}\n💎 Итого получите: {total_amount} RUB"
        else:
            promo_info = "\n💡 Подсказка: активируйте промокод в профиле для получения бонуса!"
            
        payment_method = state_data['payment_method']
        payment_info = PAYMENT_METHODS[payment_method]
        
        await message.answer(
            f"💳 Способ оплаты: {payment_info['name']}\n"
            f"♣️ Карта: {payment_info['number']}\n\n"
            f"🥳 Реквизиты верные, переспрашивать не нужно.\n\n"
            f"💰 Сумма к оплате: {amount} RUB"
            f"{promo_info}\n\n"
            f"После оплаты отправьте чек.",
            reply_markup=get_back_to_menu_keyboard()
        )
        await state.set_state(PaymentStates.waiting_for_receipt)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректную сумму",
            reply_markup=get_back_to_menu_keyboard()
        )

@router.message(PaymentStates.waiting_for_receipt, F.photo | F.document)
async def process_receipt(message: Message, state: FSMContext):
    if not message.bot or not message.from_user:
        return
        
    state_data = await state.get_data()
    amount = state_data['payment_amount']
    payment_method = state_data['payment_method']
    active_promo = state_data.get('active_promo')
    
    total_amount = amount  # Инициализируем значением без бонуса
    
    # Формируем сообщение для админа
    admin_message = (
        f"💰 Новый платеж\n"
        f"👤 От: @{message.from_user.username} ({message.from_user.id})\n"
        f"💵 Сумма: {amount} RUB\n"
        f"🏦 Метод: {PAYMENT_METHODS[payment_method]['name']}"
    )
    
    # Если есть активный промокод, проверяем можно ли его использовать
    if active_promo:
        # Проверяем, не использовал ли пользователь уже промокод
        if await has_used_any_promo(message.from_user.id):
            await message.answer("❌ Вы уже использовали промокод ранее!")
            await state.clear()
            return
            
        bonus_amount = (
            amount * (active_promo['amount'] / 100) 
            if active_promo['is_percentage'] 
            else active_promo['amount']
        )
        total_amount = amount + bonus_amount
        
        admin_message += (
            f"\n\n🎟 Активирован промокод: {active_promo['code']}\n"
            f"📊 Тип: {'Процент' if active_promo['is_percentage'] else 'Фиксированная сумма'}\n"
            f"💎 Бонус: {active_promo['amount']}{'%' if active_promo['is_percentage'] else ' RUB'}\n"
            f"💰 Итоговая сумма: {total_amount} RUB"
        )
    
    admin_message += (
        f"\n\nДля подтверждения: /approve {message.from_user.id} {total_amount}\n"
        f"Для отказа: /deny {message.from_user.id} {total_amount}"
    )
    
    # Отправляем чек и информацию администратору
    admin_id = 5349222597  # ID администратора для проверки платежей
    try:
        await message.forward(admin_id)
        await message.bot.send_message(admin_id, admin_message)
        
        await message.answer(
            "✅ Чек получен и отправлен на проверку!\n"
            "⏳ Ожидайте зачисления средств.",
            reply_markup=get_start_keyboard()
        )
    except Exception as e:
        await message.answer(
            "❌ Произошла ошибка при отправке чека. Попробуйте позже.",
            reply_markup=get_start_keyboard()
        )
        
    await state.clear()

@router.callback_query(F.data == "activate_promo")
async def activate_promo(callback: CallbackQuery, state: FSMContext):
    if not callback.message or not callback.bot:
        return
        
    # Очищаем предыдущий промокод
    await state.update_data(active_promo=None)
    
    await callback.bot.edit_message_text(
        text="Введите промокод:",
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=get_back_to_menu_keyboard()
    )
    await state.set_state(Form.waiting_for_promo)

@router.message(Form.waiting_for_promo)
async def process_promo(message: Message, state: FSMContext):
    if not message.text or not message.from_user:
        return
        
    promo_code = message.text.strip()  # Добавляем strip() для очистки от пробелов
    if not promo_code:  # Проверяем что промокод не пустой
        await message.answer(
            "❌ Введите корректный промокод",
            reply_markup=get_profile_keyboard(message.from_user.id)
        )
        return
        
    user_id = message.from_user.id
    
    # Активируем промокод
    bonus_amount = await activate_promo_code(user_id, promo_code)
    
    if bonus_amount:
        await message.answer(
            f"✅ Промокод успешно активирован!\n"
            f"💰 На ваш баланс начислено {bonus_amount} RUB",
            reply_markup=get_start_keyboard()
        )
    else:
        await message.answer(
            "❌ Промокод недействителен или уже был использован",
            reply_markup=get_profile_keyboard(user_id)
        ) 