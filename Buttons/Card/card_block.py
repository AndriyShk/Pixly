import logging, config
from datetime import datetime
from aiogram import Bot, Router, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from db import get_user, user_in_ban_list, setting_card 

bot = Bot(token=config.API_TOKEN)
router = Router()

class CardState(StatesGroup):
    waiting_for_card = State()

@router.callback_query(lambda c: c.data == 'card')
async def card(call: CallbackQuery):
    log_message = f"Карта - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)
    
    user = get_user(call.from_user.id)
    user_ban = user_in_ban_list(call.from_user.id)
    
    if user:
        if not user_ban:
            card = user[9]
            card_text = f"🔐 <b>Ваша поточна карта:</b>\n\n<code>{card if card else 'Не встановлена'}</code>\n\n❓ Бажаєте встановити або змінити карту?"

            keyboard = [
                [InlineKeyboardButton(text="💳 Встановити/Змінити Карту", callback_data='set_card')],
                [InlineKeyboardButton(text="↩️ Меню", callback_data='menu')]]
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=card_text, parse_mode='html', reply_markup=markup)
        else:
            await call.answer(config.BAN_MESSAGE, show_alert=True)
    else:
       await call.answer(config.BAN_MESSAGE, show_alert=True)

@router.callback_query(lambda c: c.data == 'set_card')
async def set_card(call: CallbackQuery, state: FSMContext):
    log_message = f"Встановити карту - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)

    user = get_user(call.from_user.id)
    user_ban = user_in_ban_list(call.from_user.id)
    
    if user:
        if not user_ban:
            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ Скасувати', callback_data='cancel_set_card')]])
            sent_message = await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text='👇 Будь ласка, введіть реквізити вашої карти:',
                reply_markup=markup)
            
            await state.update_data(message_id=sent_message.message_id)
            await state.set_state(CardState.waiting_for_card)
        else:
            await call.answer(config.BAN_MESSAGE, show_alert=True)
    else:
       await call.answer(config.BAN_MESSAGE, show_alert=True)

@router.message(CardState.waiting_for_card)
async def card(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    new_card = message.text.strip()

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

    if len(new_card) != 16 or not new_card.isdigit():
        try:
            new_message = await bot.send_message(
                chat_id=message.chat.id,
                text="<b>⛔ Неправильний формат картки!</b> Будь ласка, введіть 16-значну картку без пробілів:",
                parse_mode='html',
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="❌ Скасувати", callback_data='cancel_set_card')]]
                )
            )
            await state.update_data(message_id=new_message.message_id)
        except Exception as e:
            logging.error(f"Помилка при надсиланні повідомлення про помилку: {e}")
        return

    setting_card(new_card, user_id)
   
    menu_button = InlineKeyboardButton(text="↩️ Меню", callback_data='card')
    markup = InlineKeyboardMarkup(inline_keyboard=[[menu_button]])

    await bot.send_message(
        chat_id=message.chat.id,
        text=f'💳 Ваша карта оновлена на: <code>{new_card}</code>',
        parse_mode='html',
        reply_markup=markup)
    await state.clear()

@router.callback_query(lambda c: c.data.startswith('cancel_set_card'))
async def cancel_set_card(call: CallbackQuery, state: FSMContext):
    log_message = f"Скасувати встановлення карти - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)
    
    user_id = call.from_user.id
    data = await state.get_data()
    sent_message_id = data.get('message_id')

    if sent_message_id:
        try:
            await bot.delete_message(chat_id=call.message.chat.id, message_id=sent_message_id)
        except Exception as e:
            logging.error(f"Error deleting message: {e}")

    await bot.send_message(
        chat_id=user_id,
        text="❌ Встановлення карти було відхилено!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ Назад", callback_data='card')]]))

    await state.clear()
