import logging, config
from datetime import datetime
from aiogram import Bot, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from Utils.check_sub_block import send_subscription, check_subscription
from db import get_user, user_in_ban_list, get_user_active_order, get_user_payed_orders, get_user_rejected_orders, generate_request_id

bot = Bot(token=config.API_TOKEN)
router = Router()

@router.callback_query(lambda c: c.data.startswith('my_orders'))
async def my_orders(call: CallbackQuery):
    log_message = f"Мої ордери - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logging.info(log_message)
    await bot.send_message(chat_id=config.LOGS, text=log_message)
    
    user = get_user(call.from_user.id)
    user_ban = user_in_ban_list(call.from_user.id)
    active_orders = get_user_active_order(call.from_user.id) or []
    payed_orders = get_user_payed_orders(call.from_user.id) or []  
    rejected_orders = get_user_rejected_orders(call.from_user.id) or []
    
    if user:
        if not user_ban:
            if not await check_subscription(call.from_user.id):
                await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                await send_subscription(call.message.chat.id)
                return
            
            if not active_orders and not payed_orders and not rejected_orders:
                back_button = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='profile')]])
                orders_text = "📋 У вас поки немає ордерів."
                await bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=orders_text,
                    parse_mode='html',
                    reply_markup=back_button
                )
            else:
                page = int(call.data.split(':')[-1]) if ':' in call.data else 1
                orders_per_page = 3
                all_orders = active_orders + payed_orders + rejected_orders
                total_pages = (len(all_orders) - 1) // orders_per_page + 1
                start = (page - 1) * orders_per_page
                end = start + orders_per_page
                current_orders =all_orders[start:end]

                orders_text = '<b>📋 Мої ордери:</b>\n\n'
                for order in current_orders:
                    amount = order[-3]
                    card = order[-2]
                    status = order[-1]

                    orders_text += (
                        f"<b>⚙️ Запит на виведення:</b>\n"
                        f"💶 Сума: {amount} {config.CURRENCY}\n"
                        f"💳 Карта: <code>{card}</code>\n"
                        f"📈 Статус: {status}\n"
                        f"\n{'-'*35}\n")
                
                orders_text = orders_text.rstrip(f"\n{'-'*35}\n\n")

                navigation_buttons = []
                if page > 1:
                    navigation_buttons.append(InlineKeyboardButton(text="◀️ Попередня сторінка", callback_data=f'my_orders:{page-1}'))
                if page < total_pages:
                    navigation_buttons.append(InlineKeyboardButton(text="Наступна сторінка ▶️", callback_data=f'my_orders:{page+1}'))

                back_button = [InlineKeyboardButton(text='↩️ Назад', callback_data='profile')]

                if navigation_buttons:
                    markup = InlineKeyboardMarkup(inline_keyboard=[navigation_buttons, back_button])
                else:
                    markup = InlineKeyboardMarkup(inline_keyboard=[back_button])

                await bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=orders_text,
                    parse_mode='html',
                    reply_markup=markup)
        else:
            await call.answer(config.BAN_MESSAGE, show_alert=True)
    else:
       await call.answer(config.BAN_MESSAGE, show_alert=True)
