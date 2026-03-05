import telebot
import time
import sqlite3
import random
import threading
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from config import BOT_TOKEN

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return 'Бот работает!', 200

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
    ("🥔", 50), ("🥕", 25), ("🍅", 15), ("🍆", 8), ("🎃", 2),
]
VEG_COLUMNS = {
    "🥔": "potato", "🥕": "carrot",
    "🍅": "tomato", "🍆": "eggplant", "🎃": "pumpkin"
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

# ===== ПЕТЫ =====
PETS = {
    "🟢 Обычные": {
        "chance": 40, "emoji": "🟢",
        "pets": ["🐁","🐀","🐹","🐇","🐔","🐣","🐟","🐠","🐌","🐜","🐛","🪰","🪲","🦗","🪳","🐝","🐞"]
    },
    "🔵 Редкие": {
        "chance": 20, "emoji": "🔵",
        "pets": ["🐈","🐈‍⬛","🐕","🐩","🐓","🦆","🪿","🦜","🕊️","🦔","🐿️","🦫","🦝","🦨","🦎","🐸","🐍","🐧"]
    },
    "🟣 Эпические": {
        "chance": 17, "emoji": "🟣",
        "pets": ["🦊","🐺","🦉","🦅","🦚","🦩","🦦","🦇","🦘","🐒","🦓","🦙","🦥","🐢","🐊","🦑","🦀","🦐","🦞"]
    },
    "🟡 Легендарные": {
        "chance": 11, "emoji": "🟡",
        "pets": ["🦁","🐅","🐆","🦒","🐘","🦏","🦛","🐪","🐎","🫎","🦌","🐗","🐬","🪼","🦈","🦢","🐼","🐨","🐻"]
    },
    "🔴 Мифические": {
        "chance": 7, "emoji": "🔴",
        "pets": ["🦍","🦧","🦣","🦕","🐋","🐻‍❄️","🦬","🐂","🐙"]
    },
    "🌈 Хроматические": {
        "chance": 4, "emoji": "🌈",
        "pets": ["🐉","🦖","🦄","🐦‍🔥","🦤"]
    },
    "☄️ Секретные": {
        "chance": 1, "emoji": "☄️",
        "pets": ["🤡","😈","😇","🤖","👽","👻","💀","⛄"]
    },
}

PET_RARITY = {}
for rarity, data in PETS.items():
    for pet in data["pets"]:
        PET_RARITY[pet] = (rarity, data["emoji"])

def random_pet():
    groups = list(PETS.keys())
    weights = [PETS[g]["chance"] for g in groups]
    chosen_group = random.choices(groups, weights=weights, k=1)[0]
    return random.choice(PETS[chosen_group]["pets"]), chosen_group

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
    for col in ['potato','carrot','tomato','eggplant','pumpkin']:
        try:
            c.execute(f'ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 0')
        except: pass
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS pets (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            pet        TEXT,
            rarity     TEXT,
            count      INTEGER DEFAULT 1,
            UNIQUE(user_id, pet)
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_username(username):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username=?', (username,))
    user = c.fetchone()
    conn.close()
    return user

def register_user(user_id, username):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)', (user_id, username))
    for slot in range(1, 7):
        c.execute('INSERT OR IGNORE INTO garden (user_id, slot) VALUES (?,?)', (user_id, slot))
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

def add_exp(user_id, amount):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('UPDATE users SET exp=exp+? WHERE user_id=?', (amount, user_id))
    conn.commit()
    conn.close()

def spend_money(user_id, amount):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('UPDATE users SET money=money-? WHERE user_id=?', (amount, user_id))
    conn.commit()
    conn.close()

def add_seeds(user_id, amount):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('UPDATE users SET seeds=seeds+? WHERE user_id=?', (amount, user_id))
    conn.commit()
    conn.close()

def add_bait(user_id, amount):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('UPDATE users SET bait=bait+? WHERE user_id=?', (amount, user_id))
    conn.commit()
    conn.close()

def add_pet(user_id, pet, rarity):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO pets (user_id, pet, rarity, count) VALUES (?,?,?,1)
        ON CONFLICT(user_id, pet) DO UPDATE SET count=count+1
    ''', (user_id, pet, rarity))
    conn.commit()
    conn.close()

def get_pets(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT pet, rarity, count FROM pets WHERE user_id=? ORDER BY rarity', (user_id,))
    pets = c.fetchall()
    conn.close()
    return pets

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
        FROM garden WHERE status='growing' AND planted_at <= ?
    ''', (threshold,))
    rows = c.fetchall()
    conn.close()
    return rows

# ===== ОГОРОД UI =====
def garden_text(user_id):
    user = get_user(user_id)
    seeds = user[4] if user else 0
    bait  = user[5] if user else 0
    return (f"🪏 ОГОРОД 🪏\n🌱 Семян: {seeds}\n🪱 Червей: {bait}\n- - - - - - - - - - - - - -")

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

def shop_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🌱 Семена×5 — 💵80",         callback_data="buy_seeds"),
        InlineKeyboardButton("🪱 Наживка×5 — 💵60",        callback_data="buy_bait"),
        InlineKeyboardButton("🥚 Загадочное яйцо — 💵250", callback_data="buy_egg"),
    )
    return markup

# ===== ФОНОВЫЕ ПОТОКИ =====
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

def run_bot():
    while True:
        try:
            bot.polling(non_stop=True)
        except Exception as e:
            print(f"Ошибка бота: {e}")
            time.sleep(5)

def run_flask():
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# ===== КОМАНДЫ =====

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    bot.send_message(message.chat.id,
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Открой меню команд, чтобы узнать что тут есть.")

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
            hours   = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            bot.send_message(message.chat.id, f"⏳ Следующая награда через {hours:02d}:{minutes:02d}")
            return
    money = random.randint(100, 1000)
    exp   = random.randint(5, 20)
    seeds = random.randint(1, 3)
    bait  = random.randint(1, 3)
    update_daily(user_id, money, exp, seeds, bait, now.isoformat())
    bot.send_message(message.chat.id,
        f"🎁 Ежедневная награда 🎁\n\n"
        f"+ {money} 💵 Денег\n"
        f"+ {exp} 🌟 Опыта\n"
        f"+ {seeds} 🌱 Семян\n"
        f"+ {bait} 🪱 Наживок\n\n"
        f"⏳ Ожидай следующую награду через 24:00")

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
    bot.send_message(message.chat.id,
        f"*👤 {username}*\n\n"
        f"*🏅 Ранг: {rank}*\n"
        f"*🌟 Опыт: {exp}*\n"
        f"*💵 Денег: {money}*",
        parse_mode='Markdown')

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
    msg = bot.send_message(message.chat.id, garden_text(user_id), reply_markup=garden_keyboard(user_id))
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''UPDATE garden SET chat_id=?, message_id=?
                 WHERE user_id=? AND status IN ('growing','ready')''',
              (message.chat.id, msg.message_id, user_id))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['bag'])
def cmd_bag(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    user     = get_user(user_id)
    money    = user[2]
    seeds    = user[4]
    bait     = user[5]
    potato   = user[7]
    carrot   = user[8]
    tomato   = user[9]
    eggplant = user[10]
    pumpkin  = user[11]
    text = f"В мешке у игрока *{username}*:\n\n"
    text += f"💵 Денег: {money}\n🌱 Семян: {seeds}\n🪱 Наживок: {bait}\n- - - - - - - - -\n"
    if potato   > 0: text += f"🥔 × {potato}\n"
    if carrot   > 0: text += f"🥕 × {carrot}\n"
    if tomato   > 0: text += f"🍅 × {tomato}\n"
    if eggplant > 0: text += f"🍆 × {eggplant}\n"
    if pumpkin  > 0: text += f"🎃 × {pumpkin}\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['shop'])
def cmd_shop(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    bot.send_message(message.chat.id, "🛒--- МАГАЗИН ---🛒", reply_markup=shop_keyboard())
@bot.message_handler(commands=['sell'])
def cmd_sell(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    user = get_user(user_id)

    potato   = user[7]
    carrot   = user[8]
    tomato   = user[9]
    eggplant = user[10]
    pumpkin  = user[11]

    prices = {
        "🥔": ("potato",   potato,   8),
        "🥕": ("carrot",   carrot,   15),
        "🍅": ("tomato",   tomato,   20),
        "🍆": ("eggplant", eggplant, 35),
        "🎃": ("pumpkin",  pumpkin,  80),
    }

    total = 0
    sold_lines = []

    conn = sqlite3.connect('game.db')
    c = conn.cursor()

    for emoji, (col, count, price) in prices.items():
        if count > 0:
            earned = count * price
            total += earned
            sold_lines.append(f"{emoji} × {count}  →  {earned} 💵")
            c.execute(f'UPDATE users SET {col}=0 WHERE user_id=?', (user_id,))

    if total == 0:
        conn.close()
        bot.send_message(message.chat.id, "❌ Нечего продавать! Сначала собери урожай в /garden")
        return

    c.execute('UPDATE users SET money=money+? WHERE user_id=?', (total, user_id))
    conn.commit()
    conn.close()

    sold_text = "\n".join(sold_lines)
    bot.send_message(
        message.chat.id,
        f"🛒 *Продано:*\n{sold_text}\n\n"
        f"💰 *Получено: +{total} 💵*",
        parse_mode='Markdown'
    )

ADMIN_USERNAME = "Sid_17jj"

@bot.message_handler(commands=['set'])
def cmd_set(message):
    if message.from_user.username != ADMIN_USERNAME:
        return

    args = message.text.split()
    if len(args) != 4:
        bot.send_message(message.chat.id, "❌ Синтаксис: /set @username поле значение")
        return

    target_username = args[1].replace('@', '')
    field = args[2].lower()
    try:
        value = int(args[3])
    except ValueError:
        bot.send_message(message.chat.id, "❌ Значение должно быть числом!")
        return

    allowed_fields = {
        "money":    "money",
        "exp":      "exp",
        "seeds":    "seeds",
        "bait":     "bait",
        "potato":   "potato",
        "carrot":   "carrot",
        "tomato":   "tomato",
        "eggplant": "eggplant",
        "pumpkin":  "pumpkin",
    }

    if field not in allowed_fields:
        fields_list = ", ".join(allowed_fields.keys())
        bot.send_message(message.chat.id, f"❌ Неизвестное поле!\nДоступные: {fields_list}")
        return

    col = allowed_fields[field]
    user = get_user_by_username(target_username)
    if not user:
        bot.send_message(message.chat.id, f"❌ Игрок @{target_username} не найден!")
        return

    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute(f'UPDATE users SET {col}=? WHERE username=?', (value, target_username))
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id,
        f"✅ Готово!\n"
        f"👤 @{target_username}\n"
        f"📝 {field} → {value}"
        )

@bot.message_handler(commands=['zoo'])
def cmd_zoo(message):
    args = message.text.split()
    if len(args) > 1:
        target = args[1].replace('@', '')
        user = get_user_by_username(target)
        if not user:
            bot.send_message(message.chat.id, "❌ Пользователь не найден!")
            return
        user_id  = user[0]
        username = user[1]
    else:
        user_id  = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        register_user(user_id, username)
    pets = get_pets(user_id)
    if not pets:
        bot.send_message(message.chat.id, f"🐾 У игрока *{username}* нет питомцев!", parse_mode='Markdown')
        return
    rarity_order = [
        "☄️ Секретные","🌈 Хроматические","🔴 Мифические",
        "🟡 Легендарные","🟣 Эпические","🔵 Редкие","🟢 Обычные"
    ]
    grouped = {}
    for pet, rarity, count in pets:
        if rarity not in grouped:
            grouped[rarity] = []
        grouped[rarity].append((pet, count))
    text = f"🐾 Питомцы игрока *{username}* 🐾\n\n"
    for rarity in rarity_order:
        if rarity in grouped:
            emoji = PETS[rarity]["emoji"]
            text += f"{emoji} *{rarity}*\n"
            for pet, count in grouped[rarity]:
                text += f"  {pet} ×{count}\n" if count > 1 else f"  {pet}\n"
            text += "\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ===== КОЛБЭКИ =====

@bot.callback_query_handler(func=lambda call: call.data.startswith('plant_'))
def callback_plant(call):
    user_id = call.from_user.id
    slot = int(call.data.split('_')[1])
    user = get_user(user_id)
    if not user or user[4] < 1:
        bot.answer_callback_query(call.id, "❌ Нет семян!")
        return
    plant_seed(user_id, slot, call.message.chat.id, call.message.message_id)
    bot.edit_message_text(garden_text(user_id), chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=garden_keyboard(user_id))
    bot.answer_callback_query(call.id, "🌱 Семя посажено!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('growing_'))
def callback_growing(call):
    bot.answer_callback_query(call.id, "⏳ Ещё растёт, подожди!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('harvest_'))
def callback_harvest(call):
    user_id = call.from_user.id
    slot = int(call.data.split('_')[1])
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT status, planted_at FROM garden WHERE user_id=? AND slot=?', (user_id, slot))
    row = c.fetchone()
    conn.close()
    if row and row[0] == 'growing':
        planted = datetime.fromisoformat(row[1])
        if datetime.now() - planted >= timedelta(minutes=30):
            mark_slot_ready(user_id, slot, random_vegetable())
        else:
            bot.answer_callback_query(call.id, "⏳ Ещё не выросло!")
            return
    veg = harvest_slot(user_id, slot)
    if veg:
        exp_gain = random.randint(20, 50)
        add_exp(user_id, exp_gain)
        bot.answer_callback_query(call.id, f"+1 {veg}! +{exp_gain} 🌟")
        bot.send_message(call.message.chat.id, f"+1 {veg}  |  +{exp_gain} 🌟 Опыта")
        bot.edit_message_text(garden_text(user_id), chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=garden_keyboard(user_id))
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка!")

@bot.callback_query_handler(func=lambda call: call.data == 'buy_seeds')
def callback_buy_seeds(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    if not user or user[2] < 80:
        bot.answer_callback_query(call.id, "❌ Недостаточно средств! Нужно 💵80")
        return
    spend_money(user_id, 80)
    add_seeds(user_id, 5)
    bot.answer_callback_query(call.id, "✅ Куплено 🌱×5!")
    bot.send_message(call.message.chat.id, "✅ Ты купил *🌱 Семена×5*!", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'buy_bait')
def callback_buy_bait(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    if not user or user[2] < 60:
        bot.answer_callback_query(call.id, "❌ Недостаточно средств! Нужно 💵60")
        return
    spend_money(user_id, 60)
    add_bait(user_id, 5)
    bot.answer_callback_query(call.id, "✅ Куплено 🪱×5!")
    bot.send_message(call.message.chat.id, "✅ Ты купил *🪱 Наживка×5*!", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'buy_egg')
def callback_buy_egg(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    if not user or user[2] < 250:
        bot.answer_callback_query(call.id, "❌ Недостаточно средств! Нужно 💵250")
        return
    spend_money(user_id, 250)
    bot.answer_callback_query(call.id, "🥚 Открываем яйцо...")
    msg = bot.send_message(call.message.chat.id,
        "🥚❔ ЗАГАДОЧНОЕ ЯЙЦО ❔🥚\n\n_Открывается. . ._", parse_mode='Markdown')
    time.sleep(random.uniform(1, 2))
    pet, rarity = random_pet()
    add_pet(user_id, pet, rarity)
    emoji = PETS[rarity]["emoji"]
    bot.delete_message(call.message.chat.id, msg.message_id)
    bot.send_message(call.message.chat.id,
        f"И выпало {pet}\n\n{emoji} *{rarity}*", parse_mode='Markdown')

# ===== ЗАПУСК =====
init_db()
print("Бот запущен!")

threading.Thread(target=garden_checker, daemon=True).start()
threading.Thread(target=run_bot, daemon=True).start()

run_flask()
