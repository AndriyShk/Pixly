import logging, config
from datetime import datetime
from aiogram import Bot, Router, types
from aiogram.types import CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F

bot = Bot(token=config.API_TOKEN)
router = Router()

class CardState(StatesGroup):
    waiting_for_number = State()

invoice_message_id = None

@router.callback_query(lambda c: c.data == 'donate')
async def donate(call: CallbackQuery):
    log_message = f"Донат - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)
    
    builder = InlineKeyboardBuilder()
    builder.button(text='⭐️ Надіслати 1 зірку', callback_data='send_star_1')
    builder.button(text='🌟 Надіслати 10 зірок', callback_data='send_star_10')
    builder.button(text='💫 Надіслати 100 зірок', callback_data='send_star_100')
    builder.button(text='✨ Вказати власну кількість', callback_data='send_custom_star')
    builder.button(text='↩️ Назад', callback_data='other')
    builder.adjust(1)
    
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text='🌟 Тут ви можете підтримати нашого бота донатом:',
        reply_markup=builder.as_markup())

async def donate_return(call: CallbackQuery):
    log_message = f"Повернуто на сторінку Донат - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)

    builder = InlineKeyboardBuilder()
    builder.button(text='⭐️ Надіслати 1 зірку', callback_data='send_star_1')
    builder.button(text='🌟 Надіслати 10 зірок', callback_data='send_star_10')
    builder.button(text='💫 Надіслати 100 зірок', callback_data='send_star_100')
    builder.button(text='✨ Вказати власну кількість', callback_data='send_custom_star')
    builder.button(text='↩️ Назад', callback_data='other')
    builder.adjust(1)

    await bot.send_message(
        chat_id=call.message.chat.id,
        text='🌟 Тут ви можете підтримати нашого бота донатом:',
        reply_markup=builder.as_markup())

@router.callback_query(lambda c: c.data.startswith('send_star_'))
async def send_star_invoice(call: CallbackQuery):
    if call.data == 'send_star_1':
        await call.message.delete()
        amount = 1
    elif call.data == 'send_star_10':
        await call.message.delete()
        amount = 10
    elif call.data == 'send_star_100':
        await call.message.delete()
        amount = 100
    else:
        return
    
    await send_custom_invoice(call, amount)

@router.callback_query(lambda c: c.data == 'send_custom_star')
async def send_custom_star(call: CallbackQuery, state: FSMContext):
    log_message = f"Надіслати send_custom_star - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)
    
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Скасувати', callback_data='cancel_payment')
    builder.adjust(1)

    sent_message = await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text='👇 Будь ласка, введіть власну суму:',
        reply_markup=builder.as_markup())
    
    await state.update_data(message_id=sent_message.message_id, call=call)
    await state.set_state(CardState.waiting_for_number)

@router.message(CardState.waiting_for_number)
async def card(message: types.Message, state: FSMContext):
    number = message.text.strip()

    data = await state.get_data()
    sent_message_id = data.get('message_id')

    if sent_message_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=sent_message_id)
        except Exception as e:
            logging.error(f"Помилка при видаленні попереднього повідомлення: {e}")

    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except Exception as e:
        logging.error(f"Помилка при видаленні поточного повідомлення: {e}")

    if not number.isdigit() or int(number) <= 0 or int(number) > 5000:
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Скасувати", callback_data='cancel_payment')
        builder.adjust(1)

        new_message = await bot.send_message(
            chat_id=message.chat.id,
            text="<b>⛔ Помилка введення!</b> Будь ласка, введіть ціле число!",
            parse_mode='html',
            reply_markup=builder.as_markup())
        
        await state.update_data(message_id=new_message.message_id)
        return

    call = data.get('call')
    if call:
        await send_custom_invoice(call=call, amount=int(number))
    await state.clear()
 
async def send_custom_invoice(call: CallbackQuery, amount: int):
    global invoice_message_id
    builder = InlineKeyboardBuilder() 
    builder.button(text=f"Оплатити {amount} зірок", pay=True)
    builder.button(text="❌ Скасувати покупку", callback_data="cancel_payment")
    builder.adjust(1)

    prices = [LabeledPrice(label="XTR", amount=amount)]

    invoice = await bot.send_invoice(
        chat_id=call.message.chat.id,
        title="Підтримка бота",
        description=f"Оплата {amount} зірок для підтримки бота.",
        payload=f"{amount}_stars",
        currency="XTR",
        prices=prices,
        reply_markup=builder.as_markup())
    invoice_message_id = invoice.message_id

@router.callback_query(lambda c: c.data == 'cancel_payment')
async def cancel_payment(call: CallbackQuery):
    await call.message.delete()
    await donate_return(call)

@router.pre_checkout_query(lambda query: True)
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: types.Message):
    global invoice_message_id

    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=invoice_message_id)
    except Exception as e:
        logging.error(f"Помилка при видаленні інвойсу: {e}")

    builder = InlineKeyboardBuilder()
    builder.button(text='↩️ Меню', callback_data='menu')
    builder.adjust(1)

    await message.answer("❤️ Дякуємо за підтримку!", reply_markup=builder.as_markup())
