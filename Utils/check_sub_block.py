import logging, config
from aiogram import Bot, Router, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db import get_user

bot = Bot(token=config.API_TOKEN)
router = Router()

async def send_subscription(chat_id):
    try:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=channel['name'], url=f"{channel['link']}")]
                for channel in config.CHANNELS] + [[InlineKeyboardButton(text="✅ Готово", callback_data='sub_done')]])

        await bot.send_message(
            chat_id=chat_id,
            text="❗️<b>Щоб отримати доступ до функцій бота</b>, підпишіться на канали нижче:",
            parse_mode='html',
            reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Помилка надсилання підписки: {e}")
    
async def check_subscription(user_id):
    try:
        for channel in config.CHANNELS:
            member = await bot.get_chat_member(chat_id=f"@{channel['username']}", user_id=user_id)
            if member.status not in ['creator', 'administrator', 'member']:
                return False
        return True
    except Exception as e:
        logging.error(f"Помилка перевірки підписки: {e}")
        return False

async def update_message(message_id, chat_id, new_text, new_markup):
    try:
        current_message = await bot.get_message(chat_id, message_id)
        
        if current_message.text != new_text or current_message.reply_markup != new_markup:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_text, reply_markup=new_markup, parse_mode='html')
        else:
            print("АПДЕЙТ МЕСДЖ")
    except Exception as e:
        print(f"Помилка оновлення смс: {repr(e)}")

async def send_main_menu(message: types.Message, chat_id):
    user = get_user(chat_id)
    if user:
        keyboard = [
            [InlineKeyboardButton(text='💶 Заробити', callback_data='earn'), InlineKeyboardButton(text='👤 Профіль', callback_data='profile')],
            [InlineKeyboardButton(text='⚙️ Інше', callback_data='other'), InlineKeyboardButton(text='💳 Карта', callback_data='card')],
            [InlineKeyboardButton(text='📊 Статистика', callback_data='statistics'), InlineKeyboardButton(text='❓ FAQ', callback_data='faq')],
            [InlineKeyboardButton(text='🏆 Таблиця Лідерів', callback_data='leaderboard')],
            [InlineKeyboardButton(text='👑 Trustee Plus', callback_data='trustee')]]
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await bot.send_message(chat_id, text='🏠 Головне Меню:', reply_markup=markup)
    else:
        await message.answer(config.BAN_MESSAGE)

@router.callback_query(lambda c: c.data == 'menu')
async def back_to_menu(call: CallbackQuery):
    user = get_user(call.from_user.id)
    if user:
        keyboard = [
            [InlineKeyboardButton(text='💶 Заробити', callback_data='earn'), InlineKeyboardButton(text='👤 Профіль', callback_data='profile')],
            [InlineKeyboardButton(text='⚙️ Інше', callback_data='other'), InlineKeyboardButton(text='💳 Карта', callback_data='card')],
            [InlineKeyboardButton(text='📊 Статистика', callback_data='statistics'), InlineKeyboardButton(text='❓ FAQ', callback_data='faq')],
            [InlineKeyboardButton(text='🏆 Таблиця Лідерів', callback_data='leaderboard')],
            [InlineKeyboardButton(text='👑 Trustee Plus', callback_data='trustee')]]
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='🏠 Головне Меню:', reply_markup=markup)
    else:
        await call.message.answer(config.BAN_MESSAGE)

@router.callback_query(lambda c: c.data == 'sub_done')
async def sub_done(call: CallbackQuery):
    if await check_subscription(call.from_user.id):
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        await send_main_menu(call.message, call.message.chat.id)
    else:
        await call.answer("😭Здається, ви не підписалися!", show_alert=True)

@router.callback_query(lambda c: c.data == 'close_button')
async def close_button(call: CallbackQuery):
    try:
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    except Exception:
        print(f"Помилка видалення смс з кнопкою '⏺ Закрити'")
