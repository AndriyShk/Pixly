import logging, config
from datetime import datetime
from aiogram import Bot, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from db import get_user, user_in_ban_list

bot = Bot(token=config.API_TOKEN)
router = Router()

@router.callback_query(lambda c: c.data == 'trustee')
async def trustee(call: CallbackQuery):
    log_message = f"Trustee - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)
    
    user = get_user(call.from_user.id)
    user_ban = user_in_ban_list(call.from_user.id)

    if user:
        if not user_ban:
            video = FSInputFile(path='E:/Програмування/Telegram/MonoE/Buttons/Trustee/video/Trustee.MP4', filename='trustee.mp4')
            caption = '<b>⚡️ Нарешті. Українцям дозволили розраховуватись криптовалютою через Google Pay/Apple Pay</b>\n\nМожливості карти від Trustee:\n\n▪️Купівля крипти і виведення одразу на звичайну карту.\n▪️Зняття крипти в банкоматі.\n▪️5000€ денний ліміт (включаючи витрати за кордоном).\n▪️Верифікація через «Дію».\n▪️Відсутність фінмоніторингу.\n\n▪️Картою через Google Pay/Apple Pay можливо розраховуватися як в Україні, так і за кордоном. \n\n<i>Посилання на додаток: https://trusteeglobal.com/?refferals=8jBMqvCfUBbx</i>\n\n<b>Користуйтесь, це швидко, безпечно та зручно 😉</b>'
        
            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬇️ Завантажити додаток', url='https://trusteeglobal.com/?refferals=8jBMqvCfUBb')],[InlineKeyboardButton(text='↩️ Меню', callback_data='menu_trustee')]])
            
            await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            await bot.send_video(chat_id=call.message.chat.id, video=video, caption=caption, parse_mode='html', reply_markup=markup)
        else:
            await call.answer(config.BAN_MESSAGE, show_alert=True)
    else:
        await call.answer(config.BAN_MESSAGE, show_alert=True)

@router.callback_query(lambda c: c.data == 'menu_trustee')
async def menu_trustee(call: CallbackQuery):
    user = get_user(call.from_user.id)
    if user:
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        keyboard = [
            [InlineKeyboardButton(text='💶 Заробити', callback_data='earn'), InlineKeyboardButton(text='👤 Профіль', callback_data='profile')],
            [InlineKeyboardButton(text='⚙️ Інше', callback_data='other'), InlineKeyboardButton(text='💳 Карта', callback_data='card')],
            [InlineKeyboardButton(text='📊 Статистика', callback_data='statistics'), InlineKeyboardButton(text='❓ FAQ', callback_data='faq')],
            [InlineKeyboardButton(text='🏆 Таблиця Лідерів', callback_data='leaderboard')],
            [InlineKeyboardButton(text='👑 Trustee Plus', callback_data='trustee')]]
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await bot.send_message(chat_id=call.message.chat.id, text='🏠 Головне Меню:', reply_markup=markup)
    else:
        await call.message.answer(config.BAN_MESSAGE)


