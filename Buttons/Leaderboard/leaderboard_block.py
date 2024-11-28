import logging, config
from datetime import datetime
from aiogram import Bot, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db import get_user, user_in_ban_list, get_leaders 
import html

bot = Bot(token=config.API_TOKEN)
router = Router()

@router.callback_query(lambda c: c.data == 'leaderboard')
async def show_leaderboard(call: CallbackQuery):
    log_message = f"Таблиця Лідерів - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)

    user = get_user(call.from_user.id)
    user_ban = user_in_ban_list(call.from_user.id)
    leaderboard = get_leaders()
    
    if user:
        if not user_ban:
            if not leaderboard:
                leaderboard_text = "📊 Немає даних для таблиці лідерів."
            else:
                invite_text = 'запрошень'
                leaderboard_text = ""
                for i, (first_name, invited) in enumerate(leaderboard, 1):
                    leaderboard_text += f"{i}. {html.escape(first_name)} - {invited} {invite_text}\n"
                leaderboard_text = f"🏆 <b>Таблиця лідерів</b> 🏆\n\n{leaderboard_text}"

            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Меню', callback_data='menu')]])
            
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=leaderboard_text, parse_mode='html', reply_markup=markup)
        else:
            await call.answer(config.BAN_MESSAGE, show_alert=True)
    else:
       await call.answer(config.BAN_MESSAGE, show_alert=True)
