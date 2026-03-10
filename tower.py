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

# ═══════════════════════════════════════════════════════════════
# ОРУЖИЯ
# ═══════════════════════════════════════════════════════════════

WEAPONS = {
    # ── Начальные (⚪) ─────────────────────────────────────────
    "sword_recruit": {
        "name": "Меч Новобранца", "rarity": "⚪", "rarity_name": "Начальный",
        "stat": "strength",
        "damage": lambda s,a,i: int(8 + s * 1.5),
        "damage_str": "8 + Сила×1.5",
        "effect": None,
    },
    "axe_battle_start": {
        "name": "Боевой Топор", "rarity": "⚪", "rarity_name": "Начальный",
        "stat": "strength",
        "damage": lambda s,a,i: int(9 + s * 1.6),
        "damage_str": "9 + Сила×1.6",
        "effect": ("weakness", 1, 0.20),
        "effect_desc": "20% шанс наложить ⛓️‍💥Слабость на 1 ход",
    },
    "dagger_assassin": {
        "name": "Кинжал Ассасина", "rarity": "⚪", "rarity_name": "Начальный",
        "stat": "agility",
        "damage": lambda s,a,i: int(7 + a * 1.6),
        "damage_str": "7 + Ловкость×1.6",
        "effect": ("bleed", 1, 0.10),
        "effect_desc": "10% шанс наложить 🩸Кровотечение на 1 ход",
    },
    "bow_ranger": {
        "name": "Лук Следопыта", "rarity": "⚪", "rarity_name": "Начальный",
        "stat": "agility",
        "damage": lambda s,a,i: int(8 + a * 1.6),
        "damage_str": "8 + Ловкость×1.6",
        "effect": ("double_hit", 0, 0.15),
        "effect_desc": "15% шанс двойного удара",
        "ammo": "arrows",
    },
    "staff_mage": {
        "name": "Посох Волшебника", "rarity": "⚪", "rarity_name": "Начальный",
        "stat": "intellect",
        "damage": lambda s,a,i: int(8 + i * 1.8),
        "damage_str": "8 + Интеллект×1.8",
        "effect": ("mp_regen", 0, 0.15),
        "effect_desc": "15% шанс получить +⚡[мод.Интеллекта] Маны",
    },
    "wand_warlock": {
        "name": "Жезл Колдуна", "rarity": "⚪", "rarity_name": "Начальный",
        "stat": "intellect",
        "damage": lambda s,a,i: int(8 + i * 1.8),
        "damage_str": "8 + Интеллект×1.8",
        "effect": ("poison", 1, 0.15),
        "effect_desc": "15% шанс наложить 1 ☠️Яд",
    },
    # ── Необычные (🟢) ─────────────────────────────────────────
    "iron_sword":       {"name": "Железный меч",        "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(8+s*2),   "damage_str": "8 + Сила×2"},
    "battle_axe":       {"name": "Боевой топор",         "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(9+s*2),   "damage_str": "9 + Сила×2"},
    "long_sword":       {"name": "Длинный меч",          "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(10+s*1.8), "damage_str": "10 + Сила×1.8"},
    "bone_dagger":      {"name": "Костяной кинжал",      "rarity": "🟢", "rarity_name": "Необычный", "stat": "agility",  "damage": lambda s,a,i: int(6+a*2),   "damage_str": "6 + Ловкость×2"},
    "short_bow":        {"name": "Короткий лук",         "rarity": "🟢", "rarity_name": "Необычный", "stat": "agility",  "damage": lambda s,a,i: int(7+a*2),   "damage_str": "7 + Ловкость×2", "ammo": "arrows"},
    "hunting_bow":      {"name": "Охотничий лук",        "rarity": "🟢", "rarity_name": "Необычный", "stat": "agility",  "damage": lambda s,a,i: int(8+a*2),   "damage_str": "8 + Ловкость×2", "ammo": "arrows"},
    "guard_spear":      {"name": "Копьё стража",         "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(9+s*1.9), "damage_str": "9 + Сила×1.9"},
    "battle_hammer":    {"name": "Боевой молот",         "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(11+s*1.7), "damage_str": "11 + Сила×1.7"},
    "iron_mace":        {"name": "Железная булава",      "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(9+s*1.8), "damage_str": "9 + Сила×1.8"},
    "throwing_dagger":  {"name": "Метательный кинжал",   "rarity": "🟢", "rarity_name": "Необычный", "stat": "agility",  "damage": lambda s,a,i: int(6+a*2.2), "damage_str": "6 + Ловкость×2.2"},
    "steel_blade":      {"name": "Стальной клинок",      "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(9+s*2),   "damage_str": "9 + Сила×2"},
    "smith_hammer":     {"name": "Кузнечный молот",      "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(10+s*1.8), "damage_str": "10 + Сила×1.8"},
    "long_spear":       {"name": "Длинное копьё",        "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(9+s*1.9), "damage_str": "9 + Сила×1.9"},
    "merc_saber":       {"name": "Сабля наёмника",       "rarity": "🟢", "rarity_name": "Необычный", "stat": "agility",  "damage": lambda s,a,i: int(8+a*2),   "damage_str": "8 + Ловкость×2"},
    "thief_dagger":     {"name": "Кинжал разбойника",    "rarity": "🟢", "rarity_name": "Необычный", "stat": "agility",  "damage": lambda s,a,i: int(7+a*2),   "damage_str": "7 + Ловкость×2"},
    "guard_crossbow":   {"name": "Арбалет стражника",    "rarity": "🟢", "rarity_name": "Необычный", "stat": "agility",  "damage": lambda s,a,i: int(10+a*1.8), "damage_str": "10 + Ловкость×1.8", "ammo": "bolts"},
    "apprentice_staff": {"name": "Лёгкий посох ученика", "rarity": "🟢", "rarity_name": "Необычный", "stat": "intellect","damage": lambda s,a,i: int(6+i*1.8), "damage_str": "6 + Интеллект×1.8"},
    "bone_staff":       {"name": "Костяной посох",       "rarity": "🟢", "rarity_name": "Необычный", "stat": "intellect","damage": lambda s,a,i: int(7+i*1.9), "damage_str": "7 + Интеллект×1.9"},
    "battle_wand":      {"name": "Боевой жезл",          "rarity": "🟢", "rarity_name": "Необычный", "stat": "intellect","damage": lambda s,a,i: int(7+i*2),   "damage_str": "7 + Интеллект×2"},
    "training_sword":   {"name": "Тренировочный меч",    "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(8+s*1.9), "damage_str": "8 + Сила×1.9"},
    "patrol_sword":     {"name": "Меч караула",          "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(9+s*2),   "damage_str": "9 + Сила×2"},
    "rusty_axe":        {"name": "Ржавый топор",         "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(9+s*2),   "damage_str": "9 + Сила×2"},
    "light_blade":      {"name": "Лёгкий клинок",        "rarity": "🟢", "rarity_name": "Необычный", "stat": "agility",  "damage": lambda s,a,i: int(8+a*2),   "damage_str": "8 + Ловкость×2"},
    "short_spear":      {"name": "Короткое копьё",       "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(8+s*1.9), "damage_str": "8 + Сила×1.9"},
    "hunt_crossbow":    {"name": "Охотничий арбалет",    "rarity": "🟢", "rarity_name": "Необычный", "stat": "agility",  "damage": lambda s,a,i: int(9+a*1.9), "damage_str": "9 + Ловкость×1.9", "ammo": "bolts"},
    "student_staff":    {"name": "Посох ученика",        "rarity": "🟢", "rarity_name": "Необычный", "stat": "intellect","damage": lambda s,a,i: int(7+i*1.9), "damage_str": "7 + Интеллект×1.9"},
    "old_wand":         {"name": "Старый жезл",          "rarity": "🟢", "rarity_name": "Необычный", "stat": "intellect","damage": lambda s,a,i: int(7+i*1.8), "damage_str": "7 + Интеллект×1.8"},
    "curved_dagger":    {"name": "Кривой кинжал",        "rarity": "🟢", "rarity_name": "Необычный", "stat": "agility",  "damage": lambda s,a,i: int(6+a*2),   "damage_str": "6 + Ловкость×2"},
    "sickle":           {"name": "Боевой серп",          "rarity": "🟢", "rarity_name": "Необычный", "stat": "agility",  "damage": lambda s,a,i: int(8+a*2),   "damage_str": "8 + Ловкость×2"},
    "soldier_sword":    {"name": "Солдатский меч",       "rarity": "🟢", "rarity_name": "Необычный", "stat": "strength", "damage": lambda s,a,i: int(9+s*2),   "damage_str": "9 + Сила×2"},
    # ── Редкие (🔵) ────────────────────────────────────────────
    "flaming_blade":    {"name": "🔥Пылающий клинок",      "rarity": "🔵", "rarity_name": "Редкий", "stat": "strength", "damage": lambda s,a,i: int(12+s*2),   "damage_str": "12 + Сила×2",       "effect": ("burn", 2, 1.0)},
    "ice_axe":          {"name": "❄️Ледяной топор",        "rarity": "🔵", "rarity_name": "Редкий", "stat": "strength", "damage": lambda s,a,i: int(13+s*1.9), "damage_str": "13 + Сила×1.9",     "effect": ("cold", 2, 1.0)},
    "lightning_blade":  {"name": "⚡Клинок молнии",        "rarity": "🔵", "rarity_name": "Редкий", "stat": "agility",  "damage": lambda s,a,i: int(11+a*2.1), "damage_str": "11 + Ловкость×2.1", "effect": ("shock", 1, 1.0)},
    "poison_dagger":    {"name": "☠️Отравленный кинжал",   "rarity": "🔵", "rarity_name": "Редкий", "stat": "agility",  "damage": lambda s,a,i: int(10+a*2.2), "damage_str": "10 + Ловкость×2.2", "effect": ("poison", 3, 1.0)},
    "blood_sickle":     {"name": "🩸Кровавый серп",        "rarity": "🔵", "rarity_name": "Редкий", "stat": "agility",  "damage": lambda s,a,i: int(12+a*2),   "damage_str": "12 + Ловкость×2",   "effect": ("bleed", 3, 1.0)},
    "merc_blade":       {"name": "⚔️Клинок наёмника",      "rarity": "🔵", "rarity_name": "Редкий", "stat": "strength", "damage": lambda s,a,i: int(13+s*2),   "damage_str": "13 + Сила×2"},
    "wind_bow":         {"name": "🏹Лук охотника ветра",   "rarity": "🔵", "rarity_name": "Редкий", "stat": "agility",  "damage": lambda s,a,i: int(11+a*2.1), "damage_str": "11 + Ловкость×2.1", "ammo": "arrows"},
    "storm_crossbow":   {"name": "⚡Арбалет бури",         "rarity": "🔵", "rarity_name": "Редкий", "stat": "agility",  "damage": lambda s,a,i: int(13+a*2),   "damage_str": "13 + Ловкость×2",   "ammo": "bolts", "effect": ("shock", 1, 1.0)},
    "ice_spear":        {"name": "🧊Копьё ледяного стража","rarity": "🔵", "rarity_name": "Редкий", "stat": "strength", "damage": lambda s,a,i: int(14+s*1.9), "damage_str": "14 + Сила×1.9",     "effect": ("cold", 2, 1.0)},
    "flame_hammer":     {"name": "🔥Боевой молот пламени", "rarity": "🔵", "rarity_name": "Редкий", "stat": "strength", "damage": lambda s,a,i: int(15+s*1.8), "damage_str": "15 + Сила×1.8",     "effect": ("burn", 2, 1.0)},
    "vortex_saber":     {"name": "🌪️Сабля вихря",          "rarity": "🔵", "rarity_name": "Редкий", "stat": "agility",  "damage": lambda s,a,i: int(12+a*2.1), "damage_str": "12 + Ловкость×2.1"},
    "dark_staff":       {"name": "💀Посох чёрной магии",   "rarity": "🔵", "rarity_name": "Редкий", "stat": "intellect","damage": lambda s,a,i: int(10+i*2),   "damage_str": "10 + Интеллект×2"},
    "dark_wand":        {"name": "🌑Жезл тёмных чар",      "rarity": "🔵", "rarity_name": "Редкий", "stat": "intellect","damage": lambda s,a,i: int(11+i*2),   "damage_str": "11 + Интеллект×2",  "effect": ("weakness", 2, 1.0)},
    "thunder_staff":    {"name": "⚡Посох грома",           "rarity": "🔵", "rarity_name": "Редкий", "stat": "intellect","damage": lambda s,a,i: int(12+i*2),   "damage_str": "12 + Интеллект×2",  "effect": ("shock", 1, 1.0)},
    "blizzard_staff":   {"name": "❄️Посох ледяной бури",   "rarity": "🔵", "rarity_name": "Редкий", "stat": "intellect","damage": lambda s,a,i: int(12+i*2),   "damage_str": "12 + Интеллект×2",  "effect": ("cold", 3, 1.0)},
    "rage_fire_staff":  {"name": "🔥Посох огненной ярости","rarity": "🔵", "rarity_name": "Редкий", "stat": "intellect","damage": lambda s,a,i: int(13+i*2),   "damage_str": "13 + Интеллект×2",  "effect": ("burn", 3, 1.0)},
    "plague_sword":     {"name": "☠️Клинок чумного рыцаря","rarity": "🔵", "rarity_name": "Редкий", "stat": "strength", "damage": lambda s,a,i: int(14+s*2),   "damage_str": "14 + Сила×2",       "effect": ("poison", 3, 1.0)},
    "cult_dagger":      {"name": "🩸Кинжал кровавого культа","rarity":"🔵","rarity_name": "Редкий", "stat": "agility",  "damage": lambda s,a,i: int(12+a*2.2), "damage_str": "12 + Ловкость×2.2", "effect": ("bleed", 3, 1.0)},
    "fortress_sword":   {"name": "⚔️Меч стража крепости",  "rarity": "🔵", "rarity_name": "Редкий", "stat": "strength", "damage": lambda s,a,i: int(14+s*2),   "damage_str": "14 + Сила×2"},
    "storm_blade":      {"name": "🌩️Клинок бури",          "rarity": "🔵", "rarity_name": "Редкий", "stat": "strength", "damage": lambda s,a,i: int(15+s*1.9), "damage_str": "15 + Сила×1.9",     "effect": ("shock", 2, 1.0)},
    # ── Эпические (🟣) ─────────────────────────────────────────
    "arctic_hammer":    {"name": "❄️Арктический Молот",       "rarity": "🟣", "rarity_name": "Эпический", "stat": "strength", "damage": lambda s,a,i: int(16+s*2),   "damage_str": "16 + Сила×2"},
    "flame_blade_epic": {"name": "🔥Пламенный Клинок",        "rarity": "🟣", "rarity_name": "Эпический", "stat": "strength", "damage": lambda s,a,i: int(17+s*2),   "damage_str": "17 + Сила×2"},
    "lightning_dagger": {"name": "⚡Молниеносный Кинжал",     "rarity": "🟣", "rarity_name": "Эпический", "stat": "agility",  "damage": lambda s,a,i: int(15+a*2),   "damage_str": "15 + Ловкость×2"},
    "poison_sickle":    {"name": "☠️Ядовитый Серп",           "rarity": "🟣", "rarity_name": "Эпический", "stat": "agility",  "damage": lambda s,a,i: int(16+a*2),   "damage_str": "16 + Ловкость×2"},
    "blood_blade":      {"name": "🩸Кровавый Клинок",         "rarity": "🟣", "rarity_name": "Эпический", "stat": "agility",  "damage": lambda s,a,i: int(17+a*2),   "damage_str": "17 + Ловкость×2"},
    "light_warrior":    {"name": "⚔️Клинок Воина Света",      "rarity": "🟣", "rarity_name": "Эпический", "stat": "strength", "damage": lambda s,a,i: int(18+s*2),   "damage_str": "18 + Сила×2"},
    "shadow_bow":       {"name": "🏹Лук Теней",               "rarity": "🟣", "rarity_name": "Эпический", "stat": "agility",  "damage": lambda s,a,i: int(16+a*2),   "damage_str": "16 + Ловкость×2", "ammo": "arrows"},
    "storm_crossbow_e": {"name": "⚡Арбалет Грозы",           "rarity": "🟣", "rarity_name": "Эпический", "stat": "agility",  "damage": lambda s,a,i: int(18+a*2),   "damage_str": "18 + Ловкость×2", "ammo": "bolts"},
    "ice_staff_epic":   {"name": "🧊Ледяной Посох",           "rarity": "🟣", "rarity_name": "Эпический", "stat": "intellect","damage": lambda s,a,i: int(16+i*2),   "damage_str": "16 + Интеллект×2"},
    "fire_will_staff":  {"name": "🔥Посох Огненной Воли",     "rarity": "🟣", "rarity_name": "Эпический", "stat": "intellect","damage": lambda s,a,i: int(17+i*2),   "damage_str": "17 + Интеллект×2"},
    "lightning_staff":  {"name": "⚡Посох Молниеносной Бури",  "rarity": "🟣", "rarity_name": "Эпический", "stat": "intellect","damage": lambda s,a,i: int(18+i*2),   "damage_str": "18 + Интеллект×2"},
    "poison_dark_staff":{"name": "☠️Посох Ядовитой Тьмы",     "rarity": "🟣", "rarity_name": "Эпический", "stat": "intellect","damage": lambda s,a,i: int(17+i*2),   "damage_str": "17 + Интеллект×2"},
    # ── Легендарные (🟠) ───────────────────────────────────────
    "fire_fang":        {"name": "🔥Клинок Огненного Клыка", "rarity": "🟠", "rarity_name": "Легендарный", "stat": "strength", "damage": lambda s,a,i: int(25+s*2),   "damage_str": "25 + Сила×2",      "effect": ("double_hit", 0, 1.0)},
    "ice_fury":         {"name": "❄️Ледяная Ярость",          "rarity": "🟠", "rarity_name": "Легендарный", "stat": "strength", "damage": lambda s,a,i: int(24+s*2),   "damage_str": "24 + Сила×2",      "effect": ("cold", 3, 1.0)},
    "lightning_charge": {"name": "⚡Молниеносный Разряд",      "rarity": "🟠", "rarity_name": "Легендарный", "stat": "agility",  "damage": lambda s,a,i: int(23+a*2),   "damage_str": "23 + Ловкость×2",  "effect": ("shock", 1, 1.0)},
    "plague_blade":     {"name": "☠️Клинок Чумы",             "rarity": "🟠", "rarity_name": "Легендарный", "stat": "agility",  "damage": lambda s,a,i: int(24+a*2),   "damage_str": "24 + Ловкость×2",  "effect": ("poison", 4, 1.0)},
    "blood_fury":       {"name": "🩸Кровавая Ярость",         "rarity": "🟠", "rarity_name": "Легендарный", "stat": "agility",  "damage": lambda s,a,i: int(25+a*2),   "damage_str": "25 + Ловкость×2",  "effect": ("bleed", 4, 1.0)},
    "lightbringer":     {"name": "⚔️Меч Светоносца",          "rarity": "🟠", "rarity_name": "Легендарный", "stat": "strength", "damage": lambda s,a,i: int(26+s*2),   "damage_str": "26 + Сила×2",      "effect": ("armor_pierce", 0, 1.0)},
    "blizzard_staff_l": {"name": "🧊Посох Ледяной Бури",      "rarity": "🟠", "rarity_name": "Легендарный", "stat": "intellect","damage": lambda s,a,i: int(25+i*2),   "damage_str": "25 + Интеллект×2", "effect": ("cold_shock", 0, 1.0)},
}

STARTING_WEAPONS = {
    "warrior":   "sword_recruit",
    "barbarian": "axe_battle_start",
    "assassin":  "dagger_assassin",
    "ranger":    "bow_ranger",
    "mage":      "staff_mage",
    "warlock":   "wand_warlock",
}

def calc_weapon_damage(weapon_key, char):
    """Считает текущий урон оружия на основе характеристик персонажа"""
    w = WEAPONS.get(weapon_key)
    if not w or not w.get("damage"):
        return 0
    s = char.get("strength", 0)
    a = char.get("agility", 0)
    i = char.get("intellect", 0)
    return w["damage"](s, a, i)

def weapon_info_text(weapon_key, char):
    """Текст карточки оружия с рассчитанным уроном"""
    w = WEAPONS.get(weapon_key)
    if not w:
        return "❌ Оружие не найдено"
    dmg = calc_weapon_damage(weapon_key, char)
    effect_line = ""
    if w.get("effect_desc"):
        effect_line = f"\n✨ Эффект: {w['effect_desc']}"
    elif w.get("effect"):
        eff_key = w["effect"][0]
        effect_line = f"\n✨ Эффект: есть"
    ammo_line = ""
    if w.get("ammo"):
        ammo_name = "стрелу" if w["ammo"] == "arrows" else "болт"
        ammo_line = f"\n🏹 Расход: 1 {ammo_name} за выстрел"
    stat_icons = {"strength": "💪 Сила", "agility": "🎯 Ловкость", "intellect": "🧠 Интеллект"}
    return (
        f"{w['rarity']} *{w['name']}*\n"
        f"Редкость: {w['rarity']} {w['rarity_name']}\n"
        f"Характеристика: {stat_icons.get(w['stat'], w['stat'])}\n\n"
        f"💢 Урон: *{dmg}* ({w['damage_str']}){effect_line}{ammo_line}"
    )

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

def create_tower_char(user_id, char_name, class_key):
    cls = CLASSES[class_key]
    stats = cls["stats"]
    max_hp = cls["base_hp"] + stats["constitution"] * 1 * cls["k1"]
    max_mp = cls["base_mp"] + stats["intellect"] * 1 * cls["k2"]

    # Начальное оружие
    start_weapon_key = STARTING_WEAPONS.get(class_key, "sword_recruit")
    start_weapon_data = WEAPONS.get(start_weapon_key, {})
    start_weapon_name = start_weapon_data.get("name", "Голые кулаки")
    owned_weapons_json = json.dumps([start_weapon_name])

    # Начальные предметы
    starting_items = json.dumps(STARTING_ITEMS.get(class_key, {}))

    # Начальные заклинания
    start_spells = STARTING_SPELLS.get(class_key, [])
    learned_json = json.dumps(start_spells)
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
        start_weapon_name,
        starting_items, owned_weapons_json,
        learned_json, slot1, slot2
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

    # ── Заклинания ────────────────────────────────────────────
    def get_learned_spells(char):
        try: return json.loads(char.get('learned_spells') or '[]')
        except: return []

    def get_active_slots(char):
        return {char.get(f'spell_slot_{i}') for i in [1,2,3]} - {None}

    def spells_text(char):
        cls = CLASSES[char['class_key']]
        max_mp = calc_max_mp(char)
        learned = get_learned_spells(char)
        slots = []
        for i, slot in enumerate(['spell_slot_1','spell_slot_2','spell_slot_3'], 1):
            key = char.get(slot)
            num = ['1️⃣','2️⃣','3️⃣'][i-1]
            if key and key in SPELLS:
                sp = SPELLS[key]
                slots.append(f"{num} {sp['emoji']} {sp['name']}")
            else:
                slots.append(f"{num} —")
        active_count = sum(1 for s in ['spell_slot_1','spell_slot_2','spell_slot_3'] if char.get(s))
        return (
            f"— – – – – 💫✨ ЗАКЛИНАНИЯ ✨💫 – – – – –\n\n"
            f"Имя: *{safe(char['char_name'])}*\n"
            f"Класс: {cls['emoji']} {cls['name']}\n"
            f"⭐ Уровень: *{char['level']}*\n\n"
            f"⚡ Мана: *{char['mp']}/{max_mp}*\n\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"🎯 Активные заклинания ({active_count}/3):\n\n"
            f"{chr(10).join(slots)}\n\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"📚 Изученные заклинания: *{len(learned)}*\n\n"
            f"Выберите действие:"
        )

    def spells_main_keyboard():
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📜 Все заклинания", callback_data="tower_spells_all"),
            InlineKeyboardButton("🔄 Сменить слот",   callback_data="tower_spells_swap"),
            InlineKeyboardButton("🔙 Назад",          callback_data="tower_back"),
        )
        return markup

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_spells')
    def cb_tower_spells(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char or char['class_key'] not in SPELL_CLASSES:
            bot.answer_callback_query(call.id, "❌ Только для магов!", show_alert=True)
            return
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            spells_text(char), reply_markup=spells_main_keyboard(), parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_spells_all')
    def cb_tower_spells_all(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        learned = get_learned_spells(char)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        if not learned:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_spells"))
            bot.send_message(call.message.chat.id, "📚 Нет изученных заклинаний.", reply_markup=markup)
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for key in learned:
            sp = SPELLS.get(key)
            if sp:
                markup.add(InlineKeyboardButton(
                    f"{'⭐'*sp['level']} {sp['emoji']} {sp['name']} | ⚡{sp['mana']}",
                    callback_data=f"tower_spell_info_{key}"
                ))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_spells"))
        bot.send_message(call.message.chat.id, "📚 *Все заклинания:*", reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_spell_info_'))
    def cb_tower_spell_info(call):
        bot.answer_callback_query(call.id)
        spell_key = call.data.replace('tower_spell_info_', '')
        sp = SPELLS.get(spell_key)
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
            f"Уровень заклинания: *{sp['level']}*\n"
            f"⚡ Мана: *{sp['mana']}*{dmg_text}\n\n"
            f"{sp['desc']}",
            reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data == 'tower_spells_swap')
    def cb_tower_spells_swap(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        if not char: return
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        markup = InlineKeyboardMarkup(row_width=1)
        for i, slot in enumerate(['spell_slot_1','spell_slot_2','spell_slot_3'], 1):
            key = char.get(slot)
            label = f"{'1️⃣2️⃣3️⃣'[i-1]} "
            if key and key in SPELLS:
                sp = SPELLS[key]
                label += f"{sp['emoji']} {sp['name']}"
            else:
                label += "— (пусто)"
            markup.add(InlineKeyboardButton(label, callback_data=f"tower_pick_slot_{i}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_spells"))
        bot.send_message(call.message.chat.id, "Выбери слот для замены:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_pick_slot_'))
    def cb_tower_pick_slot(call):
        bot.answer_callback_query(call.id)
        slot_num = call.data.replace('tower_pick_slot_', '')
        char = get_tower_char(call.from_user.id)
        if not char: return
        learned = get_learned_spells(char)
        if not learned:
            bot.answer_callback_query(call.id, "❌ Нет изученных заклинаний!", show_alert=True)
            return
        # Текущее заклинание в выбранном слоте (чтобы не блокировать его же)
        current_in_slot = char.get(f'spell_slot_{slot_num}')
        # Заклинания занятые в ДРУГИХ слотах
        other_slots = {char.get(f'spell_slot_{i}') for i in [1,2,3] if str(i) != slot_num} - {None}
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        markup = InlineKeyboardMarkup(row_width=1)
        added = 0
        for key in learned:
            sp = SPELLS.get(key)
            if not sp: continue
            if key in other_slots:
                # Уже стоит в другом слоте — пропускаем
                continue
            prefix = "✅ " if key == current_in_slot else ""
            markup.add(InlineKeyboardButton(
                f"{prefix}{sp['emoji']} {sp['name']} | ⭐{sp['level']} ⚡{sp['mana']}",
                callback_data=f"tower_setslot_{slot_num}_{key}"
            ))
            added += 1
        if added == 0:
            bot.send_message(call.message.chat.id,
                "❌ Все заклинания уже заняты в других слотах.",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🔙 Назад", callback_data="tower_spells_swap")))
            return
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tower_spells_swap"))
        bot.send_message(call.message.chat.id,
            f"Выбери заклинание для слота {slot_num}:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tower_setslot_'))
    def cb_tower_setslot(call):
        bot.answer_callback_query(call.id)
        parts = call.data.replace('tower_setslot_', '').split('_', 1)
        if len(parts) < 2: return
        slot_num, spell_key = parts[0], parts[1]
        if slot_num not in ('1','2','3') or spell_key not in SPELLS: return
        user_id = call.from_user.id
        char = get_tower_char(user_id)
        if not char: return
        # Финальная проверка: не стоит ли это заклинание в другом слоте
        other_slots = {char.get(f'spell_slot_{i}') for i in [1,2,3] if str(i) != slot_num} - {None}
        if spell_key in other_slots:
            bot.answer_callback_query(call.id, "❌ Это заклинание уже стоит в другом слоте!", show_alert=True)
            return
        col = f"spell_slot_{slot_num}"
        conn = get_conn()
        c = conn.cursor()
        c.execute(f'UPDATE tower_chars SET {col}=%s WHERE user_id=%s', (spell_key, user_id))
        conn.commit()
        conn.close()
        sp = SPELLS[spell_key]
        char = get_tower_char(user_id)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id,
            f"✅ Слот {slot_num} → *{sp['emoji']} {sp['name']}*", parse_mode='Markdown')
        bot.send_message(call.message.chat.id,
            spells_text(char), reply_markup=spells_main_keyboard(), parse_mode='Markdown')

    # ── Заглушки ──────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data in [
        'tower_start', 'tower_skills', 'tower_records'
    ])
    def cb_tower_stub(call):
        labels = {
            'tower_start':   '⚔️ Режим прохождения башни будет добавлен скоро!',
            'tower_skills':  '📜 Система навыков будет добавлена скоро!',
            'tower_records': '🏆 Рекорды будут добавлены скоро!',
            'tower_spells':  '💫 Система заклинаний будет добавлена скоро!',
        }
        bot.answer_callback_query(call.id, labels.get(call.data, '🔧 В разработке'), show_alert=True)
