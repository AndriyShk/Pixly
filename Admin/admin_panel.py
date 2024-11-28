import logging, sqlite3, config, html, importlib, json
from aiogram import Bot, Router, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from db import search_user, delete_user, get_user_active_order, get_user_payed_orders, get_user_rejected_orders, is_user_banned

bot = Bot(token=config.API_TOKEN)
router = Router()

class Form(StatesGroup):
    search_user = State()

class Config(StatesGroup):
    change_channels_to_subscribe = State()
    change_minimum_withdraw = State()
    change_bonus = State()

def load_config():
    importlib.reload(config)
    return config

def save_config():
    with open('config.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    with open('config.py', 'w', encoding='utf-8') as f:
        for line in lines:
            if line.startswith("CHANNELS"):
                f.write(f"CHANNELS = {repr(config.CHANNELS)}\n")
            elif line.startswith("REWARD"):
                f.write(f"REWARD = {config.REWARD}\n")
            elif line.startswith("MINIMUM_WITHDRAW"):
                f.write(f"MINIMUM_WITHDRAW = {config.MINIMUM_WITHDRAW}\n")
            else:
                f.write(line)

pending_broadcast = {}

@router.message(Command('adm'))
async def admin_panel(message: types.Message):
    if message.from_user.id not in config.ADMIN_ID:
        return
    
    buttons = [[InlineKeyboardButton(text="🔍 Пошук користувача", callback_data="search_user")],
               [InlineKeyboardButton(text="📊 Статистика", callback_data="stata")],
               [InlineKeyboardButton(text="⚙️ Конфіг", callback_data="config")],
               [InlineKeyboardButton(text="❌ Скасувати", callback_data='cancel')]]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.send_message(chat_id=message.chat.id, text="🔧 Адмін панель:", reply_markup=keyboard)

@router.callback_query(lambda call: call.data == "admin_menu")
async def admin_menu(call: types.CallbackQuery):
    if call.from_user.id not in config.ADMIN_ID:
        return
    
    buttons = [[InlineKeyboardButton(text="🔍 Пошук користувача", callback_data="search_user")],
               [InlineKeyboardButton(text="📊 Статистика", callback_data="stata")],
               [InlineKeyboardButton(text="⚙️ Конфіг", callback_data="config")],
               [InlineKeyboardButton(text="❌ Скасувати", callback_data='cancel')]]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)
    await call.message.edit_text(text="🔧 Адмін панель:", reply_markup=keyboard)

@router.callback_query(lambda call: call.data == "search_user")
async def search_user_prompt(call: types.CallbackQuery, state: FSMContext):
    global msg
    
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='admin_menu')]])
    msg = await call.message.edit_text(text='🔍 Введіть ID користувача для пошуку:', parse_mode='html', reply_markup=markup)
    
    await state.set_state(Form.search_user)

@router.message(StateFilter(Form.search_user))
async def search_user_handler(message: types.Message, state: FSMContext):
    user_id = message.text.strip()
    
    if is_user_banned(user_id):
        await bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        await bot.send_message(
            chat_id=message.chat.id,
            text="<b>❌ Користувач заблокований</b> і не може бути переглянутий.",
            parse_mode='html',
            reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='admin_menu')]]))
        return

    user = search_user(user_id)

    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    
    if user:
        await state.update_data(user=user)
        username = user[1] if user[1] is not None else "Немає"
        first_name = html.escape(user[2]) if user[2] is not None else "Немає"
        last_name = html.escape(user[3]) if user[3] is not None else "Немає"
        balance = user[4]
        withdrawn = user[5]
        invited = user[7]
        phone = user[8]
        card = user[9]
        invited_by = user[10]
        premium = user[11]

        text = (
            f'<b>🧑‍💼 Інформація про користувача:</b>\n\n'
            f'<b>🆔 ID</b>: <code>{user[0]}</code>\n'
            f'<b>🪪 Username</b>: @{username}\n'
            f'<b>👤 Ім\'я</b>: {first_name} {last_name}\n'
            f'<b>💶 Баланс</b>: {balance}\n'
            f'<b>🏦 Виведено</b>: {withdrawn}\n'
            f'<b>👫 Запрошено</b>: {invited}\n'
            f'<b>📱 Номер</b>: +{phone}\n'
            f'<b>💳 Карта</b>: {card or 'Немає'}\n'
            f'<b>🔗 Був(ла) запрошена</b>: {invited_by or 'Немає'}\n'
            f'<b>👑 Преміум</b>: {premium or 'Немає'}\n')
        
        buttons = [[InlineKeyboardButton(text="👫 Реферали користувача", callback_data="referrals_user")],
                   [InlineKeyboardButton(text="⛔️ Заблокувати користувача", callback_data="ban_user")],
                   [InlineKeyboardButton(text="📋 Ордери користувача", callback_data='orders_user')],
                   [InlineKeyboardButton(text='↩️ Назад', callback_data='admin_menu')]]
        
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        await bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)
        await bot.send_message(chat_id=message.chat.id, text=text, parse_mode='html', reply_markup=markup)
    else:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

ITEMS_PER_PAGE = 1

@router.callback_query(lambda call: call.data == "referrals_user")
async def referrals_user(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = data.get("user")
    referrer_id = user[0] if user else None

    if not referrer_id:
        await call.message.edit_text(
            text="❗️ Користувач не знайдений.",
            parse_mode='html',
            reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_user_info')]]))
        return

    connection = sqlite3.connect(config.DB)
    cursor = connection.cursor()

    cursor.execute("SELECT user_id FROM referral_bonuses WHERE referrer_id = ?", (referrer_id,))
    referral_ids = [row[0] for row in cursor.fetchall()]

    if not referral_ids:
        await call.message.edit_text(
            text="<b>👫 У користувача немає рефералів.</b>",
            parse_mode="html",
            reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_user_info")]]))
        connection.close()
        return

    await state.update_data(referral_ids=referral_ids, current_page=0)
    await state.update_data(message_id=call.message.message_id)
    await display_referrals_page(call.message, referral_ids, cursor, 0, state)

    connection.close()

async def display_referrals_page(message, referral_ids, cursor, page, state):
    start_index = page * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    current_referrals = referral_ids[start_index:end_index]

    referrals_text = "<b>👫 Реферали користувача:</b>\n\n"
    for i, referral_id in enumerate(current_referrals, start=1 + start_index):
        cursor.execute("SELECT user_id, first_name, last_name, username, balance, withdrawing, invited, phone_number, card, invited_by, premium FROM users WHERE user_id = ?", (referral_id,))
        user = cursor.fetchone()

        if user:
            user_id, first_name, last_name, username, balance, withdrawing, invited, phone_number, card, invited_by, premium = user

            escaped_first_name = html.escape(first_name or 'Немає')
            escaped_last_name = html.escape(last_name or '')

            referrals_text += (
                f'<b>🆔 ID</b>: <code>{user_id}</code>\n'
                f'<b>🪪 Username</b>: @{username}\n'
                f'<b>👤 Ім\'я</b>: {escaped_first_name} {escaped_last_name}\n'
                f'<b>💶 Баланс</b>: {balance}\n'
                f'<b>🏦 Виведено</b>: {withdrawing}\n'
                f'<b>👫 Запрошено</b>: {invited}\n'
                f'<b>📱 Номер</b>: +{phone_number}\n'
                f'<b>💳 Карта</b>: {card or 'Немає'}\n'
                f'<b>🔗 Був(ла) запрошена</b>: <code>{invited_by or 'Немає'}</code>\n'
                f'<b>👑 Преміум</b>: {premium or 'Немає'}\n')

    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"referrals_page:{page-1}"))
    if end_index < len(referral_ids):
        buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"referrals_page:{page+1}"))
    buttons.append(InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_user_info"))

    markup = InlineKeyboardMarkup(inline_keyboard=[buttons])

    # Оновлюємо message
    message_id = (await state.get_data()).get("message_id")

    await bot.edit_message_text(
        text=referrals_text, 
        parse_mode="html", 
        chat_id=message.chat.id, 
        message_id=message_id, 
        reply_markup=markup
    )

@router.callback_query(lambda call: call.data.startswith("referrals_page:"))
async def referrals_page_callback(call: types.CallbackQuery, state: FSMContext):
    page = int(call.data.split(":")[1])
    data = await state.get_data()
    referral_ids = data.get("referral_ids")

    if referral_ids is None:
        return
    
    connection = sqlite3.connect(config.DB)
    cursor = connection.cursor()

    await display_referrals_page(call.message, referral_ids, cursor, page, state)

    connection.close()

@router.callback_query(lambda call: call.data == "ban_user")
async def ban_user(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('user')

    if isinstance(user_id, tuple):
        user_id = user_id[0]
    
    print(user_id)
    
    delete_user(user_id)

    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='admin_menu')]])
    await call.message.edit_text(text='❗️Користувач був заблокований', parse_mode='html', reply_markup=markup)
    
    await state.set_state(Form.search_user)
    await state.clear()

@router.callback_query(lambda call: call.data == "orders_user")
async def orders_user(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('user')

    active_orders = get_user_active_order(user_id)
    payed_orders = get_user_payed_orders(user_id)
    rejected_orders = get_user_rejected_orders(user_id)

    text = '<b>📋 Ордери користувача:</b>\n\n'

    if active_orders:
        text += '<b>🟢 Активні ордери:</b>\n'
        for order in active_orders:
            amount, card, status = order
            text += (
                f'💶 <b>Сума:</b> {amount}\n'
                f'💳 <b>Карта:</b> {card}\n'
                f'📈 <b>Статус:</b> {status}\n\n'
            )
    else:
        text += '🟢 Активних ордерів немає.\n\n'

    if payed_orders:
        text += '<b>✅ Виплачені ордери:</b>\n'
        for order in payed_orders:
            request_id, amount, card, status = order
            text += (
                f'⚙️ <b>№:</b> {request_id}\n'
                f'💶 <b>Сума:</b> {amount}\n'
                f'💳 <b>Карта:</b> {card}\n'
                f'📈 <b>Статус:</b> {status}\n\n'
            )
    else:
        text += '✅ Виплачених ордерів немає.\n\n'

    if rejected_orders:
        text += '<b>❌ Відхилені ордери:</b>\n'
        for order in rejected_orders:
            request_id, amount, card, status = order
            text += (
                f'⚙️ <b>№:</b> {request_id}\n'
                f'💶 <b>Сума:</b> {amount}\n'
                f'💳 <b>Карта:</b> {card}\n'
                f'📈 <b>Статус:</b> {status}\n\n'
            )
    else:
        text += '❌ Відхилених ордерів немає.\n\n'

    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_user_info')]])
    
    await call.message.edit_text(text=text, parse_mode='html', reply_markup=markup)

@router.callback_query(lambda call: call.data == "back_to_user_info")
async def back_to_user_info(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = data.get('user')

    if user:
        username = user[1] if user[1] is not None else "Немає"
        first_name = html.escape(user[2]) if user[2] is not None else "Немає"
        last_name = html.escape(user[3]) if user[3] is not None else "Немає"
        balance = user[4]
        withdrawn = user[5]
        invited = user[7]
        phone = user[8]
        card = user[9]
        invited_by = user[10]
        premium = user[11]

        text = (
            f'<b>🧑‍💼 Інформація про користувача:</b>\n\n'
            f'<b>🆔 ID</b>: <code>{user[0]}</code>\n'
            f'<b>🪪 Username</b>: @{username}\n'
            f'<b>👤 Ім\'я</b>: {first_name} {last_name}\n'
            f'<b>💶 Баланс</b>: {balance}\n'
            f'<b>🏦 Виведено</b>: {withdrawn}\n'
            f'<b>👫 Запрошено</b>: {invited}\n'
            f'<b>📱 Номер</b>: +{phone}\n'
            f'<b>💳 Карта</b>: {card or 'Немає'}\n'
            f'<b>🔗 Був(ла) запрошена</b>: {invited_by or 'Немає'}\n'
            f'<b>👑 Преміум</b>: {premium or 'Немає'}\n')
        
        buttons = [[InlineKeyboardButton(text="👫 Реферали користувача", callback_data="referrals_user")],
                   [InlineKeyboardButton(text="⛔️ Заблокувати користувача", callback_data="ban_user")],
                   [InlineKeyboardButton(text="📋 Ордери користувача", callback_data='orders_user')],
                   [InlineKeyboardButton(text='↩️ Назад', callback_data='admin_menu')]]
        
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        await call.message.edit_text(text=text, parse_mode='html', reply_markup=markup)
    else:
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='admin_menu')]])
        await call.message.edit_text(text="❗️ Користувач не знайдений.", parse_mode='html', reply_markup=markup)

@router.callback_query(lambda call: call.data == "stata")
async def statistics(call: types.CallbackQuery):
    with sqlite3.connect(config.DB) as conn:
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(*) FROM ban_list")
        blocked_users = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(*) FROM users WHERE premium = 1")
        premium_users = c.fetchone()[0] or 0

    statistics_text = (
        f"<b>📊 Статистика:</b>\n\n"
        f"👥 Всього користувачів: <b>{total_users}</b>\n"
        f"🚫 Заблокованих: <b>{blocked_users}</b>\n"
        f"⭐️ Користувачів із Premium: <b>{premium_users}</b>\n")

    buttons = [[InlineKeyboardButton(text="👑 Преміум користувачі", callback_data="premium_users:")],
               [InlineKeyboardButton(text="⛔️ Заблоковані користувачі", callback_data="blocked_users:")],
               [InlineKeyboardButton(text='↩️ Назад', callback_data='admin_menu')]]
    
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.edit_text(text=statistics_text, parse_mode='html', reply_markup=markup)

@router.callback_query(lambda call: call.data.startswith("blocked_users:"))
async def blocked_users(call: types.CallbackQuery):
    data = call.data.split(":")
    page = int(data[1]) if len(data) > 1 and data[1].isdigit() else 1
    await display_banned_users(call, page)

async def display_banned_users(call: types.CallbackQuery, page: int):
    with sqlite3.connect(config.DB) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, username, first_name, last_name, phone_number FROM ban_list")
        users = c.fetchall()

    total_users = len(users)
    if total_users == 0:
        await call.message.edit_text(
            text="❗️ Заблокованих користувачів немає.",
            parse_mode='html',
            reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='stata')]]))
        return

    if page < 1 or page > total_users:
        await call.answer("❗️Недійсна сторінка.", show_alert=True)
        return

    user = users[page - 1]
    user_id, username, first_name, last_name, phone_number = user
    
    escaped_first_name = html.escape(first_name or 'Немає')
    escaped_last_name = html.escape(last_name or '')

    text = f"<b>⛔️ Заблоковані користувачі:</b>\n\n"
    text += (
        f"<b>🆔 ID:</b> {user_id}\n"
        f"<b>🪪 Username:</b> @{username if username else ''}\n"
        f"<b>👤 Ім'я:</b> {escaped_first_name} {escaped_last_name}\n"
        f"<b>📱 Номер:</b> +{phone_number}")

    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"blocked_users:{page-1}"))
    navigation_buttons.append(InlineKeyboardButton(text="✅ Розблокувати", callback_data=f"unban_user:{user_id}"))
    if page < total_users:
        navigation_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"blocked_users:{page+1}"))

    back_button = [InlineKeyboardButton(text='↩️ Назад', callback_data='stata')]

    markup = InlineKeyboardMarkup(inline_keyboard=[navigation_buttons, back_button])

    await call.message.edit_text(
        text=text,
        parse_mode='html',
        reply_markup=markup)

@router.callback_query(lambda call: call.data.startswith("unban_user:"))
async def unban_user(call: types.CallbackQuery):
    user_id = int(call.data.split(":")[1])

    with sqlite3.connect(config.DB) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM ban_list WHERE user_id = ?", (user_id,))
        conn.commit()

    await call.answer("✅ Користувача розблоковано.", show_alert=True)
    await display_banned_users(call, 1)

@router.callback_query(lambda call: call.data.startswith("premium_users:"))
async def premium_users(call: types.CallbackQuery):
    data = call.data.split(":")
    page = int(data[1]) if len(data) > 1 and data[1].isdigit() else 1
    await display_premium_users(call, page)

async def display_premium_users(call: types.CallbackQuery, page: int):
    with sqlite3.connect(config.DB) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, username, first_name, last_name, balance, withdrawing, invited, phone_number, card, invited_by FROM users WHERE premium = 1")
        premium_users = c.fetchall()

    total_users = len(premium_users)
    if total_users == 0:
        await call.message.edit_text(
            text="❗️ Преміум користувачів немає.",
            parse_mode='html',
            reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='stata')]]))
        return

    if page < 1 or page > total_users:
        await call.answer("❗️Недійсна сторінка.", show_alert=True)
        return

    user = premium_users[page - 1]
    user_id, username, first_name, last_name, balance, withdrawing, invited, phone_number, card, invited_by  = user
    
    escaped_first_name = html.escape(first_name or 'Немає')
    escaped_last_name = html.escape(last_name or '')

    text = f"<b>👑 Преміум користувачі:</b>\n\n"
    text += (
            f'<b>🆔 ID</b>: <code>{user_id}</code>\n'
            f'<b>🪪 Username</b>: @{username if username else ''}\n'
            f"<b>👤 Ім'я</b>: {escaped_first_name} {escaped_last_name}\n"
            f'<b>💶 Баланс</b>: {balance}\n'
            f'<b>🏦 Виведено</b>: {withdrawing}\n'
            f'<b>👫 Запрошено</b>: {invited}\n'
            f'<b>📱 Номер</b>: +{phone_number}\n'
            f'<b>💳 Карта</b>: {card or 'Немає'}\n'
            f'<b>🔗 Був(ла) запрошена</b>: <code>{invited_by or 'Немає'}</code>\n')
    
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"premium_users:{page-1}"))
    if page < total_users:
        navigation_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"premium_users:{page+1}"))

    back_button = [InlineKeyboardButton(text='↩️ Назад', callback_data='stata')]
    markup = InlineKeyboardMarkup(inline_keyboard=[navigation_buttons, back_button])

    await call.message.edit_text(
        text=text,
        parse_mode='html',
        reply_markup=markup)

@router.callback_query(lambda call: call.data == "config")
async def admin_config(call: types.CallbackQuery):
    load_config() 

    channel_info = "\n".join([f"📌 Ім'я: {channel['name']}\n👤 Юзернейм: @{channel['username']}\n🔗 Посилання: {channel['link']}\n"for channel in config.CHANNELS])

    text = (f"<b>⚙️ Конфіг:</b>\n\n"
            f"📚 Канали на підписку:\n\n{channel_info}\n{'-' * 50}\n"
            f"💸 Мінімальний вивід: <b>{config.MINIMUM_WITHDRAW} {config.CURRENCY}</b>\n"
            f"👫 Нагорода за реферала: <b>{config.REWARD} {config.CURRENCY}</b>")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Канали на підписку", callback_data='channels_to_subscribe')],
        [InlineKeyboardButton(text="💸 Змінити мінімальний вивід", callback_data='change_minimum_withdraw')],
        [InlineKeyboardButton(text="👫 Змінити нагороду за реферала", callback_data='change_bonus')],
        [InlineKeyboardButton(text='↩️ Назад', callback_data='admin_menu')]])

    await bot.edit_message_text(text=text, message_id=call.message.message_id, chat_id=call.message.chat.id,
                                parse_mode='html', disable_web_page_preview=True, reply_markup=keyboard)

@router.callback_query(lambda call: call.data == "channels_to_subscribe")
async def admin_change_channels_to_subscribe(call: types.CallbackQuery, state: FSMContext):
    load_config()

    channel_info = "\n\n".join([f'<code>{{"name": "{channel["name"]}", "link": "{channel["link"]}", "username": "{channel["username"]}"}}</code>' for channel in config.CHANNELS])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='config')]])

    sent_message = await bot.edit_message_text(
        text=f"📚 Канали на підписку:\n\n<code>{channel_info}</code>\n\n👇Введіть оновлений config", 
        message_id=call.message.message_id, 
        chat_id=call.message.chat.id, 
        parse_mode='html', 
        reply_markup=keyboard)

    await state.update_data(message_id=sent_message.message_id)
    await state.set_state(Config.change_channels_to_subscribe)

@router.callback_query(lambda call: call.data == "change_minimum_withdraw")
async def admin_change_minimum_withdraw(call: types.CallbackQuery, state: FSMContext):
    load_config()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='config')]])
    sent_message = await bot.edit_message_text(text="💸 Введіть нову мінімальну суму для виведення:", message_id=call.message.message_id, chat_id=call.message.chat.id, parse_mode='html', reply_markup=keyboard)

    await state.update_data(message_id=sent_message.message_id)
    await state.set_state(Config.change_minimum_withdraw)

@router.callback_query(lambda call: call.data == "change_bonus")
async def admin_change_bonus(call: types.CallbackQuery, state: FSMContext):
    load_config()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='config')]])
    sent_message = await bot.edit_message_text(text="👫 Введіть нову нагороду за реферала:", message_id=call.message.message_id, chat_id=call.message.chat.id, parse_mode='html', reply_markup=keyboard)
    
    await state.update_data(message_id=sent_message.message_id)
    await state.set_state(Config.change_bonus.state)

@router.message(StateFilter(Config.change_channels_to_subscribe))
async def channels_to_subscribe(message: types.Message, state: FSMContext):
    load_config()
    channels_to_subscribe = message.text

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


    try:
        parsed_data = json.loads(channels_to_subscribe)
        if not isinstance(parsed_data, list) or not all(
            isinstance(channel, dict) and {"name", "link", "username"} <= channel.keys() for channel in parsed_data):
            raise ValueError("Неправильний формат")
    
    except (json.JSONDecodeError, ValueError):
        new_message = await bot.send_message(
            chat_id=message.chat.id,
            text="<b>⛔ Неправильний формат!</b> Будь ласка, введіть конфігурацію у форматі JSON:\n\n[{\"name\": \"name\", \"link\": \"https://t.me/link\", \"username\": \"username\"}, ...]",
            parse_mode='html',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ Меню", callback_data='config')]]))
        
        await state.update_data(message_id=new_message.message_id)
        return

    config.CHANNELS = parsed_data
    save_config()

    menu_button = InlineKeyboardButton(text="↩️ Меню", callback_data='config')
    markup = InlineKeyboardMarkup(inline_keyboard=[[menu_button]])
    await bot.send_message(
        chat_id=message.chat.id,
        text=f'📚 Оновлений config:\n\n<code>{channels_to_subscribe}</code>',
        parse_mode='html',
        reply_markup=markup)
    await state.clear()

@router.message(StateFilter(Config.change_minimum_withdraw))
async def minimum_withdraw(message: types.Message, state: FSMContext):
    load_config()
    minimum_withdraw = message.text

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

    if not minimum_withdraw.isdigit():
        try:
            new_message = await bot.send_message(
                chat_id=message.chat.id,
                text="⛔ Будь ласка, введіть число:",
                parse_mode='html',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ Меню", callback_data='config')]]))
            
            await state.update_data(message_id=new_message.message_id)
        except Exception as e:
            logging.error(f"Помилка при зміненні config: {e}")
        return

    config.MINIMUM_WITHDRAW = minimum_withdraw
    save_config()

    menu_button = InlineKeyboardButton(text="↩️ Меню", callback_data='config')
    markup = InlineKeyboardMarkup(inline_keyboard=[[menu_button]])
    await bot.send_message(
        chat_id=message.chat.id,
        text=f'💸 Мінімальна сума для виведення змінена на: <b>{minimum_withdraw} {config.CURRENCY}</b>',
        parse_mode='html',
        reply_markup=markup)
    await state.clear()

@router.message(StateFilter(Config.change_bonus))
async def bonus(message: types.Message, state: FSMContext):
    load_config()
    bonus = message.text

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

    if not bonus.isdigit():
        try:
            new_message = await bot.send_message(
                chat_id=message.chat.id,
                text="⛔ Будь ласка, введіть число:",
                parse_mode='html',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ Меню", callback_data='config')]]))
            
            await state.update_data(message_id=new_message.message_id)
        except Exception as e:
            logging.error(f"Помилка при зміненні config: {e}")
        return

    config.REWARD = bonus
    save_config()
    
    menu_button = InlineKeyboardButton(text="↩️ Меню", callback_data='config')
    markup = InlineKeyboardMarkup(inline_keyboard=[[menu_button]])
    await bot.send_message(
        chat_id=message.chat.id,
        text=f'👫 Нагорода за рефералів успішно змінена на: <b>{bonus} {config.CURRENCY}</b>',
        parse_mode='html',
        reply_markup=markup)
    await state.clear()



@router.message(lambda message: message.from_user.id in config.ADMIN_ID)
async def handle_admin_message(message: types.Message):

    global pending_broadcast
    pending_broadcast[message.chat.id] = message

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Розіслати", callback_data='send_all')],
        [InlineKeyboardButton(text="⏺ Розіслати з кнопкою", callback_data='send_with_button')],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data='cancel')]])

    if message.media_group_id:
        media_group = []
        for media in message.photo:
            media_group.append(InputMediaPhoto(media=media.file_id, caption=message.caption if len(media_group) == 0 else ''))
        pending_broadcast[message.chat.id] = media_group
        await bot.send_media_group(chat_id=message.chat.id, media=media_group)
    else:
        await message.send_copy(chat_id=message.chat.id, reply_markup=keyboard)

    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    
@router.callback_query(lambda c: c.data == 'send_all')
async def process_broadcast(c: CallbackQuery):
    global pending_broadcast

    if c.message.chat.id not in pending_broadcast:
        await bot.answer_callback_query(c.id, text="❗️Немає повідомлення для розсилки.")
        return

    message = pending_broadcast[c.message.chat.id]
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()

    cursor.execute('SELECT user_id FROM users')
    audience = cursor.fetchall()

    await bot.delete_message(chat_id=c.message.chat.id, message_id=c.message.message_id)
    await bot.answer_callback_query(c.id, text="✉️ Розсилка новини почалась...", show_alert=True)

    sent_count = 0
    failed_count = 0

    for user_id in audience:
        try:
            if isinstance(message, list):
                await bot.send_media_group(chat_id=user_id[0], media=message)
            else:
                await message.send_copy(chat_id=user_id[0])
            sent_count += 1
        except Exception as e:
            logging.error(f"Помилка відправки користувачу {user_id[0]}: {e}")
            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id[0],))
            conn.commit()
            failed_count += 1

    del pending_broadcast[c.message.chat.id]

    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⏺ Закрити', callback_data='close_button')]])
    
    await bot.send_message(
        chat_id=c.message.chat.id, 
        text=f"<b>⚙️ Розсилка завершена.</b>\n\n ✅ Успішно відправлено: <b>{sent_count}</b>\n ❌ Не вдалося відправити: <b>{failed_count}</b>", 
        parse_mode='html',
        reply_markup=markup
    )

@router.callback_query(lambda c: c.data == 'send_with_button')
async def process_broadcast(c: CallbackQuery):
    global pending_broadcast

    if c.message.chat.id not in pending_broadcast:
        await bot.answer_callback_query(c.id, text="❗️Немає повідомлення для розсилки.")
        return

    message = pending_broadcast[c.message.chat.id]
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()

    cursor.execute('SELECT user_id FROM users')
    audience = cursor.fetchall()

    await bot.delete_message(chat_id=c.message.chat.id, message_id=c.message.message_id)
    await bot.answer_callback_query(c.id, text="✉️ Розсилка новини почалась...", show_alert=True)

    sent_count = 0
    failed_count = 0

    for user_id in audience:
        try:
            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⏺ Закрити', callback_data='close_button')]])
            if isinstance(message, list):
                await bot.send_media_group(chat_id=user_id[0], media=message)
                await bot.send_message(chat_id=user_id[0], text="Ось ваше повідомлення.", reply_markup=markup)
            else:
                await message.send_copy(chat_id=user_id[0], reply_markup=markup)
            sent_count += 1
        except Exception as e:
            logging.error(f"Помилка відправки користувачу {user_id[0]}: {e}")
            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id[0],))
            conn.commit()
            failed_count += 1

    del pending_broadcast[c.message.chat.id]

    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⏺ Закрити', callback_data='close_button')]])
    
    await bot.send_message(
        chat_id=c.message.chat.id, 
        text=f"<b>⚙️ Розсилка завершена.</b>\n\n ✅ Успішно відправлено: <b>{sent_count}</b>\n ❌ Не вдалося відправити: <b>{failed_count}</b>", 
        parse_mode='html',
        reply_markup=markup)

@router.callback_query(lambda c: c.data == 'cancel')
async def cancel_broadcast(c: CallbackQuery):
    global pending_broadcast

    if c.message.chat.id in pending_broadcast:
        try:
            await bot.delete_message(chat_id=c.message.chat.id, message_id=pending_broadcast[c.message.chat.id].message_id)
        except Exception as e:
            logging.error(f"Помилка при видаленні повідомлення: {e}")

        del pending_broadcast[c.message.chat.id]

    await bot.delete_message(chat_id=c.message.chat.id, message_id=c.message.message_id)
    await c.answer("❌Скасовано!", show_alert=True)
