import telebot
import time
import psycopg2
import psycopg2.extras
import os
import random
import threading
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from config import BOT_TOKEN
from slot_machine import sm_spin, sm_check_wins, sm_render_grid, sm_win_line, sm_total
from fishing_handlers import register_fishing_handlers, traps_checker_loop
from garden_handlers import register_garden_handlers
from garden_buildings import register_buildings_handlers, buildings_checker_loop

bot = telebot.TeleBot(BOT_TOKEN, threaded=False, use_class_middlewares=True)
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

ACHIEVEMENTS = {
    # Ключ: (название, колонка_в_users, [пороги], [награды])
    # награда = {'money': X, 'exp': X, 'eggs': X}
    'vegs_harvested': {
        'title': '🥕 Сбор урожая',
        'levels': [
            (50,   "Новичок на грядке",  {'money': 500,   'exp': 200}),
            (150,  "Любитель урожая",    {'money': 1200,  'exp': 450}),
            (500,  "Фермер деревни",     {'money': 3500,  'exp': 1200, 'eggs': 1}),
            (1500, "Хозяин огорода",     {'money': 9000,  'exp': 2500, 'eggs': 2}),
            (5000, "Легенда грядок",     {'money': 25000, 'exp': 7000, 'eggs': 4}),
        ]
    },
    'seeds_planted': {
        'title': '🌱 Посев семян',
        'levels': [
            (20,   "Первая посадка",     {'money': 300,   'exp': 120}),
            (75,   "Зелёные руки",       {'money': 900,   'exp': 350}),
            (250,  "Садовод",            {'money': 2500,  'exp': 900,  'eggs': 1}),
            (800,  "Мастер урожая",      {'money': 7000,  'exp': 2200, 'eggs': 2}),
            (2500, "Повелитель огорода", {'money': 20000, 'exp': 6000, 'eggs': 4}),
        ]
    },
    'fish_caught': {
        'title': '🎣 Ловля рыбы',
        'levels': [
            (30,   "Первый улов",        {'money': 500,   'exp': 200}),
            (120,  "Любитель рыбалки",   {'money': 1300,  'exp': 450}),
            (400,  "Рыбак",              {'money': 3500,  'exp': 1200, 'eggs': 1}),
            (1200, "Мастер удочки",      {'money': 10000, 'exp': 2600, 'eggs': 2}),
            (4000, "Морской волк",       {'money': 28000, 'exp': 7000, 'eggs': 4}),
        ]
    },
    'fishing_count': {
        'title': '🪱 Установки наживок',
        'levels': [
            (15,   "Закинул удочку",     {'money': 300,   'exp': 120}),
            (60,   "Терпеливый рыбак",   {'money': 900,   'exp': 350}),
            (200,  "Охотник на рыбу",    {'money': 2600,  'exp': 900,  'eggs': 1}),
            (650,  "Капитан сети",       {'money': 7000,  'exp': 2300, 'eggs': 2}),
            (2000, "Легенда океана",     {'money': 20000, 'exp': 6500, 'eggs': 4}),
        ]
    },
    'casino_games': {
        'title': '🎰 Сыгранные игры',
        'levels': [
            (25,   "Азартный новичок",   {'money': 400,   'exp': 150}),
            (100,  "Игрок",              {'money': 1100,  'exp': 400}),
            (350,  "Любитель риска",     {'money': 3000,  'exp': 1000, 'eggs': 1}),
            (1000, "Хозяин казино",      {'money': 9000,  'exp': 2500, 'eggs': 2}),
            (3000, "Король азарта",      {'money': 25000, 'exp': 7000, 'eggs': 4}),
        ]
    },
    'casino_winnings': {
        'title': '💰 Выигранные деньги',
        'levels': [
            (2000,   "Первая удача",     {'exp': 200}),
            (8000,   "Полоса везения",   {'exp': 500}),
            (25000,  "Любимец фортуны", {'money': 2000,  'exp': 1200, 'eggs': 1}),
            (80000,  "Магнат казино",   {'money': 6000,  'exp': 3000, 'eggs': 2}),
            (250000, "Легенда казино",  {'money': 20000, 'exp': 8000, 'eggs': 5}),
        ]
    },
}

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
pending_slots = {}

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
            rank_index    INTEGER DEFAULT 0,
            private_chat_id BIGINT DEFAULT NULL
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

    c.execute('''
        CREATE TABLE IF NOT EXISTS traps (
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
        CREATE TABLE IF NOT EXISTS fish_catalog (
            user_id   BIGINT,
            fish_name TEXT,
            count     INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, fish_name)
        )
    ''')

    # Новые колонки снаряжения
    for col_sql in [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS rod_level  INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS line_level INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS hook_level INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS reel_level INTEGER DEFAULT 1",
    ]:
        try:
            c.execute(col_sql)
            conn.commit()
        except:
            conn.rollback()

    # Добавляем новые слоты грядок если их меньше 10
    try:
        c.execute("ALTER TABLE users ADD COLUMN private_chat_id BIGINT DEFAULT NULL")
        conn.commit()
    except: pass

    try:
        c.execute('SELECT DISTINCT user_id FROM garden')
        existing_users = c.fetchall()
        for (uid,) in existing_users:
            for slot in range(1, 11):
                c.execute('INSERT INTO garden (user_id, slot) VALUES (%s, %s) ON CONFLICT DO NOTHING', (uid, slot))
    except: pass
        
    new_columns = [
        "ALTER TABLE users ADD COLUMN vegs_harvested INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN seeds_planted   INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN fish_caught     INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN fishing_count   INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN casino_games    INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN casino_winnings INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS luck INTEGER DEFAULT 0",
    ]
    for sql in new_columns:
        try:
            c.execute(sql)
            conn.commit()
        except:
            conn.rollback()

    c.execute('''
    CREATE TABLE IF NOT EXISTS user_achievements (
        user_id   BIGINT,
        stat_key  TEXT,
        level     INTEGER,  -- 0..4 (индекс в списке levels)
        PRIMARY KEY (user_id, stat_key)
    )
''')

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
    for slot in range(1, 5):
        c.execute('INSERT INTO fishing (user_id, slot) VALUES (%s, %s) ON CONFLICT DO NOTHING', (user_id, slot))
        c.execute('INSERT INTO traps (user_id, slot) VALUES (%s, %s) ON CONFLICT DO NOTHING', (user_id, slot))
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

def check_and_give_achievements(user_id, chat_id):
    conn = get_conn()
    c = conn.cursor()

    for stat_key, ach in ACHIEVEMENTS.items():
        # Получаем текущее значение счётчика
        c.execute(f'SELECT {stat_key} FROM users WHERE user_id=%s', (user_id,))
        row = c.fetchone()
        if not row:
            continue
        current_val = row[0] or 0

        # Получаем текущий уровень достижения игрока
        c.execute('SELECT level FROM user_achievements WHERE user_id=%s AND stat_key=%s',
                  (user_id, stat_key))
        ach_row = c.fetchone()
        current_level = ach_row[0] if ach_row else -1

        levels = ach['levels']
        for i, (threshold, name, reward) in enumerate(levels):
            if i <= current_level:
                continue  # уже получено
            if current_val >= threshold:
                # Выдаём награду
                money = reward.get('money', 0)
                exp   = reward.get('exp', 0)
                eggs  = reward.get('eggs', 0)
                c.execute('''UPDATE users SET money=money+%s, exp=exp+%s, eggs=eggs+%s
                             WHERE user_id=%s''', (money, exp, eggs, user_id))
                # Сохраняем уровень
                c.execute('''INSERT INTO user_achievements (user_id, stat_key, level) VALUES (%s,%s,%s)
                             ON CONFLICT (user_id, stat_key) DO UPDATE SET level=%s''',
                          (user_id, stat_key, i, i))
                conn.commit()

                # Уведомление
                lines = []
                if money: lines.append(f"+💵{money}")
                if exp:   lines.append(f"+🌟{exp} опыта")
                if eggs:  lines.append(f"+🥚{eggs}")
                bot.send_message(
                    chat_id,
                    f"🏅 *Достижение выполнено!*\n\n"
                    f"{ach['title']}\n"
                    f"*\"{name}\"*\n\n"
                    f"Награда: {' | '.join(lines)}",
                    parse_mode='Markdown'
                )

    conn.close()

def shop_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🌱 Семена×5 — 💵80",         callback_data="buy_seeds"),
        InlineKeyboardButton("🪱 Наживка×5 — 💵60",        callback_data="buy_bait"),
        InlineKeyboardButton("🥚 Загадочное яйцо — 💵250", callback_data="buy_egg"),
    )
    return markup

# ===== ФОНОВЫЕ ПОТОКИ =====

def run_bot():
    while True:
        try:
            bot.polling(non_stop=True, skip_pending=True, timeout=60, long_polling_timeout=60)
        except telebot.apihelper.ApiTelegramException as e:
            if '409' in str(e):
                print("Конфликт 409! Жду 60 сек...")
                try: bot.delete_webhook(drop_pending_updates=True)
                except: pass
                time.sleep(60)
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
    # Сохраняем личный chat_id если это личка
    if message.chat.type == 'private':
        conn = get_conn()
        c = conn.cursor()
        c.execute('UPDATE users SET private_chat_id=%s WHERE user_id=%s',
                  (message.chat.id, user_id))
        conn.commit()
        conn.close()
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
    bait  = random.randint(1, 3)
    update_daily(user_id, money, exp, bait, now.isoformat())
    bot.send_message(message.chat.id,
        f"🎁 Ежедневная награда 🎁\n\n"
        f"+ {money} 💵 Денег\n"
        f"+ {exp} 🌟 Опыта\n"
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
        "luck": "luck",
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

    # Считаем уникальные виды (не дубликаты)
    TOTAL_PETS = 95
    unique_collected = len(pets)  # get_pets возвращает по одной строке на вид

    rarity_order = [
        "☄️ Секретные", "🌈 Хроматические", "🔴 Мифические",
        "🟡 Легендарные", "🟣 Эпические", "🔵 Редкие", "🟢 Обычные"
    ]

    grouped = {}
    for pet, rarity, count in pets:
        if rarity not in grouped:
            grouped[rarity] = []
        grouped[rarity].append((pet, count))

    safe_username = username.replace('_', '\\_').replace('*', '\\*')
    text = f"🐾 Питомцы игрока *{safe_username}* 🐾\n\n"
    text += f"🪹 Собрано *{unique_collected} / {TOTAL_PETS}*\n\n"

    for rarity in rarity_order:
        if rarity in grouped:
            emoji = PETS[rarity]["emoji"]
            text += f"{emoji} *{rarity}*\n"
            for pet, count in grouped[rarity]:
                text += f"  {pet} ×{count}\n" if count > 1 else f"  {pet}\n"
            text += "\n"

    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ===== КОЛБЭКИ =====

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

# ── Слот: ввод ставки текстом ──────────────────────────────────────────────
@bot.message_handler(func=lambda message: (
    message.from_user.id in pending_slots and
    pending_slots[message.from_user.id].get('status') == 'waiting_bet'
))
def handle_slot_bet_input(message):
    user_id  = message.from_user.id
    user     = get_user(user_id)
    money    = user[2] if user else 0
    sep      = "— – - - - - - - - - - - - - - - - - - - - – —"
    header   = "— – - 🎰 СЛОТ-МАШИНА 🎰 - – —"

    try:
        bet = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введи целое число! Например: 500")
        return

    if bet < 250:
        bot.send_message(message.chat.id, "❌ Минимальная ставка 💵250!")
        return
    if bet > money:
        bot.send_message(message.chat.id,
            f"❌ Недостаточно средств! У тебя только 💵{money}")
        return

    spend_money(user_id, bet)
    money_after = money - bet
    pending_slots[user_id] = {'status': 'ready', 'bet': bet}

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎰 КРУТИТЬ 🎰", callback_data="slot_spin"),
        InlineKeyboardButton("❌ Отмена",      callback_data="slot_cancel"),
    )
    bot.send_message(
        message.chat.id,
        f"{header}\n\n"
        f"Денег: 💵 {money_after}\n\n"
        f"Ставка: 💰 {bet}\n\n"
        f"{sep}",
        reply_markup=markup
    )

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
# ── Слот: открытие меню ────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: call.data == 'casino_slots')
def callback_casino_slots(call):
    user_id = call.from_user.id
    user    = get_user(user_id)
    money   = user[2] if user else 0
    sep     = "• – – – – – – – – – – – – – – – – – – •"
    header  = "— – - 🎰 СЛОТ-МАШИНА 🎰 - – —"

    pending_slots[user_id] = {'status': 'waiting_bet'}

    bot.send_message(
        call.message.chat.id,
        f"{header}\n\n"
        f"Денег: 💵 {money}\n\n"
        f"{sep}\n\n"
        f"Напиши ставку денег которую хочешь поставить на игру (мин. 250).\n\n"
        f"— – - - - - - - - - - - - - - - - - - - - – —"
    )
    bot.answer_callback_query(call.id)


# ── Слот: отмена ──────────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: call.data == 'slot_cancel')
def callback_slot_cancel(call):
    user_id = call.from_user.id
    data    = pending_slots.pop(user_id, None)

    if data and data.get('bet'):
        add_money(user_id, data['bet'])
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            f"Игра отменена ❌\nВозвращено: +💵{data['bet']}")
    else:
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, "Игра отменена ❌")

    bot.answer_callback_query(call.id)


# ── Слот: крутить ─────────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: call.data == 'slot_spin')
def callback_slot_spin(call):
    user_id = call.from_user.id
    data    = pending_slots.get(user_id)

    if not data or data.get('status') != 'ready':
        bot.answer_callback_query(call.id, "❌ Ставка не найдена!")
        return

    bet     = data['bet']
    user    = get_user(user_id)
    money   = user[2] if user else 0
    sep     = "— – - - - - - - - - - - - - - - - - - - - – —"
    header  = (
        f"— – - 🎰 СЛОТ-МАШИНА 🎰 - – —\n\n"
        f"Денег: 💵 {money}\n\n"
        f"Ставка: 💰 {bet}\n\n"
        f"{sep}"
    )

    bot.answer_callback_query(call.id)

    # Генерируем сетку
    luck = user[29] if user and len(user) > 29 else 0  # колонка luck
    grid = sm_spin(luck=luck)

    # Показываем пустую сетку
    try:
        bot.edit_message_text(
            f"{header}\n\n{sm_render_grid(grid, 0)}\n\n{sep}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    except: pass

    # Анимация: открываем столбец за столбцом
    import time
    for col in range(1, 6):
        time.sleep(0.5)
        try:
            bot.edit_message_text(
                f"{header}\n\n{sm_render_grid(grid, col)}\n\n{sep}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
        except: pass

    # Проверяем чертей
    devil_count = sum(1 for row in grid for cell in row if cell == '😈')
    grid_text   = sm_render_grid(grid, 5)

    if devil_count >= 3:
        pending_slots.pop(user_id, None)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎰 Играть снова", callback_data="casino_slots"))
        try:
            bot.edit_message_text(
                f"— – - 🎰 СЛОТ-МАШИНА 🎰 - – —\n\n"
                f"Денег: 💵 {money}\n\n"
                f"Ставка: 💰 {bet}\n\n"
                f"{sep}\n"
                f"          😈 ИГРА ОКОНЧЕНА 😈\n\n"
                f"{grid_text}\n\n"
                f"😈 Весь выигрыш аннулируется ❌🔥\n"
                f"{sep}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except: pass
        return

    # Проверяем комбинации
    wins      = sm_check_wins(grid)
    win_lines = []
    total     = sm_total(wins, bet)

    # Показываем комбинации одну за другой
    time.sleep(0.3)
    for win in wins:
        win_lines.append(sm_win_line(win, bet))
        try:
            bot.edit_message_text(
                f"{header}\n\n{grid_text}\n\n" +
                "\n".join(win_lines) + f"\n\n{sep}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
        except: pass
        time.sleep(0.3)

    # Финальное сообщение
    if total > 0:
        result_text = f"💰 Общий выигрыш: {total} 💵 💰"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            f"💰 Забрать +{total} 💵", callback_data="slot_collect"
        ))
        pending_slots[user_id] = {'status': 'finished', 'winnings': total}
    else:
        result_text = "😔 Нет комбинаций"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎰 Играть снова", callback_data="slot_restart"))
        pending_slots.pop(user_id, None)

    wins_text = ("\n".join(win_lines) + "\n\n") if win_lines else ""

    try:
        bot.edit_message_text(
            f"— – - 🎰 СЛОТ-МАШИНА 🎰 - – —\n\n"
            f"Денег: 💵 {money}\n\n"
            f"Ставка: 💰 {bet}\n\n"
            f"{sep}\n"
            f"          🔥 ИГРА ОКОНЧЕНА 🔥\n\n"
            f"{grid_text}\n\n"
            f"{wins_text}"
            f"{result_text}\n\n"
            f"{sep}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    except: pass

    # Счётчики достижений
    conn2 = get_conn()
    c2    = conn2.cursor()
    c2.execute('UPDATE users SET casino_games=casino_games+1 WHERE user_id=%s', (user_id,))
    if total > 0:
        c2.execute('UPDATE users SET casino_winnings=casino_winnings+%s WHERE user_id=%s',
                   (total, user_id))
    conn2.commit()
    conn2.close()
    threading.Thread(
        target=check_and_give_achievements,
        args=(user_id, call.message.chat.id),
        daemon=True
    ).start()

# ── Слот: забрать выигрыш ─────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: call.data == 'slot_collect')
def callback_slot_collect(call):
    user_id  = call.from_user.id
    data     = pending_slots.pop(user_id, None)
    winnings = data['winnings'] if data else 0

    if winnings > 0:
        add_money(user_id, winnings)

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

    # Возвращаем меню казино
    user   = get_user(user_id)
    money  = user[2] if user else 0
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🎰 Слот-Машина 🎰", callback_data="casino_slots"),
        InlineKeyboardButton("🎲 Кубик-Бомба 💣",  callback_data="casino_dice"),
    )
    bot.send_message(
        call.message.chat.id,
        f"💰 Получено: +{winnings} 💵\n\n"
        f"🎰💰 - К - А - З - И - Н - О - 💰🎰\n"
        f"💵 Денег: {money}",
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)


# ── Слот: закрыть (без выигрыша) ──────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: call.data == 'slot_close')
def callback_slot_close(call):
    pending_slots.pop(call.from_user.id, None)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'slot_restart')
def callback_slot_restart(call):
    user_id = call.from_user.id
    pending_slots[user_id] = {'status': 'waiting_bet'}
    user  = get_user(user_id)
    money = user[2] if user else 0
    sep   = "• – – – – – – – – – – – – – – – – – – •"
    try:
        bot.edit_message_text(
            f"— – - 🎰 СЛОТ-МАШИНА 🎰 - – —\n\n"
            f"Денег: 💵 {money}\n\n"
            f"{sep}\n\n"
            f"Напиши ставку денег которую хочешь поставить на игру (мин. 250).\n\n"
            f"— – - - - - - - - - - - - - - - - - - - - – —",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    except: pass
    bot.answer_callback_query(call.id)

# --- Кубик-Бомба ---
@bot.callback_query_handler(func=lambda call: call.data == 'casino_dice')
def callback_casino_dice(call):
    user_id = call.from_user.id
    sep = "- - - - - - - - - - - - - - - - - - -"
    pending_slots.pop(user_id, None)
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
    conn2 = get_conn()
    c2 = conn2.cursor()
    c2.execute('''UPDATE users SET casino_games=casino_games+1,
                  casino_winnings=casino_winnings+%s WHERE user_id=%s''', (winnings, user_id))
    conn2.commit()
    conn2.close()
    check_and_give_achievements(user_id, call.message.chat.id)
    
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
            conn2 = get_conn()
            c2 = conn2.cursor()
            c2.execute('''UPDATE users SET casino_games=casino_games+1,
                          casino_winnings=casino_winnings+%s WHERE user_id=%s''', (new_accumulated, user_id))
            conn2.commit()
            conn2.close()
            check_and_give_achievements(user_id, call.message.chat.id)
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
BATTLE_INVITE_TIMEOUT = 120  # сек — время на принятие приглашения
BATTLE_TURN_TIMEOUT   = 90   # сек — время на ход
BATTLE_HP = 20

# In-memory множество user_id кто сейчас в бою (для быстрой проверки блокировки)
active_battle_users = set()

# Глобальный lock — защищает от гонки между battle_checker и callback-хэндлерами
_battle_lock = threading.Lock()
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
            chat_id_a       BIGINT,
            chat_id_b       BIGINT,
            invite_msg_id   BIGINT DEFAULT NULL,
            invited_at      TEXT,
            last_action_at  TEXT DEFAULT NULL,
            finished_at     TEXT DEFAULT NULL
        )
    ''')
    conn.commit()

    try:
        c.execute("ALTER TABLE battles ADD COLUMN chat_id_a BIGINT")
        conn.commit()
    except: conn.rollback()

    try:
        c.execute("ALTER TABLE battles ADD COLUMN chat_id_b BIGINT")
        conn.commit()
    except: conn.rollback()

    try:
        c.execute("UPDATE battles SET chat_id_a = chat_id WHERE chat_id_a IS NULL")
        conn.commit()
    except: conn.rollback()

    try:
        c.execute("ALTER TABLE battles DROP COLUMN IF EXISTS chat_id")
        conn.commit()
    except: conn.rollback()

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
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute('SELECT * FROM battles WHERE id=%s', (battle_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_active_battle_for_user(user_id):
    conn = get_conn()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute('''SELECT * FROM battles WHERE (player_a_id=%s OR player_b_id=%s)
                 AND state IN ('invited','active')''', (user_id, user_id))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def create_battle(battle_id, a_id, a_name, b_id, b_name, stake, chat_id_a, chat_id_b, invite_msg_id):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO battles
                 (id, player_a_id, player_a_name, player_b_id, player_b_name,
                  stake, state, chat_id_a, chat_id_b, invite_msg_id, invited_at)
                 VALUES (%s,%s,%s,%s,%s,%s,'invited',%s,%s,%s,%s)''',
              (battle_id, a_id, a_name, b_id, b_name, stake, chat_id_a, chat_id_b, invite_msg_id, now))
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
    # Экранируем имена от markdown символов
    a_name    = a_name.replace('_', '\\_').replace('*', '\\*')
    b_name    = b_name.replace('_', '\\_').replace('*', '\\*')
    turn_name = turn_name.replace('_', '\\_').replace('*', '\\*')
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

def send_to_both(battle, text, reply_markup=None, parse_mode='Markdown'):
    chat_a = battle['chat_id_a']
    chat_b = battle['chat_id_b']
    try:
        bot.send_message(chat_a, text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        print(f"ERROR send_to_both chat_a={chat_a}: {e}")
    if chat_b and chat_b != chat_a:
        try:
            bot.send_message(chat_b, text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            print(f"ERROR send_to_both chat_b={chat_b}: {e}")

# ── Завершение боя ────────────────────────────────────────────────────────────
def end_battle(battle, winner_id, loser_id, winner_name, loser_name, chat_id, forfeit=False):
    battle_id = battle['id']
    a_id      = battle['player_a_id']
    b_id      = battle['player_b_id']
    stake     = battle['stake']
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

    # Экранируем имена
    w_name = winner_name.replace('_', '\\_').replace('*', '\\*')
    l_name = loser_name.replace('_', '\\_').replace('*', '\\*')

    send_to_both(battle,
        f"🏆 СРАЖЕНИЕ ОКОНЧЕНО 🏆\n\n"
        f"🥇 *@{w_name}* победил!{extra}\n"
        f"💵 Выигрыш: *{prize}*\n\n"
        f"Получено опыта:\n"
        f"🌟 @{w_name}: +{winner_exp}\n"
        f"🌟 @{l_name}: +{loser_exp}",
        reply_markup=battle_close_keyboard()
    )

# ── Обработка действия ────────────────────────────────────────────────────────
def process_battle_action(call, battle_id, action):
    user_id = call.from_user.id
    battle  = get_battle(battle_id)

    if not battle or battle['state'] != 'active':
        bot.answer_callback_query(call.id, "❌ Бой уже завершён!")
        return
    if user_id != battle['turn_player_id']:
        bot.answer_callback_query(call.id, "⏳ Сейчас не твой ход!")
        return

    a_id     = battle['player_a_id'];  a_name = battle['player_a_name']
    b_id     = battle['player_b_id'];  b_name = battle['player_b_name']
    stake    = battle['stake']
    hp_a     = battle['hp_a'];  hp_b  = battle['hp_b']
    shield_a = battle['shield_a']; shield_b = battle['shield_b']
    chat_a   = battle['chat_id_a']
    chat_b   = battle['chat_id_b']

    is_a     = (user_id == a_id)
    att_name = a_name if is_a else b_name
    def_name = b_name if is_a else a_name

    # chat атакующего и защищающегося
    att_chat = chat_a if is_a else chat_b
    def_chat = chat_b if is_a else chat_a

    bot.answer_callback_query(call.id)

    # ── Атака ──────────────────────────────────────────────────────────────
    if action == 'attack':
        send_to_both(battle, f"🗡️ *@{att_name}* атакует!", parse_mode='Markdown')

        # Кубик обоим
        dice_msg = bot.send_dice(att_chat, emoji="🎲")
        if def_chat and def_chat != att_chat:
            try: bot.send_dice(def_chat, emoji="🎲")
            except: pass
        dice_val = dice_msg.dice.value
        time.sleep(4.5)

        damage = dice_val
        shield_hit = False
        if is_a and shield_b:
            damage = damage // 2; shield_b = False; shield_hit = True
        elif not is_a and shield_a:
            damage = damage // 2; shield_a = False; shield_hit = True

        if is_a: hp_b = max(0, hp_b - damage)
        else:    hp_a = max(0, hp_a - damage)

        shield_text = f"\n🛡️ Щит поглотил часть урона! Итоговый урон: *{damage}*" if shield_hit else ""
        send_to_both(battle,
            f"🗡️ *@{att_name}* атаковал!\n"
            f"🎲 Выпало: *{dice_val}*{shield_text}\n"
            f"💢 Урон: *{damage}*\n"
            f"❤️ {a_name}: {hp_a}/{BATTLE_HP} | {b_name}: {hp_b}/{BATTLE_HP}",
            parse_mode='Markdown')

    # ── Защита ─────────────────────────────────────────────────────────────
    elif action == 'defend':
        # Проверяем — уже есть щит?
        already_shielded = shield_a if is_a else shield_b
        if already_shielded:
            bot.send_message(att_chat,
                "🛡️ У тебя уже активен щит! Выбери другое действие.")
            # Возвращаем кнопки обратно
            send_to_both(battle,
                battle_status_text(a_name, b_name, stake,
                                   att_name, hp_a, hp_b, shield_a, shield_b),
                reply_markup=battle_action_keyboard(battle_id),
                parse_mode='Markdown'
            )
            return

        if is_a: shield_a = True
        else:    shield_b = True

        send_to_both(battle,
            f"🛡️ *@{att_name}* встаёт в защиту!\n"
            f"Следующий удар по нему будет уменьшен вдвое.",
            parse_mode='Markdown')

    # ── Крит ───────────────────────────────────────────────────────────────
    elif action == 'crit':
        send_to_both(battle,
            f"💥 *@{att_name}* пытается нанести КРИТ-УДАР!", parse_mode='Markdown')

        # Кубик обоим
        dice_msg = bot.send_dice(att_chat, emoji="🎲")
        if def_chat and def_chat != att_chat:
            try: bot.send_dice(def_chat, emoji="🎲")
            except: pass
        dice_val = dice_msg.dice.value
        time.sleep(4.5)

        if dice_val >= 5:
            damage = dice_val * 2
            crit_text = f"💥 ПОПАЛ! Выпало *{dice_val}* → базовый урон *{damage}* (×2)"
        else:
            damage = 0
            crit_text = f"💨 Промах! Выпало *{dice_val}* — мимо"

        shield_hit = False
        if damage > 0:
            if is_a and shield_b:
                damage = damage // 2; shield_b = False; shield_hit = True
            elif not is_a and shield_a:
                damage = damage // 2; shield_a = False; shield_hit = True
# ── Обработка действия ────────────────────────────────────────────────────────
def process_battle_action(call, battle_id, action):
    user_id = call.from_user.id
    battle  = get_battle(battle_id)

    if not battle or battle['state'] != 'active':
        bot.answer_callback_query(call.id, "❌ Бой уже завершён!")
        return
    if user_id != battle['turn_player_id']:
        bot.answer_callback_query(call.id, "⏳ Сейчас не твой ход!")
        return

    a_id     = battle['player_a_id'];  a_name = battle['player_a_name']
    b_id     = battle['player_b_id'];  b_name = battle['player_b_name']
    stake    = battle['stake']
    hp_a     = battle['hp_a'];  hp_b  = battle['hp_b']
    shield_a = battle['shield_a']; shield_b = battle['shield_b']
    chat_a   = battle['chat_id_a']
    chat_b   = battle['chat_id_b']

    is_a     = (user_id == a_id)
    att_name = a_name if is_a else b_name
    def_name = b_name if is_a else a_name
    att_chat = chat_a if is_a else chat_b  # чат атакующего

    bot.answer_callback_query(call.id)

    # ── Атака ──────────────────────────────────────────────────────────────
    if action == 'attack':
        # 1. Объявление атаки — обоим
        send_to_both(battle, f"🗡️ *@{att_name}* атакует!", parse_mode='Markdown')

        # 2. Кубик — только атакующему
        dice_msg = bot.send_dice(att_chat, emoji="🎲")
        dice_val = dice_msg.dice.value
        time.sleep(4.5)

        # 3. Считаем урон
        damage = dice_val
        shield_text = ""
        if is_a and shield_b:
            damage = damage // 2; shield_b = False
            shield_text = f"\n🛡️ Щит поглотил урон! Итого: *{damage}*"
        elif not is_a and shield_a:
            damage = damage // 2; shield_a = False
            shield_text = f"\n🛡️ Щит поглотил урон! Итого: *{damage}*"

        if is_a: hp_b = max(0, hp_b - damage)
        else:    hp_a = max(0, hp_a - damage)

        # 4. Краткий результат — обоим
        send_to_both(battle,
            f"🗡️ *@{att_name}* атаковал на *{dice_val}* урона!{shield_text}",
            parse_mode='Markdown')

    # ── Защита ─────────────────────────────────────────────────────────────
    elif action == 'defend':
        if is_a: shield_a = True
        else:    shield_b = True

        # Краткое сообщение — обоим
        send_to_both(battle,
            f"🛡️ *@{att_name}* встаёт в защиту!\n"
            f"Следующий удар по нему будет уменьшен вдвое.",
            parse_mode='Markdown')

    # ── Крит ───────────────────────────────────────────────────────────────
    elif action == 'crit':
        # 1. Объявление крита — обоим
        send_to_both(battle,
            f"💥 *@{att_name}* пытается нанести КРИТ-УДАР!", parse_mode='Markdown')

        # 2. Кубик — только атакующему
        dice_msg = bot.send_dice(att_chat, emoji="🎲")
        dice_val = dice_msg.dice.value
        time.sleep(4.5)

        # 3. Считаем урон
        if dice_val >= 5:
            damage = dice_val * 2
            crit_text = f"💥 ПОПАЛ! Выпало *{dice_val}* → урон *{damage}* (×2)"
        else:
            damage = 0
            crit_text = f"💨 Промах! Выпало *{dice_val}* — мимо"

        shield_text = ""
        if damage > 0:
            if is_a and shield_b:
                damage = damage // 2; shield_b = False
                shield_text = f"\n🛡️ Щит поглотил урон! Итого: *{damage}*"
            elif not is_a and shield_a:
                damage = damage // 2; shield_a = False
                shield_text = f"\n🛡️ Щит поглотил урон! Итого: *{damage}*"

        if is_a: hp_b = max(0, hp_b - damage)
        else:    hp_a = max(0, hp_a - damage)

        # 4. Краткий результат — обоим
        send_to_both(battle,
            f"💥 *@{att_name}* применил КРИТ-УДАР!\n"
            f"{crit_text}{shield_text}",
            parse_mode='Markdown')

    # ── Проверка смерти ────────────────────────────────────────────────────
    if hp_a <= 0 or hp_b <= 0:
        if hp_a <= 0:
            winner_id, loser_id     = b_id, a_id
            winner_name, loser_name = b_name, a_name
        else:
            winner_id, loser_id     = a_id, b_id
            winner_name, loser_name = a_name, b_name
        end_battle(battle, winner_id, loser_id, winner_name, loser_name, chat_a)
        return

    # ── Переключить ход ────────────────────────────────────────────────────
    next_id   = b_id   if is_a else a_id
    next_name = b_name if is_a else a_name
    update_battle_state(battle_id, next_id, hp_a, hp_b, shield_a, shield_b)

    # 5. Основное сообщение с меню — обоим
    send_to_both(battle,
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
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            inv_thr = (now - timedelta(seconds=BATTLE_INVITE_TIMEOUT)).isoformat()
            c.execute("SELECT * FROM battles WHERE state='invited' AND invited_at <= %s", (inv_thr,))
            expired_invites = [dict(r) for r in c.fetchall()]
            conn.close()

            for b in expired_invites:
                bid   = b['id']; a_id = b['player_a_id']; a_name = b['player_a_name']; b_id = b['player_b_id']
                cid_a = b['chat_id_a']; cid_b = b['chat_id_b']; imid = b['invite_msg_id']
                cancel_battle(bid, a_id, b_id)
                try:
                    if imid and cid_b: bot.delete_message(cid_b, imid)
                except: pass
                for cid in set(filter(None, [cid_a, cid_b])):
                    try:
                        bot.send_message(cid,
                            f"⏰ Приглашение на битву от *{a_name}* истекло.",
                            parse_mode='Markdown')
                    except: pass

            # --- Таймаут хода ---
            conn = get_conn()
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            turn_thr = (now - timedelta(seconds=BATTLE_TURN_TIMEOUT)).isoformat()
            c.execute("SELECT * FROM battles WHERE state='active' AND last_action_at <= %s", (turn_thr,))
            expired_turns = [dict(r) for r in c.fetchall()]
            conn.close()

            for b in expired_turns:
                bid    = b['id']
                a_id   = b['player_a_id']; a_name = b['player_a_name']
                bpl_id = b['player_b_id']; b_name = b['player_b_name']
                turn   = b['turn_player_id']; cid = b['chat_id_a']
                if turn == a_id:
                    winner_id, loser_id     = bpl_id, a_id
                    winner_name, loser_name = b_name, a_name
                else:
                    winner_id, loser_id     = a_id, bpl_id
                    winner_name, loser_name = a_name, b_name
                try:
                    end_battle(b, winner_id, loser_id, winner_name, loser_name, cid, forfeit=True)
                except Exception as e:
                    print(f"ERROR end_battle forfeit: {e}")

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

    b_id      = user_b[0]
    b_name    = user_b[1]
    b_chat_id = user_b[22] if len(user_b) > 22 else None  # private_chat_id

    if b_id == user_id:
        bot.send_message(message.chat.id, "❌ Нельзя вызвать самого себя!")
        return
    if b_id in active_battle_users:
        bot.send_message(message.chat.id, f"❌ Игрок @{target_name} уже в сражении!")
        return
    if not b_chat_id:
        bot.send_message(message.chat.id,
            f"❌ Игрок @{target_name} ещё не написал боту в личку! "
            f"Попроси его написать /start боту напрямую.")
        return

    battle_id = _uuid.uuid4().hex[:8]

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Принять ⚔️",   callback_data=f"battle_acc_{battle_id}"),
        InlineKeyboardButton("Отказаться ❌", callback_data=f"battle_dec_{battle_id}"),
    )
    # Отправляем приглашение игроку B в его личку
    invite_msg = bot.send_message(
        b_chat_id,
        f"⚔️ Игрок *{username}* приглашает вас на битву ⚔️\n\n"
        f"Ставка: 💵 *{stake}*",
        reply_markup=markup,
        parse_mode='Markdown'
    )
    try:
        create_battle(battle_id, user_id, username, b_id, b_name, stake,
                      message.chat.id, b_chat_id, invite_msg.message_id)
        bot.send_message(message.chat.id,
            f"✅ Приглашение отправлено *@{target_name}*!", parse_mode='Markdown')
    except Exception as e:
        print(f"ERROR create_battle: {e}")
        active_battle_users.discard(user_id)
        active_battle_users.discard(b_id)
        bot.send_message(message.chat.id, "❌ Ошибка при создании боя, попробуй снова!")

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
    try:
        print(f"RAW call.data: '{call.data}'")
        battle_id = call.data.replace("battle_acc_", "")
        user_id = call.from_user.id
        battle = get_battle(battle_id)
        print(f"battle_id extracted: '{battle_id}'")
        print("DEBUG battle:", battle)

        if not battle or battle['state'] != 'invited':
            bot.answer_callback_query(call.id, "❌ Приглашение уже недоступно")
            return

        if user_id != battle['player_b_id']:
            bot.answer_callback_query(call.id, "❌ Это приглашение не для тебя!")
            return

        bot.answer_callback_query(call.id)

        a_id, a_name = battle['player_a_id'], battle['player_a_name']
        b_id, b_name = battle['player_b_id'], battle['player_b_name']
        stake = battle['stake']
        chat_id_b = battle['chat_id_b']
        imid = battle['invite_msg_id']

        print("DEBUG chats:", battle['chat_id_a'], chat_id_b, imid)

        user_a = get_user(a_id)
        user_b = get_user(b_id)

        if not user_a or user_a[2] < stake:
            cancel_battle(battle_id, a_id, b_id)
            send_to_both(battle, f"⚠️ Бой отменён — у *{a_name}* недостаточно средств (нужно 💵{stake})", parse_mode='Markdown')
            return

        if not user_b or user_b[2] < stake:
            cancel_battle(battle_id, a_id, b_id)
            send_to_both(battle, f"⚠️ Бой отменён — у *{b_name}* недостаточно средств (нужно 💵{stake})", parse_mode='Markdown')
            return

        spend_money(a_id, stake)
        spend_money(b_id, stake)

        try:
            bot.delete_message(chat_id_b, imid)
        except:
            pass

        turn_id = random.choice([a_id, b_id])
        turn_name = a_name if turn_id == a_id else b_name

        activate_battle(battle_id, turn_id)
        battle = get_battle(battle_id)

        print(f"DEBUG before status: chat_a={battle['chat_id_a']}, chat_b={battle['chat_id_b']}, turn={turn_name}")

        bot.send_message(battle['chat_id_a'], f"✅ *{b_name}* принял заявку на сражение!", parse_mode='Markdown')
        if battle['chat_id_b'] and battle['chat_id_b'] != battle['chat_id_a']:
            bot.send_message(battle['chat_id_b'], f"✅ *{b_name}* принял заявку на сражение!", parse_mode='Markdown')

        status = battle_status_text(a_name, b_name, stake, turn_name, BATTLE_HP, BATTLE_HP, False, False)
        keyboard = battle_action_keyboard(battle_id)

        bot.send_message(battle['chat_id_a'], status, reply_markup=keyboard, parse_mode='Markdown')
        if battle['chat_id_b'] and battle['chat_id_b'] != battle['chat_id_a']:
            bot.send_message(battle['chat_id_b'], status, reply_markup=keyboard, parse_mode='Markdown')

        print("DEBUG all done")

    except Exception as e:
        print(f"ERROR callback_battle_accept: {e}")
        import traceback; traceback.print_exc()

@bot.callback_query_handler(func=lambda call: call.data.startswith('battle_dec_'))
def callback_battle_decline(call):
    try:
        battle_id = call.data[len('battle_dec_'):]
        user_id   = call.from_user.id
        battle    = get_battle(battle_id)

        print(f"DEBUG decline: battle={battle}")

        if not battle or battle['state'] != 'invited':
            bot.answer_callback_query(call.id, "❌ Приглашение уже недоступно!")
            return
        if user_id != battle['player_b_id']:
            bot.answer_callback_query(call.id, "❌ Это приглашение не для тебя!")
            return

        a_id   = battle['player_a_id']; a_name = battle['player_a_name']
        b_id   = battle['player_b_id']; b_name = battle['player_b_name']
        chat_id_b = battle['chat_id_b']; imid = battle['invite_msg_id']

        cancel_battle(battle_id, a_id, b_id)
        try: bot.delete_message(chat_id_b, imid)
        except: pass

        send_to_both(battle,
            f"❌ *{b_name}* отказался участвовать в битве с *{a_name}*",
            parse_mode='Markdown')
        bot.answer_callback_query(call.id)

    except Exception as e:
        print(f"ERROR callback_battle_decline: {e}")
        bot.answer_callback_query(call.id, "❌ Внутренняя ошибка!")

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

@bot.message_handler(commands=['achievements'])
def cmd_achievements(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)

    try:
        conn = get_conn()
        c = conn.cursor()

        cols = ', '.join(ACHIEVEMENTS.keys())
        c.execute(f'SELECT {cols} FROM users WHERE user_id=%s', (user_id,))
        row = c.fetchone()

        c.execute('SELECT stat_key, level FROM user_achievements WHERE user_id=%s', (user_id,))
        ach_levels = {r[0]: r[1] for r in c.fetchall()}
        conn.close()

        if not row:
            bot.send_message(message.chat.id, "❌ Ошибка: данные не найдены!")
            return

        stat_values = {key: (row[i] or 0) for i, key in enumerate(ACHIEVEMENTS.keys())}

        sep = "— – - 🏅 ДОСТИЖЕНИЯ 🏅 - – —"
        end = "— — – - - - - - - - - - - - – — —"
        text = sep + "\n\n"

        for stat_key, ach in ACHIEVEMENTS.items():
            current_val = stat_values[stat_key]
            current_level = ach_levels.get(stat_key, -1)
            next_level_idx = current_level + 1
            levels = ach['levels']

            text += f"– – {ach['title']} – –\n"

            if next_level_idx >= len(levels):
                text += "✅ Все достижения выполнены!\n\n"
            else:
                threshold, name, _ = levels[next_level_idx]
                text += f"🎯 «{name}»\n"
                text += f"Прогресс: {current_val} / {threshold}\n\n"

        text += end
        bot.send_message(message.chat.id, text)

    except Exception as e:
        print(f"ERROR cmd_achievements: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка загрузки достижений. Попробуй позже.")

@bot.message_handler(commands=['initdb'])
def cmd_initdb(message):
    if message.from_user.username != ADMIN_USERNAME:
        return
    try:
        conn = get_conn()
        c = conn.cursor()
        sqls = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS vegs_harvested INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS luck INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS seeds_planted   INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS fish_caught     INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS fishing_count   INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS casino_games    INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS casino_winnings INTEGER DEFAULT 0",
        ]
        for sql in sqls:
            c.execute(sql)
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_achievements (
                user_id  BIGINT,
                stat_key TEXT,
                level    INTEGER,
                PRIMARY KEY (user_id, stat_key)
            )
        ''')
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "✅ База данных обновлена!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['checkdb'])
def cmd_checkdb(message):
    if message.from_user.username != 'Sid_17jj':
        return
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT column_name, ordinal_position FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position")
    rows = c.fetchall()
    conn.close()
    text = "\n".join([f"{pos}: {name}" for name, pos in rows])
    bot.send_message(message.chat.id, f"Колонки users:\n{text}")

@bot.message_handler(commands=['myluck'])
def cmd_myluck(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    luck = user[29] if user and len(user) > 29 else 0
    bot.send_message(message.chat.id, f"🍀 Твоя удача: {luck}")

@bot.message_handler(commands=['fixslots'])
def cmd_fixslots(message):
    if message.from_user.username != ADMIN_USERNAME:
        return
    conn = get_conn()
    c    = conn.cursor()
    try:
        # Удаляем все дубли — оставляем только строку с минимальным id
        c.execute('''
            DELETE FROM cooking_slots
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM cooking_slots
                GROUP BY user_id, bld_key, slot_num
            )
        ''')
        deleted = c.rowcount
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Удалено дублей: {deleted}")
    except Exception as e:
        conn.rollback()
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")
    finally:
        conn.close()

@bot.message_handler(commands=['resetme'])
def cmd_resetme(message):
    if message.from_user.username != ADMIN_USERNAME:
        return
    user_id = message.from_user.id
    conn = get_conn()
    c    = conn.cursor()
    try:
        # Основные характеристики
        c.execute('''UPDATE users SET money=0, exp=0, seeds=0, bait=0,
                     fish=0, tropical_fish=0, crab=0, lobster=0, squid=0,
                     shark=0, dragonfish=0, treasure=0, eggs=0, rank_index=0,
                     seeds_planted=0, fish_caught=0, fishing_count=0,
                     casino_games=0, casino_winnings=0, vegs_harvested=0,
                     luck=0, rod_level=1, line_level=1, hook_level=1, reel_level=1
                     WHERE user_id=%s''', (user_id,))
        # Каталог рыб
        c.execute('DELETE FROM fish_catalog WHERE user_id=%s', (user_id,))
        # Достижения
        c.execute('DELETE FROM user_achievements WHERE user_id=%s', (user_id,))
        # Ловушки
        c.execute('''UPDATE traps SET status='empty', started_at=NULL,
                     chat_id=NULL, message_id=NULL WHERE user_id=%s''', (user_id,))
        # Огород — грядки
        c.execute('''UPDATE garden_plots SET crop_emoji=NULL, planted_at=NULL,
                     watered_at=NULL, fert_growth=0, fert_quality=0,
                     fert_yield=0, fert_name=NULL WHERE user_id=%s''', (user_id,))
        # Огород — семена, инвентарь, удобрения, лог
        c.execute('DELETE FROM garden_seeds WHERE user_id=%s', (user_id,))
        c.execute('DELETE FROM garden_inventory WHERE user_id=%s', (user_id,))
        c.execute('DELETE FROM garden_fertilizers WHERE user_id=%s', (user_id,))
        c.execute('DELETE FROM garden_harvest_log WHERE user_id=%s', (user_id,))
        # Здания
        c.execute('DELETE FROM farm_buildings WHERE user_id=%s', (user_id,))
        c.execute('DELETE FROM cooking_slots WHERE user_id=%s', (user_id,))
        c.execute('DELETE FROM goods_inventory WHERE user_id=%s', (user_id,))

        conn.commit()
        bot.send_message(message.chat.id, "✅ Прогресс полностью сброшен. Ты снова новичок!")
    except Exception as e:
        conn.rollback()
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")
    finally:
        conn.close()

# ===== РЫБАЛКА (новая) =====
register_fishing_handlers(
    bot, get_conn, get_user, add_exp, add_money,
    add_bait, spend_money, check_and_give_achievements
)

# ===== ОГОРОД (новый) =====
register_garden_handlers(
    bot, get_conn, get_user, add_exp, add_money, spend_money, check_and_give_achievements
    )

register_buildings_handlers(
    bot, get_conn, get_user, add_exp, spend_money
)

# ===== ЗАПУСК =====
init_db()
init_battle_tables()

bot.delete_webhook(drop_pending_updates=True)
time.sleep(15)
print("Бот запущен!")

threading.Thread(
    target=buildings_checker_loop,
    args=(bot, get_conn, get_user),
    daemon=True
).start()
threading.Thread(
    target=traps_checker_loop,
    args=(bot, get_conn),
    daemon=True
).start()
threading.Thread(target=battle_checker, daemon=True).start()
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
print(f"Поток бота создан: {bot_thread.is_alive()}")

run_flask()
