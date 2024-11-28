import logging, config
from datetime import datetime
from aiogram import Bot, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db import get_user, user_in_ban_list

bot = Bot(token=config.API_TOKEN)
router = Router()

@router.callback_query(lambda c: c.data == 'faq')
async def faq(call: CallbackQuery):
    log_message = f"FAQ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)
    
    user = get_user(call.from_user.id)
    user_ban = user_in_ban_list(call.from_user.id)

    if user:
        if not user_ban:
            faq_text = (
                "❓ <b>Часті питання:</b>\n\n"
                "1. <b>Чому довго немає оплати?</b>\n"
                "Виплати проходять кожного дня з 10:00 до 23:00 в порядку черги!")
            
            back_button = InlineKeyboardButton(text='↩️ Меню', callback_data='menu')
            markup = InlineKeyboardMarkup(inline_keyboard=[[back_button]])

            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=faq_text, parse_mode='html', reply_markup=markup)
        else:
            await call.answer(config.BAN_MESSAGE, show_alert=True)
    else:
       await call.answer(config.BAN_MESSAGE, show_alert=True)
