import logging, config
from datetime import datetime
from aiogram import Bot, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from Utils.check_sub_block import send_subscription, check_subscription
from db import get_user, user_in_ban_list

bot = Bot(token=config.API_TOKEN)
router = Router()

@router.callback_query(lambda c: c.data == 'earn')
async def earn(call: CallbackQuery):
    log_message = f"Заробити - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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

            ref_link = user[6]
            invited_count = user[7]

            earn_text = f"👇 <b>Запросіть своїх друзів</b>, використовуючи це посилання, і заробляйте нагороди:\n\n🔗 {ref_link}\n\n💶 За кожного запрошеного друга ви отримаєте <b>{config.REWARD} {config.CURRENCY}</b>\n\n👥 Ви запросили: {invited_count}"
            menu = InlineKeyboardButton(text="↩️ Меню", callback_data='menu')

            markup = InlineKeyboardMarkup(inline_keyboard=[[menu]])
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=earn_text, parse_mode='html', reply_markup=markup)
        else:
            await call.answer(config.BAN_MESSAGE, show_alert=True)
    else:
       await call.answer(config.BAN_MESSAGE, show_alert=True)
