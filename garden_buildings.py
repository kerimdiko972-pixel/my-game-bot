"""
garden_buildings.py — здания фермы (Кухня, Кадка, Варочный котёл, Винодельня)
Подключение из bot.py:
    from garden_buildings import register_buildings_handlers
    register_buildings_handlers(bot, get_conn, get_user, add_exp, spend_money)
"""
import threading
import time as _time
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ============================================================
# ДАННЫЕ
# ============================================================

BUILDINGS = {
    'kitchen': {'name': 'Кухня',        'emoji': '🍳', 'unlock_price': 0,       'slots': 5},
    'barrel':  {'name': 'Кадка',        'emoji': '🪵', 'unlock_price': 10000,   'slots': 5},
    'cauldron':{'name': 'Варочный котёл','emoji': '🍯', 'unlock_price': 50000,   'slots': 5},
    'winery':  {'name': 'Винодельня',   'emoji': '🍷', 'unlock_price': 120000,  'slots': 5},
}

# Рецепты: recipe_key → данные
RECIPES = {
    # ── Кухня / Салаты ──────────────────────────────────────
    'salad_veg':    {'building': 'kitchen', 'category': 'Салаты',
                     'name': 'Овощной салат',   'emoji': '🥗',
                     'ingredients': {'🍅': 1, '🥒': 1, '🫑': 1},
                     'time_min': 25, 'price': 500,  'exp': 8},
    'salad_summer': {'building': 'kitchen', 'category': 'Салаты',
                     'name': 'Летний салат',     'emoji': '🥗',
                     'ingredients': {'🥬': 1, '🍅': 1, '🥒': 1},
                     'time_min': 30, 'price': 360,  'exp': 8},
    'salad_spicy':  {'building': 'kitchen', 'category': 'Салаты',
                     'name': 'Острый салат',     'emoji': '🥗',
                     'ingredients': {'🌶️': 1, '🍅': 1, '🫑': 1},
                     'time_min': 25, 'price': 590,  'exp': 10},
    'salad_cabbage':{'building': 'kitchen', 'category': 'Салаты',
                     'name': 'Капустный салат',  'emoji': '🥗',
                     'ingredients': {'🥬': 1, '🥕': 1},
                     'time_min': 20, 'price': 140,  'exp': 6},
    'soup_veg':     {'building': 'kitchen', 'category': 'Супы',
                     'name': 'Овощной суп',      'emoji': '🍲',
                     'ingredients': {'🥕': 1, '🥔': 1, '🍅': 1},
                     'time_min': 60, 'price': 460,  'exp': 18},
    'soup_borsch':  {'building': 'kitchen', 'category': 'Супы',
                     'name': 'Борщ',              'emoji': '🍲',
                     'ingredients': {'🥔': 1, '🥬': 1, '🥕': 1, '🍅': 1},
                     'time_min': 90, 'price': 580,  'exp': 22},
    'soup_farm':    {'building': 'kitchen', 'category': 'Супы',
                     'name': 'Фермерский суп',   'emoji': '🍲',
                     'ingredients': {'🥔': 1, '🥕': 1, '🌽': 1},
                     'time_min': 70, 'price': 620,  'exp': 20},
    'soup_spicy':   {'building': 'kitchen', 'category': 'Супы',
                     'name': 'Острый суп',        'emoji': '🍲',
                     'ingredients': {'🌶️': 1, '🍅': 1, '🫑': 1},
                     'time_min': 80, 'price': 840,  'exp': 24},
    'fried_egg':    {'building': 'kitchen', 'category': 'Жареное',
                     'name': 'Жареные баклажаны', 'emoji': '🍆',
                     'ingredients': {'🍆': 2},
                     'time_min': 30, 'price': 540,  'exp': 16},
    'fried_potato': {'building': 'kitchen', 'category': 'Жареное',
                     'name': 'Картошка фри',      'emoji': '🍟',
                     'ingredients': {'🥔': 3},
                     'time_min': 30, 'price': 380,  'exp': 12},
    'popcorn':      {'building': 'kitchen', 'category': 'Жареное',
                     'name': 'Попкорн',            'emoji': '🍿',
                     'ingredients': {'🌽': 3},
                     'time_min': 15, 'price': 1080, 'exp': 14},
    # ── Кадка / Соленья ─────────────────────────────────────
    'pickled_cuc':  {'building': 'barrel', 'category': 'Соленья',
                     'name': 'Маринованные огурцы',   'emoji': '🫙',
                     'ingredients': {'🥒': 4},
                     'time_min': 60, 'price': 510,  'exp': 16},
    'pickled_tom':  {'building': 'barrel', 'category': 'Соленья',
                     'name': 'Маринованные помидоры', 'emoji': '🫙',
                     'ingredients': {'🍅': 4},
                     'time_min': 70, 'price': 770,  'exp': 18},
    'pickled_pep':  {'building': 'barrel', 'category': 'Соленья',
                     'name': 'Маринованный перец',    'emoji': '🫙',
                     'ingredients': {'🫑': 3},
                     'time_min': 80, 'price': 770,  'exp': 18},
    'pickled_cab':  {'building': 'barrel', 'category': 'Соленья',
                     'name': 'Квашеная капуста',      'emoji': '🫙',
                     'ingredients': {'🥬': 3},
                     'time_min': 90, 'price': 310,  'exp': 14},
    'pickled_car':  {'building': 'barrel', 'category': 'Соленья',
                     'name': 'Маринованная морковь',  'emoji': '🫙',
                     'ingredients': {'🥕': 4},
                     'time_min': 60, 'price': 320,  'exp': 14},
    'compote_apple':{'building': 'barrel', 'category': 'Компоты',
                     'name': 'Яблочный компот',       'emoji': '🥤',
                     'ingredients': {'🍎': 5},
                     'time_min': 45, 'price': 2100, 'exp': 22},
    'compote_straw':{'building': 'barrel', 'category': 'Компоты',
                     'name': 'Клубничный морс',       'emoji': '🥤',
                     'ingredients': {'🍓': 4},
                     'time_min': 40, 'price': 1960, 'exp': 24},
    'compote_mix':  {'building': 'barrel', 'category': 'Компоты',
                     'name': 'Ассорти компот',        'emoji': '🥤',
                     'ingredients': {'🍎': 2, '🍓': 2, '🍒': 1},
                     'time_min': 60, 'price': 3040, 'exp': 28},
    # ── Варочный котёл ───────────────────────────────────────
    'jam_straw':    {'building': 'cauldron', 'category': 'Варенья',
                     'name': 'Клубничное варенье',    'emoji': '🫙',
                     'ingredients': {'🍓': 3},
                     'time_min': 60,  'price': 1890, 'exp': 30},
    'jam_berry':    {'building': 'cauldron', 'category': 'Варенья',
                     'name': 'Ягодный джем',          'emoji': '🫙',
                     'ingredients': {'🍓': 2, '🍒': 2},
                     'time_min': 80,  'price': 3800, 'exp': 36},
    'jam_tropical': {'building': 'cauldron', 'category': 'Варенья',
                     'name': 'Тропический джем',      'emoji': '🫙🌴',
                     'ingredients': {'🥭': 2, '🍍': 1},
                     'time_min': 120, 'price': 6720, 'exp': 42},
    'marmalade':    {'building': 'cauldron', 'category': 'Варенья',
                     'name': 'Апельсиновый мармелад', 'emoji': '🍭🍊',
                     'ingredients': {'🍊': 3},
                     'time_min': 90,  'price': 1440, 'exp': 34},
    # ── Винодельня ───────────────────────────────────────────
    'beer':   {'building': 'winery', 'category': 'Напитки',
               'name': 'Пиво',    'emoji': '🍺',
               'ingredients': {'🌾': 6},
               'time_min': 120, 'price': 300,   'exp': 40, 'aging': False},
    'cider':  {'building': 'winery', 'category': 'Напитки',
               'name': 'Сидр',   'emoji': '🍾',
               'ingredients': {'🍎': 5},
               'time_min': 120, 'price': 3900,  'exp': 55, 'aging': True},
    'wine':   {'building': 'winery', 'category': 'Напитки',
               'name': 'Вино',   'emoji': '🍷',
               'ingredients': {'🍇': 6},
               'time_min': 180, 'price': 9000,  'exp': 70, 'aging': True},
    'liqueur':{'building': 'winery', 'category': 'Напитки',
               'name': 'Ликёр',  'emoji': '🥃',
               'ingredients': {'any_fruit': 4},
               'time_min': 240, 'price': 10500, 'exp': 85, 'aging': False},
}

# Фрукты/ягоды для ликёра
FRUITS = {'🍎', '🍊', '🥭', '🍒', '🍓', '🍇', '🍉', '🍈', '🍍'}

# Выдержка для вина и сидра
AGING_MULTIPLIERS = [
    (24 * 60,  4.0),
    (6  * 60,  2.0),
    (3  * 60,  1.5),
    (60,       1.2),
]

# Бонус XP за качество
XP_QUALITY_BONUS = {1: 1.0, 2: 1.2, 3: 1.5, 4: 2.0, 5: 3.0}

def quality_str(q):
    return {1:'⭐',2:'⭐⭐',3:'⭐⭐⭐',4:'⭐⭐⭐⭐',5:'⭐⭐⭐⭐⭐'}.get(q,'⭐')

def aging_mult(finished_at_iso):
    """Возвращает множитель выдержки."""
    finished = datetime.fromisoformat(finished_at_iso)
    elapsed  = (datetime.now() - finished).total_seconds() / 60
    for mins, mult in AGING_MULTIPLIERS:
        if elapsed >= mins:
            return mult
    return 1.0

def aging_time_str(finished_at_iso):
    finished = datetime.fromisoformat(finished_at_iso)
    elapsed  = (datetime.now() - finished).total_seconds()
    h = int(elapsed // 3600)
    m = int((elapsed % 3600) // 60)
    if h > 0:
        return f"{h} ч. {m} мин."
    return f"{m} мин."

def format_time(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    if m >= 60:
        h = m // 60; m = m % 60
        return f"{h} ч. {m} мин."
    return f"{m} мин. {s} сек."

SEP = "• — — — — — — — — — — — •"

# ============================================================
# DB ФУНКЦИИ
# ============================================================
_get_conn    = None
_get_user    = None
_add_exp     = None
_spend_money = None

def _init_buildings_db():
    conn = _get_conn()
    c    = conn.cursor()
    # Разблокированные здания
    c.execute('''CREATE TABLE IF NOT EXISTS farm_buildings (
        user_id  BIGINT,
        bld_key  TEXT,
        unlocked BOOLEAN DEFAULT FALSE,
        PRIMARY KEY (user_id, bld_key)
    )''')
    # Слоты готовки
    c.execute('''CREATE TABLE IF NOT EXISTS cooking_slots (
        id           SERIAL PRIMARY KEY,
        user_id      BIGINT,
        bld_key      TEXT,
        slot_num     INTEGER,
        recipe_key   TEXT    DEFAULT NULL,
        started_at   TEXT    DEFAULT NULL,
        finished_at  TEXT    DEFAULT NULL,
        is_done      BOOLEAN DEFAULT FALSE,
        ing_used     TEXT    DEFAULT NULL,
        quality      INTEGER DEFAULT 0,
        UNIQUE (user_id, bld_key, slot_num)
    )''')
    # Инвентарь товаров
    c.execute('''CREATE TABLE IF NOT EXISTS goods_inventory (
        user_id    BIGINT,
        recipe_key TEXT,
        quality    INTEGER,
        count      INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, recipe_key, quality)
    )''')
    conn.commit()

    # Миграция: убедимся что у всех пользователей есть строки зданий
    try:
        c.execute("ALTER TABLE cooking_slots ADD COLUMN IF NOT EXISTS ing_used TEXT DEFAULT NULL")
        conn.commit()
    except: conn.rollback()
    try:
        c.execute('''ALTER TABLE cooking_slots
                     ADD CONSTRAINT cooking_slots_unique
                     UNIQUE (user_id, bld_key, slot_num)''')
        conn.commit()
    except: conn.rollback()
    try:
        c.execute("ALTER TABLE cooking_slots ADD COLUMN IF NOT EXISTS quality INTEGER DEFAULT 0")
        conn.commit()
    except: conn.rollback()

    conn.close()

def _ensure_building_rows(user_id):
    conn = _get_conn()
    c    = conn.cursor()
    for bk, bd in BUILDINGS.items():
        unlocked = bd['unlock_price'] == 0
        c.execute(
            'INSERT INTO farm_buildings (user_id, bld_key, unlocked) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',
            (user_id, bk, unlocked)
        )
    conn.commit()
    conn.close()

def _is_unlocked(user_id, bld_key):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT unlocked FROM farm_buildings WHERE user_id=%s AND bld_key=%s', (user_id, bld_key))
    r = c.fetchone()
    conn.close()
    return r and r[0]

def _unlock_building(user_id, bld_key):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('UPDATE farm_buildings SET unlocked=TRUE WHERE user_id=%s AND bld_key=%s', (user_id, bld_key))
    conn.commit()
    conn.close()

def _get_cooking_slots(user_id, bld_key):
    """Всегда возвращает ровно 5 слотов. Пустые — генерируются, не хранятся."""
    conn = _get_conn()
    c    = conn.cursor()
    c.execute(
        'SELECT id,slot_num,recipe_key,started_at,finished_at,is_done,ing_used,quality '
        'FROM cooking_slots WHERE user_id=%s AND bld_key=%s AND recipe_key IS NOT NULL',
        (user_id, bld_key)
    )
    rows = c.fetchall()
    conn.close()

    # Строим словарь занятых слотов
    filled = {}
    for r in rows:
        filled[r[1]] = {'id': r[0], 'slot_num': r[1], 'recipe_key': r[2],
                        'started_at': r[3], 'finished_at': r[4],
                        'is_done': r[5], 'ing_used': r[6], 'quality': r[7]}

    # Возвращаем ровно 5 слотов
    result = []
    for s in range(1, 6):
        if s in filled:
            result.append(filled[s])
        else:
            result.append({'id': None, 'slot_num': s, 'recipe_key': None,
                           'started_at': None, 'finished_at': None,
                           'is_done': False, 'ing_used': None, 'quality': 0})
    return result

def _start_cooking(user_id, bld_key, slot_num, recipe_key, ing_used_str, quality):
    recipe = RECIPES[recipe_key]
    now    = datetime.now()
    finish = now + timedelta(minutes=recipe['time_min'])
    conn   = _get_conn()
    c      = conn.cursor()
    # INSERT вместо UPDATE — слоты больше не хранятся заранее
    c.execute('''INSERT INTO cooking_slots
                 (user_id, bld_key, slot_num, recipe_key, started_at, finished_at, is_done, ing_used, quality)
                 VALUES (%s,%s,%s,%s,%s,%s,FALSE,%s,%s)
                 ON CONFLICT (user_id, bld_key, slot_num) DO UPDATE SET
                     recipe_key=%s, started_at=%s, finished_at=%s,
                     is_done=FALSE, ing_used=%s, quality=%s''',
              (user_id, bld_key, slot_num, recipe_key,
               now.isoformat(), finish.isoformat(), ing_used_str, quality,
               recipe_key, now.isoformat(), finish.isoformat(), ing_used_str, quality))
    conn.commit()
    conn.close()

def _collect_slot(user_id, bld_key, slot_num):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('''SELECT recipe_key, quality, finished_at FROM cooking_slots
                 WHERE user_id=%s AND bld_key=%s AND slot_num=%s AND is_done=TRUE''',
              (user_id, bld_key, slot_num))
    r = c.fetchone()
    if not r:
        conn.close()
        return None
    recipe_key, quality, finished_at = r

    c.execute('''INSERT INTO goods_inventory (user_id, recipe_key, quality, count) VALUES (%s,%s,%s,1)
                 ON CONFLICT (user_id, recipe_key, quality) DO UPDATE SET count=goods_inventory.count+1''',
              (user_id, recipe_key, quality))
    c.execute('''UPDATE cooking_slots SET recipe_key=NULL, started_at=NULL, finished_at=NULL,
                 is_done=FALSE, ing_used=NULL, quality=0
                 WHERE user_id=%s AND bld_key=%s AND slot_num=%s''',
              (user_id, bld_key, slot_num))
    conn.commit()
    conn.close()
    return recipe_key, quality, finished_at

def _get_goods_inventory(user_id):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT recipe_key, quality, count FROM goods_inventory WHERE user_id=%s AND count>0 ORDER BY recipe_key, quality',
              (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def _get_garden_inventory(user_id):
    """Берём инвентарь культур из garden_handlers."""
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT crop_emoji, quality, count FROM garden_inventory WHERE user_id=%s AND count>0',
              (user_id,))
    rows = c.fetchall()
    conn.close()
    return {(r[0], r[1]): r[2] for r in rows}

def _spend_garden_item(user_id, crop_emoji, quality, amount=1):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('''UPDATE garden_inventory SET count=count-%s
                 WHERE user_id=%s AND crop_emoji=%s AND quality=%s AND count>=%s''',
              (amount, user_id, crop_emoji, quality, amount))
    updated = c.rowcount
    conn.commit()
    conn.close()
    return updated > 0

def _return_ingredients(user_id, ing_used_str):
    """Возвращает ингредиенты игроку."""
    if not ing_used_str: return
    import json
    items = json.loads(ing_used_str)
    conn = _get_conn()
    c    = conn.cursor()
    for key, cnt in items.items():
        emoji, quality = key.split('|')
        quality = int(quality)
        c.execute('''INSERT INTO garden_inventory (user_id, crop_emoji, quality, count) VALUES (%s,%s,%s,%s)
                     ON CONFLICT (user_id, crop_emoji, quality) DO UPDATE SET count=garden_inventory.count+%s''',
                  (user_id, emoji, quality, cnt, cnt))
    conn.commit()
    conn.close()

# ============================================================
# ТЕКСТЫ
# ============================================================

def _count_in_building(slots):
    cooking = sum(1 for s in slots if s['recipe_key'] and not s['is_done'])
    done    = sum(1 for s in slots if s['is_done'])
    return cooking, done

def _buildings_main_text(user_id):
    user  = _get_user(user_id)
    money = user[2] if user else 0

    # Подсчёт предметов на складе
    goods = _get_goods_inventory(user_id)
    total_goods = sum(r[2] for r in goods)

    lines = [
        f"— – - 🏭 ЗДАНИЯ ФЕРМЫ - – —\n",
        f"💵 Денег: {money}",
        f"📦 На складе: {total_goods} предмет(ов)\n",
    ]

    # Кухня (всегда открыта)
    slots_k = _get_cooking_slots(user_id, 'kitchen')
    ck, dk  = _count_in_building(slots_k)
    lines.append(f"{SEP}\n🍳 КУХНЯ 🍳\n\n⏳ В готовке: {ck}/5\n✅ Приготовлено: {dk}\n")

    for bk in ['barrel', 'cauldron', 'winery']:
        bd = BUILDINGS[bk]
        lines.append(SEP)
        if _is_unlocked(user_id, bk):
            slots_b = _get_cooking_slots(user_id, bk)
            cb, db  = _count_in_building(slots_b)
            lines.append(f"{bd['emoji']} {bd['name']}\n\n⏳ В готовке: {cb}/5\n✅ Приготовлено: {db}\n")
        else:
            lines.append(f"🔒 {bd['name']} — ЗАБЛОКИРОВАНО\nЦена открытия: 💵 {bd['unlock_price']:,}\n")

    lines.append(SEP)
    return "\n".join(lines)

def _buildings_main_markup():
    m = InlineKeyboardMarkup(row_width=4)
    m.add(
        InlineKeyboardButton("🍳 Кухня",      callback_data="bld_open_kitchen"),
        InlineKeyboardButton("🪵 Кадка",      callback_data="bld_open_barrel"),
        InlineKeyboardButton("🍯 Котёл",      callback_data="bld_open_cauldron"),
        InlineKeyboardButton("🍷 Винодельня", callback_data="bld_open_winery"),
    )
    m.add(InlineKeyboardButton("🔙 Назад", callback_data="grd_main"))
    return m

def _building_text(user_id, bld_key):
    bd    = BUILDINGS[bld_key]
    slots = _get_cooking_slots(user_id, bld_key)
    ck, dk = _count_in_building(slots)
    now   = datetime.now()

    lines = [f"— — – - {bd['emoji']} {bd['name'].upper()} {bd['emoji']} - – — —\n",
             f"⏳ В готовке: {ck}/5",
             f"✅ Приготовлено: {dk}\n",
             SEP]

    for s in slots:
        n = s['slot_num']
        if not s['recipe_key']:
            lines.append(f"\n{n}️⃣ [Пусто]\n")
        else:
            rec  = RECIPES[s['recipe_key']]
            line = [f"\n{n}️⃣ – {rec['emoji']} {rec['name']} –"]
            if s['is_done']:
                line.append("✅ Приготовлено ❕")
                # Выдержка только для вина/сидра
                if rec.get('aging') and s['finished_at']:
                    mult     = aging_mult(s['finished_at'])
                    age_str  = aging_time_str(s['finished_at'])
                    line.append(f"🕰️ Выдержка: {age_str} | ×{mult}")
            else:
                finish = datetime.fromisoformat(s['finished_at'])
                left   = max(0, (finish - now).total_seconds())
                line.append(f"⏲️ Будет готово через: {format_time(left)}")

            # Ингредиенты
            if s['ing_used']:
                import json
                items = json.loads(s['ing_used'])
                line.append("Ингредиенты:")
                for key, cnt in items.items():
                    emoji, quality = key.split('|')
                    q_str = quality_str(int(quality))
                    if cnt > 1:
                        line.append(f"{emoji} {q_str} ×{cnt}")
                    else:
                        line.append(f"{emoji} {q_str}")

            lines.append("\n".join(line))
        lines.append(SEP)

    return "\n".join(lines)

def _building_markup(user_id, bld_key):
    slots = _get_cooking_slots(user_id, bld_key)
    has_done = any(s['is_done'] for s in slots)
    m = InlineKeyboardMarkup(row_width=3)
    btns = [
        InlineKeyboardButton("🔙 Назад",       callback_data="bld_main"),
        InlineKeyboardButton("➕ Приготовить",  callback_data=f"bld_cook_{bld_key}"),
        InlineKeyboardButton("📦 Инвентарь",   callback_data="grd_inventory"),
    ]
    if has_done:
        btns.insert(2, InlineKeyboardButton("✅ Забрать", callback_data=f"bld_collect_{bld_key}"))
    m.add(*btns)
    return m

def _recipe_list_text(bld_key):
    bd = BUILDINGS[bld_key]
    recipes = {k: v for k, v in RECIPES.items() if v['building'] == bld_key}
    cats = {}
    for rk, rv in recipes.items():
        cat = rv['category']
        cats.setdefault(cat, []).append((rk, rv))

    lines = [f"— — – - {bd['emoji']} {bd['name'].upper()} {bd['emoji']} - – — —\n",
             "Выбери рецепт для приготовления:\n"]
    for cat, items in cats.items():
        lines.append(f"• • • {cat} • • •\n")
        for rk, rv in items:
            ing_str = ", ".join(f"{e} ×{n}" for e, n in rv['ingredients'].items())
            lines.append(f"{rv['emoji']} {rv['name']} — {ing_str}")
            lines.append(f"⏲️ Время: {format_time(rv['time_min']*60)}\n")
    return "\n".join(lines)

def _recipe_list_markup(bld_key):
    recipes = {k: v for k, v in RECIPES.items() if v['building'] == bld_key}
    m = InlineKeyboardMarkup(row_width=3)
    btns = []
    for rk, rv in recipes.items():
        btns.append(InlineKeyboardButton(
            f"{rv['emoji']} {rv['name']}", callback_data=f"bld_recipe_{bld_key}_{rk}"
        ))
    m.add(*btns)
    m.add(
        InlineKeyboardButton("🔙 Назад",     callback_data=f"bld_open_{bld_key}"),
        InlineKeyboardButton("📦 Инвентарь", callback_data="grd_inventory"),
    )
    return m

# ============================================================
# ХРАНИЛИЩЕ СЕССИЙ ВЫБОРА ИНГРЕДИЕНТОВ
# ============================================================
_cooking_sessions = {}
_session_lock     = threading.Lock()

# ============================================================
# РЕГИСТРАЦИЯ ХЭНДЛЕРОВ
# ============================================================

def register_buildings_handlers(bot, get_conn, get_user, add_exp, spend_money):
    global _get_conn, _get_user, _add_exp, _spend_money
    _get_conn    = get_conn
    _get_user    = get_user
    _add_exp     = add_exp
    _spend_money = spend_money

    _init_buildings_db()

    # ── Главное меню зданий ──────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'bld_main')
    def cb_bld_main(call):
        user_id = call.from_user.id
        try:
            bot.edit_message_text(
                _buildings_main_text(user_id),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_buildings_main_markup()
            )
        except: pass
        bot.answer_callback_query(call.id)

    # grd_wip переопределяем для зданий
    @bot.callback_query_handler(func=lambda c: c.data == 'grd_buildings')
    def cb_grd_buildings(call):
        user_id = call.from_user.id
        try:
            bot.edit_message_text(
                _buildings_main_text(user_id),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_buildings_main_markup()
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Открыть конкретное здание ────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('bld_open_'))
    def cb_bld_open(call):
        user_id  = call.from_user.id
        bld_key  = call.data[len('bld_open_'):]
        bd = BUILDINGS.get(bld_key)
        if not bd:
            bot.answer_callback_query(call.id, "❌ Ошибка!")
            return

        if not _is_unlocked(user_id, bld_key):
            # Показываем заблокированное здание
            user  = _get_user(user_id)
            money = user[2] if user else 0
            text  = (
                f"— – - {bd['emoji']} {bd['name'].upper()} {bd['emoji']} - – —\n\n"
                f"💵 Денег: {money}\n\n"
                f"{SEP}\n\n"
                f"🔒 Заблокировано\n"
                f"💰 Для открытия: 💵 {bd['unlock_price']:,}\n"
            )
            m = InlineKeyboardMarkup(row_width=2)
            m.add(
                InlineKeyboardButton("✅ Открыть", callback_data=f"bld_unlock_{bld_key}"),
                InlineKeyboardButton("🔙 Назад",   callback_data="bld_main"),
            )
            try:
                bot.edit_message_text(text, chat_id=call.message.chat.id,
                                      message_id=call.message.message_id, reply_markup=m)
            except: pass
            bot.answer_callback_query(call.id)
            return

        try:
            bot.edit_message_text(
                _building_text(user_id, bld_key),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_building_markup(user_id, bld_key)
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Разблокировать здание ────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('bld_unlock_'))
    def cb_bld_unlock(call):
        user_id = call.from_user.id
        bld_key = call.data[len('bld_unlock_'):]
        bd      = BUILDINGS.get(bld_key)
        if not bd:
            bot.answer_callback_query(call.id, "❌ Ошибка!")
            return
        user  = _get_user(user_id)
        money = user[2] if user else 0
        if money < bd['unlock_price']:
            bot.answer_callback_query(call.id, f"❌ Нужно 💵{bd['unlock_price']:,}!")
            return
        _spend_money(user_id, bd['unlock_price'])
        _unlock_building(user_id, bld_key)
        bot.answer_callback_query(call.id, f"✅ {bd['name']} открыта!")
        try:
            bot.edit_message_text(
                _building_text(user_id, bld_key),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_building_markup(user_id, bld_key)
            )
        except: pass

    # ── Список рецептов ──────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('bld_cook_'))
    def cb_bld_cook(call):
        user_id = call.from_user.id
        bld_key = call.data[len('bld_cook_'):]
        slots   = _get_cooking_slots(user_id, bld_key)
        free    = [s for s in slots if not s['recipe_key']]

        if not free:
            bot.answer_callback_query(
                call.id,
                "⚠️ Все слоты заняты\n\nДождитесь окончания готовки\nили заберите готовые блюда.",
                show_alert=True
            )
            return

        try:
            bot.edit_message_text(
                _recipe_list_text(bld_key),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_recipe_list_markup(bld_key)
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Выбор рецепта ────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('bld_recipe_'))
    def cb_bld_recipe(call):
        user_id  = call.from_user.id
        parts    = call.data[len('bld_recipe_'):].split('_', 1)
        bld_key  = parts[0]
        recipe_key = parts[1]
        recipe   = RECIPES.get(recipe_key)
        if not recipe:
            bot.answer_callback_query(call.id, "❌ Ошибка!")
            return

        inv = _get_garden_inventory(user_id)

        # Проверяем наличие всех ингредиентов
        for ing_emoji, need_count in recipe['ingredients'].items():
            if ing_emoji == 'any_fruit':
                total_fruits = sum(cnt for (e, q), cnt in inv.items() if e in FRUITS)
                if total_fruits < need_count:
                    bot.answer_callback_query(
                        call.id, f"❌ Нет ягод/фруктов ×{need_count}‼️", show_alert=True)
                    return
            else:
                total = sum(cnt for (e, q), cnt in inv.items() if e == ing_emoji)
                if total < need_count:
                    bot.answer_callback_query(
                        call.id, f"❌ Нет {ing_emoji} ×{need_count}‼️", show_alert=True)
                    return

        # Инициализируем сессию
        with _session_lock:
            _cooking_sessions[user_id] = {
                'bld_key':    bld_key,
                'recipe_key': recipe_key,
                'collected':  {},  # {emoji|quality: count}
                'needed':     dict(recipe['ingredients']),
            }

        _show_ingredient_selection(bot, call, user_id, recipe_key, bld_key)

    def _show_ingredient_selection(bot, call, user_id, recipe_key, bld_key):
        with _session_lock:
            session = _cooking_sessions.get(user_id)
        if not session:
            return

        recipe    = RECIPES[recipe_key]
        collected = session['collected']
        needed    = session['needed']

        # Статус ингредиентов
        ing_status = []
        for ing_emoji, need_count in recipe['ingredients'].items():
            got = sum(v for k, v in collected.items() if k.split('|')[0] == ing_emoji)
            if ing_emoji == 'any_fruit':
                got_any = sum(v for k, v in collected.items() if k.split('|')[0] in FRUITS)
                if got_any >= need_count:
                    ing_status.append(f"🍓/🍎 ✅")
                else:
                    ing_status.append(f"🍓/🍎 ×{need_count - got_any}")
            else:
                if got >= need_count:
                    ing_status.append(f"{ing_emoji} ✅")
                else:
                    ing_status.append(f"{ing_emoji} ×{need_count - got}")

        # Все ли собраны?
        all_done = True
        for ing_emoji, need_count in recipe['ingredients'].items():
            if ing_emoji == 'any_fruit':
                got = sum(v for k, v in collected.items() if k.split('|')[0] in FRUITS)
            else:
                got = sum(v for k, v in collected.items() if k.split('|')[0] == ing_emoji)
            if got < need_count:
                all_done = False
                break

        text = (
            f"— {recipe['emoji']} {recipe['name']} —\n\n"
            f"{', '.join(ing_status)}\n\n"
            f"⏲️ Время: {format_time(recipe['time_min'] * 60)}\n\n"
        )

        if all_done:
            text += "Ингредиенты выбраны. Приготовить?"
            m = InlineKeyboardMarkup(row_width=2)
            m.add(
                InlineKeyboardButton("✅ Готовить", callback_data=f"bld_startcook_{bld_key}_{recipe_key}"),
                InlineKeyboardButton("❌ Отмена",   callback_data=f"bld_cancelcook_{bld_key}"),
            )
        else:
            text += "Выбери ингредиенты для готовки:"
            inv = _get_garden_inventory(user_id)
            m   = InlineKeyboardMarkup(row_width=1)
            btns = []
            for (emoji, quality), count in sorted(inv.items(), key=lambda x: (-x[0][1], x[0][0])):
                # Показываем только нужные ингредиенты для этого рецепта
                needed_emojis = set(recipe['ingredients'].keys())
                is_needed = (
                    emoji in needed_emojis or
                    ('any_fruit' in needed_emojis and emoji in FRUITS)
                )
                if not is_needed:
                    continue
                btns.append(InlineKeyboardButton(
                    f"{emoji} {quality_str(quality)} ×{count}",
                    callback_data=f"bld_ing_{bld_key}_{recipe_key}_{emoji}_{quality}"
                ))
            m.add(*btns)
            m.add(InlineKeyboardButton("❌ Отмена", callback_data=f"bld_cancelcook_{bld_key}"))

        try:
            bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=m
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Выбор ингредиента ────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('bld_ing_'))
    def cb_bld_ing(call):
        user_id = call.from_user.id
        parts   = call.data[len('bld_ing_'):].split('_')
        bld_key    = parts[0]
        recipe_key = parts[1]
        emoji      = parts[2]
        quality    = int(parts[3])

        with _session_lock:
            session = _cooking_sessions.get(user_id)
        if not session or session['recipe_key'] != recipe_key:
            bot.answer_callback_query(call.id, "❌ Сессия истекла!")
            return

        recipe  = RECIPES[recipe_key]
        ing_key = f"{emoji}|{quality}"

        # Проверяем что этот ингредиент ещё нужен
        if emoji in recipe['ingredients']:
            need = recipe['ingredients'][emoji]
            got  = sum(v for k, v in session['collected'].items() if k.split('|')[0] == emoji)
            if got >= need:
                bot.answer_callback_query(call.id, f"✅ {emoji} уже набрано!")
                return
        elif 'any_fruit' in recipe['ingredients']:
            need = recipe['ingredients']['any_fruit']
            got  = sum(v for k, v in session['collected'].items() if k.split('|')[0] in FRUITS)
            if got >= need:
                bot.answer_callback_query(call.id, "✅ Фруктов уже достаточно!")
                return
        else:
            bot.answer_callback_query(call.id, "❌ Этот ингредиент не нужен!")
            return

        # Списываем 1 штуку с инвентаря
        if not _spend_garden_item(user_id, emoji, quality, 1):
            bot.answer_callback_query(call.id, "❌ Недостаточно!")
            return

        with _session_lock:
            s = _cooking_sessions.get(user_id)
            if s:
                s['collected'][ing_key] = s['collected'].get(ing_key, 0) + 1

        _show_ingredient_selection(bot, call, user_id, recipe_key, bld_key)

    # ── Отмена готовки (возврат ингредиентов) ────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('bld_cancelcook_'))
    def cb_bld_cancelcook(call):
        user_id = call.from_user.id
        bld_key = call.data[len('bld_cancelcook_'):]

        with _session_lock:
            session = _cooking_sessions.pop(user_id, None)

        if session and session['collected']:
            import json
            _return_ingredients(user_id, json.dumps(session['collected']))

        try:
            bot.edit_message_text(
                _building_text(user_id, bld_key),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_building_markup(user_id, bld_key)
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Начать готовку ───────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('bld_startcook_'))
    def cb_bld_startcook(call):
        import json
        user_id = call.from_user.id
        parts   = call.data[len('bld_startcook_'):].split('_', 1)
        bld_key    = parts[0]
        recipe_key = parts[1]

        with _session_lock:
            session = _cooking_sessions.pop(user_id, None)
        if not session:
            bot.answer_callback_query(call.id, "❌ Сессия истекла!")
            return

        # Найти свободный слот
        slots = _get_cooking_slots(user_id, bld_key)
        free  = [s for s in slots if not s['recipe_key']]
        if not free:
            bot.answer_callback_query(call.id, "⚠️ Все слоты заняты!", show_alert=True)
            return

        slot_num   = free[0]['slot_num']
        collected  = session['collected']

        # Вычислить качество
        qualities = []
        for key, cnt in collected.items():
            q = int(key.split('|')[1])
            qualities.extend([q] * cnt)
        avg_quality = max(1, int(sum(qualities) / len(qualities))) if qualities else 1

        ing_str = json.dumps(collected)
        _start_cooking(user_id, bld_key, slot_num, recipe_key, ing_str, avg_quality)

        bot.answer_callback_query(call.id, "✅ Готовка началась!")
        try:
            bot.edit_message_text(
                _building_text(user_id, bld_key),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_building_markup(user_id, bld_key)
            )
        except: pass

    # ── Забрать готовые ──────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('bld_collect_'))
    def cb_bld_collect(call):
        user_id = call.from_user.id
        bld_key = call.data[len('bld_collect_'):]
        slots   = _get_cooking_slots(user_id, bld_key)
        results = []

        for s in slots:
            if s['is_done']:
                result = _collect_slot(user_id, bld_key, s['slot_num'])
                if result:
                    rk, quality, finished_at = result
                    rec = RECIPES[rk]

                    # Цена с учётом выдержки
                    price_mult = 1.0
                    if rec.get('aging') and finished_at:
                        price_mult = aging_mult(finished_at)

                    # XP с учётом качества
                    base_exp = rec['exp']
                    xp_mult  = XP_QUALITY_BONUS.get(quality, 1.0)
                    exp_gain = int(base_exp * xp_mult)

                    _add_exp(user_id, exp_gain)
                    results.append(
                        f"+{rec['emoji']} {rec['name']} ×1 | {quality_str(quality)}"
                        + (f" | 🕰️×{price_mult}" if price_mult > 1.0 else "")
                        + f" | +{exp_gain}⭐"
                    )

        if results:
            bot.send_message(call.message.chat.id, "\n".join(results))
        else:
            bot.answer_callback_query(call.id, "❌ Ничего нет!")
            return

        try:
            bot.edit_message_text(
                _building_text(user_id, bld_key),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_building_markup(user_id, bld_key)
            )
        except: pass
        bot.answer_callback_query(call.id)


# ============================================================
# ФОНОВЫЙ ЧЕКЕР (готовка завершена)
# ============================================================

def buildings_checker_loop(bot, get_conn_fn, get_user_fn):
    while True:
        try:
            conn = get_conn_fn()
            c    = conn.cursor()
            now  = datetime.now().isoformat()
            c.execute('''UPDATE cooking_slots SET is_done=TRUE
                         WHERE is_done=FALSE AND recipe_key IS NOT NULL AND finished_at <= %s''',
                      (now,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Buildings checker error: {e}")
        _time.sleep(30)
