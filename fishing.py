import random
import threading

# ============================================================
# РЕДКОСТИ
# ============================================================
RARITY_COMMON    = '⚪'
RARITY_UNCOMMON  = '🟢'
RARITY_RARE      = '🔵'
RARITY_EPIC      = '🟣'
RARITY_LEGENDARY = '🟡'

RARITY_NAMES = {
    RARITY_COMMON:    'Обычный',
    RARITY_UNCOMMON:  'Необычный',
    RARITY_RARE:      'Редкий',
    RARITY_EPIC:      'Эпический',
    RARITY_LEGENDARY: 'Легендарный',
}

RARITY_ORDER = [RARITY_COMMON, RARITY_UNCOMMON, RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY]

# ============================================================
# ТАБЛИЦА РЫБ
# (rarity, emoji, name, strength, price, exp_min, exp_max, reaction_time)
# ============================================================
FISH_TABLE = [
    # ── Обычные 50% ─────────────────────────────────────────
    (RARITY_COMMON, '🐟', 'Анчоус',       5,   40, 10, 50, 2.4),
    (RARITY_COMMON, '🐟', 'Карась',       5,   60, 10, 50, 2.4),
    (RARITY_COMMON, '🐟', 'Плотва',       6,   70, 10, 50, 2.4),
    (RARITY_COMMON, '🐟', 'Краснопёрка',  6,   80, 10, 50, 2.4),
    (RARITY_COMMON, '🐟', 'Окунь',        6,  100, 10, 50, 2.4),
    (RARITY_COMMON, '🐟', 'Бычок',        6,  110, 10, 50, 2.4),
    (RARITY_COMMON, '🐟', 'Салака',       5,   50, 10, 50, 2.4),
    (RARITY_COMMON, '🐟', 'Уклейка',      6,   60, 10, 50, 2.4),
    (RARITY_COMMON, '🐟', 'Пескарь',      6,   70, 10, 50, 2.4),
    (RARITY_COMMON, '🐟', 'Молодой карп', 7,  120, 10, 50, 2.4),
    # ── Необычные 25% ───────────────────────────────────────
    (RARITY_UNCOMMON, '🐠', 'Лещ',           8,  180, 50, 100, 1.9),
    (RARITY_UNCOMMON, '🐠', 'Голавль',       8,  200, 50, 100, 1.9),
    (RARITY_UNCOMMON, '🐠', 'Язь',           9,  220, 50, 100, 1.9),
    (RARITY_UNCOMMON, '🐠', 'Форель',        9,  260, 50, 100, 1.9),
    (RARITY_UNCOMMON, '🐠', 'Щука',          10,  320, 50, 100, 1.9),
    (RARITY_UNCOMMON, '🐠', 'Сазан',         10,  350, 50, 100, 1.9),
    (RARITY_UNCOMMON, '🐠', 'Камбала',       9,  240, 50, 100, 1.9),
    (RARITY_UNCOMMON, '🐠', 'Морской окунь', 9,  280, 50, 100, 1.9),
    # ── Редкие 15% ──────────────────────────────────────────
    (RARITY_RARE, '🦈', 'Судак',      11,   500, 100, 250, 1.4),
    (RARITY_RARE, '🦈', 'Амур',       12,   600, 100, 250, 1.4),
    (RARITY_RARE, '🦈', 'Осётр',     13,   750, 100, 250, 1.4),
    (RARITY_RARE, '🦈', 'Сом',       14,   900, 100, 250, 1.4),
    (RARITY_RARE, '🦈', 'Рыба-меч',  15,  1200, 100, 250, 1.4),
    (RARITY_RARE, '🦈', 'Тунец',     13,   800, 100, 250, 1.4),
    # ── Эпические 7% ────────────────────────────────────────
    (RARITY_EPIC, '🐋', 'Гигантская щука', 17, 2500, 250, 500, 0.9),
    (RARITY_EPIC, '🐋', 'Золотой карп',    16, 2200, 250, 500, 0.9),
    (RARITY_EPIC, '🐋', 'Титан-сом',       18, 3200, 250, 500, 0.9),
    (RARITY_EPIC, '🐋', 'Лунная форель',   15, 2800, 250, 500, 0.9),
    # ── Легендарные 3% ──────────────────────────────────────
    (RARITY_LEGENDARY, '🐉', 'Рыба-Дракон',  21, 7000, 500, 1000, 0.4),
    (RARITY_LEGENDARY, '🐲', 'Древний осётр',24, 9000, 500, 1000, 0.4),
]

FISH_BY_RARITY = {r: [f for f in FISH_TABLE if f[0] == r] for r in RARITY_ORDER}

RARITY_BASE_CHANCES = {
    RARITY_COMMON:    50.0,
    RARITY_UNCOMMON:  25.0,
    RARITY_RARE:      15.0,
    RARITY_EPIC:       7.0,
    RARITY_LEGENDARY:  3.0,
}

# ============================================================
# СНАРЯЖЕНИЕ
# ============================================================
LEVEL_EMOJIS = {1: '⚪', 2: '🟢', 3: '🔵', 4: '🟣', 5: '🟡'}
MAX_LEVEL = 5

ROD_LEVELS = {
    1: {'damage': 1, 'time_bonus': 0.0, 'price': 0},
    2: {'damage': 2, 'time_bonus': 0.2, 'price': 5000},
    3: {'damage': 3, 'time_bonus': 0.4, 'price': 25000},
    4: {'damage': 4, 'time_bonus': 0.7, 'price': 120000},
    5: {'damage': 5, 'time_bonus': 1.0, 'price': 500000},
}
LINE_LEVELS = {
    1: {'max_tension': 10, 'start_tension': 1, 'price': 0},
    2: {'max_tension': 13, 'start_tension': 3, 'price': 4000},
    3: {'max_tension': 17, 'start_tension': 5, 'price': 20000},
    4: {'max_tension': 20, 'start_tension': 7, 'price': 100000},
    5: {'max_tension': 25, 'start_tension': 9, 'price': 600000},
}
HOOK_LEVELS = {
    1: {'hook_chance': 0,  'rare_bonus': 0, 'price': 0},
    2: {'hook_chance': 5,  'rare_bonus': 1, 'price': 6000},
    3: {'hook_chance': 10, 'rare_bonus': 2, 'price': 30000},
    4: {'hook_chance': 15, 'rare_bonus': 4, 'price': 150000},
    5: {'hook_chance': 25, 'rare_bonus': 7, 'price': 500000},
}
REEL_LEVELS = {
    1: {'loosen': 2, 'price': 0},
    2: {'loosen': 3, 'price': 5000},
    3: {'loosen': 4, 'price': 30000},
    4: {'loosen': 6, 'price': 150000},
    5: {'loosen': 8, 'price': 450000},
}

EQUIPMENT_ITEMS = {
    'rod':  {'name': 'Удочку 🎣',  'levels': ROD_LEVELS,  'col': 'rod_level'},
    'line': {'name': 'Леску 🧵',   'levels': LINE_LEVELS, 'col': 'line_level'},
    'hook': {'name': 'Крючок 🪝',  'levels': HOOK_LEVELS, 'col': 'hook_level'},
    'reel': {'name': 'Катушку ⚙️', 'levels': REEL_LEVELS, 'col': 'reel_level'},
}

# ============================================================
# ЛОВУШКИ
# ============================================================
TRAP_SLOTS = 4
TRAP_REWARD_TABLE = [
    (RARITY_COMMON,    75.0),
    (RARITY_UNCOMMON,  24.8),
    ('treasure',        0.2),
]

# ============================================================
# АКТИВНЫЕ СЕССИИ (в памяти)
# ============================================================
fishing_sessions = {}
sessions_lock    = threading.Lock()

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def get_equipment(conn, user_id):
    c = conn.cursor()
    c.execute(
        'SELECT rod_level, line_level, hook_level, reel_level FROM users WHERE user_id=%s',
        (user_id,)
    )
    row = c.fetchone()
    if not row:
        return {'rod': 1, 'line': 1, 'hook': 1, 'reel': 1}
    return {
        'rod':  max(1, row[0] or 1),
        'line': max(1, row[1] or 1),
        'hook': max(1, row[2] or 1),
        'reel': max(1, row[3] or 1),
    }

def random_fish(rare_bonus=0):
    """Выбирает случайную рыбу с учётом бонуса редкости."""
    common_base = RARITY_BASE_CHANCES[RARITY_COMMON]
    common_new  = max(0.0, common_base - rare_bonus)
    shifted     = common_base - common_new

    non_common_base  = {r: RARITY_BASE_CHANCES[r] for r in RARITY_ORDER if r != RARITY_COMMON}
    non_common_total = sum(non_common_base.values())

    chances = {RARITY_COMMON: common_new}
    for r in RARITY_ORDER:
        if r == RARITY_COMMON: continue
        chances[r] = non_common_base[r] + shifted * (non_common_base[r] / non_common_total)

    rarities = list(chances.keys())
    weights  = [chances[r] for r in rarities]
    chosen   = random.choices(rarities, weights=weights, k=1)[0]
    return random.choice(FISH_BY_RARITY[chosen])
    # → (rarity, emoji, name, strength, price, exp_min, exp_max, reaction_time)

def random_trap_reward():
    """Случайная награда с ловушки."""
    cats    = [c for c, _ in TRAP_REWARD_TABLE]
    weights = [w for _, w in TRAP_REWARD_TABLE]
    chosen  = random.choices(cats, weights=weights, k=1)[0]
    if chosen == 'treasure':
        return 'treasure', None
    return chosen, random.choice(FISH_BY_RARITY[chosen])

def fish_action(is_epic_or_legendary=False):
    """Случайное действие рыбы. → (text, tension_delta, strength_delta)"""
    roll = random.random()
    if is_epic_or_legendary:
        if roll < 0.30:
            return "🐟 Рыба дёрнулась!\n+1 к натяжению лески.", 1, 0
        elif roll < 0.60:
            return "🐟 Рыба спокойна... —\nНичего не происходит.", 0, 0
        elif roll < 0.70:
            return "🐟 Рыба резко рванула!\n+2 к натяжению лески.", 2, 0
        elif roll < 0.85:
            return "🐟 Рыба поддаётся...\n-1 к натяжению лески и -1 к Силе рыбы.", -1, -1
        else:
            return "🐟 Рыба восстанавливается...\n+1 Силы рыбы", 0, 1
    else:
        if roll < 0.35:
            return "🐟 Рыба дёрнулась!\n+1 к натяжению лески.", 1, 0
        elif roll < 0.70:
            return "🐟 Рыба спокойна... —\nНичего не происходит.", 0, 0
        elif roll < 0.85:
            return "🐟 Рыба поддаётся...\n-1 к натяжению лески и -1 к Силе рыбы.", -1, -1
        else:
            return "🐟 Рыба восстанавливается...\n+1 Силы рыбы", 0, 1
        
def make_bar(current, max_val, width=10):
    current = max(0, current)
    filled  = round(current / max_val * width) if max_val > 0 else 0
    filled  = min(filled, width)
    return '█' * filled + '░' * (width - filled)

def strength_text(cur, mx):
    return f"{make_bar(cur, mx)} ({cur}/{mx})"

def tension_text(cur, mx):
    return f"{make_bar(cur, mx)} ({cur}/{mx})"

def lv(n):
    return LEVEL_EMOJIS.get(n, '⚪')

# ── Тексты меню ─────────────────────────────────────────────

SEP  = "— – - - - - - - - - - - - - - - - - - – —"
SEP2 = "• – – – – – – – – – – – – – – – – – – •"

def main_menu_text(money, bait, eq):
    return (
        f"— – - 🎣 РЫБАЛКА 🎣 - – —\n\n"
        f"Денег: 💵 {money}\n"
        f"Наживок: 🪱 {bait}\n\n"
        f"{SEP2}\n\n"
        f"🎣 Удочка: {lv(eq['rod'])} Ур. {eq['rod']}\n"
        f"🧵 Леска: {lv(eq['line'])} Ур. {eq['line']}\n"
        f"🪝 Крючок: {lv(eq['hook'])} Ур. {eq['hook']}\n"
        f"⚙️ Катушка: {lv(eq['reel'])} Ур. {eq['reel']}\n\n"
        f"{SEP}"
    )

def equipment_menu_text(money, bait, eq):
    rod  = ROD_LEVELS[eq['rod']]
    line = LINE_LEVELS[eq['line']]
    hook = HOOK_LEVELS[eq['hook']]
    reel = REEL_LEVELS[eq['reel']]
    return (
        f"— – - 🧰 *СНАРЯЖЕНИЕ* 🧰 - – —\n\n"
        f"Денег: 💵 {money}\n"
        f"Наживок: 🪱 {bait}\n\n"
        f"{SEP2}\n\n"
        f"🎣 Удочка: {lv(eq['rod'])} Ур. {eq['rod']}\n\n"
        f"🔸Бонус урона: +{rod['damage']}\n"
        f"⏱️Бонус времени реакции: +{rod['time_bonus']} сек.\n\n"
        f"{SEP2}\n\n"
        f"🧵 Леска: {lv(eq['line'])} Ур. {eq['line']}\n\n"
        f"❤️Максимум натяжения: {line['max_tension']}\n\n"
        f"{SEP2}\n\n"
        f"🪝 Крючок: {lv(eq['hook'])} Ур. {eq['hook']}\n\n"
        f"⚡Шанс успешной подсечки: +{hook['hook_chance']}%\n"
        f"⭐Бонус редкой рыбы: +{hook['rare_bonus']}%\n\n"
        f"{SEP2}\n\n"
        f"⚙️ Катушка: {lv(eq['reel'])} Ур. {eq['reel']}\n\n"
        f"🧘Ослабление: -{reel['loosen']}\n\n"
        f"{SEP}"
    )

def upgrade_preview_text(item_key, current_level):
    """→ (text, price) или (None, None) если макс."""
    next_lv = current_level + 1
    if next_lv > MAX_LEVEL:
        return None, None

    item  = EQUIPMENT_ITEMS[item_key]
    name  = item['name']
    lvls  = item['levels']
    cur   = lvls[current_level]
    nxt   = lvls[next_lv]
    price = nxt['price']

    if item_key == 'rod':
        stats = (
            f"🔸Бонус урона: +{cur['damage']} –> +{nxt['damage']}\n"
            f"⏱️Бонус времени реакции: +{cur['time_bonus']} сек. –> +{nxt['time_bonus']} сек."
        )
    elif item_key == 'line':
        stats = f"❤️Максимум натяжения: {cur['max_tension']} –> {nxt['max_tension']}"
    elif item_key == 'hook':
        stats = (
            f"⚡Шанс успешной подсечки: +{cur['hook_chance']}% –> +{nxt['hook_chance']}%\n"
            f"⭐Бонус редкой рыбы: +{cur['rare_bonus']}% –> +{nxt['rare_bonus']}%"
        )
    else:  # reel
        stats = f"🧘Ослабление: -{cur['loosen']} –> -{nxt['loosen']}"

    text = (
        f"⏫ Улучшить {name}\n"
        f"{lv(current_level)} Ур. {current_level} —> {lv(next_lv)} Ур. {next_lv}\n\n"
        f"{stats}\n\n"
        f"Цена: 💵 {price:,}\n\n"
        f"Улучшить?"
    )
    return text, price

def fight_text(fish_name, fish_emoji, cur_str, max_str, cur_ten, max_ten, action_note=""):
    note_line = f"\n{action_note}\n" if action_note else "\n"
    return (
        f"🎣 Рыба на крючке!\n"
        f"{note_line}"
        f"{fish_emoji} ???\n"
        f"Сила рыбы: {strength_text(cur_str, max_str)}\n"
        f"Натяжение лески: {tension_text(cur_ten, max_ten)}"
    )
