import sqlite3
import random
from datetime import datetime
import config
import logging

logging.basicConfig(level=logging.INFO)

def create_db():
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY, 
                username TEXT, 
                first_name TEXT, 
                last_name TEXT,
                balance INTEGER, 
                withdrawing INTEGER, 
                ref_link TEXT, 
                invited INTEGER,
                phone_number TEXT,
                card TEXT,
                invited_by INTEGER,
                premium BOOLEAN)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS active_orders(
                user_id INTEGER PRIMARY KEY,
                amount INTEGER NOT NULL,
                card TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS payed_orders(
                request_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                amount INTEGER NOT NULL,
                card TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS rejected_orders(
                request_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                amount INTEGER NOT NULL,
                card TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS referral_bonuses
                (user_id INTEGER PRIMARY KEY, 
                referrer_id INTEGER,
                bonus_given BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS ban_list(
                user_id INTEGER PRIMARY KEY,
                username TEXT, 
                first_name TEXT, 
                last_name TEXT,
                phone_number TEXT)''')  
    conn.commit()
    conn.close()

#Отримання id користвача
def get_user(user_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

#Перевірка чи є вже користувач в боті
def user_exists(user_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

#Перевірка чи користувач забанений
def user_in_ban_list(user_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("SELECT * FROM ban_list WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

#Додавання користувача в чорний список
def add_to_ban_list(user_id, username, first_name, last_name, phone_number):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("INSERT INTO ban_list (user_id, username, first_name, last_name, phone_number) VALUES (? ,?, ?, ?, ?)", (user_id,  username, first_name, last_name, phone_number))
    conn.commit()
    conn.close()

#Додавання користувача в БД
def add_user(user_id, username, first_name, last_name, ref_link, phone_number, premium):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute('''INSERT INTO users (user_id, username, first_name, last_name, balance, withdrawing, ref_link, invited, phone_number, card, premium)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (user_id, username, first_name, last_name, 0, 0, ref_link, 0, phone_number, None, premium))
    conn.commit()
    conn.close()

#Додавання бонусу користувачу за запрошення реферала
def update_balance_and_invited(user_id, amount, invited):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ?, invited = invited + ? WHERE user_id = ?", (amount, invited, user_id))
    conn.commit()
    conn.close()

#Додавання бонусу користувачу за запрошення реферала
def update_withdrawing(id, amount):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("UPDATE users SET withdrawing = withdrawing + ? WHERE user_id = ?", (amount, id))
    conn.commit()
    conn.close()

#Оновлення балансу
def update_balance(id, amount):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, id))
    conn.commit()
    conn.close()

#Встановлення карти
def setting_card(new_card, user_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("UPDATE users SET card = ? WHERE user_id = ?", (new_card, user_id))
    conn.commit()
    conn.close()
   
#Отримання всіх користувачів в боті
def get_total_users():
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    conn.close()
    return total_users

#Отримання всіх оплат користувачам
def get_total_payed():
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM payed_orders")
    total_withdrawn = c.fetchone()[0]
    conn.close()
    return total_withdrawn if total_withdrawn else 0

#Отримання користувача якого запросили
def get_user_invited_by(user_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("SELECT invited_by FROM users WHERE user_id = ?", (user_id,))
    invited_by = c.fetchone()
    conn.close()
    return invited_by[0] if invited_by else None

#Оновлення запрошень
def update_invited_by(user_id, referrer_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("UPDATE users SET invited_by = ? WHERE user_id = ?", (referrer_id, user_id))
    conn.commit()
    conn.close()

#Відхилення виплати
def reject_withdrawing(user_id, amount):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

#Додавання активного ордера в БД
def add_active_order(user_id, amount, card, status, created_at):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()

    c.execute("SELECT user_id FROM active_orders WHERE user_id = ?", (user_id,))
    existing_order = c.fetchone()

    if existing_order:
        c.execute('''UPDATE active_orders SET user_id = ?, amount = ?, card = ?, status = ?, created_at = ? 
                     WHERE user_id = ?''', (user_id, amount, card, status, created_at))
    else:
        c.execute("INSERT INTO active_orders (user_id, amount, card, status, created_at) VALUES (?, ?, ?, ?, ?)",
                  (user_id, amount, card, status, created_at))

    conn.commit()
    conn.close()

#Перевірка чи є ордер на виплату
def has_active_order(user_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("SELECT * FROM active_orders WHERE user_id = ? AND status = ?", (user_id, '⌛️ обробляється...'))
    order = c.fetchone()
    conn.close()
    return order is not None

# Отримання активних ордерів
def get_user_active_order(user_id):
    if isinstance(user_id, tuple):  # Якщо user_id — кортеж, беремо перший елемент
        user_id = user_id[0]
    with sqlite3.connect(config.DB) as conn:
        c = conn.cursor()
        c.execute("SELECT amount, card, status FROM active_orders WHERE user_id = ? LIMIT 1", (user_id,))
        return c.fetchall()

#Отримання виплачених ордерів
def get_user_payed_orders(user_id): 
    # Перевіряємо, чи user_id є кортежем, і беремо перший елемент
    if isinstance(user_id, tuple):
        user_id = user_id[0]
    with sqlite3.connect(config.DB) as conn:
        c = conn.cursor()
        c.execute("SELECT request_id, amount, card, status FROM payed_orders WHERE user_id = ?", (user_id,))
        return c.fetchall()

#Отримання відхилених ордерів
def get_user_rejected_orders(user_id): 
    # Перевіряємо, чи user_id є кортежем, і беремо перший елемент
    if isinstance(user_id, tuple):
        user_id = user_id[0]
    with sqlite3.connect(config.DB) as conn:
        c = conn.cursor()
        c.execute("SELECT request_id, amount, card, status FROM rejected_orders WHERE user_id = ?", (user_id,))
        return c.fetchall()

#Оновлення статусу ордера
def update_order_status(user_id, status):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    try:
        c.execute("UPDATE active_orders SET status = ? WHERE user_id = ?", (status, user_id))
    finally:
        c.close()
        conn.close()

#Переміщення ордера в оплачені та видалення його з активних
def move_order_to_payed(user_id, order):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()

    # Перевіряємо, чи є тільки один кортеж в ордері
    if len(order) == 1:
        amount, card, status = order[0]  # Розпаковуємо значення з першого елементу (кортежу)
    else:
        print("Ордер має невірну кількість елементів", order)
        return

    request_id = generate_request_id()

    # Вставляємо новий ордер в таблицю payed_orders, навіть якщо вже є ордер для цього користувача
    c.execute('''INSERT INTO payed_orders (user_id, amount, card, status, created_at, request_id)
                 VALUES (?, ?, ?, ?, ?, ?)''', 
              (user_id, amount, card, "✅ Оплачено", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), request_id))

    # Видаляємо ордер з таблиці active_orders
    c.execute('DELETE FROM active_orders WHERE user_id = ? AND amount = ? AND card = ? AND status = ?',
              (user_id, amount, card, status))

    conn.commit()
    conn.close()

#Переміщення ордера в відхилені та видалення його з активних
def move_order_to_rejected(user_id, order):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()

    # Перевіряємо, чи є тільки один кортеж в ордері
    if len(order) == 1:
        amount, card, status = order[0]  # Розпаковуємо значення з першого елементу (кортежу)
    else:
        print("Ордер має невірну кількість елементів", order)
        return

    request_id = generate_request_id()  # Генерація request_id

    # Вставляємо новий ордер в таблицю rejected_orders
    c.execute('''INSERT INTO rejected_orders (user_id, amount, card, status, created_at, request_id)
                 VALUES (?, ?, ?, ?, ?, ?)''', 
              (user_id, amount, card, "❌ Відхилено", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), request_id))

    # Видаляємо ордер з таблиці active_orders
    c.execute('DELETE FROM active_orders WHERE user_id = ? AND amount = ? AND card = ? AND status = ?',
              (user_id, amount, card, status))

    conn.commit()
    conn.close()

#Генерація випадкого числа
def generate_request_id():
    return random.randint(111111, 999999)

def check_bonus_given(referrer_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM referral_bonuses WHERE referrer_id = ? AND bonus_given = 0", (referrer_id,))
        result = c.fetchone()
    finally:
        c.close()
        conn.close()
        return result is not None

def mark_bonus_given(referrer_id, user_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()

    c.execute("SELECT user_id FROM referral_bonuses WHERE user_id = ?", (user_id,))
    existing_record = c.fetchone()

    if not existing_record:
        c.execute("INSERT INTO referral_bonuses (user_id, referrer_id, bonus_given) VALUES (?, ?, 1)", (user_id, referrer_id))
    else:
        print(f"Бонус вже нараховано для користувача з ID: {user_id}")

    conn.commit()
    conn.close()

def update_user_phone(id, phone):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, id))
    conn.commit()
    conn.close()

def get_leaders():
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()

    c.execute("""SELECT first_name, invited FROM users WHERE invited > 0 ORDER BY invited DESC LIMIT 10""")
    leaderboard = c.fetchall()
    conn.close()
    return leaderboard

def update_withdrawing(amount, user_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("UPDATE users SET withdrawing = withdrawing + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def not_paid_1(user_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    try:
        c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user_balance = c.fetchone()
        return user_balance
    finally:
        conn.close()

def not_paid_2(user_balance, amount, user_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    try:
        new_balance = user_balance[0] + amount
        c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        conn.commit()
    finally:
        conn.close()

def search_user(user_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def check_active_order(user_id: int) -> bool:
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()
    
    cursor.execute("""SELECT user_id FROM active_orders WHERE user_id = ? AND status = '⌛️ обробляється...'""", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return bool(result)

def delete_user(user_id):
    conn = sqlite3.connect(config.DB)
    c = conn.cursor()
    try:
        if isinstance(user_id, tuple):
            user_id = user_id[0]

        c.execute("SELECT user_id, username, first_name, last_name, phone_number FROM users WHERE user_id = ?", (user_id,))
        user_data = c.fetchone()


        if not user_data:
            return
        
        c.execute("DELETE FROM referral_bonuses WHERE referrer_id = ?", (user_id,))
        c.execute("DELETE FROM active_orders WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM payed_orders WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM rejected_orders WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    
        c.execute('''INSERT INTO ban_list (user_id, username, first_name, last_name, phone_number) VALUES (?, ?, ?, ?, ?)''', user_data)
        
        conn.commit()
        return
    
    except Exception as e:
        print(f"Сталася помилка: {e}")
    finally:
        c.close()
        conn.close()

def is_user_banned(user_id: str) -> bool:
    connection = sqlite3.connect(config.DB)
    cursor = connection.cursor()
    cursor.execute("SELECT 1 FROM ban_list WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    connection.close()
    return result is not None