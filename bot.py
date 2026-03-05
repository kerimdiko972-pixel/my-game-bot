import telebot
import time
import sqlite3
import random
import threading
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN

bot = telebot.TeleBot(BOT_TOKEN)

# ===== РАНГИ =====
RANKS = [
    (100000, "🔱Император🔱"),
    (20000,  "💠Легенда💠"),
    (7000,   "🔴Грандмастер🔴"),
    (2000,   "🟣Мастер🟣"),
    (500,    "🔵Профи🔵"),
    (100,    "🟢Опытный🟢"),
    (0,      "⚪Новичок⚪"),
]

def get_rank(exp):
    for min_exp, rank in RANKS:
        if exp >= min_exp:
            return rank
    return "⚪Новичок⚪"

# ===== ОВОЩИ =====
VEGETABLES = [
    ("🥔", 50),
    ("🥕", 25),
    ("🍅", 15),
    ("🍆", 8),
    ("🎃", 2),
]

VEG_COLUMNS = {
    "🥔": "potato",
    "🥕": "carrot",
    "🍅": "tomato",
    "🍆": "eggplant",
    "🎃": "pumpkin"
}

def random_vegetable():
    total = sum(w for _, w in VEGETABLES)
    r = random.randint(1, total)
    cumulative = 0
    for veg, weight in VEGETABLES:
        cumulative += weight
        if r <= cumulative:
            return veg
    return "🥔"

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT,
            money      INTEGER DEFAULT 0,
            exp        INTEGER DEFAULT 0,
            seeds      INTEGER DEFAULT 0,
            bait       INTEGER DEFAULT 0,
            last_daily TEXT DEFAULT NULL,
            potato     INTEGER DEFAULT 0,
            carrot     INTEGER DEFAULT 0,
            tomato     INTEGER DEFAULT 0,
            eggplant   INTEGER DEFAULT 0,
            pumpkin    INTEGER DEFAULT 0
        )
    ''')
    # Если старая БД без овощей — добавляем колонки
    for col in ['potato', 'carrot', 'tomato', 'eggplant', 'pumpkin']:
        try:
            c.execute(f'ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 0')
        except:
            pass
    c.execute('''
        CREATE TABLE IF NOT EXISTS garden (
            user_id    INTEGER,
            slot       INTEGER,
            status     TEXT DEFAULT 'empty',
            planted_at TEXT DEFAULT NULL,
            vegetable  TEXT DEFAULT NULL,
            chat_id    INTEGER DEFAULT NULL,
            message_id INTEGER DEFAULT NULL,
            PRIMARY KEY (user_id, slot)
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_username(username):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    return user

def register_user(user_id, username):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    for slot in range(1, 7):
        c.execute('INSERT OR IGNORE INTO garden (user_id, slot) VALUES (?, ?)', (user_id, slot))
    conn.commit()
    conn.close()

def update_daily(user_id, money, exp, seeds, bait, timestamp):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''
        UPDATE users SET money=money+?, exp=exp+?, seeds=seeds+?, bait=bait+?, last_daily=?
        WHERE user_id=?
    ''', (money, exp, seeds, bait, timestamp, user_id))
    conn.commit()
    conn.close()

def get_top_users(limit=15):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT username, money FROM users ORDER BY money DESC LIMIT ?', (limit,))
    top = c.fetchall()
    conn.close()
    return top

def get_garden(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT slot, status, planted_at, vegetable FROM garden WHERE user_id=? ORDER BY slot', (user_id,))
    slots = c.fetchall()
    conn.close()
    return slots

def plant_seed(user_id, slot, chat_id, message_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        UPDATE garden SET status='growing', planted_at=?, vegetable=NULL, chat_id=?, message_id=?
        WHERE user_id=? AND slot=?
    ''', (now, chat_id, message_id, user_id, slot))
    c.execute('UPDATE users SET seeds=seeds-1 WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()

def mark_slot_ready(user_id, slot, vegetable):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('UPDATE garden SET status="ready", vegetable=? WHERE user_id=? AND slot=?',
              (vegetable, user_id, slot))
    conn.commit()
    conn.close()

def harvest_slot(user_id, slot):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT vegetable, status FROM garden WHERE user_id=? AND slot=?', (user_id, slot))
    row = c.fetchone()
    if not row or row[1] != 'ready':
        conn.close()
        return None
    veg = row[0]
    col = VEG_COLUMNS.get(veg)
    if col:
        c.execute(f'UPDATE users SET {col}={col}+1 WHERE user_id=?', (user_id,))
    c.execute('''
        UPDATE garden SET status="empty", planted_at=NULL, vegetable=NULL, chat_id=NULL, message_id=NULL
        WHERE user_id=? AND slot=?
    ''', (user_id, slot))
    conn.commit()
    conn.close()
    return veg

def get_ready_to_harvest():
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    threshold = (datetime.now() - timedelta(minutes=30)).isoformat()
    c.execute('''
        SELECT user_id, slot, chat_id, message_id
        FROM garden
        WHERE status='growing' AND planted_at <= ?
    ''', (threshold,))
    rows = c.fetchall()
    conn.close()
    return rows

# ===== ОГОРОД UI =====
def garden_text(user_id):
    user = get_user(user_id)
    seeds = user[4] if user else 0
    bait  = user[5] if user else 0
    return (
        f"🪏 ОГОРОД 🪏\n"
        f"🌱 Семян: {seeds}\n"
        f"🪱 Червей: {bait}\n"
        f"- - - - - - - - - - - - - -"
    )

def garden_keyboard(user_id):
    slots = get_garden(user_id)
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for slot, status, planted_at, vegetable in slots:
        if status == 'empty':
            btn = InlineKeyboardButton("🪏Посадить", callback_data=f"plant_{slot}")
        elif status == 'growing':
            planted = datetime.fromisoformat(planted_at)
            remaining = (planted + timedelta(minutes=30)) - datetime.now()
            if remaining.total_seconds() <= 0:
                btn = InlineKeyboardButton("🌱 Готово!", callback_data=f"harvest_{slot}")
            else:
                mins = int(remaining.total_seconds() // 60)
                btn = InlineKeyboardButton(f"🌱 {mins}мин", callback_data=f"growing_{slot}")
        elif status == 'ready':
            btn = InlineKeyboardButton(f"{vegetable} Собрать!", callback_data=f"harvest_{slot}")
        else:
            btn = InlineKeyboardButton("🪏Посадить", callback_data=f"plant_{slot}")
        buttons.append(btn)
    markup.add(*buttons)
    return markup

# ===== ФОНОВЫЙ ПОТОК (проверяет огород) =====
def garden_checker():
    while True:
        try:
            ready = get_ready_to_harvest()
            for user_id, slot, chat_id, message_id in ready:
                veg = random_vegetable()
                mark_slot_ready(user_id, slot, veg)
                if chat_id and message_id:
                    try:
                        bot.edit_message_text(
                            garden_text(user_id),
                            chat_id=chat_id,
                            message_id=message_id,
                            reply_markup=garden_keyboard(user_id)
                        )
                    except Exception as e:
                        print(f"Garden edit error: {e}")
        except Exception as e:
            print(f"Checker error: {e}")
        time.sleep(30)

# ===== КОМАНДЫ =====

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Открой меню команд, чтобы узнать что тут есть."
    )

@bot.message_handler(commands=['daily'])
def cmd_daily(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    user = get_user(user_id)
    now = datetime.now()
    if user and user[6]:
        last = datetime.fromisoformat(user[6])
        diff = now - last
        if diff < timedelta(hours=24):
            remaining = timedelta(hours=24) - diff
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            bot.send_message(message.chat.id, f"⏳ Следующая награда через {hours:02d}:{minutes:02d}")
            return
    money = random.randint(100, 1000)
    exp   = random.randint(5, 20)
    seeds = random.randint(1, 3)
    bait  = random.randint(1, 3)
    update_daily(user_id, money, exp, seeds, bait, now.isoformat())
    bot.send_message(
        message.chat.id,
        f"🎁 Ежедневная награда 🎁\n\n"
        f"+ {money} 💵 Денег\n"
        f"+ {exp} 🌟 Опыта\n"
        f"+ {seeds} 🌱 Семян\n"
        f"+ {bait} 🪱 Наживок\n\n"
        f"⏳ Ожидай следующую награду через 24:00"
    )

@bot.message_handler(commands=['bio'])
def cmd_bio(message):
    args = message.text.split()
    if len(args) > 1:
        target = args[1].replace('@', '')
        user = get_user_by_username(target)
        if not user:
            bot.send_message(message.chat.id, "❌ Пользователь не найден!")
            return
    else:
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        register_user(user_id, username)
        user = get_user(user_id)

    username = user[1]
    money    = user[2]
    exp      = user[3]
    rank     = get_rank(exp)

    bot.send_message(
        message.chat.id,
        f"*👤 {username}*\n\n"
        f"*🏅 Ранг: {rank}*\n"
        f"*🌟 Опыт: {exp}*\n"
        f"*💵 Денег: {money}*",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['rating'])
def cmd_rating(message):
    top = get_top_users(15)
    if not top:
        bot.send_message(message.chat.id, "Рейтинг пока пуст!")
        return
    text = "🏆 Рейтинг игроков по деньгам 💵:\n\n"
    for i, (username, money) in enumerate(top, 1):
        text += f"{i}. {username} — {money} 💵\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['garden'])
def cmd_garden(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    msg = bot.send_message(
        message.chat.id,
        garden_text(user_id),
        reply_markup=garden_keyboard(user_id)
    )
    # Обновляем message_id для растущих слотов
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''
        UPDATE garden SET chat_id=?, message_id=?
        WHERE user_id=? AND status IN ('growing', 'ready')
    ''', (message.chat.id, msg.message_id, user_id))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['bag'])
def cmd_bag(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    user = get_user(user_id)
    money    = user[2]
    seeds    = user[4]
    bait     = user[5]
    potato   = user[7]
    carrot   = user[8]
    tomato   = user[9]
    eggplant = user[10]
    pumpkin  = user[11]

    text = f"В мешке у игрока *{username}*:\n\n"
    text += f"💵 Денег: {money}\n"
    text += f"🌱 Семян: {seeds}\n"
    text += f"🪱 Наживок: {bait}\n"
    text += f"- - - - - - - - -\n"
    if potato   > 0: text += f"🥔 × {potato}\n"
    if carrot   > 0: text += f"🥕 × {carrot}\n"
    if tomato   > 0: text += f"🍅 × {tomato}\n"
    if eggplant > 0: text += f"🍆 × {eggplant}\n"
    if pumpkin  > 0: text += f"🎃 × {pumpkin}\n"

    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ===== КОЛБЭКИ ОГОРОДА =====

@bot.callback_query_handler(func=lambda call: call.data.startswith('plant_'))
def callback_plant(call):
    user_id = call.from_user.id
    slot = int(call.data.split('_')[1])
    user = get_user(user_id)
    if not user or user[4] < 1:
        bot.answer_callback_query(call.id, "❌ Нет семян!")
        return
    plant_seed(user_id, slot, call.message.chat.id, call.message.message_id)
    bot.edit_message_text(
        garden_text(user_id),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=garden_keyboard(user_id)
    )
    bot.answer_callback_query(call.id, "🌱 Семя посажено!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('growing_'))
def callback_growing(call):
    bot.answer_callback_query(call.id, "⏳ Ещё растёт, подожди!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('harvest_'))
def callback_harvest(call):
    user_id = call.from_user.id
    slot = int(call.data.split('_')[1])
    # Если статус growing но время вышло — сначала помечаем ready
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT status, planted_at FROM garden WHERE user_id=? AND slot=?', (user_id, slot))
    row = c.fetchone()
    conn.close()
    if row and row[0] == 'growing':
        planted = datetime.fromisoformat(row[1])
        if datetime.now() - planted >= timedelta(minutes=30):
            veg = random_vegetable()
            mark_slot_ready(user_id, slot, veg)
        else:
            bot.answer_callback_query(call.id, "⏳ Ещё не выросло!")
            return
    veg = harvest_slot(user_id, slot)
    if veg:
        bot.answer_callback_query(call.id, f"+1 {veg} собрано!")
        bot.send_message(call.message.chat.id, f"+1 {veg}")
        bot.edit_message_text(
            garden_text(user_id),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=garden_keyboard(user_id)
        )
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка!")

# ===== ЗАПУСК =====
init_db()
print("Бот запущен!")

checker = threading.Thread(target=garden_checker, daemon=True)
checker.start()

while True:
    try:
        bot.polling(non_stop=True)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(5)
