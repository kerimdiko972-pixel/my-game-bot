import telebot
import time
import psycopg2
import os
import random
import threading
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from config import BOT_TOKEN

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

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

RANK_REWARDS = {
    "🟢Опытный🟢":      {"money": 500,   "seeds": 3,  "bait": 1,  "eggs": 0},
    "🔵Профи🔵":        {"money": 600,   "seeds": 5,  "bait": 3,  "eggs": 0},
    "🟣Мастер🟣":       {"money": 1000,  "seeds": 8,  "bait": 5,  "eggs": 1},
    "🔴Грандмастер🔴":  {"money": 3500,  "seeds": 10, "bait": 7,  "eggs": 3},
    "💠Легенда💠":      {"money": 7000,  "seeds": 15, "bait": 9,  "eggs": 5},
    "🔱Император🔱":    {"money": 15000, "seeds": 20, "bait": 10, "eggs": 8},
}

RANK_ORDER = [
    (0,      "⚪Новичок⚪"),
    (100,    "🟢Опытный🟢"),
    (500,    "🔵Профи🔵"),
    (2000,   "🟣Мастер🟣"),
    (7000,   "🔴Грандмастер🔴"),
    (20000,  "💠Легенда💠"),
    (100000, "🔱Император🔱"),
]

# Рыбалка
FISH_CATCHES = [
    ("🐟",  540),
    ("🐠",  200),
    ("🦀",  80),
    ("🦞",  70),
    ("🦑",  60),
    ("🦈",  30),
    ("🐉",  17),
    ("🧳",  3),
]
FISH_NAMES = {
    "🐟": "Рыба",
    "🐠": "Тропическая рыба",
    "🦀": "Краб",
    "🦞": "Лобстер",
    "🦑": "Кальмар",
    "🦈": "Акула",
    "🐉": "Драгон-Фиш",
    "🧳": "Сокровище",
}
FISH_COLUMNS = {
    "🐟": "fish",
    "🐠": "tropical_fish",
    "🦀": "crab",
    "🦞": "lobster",
    "🦑": "squid",
    "🦈": "shark",
    "🐉": "dragonfish",
    "🧳": "treasure",
}

def random_fish():
    items = [f for f, _ in FISH_CATCHES]
    weights = [w for _, w in FISH_CATCHES]
    return random.choices(items, weights=weights, k=1)[0]

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

RARITY_SINGULAR = {
    "🟢 Обычные":      "🟢 Обычный",
    "🔵 Редкие":       "🔵 Редкий",
    "🟣 Эпические":    "🟣 Эпический",
    "🟡 Легендарные":  "🟡 Легендарный",
    "🔴 Мифические":   "🔴 Мифический",
    "🌈 Хроматические":"🌈 Хроматический",
    "☄️ Секретные":    "☄️ Секретный",
}

def random_pet():
    groups = list(PETS.keys())
    weights = [PETS[g]["chance"] for g in groups]
    chosen_group = random.choices(groups, weights=weights, k=1)[0]
    return random.choice(PETS[chosen_group]["pets"]), chosen_group

# ===== СЛОТ МАШИНА =====
SLOT_SYMBOLS = [
    ("🍒", 30),
    ("🍋", 25),
    ("🍀", 18),
    ("🔔", 12),
    ("💎", 10),
    ("🌟", 5),
]

SLOT_TWO_MULTIPLIERS = {
    "🍒": 1.5,
    "🍋": 1.8,
    "🍀": 2.0,
    "🔔": 3.0,
    "💎": 4.0,
    "🌟": 5.0,
}

SLOT_THREE_MULTIPLIERS = {
    "🍒": 3.0,
    "🍋": 3.5,
    "🍀": 4.0,
    "🔔": 4.5,
    "💎": 7.0,
    "🌟": 10.0,
}

# Хранилище ставок: {user_id: bet}
pending_bets = {}

def spin_slot():
    symbols = [s for s, _ in SLOT_SYMBOLS]
    weights = [w for _, w in SLOT_SYMBOLS]
    return random.choices(symbols, weights=weights, k=3)

pending_dice = {}
# Структура: {user_id: {'bet': int, 'round': int, 'accumulated': int, 'status': str}}

DICE_MULTIPLIERS = {
    1: 1.3, 2: 1.5, 3: 1.8, 4: 2.2, 5: 2.7,
    6: 3.5, 7: 4.5, 8: 6.0, 9: 8.0, 10: 12.0
}

def dice_grid(current_round, last_result=None, exploded=False):
    cells = []
    for i in range(1, 11):
        if i < current_round:
            cells.append(f"{i} ✅")
        elif i == current_round:
            if exploded:
                cells.append(f"{i} 💣")
            elif last_result is not None:
                cells.append(f"{i} ✅")
            else:
                cells.append(f"{i} ⚪")
        else:
            cells.append(f"{i} ⚪")
    row1 = "  ".join(cells[:5])
    row2 = "  ".join(cells[5:])
    return f"{row1}\n{row2}"

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id       BIGINT PRIMARY KEY,
            username      TEXT,
            money         INTEGER DEFAULT 0,
            exp           INTEGER DEFAULT 0,
            seeds         INTEGER DEFAULT 0,
            bait          INTEGER DEFAULT 0,
            last_daily    TEXT DEFAULT NULL,
            potato        INTEGER DEFAULT 0,
            carrot        INTEGER DEFAULT 0,
            tomato        INTEGER DEFAULT 0,
            eggplant      INTEGER DEFAULT 0,
            pumpkin       INTEGER DEFAULT 0,
            fish          INTEGER DEFAULT 0,
            tropical_fish INTEGER DEFAULT 0,
            crab          INTEGER DEFAULT 0,
            lobster       INTEGER DEFAULT 0,
            squid         INTEGER DEFAULT 0,
            shark         INTEGER DEFAULT 0,
            dragonfish    INTEGER DEFAULT 0,
            treasure      INTEGER DEFAULT 0,
            eggs          INTEGER DEFAULT 0,
            rank_index    INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS garden (
            user_id    BIGINT,
            slot       INTEGER,
            status     TEXT DEFAULT 'empty',
            planted_at TEXT DEFAULT NULL,
            vegetable  TEXT DEFAULT NULL,
            chat_id    BIGINT DEFAULT NULL,
            message_id BIGINT DEFAULT NULL,
            PRIMARY KEY (user_id, slot)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS fishing (
            user_id    BIGINT,
            slot       INTEGER,
            status     TEXT DEFAULT 'empty',
            started_at TEXT DEFAULT NULL,
            chat_id    BIGINT DEFAULT NULL,
            message_id BIGINT DEFAULT NULL,
            PRIMARY KEY (user_id, slot)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS pets (
            id       SERIAL PRIMARY KEY,
            user_id  BIGINT,
            pet      TEXT,
            rarity   TEXT,
            count    INTEGER DEFAULT 1,
            UNIQUE(user_id, pet)
        )
    ''')

    # Добавляем новые слоты грядок если их меньше 10
    try:
        c.execute('SELECT DISTINCT user_id FROM garden')
        existing_users = c.fetchall()
        for (uid,) in existing_users:
            for slot in range(1, 11):
                c.execute('INSERT INTO garden (user_id, slot) VALUES (%s, %s) ON CONFLICT DO NOTHING', (uid, slot))
    except: pass

    conn.commit()
    conn.close()
    print("База данных инициализирована!")

def get_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id=%s', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_username(username):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username=%s', (username,))
    user = c.fetchone()
    conn.close()
    return user

def register_user(user_id, username):
    conn = get_conn()
    c = conn.cursor()
    c.execute('INSERT INTO users (user_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING', (user_id, username))
    for slot in range(1, 11):
        c.execute('INSERT INTO garden (user_id, slot) VALUES (%s, %s) ON CONFLICT DO NOTHING', (user_id, slot))
    for slot in range(1, 5):
        c.execute('INSERT INTO fishing (user_id, slot) VALUES (%s, %s) ON CONFLICT DO NOTHING', (user_id, slot))
    conn.commit()
    conn.close()

def update_daily(user_id, money, exp, seeds, bait, timestamp):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        UPDATE users SET money=money+%s, exp=exp+%s, seeds=seeds+%s, bait=bait+%s, last_daily=%s
        WHERE user_id=%s
    ''', (money, exp, seeds, bait, timestamp, user_id))
    conn.commit()
    conn.close()

def add_exp(user_id, amount, chat_id=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET exp=exp+%s WHERE user_id=%s', (amount, user_id))
    conn.commit()
    conn.close()
    if chat_id:
        check_rank_up(user_id, chat_id)

def spend_money(user_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET money=money-%s WHERE user_id=%s', (amount, user_id))
    conn.commit()
    conn.close()

def add_money(user_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET money=money+%s WHERE user_id=%s', (amount, user_id))
    conn.commit()
    conn.close()

def add_seeds(user_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET seeds=seeds+%s WHERE user_id=%s', (amount, user_id))
    conn.commit()
    conn.close()

def add_bait(user_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET bait=bait+%s WHERE user_id=%s', (amount, user_id))
    conn.commit()
    conn.close()

def add_eggs(user_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET eggs=eggs+%s WHERE user_id=%s', (amount, user_id))
    conn.commit()
    conn.close()

def add_fish_item(user_id, fish_emoji):
    col = FISH_COLUMNS.get(fish_emoji)
    if not col: return
    conn = get_conn()
    c = conn.cursor()
    c.execute(f'UPDATE users SET {col}={col}+1 WHERE user_id=%s', (user_id,))
    conn.commit()
    conn.close()

def check_rank_up(user_id, chat_id):
    user = get_user(user_id)
    if not user: return
    current_exp  = user[3]
    stored_index = user[21] if len(user) > 21 else 0

    for i, (min_exp, rank_name) in enumerate(RANK_ORDER):
        if i == 0: continue
        if current_exp >= min_exp and i > stored_index:
            rewards = RANK_REWARDS.get(rank_name, {})
            money = rewards.get("money", 0)
            seeds = rewards.get("seeds", 0)
            bait  = rewards.get("bait", 0)
            eggs  = rewards.get("eggs", 0)

            conn = get_conn()
            c = conn.cursor()
            c.execute('''UPDATE users SET rank_index=%s, money=money+%s, seeds=seeds+%s,
                         bait=bait+%s, eggs=eggs+%s WHERE user_id=%s''',
                      (i, money, seeds, bait, eggs, user_id))
            conn.commit()
            conn.close()

            reward_lines = [f"💵 +{money}"]
            if seeds: reward_lines.append(f"🌱 +{seeds} Семян")
            if bait:  reward_lines.append(f"🪱 +{bait} Наживок")
            if eggs:  reward_lines.append(f"🥚 +{eggs} Яиц")

            bot.send_message(
                chat_id,
                f"🎉 *Новый ранг!*\n\n"
                f"🏅 Ты достиг ранга:\n*{rank_name}*\n\n"
                f"*Награда:*\n" + "\n".join(reward_lines),
                parse_mode='Markdown'
            )
            stored_index = i

# Рыбалка - вспомогательные функции
def get_fishing(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT slot, status, started_at FROM fishing WHERE user_id=%s ORDER BY slot', (user_id,))
    slots = c.fetchall()
    conn.close()
    return slots

def start_fishing(user_id, slot, chat_id, message_id):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''UPDATE fishing SET status='fishing', started_at=%s, chat_id=%s, message_id=%s
                 WHERE user_id=%s AND slot=%s''', (now, chat_id, message_id, user_id, slot))
    c.execute('UPDATE users SET bait=bait-3 WHERE user_id=%s', (user_id,))
    conn.commit()
    conn.close()

def reset_fishing_slot(user_id, slot):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''UPDATE fishing SET status='empty', started_at=NULL, chat_id=NULL, message_id=NULL
                 WHERE user_id=%s AND slot=%s''', (user_id, slot))
    conn.commit()
    conn.close()

def get_ready_fishing():
    conn = get_conn()
    c = conn.cursor()
    threshold = (datetime.now() - timedelta(hours=1)).isoformat()
    c.execute('''SELECT user_id, slot, chat_id, message_id FROM fishing
                 WHERE status='fishing' AND started_at <= %s''', (threshold,))
    rows = c.fetchall()
    conn.close()
    return rows

def fishing_text(user_id):
    user = get_user(user_id)
    money = user[2] if user else 0
    bait  = user[5] if user else 0
    return (f"🌊 РЫБАЛКА 🎣\n"
            f"💵 Денег: {money}\n"
            f"🪱 Наживок: {bait}\n"
            f"- - - - - - - - - - - -")

def fishing_keyboard(user_id):
    slots = get_fishing(user_id)
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for slot, status, started_at in slots:
        if status == 'empty':
            btn = InlineKeyboardButton("Установить 🪱×3", callback_data=f"fish_start_{slot}")
        elif status == 'fishing':
            started = datetime.fromisoformat(started_at)
            remaining = (started + timedelta(hours=1)) - datetime.now()
            if remaining.total_seconds() <= 0:
                btn = InlineKeyboardButton("✅ Забрать улов", callback_data=f"fish_collect_{slot}")
            else:
                mins = int(remaining.total_seconds() // 60)
                btn = InlineKeyboardButton(f"⏳ {mins} мин.", callback_data=f"fish_wait_{slot}")
        elif status == 'ready':
            btn = InlineKeyboardButton("✅ Забрать улов", callback_data=f"fish_collect_{slot}")
        else:
            btn = InlineKeyboardButton("Установить 🪱×3", callback_data=f"fish_start_{slot}")
        buttons.append(btn)
    markup.add(*buttons)
    return markup

def add_pet(user_id, pet, rarity):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO pets (user_id, pet, rarity, count) VALUES (%s, %s, %s, 1)
        ON CONFLICT(user_id, pet) DO UPDATE SET count=pets.count+1
    ''', (user_id, pet, rarity))
    conn.commit()
    conn.close()

def get_pets(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT pet, rarity, count FROM pets WHERE user_id=%s ORDER BY rarity', (user_id,))
    pets = c.fetchall()
    conn.close()
    return pets

def get_top_users(limit=15):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT username, money FROM users ORDER BY money DESC LIMIT %s', (limit,))
    top = c.fetchall()
    conn.close()
    return top

def get_garden(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT slot, status, planted_at, vegetable FROM garden WHERE user_id=%s ORDER BY slot', (user_id,))
    slots = c.fetchall()
    conn.close()
    return slots

def plant_seed(user_id, slot, chat_id, message_id):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        UPDATE garden SET status='growing', planted_at=%s, vegetable=NULL, chat_id=%s, message_id=%s
        WHERE user_id=%s AND slot=%s
    ''', (now, chat_id, message_id, user_id, slot))
    c.execute('UPDATE users SET seeds=seeds-1 WHERE user_id=%s', (user_id,))
    conn.commit()
    conn.close()

def mark_slot_ready(user_id, slot, vegetable):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE garden SET status='ready', vegetable=%s WHERE user_id=%s AND slot=%s",
              (vegetable, user_id, slot))
    conn.commit()
    conn.close()

def harvest_slot(user_id, slot):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT vegetable, status FROM garden WHERE user_id=%s AND slot=%s', (user_id, slot))
    row = c.fetchone()
    if not row or row[1] != 'ready':
        conn.close()
        return None
    veg = row[0]
    col = VEG_COLUMNS.get(veg)
    if col:
        c.execute(f'UPDATE users SET {col}={col}+1 WHERE user_id=%s', (user_id,))
    c.execute('''
        UPDATE garden SET status='empty', planted_at=NULL, vegetable=NULL, chat_id=NULL, message_id=NULL
        WHERE user_id=%s AND slot=%s
    ''', (user_id, slot))
    conn.commit()
    conn.close()
    return veg

def get_ready_to_harvest():
    conn = get_conn()
    c = conn.cursor()
    threshold = (datetime.now() - timedelta(minutes=30)).isoformat()
    c.execute('''
        SELECT user_id, slot, chat_id, message_id
        FROM garden WHERE status='growing' AND planted_at <= %s
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
    markup = InlineKeyboardMarkup(row_width=5)
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
            # Огород
            ready = get_ready_to_harvest()
            for user_id, slot, chat_id, message_id in ready:
                veg = random_vegetable()
                mark_slot_ready(user_id, slot, veg)
                if chat_id and message_id:
                    try:
                        bot.edit_message_text(garden_text(user_id), chat_id=chat_id,
                            message_id=message_id, reply_markup=garden_keyboard(user_id))
                    except: pass
            # Рыбалка
            ready_fish = get_ready_fishing()
            for user_id, slot, chat_id, message_id in ready_fish:
                conn = get_conn()
                c = conn.cursor()
                c.execute("UPDATE fishing SET status='ready' WHERE user_id=%s AND slot=%s", (user_id, slot))
                conn.commit()
                conn.close()
                if chat_id and message_id:
                    try:
                        bot.edit_message_text(fishing_text(user_id), chat_id=chat_id,
                            message_id=message_id, reply_markup=fishing_keyboard(user_id))
                    except: pass
        except Exception as e:
            print(f"Checker error: {e}")
        time.sleep(30)

def run_bot():
    while True:
        try:
            bot.polling(non_stop=True, skip_pending=True, timeout=30)
        except telebot.apihelper.ApiTelegramException as e:
            if '409' in str(e):
                print("Конфликт! Удаляю webhook и жду 10 сек...")
                try:
                    bot.delete_webhook(drop_pending_updates=True)
                except: pass
                time.sleep(10)
            else:
                print(f"Ошибка API: {e}")
                time.sleep(5)
        except Exception as e:
            print(f"Ошибка бота: {e}")
            time.sleep(5)

def run_flask():
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

@bot.message_handler(commands=['rating_rank'])
def cmd_rating_rank(message):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT username, exp, rank_index FROM users ORDER BY exp DESC LIMIT 15')
    top = c.fetchall()
    conn.close()

    if not top:
        bot.send_message(message.chat.id, "Рейтинг пока пуст!")
        return

    text = "🏆 Рейтинг игроков по рангу 🌟:\n\n"
    for i, (username, exp, rank_index) in enumerate(top, 1):
        rank = get_rank(exp)
        text += f"{i}. {username} — {rank} ({exp} 🌟)\n"

    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['casino'])
def cmd_casino(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    user = get_user(user_id)
    money = user[2] if user else 0

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🎰 Слот машина 🎰", callback_data="casino_slots"),
        InlineKeyboardButton("🎲 Кубик-Бомба 💣",  callback_data="casino_dice"),
    )
    bot.send_message(
        message.chat.id,
        f"🎰💰 - К - А - З - И - Н - О - 💰🎰\n"
        f"💵 Денег: {money}",
        reply_markup=markup
    )

@bot.message_handler(commands=['garden'])
def cmd_garden(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    msg = bot.send_message(message.chat.id, garden_text(user_id), reply_markup=garden_keyboard(user_id))
    conn = get_conn()
    c = conn.cursor()
    c.execute('''UPDATE garden SET chat_id=%s, message_id=%s
                 WHERE user_id=%s AND status IN ('growing','ready')''',
              (message.chat.id, msg.message_id, user_id))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['bag'])
def cmd_bag(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    user = get_user(user_id)

    money      = user[2]
    seeds      = user[4]
    bait       = user[5]
    potato     = user[7]
    carrot     = user[8]
    tomato     = user[9]
    eggplant   = user[10]
    pumpkin    = user[11]
    fish       = user[12] if len(user) > 12 else 0
    t_fish     = user[13] if len(user) > 13 else 0
    crab       = user[14] if len(user) > 14 else 0
    lobster    = user[15] if len(user) > 15 else 0
    squid      = user[16] if len(user) > 16 else 0
    shark      = user[17] if len(user) > 17 else 0
    dragonfish = user[18] if len(user) > 18 else 0
    treasure   = user[19] if len(user) > 19 else 0
    eggs       = user[20] if len(user) > 20 else 0

    sep = "- - - - - - - - - -"
    text = f"В мешке у игрока *{username}*:\n{sep}\n"
    text += f"💵 Денег: {money}\n🌱 Семян: {seeds}\n🪱 Наживок: {bait}\n"

    vegs = []
    if potato:   vegs.append(f"🥔 × {potato}")
    if carrot:   vegs.append(f"🥕 × {carrot}")
    if tomato:   vegs.append(f"🍅 × {tomato}")
    if eggplant: vegs.append(f"🍆 × {eggplant}")
    if pumpkin:  vegs.append(f"🎃 × {pumpkin}")
    if vegs:
        text += sep + "\n" + "\n".join(vegs) + "\n"

    fishes = []
    if fish:       fishes.append(f"🐟 × {fish}")
    if t_fish:     fishes.append(f"🐠 × {t_fish}")
    if crab:       fishes.append(f"🦀 × {crab}")
    if lobster:    fishes.append(f"🦞 × {lobster}")
    if squid:      fishes.append(f"🦑 × {squid}")
    if shark:      fishes.append(f"🦈 × {shark}")
    if dragonfish: fishes.append(f"🐉 × {dragonfish}")
    if fishes:
        text += sep + "\n" + "\n".join(fishes) + "\n"

    specials = []
    if treasure: specials.append(f"🧳 × {treasure}")
    if eggs:     specials.append(f"🥚 × {eggs}")
    if specials:
        text += sep + "\n" + "\n".join(specials) + "\n"

    markup = None
    buttons = []
    if eggs     > 0: buttons.append(InlineKeyboardButton("🥚 ОТКРЫТЬ", callback_data="open_egg_bag"))
    if treasure > 0: buttons.append(InlineKeyboardButton("🧳 ОТКРЫТЬ", callback_data="open_treasure"))
    if buttons:
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(*buttons)

    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['fishing'])
def cmd_fishing(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    msg = bot.send_message(message.chat.id, fishing_text(user_id), reply_markup=fishing_keyboard(user_id))
    conn = get_conn()
    c = conn.cursor()
    c.execute('''UPDATE fishing SET chat_id=%s, message_id=%s
                 WHERE user_id=%s AND status IN ('fishing','ready')''',
              (message.chat.id, msg.message_id, user_id))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['shop'])
def cmd_shop(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    user = get_user(user_id)
    money = user[2] if user else 0
    seeds = user[4] if user else 0
    bait  = user[5] if user else 0
    eggs  = user[20] if user and len(user) > 20 else 0
    sep = "– – – – – – – – – – – – – –"
    bot.send_message(
        message.chat.id,
        f"🛒--- МАГАЗИН ---🛒\n{sep}\n"
        f"💵 Денег: {money}\n"
        f"🌱 Семян: {seeds}\n"
        f"🪱 Наживок: {bait}\n"
        f"🥚 Яиц: {eggs}\n"
        f"{sep}",
        reply_markup=shop_keyboard()
    )

@bot.message_handler(commands=['sell'])
def cmd_sell(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    user = get_user(user_id)

    prices = {
        "🥔": ("potato",        user[7],  8),
        "🥕": ("carrot",        user[8],  15),
        "🍅": ("tomato",        user[9],  20),
        "🍆": ("eggplant",      user[10], 35),
        "🎃": ("pumpkin",       user[11], 80),
        "🐟": ("fish",          user[12], 10),
        "🐠": ("tropical_fish", user[13], 20),
        "🦀": ("crab",          user[14], 45),
        "🦞": ("lobster",       user[15], 70),
        "🦑": ("squid",         user[16], 90),
        "🦈": ("shark",         user[17], 200),
        "🐉": ("dragonfish",    user[18], 500),
    }

    total = 0
    sold_lines = []

    conn = get_conn()
    c = conn.cursor()

    for emoji, (col, count, price) in prices.items():
        if count > 0:
            earned = count * price
            total += earned
            sold_lines.append(f"{emoji} × {count}  →  {earned} 💵")
            c.execute(f'UPDATE users SET {col}=0 WHERE user_id=%s', (user_id,))

    if total == 0:
        conn.close()
        bot.send_message(message.chat.id, "❌ Нечего продавать!\nСобери урожай /garden или улов /fishing")
        return

    c.execute('UPDATE users SET money=money+%s WHERE user_id=%s', (total, user_id))
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

    conn = get_conn()
    c = conn.cursor()
    c.execute(f'UPDATE users SET {col}=%s WHERE username=%s', (value, target_username))
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

# Обработка текстового ввода ставки для кубика (ПЕРВЫМ чтобы не перехватил слот)
@bot.message_handler(func=lambda message: message.from_user.id in pending_dice and pending_dice[message.from_user.id].get('status') == 'waiting')
def handle_dice_bet_input(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    money = user[2] if user else 0
    sep = "- - - - - - - - - - - - - - - - - - -"
    try:
        bet = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введи число! Например: 200")
        return
    if bet < 50:
        bot.send_message(message.chat.id, "❌ Минимальная ставка 💵50!")
        return
    if bet > money:
        bot.send_message(message.chat.id, f"❌ Недостаточно средств! У тебя только 💵{money}")
        return
    spend_money(user_id, bet)
    pending_dice[user_id] = {
        'bet': bet,
        'round': 1,
        'accumulated': bet,
        'status': 'playing'
    }
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎲 Бросить", callback_data="dice_throw"),
        InlineKeyboardButton("❌ Отмена",  callback_data="dice_cancel"),
    )
    bot.send_message(
        message.chat.id,
        f"🎲 – КУБИК - БОМБА – 💣\n{sep}\n"
        f"Ставка: 💵 {bet}\n{sep}\n"
        f"{dice_grid(1)}\n{sep}",
        reply_markup=markup
    )

# Обработка текстового ввода ставки для слотов
@bot.message_handler(func=lambda message: message.from_user.id in pending_bets and pending_bets[message.from_user.id] == 'waiting')
def handle_bet_input(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    money = user[2] if user else 0
    try:
        bet = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введи число! Например: 500")
        return
    if bet < 100:
        bot.send_message(message.chat.id, "❌ Минимальная ставка 💵100!")
        return
    if bet > money:
        bot.send_message(message.chat.id, f"❌ Недостаточно средств! У тебя только 💵{money}")
        return
    spend_money(user_id, bet)
    pending_bets[user_id] = bet
    sep = "– – – – – – – – – – – – – – –"
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Крутить 🎰", callback_data="slot_spin"),
        InlineKeyboardButton("Отмена ❌",  callback_data="slot_cancel"),
    )
    bot.send_message(
        message.chat.id,
        f"🎰 СЛОТ МАШИНА 🎰\n{sep}\n"
        f"Ставка: 💵 {bet}\n{sep}\n\n"
        f"| ❔ | ❔ | ❔ |",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('growing_'))
def callback_growing(call):
    bot.answer_callback_query(call.id, "⏳ Ещё растёт, подожди!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('harvest_'))
def callback_harvest(call):
    user_id = call.from_user.id
    slot = int(call.data.split('_')[1])
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT status, planted_at FROM garden WHERE user_id=%s AND slot=%s', (user_id, slot))
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
        add_exp(user_id, exp_gain, call.message.chat.id)

        bonus_worm = ""
        if random.randint(1, 10) == 1:
            add_bait(user_id, 1)
            bonus_worm = "  +1 🪱"

        bot.answer_callback_query(call.id, f"+1 {veg}! +{exp_gain} 🌟{bonus_worm}")
        bot.send_message(call.message.chat.id, f"+1 {veg}  |  +{exp_gain} 🌟 Опыта{bonus_worm}")
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
    add_eggs(user_id, 1)
    bot.answer_callback_query(call.id, "✅ Яйцо добавлено в мешок!")
    bot.send_message(call.message.chat.id,
        "✅ Куплено *🥚 Загадочное яйцо*!\nОткрой его через */bag*", parse_mode='Markdown')

# --- Рыбалка ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('fish_start_'))
def callback_fish_start(call):
    user_id = call.from_user.id
    slot = int(call.data.split('_')[2])
    user = get_user(user_id)
    if not user or user[5] < 3:
        bot.answer_callback_query(call.id, "❌ Нужно минимум 3 🪱 наживки!")
        return
    start_fishing(user_id, slot, call.message.chat.id, call.message.message_id)
    bot.edit_message_text(fishing_text(user_id), chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=fishing_keyboard(user_id))
    bot.answer_callback_query(call.id, "🎣 Удочка заброшена!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('fish_wait_'))
def callback_fish_wait(call):
    bot.answer_callback_query(call.id, "⏳ Ещё не время! Подожди.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('fish_collect_'))
def callback_fish_collect(call):
    user_id = call.from_user.id
    slot = int(call.data.split('_')[2])

    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT status, started_at FROM fishing WHERE user_id=%s AND slot=%s', (user_id, slot))
    row = c.fetchone()
    conn.close()

    if row and row[0] == 'fishing':
        started = datetime.fromisoformat(row[1])
        if datetime.now() - started < timedelta(hours=1):
            bot.answer_callback_query(call.id, "⏳ Ещё не готово!")
            return

    catch = [random_fish() for _ in range(3)]
    exp_gain = random.randint(50, 100)

    for fish_item in catch:
        add_fish_item(user_id, fish_item)
    add_exp(user_id, exp_gain, call.message.chat.id)
    reset_fishing_slot(user_id, slot)

    lines = "\n".join([f"+ {f} {FISH_NAMES[f]}" for f in catch])
    bot.answer_callback_query(call.id, "🎣 Улов собран!")
    bot.send_message(
        call.message.chat.id,
        f"🎣 *Выловлено:*\n{lines}\n+ {exp_gain} 🌟 Опыта",
        parse_mode='Markdown'
    )
    bot.edit_message_text(fishing_text(user_id), chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=fishing_keyboard(user_id))

# --- Открытие яйца из мешка ---
@bot.callback_query_handler(func=lambda call: call.data == 'open_egg_bag')
def callback_open_egg_bag(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    eggs = user[20] if len(user) > 20 else 0
    if eggs < 1:
        bot.answer_callback_query(call.id, "❌ Нет яиц!")
        return
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET eggs=eggs-1 WHERE user_id=%s', (user_id,))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "🥚 Открываем...")
    msg = bot.send_message(call.message.chat.id,
        "🥚❔ ЗАГАДОЧНОЕ ЯЙЦО ❔🥚\n\n_Открывается. . ._", parse_mode='Markdown')
    time.sleep(random.uniform(1, 2))
    pet, rarity = random_pet()
    add_pet(user_id, pet, rarity)
    bot.delete_message(call.message.chat.id, msg.message_id)
    bot.send_message(
        call.message.chat.id,
        f"_✨ И выпал. . ._\n\n*{RARITY_SINGULAR.get(rarity, rarity)} {pet}*",
        parse_mode='Markdown'
    )

# --- Открытие сокровища ---
@bot.callback_query_handler(func=lambda call: call.data == 'open_treasure')
def callback_open_treasure(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    treasure = user[19] if len(user) > 19 else 0
    if treasure < 1:
        bot.answer_callback_query(call.id, "❌ Нет сокровища!")
        return

    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET treasure=treasure-1 WHERE user_id=%s', (user_id,))
    conn.commit()
    conn.close()

    bot.answer_callback_query(call.id, "🧳 Открываем сокровище...")
    msg = bot.send_message(call.message.chat.id,
        "🧳 *СОКРОВИЩЕ* 🧳\n\n_Открывается. . ._", parse_mode='Markdown')
    time.sleep(random.uniform(1, 2))

    tiers = [(50, 100, 500, 1), (35, 501, 1000, 3), (10, 1001, 3000, 5), (5, 3001, 10000, 8)]
    weights = [t[0] for t in tiers]
    tier = random.choices(tiers, weights=weights, k=1)[0]
    _, min_m, max_m, egg_count = tier

    if random.random() < 0.5:
        reward_money = random.randint(min_m, max_m)
        add_money(user_id, reward_money)
        result_text = f"💵 +{reward_money} Монет!"
    else:
        add_eggs(user_id, egg_count)
        result_text = f"🥚 +{egg_count} Яиц!"

    bot.delete_message(call.message.chat.id, msg.message_id)
    bot.send_message(call.message.chat.id,
        f"🧳 *Сокровище открыто!*\n\n{result_text}", parse_mode='Markdown')

# --- Казино ---
@bot.callback_query_handler(func=lambda call: call.data == 'casino_slots')
def callback_casino_slots(call):
    user_id = call.from_user.id
    pending_dice.pop(user_id, None)
    pending_bets[user_id] = 'waiting'
    sep = "– – – – – – – – – – – – – – –"
    bot.send_message(
        call.message.chat.id,
        f"🎰 СЛОТ МАШИНА 🎰\n{sep}\n"
        f"Напиши ставку 💵 денег которую хочешь поставить на игру (мин. 100)."
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'slot_cancel')
def callback_slot_cancel(call):
    user_id = call.from_user.id
    bet = pending_bets.pop(user_id, 0)
    if isinstance(bet, int) and bet > 0:
        add_money(user_id, bet)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(
            call.message.chat.id,
            f"Игра отменена ❌\nВозвращённая ставка: +💵{bet}"
        )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'slot_spin')
def callback_slot_spin(call):
    user_id = call.from_user.id
    bet = pending_bets.get(user_id)

    if not isinstance(bet, int) or bet <= 0:
        bot.answer_callback_query(call.id, "❌ Ставка не найдена!")
        return

    bot.answer_callback_query(call.id)
    sep = "– – – – – – – – – – – – – – –"
    slots = spin_slot()

    try:
        bot.edit_message_text(
            f"🎰 СЛОТ МАШИНА 🎰\n{sep}\nСтавка: 💵 {bet}\n{sep}\n\n| {slots[0]} | ❔ | ❔ |",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        time.sleep(0.7)
        bot.edit_message_text(
            f"🎰 СЛОТ МАШИНА 🎰\n{sep}\nСтавка: 💵 {bet}\n{sep}\n\n| {slots[0]} | {slots[1]} | ❔ |",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        time.sleep(0.7)
        bot.edit_message_text(
            f"🎰 СЛОТ МАШИНА 🎰\n{sep}\nСтавка: 💵 {bet}\n{sep}\n\n| {slots[0]} | {slots[1]} | {slots[2]} |",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        time.sleep(0.5)
    except Exception as e:
        print(f"Анимация ошибка: {e}")

    winnings = 0
    result_text = ""

    counts = {}
    for s in slots:
        counts[s] = counts.get(s, 0) + 1

    triple = None
    double = None
    for symbol, count in counts.items():
        if count == 3:
            triple = symbol
        elif count == 2:
            double = symbol

    if triple:
        multiplier = SLOT_THREE_MULTIPLIERS[triple]
        winnings = int(bet * multiplier)
        result_text = (
            f"TRI {triple}{triple}{triple}\n"
            f"💵{bet} x {multiplier} = {winnings}\n\n"
            f"Получено: +{winnings} 💵"
        )
    elif double:
        multiplier = SLOT_TWO_MULTIPLIERS[double]
        winnings = int(bet * multiplier)
        result_text = (
            f"Комбо из двух {double}{double}\n"
            f"💵{bet} x {multiplier} = {winnings}\n\n"
            f"Получено: +{winnings} 💵"
        )
    else:
        result_text = f"Нет совпадений\n\nПотеряно: -{bet} 💵"

    if winnings > 0:
        add_money(user_id, winnings)

    pending_bets.pop(user_id, None)

    user_now = get_user(user_id)
    money_now = user_now[2] if user_now else 0

    markup = None
    if winnings == 0:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("❌ Закрыть", callback_data="slot_close"))

    try:
        bot.edit_message_text(
            f"🎰 СЛОТ МАШИНА 🎰\n{sep}\n"
            f"Ставка: 💵 {bet}\n{sep}\n\n"
            f"| {slots[0]} | {slots[1]} | {slots[2]} |\n\n"
            f"{result_text}\n\n"
            f"💵 Баланс: {money_now}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        print(f"Финал ошибка: {e}")
        bot.send_message(
            call.message.chat.id,
            f"🎰 Результат:\n| {slots[0]} | {slots[1]} | {slots[2]} |\n\n"
            f"{result_text}\n\n💵 Баланс: {money_now}",
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data == 'slot_close')
def callback_slot_close(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.answer_callback_query(call.id)

# --- Кубик-Бомба ---
@bot.callback_query_handler(func=lambda call: call.data == 'casino_dice')
def callback_casino_dice(call):
    user_id = call.from_user.id
    sep = "- - - - - - - - - - - - - - - - - - -"
    pending_bets.pop(user_id, None)
    pending_dice[user_id] = {'status': 'waiting'}
    bot.send_message(
        call.message.chat.id,
        f"🎲 – КУБИК - БОМБА – 💣\n{sep}\n"
        f"Напиши ставку 💵 денег которую хочешь поставить на игру и начать (мин. 50)."
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'dice_cancel')
def callback_dice_cancel(call):
    user_id = call.from_user.id
    data = pending_dice.pop(user_id, None)

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

    if data and data.get('status') == 'playing' and data.get('bet'):
        bet = int(data['bet'])
        conn = get_conn()
        c = conn.cursor()
        c.execute('UPDATE users SET money=money+%s WHERE user_id=%s', (bet, user_id))
        conn.commit()
        conn.close()
        bot.send_message(call.message.chat.id,
            f"Игра отменена ❌\nВозвращённая ставка: +💵 {bet}")
    else:
        bot.send_message(call.message.chat.id, "Игра отменена ❌")

    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'dice_take')
def callback_dice_take(call):
    user_id = call.from_user.id
    data = pending_dice.pop(user_id, None)
    if not data:
        bot.answer_callback_query(call.id, "❌ Игра не найдена!")
        return
    winnings = int(data['accumulated'])
    add_money(user_id, winnings)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.send_message(
        call.message.chat.id,
        f"💰 Ты забрал выигрыш!\n\n+💵 {winnings}"
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'dice_throw')
def callback_dice_throw(call):
    user_id = call.from_user.id
    data = pending_dice.get(user_id)
    sep = "- - - - - - - - - - - - - - - - - - -"

    if not data or data.get('status') != 'playing':
        bot.answer_callback_query(call.id, "❌ Игра не найдена!")
        return

    bot.answer_callback_query(call.id)

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

    dice_msg = bot.send_dice(call.message.chat.id, emoji="🎲")
    dice_value = dice_msg.dice.value
    time.sleep(6.0)

    current_round = data['round']
    bet = data['bet']
    multiplier = DICE_MULTIPLIERS[current_round]
    accumulated = data['accumulated']

    if dice_value >= 3:
        new_accumulated = int(accumulated * multiplier)

        lucky = False
        if dice_value == 6:
            lucky = True
            bonus = int(new_accumulated * 0.10)
            new_accumulated += bonus

        pending_dice[user_id]['accumulated'] = new_accumulated
        pending_dice[user_id]['round'] = current_round + 1

        lucky_text = "\n✨ СЧАСТЛИВЫЙ БРОСОК! +10% к выигрышу" if lucky else ""

        if current_round == 10:
            pending_dice.pop(user_id, None)
            add_money(user_id, new_accumulated)
            bot.send_message(
                call.message.chat.id,
                f"| Выпало: {dice_value} |{lucky_text}\n\n"
                f"🎉 10/10 раундов пройдено!\n\n"
                f"💰 Автовыигрыш: +💵 {new_accumulated}\n\n"
                f"{dice_grid(10, last_result=dice_value)}\n{sep}"
            )
        else:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("🎲 Бросить", callback_data="dice_throw"),
                InlineKeyboardButton("💵 Забрать", callback_data="dice_take"),
            )
            bot.send_message(
                call.message.chat.id,
                f"| Выпало: {dice_value} |{lucky_text}\n\n"
                f"💵 {accumulated} × {multiplier} = {new_accumulated}\n\n"
                f"{dice_grid(current_round, last_result=dice_value)}\n{sep}",
                reply_markup=markup
            )
    else:
        pending_dice.pop(user_id, None)
        bot.send_message(
            call.message.chat.id,
            f"| Выпало: {dice_value} |\n\n"
            f"❌💥 Проигрыш\n\n"
            f"- {bet} 💵\n\n"
            f"{dice_grid(current_round, exploded=True)}\n{sep}"
        )

# ===== БИТВА =====
import uuid as _uuid

MIN_BATTLE_STAKE  = 50
MAX_BATTLE_STAKE  = 100_000
BATTLE_INVITE_TIMEOUT = 60   # сек — время на принятие приглашения
BATTLE_TURN_TIMEOUT   = 90   # сек — время на ход
BATTLE_HP = 20

# In-memory множество user_id кто сейчас в бою (для быстрой проверки блокировки)
active_battle_users = set()

# ── Таблицы ──────────────────────────────────────────────────────────────────
def init_battle_tables():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS battles (
            id              TEXT PRIMARY KEY,
            player_a_id     BIGINT,
            player_a_name   TEXT,
            player_b_id     BIGINT,
            player_b_name   TEXT,
            stake           INTEGER,
            state           TEXT DEFAULT 'invited',
            turn_player_id  BIGINT DEFAULT NULL,
            hp_a            INTEGER DEFAULT 20,
            hp_b            INTEGER DEFAULT 20,
            shield_a        BOOLEAN DEFAULT FALSE,
            shield_b        BOOLEAN DEFAULT FALSE,
            chat_id         BIGINT,
            invite_msg_id   BIGINT DEFAULT NULL,
            invited_at      TEXT,
            last_action_at  TEXT DEFAULT NULL,
            finished_at     TEXT DEFAULT NULL
        )
    ''')
    # Восстановить active_battle_users после перезапуска
    c.execute("SELECT player_a_id, player_b_id FROM battles WHERE state IN ('invited','active')")
    rows = c.fetchall()
    for a_id, b_id in rows:
        active_battle_users.add(a_id)
        active_battle_users.add(b_id)
    conn.commit()
    conn.close()

# ── Колонки battles ───────────────────────────────────────────────────────────
# 0:id  1:player_a_id  2:player_a_name  3:player_b_id  4:player_b_name
# 5:stake  6:state  7:turn_player_id  8:hp_a  9:hp_b
# 10:shield_a  11:shield_b  12:chat_id  13:invite_msg_id
# 14:invited_at  15:last_action_at  16:finished_at

# ── CRUD ──────────────────────────────────────────────────────────────────────
def get_battle(battle_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM battles WHERE id=%s', (battle_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_active_battle_for_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT * FROM battles WHERE (player_a_id=%s OR player_b_id=%s)
                 AND state IN ('invited','active')''', (user_id, user_id))
    row = c.fetchone()
    conn.close()
    return row

def create_battle(battle_id, a_id, a_name, b_id, b_name, stake, chat_id, invite_msg_id):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO battles
                 (id, player_a_id, player_a_name, player_b_id, player_b_name,
                  stake, state, chat_id, invite_msg_id, invited_at)
                 VALUES (%s,%s,%s,%s,%s,%s,'invited',%s,%s,%s)''',
              (battle_id, a_id, a_name, b_id, b_name, stake, chat_id, invite_msg_id, now))
    conn.commit()
    conn.close()
    active_battle_users.add(a_id)
    active_battle_users.add(b_id)

def cancel_battle(battle_id, a_id=None, b_id=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE battles SET state='cancelled', finished_at=%s WHERE id=%s",
              (datetime.now().isoformat(), battle_id))
    conn.commit()
    conn.close()
    if a_id: active_battle_users.discard(a_id)
    if b_id: active_battle_users.discard(b_id)

def activate_battle(battle_id, turn_player_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''UPDATE battles SET state='active', turn_player_id=%s,
                 last_action_at=%s WHERE id=%s''',
              (turn_player_id, datetime.now().isoformat(), battle_id))
    conn.commit()
    conn.close()

def update_battle_state(battle_id, next_turn_id, hp_a, hp_b, shield_a, shield_b):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''UPDATE battles SET turn_player_id=%s, hp_a=%s, hp_b=%s,
                 shield_a=%s, shield_b=%s, last_action_at=%s WHERE id=%s''',
              (next_turn_id, hp_a, hp_b, shield_a, shield_b,
               datetime.now().isoformat(), battle_id))
    conn.commit()
    conn.close()

def finish_battle_db(battle_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE battles SET state='finished', finished_at=%s WHERE id=%s",
              (datetime.now().isoformat(), battle_id))
    conn.commit()
    conn.close()

# ── UI хелперы ────────────────────────────────────────────────────────────────
SEP_B = "– – – – – – – – – – – – – – – –"

def battle_status_text(a_name, b_name, stake, turn_name, hp_a, hp_b, shield_a, shield_b):
    sh_a = " 🛡️" if shield_a else ""
    sh_b = " 🛡️" if shield_b else ""
    return (
        f"{SEP_B}\n"
        f"⚔️ СРАЖЕНИЕ: *{a_name}*  VS  *{b_name}* ⚔️\n"
        f"{SEP_B}\n"
        f"Выигрыш: 💵 *{stake * 2}*\n"
        f"{SEP_B}\n"
        f"⏳ Ход: @{turn_name}\n"
        f"{SEP_B}\n"
        f"❤️{sh_a} {a_name}: {hp_a}/{BATTLE_HP}\n"
        f"❤️{sh_b} {b_name}: {hp_b}/{BATTLE_HP}\n"
        f"{SEP_B}"
    )

def battle_action_keyboard(battle_id):
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("🗡️ АТАКОВАТЬ",  callback_data=f"ba_atk_{battle_id}"),
        InlineKeyboardButton("🛡️ ЗАЩИЩАТЬСЯ", callback_data=f"ba_def_{battle_id}"),
        InlineKeyboardButton("💥 КРИТ-УДАР",  callback_data=f"ba_crt_{battle_id}"),
    )
    return markup

def battle_close_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Закрыть", callback_data="battle_close"))
    return markup

# ── Завершение боя ────────────────────────────────────────────────────────────
def end_battle(battle, winner_id, loser_id, winner_name, loser_name, chat_id, forfeit=False):
    battle_id = battle[0]
    a_id      = battle[1]
    b_id      = battle[3]
    stake     = battle[5]
    prize     = stake * 2

    add_money(winner_id, prize)
    finish_battle_db(battle_id)
    active_battle_users.discard(a_id)
    active_battle_users.discard(b_id)

    winner_exp = random.randint(100, 200)
    loser_exp  = random.randint(5, 20)
    add_exp(winner_id, winner_exp, chat_id)
    add_exp(loser_id,  loser_exp,  chat_id)

    extra = "\n⏰ Противник не успел сделать ход — форфейт!" if forfeit else ""

    bot.send_message(
        chat_id,
        f"🏳️💥 СРАЖЕНИЕ ОКОНЧЕНО 💥🏳️\n\n"
        f"🏆 @{winner_name} победил!{extra}\n"
        f"Он выиграл: 💵 {prize}\n\n"
        f"Получено опыта:\n"
        f"🌟 @{winner_name}: +{winner_exp}\n"
        f"🌟 @{loser_name}: +{loser_exp}",
        reply_markup=battle_close_keyboard(),
        parse_mode='Markdown'
    )

# ── Обработка действия ────────────────────────────────────────────────────────
def process_battle_action(call, battle_id, action):
    user_id = call.from_user.id
    battle  = get_battle(battle_id)

    if not battle or battle[6] != 'active':
        bot.answer_callback_query(call.id, "❌ Бой уже завершён!")
        return
    if user_id != battle[7]:
        bot.answer_callback_query(call.id, "⏳ Сейчас не твой ход!")
        return

    a_id      = battle[1];  a_name = battle[2]
    b_id      = battle[3];  b_name = battle[4]
    stake     = battle[5]
    hp_a      = battle[8];  hp_b   = battle[9]
    shield_a  = battle[10]; shield_b = battle[11]
    chat_id   = battle[12]

    is_a      = (user_id == a_id)
    att_name  = a_name if is_a else b_name
    def_name  = b_name if is_a else a_name

    bot.answer_callback_query(call.id)

    # ── Атака ──────────────────────────────────────────────────────────────
    if action == 'attack':
        bot.send_message(chat_id, f"🗡️ *@{att_name}* атакует!", parse_mode='Markdown')
        dice_msg  = bot.send_dice(chat_id, emoji="🎲")
        dice_val  = dice_msg.dice.value
        time.sleep(4.5)

        damage = dice_val
        if is_a and shield_b:
            damage = damage // 2; shield_b = False
        elif not is_a and shield_a:
            damage = damage // 2; shield_a = False

        if is_a: hp_b = max(0, hp_b - damage)
        else:    hp_a = max(0, hp_a - damage)

        bot.send_message(chat_id,
            f"🗡️ *@{att_name}* атаковал на *{dice_val}* урона!\n"
            f"❤️ {a_name}: {hp_a}/{BATTLE_HP} | {b_name}: {hp_b}/{BATTLE_HP}",
            parse_mode='Markdown')

    # ── Защита ─────────────────────────────────────────────────────────────
    elif action == 'defend':
        if is_a: shield_a = True
        else:    shield_b = True
        bot.send_message(chat_id,
            f"🛡️ *@{att_name}* встаёт в защиту!\n"
            f"Следующий урон по нему будет уменьшен вдвое.",
            parse_mode='Markdown')
        bot.send_message(chat_id,
            f"🛡️ @{att_name} защищается — @{def_name}, действуй!",
            parse_mode='Markdown')

    # ── Крит ───────────────────────────────────────────────────────────────
    elif action == 'crit':
        bot.send_message(chat_id,
            f"💥 *@{att_name}* пытается нанести КРИТ-УДАР!", parse_mode='Markdown')
        dice_msg = bot.send_dice(chat_id, emoji="🎲")
        dice_val = dice_msg.dice.value
        time.sleep(4.5)

        if dice_val >= 5:
            damage      = dice_val * 2
            result_text = f"💥 ПОПАЛ! Выпало {dice_val} → урон *{damage}* (×2)"
        else:
            damage      = 0
            result_text = f"💨 Промах! Выпало {dice_val} — мимо"

        if damage > 0:
            if is_a and shield_b:
                damage = damage // 2; shield_b = False
            elif not is_a and shield_a:
                damage = damage // 2; shield_a = False

        if is_a: hp_b = max(0, hp_b - damage)
        else:    hp_a = max(0, hp_a - damage)

        bot.send_message(chat_id,
            f"💥 *@{att_name}* применил КРИТ-УДАР: {result_text}\n"
            f"❤️ {a_name}: {hp_a}/{BATTLE_HP} | {b_name}: {hp_b}/{BATTLE_HP}",
            parse_mode='Markdown')

    # ── Проверка смерти ────────────────────────────────────────────────────
    if hp_a <= 0 or hp_b <= 0:
        if hp_a <= 0:
            winner_id, loser_id     = b_id, a_id
            winner_name, loser_name = b_name, a_name
        else:
            winner_id, loser_id     = a_id, b_id
            winner_name, loser_name = a_name, b_name
        end_battle(battle, winner_id, loser_id, winner_name, loser_name, chat_id)
        return

    # ── Переключить ход ────────────────────────────────────────────────────
    next_id   = b_id   if is_a else a_id
    next_name = b_name if is_a else a_name
    update_battle_state(battle_id, next_id, hp_a, hp_b, shield_a, shield_b)

    bot.send_message(
        chat_id,
        battle_status_text(a_name, b_name, stake, next_name, hp_a, hp_b, shield_a, shield_b),
        reply_markup=battle_action_keyboard(battle_id),
        parse_mode='Markdown'
    )

# ── Фоновый поток таймаутов ───────────────────────────────────────────────────
def battle_checker():
    while True:
        try:
            now = datetime.now()

            # --- Таймаут приглашения ---
            conn = get_conn()
            c = conn.cursor()
            inv_thr = (now - timedelta(seconds=BATTLE_INVITE_TIMEOUT)).isoformat()
            c.execute("SELECT * FROM battles WHERE state='invited' AND invited_at <= %s", (inv_thr,))
            expired_invites = c.fetchall()
            conn.close()

            for b in expired_invites:
                bid   = b[0]; a_id = b[1]; a_name = b[2]; b_id = b[3]
                cid   = b[12]; imid = b[13]
                cancel_battle(bid, a_id, b_id)
                try:
                    if imid: bot.delete_message(cid, imid)
                except: pass
                try:
                    bot.send_message(cid,
                        f"⏰ Приглашение на битву от *{a_name}* истекло.",
                        parse_mode='Markdown')
                except: pass

            # --- Таймаут хода ---
            conn = get_conn()
            c = conn.cursor()
            turn_thr = (now - timedelta(seconds=BATTLE_TURN_TIMEOUT)).isoformat()
            c.execute("SELECT * FROM battles WHERE state='active' AND last_action_at <= %s", (turn_thr,))
            expired_turns = c.fetchall()
            conn.close()

            for b in expired_turns:
                bid    = b[0]
                a_id   = b[1]; a_name = b[2]
                bpl_id = b[3]; b_name = b[4]
                turn   = b[7]; cid    = b[12]
                if turn == a_id:
                    winner_id, loser_id     = bpl_id, a_id
                    winner_name, loser_name = b_name, a_name
                else:
                    winner_id, loser_id     = a_id, bpl_id
                    winner_name, loser_name = a_name, b_name
                try:
                    end_battle(b, winner_id, loser_id, winner_name, loser_name, cid, forfeit=True)
                except: pass

        except Exception as e:
            print(f"Battle checker error: {e}")
        time.sleep(10)

# ── КОМАНДА /battle ───────────────────────────────────────────────────────────
@bot.message_handler(commands=['battle'])
def cmd_battle(message):
    user_id  = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)

    args = message.text.split()
    if len(args) < 3:
        bot.send_message(message.chat.id,
            "❌ Используй: /battle @username ставка\nПример: /battle @player123 200")
        return

    target_name = args[1].replace('@', '')
    try:
        stake = int(args[2])
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ставка должна быть числом!")
        return

    if stake < MIN_BATTLE_STAKE:
        bot.send_message(message.chat.id, f"❌ Минимальная ставка: 💵{MIN_BATTLE_STAKE}")
        return
    if stake > MAX_BATTLE_STAKE:
        bot.send_message(message.chat.id, f"❌ Максимальная ставка: 💵{MAX_BATTLE_STAKE:,}")
        return

    user_a = get_user(user_id)
    if not user_a or user_a[2] < stake:
        bot.send_message(message.chat.id,
            f"❌ Недостаточно средств! У тебя только 💵{user_a[2] if user_a else 0}")
        return

    if user_id in active_battle_users:
        bot.send_message(message.chat.id, "❌ Ты уже в сражении! Заверши текущий бой.")
        return

    user_b = get_user_by_username(target_name)
    if not user_b:
        bot.send_message(message.chat.id, f"❌ Игрок @{target_name} не найден!")
        return

    b_id   = user_b[0]
    b_name = user_b[1]

    if b_id == user_id:
        bot.send_message(message.chat.id, "❌ Нельзя вызвать самого себя!")
        return

    if b_id in active_battle_users:
        bot.send_message(message.chat.id, f"❌ Игрок @{target_name} уже в сражении!")
        return

    battle_id = _uuid.uuid4().hex[:8]

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Принять ⚔️",   callback_data=f"battle_acc_{battle_id}"),
        InlineKeyboardButton("Отказаться ❌", callback_data=f"battle_dec_{battle_id}"),
    )
    invite_msg = bot.send_message(
        message.chat.id,
        f"⚔️ Игрок *{username}* приглашает *@{target_name}* на битву ⚔️\n\n"
        f"Ставка: 💵 *{stake}*",
        reply_markup=markup,
        parse_mode='Markdown'
    )
    create_battle(battle_id, user_id, username, b_id, b_name, stake,
                  message.chat.id, invite_msg.message_id)

# Блокировать команды во время боя (кроме /battle, /start)
BATTLE_ALLOWED_COMMANDS = {'/battle', '/start'}
@bot.message_handler(func=lambda msg: (
    msg.text and msg.text.startswith('/') and
    msg.text.split()[0].split('@')[0] not in BATTLE_ALLOWED_COMMANDS and
    msg.from_user.id in active_battle_users
))
def cmd_blocked_in_battle(message):
    bot.send_message(message.chat.id,
        "⚔️ Ты сейчас в сражении!\nЗаверши бой прежде чем использовать другие команды.")

# ── КОЛБЭКИ БИТВЫ ─────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data.startswith('battle_acc_'))
def callback_battle_accept(call):
    battle_id = call.data[len('battle_acc_'):]
    user_id   = call.from_user.id
    battle    = get_battle(battle_id)

    if not battle or battle[6] != 'invited':
        bot.answer_callback_query(call.id, "❌ Приглашение уже недоступно!")
        return
    if user_id != battle[3]:
        bot.answer_callback_query(call.id, "❌ Это приглашение не для тебя!")
        return

    a_id   = battle[1]; a_name = battle[2]
    b_id   = battle[3]; b_name = battle[4]
    stake  = battle[5]; chat_id = battle[12]; imid = battle[13]

    user_a = get_user(a_id)
    user_b = get_user(b_id)

    if not user_a or user_a[2] < stake:
        cancel_battle(battle_id, a_id, b_id)
        try: bot.delete_message(chat_id, imid)
        except: pass
        bot.send_message(chat_id,
            f"⚠️ Бой отменён — у *{a_name}* недостаточно средств (нужно 💵{stake})",
            parse_mode='Markdown')
        bot.answer_callback_query(call.id)
        return

    if not user_b or user_b[2] < stake:
        cancel_battle(battle_id, a_id, b_id)
        try: bot.delete_message(chat_id, imid)
        except: pass
        bot.send_message(chat_id,
            f"⚠️ Бой отменён — у *{b_name}* недостаточно средств (нужно 💵{stake})",
            parse_mode='Markdown')
        bot.answer_callback_query(call.id)
        return

    spend_money(a_id, stake)
    spend_money(b_id, stake)

    try: bot.delete_message(chat_id, imid)
    except: pass

    bot.send_message(chat_id,
        f"✅ *{b_name}* принял заявку на сражение!",
        parse_mode='Markdown')

    turn_id   = random.choice([a_id, b_id])
    turn_name = a_name if turn_id == a_id else b_name

    activate_battle(battle_id, turn_id)

    bot.send_message(
        chat_id,
        battle_status_text(a_name, b_name, stake, turn_name,
                           BATTLE_HP, BATTLE_HP, False, False),
        reply_markup=battle_action_keyboard(battle_id),
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('battle_dec_'))
def callback_battle_decline(call):
    battle_id = call.data[len('battle_dec_'):]
    user_id   = call.from_user.id
    battle    = get_battle(battle_id)

    if not battle or battle[6] != 'invited':
        bot.answer_callback_query(call.id, "❌ Приглашение уже недоступно!")
        return
    if user_id != battle[3]:
        bot.answer_callback_query(call.id, "❌ Это приглашение не для тебя!")
        return

    a_id   = battle[1]; a_name = battle[2]
    b_id   = battle[3]; b_name = battle[4]
    chat_id = battle[12]; imid = battle[13]

    cancel_battle(battle_id, a_id, b_id)
    try: bot.delete_message(chat_id, imid)
    except: pass

    bot.send_message(chat_id,
        f"❌ *{b_name}* отказался участвовать в битве с *{a_name}*",
        parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('ba_atk_'))
def callback_battle_attack(call):
    process_battle_action(call, call.data[len('ba_atk_'):], 'attack')

@bot.callback_query_handler(func=lambda call: call.data.startswith('ba_def_'))
def callback_battle_defend(call):
    process_battle_action(call, call.data[len('ba_def_'):], 'defend')

@bot.callback_query_handler(func=lambda call: call.data.startswith('ba_crt_'))
def callback_battle_crit(call):
    process_battle_action(call, call.data[len('ba_crt_'):], 'crit')

@bot.callback_query_handler(func=lambda call: call.data == 'battle_close')
def callback_battle_close(call):
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.answer_callback_query(call.id)

# ===== ЗАПУСК =====
init_db()
init_battle_tables()

bot.delete_webhook(drop_pending_updates=True)
time.sleep(3)
print("Бот запущен!")

threading.Thread(target=garden_checker, daemon=True).start()
threading.Thread(target=battle_checker, daemon=True).start()
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
print(f"Поток бота создан: {bot_thread.is_alive()}")

run_flask()
