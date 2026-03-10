import psycopg2
import psycopg2.extras
import os
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

# ═══════════════════════════════════════════════════════════════
# МОДИФИКАТОРЫ ХАРАКТЕРИСТИК
# ═══════════════════════════════════════════════════════════════

STAT_MOD = {
    1:-5, 2:-4, 3:-4, 4:-3, 5:-3, 6:-2, 7:-2, 8:-1, 9:-1, 10:0,
    11:0, 12:1, 13:1, 14:2, 15:2, 16:3, 17:3, 18:4, 19:4, 20:5,
}

def get_mod(val):
    return STAT_MOD.get(max(1, min(20, int(val))), 0)

# ═══════════════════════════════════════════════════════════════
# КОНСТАНТЫ КЛАССОВ
# ═══════════════════════════════════════════════════════════════

CLASSES = {
    "warrior": {
        "name":"Воин","emoji":"⚔️","base_hp":130,"base_mp":6,"k1":3,"k2":1,
        "stats":{"strength":8,"agility":5,"intellect":3,"constitution":8,"speed":6,"charisma":5},
        "lead":["strength","constitution"],"start_weapon":"starter_warrior",
    },
    "barbarian": {
        "name":"Варвар","emoji":"🪓","base_hp":140,"base_mp":5,"k1":3,"k2":1,
        "stats":{"strength":9,"agility":4,"intellect":2,"constitution":9,"speed":6,"charisma":3},
        "lead":["strength","constitution"],"start_weapon":"starter_barbarian",
    },
    "assassin": {
        "name":"Ассасин","emoji":"🗡️","base_hp":90,"base_mp":8,"k1":2,"k2":2,
        "stats":{"strength":6,"agility":9,"intellect":4,"constitution":4,"speed":7,"charisma":6},
        "lead":["agility","charisma"],"start_weapon":"starter_assassin",
    },
    "ranger": {
        "name":"Следопыт","emoji":"🏹","base_hp":100,"base_mp":8,"k1":2,"k2":2,
        "stats":{"strength":6,"agility":8,"intellect":4,"constitution":5,"speed":7,"charisma":4},
        "lead":["agility","intellect"],"start_weapon":"starter_ranger",
    },
    "mage": {
        "name":"Волшебник","emoji":"🪄","base_hp":100,"base_mp":20,"k1":1,"k2":3,
        "stats":{"strength":2,"agility":4,"intellect":9,"constitution":5,"speed":10,"charisma":6},
        "lead":["intellect","charisma"],"start_weapon":"starter_mage",
    },
    "warlock": {
        "name":"Колдун","emoji":"🔮","base_hp":120,"base_mp":20,"k1":1,"k2":3,
        "stats":{"strength":3,"agility":4,"intellect":8,"constitution":7,"speed":8,"charisma":8},
        "lead":["intellect","charisma"],"start_weapon":"starter_warlock",
    },
}

SPELL_CLASSES = {"mage","warlock"}

STAT_NAMES = {
    "strength":"💪 Сила","agility":"🎯 Ловкость","intellect":"🧠 Интеллект",
    "constitution":"🫀 Телосложение","speed":"🏃 Скорость","charisma":"👄 Харизма",
}

SEP = "– – – – – – – – – – – – – – – –"

# ═══════════════════════════════════════════════════════════════
# ОРУЖИЯ
# ═══════════════════════════════════════════════════════════════

WEAPONS = {
    # Стартовые
    "starter_warrior":  {"name":"Меч Новобранца",    "rarity":"⚪","rarity_name":"Начальный","stat_key":"strength",  "damage":lambda c:int(8+c["strength"]*1.5), "desc_template":"8+Сила×1.5",   "effect":"Нет"},
    "starter_barbarian":{"name":"Боевой Топор",       "rarity":"⚪","rarity_name":"Начальный","stat_key":"strength",  "damage":lambda c:int(9+c["strength"]*1.6), "desc_template":"9+Сила×1.6",   "effect":"20% шанс ⛓️‍💥Слабость 1 ход."},
    "starter_assassin": {"name":"Кинжал Ассасина",   "rarity":"⚪","rarity_name":"Начальный","stat_key":"agility",   "damage":lambda c:int(7+c["agility"]*1.6),  "desc_template":"7+Ловк×1.6",   "effect":"10% шанс 🩸Кровотечение 1 ход."},
    "starter_ranger":   {"name":"Лук Следопыта",     "rarity":"⚪","rarity_name":"Начальный","stat_key":"agility",   "damage":lambda c:int(8+c["agility"]*1.6),  "desc_template":"8+Ловк×1.6",   "effect":"15% шанс двойного удара."},
    "starter_mage":     {"name":"Посох Волшебника",  "rarity":"⚪","rarity_name":"Начальный","stat_key":"intellect", "damage":lambda c:int(8+c["intellect"]*1.8),"desc_template":"8+Инт×1.8",    "effect":"15% шанс +⚡[мод.Инт] маны."},
    "starter_warlock":  {"name":"Жезл Колдуна",      "rarity":"⚪","rarity_name":"Начальный","stat_key":"intellect", "damage":lambda c:int(8+c["intellect"]*1.8),"desc_template":"8+Инт×1.8",    "effect":"15% шанс 1 ☠️Яд."},
    # Необычные
    "iron_sword":       {"name":"Железный меч",          "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(8+c["strength"]*2),    "desc_template":"8+Сила×2",    "effect":None},
    "battle_axe":       {"name":"Боевой топор",           "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(9+c["strength"]*2),    "desc_template":"9+Сила×2",    "effect":None},
    "long_sword":       {"name":"Длинный меч",            "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(10+c["strength"]*1.8), "desc_template":"10+Сила×1.8", "effect":None},
    "bone_dagger":      {"name":"Костяной кинжал",        "rarity":"🟢","rarity_name":"Необычный","stat_key":"agility",  "damage":lambda c:int(6+c["agility"]*2),     "desc_template":"6+Ловк×2",    "effect":None},
    "short_bow":        {"name":"Короткий лук",           "rarity":"🟢","rarity_name":"Необычный","stat_key":"agility",  "damage":lambda c:int(7+c["agility"]*2),     "desc_template":"7+Ловк×2",    "effect":"Требует 1 стрелу."},
    "hunting_bow":      {"name":"Охотничий лук",          "rarity":"🟢","rarity_name":"Необычный","stat_key":"agility",  "damage":lambda c:int(8+c["agility"]*2),     "desc_template":"8+Ловк×2",    "effect":"Требует 1 стрелу."},
    "guard_spear":      {"name":"Копьё стража",           "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(9+c["strength"]*1.9),  "desc_template":"9+Сила×1.9",  "effect":None},
    "war_hammer":       {"name":"Боевой молот",           "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(11+c["strength"]*1.7), "desc_template":"11+Сила×1.7", "effect":None},
    "iron_mace":        {"name":"Железная булава",        "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(9+c["strength"]*1.8),  "desc_template":"9+Сила×1.8",  "effect":None},
    "throwing_knife":   {"name":"Метательный кинжал",     "rarity":"🟢","rarity_name":"Необычный","stat_key":"agility",  "damage":lambda c:int(6+c["agility"]*2.2),   "desc_template":"6+Ловк×2.2",  "effect":"Требует 1 бросок."},
    "steel_blade":      {"name":"Стальной клинок",        "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(9+c["strength"]*2),    "desc_template":"9+Сила×2",    "effect":None},
    "smith_hammer":     {"name":"Кузнечный молот",        "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(10+c["strength"]*1.8), "desc_template":"10+Сила×1.8", "effect":None},
    "long_spear":       {"name":"Длинное копьё",          "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(9+c["strength"]*1.9),  "desc_template":"9+Сила×1.9",  "effect":None},
    "merc_saber":       {"name":"Сабля наёмника",         "rarity":"🟢","rarity_name":"Необычный","stat_key":"agility",  "damage":lambda c:int(8+c["agility"]*2),     "desc_template":"8+Ловк×2",    "effect":None},
    "bandit_dagger":    {"name":"Кинжал разбойника",      "rarity":"🟢","rarity_name":"Необычный","stat_key":"agility",  "damage":lambda c:int(7+c["agility"]*2),     "desc_template":"7+Ловк×2",    "effect":None},
    "guard_crossbow":   {"name":"Арбалет стражника",      "rarity":"🟢","rarity_name":"Необычный","stat_key":"agility",  "damage":lambda c:int(10+c["agility"]*1.8),  "desc_template":"10+Ловк×1.8", "effect":"Требует 1 болт."},
    "apprentice_staff": {"name":"Лёгкий посох ученика",  "rarity":"🟢","rarity_name":"Необычный","stat_key":"intellect","damage":lambda c:int(6+c["intellect"]*1.8), "desc_template":"6+Инт×1.8",   "effect":"+1 к регенерации маны."},
    "bone_staff":       {"name":"Костяной посох",         "rarity":"🟢","rarity_name":"Необычный","stat_key":"intellect","damage":lambda c:int(7+c["intellect"]*1.9), "desc_template":"7+Инт×1.9",   "effect":None},
    "battle_wand":      {"name":"Боевой жезл",            "rarity":"🟢","rarity_name":"Необычный","stat_key":"intellect","damage":lambda c:int(7+c["intellect"]*2),   "desc_template":"7+Инт×2",     "effect":"+5% к шансам статуса."},
    "training_sword":   {"name":"Тренировочный меч",      "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(8+c["strength"]*1.9),  "desc_template":"8+Сила×1.9",  "effect":None},
    "patrol_sword":     {"name":"Меч караула",            "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(9+c["strength"]*2),    "desc_template":"9+Сила×2",    "effect":None},
    "rusty_axe":        {"name":"Ржавый топор",           "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(9+c["strength"]*2),    "desc_template":"9+Сила×2",    "effect":None},
    "light_blade":      {"name":"Лёгкий клинок",          "rarity":"🟢","rarity_name":"Необычный","stat_key":"agility",  "damage":lambda c:int(8+c["agility"]*2),     "desc_template":"8+Ловк×2",    "effect":None},
    "short_spear":      {"name":"Короткое копьё",         "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(8+c["strength"]*1.9),  "desc_template":"8+Сила×1.9",  "effect":None},
    "hunt_crossbow":    {"name":"Охотничий арбалет",      "rarity":"🟢","rarity_name":"Необычный","stat_key":"agility",  "damage":lambda c:int(9+c["agility"]*1.9),   "desc_template":"9+Ловк×1.9",  "effect":"Требует 1 болт."},
    "apprentice_staff2":{"name":"Посох ученика",          "rarity":"🟢","rarity_name":"Необычный","stat_key":"intellect","damage":lambda c:int(7+c["intellect"]*1.9), "desc_template":"7+Инт×1.9",   "effect":"Лёгкий бонус к мане."},
    "old_wand":         {"name":"Старый жезл",            "rarity":"🟢","rarity_name":"Необычный","stat_key":"intellect","damage":lambda c:int(7+c["intellect"]*1.8), "desc_template":"7+Инт×1.8",   "effect":None},
    "curved_dagger":    {"name":"Кривой кинжал",          "rarity":"🟢","rarity_name":"Необычный","stat_key":"agility",  "damage":lambda c:int(6+c["agility"]*2),     "desc_template":"6+Ловк×2",    "effect":None},
    "battle_sickle":    {"name":"Боевой серп",            "rarity":"🟢","rarity_name":"Необычный","stat_key":"agility",  "damage":lambda c:int(8+c["agility"]*2),     "desc_template":"8+Ловк×2",    "effect":None},
    "soldier_sword":    {"name":"Солдатский меч",         "rarity":"🟢","rarity_name":"Необычный","stat_key":"strength", "damage":lambda c:int(9+c["strength"]*2),    "desc_template":"9+Сила×2",    "effect":None},
    # Редкие
    "flaming_blade":    {"name":"🔥Пылающий клинок",      "rarity":"🔵","rarity_name":"Редкий","stat_key":"strength", "damage":lambda c:int(12+c["strength"]*2),   "desc_template":"12+Сила×2",    "effect":"🔥Ожог 2 хода."},
    "ice_axe":          {"name":"❄️Ледяной топор",         "rarity":"🔵","rarity_name":"Редкий","stat_key":"strength", "damage":lambda c:int(13+c["strength"]*1.9), "desc_template":"13+Сила×1.9",  "effect":"❄️Холод 2 хода."},
    "lightning_blade":  {"name":"⚡Клинок молнии",         "rarity":"🔵","rarity_name":"Редкий","stat_key":"agility",  "damage":lambda c:int(11+c["agility"]*2.1),  "desc_template":"11+Ловк×2.1",  "effect":"💫Шок 1 ход."},
    "poison_dagger":    {"name":"☠️Отравленный кинжал",    "rarity":"🔵","rarity_name":"Редкий","stat_key":"agility",  "damage":lambda c:int(10+c["agility"]*2.2),  "desc_template":"10+Ловк×2.2",  "effect":"☠️Яд 3 хода."},
    "blood_sickle":     {"name":"🩸Кровавый серп",         "rarity":"🔵","rarity_name":"Редкий","stat_key":"agility",  "damage":lambda c:int(12+c["agility"]*2),    "desc_template":"12+Ловк×2",    "effect":"🩸Кровотечение 3 хода."},
    "merc_blade":       {"name":"⚔️Клинок наёмника",       "rarity":"🔵","rarity_name":"Редкий","stat_key":"strength", "damage":lambda c:int(13+c["strength"]*2),   "desc_template":"13+Сила×2",    "effect":None},
    "wind_hunter_bow":  {"name":"🏹Лук охотника ветра",    "rarity":"🔵","rarity_name":"Редкий","stat_key":"agility",  "damage":lambda c:int(11+c["agility"]*2.1),  "desc_template":"11+Ловк×2.1",  "effect":"Требует 1 стрелу."},
    "storm_crossbow":   {"name":"⚡Арбалет бури",           "rarity":"🔵","rarity_name":"Редкий","stat_key":"agility",  "damage":lambda c:int(13+c["agility"]*2),    "desc_template":"13+Ловк×2",    "effect":"Требует 1 болт. 💫Шок 1 ход."},
    "ice_guard_spear":  {"name":"🧊Копьё ледяного стража", "rarity":"🔵","rarity_name":"Редкий","stat_key":"strength", "damage":lambda c:int(14+c["strength"]*1.9), "desc_template":"14+Сила×1.9",  "effect":"❄️Холод 2 хода."},
    "flame_hammer":     {"name":"🔥Боевой молот пламени",  "rarity":"🔵","rarity_name":"Редкий","stat_key":"strength", "damage":lambda c:int(15+c["strength"]*1.8), "desc_template":"15+Сила×1.8",  "effect":"🔥Ожог 2 хода."},
    "vortex_saber":     {"name":"🌪️Сабля вихря",           "rarity":"🔵","rarity_name":"Редкий","stat_key":"agility",  "damage":lambda c:int(12+c["agility"]*2.1),  "desc_template":"12+Ловк×2.1",  "effect":None},
    "black_magic_staff":{"name":"💀Посох чёрной магии",    "rarity":"🔵","rarity_name":"Редкий","stat_key":"intellect","damage":lambda c:int(10+c["intellect"]*2),  "desc_template":"10+Инт×2",     "effect":"+10% к силе заклинаний."},
    "dark_wand":        {"name":"🌑Жезл тёмных чар",       "rarity":"🔵","rarity_name":"Редкий","stat_key":"intellect","damage":lambda c:int(11+c["intellect"]*2),  "desc_template":"11+Инт×2",     "effect":"⛓️‍💥Слабость 2 хода."},
    "thunder_staff":    {"name":"⚡Посох грома",            "rarity":"🔵","rarity_name":"Редкий","stat_key":"intellect","damage":lambda c:int(12+c["intellect"]*2),  "desc_template":"12+Инт×2",     "effect":"💫Шок 1 ход."},
    "ice_storm_staff":  {"name":"❄️Посох ледяной бури",    "rarity":"🔵","rarity_name":"Редкий","stat_key":"intellect","damage":lambda c:int(12+c["intellect"]*2),  "desc_template":"12+Инт×2",     "effect":"❄️Холод 3 хода."},
    "fury_fire_staff":  {"name":"🔥Посох огненной ярости", "rarity":"🔵","rarity_name":"Редкий","stat_key":"intellect","damage":lambda c:int(13+c["intellect"]*2),  "desc_template":"13+Инт×2",     "effect":"🔥Ожог 3 хода."},
    "plague_knight":    {"name":"☠️Клинок чумного рыцаря", "rarity":"🔵","rarity_name":"Редкий","stat_key":"strength", "damage":lambda c:int(14+c["strength"]*2),   "desc_template":"14+Сила×2",    "effect":"☠️Яд 3 хода."},
    "cult_dagger":      {"name":"🩸Кинжал кровавого культа","rarity":"🔵","rarity_name":"Редкий","stat_key":"agility", "damage":lambda c:int(12+c["agility"]*2.2),  "desc_template":"12+Ловк×2.2",  "effect":"🩸Кровотечение 3 хода."},
    "fortress_sword":   {"name":"⚔️Меч стража крепости",   "rarity":"🔵","rarity_name":"Редкий","stat_key":"strength", "damage":lambda c:int(14+c["strength"]*2),   "desc_template":"14+Сила×2",    "effect":None},
    "storm_blade":      {"name":"🌩️Клинок бури",           "rarity":"🔵","rarity_name":"Редкий","stat_key":"strength", "damage":lambda c:int(15+c["strength"]*1.9), "desc_template":"15+Сила×1.9",  "effect":"💫Шок 2 хода."},
    # Эпические
    "arctic_hammer":    {"name":"❄️Арктический Молот",          "rarity":"🟣","rarity_name":"Эпический","stat_key":"strength", "damage":lambda c:int(16+c["strength"]*2),   "desc_template":"16+Сила×2",  "effect":None},
    "flame_blade":      {"name":"🔥Пламенный Клинок",           "rarity":"🟣","rarity_name":"Эпический","stat_key":"strength", "damage":lambda c:int(17+c["strength"]*2),   "desc_template":"17+Сила×2",  "effect":None},
    "lightning_dagger": {"name":"⚡Молниеносный Кинжал",        "rarity":"🟣","rarity_name":"Эпический","stat_key":"agility",  "damage":lambda c:int(15+c["agility"]*2),    "desc_template":"15+Ловк×2",  "effect":None},
    "poison_sickle":    {"name":"☠️Ядовитый Серп",              "rarity":"🟣","rarity_name":"Эпический","stat_key":"agility",  "damage":lambda c:int(16+c["agility"]*2),    "desc_template":"16+Ловк×2",  "effect":None},
    "blood_blade_epic": {"name":"🩸Кровавый Клинок",            "rarity":"🟣","rarity_name":"Эпический","stat_key":"agility",  "damage":lambda c:int(17+c["agility"]*2),    "desc_template":"17+Ловк×2",  "effect":None},
    "light_warrior":    {"name":"⚔️Клинок Воина Света",         "rarity":"🟣","rarity_name":"Эпический","stat_key":"strength", "damage":lambda c:int(18+c["strength"]*2),   "desc_template":"18+Сила×2",  "effect":None},
    "shadow_bow":       {"name":"🏹Лук Теней",                  "rarity":"🟣","rarity_name":"Эпический","stat_key":"agility",  "damage":lambda c:int(16+c["agility"]*2),    "desc_template":"16+Ловк×2",  "effect":"Требует 1 стрелу."},
    "storm_crossbow_e": {"name":"⚡Арбалет Грозы",              "rarity":"🟣","rarity_name":"Эпический","stat_key":"agility",  "damage":lambda c:int(18+c["agility"]*2),    "desc_template":"18+Ловк×2",  "effect":"Требует 1 болт."},
    "ice_staff_epic":   {"name":"🧊Ледяной Посох",              "rarity":"🟣","rarity_name":"Эпический","stat_key":"intellect","damage":lambda c:int(16+c["intellect"]*2),  "desc_template":"16+Инт×2",   "effect":None},
    "fire_will_staff":  {"name":"🔥Посох Огненной Воли",        "rarity":"🟣","rarity_name":"Эпический","stat_key":"intellect","damage":lambda c:int(17+c["intellect"]*2),  "desc_template":"17+Инт×2",   "effect":None},
    "lightning_storm_staff":{"name":"⚡Посох Молниеносной Бури","rarity":"🟣","rarity_name":"Эпический","stat_key":"intellect","damage":lambda c:int(18+c["intellect"]*2),  "desc_template":"18+Инт×2",   "effect":None},
    "poison_dark_staff":{"name":"☠️Посох Ядовитой Тьмы",       "rarity":"🟣","rarity_name":"Эпический","stat_key":"intellect","damage":lambda c:int(17+c["intellect"]*2),  "desc_template":"17+Инт×2",   "effect":None},
    # Легендарные
    "fire_fang":        {"name":"🔥Клинок Огненного Клыка",  "rarity":"🟠","rarity_name":"Легендарный","stat_key":"strength", "damage":lambda c:int(25+c["strength"]*2),  "desc_template":"25+Сила×2",  "effect":"Удар наносится дважды."},
    "ice_fury":         {"name":"❄️Ледяная Ярость",          "rarity":"🟠","rarity_name":"Легендарный","stat_key":"strength", "damage":lambda c:int(24+c["strength"]*2),  "desc_template":"24+Сила×2",  "effect":"❄️Холод 3 хода."},
    "lightning_discharge_leg":{"name":"⚡Молниеносный Разряд","rarity":"🟠","rarity_name":"Легендарный","stat_key":"agility", "damage":lambda c:int(23+c["agility"]*2),   "desc_template":"23+Ловк×2",  "effect":"💫Шок 1 ход (пропуск)."},
    "plague_blade":     {"name":"☠️Клинок Чумы",            "rarity":"🟠","rarity_name":"Легендарный","stat_key":"agility",  "damage":lambda c:int(24+c["agility"]*2),   "desc_template":"24+Ловк×2",  "effect":"☠️Яд 4 хода."},
    "blood_fury":       {"name":"🩸Кровавая Ярость",         "rarity":"🟠","rarity_name":"Легендарный","stat_key":"agility",  "damage":lambda c:int(25+c["agility"]*2),   "desc_template":"25+Ловк×2",  "effect":"🩸Кровотечение 4 хода."},
    "lightbearer_sword":{"name":"⚔️Меч Светоносца",         "rarity":"🟠","rarity_name":"Легендарный","stat_key":"strength", "damage":lambda c:int(26+c["strength"]*2),  "desc_template":"26+Сила×2",  "effect":"Игнорирует броню врага."},
    "ice_storm_staff_leg":{"name":"🧊Посох Ледяной Бури",   "rarity":"🟠","rarity_name":"Легендарный","stat_key":"intellect","damage":lambda c:int(25+c["intellect"]*2), "desc_template":"25+Инт×2",   "effect":"❄️Холод 4 хода + 💫Шок 2 хода."},
}

# ═══════════════════════════════════════════════════════════════
# ЭФФЕКТЫ СТАТУСОВ
# ═══════════════════════════════════════════════════════════════

STATUS_EFFECTS = {
    "burn":       {"name":"Ожог","emoji":"🔥","desc":"Наносит 5–10 урона в конце каждого хода."},
    "cold":       {"name":"Холод","emoji":"❄️","desc":"Уменьшает скорость и ловкость на -2."},
    "shock":      {"name":"Шок","emoji":"💫","desc":"Пропускает ход."},
    "weakness":   {"name":"Слабость","emoji":"⛓️‍💥","desc":"-50% урона и -2 к силе."},
    "poison":     {"name":"Яд","emoji":"☠️","desc":"Урон = 10×{стак}, убывает на 1 каждый ход."},
    "blind":      {"name":"Слепота","emoji":"👁️‍🗨️","desc":"50% шанс промахнуться."},
    "regen":      {"name":"Регенерация","emoji":"🌿","desc":"Восст. 10×{стак} ХП, убывает на 1."},
    "fear":       {"name":"Страх","emoji":"😱","desc":"Не может атаковать."},
    "sleep":      {"name":"Сон","emoji":"💤","desc":"Пропуск хода до получения урона."},
    "bleed":      {"name":"Кровотечение","emoji":"🩸","desc":"Наносит 8–10 урона при любом действии."},
    "second_wind":{"name":"Второе дыхание","emoji":"❤️‍🔥","desc":"Выжить при смерти с 1 ХП."},
}

# ═══════════════════════════════════════════════════════════════
# РАСХОДНИКИ
# ═══════════════════════════════════════════════════════════════

CONSUMABLES = {
    "health_potion":     {"name":"Зелье здоровья",            "emoji":"❤️",   "desc":"Восстанавливает 25–50 HP.","type":"consumable"},
    "big_health_potion": {"name":"Большое зелье здоровья",    "emoji":"❤️❤️", "desc":"Восстанавливает 75–100 HP.","type":"consumable"},
    "mana_potion":       {"name":"Зелье маны",                "emoji":"⚡",   "desc":"Восстанавливает 15–30 MP.","type":"consumable"},
    "big_mana_potion":   {"name":"Большое зелье маны",        "emoji":"⚡⚡",  "desc":"Восстанавливает 50–70 MP.","type":"consumable"},
    "str_potion":        {"name":"Зелье силы",                "emoji":"💪",   "desc":"+2 к Силе на 3 этажа.","type":"consumable"},
    "agi_potion":        {"name":"Зелье ловкости",            "emoji":"🎯",   "desc":"+2 к Ловкости на 3 этажа.","type":"consumable"},
    "int_potion":        {"name":"Зелье интеллекта",          "emoji":"🧠",   "desc":"+2 к Интеллекту на 3 этажа.","type":"consumable"},
    "con_potion":        {"name":"Зелье телосложения",        "emoji":"🫀",   "desc":"+5 HP максимум на 3 этажа.","type":"consumable"},
    "cha_potion":        {"name":"Зелье харизмы",             "emoji":"👄",   "desc":"+2 к Харизме на 3 этажа.","type":"consumable"},
    "arrows":            {"name":"Стрелы",                    "emoji":"🏹",   "desc":"1 стрела на выстрел.","type":"ammo"},
    "bolts":             {"name":"Арбалетные болты",          "emoji":"⚡",   "desc":"Боеприпас для арбалетов, +2 урон.","type":"ammo"},
    "bomb":              {"name":"Бомба",                     "emoji":"💣",   "desc":"10–20 урона всем врагам. 20% 🔥ожог.","type":"consumable"},
    "ice_flask":         {"name":"Ледяной флакон",            "emoji":"❄️",   "desc":"5–10 урона 1 врагу + 1 ❄️холод.","type":"consumable"},
    "speed_potion":      {"name":"Зелье быстрого бега",       "emoji":"🏃",   "desc":"+3 к скорости на 3 этажа.","type":"consumable"},
    "scroll_fireball":   {"name":"Свиток огненного шара",     "emoji":"🔥📜", "desc":"Одноразовый огненный шар.","type":"scroll"},
    "scroll_ice_arrow":  {"name":"Свиток ледяной стрелы",     "emoji":"❄️📜", "desc":"Одноразовая ледяная стрела.","type":"scroll"},
    "scroll_heal":       {"name":"Свиток исцеления",          "emoji":"❤️📜", "desc":"Восстанавливает 30–50 HP.","type":"scroll"},
    "scroll_mana":       {"name":"Свиток маны",               "emoji":"⚡📜", "desc":"Восстанавливает 20–40 MP.","type":"scroll"},
    "smoke_bomb":        {"name":"Дымовая бомба",             "emoji":"🌫️",  "desc":"👁️‍🗨️Слепота всем врагам на 2 хода.","type":"consumable"},
    "lantern":           {"name":"Фонарик",                   "emoji":"🔦",   "desc":"Освещает скрытых врагов. Вне боя.","type":"tool"},
    "rope":              {"name":"Верёвка",                   "emoji":"🪢",   "desc":"Для ловушек или спуска.","type":"tool"},
    "pickaxe":           {"name":"Кирка",                     "emoji":"⛏️",   "desc":"Разрушает стены/сундуки.","type":"tool"},
    "poison_bomb":       {"name":"Ядовитая бомба",            "emoji":"☠️",   "desc":"5 ☠️Яда всем врагам.","type":"consumable"},
    "regen_small":       {"name":"Малый эликсир регенерации", "emoji":"🌿",   "desc":"+2 HP и +2 MP каждый ход (3 хода).","type":"consumable"},
    "regen_big":         {"name":"Большой эликсир регенерации","emoji":"🌿🌿","desc":"+5 HP и +5 MP каждый ход (5 ходов).","type":"consumable"},
    "scroll_teleport":   {"name":"Свиток телепортации",       "emoji":"✨📜", "desc":"Случайный этаж вперёд (1–7).","type":"scroll"},
    "second_wind_potion":{"name":"Зелье второго дыхания",     "emoji":"❤️‍🔥", "desc":"Статус «Второе дыхание».","type":"consumable"},
}

# ═══════════════════════════════════════════════════════════════
# ЗАКЛИНАНИЯ
# ═══════════════════════════════════════════════════════════════

SPELLS = {
    "fire_spark":          {"name":"Искра огня",             "emoji":"🔥","level":1,"mana":4, "desc":"Наносит 6+(Инт×1) урона. 🔥Ожог(2).","damage":lambda i:int(6+i*1),  "effect":("burn",2)},
    "ice_arrow_1":         {"name":"Ледяная стрела",         "emoji":"❄️","level":1,"mana":4, "desc":"Наносит 5+(Инт×1) урона. ❄️Холод(2).","damage":lambda i:int(5+i*1), "effect":("cold",2)},
    "lightning_spark":     {"name":"Искра молнии",           "emoji":"⚡","level":1,"mana":5, "desc":"6+(Инт×1.1) урона. 20% 💫Шок(1).","damage":lambda i:int(6+i*1.1),   "effect":("shock",1),"effect_chance":0.2},
    "poison_bite":         {"name":"Ядовитый укус",          "emoji":"☠️","level":1,"mana":5, "desc":"☠️Яд(2).","damage":None,"effect":("poison",2)},
    "blindness_fog":       {"name":"Туман слепоты",          "emoji":"🌫️","level":1,"mana":6, "desc":"👁️‍🗨️Слепота(2).","damage":None,"effect":("blind",2)},
    "minor_regen":         {"name":"Малое восстановление",   "emoji":"🌿","level":1,"mana":5, "desc":"🌿Регенерация(2).","damage":None,"effect":("regen",2),"target":"self"},
    "blood_prick":         {"name":"Кровавый укол",          "emoji":"🩸","level":1,"mana":5, "desc":"5+(Инт×1) урона. 🩸Кровотечение(2).","damage":lambda i:int(5+i*1),"effect":("bleed",2)},
    "weakness_curse":      {"name":"Проклятие слабости",     "emoji":"💀","level":1,"mana":6, "desc":"⛓️‍💥Слабость(2).","damage":None,"effect":("weakness",2)},
    "fear_aura":           {"name":"Аура страха",            "emoji":"😱","level":1,"mana":7, "desc":"😱Страх(1).","damage":None,"effect":("fear",1)},
    "magic_barrier":       {"name":"Магический барьер",      "emoji":"🛡️","level":1,"mana":6, "desc":"Снижает урон на 10+Инт.","damage":None,"effect":("barrier",0),"target":"self","barrier_val":lambda i:10+i},
    "electrocharge":       {"name":"Электроразряд",          "emoji":"💫","level":1,"mana":5, "desc":"6+(Инт×1.1) урона.","damage":lambda i:int(6+i*1.1),"effect":None},
    "sleep_spell":         {"name":"Усыпление",              "emoji":"🌙","level":1,"mana":7, "desc":"💤Сон.","damage":None,"effect":("sleep",0)},
    "fireball":            {"name":"Огненный шар",           "emoji":"🔥","level":2,"mana":8, "desc":"10+(Инт×1.5) урона. 🔥Ожог(3).","damage":lambda i:int(10+i*1.5),"effect":("burn",3)},
    "ice_arrow_2":         {"name":"Ледяная стрела II",      "emoji":"❄️","level":2,"mana":7, "desc":"9+(Инт×1.4) урона. ❄️Холод(2).","damage":lambda i:int(9+i*1.4), "effect":("cold",2)},
    "lightning_discharge": {"name":"Разряд молнии",          "emoji":"⚡","level":2,"mana":9, "desc":"12+(Инт×1.6) урона. 💫Шок(1).","damage":lambda i:int(12+i*1.6),"effect":("shock",1)},
    "poison_cloud":        {"name":"Ядовитое облако",        "emoji":"☠️","level":2,"mana":8, "desc":"☠️Яд(3).","damage":None,"effect":("poison",3)},
    "strong_regen":        {"name":"Сильная регенерация",    "emoji":"🌿","level":2,"mana":8, "desc":"🌿Регенерация(3).","damage":None,"effect":("regen",3),"target":"self"},
    "blood_curse":         {"name":"Кровавое проклятие",     "emoji":"🩸","level":2,"mana":9, "desc":"🩸Кровотечение(3).","damage":None,"effect":("bleed",3)},
    "darkness_curse":      {"name":"Проклятие тьмы",         "emoji":"👁️","level":2,"mana":8, "desc":"👁️‍🗨️Слепота(3).","damage":None,"effect":("blind",3)},
    "terror_wave":         {"name":"Волна ужаса",            "emoji":"😱","level":2,"mana":10,"desc":"😱Страх(2).","damage":None,"effect":("fear",2)},
    "protection_sphere":   {"name":"Сфера защиты",           "emoji":"🛡️","level":2,"mana":9, "desc":"Снижает урон на 20+Инт.","damage":None,"effect":("barrier",0),"target":"self","barrier_val":lambda i:20+i},
    "magic_push":          {"name":"Магический толчок",      "emoji":"🌪️","level":2,"mana":8, "desc":"10+(Инт×1.5) урона.","damage":lambda i:int(10+i*1.5),"effect":None},
    "fire_storm":          {"name":"Огненная буря",          "emoji":"🔥","level":3,"mana":12,"desc":"15+(Инт×2) урона. 🔥Ожог(3).","damage":lambda i:int(15+i*2),"effect":("burn",3)},
    "ice_storm":           {"name":"Ледяной шторм",          "emoji":"❄️","level":3,"mana":12,"desc":"14+(Инт×2) урона. ❄️Холод(3).","damage":lambda i:int(14+i*2),"effect":("cold",3)},
    "chain_lightning":     {"name":"Цепная молния",          "emoji":"⚡","level":3,"mana":13,"desc":"17+(Инт×2) урона. 💫Шок(1).","damage":lambda i:int(17+i*2),"effect":("shock",1)},
    "plague":              {"name":"Чума",                   "emoji":"☠️","level":3,"mana":12,"desc":"☠️Яд(4).","damage":None,"effect":("poison",4)},
    "flesh_tear":          {"name":"Разрыв плоти",           "emoji":"🩸","level":3,"mana":12,"desc":"🩸Кровотечение(4).","damage":None,"effect":("bleed",4)},
    "deep_sleep":          {"name":"Глубокий сон",           "emoji":"🌙","level":3,"mana":13,"desc":"💤Сон.","damage":None,"effect":("sleep",0)},
    "horror_curse":        {"name":"Проклятие ужаса",        "emoji":"😱","level":3,"mana":13,"desc":"😱Страх(2).","damage":None,"effect":("fear",2)},
    "life_flow":           {"name":"Поток жизни",            "emoji":"🌿","level":3,"mana":12,"desc":"🌿Регенерация(4).","damage":None,"effect":("regen",4),"target":"self"},
    "void_darkness":       {"name":"Тьма бездны",            "emoji":"👁️","level":3,"mana":13,"desc":"👁️‍🗨️Слепота(4).","damage":None,"effect":("blind",4)},
    "weakening_curse":     {"name":"Ослабляющее проклятие",  "emoji":"💀","level":3,"mana":12,"desc":"⛓️‍💥Слабость(3).","damage":None,"effect":("weakness",3)},
    "hellfire":            {"name":"Адское пламя",           "emoji":"🔥","level":4,"mana":16,"desc":"22+(Инт×2.5) урона. 🔥Ожог(4).","damage":lambda i:int(22+i*2.5),"effect":("burn",4)},
    "lightning_storm":     {"name":"Буря молний",            "emoji":"⚡","level":4,"mana":17,"desc":"23+(Инт×2.5) урона. 💫Шок(2).","damage":lambda i:int(23+i*2.5),"effect":("shock",2)},
    "death_plague":        {"name":"Смертельная чума",       "emoji":"☠️","level":4,"mana":16,"desc":"☠️Яд(5).","damage":None,"effect":("poison",5)},
    "blood_execution":     {"name":"Кровавая казнь",         "emoji":"🩸","level":4,"mana":16,"desc":"🩸Кровотечение(5).","damage":None,"effect":("bleed",5)},
    "horror_gaze":         {"name":"Взгляд ужаса",           "emoji":"😱","level":4,"mana":15,"desc":"😱Страх(3).","damage":None,"effect":("fear",3)},
    "great_regen":         {"name":"Великая регенерация",    "emoji":"🌿","level":4,"mana":15,"desc":"🌿Регенерация(5).","damage":None,"effect":("regen",5),"target":"self"},
    "shadow_punishment":   {"name":"Теневая кара",           "emoji":"🌑","level":4,"mana":16,"desc":"20+(Инт×2.4) урона. ⛓️‍💥Слабость(3).","damage":lambda i:int(20+i*2.4),"effect":("weakness",3)},
    "meteor":              {"name":"Метеор",                 "emoji":"☄️","level":5,"mana":22,"desc":"30+(Инт×3) урона. 🔥Ожог(5).","damage":lambda i:int(30+i*3),"effect":("burn",5)},
    "lightning_cataclysm": {"name":"Катаклизм молний",       "emoji":"⚡","level":5,"mana":23,"desc":"32+(Инт×3) урона. 💫Шок(2).","damage":lambda i:int(32+i*3),"effect":("shock",2)},
    "destruction_plague":  {"name":"Чума разрушения",        "emoji":"☠️","level":5,"mana":21,"desc":"☠️Яд(6).","damage":None,"effect":("poison",6)},
    "blood_apocalypse":    {"name":"Кровавый апокалипсис",   "emoji":"🩸","level":5,"mana":21,"desc":"🩸Кровотечение(6).","damage":None,"effect":("bleed",6)},
    "death_touch":         {"name":"Прикосновение смерти",   "emoji":"🌑","level":5,"mana":22,"desc":"28+(Инт×2.8) урона. ⛓️‍💥Слабость(4).","damage":lambda i:int(28+i*2.8),"effect":("weakness",4)},
}

STARTING_SPELLS = {
    "mage":    ["fire_spark","ice_arrow_1"],
    "warlock": ["poison_bite","fear_aura"],
}

# ═══════════════════════════════════════════════════════════════
# НАЧАЛЬНЫЕ ПРЕДМЕТЫ
# ═══════════════════════════════════════════════════════════════

STARTING_ITEMS = {
    "warrior":   {"health_potion":2,"str_potion":1,"bomb":1,"regen_small":1,"rope":1},
    "barbarian": {"health_potion":3,"str_potion":1,"speed_potion":1,"bomb":1},
    "assassin":  {"health_potion":1,"agi_potion":1,"smoke_bomb":1,"poison_bomb":1,"regen_small":1},
    "ranger":    {"health_potion":1,"agi_potion":1,"arrows":15,"ice_flask":1,"lantern":1},
    "mage":      {"health_potion":1,"mana_potion":2,"scroll_fireball":1,"scroll_heal":1,"regen_small":1},
    "warlock":   {"health_potion":1,"mana_potion":2,"scroll_ice_arrow":1,"poison_bomb":1,"scroll_teleport":1},
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
            weapon          TEXT DEFAULT NULL,
            armor           TEXT DEFAULT 'Лёгкая одежда',
            artifact        TEXT DEFAULT 'Нет',
            coins           INTEGER DEFAULT 0,
            best_floor      INTEGER DEFAULT 0,
            items           TEXT DEFAULT '{}',
            owned_weapons   TEXT DEFAULT '[]',
            owned_armors    TEXT DEFAULT '["Лёгкая одежда"]',
            owned_artifacts TEXT DEFAULT '[]',
            learned_spells  TEXT DEFAULT '[]',
            spell_slot_1    TEXT DEFAULT NULL,
            spell_slot_2    TEXT DEFAULT NULL,
            spell_slot_3    TEXT DEFAULT NULL
        )
    ''')
    for col, defval in [
        ("items","TEXT DEFAULT '{}'"),("owned_weapons","TEXT DEFAULT '[]'"),
        ("owned_armors","TEXT DEFAULT '[\"Лёгкая одежда\"]'"),("owned_artifacts","TEXT DEFAULT '[]'"),
        ("learned_spells","TEXT DEFAULT '[]'"),("spell_slot_1","TEXT DEFAULT NULL"),
        ("spell_slot_2","TEXT DEFAULT NULL"),("spell_slot_3","TEXT DEFAULT NULL"),
        ("username","TEXT DEFAULT NULL"),
    ]:
        try: c.execute(f"ALTER TABLE tower_chars ADD COLUMN {col} {defval}"); conn.commit()
        except: conn.rollback()
    conn.commit()
    conn.close()
    print("Таблица tower_chars инициализирована!")

def save_username(user_id, username):
    """Сохраняет или обновляет username игрока."""
    if not username:
        return
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE tower_chars SET username=%s WHERE user_id=%s', (username, user_id))
    conn.commit()
    conn.close()

def get_leaderboard(limit=10):
    """Возвращает топ игроков по best_floor."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT username, char_name, class_key, level, best_floor
        FROM tower_chars
        WHERE best_floor > 0
        ORDER BY best_floor DESC
        LIMIT %s
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows
    conn = get_conn()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute('SELECT * FROM tower_chars WHERE user_id=%s', (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def create_tower_char(user_id, char_name, class_key):
    cls = CLASSES[class_key]
    stats = cls["stats"]
    max_hp = cls["base_hp"] + stats["constitution"] * 1 * cls["k1"]
    max_mp = cls["base_mp"] + stats["intellect"] * 1 * cls["k2"]
    start_weapon_key = cls["start_weapon"]
    starting_items = json.dumps(STARTING_ITEMS.get(class_key, {}))
    owned_weapons = json.dumps([start_weapon_key])
    start_spells = STARTING_SPELLS.get(class_key, [])
    learned = json.dumps(start_spells)
    slot1 = start_spells[0] if len(start_spells) > 0 else None
    slot2 = start_spells[1] if len(start_spells) > 1 else None
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO tower_chars
        (user_id, char_name, class_key, level, exp, stat_points, mastery_bonus,
         hp, mp, strength, agility, intellect, constitution, speed, charisma,
         weapon, armor, artifact, coins, best_floor,
         items, owned_weapons, owned_armors, owned_artifacts,
         learned_spells, spell_slot_1, spell_slot_2, spell_slot_3)
        VALUES (%s,%s,%s,1,0,0,1,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,'Лёгкая одежда','Нет',0,0,
                %s,%s,'["Лёгкая одежда"]','[]',
                %s,%s,%s,NULL)
        ON CONFLICT (user_id) DO NOTHING
    ''', (
        user_id, char_name, class_key,
        max_hp, max_mp,
        stats["strength"], stats["agility"], stats["intellect"],
        stats["constitution"], stats["speed"], stats["charisma"],
        start_weapon_key, starting_items, owned_weapons,
        learned, slot1, slot2
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
    try: return json.loads(char.get('items') or '{}')
    except: return {}

def save_items(user_id, items_dict):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE tower_chars SET items=%s WHERE user_id=%s', (json.dumps(items_dict), user_id))
    conn.commit()
    conn.close()

def get_owned_list(char, col):
    try: return json.loads(char.get(col) or '[]')
    except: return []

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

def safe(text):
    return str(text).replace('_', '\\_').replace('*', '\\*')

# ═══════════════════════════════════════════════════════════════
# UI ТЕКСТЫ
# ═══════════════════════════════════════════════════════════════

def weapon_line_text(char):
    w_key = char.get('weapon')
    w = WEAPONS.get(w_key)
    if w:
        return f"{w['name']} *(урон: {w['damage'](char)})*"
    return str(w_key or 'Нет')

def tower_main_text(char):
    cls = CLASSES[char['class_key']]
    max_hp = calc_max_hp(char)
    max_mp = calc_max_mp(char)
    lvl = char['level']
    lead = cls['lead']

    def stat_line(key):
        star = "⭐" if key in lead else "  "
        return f"{star}{STAT_NAMES[key]}: {char[key]}"

    skills = []
    for i, slot in enumerate(['skill_1','skill_2','skill_3'], 1):
        val = char[slot] or '—'
        skills.append(f"{'1️⃣2️⃣3️⃣'[i-1]} {val}")

    return (
        f"— – - 🏯 БАШНЯ ХАОСА 🏯 - – —\n\n"
        f"🎖️ Твой рекорд: *{char['best_floor']}* этаж\n\n"
        f"– *{safe(char['char_name'])}* –\n"
        f"Класс: {cls['emoji']} {cls['name']}\n"
        f"Уровень: *{lvl}* (⭐ {char['exp']}/{exp_for_next_level(lvl)} опыта)\n"
        f"Очки Характеристик: *{char['stat_points']}*\n"
        f"Бонус Мастерства: *+{mastery_bonus(lvl)}*\n\n"
        f"❤️ ХП: *{char['hp']}/{max_hp}*\n"
        f"⚡ Мана: *{char['mp']}/{max_mp}*\n\n"
        f"{stat_line('strength')}\n{stat_line('agility')}\n{stat_line('intellect')}\n"
        f"{stat_line('constitution')}\n{stat_line('speed')}\n{stat_line('charisma')}\n\n"
        f"💫 *Навыки:*\n{chr(10).join(skills)}\n\n"
        f"– 📦 Снаряжение –\n\n"
        f"🗡️ Оружие: {weapon_line_text(char)}\n"
        f"🛡️ Броня: {char['armor']}\n"
        f"🧪 Артефакт: {char['artifact']}\n\n"
        f"💰 Монет: *{char['coins']}*\n\n{SEP}"
    )

def tower_main_keyboard(char):
    is_spell = char['class_key'] in SPELL_CLASSES
    markup = InlineKeyboardMarkup(row_width=2)
    if is_spell:
        markup.add(
            InlineKeyboardButton("⚔️ Начать",       callback_data="tower_start"),
            InlineKeyboardButton("💫 Заклинания",    callback_data="tower_spells"),
        )
    else:
        markup.add(InlineKeyboardButton("⚔️ Начать", callback_data="tower_start"))
    markup.add(
        InlineKeyboardButton("⬆️ Улучшить статы",   callback_data="tower_upgrade"),
        InlineKeyboardButton("📜 Навыки",            callback_data="tower_skills"),
        InlineKeyboardButton("🎒 Рюкзак",            callback_data="tower_bag"),
        InlineKeyboardButton("🏆 Рекорды",           callback_data="tower_records"),
        InlineKeyboardButton("❌ Удалить персонажа", callback_data="tower_delete_ask"),
    )
    return markup

def class_select_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    for key, cls in CLASSES.items():
        markup.add(InlineKeyboardButton(f"{cls['emoji']} {cls['name']}", callback_data=f"tower_class_{key}"))
    return markup

def upgrade_text(char):
    cls = CLASSES[char['class_key']]
    def sl(key, label):
        val = char[key]; cost = cp_cost(val)
        maxed = " *(МАКС)*" if val >= 20 else f" *({cost} ОХ)*"
        return f"{label}: *{val}*{maxed}"
    return (
        f"— – - ⬆️✨ УЛУЧШЕНИЕ ХАРАКТЕРИСТИК ✨⬆️ - – —\n\n"
        f"Имя: *{safe(char['char_name'])}*\nКласс: {cls['emoji']} {cls['name']}\n"
        f"⭐ Уровень: *{char['level']}*\n\n🪙 Очки Характеристик: *{char['stat_points']}*\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"❤️ ХП: *{char['hp']}/{calc_max_hp(char)}*\n"
        f"⚡ Макс. Мана: *{calc_max_mp(char)}*\n\n"
        f"{sl('strength','💪 Сила')}\n\n{sl('agility','🎯 Ловкость')}\n\n"
        f"{sl('intellect','🧠 Интеллект')}\n\n{sl('constitution','🫀 Телосложение')}\n\n"
        f"{sl('charisma','👄 Харизма')}\n\n━━━━━━━━━━━━━━━━"
    )

def upgrade_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("+ 💪 Сила",        callback_data="tower_up_strength"),
        InlineKeyboardButton("+ 🎯 Ловкость",     callback_data="tower_up_agility"),
        InlineKeyboardButton("+ 🧠 Интеллект",    callback_data="tower_up_intellect"),
        InlineKeyboardButton("+ 🫀 Телосложение", callback_data="tower_up_constitution"),
        InlineKeyboardButton("+ 👄 Харизма",      callback_data="tower_up_charisma"),
        InlineKeyboardButton("🔙 Назад",          callback_data="tower_back"),
    )
    return markup

def bag_text(char):
    cls = CLASSES[char['class_key']]
    items = get_items(char)
    total = sum(items.values())
    if items:
        parts = []
        for key, count in items.items():
            cd = CONSUMABLES.get(key)
            if cd:
                n = f"{cd['emoji']} {cd['name']}"
                parts.append(f"{n} ×{count}" if count > 1 else n)
        items_str = "; ".join(parts)
    else:
        items_str = "Пусто"
    return (
        f"— – - 🎒 РЮКЗАК И СНАРЯЖЕНИЕ 🎒 - – —\n\n"
        f"Имя: *{safe(char['char_name'])}*\nКласс: {cls['emoji']} {cls['name']}\n"
        f"⭐ Уровень: *{char['level']}*\n\n💰 Монеты: *{char['coins']}*\n\n"
        f"━━━━━━━━━━━━━━━━\n\n📦 Экипировка:\n\n"
        f"🗡️ Оружие: {weapon_line_text(char)}\n"
        f"🛡️ Броня: {char['armor']}\n✨ Артефакт: {char['artifact']}\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"🎒 Содержимое рюкзака (мест {total}/20):\n\n{items_str}\n\n━━━━━━━━━━━━━━━━"
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
_creating = {}

def register_tower(bot):

    @bot.message_handler(commands=['tower'])
    def cmd_tower(message):
        uid = message.from_user.id
        uname = message.from_user.username
        char = get_tower_char(uid)
        if uname and char:
            save_username(uid, uname)
        if not char:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("👤 Создать", callback_data="tower_create"))
            bot.send_message(message.chat.id,
                "— – - 🏯 БАШНЯ ХАОСА 🏯 - – —\n\n❌ У тебя ещё не создан персонаж",
                reply_markup=markup)
        else:
            bot.send_message(message.chat.id, tower_main_text(char),
                reply_markup=tower_main_keyboard(char), parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_create')
    def cb_create(call):
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id,
            "– 👤 СОЗДАНИЕ ПЕРСОНАЖА –\n\nВыбери класс своего персонажа",
            reply_markup=class_select_keyboard())

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_class_'))
    def cb_class(call):
        bot.answer_callback_query(call.id)
        uid = call.from_user.id
        key = call.data.replace('tower_class_', '')
        if key not in CLASSES: return
        _creating[uid] = {'class': key, 'step': 'waiting_name'}
        cls = CLASSES[key]
        bot.send_message(call.message.chat.id,
            f"– 👤 СОЗДАНИЕ ПЕРСОНАЖА –\n\nКласс: {cls['emoji']} *{cls['name']}*\n\nДай имя своему персонажу:",
            parse_mode='Markdown')

    @bot.message_handler(func=lambda msg: msg.from_user.id in _creating
                         and _creating[msg.from_user.id].get('step') == 'waiting_name')
    def handle_name(message):
        uid = message.from_user.id
        name = message.text.strip()
        if len(name) < 2 or len(name) > 20:
            bot.send_message(message.chat.id, "❌ Имя от 2 до 20 символов. Попробуй ещё раз:"); return
        _creating[uid]['name'] = name
        _creating[uid]['step'] = 'confirm_name'
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Подтвердить", callback_data="tower_name_confirm"),
            InlineKeyboardButton("✍️ Изменить",    callback_data="tower_name_change"),
        )
        bot.send_message(message.chat.id, f"Имя персонажа: *{safe(name)}*",
            reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_name_confirm')
    def cb_name_confirm(call):
        bot.answer_callback_query(call.id)
        uid = call.from_user.id
        data = _creating.get(uid)
        if not data or data.get('step') != 'confirm_name':
            bot.send_message(call.message.chat.id, "❌ Начни создание заново через /tower"); return
        create_tower_char(uid, data['name'], data['class'])
        _creating.pop(uid, None)
        char = get_tower_char(uid)
        bot.send_message(call.message.chat.id, tower_main_text(char),
            reply_markup=tower_main_keyboard(char), parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_name_change')
    def cb_name_change(call):
        bot.answer_callback_query(call.id)
        uid = call.from_user.id
        if uid in _creating: _creating[uid]['step'] = 'waiting_name'
        bot.send_message(call.message.chat.id, "– 👤 СОЗДАНИЕ ПЕРСОНАЖА –\n\nВведи новое имя:")

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_back')
    def cb_back(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, tower_main_text(char),
            reply_markup=tower_main_keyboard(char), parse_mode='Markdown')

    # ── Улучшение статов ──────────────────────────────────────

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_upgrade')
    def cb_upgrade(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        bot.send_message(call.message.chat.id, upgrade_text(char),
            reply_markup=upgrade_keyboard(), parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_up_'))
    def cb_up_stat(call):
        bot.answer_callback_query(call.id)
        uid = call.from_user.id
        stat_key = call.data.replace('tower_up_', '')
        labels = {'strength':'💪 Сила','agility':'🎯 Ловкость','intellect':'🧠 Интеллект',
                  'constitution':'🫀 Телосложение','charisma':'👄 Харизма'}
        if stat_key not in labels: return
        char = get_tower_char(uid)
        if not char: return
        old = char[stat_key]
        if old >= 20:
            bot.send_message(call.message.chat.id,
                f"❌ *{labels[stat_key]}* уже на максимуме!", parse_mode='Markdown'); return
        cost = cp_cost(old)
        if char['stat_points'] < cost:
            bot.send_message(call.message.chat.id,
                f"❌ Нужно *{cost} ОХ*, у тебя *{char['stat_points']} ОХ*", parse_mode='Markdown'); return
        new_val = old + 1
        new_pts = char['stat_points'] - cost
        conn = get_conn(); c = conn.cursor()
        c.execute(f'UPDATE tower_chars SET {stat_key}=%s, stat_points=%s WHERE user_id=%s',
                  (new_val, new_pts, uid))
        conn.commit(); conn.close()
        char = get_tower_char(uid)
        bot.send_message(call.message.chat.id,
            f"– 🆙 *{labels[stat_key]} повышена!* –\n\n{old} ➡️ *{new_val}*\n\n🪙 ОХ: *{new_pts}*",
            parse_mode='Markdown')
        bot.send_message(call.message.chat.id, upgrade_text(char),
            reply_markup=upgrade_keyboard(), parse_mode='Markdown')

    # ── Рюкзак ────────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_bag')
    def cb_bag(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, bag_text(char),
            reply_markup=bag_keyboard(), parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_equip_menu')
    def cb_equip_menu(call):
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
        bot.send_message(call.message.chat.id, "Выбери слот экипировки:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_equip_weapon')
    def cb_equip_weapon(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        owned = get_owned_list(char, 'owned_weapons')
        current = char.get('weapon')
        markup = InlineKeyboardMarkup(row_width=1)
        for key in owned:
            w = WEAPONS.get(key)
            if not w: continue
            dmg = w['damage'](char)
            prefix = "✅ " if key == current else ""
            markup.add(InlineKeyboardButton(
                f"{prefix}{w['rarity']} {w['name']} | урон: {dmg}",
                callback_data=f"tower_do_equip_weapon_{key}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_equip_menu"))
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, "🗡️ Выбери оружие:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_equip_armor')
    def cb_equip_armor(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        owned = get_owned_list(char, 'owned_armors')
        current = char.get('armor')
        markup = InlineKeyboardMarkup(row_width=1)
        for name in owned:
            prefix = "✅ " if name == current else ""
            markup.add(InlineKeyboardButton(f"{prefix}{name}",
                callback_data=f"tower_do_equip_armor_{name[:40]}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_equip_menu"))
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, "🛡️ Выбери броню:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_equip_artifact')
    def cb_equip_artifact(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        owned = get_owned_list(char, 'owned_artifacts')
        current = char.get('artifact')
        markup = InlineKeyboardMarkup(row_width=1)
        for name in owned:
            prefix = "✅ " if name == current else ""
            markup.add(InlineKeyboardButton(f"{prefix}{name}",
                callback_data=f"tower_do_equip_artifact_{name[:40]}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_equip_menu"))
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, "🧪 Выбери артефакт:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_do_equip_weapon_'))
    def cb_do_equip_weapon(call):
        bot.answer_callback_query(call.id)
        uid = call.from_user.id
        wkey = call.data.replace('tower_do_equip_weapon_', '')
        if wkey not in WEAPONS: return
        conn = get_conn(); c = conn.cursor()
        c.execute('UPDATE tower_chars SET weapon=%s WHERE user_id=%s', (wkey, uid))
        conn.commit(); conn.close()
        char = get_tower_char(uid)
        w = WEAPONS[wkey]
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            f"✅ Оружие: *{w['name']}* *(урон: {w['damage'](char)})*", parse_mode='Markdown')
        bot.send_message(call.message.chat.id, bag_text(char),
            reply_markup=bag_keyboard(), parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_do_equip_armor_'))
    def cb_do_equip_armor(call):
        bot.answer_callback_query(call.id)
        uid = call.from_user.id
        name = call.data.replace('tower_do_equip_armor_', '')
        conn = get_conn(); c = conn.cursor()
        c.execute('UPDATE tower_chars SET armor=%s WHERE user_id=%s', (name, uid))
        conn.commit(); conn.close()
        char = get_tower_char(uid)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, f"✅ Броня: *{safe(name)}*", parse_mode='Markdown')
        bot.send_message(call.message.chat.id, bag_text(char),
            reply_markup=bag_keyboard(), parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_do_equip_artifact_'))
    def cb_do_equip_artifact(call):
        bot.answer_callback_query(call.id)
        uid = call.from_user.id
        name = call.data.replace('tower_do_equip_artifact_', '')
        conn = get_conn(); c = conn.cursor()
        c.execute('UPDATE tower_chars SET artifact=%s WHERE user_id=%s', (name, uid))
        conn.commit(); conn.close()
        char = get_tower_char(uid)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, f"✅ Артефакт: *{safe(name)}*", parse_mode='Markdown')
        bot.send_message(call.message.chat.id, bag_text(char),
            reply_markup=bag_keyboard(), parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_examine')
    def cb_examine(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        items = get_items(char)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        if not items:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_bag"))
            bot.send_message(call.message.chat.id, "— Содержимое рюкзака: —\n\nРюкзак пуст 😔", reply_markup=markup)
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for key, count in items.items():
            cd = CONSUMABLES.get(key)
            if cd:
                label = f"{cd['emoji']} {cd['name']}"
                if count > 1: label += f" ×{count}"
                markup.add(InlineKeyboardButton(label, callback_data=f"tower_item_info_{key}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_bag"))
        bot.send_message(call.message.chat.id, "— Содержимое рюкзака: —", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_item_info_'))
    def cb_item_info(call):
        bot.answer_callback_query(call.id)
        ikey = call.data.replace('tower_item_info_', '')
        char = get_tower_char(call.from_user.id)
        if not char: return
        items = get_items(char)
        count = items.get(ikey, 0)
        cd = CONSUMABLES.get(ikey)
        if not cd: return
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton(f"{cd['emoji']} Использовать", callback_data=f"tower_use_{ikey}"),
            InlineKeyboardButton("🔙 Назад", callback_data="tower_examine"),
        )
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            f"{cd['emoji']} *{cd['name']}*\nКоличество: *{count}*\n\n{cd['desc']}",
            reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_use_'))
    def cb_use_item(call):
        bot.answer_callback_query(call.id)
        ikey = call.data.replace('tower_use_', '')
        uid = call.from_user.id
        char = get_tower_char(uid)
        if not char: return
        items = get_items(char)
        if items.get(ikey, 0) <= 0:
            bot.send_message(call.message.chat.id, "❌ У тебя нет этого предмета!"); return
        cd = CONSUMABLES.get(ikey)
        if not cd: return
        usable = {'health_potion','big_health_potion','mana_potion','big_mana_potion','scroll_heal','scroll_mana'}
        if ikey not in usable:
            bot.send_message(call.message.chat.id,
                f"⚠️ *{cd['name']}* только в бою!", parse_mode='Markdown'); return
        import random
        mhp = calc_max_hp(char); mmp = calc_max_mp(char)
        nhp, nmp = char['hp'], char['mp']
        res = ""
        if ikey == 'health_potion':
            h = random.randint(25,50); nhp = min(mhp, nhp+h); res=f"❤️ +{h} HP ({nhp}/{mhp})"
        elif ikey == 'big_health_potion':
            h = random.randint(75,100); nhp = min(mhp, nhp+h); res=f"❤️ +{h} HP ({nhp}/{mhp})"
        elif ikey == 'mana_potion':
            m = random.randint(15,30); nmp = min(mmp, nmp+m); res=f"⚡ +{m} MP ({nmp}/{mmp})"
        elif ikey == 'big_mana_potion':
            m = random.randint(50,70); nmp = min(mmp, nmp+m); res=f"⚡ +{m} MP ({nmp}/{mmp})"
        elif ikey == 'scroll_heal':
            h = random.randint(30,50); nhp = min(mhp, nhp+h); res=f"❤️ +{h} HP ({nhp}/{mhp})"
        elif ikey == 'scroll_mana':
            m = random.randint(20,40); nmp = min(mmp, nmp+m); res=f"⚡ +{m} MP ({nmp}/{mmp})"
        items[ikey] -= 1
        if items[ikey] <= 0: del items[ikey]
        save_items(uid, items)
        conn = get_conn(); c = conn.cursor()
        c.execute('UPDATE tower_chars SET hp=%s, mp=%s WHERE user_id=%s', (nhp, nmp, uid))
        conn.commit(); conn.close()
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            f"✅ *{cd['emoji']} {cd['name']}*\n\n{res}", parse_mode='Markdown')

    # ── Заклинания ────────────────────────────────────────────

    def get_learned(char):
        try: return json.loads(char.get('learned_spells') or '[]')
        except: return []

    def get_slots(char):
        return [char.get('spell_slot_1'), char.get('spell_slot_2'), char.get('spell_slot_3')]

    def spells_text(char):
        cls = CLASSES[char['class_key']]
        slots = get_slots(char)
        learned = get_learned(char)
        slot_lines = []
        for i, key in enumerate(slots, 1):
            num = ['1️⃣','2️⃣','3️⃣'][i-1]
            if key and key in SPELLS:
                sp = SPELLS[key]
                slot_lines.append(f"{num} {sp['emoji']} {sp['name']}")
            else:
                slot_lines.append(f"{num} —")
        return (
            f"— – – – – 💫✨ ЗАКЛИНАНИЯ ✨💫 – – – – –\n\n"
            f"Имя: *{safe(char['char_name'])}*\nКласс: {cls['emoji']} {cls['name']}\n"
            f"⭐ Уровень: *{char['level']}*\n\n"
            f"⚡ Мана: *{char['mp']}/{calc_max_mp(char)}*\n\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"🎯 Активные заклинания ({sum(1 for s in slots if s)}/3):\n\n"
            f"{chr(10).join(slot_lines)}\n\n━━━━━━━━━━━━━━━━\n\n"
            f"📚 Изученные заклинания: *{len(learned)}*\n\nВыберите действие:"
        )

    def spells_kb():
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📜 Все заклинания", callback_data="tower_spells_all"),
            InlineKeyboardButton("🔄 Сменить слот",   callback_data="tower_spells_swap"),
            InlineKeyboardButton("🔙 Назад",          callback_data="tower_back"),
        )
        return markup

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_spells')
    def cb_spells(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char or char['class_key'] not in SPELL_CLASSES:
            bot.answer_callback_query(call.id, "❌ Только для магов!", show_alert=True); return
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, spells_text(char),
            reply_markup=spells_kb(), parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_spells_all')
    def cb_spells_all(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        learned = get_learned(char)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        if not learned:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_spells"))
            bot.send_message(call.message.chat.id, "📚 Нет изученных заклинаний.", reply_markup=markup); return
        markup = InlineKeyboardMarkup(row_width=1)
        for key in learned:
            sp = SPELLS.get(key)
            if sp:
                markup.add(InlineKeyboardButton(
                    f"{'⭐'*sp['level']} {sp['emoji']} {sp['name']} | ⚡{sp['mana']}",
                    callback_data=f"tower_spell_info_{key}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_spells"))
        bot.send_message(call.message.chat.id, "📚 *Все заклинания:*",
            reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_spell_info_'))
    def cb_spell_info(call):
        bot.answer_callback_query(call.id)
        skey = call.data.replace('tower_spell_info_', '')
        sp = SPELLS.get(skey)
        char = get_tower_char(call.from_user.id)
        if not sp or not char: return
        intel = char['intellect']
        dmg_text = f"\n💢 Урон: *{int(sp['damage'](intel))}*" if sp.get('damage') else ""
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_spells_all"))
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            f"{'⭐'*sp['level']} {sp['emoji']} *{sp['name']}*\n"
            f"Уровень: *{sp['level']}*\n⚡ Мана: *{sp['mana']}*{dmg_text}\n\n{sp['desc']}",
            reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_spells_swap')
    def cb_spells_swap(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        slots = get_slots(char)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        markup = InlineKeyboardMarkup(row_width=1)
        for i, key in enumerate(slots, 1):
            num = ['1️⃣','2️⃣','3️⃣'][i-1]
            if key and key in SPELLS:
                sp = SPELLS[key]
                label = f"{num} {sp['emoji']} {sp['name']}"
            else:
                label = f"{num} — (пусто)"
            markup.add(InlineKeyboardButton(label, callback_data=f"tower_pick_slot_{i}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_spells"))
        bot.send_message(call.message.chat.id, "Выбери слот для замены:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_pick_slot_'))
    def cb_pick_slot(call):
        bot.answer_callback_query(call.id)
        slot_num = call.data.replace('tower_pick_slot_', '')
        char = get_tower_char(call.from_user.id)
        if not char: return
        learned = get_learned(char)
        if not learned:
            bot.answer_callback_query(call.id, "❌ Нет изученных заклинаний!", show_alert=True); return
        slots = get_slots(char)
        current_in_slot = slots[int(slot_num)-1]
        # Занятые ДРУГИМИ слотами — скрываем
        used_in_other = {s for i, s in enumerate(slots) if str(i+1) != slot_num and s}
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        markup = InlineKeyboardMarkup(row_width=1)
        for key in learned:
            if key in used_in_other: continue  # уже стоит в другом слоте
            sp = SPELLS.get(key)
            if not sp: continue
            prefix = "✅ " if key == current_in_slot else ""
            markup.add(InlineKeyboardButton(
                f"{prefix}{sp['emoji']} {sp['name']} | ⭐{sp['level']} ⚡{sp['mana']}",
                callback_data=f"tower_set_slot_{slot_num}_{key}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_spells_swap"))
        bot.send_message(call.message.chat.id, f"Выбери заклинание для слота {slot_num}:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_set_slot_'))
    def cb_set_slot(call):
        bot.answer_callback_query(call.id)
        parts = call.data.replace('tower_set_slot_', '').split('_', 1)
        if len(parts) < 2: return
        slot_num, spell_key = parts[0], parts[1]
        if slot_num not in ('1','2','3') or spell_key not in SPELLS: return
        uid = call.from_user.id
        char = get_tower_char(uid)
        if not char: return
        # Финальная защита от дублирования
        slots = get_slots(char)
        for i, s in enumerate(slots):
            if str(i+1) != slot_num and s == spell_key:
                bot.answer_callback_query(call.id,
                    "❌ Это заклинание уже в другом слоте!", show_alert=True); return
        conn = get_conn(); c = conn.cursor()
        c.execute(f'UPDATE tower_chars SET spell_slot_{slot_num}=%s WHERE user_id=%s', (spell_key, uid))
        conn.commit(); conn.close()
        sp = SPELLS[spell_key]
        char = get_tower_char(uid)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            f"✅ Слот {slot_num} → *{sp['emoji']} {sp['name']}*", parse_mode='Markdown')
        bot.send_message(call.message.chat.id, spells_text(char),
            reply_markup=spells_kb(), parse_mode='Markdown')

    # ── Удаление ──────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_delete_ask')
    def cb_delete_ask(call):
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Да, удалить", callback_data="tower_delete_confirm"),
            InlineKeyboardButton("❌ Отмена",       callback_data="tower_delete_cancel"),
        )
        bot.send_message(call.message.chat.id,
            "⚠️ Удалить персонажа? Весь прогресс будет потерян!", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_delete_confirm')
    def cb_delete_confirm(call):
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
    def cb_delete_cancel(call):
        bot.answer_callback_query(call.id, "Отменено")

    # ── Заглушки ──────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda call: call.data in ['tower_start','tower_skills'])
    def cb_stub(call):
        labels = {
            'tower_start':   '⚔️ Режим прохождения башни будет добавлен скоро!',
            'tower_skills':  '📜 Система навыков будет добавлена скоро!',
        }
        bot.answer_callback_query(call.id, labels.get(call.data, '🔧 В разработке'), show_alert=True)

    # ── Рекорды ───────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_records')
    def cb_tower_records(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id

        # Сохраняем username вызывающего
        uname = call.from_user.username
        if uname:
            save_username(user_id, uname)

        rows = get_leaderboard(10)

        if not rows:
            bot.send_message(call.message.chat.id,
                "🏆 Рекордов пока нет. Будь первым!", parse_mode='Markdown')
            return

        medals = ['🥇','🥈','🥉']
        lines = ['— – ‐ 🏆 *РЕКОРДЫ* 🏆 ‐ – —\n']

        for i, (username, char_name, class_key, level, best_floor) in enumerate(rows, 1):
            cls = CLASSES.get(class_key, {})
            cls_emoji = cls.get('emoji', '❓')
            name_str = f"@{username}" if username else f"#{i}"
            medal = medals[i-1] if i <= 3 else f"{i}\\."
            safe_name = safe(char_name)
            lines.append(
                f"{medal} {name_str} — {cls_emoji} {safe_name} {level} — 🏯 {best_floor}"
            )

        bot.send_message(call.message.chat.id,
            "\n".join(lines), parse_mode='Markdown')
