import logging, asyncio, html, config, random
from aiogram.fsm.context import FSMContext
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram import F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from Buttons.Earn import earn_block
from Buttons.Profile import profile_block
from Buttons.Profile.Withdraw import withdraw_block
from Buttons.Profile.Orders import my_orders_block
from Buttons.Card import card_block
from Buttons.Stats import stats_block
from Buttons.Other import other_block
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from Buttons.Other.Donate import donate_block
from Buttons.Leaderboard import leaderboard_block
from Buttons.FAQ import faq_block
from Buttons.Trustee import trustee_block
from Admin import admin_panel
from Utils import check_sub_block
from Utils.check_sub_block import send_subscription, send_main_menu, check_subscription
from db import (create_db, user_exists, add_user, update_balance_and_invited, check_bonus_given, 
                mark_bonus_given, add_to_ban_list, user_in_ban_list, update_invited_by)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

session = AiohttpSession()
bot = Bot(token=config.API_TOKEN, session=session)
dp = Dispatcher()
create_db()

class UserStates(StatesGroup):
    awaiting_captcha = State()
    awaiting_phone = State()

@dp.message(Command('start'))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    referrer_id = None

    if len(message.text.split()) > 1:
        referrer_id = message.text.split()[1]
        if referrer_id == str(user_id):
            referrer_id = None

    if user_in_ban_list(user_id):
        await message.answer(config.BAN_MESSAGE)
        return

    if not user_exists(user_id):
        await send_captcha(message, state)
        await state.set_state(UserStates.awaiting_captcha)
        await state.update_data(referrer_id=referrer_id)
        return

    if await check_subscription(message.chat.id):
        await send_main_menu(message, message.chat.id)
    else:
        await send_subscription(message.chat.id)

async def send_captcha(message: Message, state: FSMContext):
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    captcha_result = num1 + num2

    options = [captcha_result, captcha_result + random.randint(1, 5), captcha_result - random.randint(1, 5)]
    random.shuffle(options)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(option), callback_data=f"captcha_{option}") for option in options]])

    await message.bot.send_message(
        chat_id=message.chat.id,
        text=f"🛡 Для підтвердження, що ви не бот, розв'яжіть приклад: {num1} + {num2} = ?",
        reply_markup=keyboard)

    await state.update_data(captcha_result=captcha_result)

@dp.callback_query(lambda c: c.data.startswith('captcha_'))
async def captcha(call: CallbackQuery, state: FSMContext):
    user_answer = int(call.data.split('_')[1])
    data = await state.get_data()
    captcha_result = data.get('captcha_result')

    if user_answer == captcha_result:
        await call.message.delete()
        await state.update_data(captcha_result=None)

        phone_button = KeyboardButton(text="📱 Надати номер телефону", request_contact=True)
        markup = ReplyKeyboardMarkup(keyboard=[[phone_button]], resize_keyboard=True, one_time_keyboard=True)
        sent_message = await call.message.answer("👇Щоб продовжити, будь ласка, надайте ваш номер телефону:", reply_markup=markup)
        await state.update_data(start_message_id=sent_message.message_id)
    else:
        await call.answer("❌ Неправильна відповідь, спробуйте ще раз.", show_alert=True)
        await call.message.delete()
        await bot.send_message(chat_id=config.LOGS, text=f"❌ Неправильна капча")
        await send_captcha(call.message, state)

@dp.message(F.contact)
async def contact(message: types.Message, state: FSMContext):
    phone_number = message.contact.phone_number
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    ref_link = f"https://t.me/{config.BOT_USERNAME}?start={user_id}"
    premium = message.from_user.is_premium

    data = await state.get_data()
    start_message_id = data.get("start_message_id")
    referrer_id = data.get("referrer_id")

    phone_number = phone_number.replace(" ", "").replace("+", "")
    if not phone_number.startswith("380"):
        if not user_in_ban_list(user_id):
            add_to_ban_list(user_id, username, first_name, last_name, phone_number)
        await message.answer("⛔ Ви заблоковані через номер телефону.\n\n⚙️ Пітримуються тільки українські номера!")
        await bot.send_message(chat_id=config.LOGS, text=f"⛔ Заблоковано номер: {phone_number}")
        return
    
    if not user_exists(user_id):
        add_user(user_id, username, first_name, last_name, ref_link, phone_number, premium)
        
        text = f"ID: <code>{html.escape(str(user_id))}</code>\n"
        if username:
            escaped_username = html.escape(username)
            text += f'Юзер: @{escaped_username}\n'
        if first_name:
            text += f'Ім\'я: {html.escape(first_name)}\n'
        if last_name:
            text += f'Прізвище: {html.escape(last_name)}\n'
        if phone_number:
            text += f'Номер: {phone_number}\n'
        if referrer_id:
            text += f'Запрошений користувачем: <code>{referrer_id}</code>\n'
        if premium:
            text += f'Преміум: {premium}\n'
    
        await bot.send_message(chat_id=config.CHAT_USER_LOGS, text=text, parse_mode='html')

        if referrer_id and user_exists(referrer_id):
            update_invited_by(user_id, referrer_id)
            if not check_bonus_given(referrer_id):
                update_balance_and_invited(referrer_id, config.REWARD, 1)
                mark_bonus_given(referrer_id, user_id)

                invited_name = first_name if first_name else " "
                markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⏺ Закрити', callback_data='close_button')]])
                await bot.send_message(chat_id=referrer_id, text=f'🎉 Ви отримали <b>{config.REWARD} {config.CURRENCY}</b> за запрошення користувача <b>{invited_name}</b>!', parse_mode='html', reply_markup=markup)

    if start_message_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=start_message_id)
        except Exception as e:
            print(f"Повідомлення з ID {start_message_id} вже не знайдено або видалено.")
    else:
        print("start_message_id відсутній у стані.")

    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except Exception as e:
        print(f"Повідомлення {message.message_id} вже видалене.")
        
    if await check_subscription(user_id):
        await send_main_menu(message, message.chat.id)
    else:
        await send_subscription(message.chat.id)

async def main():
    try:
        dp.include_routers(
            earn_block.router, profile_block.router, card_block.router,
            stats_block.router, other_block.router, my_orders_block.router,
            leaderboard_block.router, withdraw_block.router, donate_block.router,
            faq_block.router, trustee_block.router, admin_panel.router, check_sub_block.router)
        
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот був зупинений.")
    except Exception as e:
        logging.error(f"Помилка під час роботи бота: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Програму зупинено вручну.")

