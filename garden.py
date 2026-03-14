"""
garden.py — данные и константы новой игры огорода.
"""
from datetime import datetime, timedelta
import random

# ============================================================
# ТИПЫ ГРЯДОК
# ============================================================
BED_TYPES = {
    1: {'name': 'Земля',    'emoji': '🌱', 'slots': 25, 'regrow': False},
    2: {'name': 'Кустовые', 'emoji': '🌿', 'slots': 20, 'regrow': True},
    3: {'name': 'Деревья',  'emoji': '🌳', 'slots': 12, 'regrow': True},
}

# ============================================================
# КУЛЬТУРЫ
# (bed_type, emoji, name, grow_minutes, base_price, seed_price)
# ============================================================
CROPS = {
    # Земля
    '🥔': {'bed': 1, 'name': 'Картошка',           'grow_min': 30,  'price': 70,   'seed_price': 15},
    '🌾': {'bed': 1, 'name': 'Пшеница',            'grow_min': 15,  'price': 90,   'seed_price': 40},
    '🥕': {'bed': 1, 'name': 'Морковь',            'grow_min': 20,  'price': 40,   'seed_price': 10},
    '🌽': {'bed': 1, 'name': 'Кукуруза',           'grow_min': 60,  'price': 200,  'seed_price': 50},
    '🫜': {'bed': 1, 'name': 'Свёкла',             'grow_min': 45,  'price': 90,   'seed_price': 20},
    '🥬': {'bed': 1, 'name': 'Капуста',            'grow_min': 25,  'price': 60,   'seed_price': 12},
    '🍉': {'bed': 1, 'name': 'Арбуз',              'grow_min': 120, 'price': 600,  'seed_price': 150},
    '🍈': {'bed': 1, 'name': 'Дыня',               'grow_min': 110, 'price': 550,  'seed_price': 140},
    '🍍': {'bed': 1, 'name': 'Ананас',             'grow_min': 180, 'price': 1200, 'seed_price': 300},
    # Кустовые
    '🍅': {'bed': 2, 'name': 'Помидор',            'grow_min': 45,  'price': 120,  'seed_price': 30},
    '🥒': {'bed': 2, 'name': 'Огурец',             'grow_min': 35,  'price': 80,   'seed_price': 20},
    '🫑': {'bed': 2, 'name': 'Болгарский перец',   'grow_min': 50,  'price': 160,  'seed_price': 40},
    '🍆': {'bed': 2, 'name': 'Баклажан',           'grow_min': 50,  'price': 150,  'seed_price': 35},
    '🌶️': {'bed': 2, 'name': 'Перчик',             'grow_min': 45,  'price': 140,  'seed_price': 35},
    '🍓': {'bed': 2, 'name': 'Клубника',           'grow_min': 90,  'price': 350,  'seed_price': 80},
    '🍇': {'bed': 2, 'name': 'Виноград',           'grow_min': 120, 'price': 500,  'seed_price': 120},
    # Деревья
    '🍎': {'bed': 3, 'name': 'Яблоко',             'grow_min': 360, 'price': 300,  'seed_price': 70},
    '🍊': {'bed': 3, 'name': 'Апельсин',           'grow_min': 360, 'price': 320,  'seed_price': 80},
    '🥭': {'bed': 3, 'name': 'Манго',              'grow_min': 480, 'price': 800,  'seed_price': 200},
    '🍒': {'bed': 3, 'name': 'Вишня',              'grow_min': 180, 'price': 600,  'seed_price': 150},
}

def crops_by_bed(bed_num):
    return {e: d for e, d in CROPS.items() if d['bed'] == bed_num}

# ============================================================
# КАЧЕСТВО
# ============================================================
QUALITY_LEVELS = [
    (1, '⭐',       1.0,  60),
    (2, '⭐⭐',     1.5,  25),
    (3, '⭐⭐⭐',   2.0,  10),
    (4, '⭐⭐⭐⭐',     3.0,  4),
    (5, '⭐⭐⭐⭐⭐',   5.0,  1),
]

def roll_quality(quality_bonus_pct=0):
    r = random.random() * 100
    w1 = max(0, 60 - quality_bonus_pct * 0.60)
    w2 = 25
    w3 = 10
    w4 = 4  + quality_bonus_pct * 0.04
    w5 = 1  + quality_bonus_pct * 0.56
    if r < w1:
        return 1
    elif r < w1 + w2:
        return 2
    elif r < w1 + w2 + w3:
        return 3
    elif r < w1 + w2 + w3 + w4:
        return 4
    else:
        return 5

def quality_str(q):
    return {1: '⭐', 2: '⭐⭐', 3: '⭐⭐⭐', 4: '⭐⭐⭐⭐', 5: '⭐⭐⭐⭐⭐'}.get(q, '⭐')

def quality_mult(q):
    return {1: 1.0, 2: 1.5, 3: 2.0, 4: 3.0, 5: 5.0}.get(q, 1.0)

# ============================================================
# УДОБРЕНИЯ
# ============================================================
FERTILIZERS = {
    'rostostim_1': {'name': 'Ростостим I',    'emoji': '⚡', 'tier': 1, 'price': 1200,
                    'growth': 15, 'quality': 0,  'yield': 0},
    'rostostim_2': {'name': 'Ростостим II',   'emoji': '⚡', 'tier': 2, 'price': 3000,
                    'growth': 30, 'quality': 0,  'yield': 0},
    'rostostim_3': {'name': 'Ростостим III',  'emoji': '⚡', 'tier': 3, 'price': 10000,
                    'growth': 50, 'quality': 0,  'yield': 0},
    'kachestivt_1':{'name': 'Качествит I',    'emoji': '⭐', 'tier': 1, 'price': 1500,
                    'growth': 0,  'quality': 10, 'yield': 0},
    'kachestivt_2':{'name': 'Качествит II',   'emoji': '⭐', 'tier': 2, 'price': 3500,
                    'growth': 0,  'quality': 20, 'yield': 0},
    'kachestivt_3':{'name': 'Качествит III',  'emoji': '⭐', 'tier': 3, 'price': 12000,
                    'growth': 0,  'quality': 35, 'yield': 0},
    'urozhay_1':   {'name': 'УрожайПлюс I',   'emoji': '🌾', 'tier': 1, 'price': 2000,
                    'growth': 0,  'quality': 0,  'yield': 1},
    'urozhay_2':   {'name': 'УрожайПлюс II',  'emoji': '🌾', 'tier': 2, 'price': 5000,
                    'growth': 0,  'quality': 0,  'yield': 2},
    'urozhay_3':   {'name': 'УрожайПлюс III', 'emoji': '🌾', 'tier': 3, 'price': 12500,
                    'growth': 0,  'quality': 0,  'yield': 3},
}

# ============================================================
# ПОЛИВ
# ============================================================
WATER_BONUS_GROWTH = 10   # % бонус роста от полива
WATER_DURATION_MIN = 15   # минут действует полив

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
SEP  = "• – – – – – – – – – – – – •"
SEP2 = "— – - - - - - - - - - - - - - - - - - – —"

def get_slot_emoji(slot_row, now=None):
    """Возвращает эмодзи кнопки слота."""
    if now is None:
        now = datetime.now()
    if not slot_row or not slot_row['crop_emoji']:
        return '🟫'
    crop_e   = slot_row['crop_emoji']
    crop     = CROPS.get(crop_e, {})
    bed_num  = crop.get('bed', 1)
    planted  = datetime.fromisoformat(slot_row['planted_at'])
    grow_min = crop.get('grow_min', 30)
    growth_bonus = slot_row.get('fert_growth', 0)
    eff_min  = grow_min * (1 - growth_bonus / 100)

    # Полив
    watered_at = slot_row.get('watered_at')
    if watered_at:
        watered_dt = datetime.fromisoformat(watered_at)
        if (now - watered_dt).total_seconds() < WATER_DURATION_MIN * 60:
            eff_min = eff_min * (1 - WATER_BONUS_GROWTH / 100)

    if (now - planted).total_seconds() >= eff_min * 60:
        return crop_e  # созрело — показываем эмодзи культуры
    else:
        grow_emoji = {1: '🌱', 2: '🌿', 3: '🌳'}.get(bed_num, '🌱')
        # Нужен полив?
        if watered_at:
            watered_dt = datetime.fromisoformat(watered_at)
            if (now - watered_dt).total_seconds() < WATER_DURATION_MIN * 60:
                return grow_emoji  # есть влажность
        return grow_emoji + '💧'  # нет влажности

def is_ready(slot_row, now=None):
    if now is None:
        now = datetime.now()
    if not slot_row or not slot_row['crop_emoji']:
        return False
    crop_e   = slot_row['crop_emoji']
    crop     = CROPS.get(crop_e, {})
    planted  = datetime.fromisoformat(slot_row['planted_at'])
    grow_min = crop.get('grow_min', 30)
    growth_bonus = slot_row.get('fert_growth', 0)
    eff_min  = grow_min * (1 - growth_bonus / 100)

    watered_at = slot_row.get('watered_at')
    if watered_at:
        watered_dt = datetime.fromisoformat(watered_at)
        if (now - watered_dt).total_seconds() < WATER_DURATION_MIN * 60:
            eff_min = eff_min * (1 - WATER_BONUS_GROWTH / 100)

    return (now - planted).total_seconds() >= eff_min * 60

def growth_progress(slot_row, now=None):
    """Возвращает (pct, seconds_left)"""
    if now is None:
        now = datetime.now()
    crop_e   = slot_row['crop_emoji']
    crop     = CROPS.get(crop_e, {})
    planted  = datetime.fromisoformat(slot_row['planted_at'])
    grow_min = crop.get('grow_min', 30)
    growth_bonus = slot_row.get('fert_growth', 0)
    eff_min  = grow_min * (1 - growth_bonus / 100)

    watered_at = slot_row.get('watered_at')
    if watered_at:
        watered_dt = datetime.fromisoformat(watered_at)
        if (now - watered_dt).total_seconds() < WATER_DURATION_MIN * 60:
            eff_min = eff_min * (1 - WATER_BONUS_GROWTH / 100)

    elapsed  = (now - planted).total_seconds()
    total    = eff_min * 60
    pct      = min(100, int(elapsed / total * 100))
    left     = max(0, total - elapsed)
    return pct, left

def format_time(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    if m >= 60:
        h = m // 60
        m = m % 60
        return f"{h} ч. {m} мин."
    return f"{m} мин. {s} сек."

def water_status(slot_row, now=None):
    if now is None:
        now = datetime.now()
    watered_at = slot_row.get('watered_at')
    if not watered_at:
        return '❌', False
    watered_dt = datetime.fromisoformat(watered_at)
    elapsed    = (now - watered_dt).total_seconds()
    if elapsed >= WATER_DURATION_MIN * 60:
        return '❌', False
    left = WATER_DURATION_MIN * 60 - elapsed
    return f'✅ ({int(left//60)} мин.)', True

def growth_bonuses(slot_row):
    bonuses = []
    wb = WATER_BONUS_GROWTH if slot_row.get('watered_at') else 0
    # Проверяем актуальность полива
    if slot_row.get('watered_at'):
        watered_dt = datetime.fromisoformat(slot_row['watered_at'])
        if (datetime.now() - watered_dt).total_seconds() >= WATER_DURATION_MIN * 60:
            wb = 0
    fg = slot_row.get('fert_growth', 0)
    total = wb + fg
    return total, slot_row.get('fert_quality', 0)
