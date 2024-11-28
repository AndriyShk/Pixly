import logging, config
from datetime import datetime
from aiogram import Bot, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from db import get_user, user_in_ban_list, get_total_users, get_total_payed

bot = Bot(token=config.API_TOKEN)
router = Router()

class CardState(StatesGroup):
    waiting_for_amount = State()

@router.callback_query(lambda c: c.data == 'statistics')
async def statistics(call: CallbackQuery):
    log_message = f"Статистика - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)
    
    total_users = get_total_users()
    total_payed = get_total_payed()
    user = get_user(call.from_user.id)
    user_ban = user_in_ban_list(call.from_user.id)

    if user:
        if not user_ban:
            stats_text = (f"📊 <b>Статистика:</b>\n\n"
                        f"👥 Всього користувачів: {total_users}\n"
                        f"💸 Всього виплачено: {total_payed} {config.CURRENCY}")
        
            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Меню', callback_data='menu')]])
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=stats_text, parse_mode='html', reply_markup=markup)
        else:
            await call.answer(config.BAN_MESSAGE, show_alert=True)
    else:
       await call.answer(config.BAN_MESSAGE, show_alert=True)
