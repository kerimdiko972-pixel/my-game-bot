import psycopg2
import psycopg2.extras
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

# ═══════════════════════════════════════════════════════════════
# КОНСТАНТЫ КЛАССОВ
# ═══════════════════════════════════════════════════════════════

CLASSES = {
    "warrior": {
        "name": "Воин",
        "emoji": "⚔️",
        "base_hp": 130, "base_mp": 48,
        "k1": 3, "k2": 1,
        "stats": {"strength": 8, "agility": 5, "intellect": 3,
                  "constitution": 8, "speed": 6, "charisma": 5},
        "lead": ["strength", "constitution"],
    },
    "barbarian": {
        "name": "Варвар",
        "emoji": "🪓",
        "base_hp": 140, "base_mp": 42,
        "k1": 3, "k2": 1,
        "stats": {"strength": 9, "agility": 4, "intellect": 2,
                  "constitution": 9, "speed": 6, "charisma": 3},
        "lead": ["strength", "constitution"],
    },
    "assassin": {
        "name": "Ассасин",
        "emoji": "🗡️",
        "base_hp": 90, "base_mp": 54,
        "k1": 2, "k2": 2,
        "stats": {"strength": 6, "agility": 9, "intellect": 4,
                  "constitution": 4, "speed": 7, "charisma": 6},
        "lead": ["agility", "charisma"],
    },
    "ranger": {
        "name": "Следопыт",
        "emoji": "🏹",
        "base_hp": 100, "base_mp": 54,
        "k1": 2, "k2": 2,
        "stats": {"strength": 6, "agility": 8, "intellect": 4,
                  "constitution": 5, "speed": 7, "charisma": 4},
        "lead": ["agility", "intellect"],
    },
    "mage": {
        "name": "Волшебник",
        "emoji": "🪄",
        "base_hp": 100, "base_mp": 84,
        "k1": 1, "k2": 3,
        "stats": {"strength": 2, "agility": 4, "intellect": 9,
                  "constitution": 5, "speed": 10, "charisma": 6},
        "lead": ["intellect", "charisma"],
    },
    "warlock": {
        "name": "Колдун",
        "emoji": "🔮",
        "base_hp": 120, "base_mp": 78,
        "k1": 1, "k2": 3,
        "stats": {"strength": 3, "agility": 4, "intellect": 8,
                  "constitution": 7, "speed": 8, "charisma": 8},
        "lead": ["intellect", "charisma"],
    },
}

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
            best_floor      INTEGER DEFAULT 0
        )
    ''')
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

def create_tower_char(user_id, char_name, class_key):
    cls = CLASSES[class_key]
    stats = cls["stats"]
    base_hp = cls["base_hp"]
    base_mp = cls["base_mp"]
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO tower_chars
        (user_id, char_name, class_key, level, exp, stat_points, mastery_bonus,
         hp, mp, strength, agility, intellect, constitution, speed, charisma,
         weapon, armor, artifact, coins, best_floor)
        VALUES (%s,%s,%s,1,0,0,1,%s,%s,%s,%s,%s,%s,%s,%s,
                'Голые кулаки','Лёгкая одежда','Нет',0,0)
        ON CONFLICT (user_id) DO NOTHING
    ''', (
        user_id, char_name, class_key,
        base_hp, base_mp,
        stats["strength"], stats["agility"], stats["intellect"],
        stats["constitution"], stats["speed"], stats["charisma"]
    ))
    conn.commit()
    conn.close()

def delete_tower_char(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM tower_chars WHERE user_id=%s', (user_id,))
    conn.commit()
    conn.close()

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

# ═══════════════════════════════════════════════════════════════
# UI ТЕКСТЫ
# ═══════════════════════════════════════════════════════════════

def tower_main_text(char):
    cls = CLASSES[char['class_key']]
    max_hp = calc_max_hp(char)
    max_mp = calc_max_mp(char)
    lvl = char['level']
    exp = char['exp']
    exp_next = exp_for_next_level(lvl)
    mb = mastery_bonus(lvl)

    safe_name = char['char_name'].replace('_', '\\_').replace('*', '\\*')

    # Характеристики — ведущие отмечены звездой
    lead = cls['lead']
    def stat_line(key):
        star = "⭐" if key in lead else "  "
        return f"{star}{STAT_NAMES[key]}: {char[key]}"

    skills = []
    for i, slot in enumerate(['skill_1', 'skill_2', 'skill_3'], 1):
        val = char[slot] or '—'
        num = ['1️⃣', '2️⃣', '3️⃣'][i-1]
        skills.append(f"{num} {val}")

    text = (
        f"— – - 🏯 БАШНЯ ХАОСА 🏯 - – —\n\n"
        f"🎖️ Твой рекорд: *{char['best_floor']}* этаж\n\n"
        f"– *{safe_name}* –\n"
        f"Класс: {cls['emoji']} {cls['name']}\n"
        f"Уровень: *{lvl}* (⭐ {exp}/{exp_next} опыта)\n"
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
    return text

def tower_main_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⚔️ Начать",          callback_data="tower_start"),
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

# ═══════════════════════════════════════════════════════════════
# РЕГИСТРАЦИЯ ХЭНДЛЕРОВ
# ═══════════════════════════════════════════════════════════════

# Временное хранилище при создании персонажа: {user_id: {'class': key, 'step': ...}}
_creating = {}

def register_tower(bot):

    # ── /tower ────────────────────────────────────────────────
    @bot.message_handler(commands=['tower'])
    def cmd_tower(message):
        user_id = message.from_user.id
        char = get_tower_char(user_id)
        if not char:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("👤 Создать", callback_data="tower_create"))
            bot.send_message(
                message.chat.id,
                "— – - 🏯 БАШНЯ ХАОСА 🏯 - – —\n\n"
                "❌ У тебя ещё не создан персонаж",
                reply_markup=markup
            )
        else:
            bot.send_message(
                message.chat.id,
                tower_main_text(char),
                reply_markup=tower_main_keyboard(),
                parse_mode='Markdown'
            )

    # ── Нажали "Создать" ──────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tower_create')
    def cb_tower_create(call):
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "– 👤 СОЗДАНИЕ ПЕРСОНАЖА –\n\n"
            "Выбери класс своего персонажа",
            reply_markup=class_select_keyboard()
        )

    # ── Выбор класса ─────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_class_'))
    def cb_tower_class(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        class_key = call.data.replace('tower_class_', '')
        if class_key not in CLASSES:
            return
        _creating[user_id] = {'class': class_key, 'step': 'waiting_name'}
        bot.send_message(
            call.message.chat.id,
            "– 👤 СОЗДАНИЕ ПЕРСОНАЖА –\n\n"
            f"Класс: {CLASSES[class_key]['emoji']} *{CLASSES[class_key]['name']}*\n\n"
            "Дай имя своему персонажу:",
            parse_mode='Markdown'
        )

    # ── Ввод имени ────────────────────────────────────────────
    @bot.message_handler(func=lambda msg: msg.from_user.id in _creating
                         and _creating[msg.from_user.id].get('step') == 'waiting_name')
    def handle_tower_name(message):
        user_id = message.from_user.id
        name = message.text.strip()
        if len(name) < 2 or len(name) > 20:
            bot.send_message(message.chat.id, "❌ Имя должно быть от 2 до 20 символов. Попробуй ещё раз:")
            return
        _creating[user_id]['name'] = name
        _creating[user_id]['step'] = 'confirm_name'

        safe_name = name.replace('_', '\\_').replace('*', '\\*')
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Подтвердить", callback_data="tower_name_confirm"),
            InlineKeyboardButton("✍️ Изменить",    callback_data="tower_name_change"),
        )
        bot.send_message(
            message.chat.id,
            f"Имя персонажа: *{safe_name}*",
            reply_markup=markup,
            parse_mode='Markdown'
        )

    # ── Подтверждение имени ───────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tower_name_confirm')
    def cb_tower_name_confirm(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        data = _creating.get(user_id)
        if not data or data.get('step') != 'confirm_name':
            bot.send_message(call.message.chat.id, "❌ Начни создание заново через /tower")
            return

        char_name = data['name']
        class_key = data['class']
        create_tower_char(user_id, char_name, class_key)
        _creating.pop(user_id, None)

        char = get_tower_char(user_id)
        bot.send_message(
            call.message.chat.id,
            tower_main_text(char),
            reply_markup=tower_main_keyboard(),
            parse_mode='Markdown'
        )

    # ── Изменить имя ──────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tower_name_change')
    def cb_tower_name_change(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        if user_id in _creating:
            _creating[user_id]['step'] = 'waiting_name'
        bot.send_message(
            call.message.chat.id,
            "– 👤 СОЗДАНИЕ ПЕРСОНАЖА –\n\n"
            "Введи новое имя персонажа:"
        )

    # ── Удалить — подтверждение ───────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tower_delete_ask')
    def cb_tower_delete_ask(call):
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Да, удалить", callback_data="tower_delete_confirm"),
            InlineKeyboardButton("❌ Отмена",       callback_data="tower_delete_cancel"),
        )
        bot.send_message(
            call.message.chat.id,
            "⚠️ Ты уверен что хочешь удалить персонажа?\n"
            "Весь прогресс будет потерян безвозвратно!",
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_delete_confirm')
    def cb_tower_delete_confirm(call):
        bot.answer_callback_query(call.id)
        delete_tower_char(call.from_user.id)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("👤 Создать", callback_data="tower_create"))
        bot.send_message(
            call.message.chat.id,
            "— – - 🏯 БАШНЯ ХАОСА 🏯 - – —\n\n"
            "❌ У тебя ещё не создан персонаж",
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_delete_cancel')
    def cb_tower_delete_cancel(call):
        bot.answer_callback_query(call.id, "Отменено")

    # ── Заглушки для кнопок (пока не реализованы) ────────────
    @bot.callback_query_handler(func=lambda call: call.data in [
        'tower_start', 'tower_upgrade', 'tower_skills', 'tower_bag', 'tower_records'
    ])
    def cb_tower_stub(call):
        labels = {
            'tower_start':   '⚔️ Режим прохождения башни будет добавлен скоро!',
            'tower_upgrade': '⬆️ Улучшение статов будет добавлено скоро!',
            'tower_skills':  '📜 Система навыков будет добавлена скоро!',
            'tower_bag':     '🎒 Рюкзак будет добавлен скоро!',
            'tower_records': '🏆 Рекорды будут добавлены скоро!',
        }
        bot.answer_callback_query(call.id, labels.get(call.data, '🔧 В разработке'), show_alert=True)
