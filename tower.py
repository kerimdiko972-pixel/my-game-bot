import psycopg2
import psycopg2.extras
import os
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

# ═══════════════════════════════════════════════════════════════
# КОНСТАНТЫ КЛАССОВ
# ═══════════════════════════════════════════════════════════════

CLASSES = {
    "warrior": {
        "name": "Воин", "emoji": "⚔️",
        "base_hp": 130, "base_mp": 48, "k1": 3, "k2": 1,
        "stats": {"strength": 8, "agility": 5, "intellect": 3,
                  "constitution": 8, "speed": 6, "charisma": 5},
        "lead": ["strength", "constitution"],
    },
    "barbarian": {
        "name": "Варвар", "emoji": "🪓",
        "base_hp": 140, "base_mp": 42, "k1": 3, "k2": 1,
        "stats": {"strength": 9, "agility": 4, "intellect": 2,
                  "constitution": 9, "speed": 6, "charisma": 3},
        "lead": ["strength", "constitution"],
    },
    "assassin": {
        "name": "Ассасин", "emoji": "🗡️",
        "base_hp": 90, "base_mp": 54, "k1": 2, "k2": 2,
        "stats": {"strength": 6, "agility": 9, "intellect": 4,
                  "constitution": 4, "speed": 7, "charisma": 6},
        "lead": ["agility", "charisma"],
    },
    "ranger": {
        "name": "Следопыт", "emoji": "🏹",
        "base_hp": 100, "base_mp": 54, "k1": 2, "k2": 2,
        "stats": {"strength": 6, "agility": 8, "intellect": 4,
                  "constitution": 5, "speed": 7, "charisma": 4},
        "lead": ["agility", "intellect"],
    },
    "mage": {
        "name": "Волшебник", "emoji": "🪄",
        "base_hp": 100, "base_mp": 84, "k1": 1, "k2": 3,
        "stats": {"strength": 2, "agility": 4, "intellect": 9,
                  "constitution": 5, "speed": 10, "charisma": 6},
        "lead": ["intellect", "charisma"],
    },
    "warlock": {
        "name": "Колдун", "emoji": "🔮",
        "base_hp": 120, "base_mp": 78, "k1": 1, "k2": 3,
        "stats": {"strength": 3, "agility": 4, "intellect": 8,
                  "constitution": 7, "speed": 8, "charisma": 8},
        "lead": ["intellect", "charisma"],
    },
}

SPELL_CLASSES = {"mage", "warlock"}

STAT_NAMES = {
    "strength":     "💪 Сила",
    "agility":      "🎯 Ловкость",
    "intellect":    "🧠 Интеллект",
    "constitution": "🫀 Телосложение",
    "speed":        "🏃 Скорость",
    "charisma":     "👄 Харизма",
}

SEP = "– – – – – – – – – – – – – – – –"

# ═══════════════════════════════════════════════════════════════
# ЭФФЕКТЫ СТАТУСОВ
# ═══════════════════════════════════════════════════════════════

STATUS_EFFECTS = {
    "burn":        {"name": "Ожог",          "emoji": "🔥",  "desc": "Наносит 5–10 урона в конце каждого хода."},
    "cold":        {"name": "Холод",          "emoji": "❄️",  "desc": "Уменьшает скорость и ловкость на -2."},
    "shock":       {"name": "Шок",            "emoji": "💫",  "desc": "Пропускает ход."},
    "weakness":    {"name": "Слабость",       "emoji": "⛓️‍💥", "desc": "-50% наносимого урона и -2 к силе."},
    "poison":      {"name": "Яд",             "emoji": "☠️",  "desc": "Наносит урон равный 10×{кол.яда}, убывает на 1 каждый ход."},
    "blind":       {"name": "Слепота",        "emoji": "👁️‍🗨️", "desc": "50% шанс промахнуться атакой."},
    "regen":       {"name": "Регенерация",    "emoji": "🌿",  "desc": "Восстанавливает 10×{кол.} ХП, убывает на 1 каждый ход."},
    "fear":        {"name": "Страх",          "emoji": "😱",  "desc": "Не может атаковать."},
    "sleep":       {"name": "Сон",            "emoji": "💤",  "desc": "Пропуск хода до получения урона или действия врага."},
    "bleed":       {"name": "Кровотечение",   "emoji": "🩸",  "desc": "Наносит 8–10 урона при любом действии."},
    "second_wind": {"name": "Второе дыхание", "emoji": "❤️‍🔥", "desc": "Выжить при смерти и получить 1 ХП."},
}

# ═══════════════════════════════════════════════════════════════
# РАСХОДНИКИ
# ═══════════════════════════════════════════════════════════════

CONSUMABLES = {
    "health_potion":      {"name": "Зелье здоровья",              "emoji": "❤️",    "desc": "Восстанавливает 25–50 HP.", "type": "consumable"},
    "big_health_potion":  {"name": "Большое зелье здоровья",      "emoji": "❤️❤️",  "desc": "Восстанавливает 75–100 HP.", "type": "consumable"},
    "mana_potion":        {"name": "Зелье маны",                  "emoji": "⚡",    "desc": "Восстанавливает 15–30 MP.", "type": "consumable"},
    "big_mana_potion":    {"name": "Большое зелье маны",          "emoji": "⚡⚡",   "desc": "Восстанавливает 50–70 MP.", "type": "consumable"},
    "str_potion":         {"name": "Зелье силы",                  "emoji": "💪",    "desc": "+2 к Силе на 3 этажа.", "type": "consumable"},
    "agi_potion":         {"name": "Зелье ловкости",              "emoji": "🎯",    "desc": "+2 к Ловкости на 3 этажа.", "type": "consumable"},
    "int_potion":         {"name": "Зелье интеллекта",            "emoji": "🧠",    "desc": "+2 к Интеллекту на 3 этажа.", "type": "consumable"},
    "con_potion":         {"name": "Зелье телосложения",          "emoji": "🫀",    "desc": "+5 HP максимум на 3 этажа.", "type": "consumable"},
    "cha_potion":         {"name": "Зелье харизмы",               "emoji": "👄",    "desc": "+2 к Харизме на 3 этажа.", "type": "consumable"},
    "arrows":             {"name": "Стрелы",                      "emoji": "🏹",    "desc": "Расходный боеприпас для луков/арбалетов, 1 стрела на выстрел.", "type": "ammo"},
    "bolts":              {"name": "Арбалетные болты",            "emoji": "⚡",    "desc": "Расходный боеприпас для арбалетов, +2 урон.", "type": "ammo"},
    "bomb":               {"name": "Бомба",                       "emoji": "💣",    "desc": "Наносит 10–20 урона всем врагам на этаже и 20% шанс наложить 🔥ожог.", "type": "consumable"},
    "ice_flask":          {"name": "Ледяной флакон",              "emoji": "❄️",    "desc": "Наносит 5–10 урона 1 врагу и накладывает 1 холод.", "type": "consumable"},
    "speed_potion":       {"name": "Зелье быстрого бега",         "emoji": "🏃",    "desc": "+3 к скорости на 3 этажа.", "type": "consumable"},
    "scroll_fireball":    {"name": "Свиток огненного шара",       "emoji": "🔥📜",  "desc": "Одноразовое заклинание «Огненный шар».", "type": "scroll"},
    "scroll_ice_arrow":   {"name": "Свиток ледяной стрелы",       "emoji": "❄️📜",  "desc": "Одноразовое заклинание «Ледяная стрела».", "type": "scroll"},
    "scroll_heal":        {"name": "Свиток исцеления",            "emoji": "❤️📜",  "desc": "Восстанавливает 30–50 HP.", "type": "scroll"},
    "scroll_mana":        {"name": "Свиток маны",                 "emoji": "⚡📜",  "desc": "Восстанавливает 20–40 MP.", "type": "scroll"},
    "smoke_bomb":         {"name": "Дымовая бомба",               "emoji": "🌫️",   "desc": "Накладывает всем врагам 👁️‍🗨️слепоту на 2 хода.", "type": "consumable"},
    "lantern":            {"name": "Фонарик",                     "emoji": "🔦",    "desc": "Освещает скрытых врагов. Используется вне боя.", "type": "tool"},
    "rope":               {"name": "Верёвка",                     "emoji": "🪢",    "desc": "Используется для ловушек или спуска.", "type": "tool"},
    "pickaxe":            {"name": "Кирка",                       "emoji": "⛏️",    "desc": "Разрушает стены/сундуки.", "type": "tool"},
    "poison_bomb":        {"name": "Ядовитая бомба",              "emoji": "☠️",    "desc": "Накладывает 5 ☠️Яда всем врагам на этаже.", "type": "consumable"},
    "regen_small":        {"name": "Малый эликсир регенерации",   "emoji": "🌿",    "desc": "+2 HP и +2 MP каждый ход (3 хода).", "type": "consumable"},
    "regen_big":          {"name": "Большой эликсир регенерации", "emoji": "🌿🌿",  "desc": "+5 HP и +5 MP каждый ход (5 ходов).", "type": "consumable"},
    "scroll_teleport":    {"name": "Свиток телепортации",         "emoji": "✨📜",  "desc": "Перемещает на случайный этаж вперёд (1–7).", "type": "scroll"},
    "second_wind_potion": {"name": "Зелье второго дыхания",       "emoji": "❤️‍🔥",  "desc": "Получи статус «Второе дыхание ❤️‍🔥».", "type": "consumable"},
}

# ═══════════════════════════════════════════════════════════════
# БАЗА ДАННЫХ
# ═══════════════════════════════════════════════════════════════

def init_tower_tables():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tower_chars (
            user_id         BIGINT PRIMARY KEY,
            char_name       TEXT,
            class_key       TEXT,
            level           INTEGER DEFAULT 1,
            exp             INTEGER DEFAULT 0,
            stat_points     INTEGER DEFAULT 0,
            mastery_bonus   INTEGER DEFAULT 0,
            hp              INTEGER DEFAULT 0,
            mp              INTEGER DEFAULT 0,
            strength        INTEGER DEFAULT 0,
            agility         INTEGER DEFAULT 0,
            intellect       INTEGER DEFAULT 0,
            constitution    INTEGER DEFAULT 0,
            speed           INTEGER DEFAULT 0,
            charisma        INTEGER DEFAULT 0,
            skill_1         TEXT DEFAULT NULL,
            skill_2         TEXT DEFAULT NULL,
            skill_3         TEXT DEFAULT NULL,
            weapon          TEXT DEFAULT 'Голые кулаки',
            armor           TEXT DEFAULT 'Лёгкая одежда',
            artifact        TEXT DEFAULT 'Нет',
            coins           INTEGER DEFAULT 0,
            best_floor      INTEGER DEFAULT 0,
            items           TEXT DEFAULT '{}',
            owned_weapons   TEXT DEFAULT '["Голые кулаки"]',
            owned_armors    TEXT DEFAULT '["Лёгкая одежда"]',
            owned_artifacts TEXT DEFAULT '[]'
        )
    ''')
    # Миграция: добавляем новые колонки если их нет
    for col, definition in [
        ("items",           "TEXT DEFAULT '{}'"),
        ("owned_weapons",   "TEXT DEFAULT '[\"Голые кулаки\"]'"),
        ("owned_armors",    "TEXT DEFAULT '[\"Лёгкая одежда\"]'"),
        ("owned_artifacts", "TEXT DEFAULT '[]'"),
    ]:
        try:
            c.execute(f"ALTER TABLE tower_chars ADD COLUMN {col} {definition}")
            conn.commit()
        except: conn.rollback()

    conn.commit()
    conn.close()
    print("Таблица tower_chars инициализирована!")

def get_tower_char(user_id):
    conn = get_conn()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute('SELECT * FROM tower_chars WHERE user_id=%s', (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

STARTING_ITEMS = {
    "warrior": {
        "health_potion": 2,
        "str_potion": 1,
        "bomb": 1,
        "regen_small": 1,
        "rope": 1,
    },
    "barbarian": {
        "health_potion": 3,
        "str_potion": 1,
        "speed_potion": 1,
        "bomb": 1,
    },
    "assassin": {
        "health_potion": 1,
        "agi_potion": 1,
        "smoke_bomb": 1,
        "poison_bomb": 1,
        "regen_small": 1,
    },
    "ranger": {
        "health_potion": 1,
        "agi_potion": 1,
        "arrows": 15,
        "ice_flask": 1,
        "lantern": 1,
    },
    "mage": {
        "health_potion": 1,
        "mana_potion": 2,
        "scroll_fireball": 1,
        "scroll_heal": 1,
        "regen_small": 1,
    },
    "warlock": {
        "health_potion": 1,
        "mana_potion": 2,
        "scroll_ice_arrow": 1,
        "poison_bomb": 1,
        "scroll_teleport": 1,
    },
}

def create_tower_char(user_id, char_name, class_key):
    cls = CLASSES[class_key]
    stats = cls["stats"]
    max_hp = cls["base_hp"] + stats["constitution"] * 1 * cls["k1"]
    max_mp = cls["base_mp"] + stats["intellect"] * 1 * cls["k2"]
    starting_items = json.dumps(STARTING_ITEMS.get(class_key, {}))
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO tower_chars
        (user_id, char_name, class_key, level, exp, stat_points, mastery_bonus,
         hp, mp, strength, agility, intellect, constitution, speed, charisma,
         weapon, armor, artifact, coins, best_floor,
         items, owned_weapons, owned_armors, owned_artifacts)
        VALUES (%s,%s,%s,1,0,0,1,%s,%s,%s,%s,%s,%s,%s,%s,
                'Голые кулаки','Лёгкая одежда','Нет',0,0,
                %s,'["Голые кулаки"]','["Лёгкая одежда"]','[]')
        ON CONFLICT (user_id) DO NOTHING
    ''', (
        user_id, char_name, class_key,
        max_hp, max_mp,
        stats["strength"], stats["agility"], stats["intellect"],
        stats["constitution"], stats["speed"], stats["charisma"],
        starting_items
    ))
    conn.commit()
    conn.close()

def delete_tower_char(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM tower_chars WHERE user_id=%s', (user_id,))
    conn.commit()
    conn.close()

def get_items(char):
    try:
        return json.loads(char.get('items') or '{}')
    except:
        return {}

def save_items(user_id, items_dict):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE tower_chars SET items=%s WHERE user_id=%s',
              (json.dumps(items_dict), user_id))
    conn.commit()
    conn.close()

def get_owned_equipment(char, slot):
    """slot: 'owned_weapons', 'owned_armors', 'owned_artifacts'"""
    try:
        return json.loads(char.get(slot) or '[]')
    except:
        return []

# ═══════════════════════════════════════════════════════════════
# ВЫЧИСЛЕНИЯ
# ═══════════════════════════════════════════════════════════════

def calc_max_hp(char):
    cls = CLASSES[char['class_key']]
    return cls['base_hp'] + char['constitution'] * char['level'] * cls['k1']

def calc_max_mp(char):
    cls = CLASSES[char['class_key']]
    return cls['base_mp'] + char['intellect'] * char['level'] * cls['k2']

def exp_for_next_level(level):
    return level * 100

def mastery_bonus(level):
    return 1 + (level - 1) // 4

def cp_cost(current_val):
    if current_val < 5:  return 1
    if current_val < 10: return 2
    if current_val < 15: return 3
    return 4

# ═══════════════════════════════════════════════════════════════
# UI ТЕКСТЫ
# ═══════════════════════════════════════════════════════════════

def safe(text):
    return str(text).replace('_', '\\_').replace('*', '\\*')

def tower_main_text(char):
    cls = CLASSES[char['class_key']]
    max_hp = calc_max_hp(char)
    max_mp = calc_max_mp(char)
    lvl = char['level']
    exp_next = exp_for_next_level(lvl)
    mb = mastery_bonus(lvl)
    lead = cls['lead']

    def stat_line(key):
        star = "⭐" if key in lead else "  "
        return f"{star}{STAT_NAMES[key]}: {char[key]}"

    skills = []
    for i, slot in enumerate(['skill_1', 'skill_2', 'skill_3'], 1):
        val = char[slot] or '—'
        num = ['1️⃣', '2️⃣', '3️⃣'][i-1]
        skills.append(f"{num} {val}")

    return (
        f"— – - 🏯 БАШНЯ ХАОСА 🏯 - – —\n\n"
        f"🎖️ Твой рекорд: *{char['best_floor']}* этаж\n\n"
        f"– *{safe(char['char_name'])}* –\n"
        f"Класс: {cls['emoji']} {cls['name']}\n"
        f"Уровень: *{lvl}* (⭐ {char['exp']}/{exp_next} опыта)\n"
        f"Очки Характеристик: *{char['stat_points']}*\n"
        f"Бонус Мастерства: *+{mb}*\n\n"
        f"❤️ ХП: *{char['hp']}/{max_hp}*\n"
        f"⚡ Мана: *{char['mp']}/{max_mp}*\n\n"
        f"{stat_line('strength')}\n"
        f"{stat_line('agility')}\n"
        f"{stat_line('intellect')}\n"
        f"{stat_line('constitution')}\n"
        f"{stat_line('speed')}\n"
        f"{stat_line('charisma')}\n\n"
        f"💫 *Навыки:*\n"
        f"{chr(10).join(skills)}\n\n"
        f"– 📦 Снаряжение –\n\n"
        f"🗡️ Оружие: {char['weapon']}\n"
        f"🛡️ Броня: {char['armor']}\n"
        f"🧪 Артефакт: {char['artifact']}\n\n"
        f"💰 Монет: *{char['coins']}*\n\n"
        f"{SEP}"
    )

def tower_main_keyboard(char):
    is_spell_class = char['class_key'] in SPELL_CLASSES
    markup = InlineKeyboardMarkup(row_width=2)
    if is_spell_class:
        markup.add(
            InlineKeyboardButton("⚔️ Начать",          callback_data="tower_start"),
            InlineKeyboardButton("💫 Заклинания",       callback_data="tower_spells"),
        )
    else:
        markup.add(
            InlineKeyboardButton("⚔️ Начать",          callback_data="tower_start"),
        )
    markup.add(
        InlineKeyboardButton("⬆️ Улучшить статы",  callback_data="tower_upgrade"),
        InlineKeyboardButton("📜 Навыки",           callback_data="tower_skills"),
        InlineKeyboardButton("🎒 Рюкзак",           callback_data="tower_bag"),
        InlineKeyboardButton("🏆 Рекорды",          callback_data="tower_records"),
        InlineKeyboardButton("❌ Удалить персонажа", callback_data="tower_delete_ask"),
    )
    return markup

def class_select_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    for key, cls in CLASSES.items():
        markup.add(InlineKeyboardButton(
            f"{cls['emoji']} {cls['name']}",
            callback_data=f"tower_class_{key}"
        ))
    return markup

# ── Улучшение характеристик UI ────────────────────────────────

def upgrade_text(char):
    cls = CLASSES[char['class_key']]
    max_hp = calc_max_hp(char)
    max_mp = calc_max_mp(char)

    def stat_line(key, label):
        val = char[key]
        cost = cp_cost(val)
        maxed = " *(МАКС)*" if val >= 20 else f" *({cost} ОХ)*"
        return f"{label}: *{val}*{maxed}"

    return (
        f"— – - ⬆️✨ УЛУЧШЕНИЕ ХАРАКТЕРИСТИК ✨⬆️ - – —\n\n"
        f"Имя: *{safe(char['char_name'])}*\n"
        f"Класс: {cls['emoji']} {cls['name']}\n"
        f"⭐ Уровень: *{char['level']}*\n\n"
        f"🪙 Очки Характеристик: *{char['stat_points']}*\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"❤️ ХП: *{char['hp']}/{max_hp}*\n"
        f"⚡ Макс. Мана: *{max_mp}*\n\n"
        f"{stat_line('strength',     '💪 Сила')}\n\n"
        f"{stat_line('agility',      '🎯 Ловкость')}\n\n"
        f"{stat_line('intellect',    '🧠 Интеллект')}\n\n"
        f"{stat_line('constitution', '🫀 Телосложение')}\n\n"
        f"{stat_line('charisma',     '👄 Харизма')}\n\n"
        f"━━━━━━━━━━━━━━━━"
    )

def upgrade_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("+ 💪 Сила",         callback_data="tower_up_strength"),
        InlineKeyboardButton("+ 🎯 Ловкость",      callback_data="tower_up_agility"),
        InlineKeyboardButton("+ 🧠 Интеллект",     callback_data="tower_up_intellect"),
        InlineKeyboardButton("+ 🫀 Телосложение",  callback_data="tower_up_constitution"),
        InlineKeyboardButton("+ 👄 Харизма",       callback_data="tower_up_charisma"),
        InlineKeyboardButton("🔙 Назад",           callback_data="tower_back"),
    )
    return markup

# ── Рюкзак UI ─────────────────────────────────────────────────

def bag_text(char):
    cls = CLASSES[char['class_key']]
    items = get_items(char)
    total_items = sum(items.values())

    if items:
        items_lines = []
        for key, count in items.items():
            c_data = CONSUMABLES.get(key)
            if c_data:
                name = f"{c_data['emoji']} {c_data['name']}"
                items_lines.append(f"{name} ×{count}" if count > 1 else name)
        items_str = "; ".join(items_lines)
    else:
        items_str = "Пусто"

    return (
        f"— – - 🎒 РЮКЗАК И СНАРЯЖЕНИЕ 🎒 - – —\n\n"
        f"Имя: *{safe(char['char_name'])}*\n"
        f"Класс: {cls['emoji']} {cls['name']}\n"
        f"⭐ Уровень: *{char['level']}*\n\n"
        f"💰 Монеты: *{char['coins']}*\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"📦 Экипировка:\n\n"
        f"🗡️ Оружие: {char['weapon']}\n"
        f"🛡️ Броня: {char['armor']}\n"
        f"✨ Артефакт: {char['artifact']}\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"🎒 Содержимое рюкзака (мест {total_items}/20):\n\n"
        f"{items_str}\n\n"
        f"━━━━━━━━━━━━━━━━"
    )

def bag_keyboard():
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("⚔️ Экипировать", callback_data="tower_equip_menu"),
        InlineKeyboardButton("🎒 Изучить",      callback_data="tower_examine"),
        InlineKeyboardButton("🔙 Назад",        callback_data="tower_back"),
    )
    return markup

# ═══════════════════════════════════════════════════════════════
# ХРАНИЛИЩЕ СОСТОЯНИЙ
# ═══════════════════════════════════════════════════════════════

_creating = {}  # {user_id: {'class': key, 'step': str, 'name': str}}

# ═══════════════════════════════════════════════════════════════
# РЕГИСТРАЦИЯ ХЭНДЛЕРОВ
# ═══════════════════════════════════════════════════════════════

def register_tower(bot):

    # ── /tower ────────────────────────────────────────────────
    @bot.message_handler(commands=['tower'])
    def cmd_tower(message):
        user_id = message.from_user.id
        char = get_tower_char(user_id)
        if not char:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("👤 Создать", callback_data="tower_create"))
            bot.send_message(message.chat.id,
                "— – - 🏯 БАШНЯ ХАОСА 🏯 - – —\n\n❌ У тебя ещё не создан персонаж",
                reply_markup=markup)
        else:
            bot.send_message(message.chat.id,
                tower_main_text(char),
                reply_markup=tower_main_keyboard(char),
                parse_mode='Markdown')

    # ── Создать персонажа ─────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tower_create')
    def cb_tower_create(call):
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id,
            "– 👤 СОЗДАНИЕ ПЕРСОНАЖА –\n\nВыбери класс своего персонажа",
            reply_markup=class_select_keyboard())

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_class_'))
    def cb_tower_class(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        class_key = call.data.replace('tower_class_', '')
        if class_key not in CLASSES:
            return
        _creating[user_id] = {'class': class_key, 'step': 'waiting_name'}
        cls = CLASSES[class_key]
        bot.send_message(call.message.chat.id,
            f"– 👤 СОЗДАНИЕ ПЕРСОНАЖА –\n\n"
            f"Класс: {cls['emoji']} *{cls['name']}*\n\n"
            f"Дай имя своему персонажу:",
            parse_mode='Markdown')

    @bot.message_handler(func=lambda msg: msg.from_user.id in _creating
                         and _creating[msg.from_user.id].get('step') == 'waiting_name')
    def handle_tower_name(message):
        user_id = message.from_user.id
        name = message.text.strip()
        if len(name) < 2 or len(name) > 20:
            bot.send_message(message.chat.id,
                "❌ Имя должно быть от 2 до 20 символов. Попробуй ещё раз:")
            return
        _creating[user_id]['name'] = name
        _creating[user_id]['step'] = 'confirm_name'
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Подтвердить", callback_data="tower_name_confirm"),
            InlineKeyboardButton("✍️ Изменить",    callback_data="tower_name_change"),
        )
        bot.send_message(message.chat.id,
            f"Имя персонажа: *{safe(name)}*",
            reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_name_confirm')
    def cb_tower_name_confirm(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        data = _creating.get(user_id)
        if not data or data.get('step') != 'confirm_name':
            bot.send_message(call.message.chat.id, "❌ Начни создание заново через /tower")
            return
        create_tower_char(user_id, data['name'], data['class'])
        _creating.pop(user_id, None)
        char = get_tower_char(user_id)
        bot.send_message(call.message.chat.id,
            tower_main_text(char),
            reply_markup=tower_main_keyboard(char),
            parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_name_change')
    def cb_tower_name_change(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        if user_id in _creating:
            _creating[user_id]['step'] = 'waiting_name'
        bot.send_message(call.message.chat.id,
            "– 👤 СОЗДАНИЕ ПЕРСОНАЖА –\n\nВведи новое имя персонажа:")

    # ── Назад в главное меню ──────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tower_back')
    def cb_tower_back(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char:
            return
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            tower_main_text(char),
            reply_markup=tower_main_keyboard(char),
            parse_mode='Markdown')

    # ── Улучшение характеристик ───────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tower_upgrade')
    def cb_tower_upgrade(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char:
            return
        bot.send_message(call.message.chat.id,
            upgrade_text(char), reply_markup=upgrade_keyboard(), parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_up_'))
    def cb_tower_up_stat(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        stat_key = call.data.replace('tower_up_', '')
        stat_labels = {
            'strength':     '💪 Сила',
            'agility':      '🎯 Ловкость',
            'intellect':    '🧠 Интеллект',
            'constitution': '🫀 Телосложение',
            'charisma':     '👄 Харизма',
        }
        if stat_key not in stat_labels:
            return
        char = get_tower_char(user_id)
        if not char:
            return
        old_val = char[stat_key]
        if old_val >= 20:
            bot.send_message(call.message.chat.id,
                f"❌ *{stat_labels[stat_key]}* уже на максимальном уровне (20)!",
                parse_mode='Markdown')
            return
        cost = cp_cost(old_val)
        if char['stat_points'] < cost:
            bot.send_message(call.message.chat.id,
                f"❌ Недостаточно Очков Характеристик!\n"
                f"Нужно: *{cost} ОХ*, у тебя: *{char['stat_points']} ОХ*",
                parse_mode='Markdown')
            return
        new_val = old_val + 1
        new_points = char['stat_points'] - cost
        conn = get_conn()
        c = conn.cursor()
        c.execute(f'UPDATE tower_chars SET {stat_key}=%s, stat_points=%s WHERE user_id=%s',
                  (new_val, new_points, user_id))
        conn.commit()
        conn.close()
        char = get_tower_char(user_id)
        bot.send_message(call.message.chat.id,
            f"– 🆙 *{stat_labels[stat_key]} повышена!* –\n\n"
            f"{old_val} ➡️ *{new_val}*\n\n"
            f"🪙 Очков Характеристик: *{new_points}*",
            parse_mode='Markdown')
        bot.send_message(call.message.chat.id,
            upgrade_text(char), reply_markup=upgrade_keyboard(), parse_mode='Markdown')

    # ── Рюкзак ────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tower_bag')
    def cb_tower_bag(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char:
            return
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            bag_text(char), reply_markup=bag_keyboard(), parse_mode='Markdown')

    # ── Экипировать ───────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tower_equip_menu')
    def cb_tower_equip_menu(call):
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("🗡️ Оружие",   callback_data="tower_equip_weapon"),
            InlineKeyboardButton("🛡️ Броня",    callback_data="tower_equip_armor"),
            InlineKeyboardButton("🧪 Артефакт", callback_data="tower_equip_artifact"),
            InlineKeyboardButton("🔙 Назад",    callback_data="tower_bag"),
        )
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            "Выбери какой слот экипировки изменить:", reply_markup=markup)

    def equip_slot_keyboard(char, slot_type):
        """Формирует клавиатуру из предметов определённого типа"""
        slot_map = {
            'weapon':   'owned_weapons',
            'armor':    'owned_armors',
            'artifact': 'owned_artifacts',
        }
        equipped = char[slot_type]
        owned = get_owned_equipment(char, slot_map[slot_type])
        markup = InlineKeyboardMarkup(row_width=1)
        for item_name in owned:
            prefix = "✅ " if item_name == equipped else ""
            markup.add(InlineKeyboardButton(
                f"{prefix}{item_name}",
                callback_data=f"tower_do_equip_{slot_type}_{item_name[:30]}"
            ))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_equip_menu"))
        return markup

    for _slot in ['weapon', 'armor', 'artifact']:
        def make_handler(slot):
            @bot.callback_query_handler(func=lambda call, s=slot: call.data == f'tower_equip_{s}')
            def cb_equip_slot(call, s=slot):
                bot.answer_callback_query(call.id)
                char = get_tower_char(call.from_user.id)
                if not char:
                    return
                labels = {'weapon': '🗡️ Оружие', 'armor': '🛡️ Броня', 'artifact': '🧪 Артефакт'}
                try: bot.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
                bot.send_message(call.message.chat.id,
                    f"Выбери {labels[s]}:",
                    reply_markup=equip_slot_keyboard(char, s))
        make_handler(_slot)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_do_equip_'))
    def cb_tower_do_equip(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        parts = call.data.replace('tower_do_equip_', '').split('_', 1)
        if len(parts) < 2:
            return
        slot_type, item_name = parts[0], parts[1]
        if slot_type not in ('weapon', 'armor', 'artifact'):
            return
        conn = get_conn()
        c = conn.cursor()
        c.execute(f'UPDATE tower_chars SET {slot_type}=%s WHERE user_id=%s', (item_name, user_id))
        conn.commit()
        conn.close()
        char = get_tower_char(user_id)
        labels = {'weapon': '🗡️ Оружие', 'armor': '🛡️ Броня', 'artifact': '🧪 Артефакт'}
        bot.send_message(call.message.chat.id,
            f"✅ *{labels[slot_type]}* изменено на *{safe(item_name)}*!",
            parse_mode='Markdown')
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            bag_text(char), reply_markup=bag_keyboard(), parse_mode='Markdown')

    # ── Изучить содержимое рюкзака ────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tower_examine')
    def cb_tower_examine(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char:
            return
        items = get_items(char)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        if not items:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_bag"))
            bot.send_message(call.message.chat.id,
                "— Содержимое рюкзака: —\n\nРюкзак пуст 😔",
                reply_markup=markup)
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for key, count in items.items():
            c_data = CONSUMABLES.get(key)
            if c_data:
                label = f"{c_data['emoji']} {c_data['name']}"
                if count > 1:
                    label += f" ×{count}"
                markup.add(InlineKeyboardButton(label, callback_data=f"tower_item_info_{key}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_bag"))
        bot.send_message(call.message.chat.id,
            "— Содержимое рюкзака: —", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_item_info_'))
    def cb_tower_item_info(call):
        bot.answer_callback_query(call.id)
        item_key = call.data.replace('tower_item_info_', '')
        char = get_tower_char(call.from_user.id)
        if not char:
            return
        items = get_items(char)
        count = items.get(item_key, 0)
        c_data = CONSUMABLES.get(item_key)
        if not c_data:
            return
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton(f"{c_data['emoji']} Использовать", callback_data=f"tower_use_{item_key}"),
            InlineKeyboardButton("🔙 Назад",                        callback_data="tower_examine"),
        )
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            f"{c_data['emoji']} *{c_data['name']}*\n"
            f"Количество: *{count}*\n\n"
            f"{c_data['desc']}",
            reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_use_'))
    def cb_tower_use_item(call):
        bot.answer_callback_query(call.id)
        item_key = call.data.replace('tower_use_', '')
        user_id = call.from_user.id
        char = get_tower_char(user_id)
        if not char:
            return
        items = get_items(char)
        if items.get(item_key, 0) <= 0:
            bot.send_message(call.message.chat.id, "❌ У тебя нет этого предмета!")
            return
        c_data = CONSUMABLES.get(item_key)
        if not c_data:
            return
        # Вне боя можно использовать только зелья хп/маны
        usable_outside = {
            'health_potion', 'big_health_potion',
            'mana_potion', 'big_mana_potion',
            'scroll_heal', 'scroll_mana',
        }
        if item_key not in usable_outside:
            bot.send_message(call.message.chat.id,
                f"⚠️ *{c_data['name']}* можно использовать только в бою!",
                parse_mode='Markdown')
            return
        import random
        max_hp = calc_max_hp(char)
        max_mp = calc_max_mp(char)
        new_hp = char['hp']
        new_mp = char['mp']
        result_text = ""
        if item_key == 'health_potion':
            heal = random.randint(25, 50)
            new_hp = min(max_hp, char['hp'] + heal)
            result_text = f"❤️ +{heal} HP ({new_hp}/{max_hp})"
        elif item_key == 'big_health_potion':
            heal = random.randint(75, 100)
            new_hp = min(max_hp, char['hp'] + heal)
            result_text = f"❤️ +{heal} HP ({new_hp}/{max_hp})"
        elif item_key == 'mana_potion':
            regen = random.randint(15, 30)
            new_mp = min(max_mp, char['mp'] + regen)
            result_text = f"⚡ +{regen} MP ({new_mp}/{max_mp})"
        elif item_key == 'big_mana_potion':
            regen = random.randint(50, 70)
            new_mp = min(max_mp, char['mp'] + regen)
            result_text = f"⚡ +{regen} MP ({new_mp}/{max_mp})"
        elif item_key == 'scroll_heal':
            heal = random.randint(30, 50)
            new_hp = min(max_hp, char['hp'] + heal)
            result_text = f"❤️ +{heal} HP ({new_hp}/{max_hp})"
        elif item_key == 'scroll_mana':
            regen = random.randint(20, 40)
            new_mp = min(max_mp, char['mp'] + regen)
            result_text = f"⚡ +{regen} MP ({new_mp}/{max_mp})"

        # Списываем предмет
        items[item_key] -= 1
        if items[item_key] <= 0:
            del items[item_key]
        save_items(user_id, items)

        conn = get_conn()
        c = conn.cursor()
        c.execute('UPDATE tower_chars SET hp=%s, mp=%s WHERE user_id=%s', (new_hp, new_mp, user_id))
        conn.commit()
        conn.close()

        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            f"✅ Использовал *{c_data['emoji']} {c_data['name']}*\n\n{result_text}",
            parse_mode='Markdown')

    # ── Удаление персонажа ────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tower_delete_ask')
    def cb_tower_delete_ask(call):
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Да, удалить", callback_data="tower_delete_confirm"),
            InlineKeyboardButton("❌ Отмена",       callback_data="tower_delete_cancel"),
        )
        bot.send_message(call.message.chat.id,
            "⚠️ Ты уверен что хочешь удалить персонажа?\n"
            "Весь прогресс будет потерян безвозвратно!",
            reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_delete_confirm')
    def cb_tower_delete_confirm(call):
        bot.answer_callback_query(call.id)
        delete_tower_char(call.from_user.id)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("👤 Создать", callback_data="tower_create"))
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            "— – - 🏯 БАШНЯ ХАОСА 🏯 - – —\n\n❌ У тебя ещё не создан персонаж",
            reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_delete_cancel')
    def cb_tower_delete_cancel(call):
        bot.answer_callback_query(call.id, "Отменено")

    # ── Заглушки ──────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data in [
        'tower_start', 'tower_skills', 'tower_records', 'tower_spells'
    ])
    def cb_tower_stub(call):
        labels = {
            'tower_start':   '⚔️ Режим прохождения башни будет добавлен скоро!',
            'tower_skills':  '📜 Система навыков будет добавлена скоро!',
            'tower_records': '🏆 Рекорды будут добавлены скоро!',
            'tower_spells':  '💫 Система заклинаний будет добавлена скоро!',
        }
        bot.answer_callback_query(call.id, labels.get(call.data, '🔧 В разработке'), show_alert=True)
