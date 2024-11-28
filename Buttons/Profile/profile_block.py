import logging, config
from datetime import datetime
from aiogram import Bot, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from Utils.check_sub_block import send_subscription, check_subscription
from db import get_user, user_in_ban_list
import html

bot = Bot(token=config.API_TOKEN)
router = Router()

@router.callback_query(lambda c: c.data == 'profile')
async def profile(call: CallbackQuery):
    log_message = f"Профіль - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)
    
    user = get_user(call.from_user.id)
    user_ban = user_in_ban_list(call.from_user.id)

    if user:
        if not user_ban:
            if not await check_subscription(call.from_user.id):
                await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                await send_subscription(call.message.chat.id)
                return
            
            id = user[0]
            first_name = html.escape(user[2])
            balance = user[4]
            withdrawing = user[5]
            invited = user[7]

            profile_text = (f"👤 <b>Профіль:</b>\n\n"
                            f"🆔 <b>ID:</b> {id}\n"
                            f"👤 <b>Ім'я:</b> {first_name}\n"
                            f"👫 <b>Запрошено друзів:</b> {invited}\n"
                            f"==================\n"
                            f"💶 <b>Баланс:</b> {balance} {config.CURRENCY}\n"
                            f"🏦 <b>Виведено:</b> {withdrawing} {config.CURRENCY}")

            keyboard = [
                [InlineKeyboardButton(text=f"💶 Вивести {config.CURRENCY}", callback_data='withdraw')],
                [InlineKeyboardButton(text="📋 Мої ордери", callback_data='my_orders')],
                [InlineKeyboardButton(text="↩️ Меню", callback_data='menu')]]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=profile_text, parse_mode='html', reply_markup=markup)
        else:
            await call.answer(config.BAN_MESSAGE, show_alert=True)
    else:
        await call.answer(config.BAN_MESSAGE, show_alert=True)
