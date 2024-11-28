import logging, config, asyncio, html
from datetime import datetime
from aiogram import Bot, Router, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from Buttons.Profile.profile_block import profile
from Utils.check_sub_block import send_subscription, check_subscription
from db import (get_user, user_in_ban_list, add_active_order, update_balance, not_paid_1, not_paid_2, get_user_active_order, check_active_order, move_order_to_payed, move_order_to_rejected, update_withdrawing, has_active_order)

bot = Bot(token=config.API_TOKEN)
router = Router()

class CardState(StatesGroup):
    waiting_for_amount = State()

@router.callback_query(lambda c: c.data == 'withdraw')
async def withdraw(call: CallbackQuery, state: FSMContext):
    log_message = f"Вивести - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)

    user = get_user(call.from_user.id)
    user_ban = user_in_ban_list(call.from_user.id)
    balance = user[4]
    card = user[9]
    
    if user:
        if not user_ban:
            if not await check_subscription(call.from_user.id):
                await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                await send_subscription(call.message.chat.id)
                return
            
            if has_active_order(call.from_user.id):
                markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='profile')]])
                sent_message = await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'❗️<b>У вас вже є відкритий ордер на виплату!</b>\n\nНе можна створити більше одного. Дочекайтеся виплати попереднього!', parse_mode='html', reply_markup=markup)
                await state.update_data(message_id=sent_message.message_id)
                return
            
            if not card:
                markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='profile')]])
                sent_message = await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'<b>❌ Карта не вказана!</b> Будь ласка, спочатку встановіть реквізити вашої карти.', parse_mode='html', reply_markup=markup)
                
                await state.update_data(message_id=sent_message.message_id)
                return

            if balance < config.MINIMUM_WITHDRAW:
                markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='profile')]])
                sent_message = await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'❗️<b>Мінімальний баланс для виведення становить {config.MINIMUM_WITHDRAW} {config.CURRENCY}.</b>\n\nУ вас недостатньо коштів.', parse_mode='html', reply_markup=markup)
                
                await state.update_data(message_id=sent_message.message_id)
                return

            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ Скасувати', callback_data='cancel_withdraw')]])
            sent_message = await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'👇 Будь ласка, введіть суму, яку ви хочете вивести:', reply_markup=markup)
            
            await state.update_data(message_id=sent_message.message_id)
            await state.set_state(CardState.waiting_for_amount)
        else:
            await call.answer(config.BAN_MESSAGE, show_alert=True)
    else:
       await call.answer(config.BAN_MESSAGE, show_alert=True)

@router.message(StateFilter(CardState.waiting_for_amount))
async def withdraw_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        user = get_user(message.from_user.id)
        balance = user[4]
        card = user[9]
        
        data = await state.get_data()
        previous_message_id = data.get('message_id')
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        
        if amount > balance:
            error_message = await message.answer(text=f'❗️ У вас недостатньо коштів для виведення! Ваш баланс: {balance} {config.CURRENCY}', parse_mode='html')
            await asyncio.sleep(5)
            await bot.delete_message(chat_id=error_message.chat.id, message_id=error_message.message_id)
            return
        
        if amount < config.MINIMUM_WITHDRAW:
            error_message = await message.answer(text=f'❗️ Сума повинна бути не менша {config.MINIMUM_WITHDRAW} {config.CURRENCY}', parse_mode='html')
            await asyncio.sleep(5)
            await bot.delete_message(chat_id=error_message.chat.id, message_id=error_message.message_id)
            return
        
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='✅ Підтвердити', callback_data=f'confirm_withdraw_{amount}')],
            [InlineKeyboardButton(text='❌ Скасувати', callback_data='cancel_button')]])

        sent_message = await bot.edit_message_text(chat_id=message.chat.id, message_id=previous_message_id, text=f'<b>⚙️ Заявка на виведення:</b>\n\n💶 Сума: {amount} {config.CURRENCY}\n💳 Карта: <code>{card}</code>', reply_markup=markup, parse_mode='html')
        await state.update_data(message_id=sent_message.message_id)
        await state.clear()

    except ValueError:
        user = get_user(message.from_user.id)
        error_message = await message.answer(text='<b>Упс... 🥲</b>\n\nБудь ласка, введіть дійсне число для суми виведення.', parse_mode='html')

        await asyncio.sleep(5)
        await bot.delete_message(chat_id=error_message.chat.id, message_id=error_message.message_id)
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

@router.callback_query(lambda c: c.data.startswith('cancel_button'))
async def cancel_button(call: CallbackQuery):
    log_message = f"Скасувати заявку - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)
    
    user = get_user(call.from_user.id)
    user_ban = user_in_ban_list(call.from_user.id)

    if user:
        if not user_ban:
            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='profile')]])
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='❌ Ваша заявка на виведення коштів була відхилена', reply_markup=markup)
        else:
            await call.answer(config.BAN_MESSAGE, show_alert=True)
    else:
       await call.answer(config.BAN_MESSAGE, show_alert=True)

@router.callback_query(lambda c: c.data.startswith('confirm_withdraw_'))
async def confirm_withdraw(call: CallbackQuery):
    log_message = f"Підтвердити заявку - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)

    user = get_user(call.from_user.id)
    user_ban = user_in_ban_list(call.from_user.id)
    
    user_id = user[0]
    first_name = html.escape(user[2])
    amount = int(call.data.split('_')[2])
    card = user[9]
    
    if user:
        if not user_ban:
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            active_order = check_active_order(call.from_user.id)
        
            if active_order:
                await call.answer("❗️ У вас вже є активний запит на виведення коштів. Дочекайтеся його обробки.", show_alert=True)
                return
            add_active_order(call.from_user.id, amount, card, "⌛️ обробляється...", created_at)

            admin_text = (f"<b>👤 Користувач:</b> {first_name}\n"
                          f"<b>🆔 ID:</b> <code>{user_id}</code>\n"
                          f"<b>💶 Сума:</b> {amount} {config.CURRENCY}\n"
                          f"<b>💳 Карта:</b> <code>{card}</code>")
            
            confirm_button = InlineKeyboardButton(text='✅ Оплачено', callback_data=f'paid_{user[0]}_{amount}')
            reject_button = InlineKeyboardButton(text='❌ Відмінити', callback_data=f'not_paid_{user[0]}_{amount}')
            
            markup = InlineKeyboardMarkup(inline_keyboard=[[confirm_button],[reject_button]])
            await bot.send_message(chat_id=config.PAYOUTS_CHANNEL_ID, text=admin_text, parse_mode='html', reply_markup=markup)
            
            confirmation_text = (
                f"<b>⚙️Ваш запит на виведення коштів:</b>\n\n"
                f"<b>💶 Сума:</b> {amount} {config.CURRENCY}\n"
                f"<b>💳 Карта:</b> <code>{card}</code>\n\n"
                f"❗️Надіслано адміністратору для затвердження")

            update_balance(call.from_user.id, amount)

            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='profile')]])
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='html', text=confirmation_text, reply_markup=markup)
        else:
            await call.answer(config.BAN_MESSAGE, show_alert=True)
    else:
        await call.answer(config.BAN_MESSAGE, show_alert=True)

@router.callback_query(lambda c: c.data.startswith('cancel_withdraw'))
async def cancel_withdraw(call: CallbackQuery):
    await profile(call)

@router.callback_query(lambda c: c.data.startswith('paid_') and len(c.data.split('_')) == 3)
async def paid(call: CallbackQuery):
    log_message = f"Підтверджено в оплаті - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)
    
    data = call.data.split('_')
    user_id = int(data[1])
    amount = int(data[2])
    
    try:
        order = get_user_active_order(user_id)
        if order:
            user_data = get_user(user_id)
            
            move_order_to_payed(user_id, order)

            first_name = user_data[2]
            update_withdrawing(amount, user_id)

            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⏺ Закрити', callback_data='close_button')]])
            await bot.send_message(chat_id=user_id, text=f'<b>✅ Ваше виведення коштів успішно оброблено!</b>\n\n🎯 Залиште відгук, будь ласка: {config.ADMIN_USERNAME[0]}', parse_mode='html', reply_markup=markup)
        
            channel_confirmation_text = (f"✅ Виплата виконана:\n\n"
                                    f"👤 <b>Користувач:</b> {html.escape(first_name)}\n"
                                    f"💸 <b>Сума:</b> {amount} {config.CURRENCY}\n")

            await bot.send_message(chat_id=config.CHAT_WITHDRAW, text=channel_confirmation_text, parse_mode='html')
            await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            print("Ордер не знайдено")
    except Exception as e:
        print("Помилка з оплатою ордера:", repr(e))

@router.callback_query(lambda c: c.data.startswith('not_paid_'))
async def not_paid(call: CallbackQuery):
    log_message = f"Відхилено в оплаті - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)
    
    data = call.data.split('_')
    user_id = data[2]
    amount = int(data[3])

    try:
        order = get_user_active_order(user_id)
        if order:
            user_balance = not_paid_1(user_id)
            if user_balance:
                move_order_to_rejected(user_id, order)
                not_paid_2(user_balance, amount, user_id)
            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⏺ Закрити', callback_data='close_button')]])
            await bot.send_message(chat_id=user_id, text=f'<b>❌ Ваш вивід не виконано!</b>\n\nБудь ласка, перевірте правильність даних!', parse_mode='html', reply_markup=markup)
            await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        
        else:
            print("Ордер не знайдено")
    except Exception as e:
        print("Помилка з відхиленням ордера:", repr(e))
