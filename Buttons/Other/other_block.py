import logging, config
from datetime import datetime
from aiogram import Bot, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db import get_user

bot = Bot(token=config.API_TOKEN)
router = Router()

@router.callback_query(lambda c: c.data == 'other')
async def other(call: CallbackQuery):
    log_message = f"Інше - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)
    
    user = get_user(call.from_user.id)
    
    if user:
        buttons = ([[InlineKeyboardButton(text='💳 Виплати', url='https://t.me/+TcmBb5J-kik3NWY6')],
                [InlineKeyboardButton(text='👑 Відгуки', url='https://t.me/+_lRIodMbAiVmYWI6')],
                [InlineKeyboardButton(text='🛠 Тех. Підтримка', url=f'https://t.me/{config.ADMIN_USERNAME[1]}')],
                [InlineKeyboardButton(text='🌟 Донат', callback_data='donate')],
                [InlineKeyboardButton(text='↩️ Меню', callback_data='menu')]])

        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='⚙️ Інше:', reply_markup=markup)
    else:
       await call.answer(config.BAN_MESSAGE, show_alert=True)
