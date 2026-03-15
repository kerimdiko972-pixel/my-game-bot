"""
garden.py — данные и константы новой игры огорода (с погодой).
"""
from datetime import datetime, timedelta
import random

BED_TYPES = {
    1: {'name': 'Земля',    'emoji': '🌱', 'slots': 25, 'regrow': False},
    2: {'name': 'Кустовые', 'emoji': '🌿', 'slots': 20, 'regrow': True},
    3: {'name': 'Деревья',  'emoji': '🌳', 'slots': 12, 'regrow': True},
}

CROPS = {
    '🥔': {'bed': 1, 'name': 'Картошка',          'grow_min': 30,  'price': 70,   'seed_price': 15},
    '🥕': {'bed': 1, 'name': 'Морковь',            'grow_min': 20,  'price': 40,   'seed_price': 10},
    '🌽': {'bed': 1, 'name': 'Кукуруза',           'grow_min': 60,  'price': 200,  'seed_price': 50},
    '🫜': {'bed': 1, 'name': 'Свёкла',             'grow_min': 45,  'price': 90,   'seed_price': 20},
    '🥬': {'bed': 1, 'name': 'Капуста',            'grow_min': 25,  'price': 60,   'seed_price': 12},
    '🍉': {'bed': 1, 'name': 'Арбуз',              'grow_min': 120, 'price': 600,  'seed_price': 150},
    '🍈': {'bed': 1, 'name': 'Дыня',               'grow_min': 110, 'price': 550,  'seed_price': 140},
    '🍍': {'bed': 1, 'name': 'Ананас',             'grow_min': 180, 'price': 1200, 'seed_price': 300},
    '🌾': {'bed': 1, 'name': 'Пшеница',            'grow_min': 15,  'price': 90,   'seed_price': 40},
    '🍅': {'bed': 2, 'name': 'Помидор',            'grow_min': 45,  'price': 120,  'seed_price': 30},
    '🥒': {'bed': 2, 'name': 'Огурец',             'grow_min': 35,  'price': 80,   'seed_price': 20},
    '🫑': {'bed': 2, 'name': 'Болгарский перец',   'grow_min': 50,  'price': 160,  'seed_price': 40},
    '🍆': {'bed': 2, 'name': 'Баклажан',           'grow_min': 50,  'price': 150,  'seed_price': 35},
    '🌶️': {'bed': 2, 'name': 'Перчик',             'grow_min': 45,  'price': 140,  'seed_price': 35},
    '🍓': {'bed': 2, 'name': 'Клубника',           'grow_min': 90,  'price': 350,  'seed_price': 80},
    '🍇': {'bed': 2, 'name': 'Виноград',           'grow_min': 120, 'price': 500,  'seed_price': 120},
    '🍎': {'bed': 3, 'name': 'Яблоко',             'grow_min': 360, 'price': 300,  'seed_price': 70},
    '🍊': {'bed': 3, 'name': 'Апельсин',           'grow_min': 360, 'price': 320,  'seed_price': 80},
    '🥭': {'bed': 3, 'name': 'Манго',              'grow_min': 480, 'price': 800,  'seed_price': 200},
    '🍒': {'bed': 3, 'name': 'Вишня',              'grow_min': 180, 'price': 600,  'seed_price': 150},
}

def crops_by_bed(bed_num):
    return {e: d for e, d in CROPS.items() if d['bed'] == bed_num}

def roll_quality(quality_bonus_pct=0):
    r  = random.random() * 100
    w1 = max(0, 60 - quality_bonus_pct * 0.60)
    w2 = 25
    w3 = 10
    w4 = 4  + quality_bonus_pct * 0.04
    w5 = 1  + quality_bonus_pct * 0.56
    if r < w1:             return 1
    elif r < w1+w2:        return 2
    elif r < w1+w2+w3:     return 3
    elif r < w1+w2+w3+w4:  return 4
    else:                  return 5

def quality_str(q):
    return {1:'⭐',2:'⭐⭐',3:'⭐⭐⭐',4:'⭐⭐⭐⭐',5:'⭐⭐⭐⭐⭐'}.get(q,'⭐')

def quality_mult(q):
    return {1:1.0,2:1.5,3:2.0,4:3.0,5:5.0}.get(q,1.0)

FERTILIZERS = {
    'rostostim_1': {'name': 'Ростостим I',    'emoji': '⚡', 'tier': 1, 'price': 1200, 'growth': 15, 'quality': 0,  'yield': 0},
    'rostostim_2': {'name': 'Ростостим II',   'emoji': '⚡', 'tier': 2, 'price': 3000, 'growth': 30, 'quality': 0,  'yield': 0},
    'rostostim_3': {'name': 'Ростостим III',  'emoji': '⚡', 'tier': 3, 'price': 10000,'growth': 50, 'quality': 0,  'yield': 0},
    'kachestivt_1':{'name': 'Качествит I',    'emoji': '⭐', 'tier': 1, 'price': 1500, 'growth': 0,  'quality': 10, 'yield': 0},
    'kachestivt_2':{'name': 'Качествит II',   'emoji': '⭐', 'tier': 2, 'price': 3500, 'growth': 0,  'quality': 20, 'yield': 0},
    'kachestivt_3':{'name': 'Качествит III',  'emoji': '⭐', 'tier': 3, 'price': 12000,'growth': 0,  'quality': 35, 'yield': 0},
    'urozhay_1':   {'name': 'УрожайПлюс I',   'emoji': '🌾', 'tier': 1, 'price': 2000, 'growth': 0,  'quality': 0,  'yield': 1},
    'urozhay_2':   {'name': 'УрожайПлюс II',  'emoji': '🌾', 'tier': 2, 'price': 5000, 'growth': 0,  'quality': 0,  'yield': 2},
    'urozhay_3':   {'name': 'УрожайПлюс III', 'emoji': '🌾', 'tier': 3, 'price': 12500,'growth': 0,  'quality': 0,  'yield': 3},
}

WATER_BONUS_GROWTH = 10
WATER_DURATION_MIN = 15

# ============================================================
# ПОГОДА
# ============================================================
WEATHER_TYPES = {
    'cloudy':        {'emoji': '☁️',  'name': 'Пасмурно',
                      'growth': -10, 'quality': 0,  'always_watered': False, 'water_drain_mult': 1.0,
                      'effect_text': '🌱 Скорость роста: -10%'},
    'partly_cloudy': {'emoji': '⛅',  'name': 'Переменная облачность',
                      'growth': 5,   'quality': 5,  'always_watered': False, 'water_drain_mult': 1.0,
                      'effect_text': '🌱 Скорость роста: +5%, ⭐ Качество: +5%'},
    'sunny':         {'emoji': '☀️',  'name': 'Яркое солнце',
                      'growth': 15,  'quality': 5,  'always_watered': False, 'water_drain_mult': 1.25,
                      'effect_text': '🌱 Скорость роста: +15%, ⭐ Качество: +5%, 💧 Вода высыхает быстрее'},
    'rain':          {'emoji': '🌧️',  'name': 'Идёт дождь',
                      'growth': 10,  'quality': 5,  'always_watered': True,  'water_drain_mult': 1.0,
                      'effect_text': '🌱 Скорость роста: +10%, ⭐ Качество: +5%, 💧 Все растения политы'},
    'sunny_rain':    {'emoji': '🌦️',  'name': 'Солнечный дождь',
                      'growth': 20,  'quality': 10, 'always_watered': True,  'water_drain_mult': 1.0,
                      'effect_text': '🌱 Рост: +20%, ⭐ Качество: +10%, 💧 Все растения политы'},
}

WEATHER_WEIGHTS      = {'cloudy': 20, 'partly_cloudy': 50, 'sunny': 20, 'rain': 7, 'sunny_rain': 3}
WEATHER_CHANGE_HOURS = 2.5

_current_weather_key = 'cloudy'

def get_weather():     return _current_weather_key
def set_weather(key):
    global _current_weather_key
    _current_weather_key = key

def roll_weather():
    keys = list(WEATHER_WEIGHTS.keys())
    return random.choices(keys, weights=[WEATHER_WEIGHTS[k] for k in keys], k=1)[0]

def weather_info():
    w = WEATHER_TYPES.get(_current_weather_key, WEATHER_TYPES['cloudy'])
    return w['emoji'], w['name'], w['effect_text']

def weather_growth_bonus():    return WEATHER_TYPES.get(_current_weather_key, {}).get('growth', 0)
def weather_quality_bonus():   return WEATHER_TYPES.get(_current_weather_key, {}).get('quality', 0)
def weather_always_watered():  return WEATHER_TYPES.get(_current_weather_key, {}).get('always_watered', False)
def weather_water_drain():     return WEATHER_TYPES.get(_current_weather_key, {}).get('water_drain_mult', 1.0)

SEP  = "• – – – – – – – – – – – – •"
SEP2 = "— – - - - - - - - - - - - - - - - - - – —"

def _effective_water_duration():
    return WATER_DURATION_MIN / weather_water_drain()

def _is_watered(slot_row, now):
    if weather_always_watered():
        return True
    watered_at = slot_row.get('watered_at')
    if not watered_at:
        return False
    return (now - datetime.fromisoformat(watered_at)).total_seconds() < _effective_water_duration() * 60

def _calc_eff_min(slot_row, now):
    grow_min    = CROPS.get(slot_row['crop_emoji'], {}).get('grow_min', 30)
    total_bonus = slot_row.get('fert_growth', 0) + weather_growth_bonus()
    eff_min     = max(1, grow_min * (1 - total_bonus / 100))
    if _is_watered(slot_row, now):
        eff_min = max(1, eff_min * (1 - WATER_BONUS_GROWTH / 100))
    return eff_min

def get_slot_emoji(slot_row, now=None):
    if now is None: now = datetime.now()
    if not slot_row or not slot_row['crop_emoji']: return '🟫'
    crop_e  = slot_row['crop_emoji']
    bed_num = CROPS.get(crop_e, {}).get('bed', 1)
    planted = datetime.fromisoformat(slot_row['planted_at'])
    eff_min = _calc_eff_min(slot_row, now)
    if (now - planted).total_seconds() >= eff_min * 60:
        return crop_e
    grow_emoji = {1: '🌱', 2: '🌿', 3: '🌳'}.get(bed_num, '🌱')
    return grow_emoji if _is_watered(slot_row, now) else grow_emoji + '💧'

def is_ready(slot_row, now=None):
    if now is None: now = datetime.now()
    if not slot_row or not slot_row['crop_emoji']: return False
    planted = datetime.fromisoformat(slot_row['planted_at'])
    return (now - planted).total_seconds() >= _calc_eff_min(slot_row, now) * 60

def growth_progress(slot_row, now=None):
    if now is None: now = datetime.now()
    planted = datetime.fromisoformat(slot_row['planted_at'])
    eff_min = _calc_eff_min(slot_row, now)
    elapsed = (now - planted).total_seconds()
    total   = eff_min * 60
    return min(100, int(elapsed / total * 100)), max(0, total - elapsed)

def format_time(seconds):
    m = int(seconds // 60); s = int(seconds % 60)
    if m >= 60:
        h = m // 60; m = m % 60
        return f"{h} ч. {m} мин."
    return f"{m} мин. {s} сек."

def water_status(slot_row, now=None):
    if now is None: now = datetime.now()
    if weather_always_watered():
        return '✅ (дождь)', True
    watered_at = slot_row.get('watered_at')
    if not watered_at: return '❌', False
    elapsed = (now - datetime.fromisoformat(watered_at)).total_seconds()
    eff_dur = _effective_water_duration() * 60
    if elapsed >= eff_dur: return '❌', False
    return f'✅ ({int((eff_dur - elapsed)//60)} мин.)', True

def growth_bonuses(slot_row):
    now = datetime.now()
    wb  = WATER_BONUS_GROWTH if _is_watered(slot_row, now) else 0
    return wb + slot_row.get('fert_growth', 0) + weather_growth_bonus(), \
           slot_row.get('fert_quality', 0) + weather_quality_bonus()
