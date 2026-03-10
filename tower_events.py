import random
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from tower import (
    get_conn, get_tower_char, calc_max_hp, calc_max_mp,
    CONSUMABLES, get_items, save_items, get_mod, safe, WEAPONS
)
from tower_battle import (
    get_battle, save_battle, delete_battle,
    update_char_hp_mp, spawn_enemy, roll_enemy_action,
    send_battle, ENEMIES
)

# ═══════════════════════════════════════════════════════════════
# СИСТЕМА ПРОВЕРОК
# ═══════════════════════════════════════════════════════════════
# Бросок: d20 + модификатор_характеристики >= DC → успех
# Игрок не видит DC и результат броска

STAT_KEY_MAP = {
    "intellect":    "intellect",
    "charisma":     "charisma",
    "agility":      "agility",
    "strength":     "strength",
    "constitution": "constitution",
    "speed":        "speed",
}

def roll_check(char, stat):
    """Возвращает (бросок_итого, модификатор)"""
    val = char.get(STAT_KEY_MAP.get(stat, stat), 10)
    mod = get_mod(val)
    roll = random.randint(1, 20)
    return roll + mod, mod

def check(char, stat, dc):
    """True = успех"""
    total, _ = roll_check(char, stat)
    return total >= dc

# ═══════════════════════════════════════════════════════════════
# СПИСОК СОБЫТИЙ (40 штук)
# ═══════════════════════════════════════════════════════════════
# Структура choice: id, label, emoji, stat (None = без проверки), dc

EVENTS = [
    # ── 1-20: основные ──────────────────────────────────────────
    {
        "id": "e01",
        "text": (
            "🧒 По коридору бежит *плачущий мальчик*:\n"
            "_«Потерял маму, помоги найти!»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "help",   "label": "🔍 Помочь",                    "stat": "intellect", "dc": 10},
            {"id": "guard",  "label": "👮 Отнести к стражнику",       "stat": "charisma",  "dc": 11},
            {"id": "ignore", "label": "🚶 Пройти мимо",               "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e02",
        "text": (
            "🧓 У входа в зал стоит *попрошайка* с бархатным мешочком:\n"
            "_«Помоги бедному старцу»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "give",    "label": "💰 Дать 10 монет",             "stat": None,        "dc": None},
            {"id": "bluff",   "label": "👄 Прикинуться богачом",       "stat": "charisma",  "dc": 12},
            {"id": "steal",   "label": "🎯 Взять мешочек тихо",       "stat": "agility",   "dc": 13},
        ]
    },
    {
        "id": "e03",
        "text": (
            "📦 *Сундук в нише* — заперт на древний замок.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "pick",    "label": "🎯 Взломать замок",            "stat": "agility",   "dc": 12},
            {"id": "smash",   "label": "💪 Разбить силой",             "stat": "strength",  "dc": 14},
            {"id": "study",   "label": "🧠 Разведать хитростью",       "stat": "intellect", "dc": 11},
        ]
    },
    {
        "id": "e04",
        "text": (
            "🛒 *Торговец редкостями* предлагает рискованную сделку.\n"
            "_«30 монет за нечто особенное»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "buy",     "label": "💰 Купить за 30 монет",        "stat": None,        "dc": None},
            {"id": "haggle",  "label": "👄 Поторговаться",             "stat": "charisma",  "dc": 13},
            {"id": "leave",   "label": "🚶 Уйти",                      "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e05",
        "text": (
            "🔴 На полу *странный флакон* — красный свет изнутри, странный запах.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "drink",   "label": "🧪 Выпить",                    "stat": "intellect", "dc": 12},
            {"id": "toss",    "label": "🗑️ Выбросить",                 "stat": None,        "dc": None},
            {"id": "take",    "label": "🎒 Забрать в рюкзак",          "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e06",
        "text": (
            "👻 В проходе слышны *шёпоты* — призрак просит книгу.\n"
            "_«Верни то, что принадлежит мне...»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "deceive", "label": "👄 Обмануть призрака",         "stat": "charisma",  "dc": 13},
            {"id": "fight",   "label": "⚔️ Сразиться",                 "stat": None,        "dc": None},
            {"id": "ignore",  "label": "🚶 Пройти мимо",               "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e07",
        "text": (
            "📜 Найден *свиток с загадкой*:\n"
            "_«Я всегда бегу, но не устаю. Что я?»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "answer",  "label": "🧠 Ответить на загадку",       "stat": "intellect", "dc": 13},
            {"id": "burn",    "label": "🔥 Сжечь свиток",              "stat": None,        "dc": None},
            {"id": "sell",    "label": "💰 Продать свиток",             "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e08",
        "text": (
            "⚠️ *Ловушка!* — пол начинает осыпаться под ногами.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "jump",    "label": "🎯 Быстро прыгнуть",           "stat": "agility",   "dc": 12},
            {"id": "hold",    "label": "💪 Удержаться руками",         "stat": "strength",  "dc": 13},
            {"id": "hide",    "label": "🧠 Найти обходной путь",       "stat": "intellect", "dc": 14},
        ]
    },
    {
        "id": "e09",
        "text": (
            "🐾 В коридоре раскидано мясо — рядом *голодный зверь* рычит.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "feed",    "label": "👄 Отдать мясо",               "stat": "charisma",  "dc": 11},
            {"id": "run",     "label": "🏃 Убежать",                   "stat": "speed",     "dc": 12},
            {"id": "fight",   "label": "⚔️ Сразиться",                 "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e10",
        "text": (
            "🪣 *Старый колодец* — внизу что-то светится.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "look",    "label": "🧠 Нагнуться и посмотреть",    "stat": "intellect", "dc": 11},
            {"id": "rope",    "label": "💪 Спустить верёвку",          "stat": "strength",  "dc": 12},
            {"id": "call",    "label": "👄 Позвать на помощь",         "stat": "charisma",  "dc": 13},
        ]
    },
    {
        "id": "e11",
        "text": (
            "🐑 На стене *рисунок пастуха* с загадкой:\n"
            "_«Угадаешь — получишь пищу»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "solve",   "label": "🧠 Решить загадку",            "stat": "intellect", "dc": 11},
            {"id": "force",   "label": "💪 Разрушить стену",           "stat": "strength",  "dc": 14},
            {"id": "ignore",  "label": "🚶 Пройти мимо",               "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e12",
        "text": (
            "🎸 При входе в зал *уличный музыкант* просит слушателя.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "listen",  "label": "👄 Послушать",                 "stat": "charisma",  "dc": 10},
            {"id": "coin",    "label": "💰 Подать монету",             "stat": None,        "dc": None},
            {"id": "leave",   "label": "🚶 Уйти",                      "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e13",
        "text": (
            "🍲 Ты видишь *старую печку с едой*.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "eat",     "label": "🫀 Поесть",                    "stat": "constitution", "dc": 8},
            {"id": "check",   "label": "🧠 Осмотреться вокруг",       "stat": "intellect", "dc": 12},
            {"id": "take",    "label": "🎯 Забрать продукты с собой",  "stat": "agility",   "dc": 11},
        ]
    },
    {
        "id": "e14",
        "text": (
            "🪨 Рядом табличка: _«Проверь силу — брось камень»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "throw",   "label": "💪 Бросить камень",            "stat": "strength",  "dc": 13},
            {"id": "fake",    "label": "🎯 Подделать результат",       "stat": "agility",   "dc": 12},
            {"id": "pass",    "label": "🚶 Пройти мимо",               "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e15",
        "text": (
            "🧙 *Торговец заклинаниями* даёт викторину.\n"
            "_«Ответишь — получишь свиток бесплатно»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "answer",  "label": "🧠 Ответить",                  "stat": "intellect", "dc": 13},
            {"id": "bribe",   "label": "👄 Подкупить",                 "stat": "charisma",  "dc": 12},
            {"id": "buy",     "label": "💰 Купить наугад (25м)",       "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e16",
        "text": (
            "🔮 На полу *бьётся хрустальный шар* — внутри пульсирует свет.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "grab",    "label": "🎯 Схватить шар",              "stat": "agility",   "dc": 13},
            {"id": "smash",   "label": "💪 Разбить",                   "stat": "strength",  "dc": 11},
            {"id": "study",   "label": "🧠 Изучить",                   "stat": "intellect", "dc": 14},
        ]
    },
    {
        "id": "e17",
        "text": (
            "🗣️ Ты натыкаешься на *двух путников*, спорящих о дороге.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "calm",    "label": "👄 Умиротворить",              "stat": "charisma",  "dc": 12},
            {"id": "bribe",   "label": "💰 Подкупить (10м)",           "stat": None,        "dc": None},
            {"id": "argue",   "label": "🧠 Присоединиться к спору",    "stat": "intellect", "dc": 13},
        ]
    },
    {
        "id": "e18",
        "text": (
            "🌑 В тёмной комнате *слышится плач и шорохи*.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "go",      "label": "🎯 Пойти на звук",             "stat": "agility",   "dc": 12},
            {"id": "shout",   "label": "👄 Покричать в ответ",         "stat": "charisma",  "dc": 11},
            {"id": "retreat", "label": "🚶 Отступить",                 "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e19",
        "text": (
            "🗺️ Надпись на стене:\n"
            "_«Отдай монету — получишь карту»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "pay",     "label": "💰 Отдать 15 монет",           "stat": None,        "dc": None},
            {"id": "steal",   "label": "🎯 Украсть карту",             "stat": "agility",   "dc": 13},
            {"id": "ask",     "label": "👄 Поторговаться",             "stat": "charisma",  "dc": 11},
        ]
    },
    {
        "id": "e20",
        "text": (
            "🧟 *Старый колдун* предлагает сделку:\n"
            "_«Пожертвуй частью HP ради силы на час»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "agree",   "label": "🫀 Согласиться",               "stat": "constitution", "dc": 10},
            {"id": "refuse",  "label": "🚶 Отказаться",                "stat": None,        "dc": None},
            {"id": "trick",   "label": "👄 Попытаться перехитрить",    "stat": "charisma",  "dc": 14},
        ]
    },
    # ── 21-40: дополнительные ───────────────────────────────────
    {
        "id": "e21",
        "text": (
            "🔒 В углу *старый сундук* с потайным замком.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "pick",    "label": "🎯 Взломать замок",            "stat": "agility",   "dc": 12},
            {"id": "smash",   "label": "💪 Разбить",                   "stat": "strength",  "dc": 13},
            {"id": "ignore",  "label": "🚶 Пройти мимо",               "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e22",
        "text": (
            "✨ На полу лежит *монета с магическим сиянием*.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "take",    "label": "🎯 Взять монету",              "stat": "agility",   "dc": 11},
            {"id": "pass",    "label": "🚶 Пройти мимо",               "stat": None,        "dc": None},
            {"id": "study",   "label": "🧠 Исследовать",               "stat": "intellect", "dc": 12},
        ]
    },
    {
        "id": "e23",
        "text": (
            "🔊 Из *тёмного коридора* слышен странный звук.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "check",   "label": "🎯 Пойти проверить",           "stat": "agility",   "dc": 12},
            {"id": "ignore",  "label": "🚶 Игнорировать",              "stat": None,        "dc": None},
            {"id": "shout",   "label": "👄 Прокричать",                "stat": "charisma",  "dc": 11},
        ]
    },
    {
        "id": "e24",
        "text": (
            "📝 На стене надпись:\n"
            "_«Кто решит загадку — получит награду»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "solve",   "label": "🧠 Решить загадку",            "stat": "intellect", "dc": 13},
            {"id": "pass",    "label": "🚶 Пройти мимо",               "stat": None,        "dc": None},
            {"id": "break",   "label": "💪 Разрушить стену",           "stat": "strength",  "dc": 14},
        ]
    },
    {
        "id": "e25",
        "text": (
            "🛡️ Перед тобой *глухой страж* с ключом от комнаты.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "bribe",   "label": "👄 Подкупить",                 "stat": "charisma",  "dc": 12},
            {"id": "fight",   "label": "⚔️ Сразиться",                 "stat": None,        "dc": None},
            {"id": "sneak",   "label": "🎯 Обойти стража",             "stat": "agility",   "dc": 13},
        ]
    },
    {
        "id": "e26",
        "text": (
            "⚗️ Ты находишь *сундук с зельями*.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "grab",    "label": "🎯 Взять зелье",               "stat": "agility",   "dc": 11},
            {"id": "careful", "label": "🧠 Открыть осторожно",         "stat": "intellect", "dc": 12},
            {"id": "ignore",  "label": "🚶 Игнорировать",              "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e27",
        "text": (
            "🌑 *Тень движется* вдоль стены. Голос шепчет:\n"
            "_«Помоги мне...»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "help",    "label": "👄 Помочь тени",               "stat": "charisma",  "dc": 12},
            {"id": "ignore",  "label": "🚶 Игнорировать",              "stat": None,        "dc": None},
            {"id": "fight",   "label": "⚔️ Сразиться с тенью",        "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e28",
        "text": (
            "🧪 *Старый алхимик* предлагает обмен: зелье за золото.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "buy",     "label": "💰 Купить за 20 монет",        "stat": None,        "dc": None},
            {"id": "haggle",  "label": "👄 Попытаться договориться",   "stat": "charisma",  "dc": 12},
            {"id": "refuse",  "label": "🚶 Отказаться",                "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e29",
        "text": (
            "💎 Ты натыкаешься на *магический кристалл*, пульсирующий синим.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "take",    "label": "🎯 Взять кристалл",            "stat": "agility",   "dc": 11},
            {"id": "study",   "label": "🧠 Исследовать",               "stat": "intellect", "dc": 13},
            {"id": "ignore",  "label": "🚶 Пройти мимо",               "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e30",
        "text": (
            "📜 На полу лежит *свиток с неизвестным заклинанием*.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "use",     "label": "🧠 Использовать",              "stat": "intellect", "dc": 13},
            {"id": "sell",    "label": "👄 Продать",                   "stat": "charisma",  "dc": 10},
            {"id": "leave",   "label": "🚶 Оставить",                  "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e31",
        "text": (
            "🕳️ Перед тобой *небольшая пропасть*.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "jump",    "label": "🏃 Прыгнуть",                  "stat": "speed",     "dc": 12},
            {"id": "rope",    "label": "💪 Спуститься на верёвке",     "stat": "strength",  "dc": 11},
            {"id": "detour",  "label": "🎯 Найти обход",               "stat": "agility",   "dc": 13},
        ]
    },
    {
        "id": "e32",
        "text": (
            "🗡️ Ты встречаешь *торговца оружием*.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "buy",     "label": "💰 Купить за 25 монет",        "stat": None,        "dc": None},
            {"id": "check",   "label": "🧠 Проверить качество",        "stat": "intellect", "dc": 12},
            {"id": "steal",   "label": "🎯 Попытаться украсть",        "stat": "agility",   "dc": 14},
        ]
    },
    {
        "id": "e33",
        "text": (
            "🚪 В комнате *три двери*:\n"
            "🔴 Красная, 🔵 Синяя, 🟢 Зелёная.\n\n"
            "Какую выбираешь?"
        ),
        "choices": [
            {"id": "red",     "label": "🔴 Красная дверь",             "stat": "intellect", "dc": 13},
            {"id": "blue",    "label": "🔵 Синяя дверь",               "stat": "charisma",  "dc": 12},
            {"id": "green",   "label": "🟢 Зелёная дверь",             "stat": "agility",   "dc": 11},
        ]
    },
    {
        "id": "e34",
        "text": (
            "🌀 *Магическая дверь* с рунами — пульсирует энергией.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "decode",  "label": "🧠 Разгадать руны",            "stat": "intellect", "dc": 14},
            {"id": "break",   "label": "💪 Разрушить",                 "stat": "strength",  "dc": 13},
            {"id": "bypass",  "label": "🚶 Обойти",                    "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e35",
        "text": (
            "😈 *Маленький демон* предлагает сыграть на монеты.\n"
            "_«Выиграешь — возьмёшь вдвое больше»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "play",    "label": "👄 Сыграть",                   "stat": "charisma",  "dc": 12},
            {"id": "refuse",  "label": "🚶 Отказаться",                "stat": None,        "dc": None},
            {"id": "cheat",   "label": "🧠 Попытаться обмануть",       "stat": "intellect", "dc": 14},
        ]
    },
    {
        "id": "e36",
        "text": (
            "💧 На полу *скользкая жидкость*, из которой доносится шорох.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "careful", "label": "🎯 Перейти осторожно",         "stat": "agility",   "dc": 11},
            {"id": "rush",    "label": "💪 Перепрыгнуть",              "stat": "strength",  "dc": 12},
            {"id": "ignore",  "label": "🚶 Обойти стороной",           "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e37",
        "text": (
            "🧙‍♀️ *Старая ведьма* предлагает загадочный напиток.\n"
            "_«Выпьешь — даст силу, или яд... кто знает»_\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "drink",   "label": "🧠 Выпить (оценить состав)",   "stat": "intellect", "dc": 13},
            {"id": "refuse",  "label": "🚶 Отказаться",                "stat": None,        "dc": None},
            {"id": "sell",    "label": "👄 Продать напиток",           "stat": "charisma",  "dc": 11},
        ]
    },
    {
        "id": "e38",
        "text": (
            "📦 *Рычащий зверь* стоит прямо на сундуке.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "force",   "label": "💪 Прогнать силой",            "stat": "strength",  "dc": 13},
            {"id": "scare",   "label": "👄 Припугнуть",                "stat": "charisma",  "dc": 12},
            {"id": "fight",   "label": "⚔️ Сразиться",                 "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e39",
        "text": (
            "💎 На полу лежит *пульсирующий кристалл*.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "take",    "label": "🎯 Взять",                     "stat": "agility",   "dc": 11},
            {"id": "study",   "label": "🧠 Исследовать",               "stat": "intellect", "dc": 12},
            {"id": "ignore",  "label": "🚶 Пройти мимо",               "stat": None,        "dc": None},
        ]
    },
    {
        "id": "e40",
        "text": (
            "🆘 Из туннеля доносится *зов о помощи*.\n\n"
            "Что делаешь?"
        ),
        "choices": [
            {"id": "help",    "label": "💪 Помочь",                    "stat": "strength",  "dc": 12},
            {"id": "ignore",  "label": "🚶 Игнорировать",              "stat": None,        "dc": None},
            {"id": "trick",   "label": "👄 Обмануть зовущего",         "stat": "charisma",  "dc": 13},
        ]
    },
]

EVENT_ID_MAP = {e["id"]: e for e in EVENTS}

def get_random_event():
    return random.choice(EVENTS)

# ═══════════════════════════════════════════════════════════════
# ПОСЛЕДСТВИЯ СОБЫТИЙ
# ═══════════════════════════════════════════════════════════════

def apply_event_outcome(event_id, choice_id, success, char, state, user_id):
    """
    Применяет последствие выбора. Возвращает текст результата.
    Все изменения HP/MP/items/coins применяются здесь.
    """
    max_hp = calc_max_hp(char)
    max_mp = calc_max_mp(char)
    cur_hp = char['hp']
    cur_mp = char['mp']
    items = get_items(char)
    result = ""
    start_battle = False  # если нужно начать битву с врагом
    battle_enemy_override = None

    # ── helpers ───────────────────────────────────────────────
    def add_hp(n):
        nonlocal cur_hp
        cur_hp = min(max_hp, cur_hp + n)

    def sub_hp(n):
        nonlocal cur_hp
        cur_hp = max(1, cur_hp - n)

    def add_mp(n):
        nonlocal cur_mp
        cur_mp = min(max_mp, cur_mp + n)

    def add_coins(n):
        conn = get_conn(); c = conn.cursor()
        c.execute('UPDATE tower_chars SET coins=coins+%s WHERE user_id=%s', (n, user_id))
        conn.commit(); conn.close()

    def sub_coins(n):
        conn = get_conn(); c = conn.cursor()
        c.execute('UPDATE tower_chars SET coins=GREATEST(0,coins-%s) WHERE user_id=%s', (n, user_id))
        conn.commit(); conn.close()

    def add_item(key, n=1):
        items[key] = items.get(key, 0) + n

    def add_status(st, val):
        p_st = state.get('player_statuses', {})
        p_st[st] = p_st.get(st, 0) + val
        state['player_statuses'] = p_st

    # ── e01: плачущий мальчик ─────────────────────────────────
    if event_id == "e01":
        if choice_id == "help":
            if success:
                add_coins(10); add_item('regen_small')
                result = "✅ Ты нашёл маму мальчика. Тебе дали *10 монет* и небольшой эликсир."
            else:
                sub_hp(5)
                result = "❌ Заплутали вместе. Ты потерял *5 HP* и ребёнок убежал."
        elif choice_id == "guard":
            if success:
                add_coins(15)
                result = "✅ Стражник доволен. Награда *15 монет*."
            else:
                sub_coins(5)
                result = "❌ Стражник недоволен. Штраф *−5 монет*."
        elif choice_id == "ignore":
            if random.random() < 0.3:
                result = "⚠️ Позже на тебя напал вор!"
                start_battle = True
                battle_enemy_override = "rat"
            else:
                result = "🚶 Ты прошёл мимо. Ничего не произошло."

    # ── e02: попрошайка ───────────────────────────────────────
    elif event_id == "e02":
        if choice_id == "give":
            sub_coins(10)
            state['charisma_bonus'] = state.get('charisma_bonus', 0) + 1
            result = "✅ Старец благодарит. Ты чувствуешь себя добрее. *+1 к Харизме* (временно)."
        elif choice_id == "bluff":
            if success:
                add_coins(20)
                result = "✅ Старец растрогался и дал тебе *20 монет*."
            else:
                result = "❌ Старец заметил ложь. Он разочарован."
        elif choice_id == "steal":
            if success:
                add_item('health_potion')
                result = "✅ В мешочке оказалось *зелье здоровья*!"
            else:
                sub_hp(10)
                result = "❌ Ловушка! *−10 HP*."

    # ── e03: сундук в нише ────────────────────────────────────
    elif event_id == "e03":
        if choice_id == "pick":
            if success:
                _give_random_item(items, 'uncommon')
                result = "✅ Замок поддался. Внутри *ценный предмет*!"
            else:
                sub_hp(8)
                result = "❌ Ловушка! *−8 HP*."
        elif choice_id == "smash":
            if success:
                _give_random_item(items, 'basic')
                result = "✅ Сундук открыт силой. Внутри *предмет*."
            else:
                sub_hp(5)
                result = "❌ Не вышло. *−5 HP*."
        elif choice_id == "study":
            if success:
                add_coins(10); _give_random_item(items, 'basic')
                result = "✅ Нашёл обходной путь! *+10 монет* и предмет."
            else:
                result = "❌ Потратил время зря. Впереди враг!"
                start_battle = True

    # ── e04: торговец редкостями ──────────────────────────────
    elif event_id == "e04":
        if choice_id == "buy":
            conn = get_conn(); c = conn.cursor()
            c.execute('SELECT coins FROM tower_chars WHERE user_id=%s', (user_id,))
            row = c.fetchone(); conn.close()
            if row and row[0] >= 30:
                sub_coins(30); _give_random_item(items, 'rare')
                result = "✅ Купил редкую вещь за *30 монет*!"
            else:
                result = "❌ Не хватает монет."
        elif choice_id == "haggle":
            if success:
                conn = get_conn(); c = conn.cursor()
                c.execute('SELECT coins FROM tower_chars WHERE user_id=%s', (user_id,))
                row = c.fetchone(); conn.close()
                if row and row[0] >= 15:
                    sub_coins(15); _give_random_item(items, 'rare')
                    result = "✅ Сторговался! Купил за *15 монет*."
                else:
                    result = "❌ Не хватает монет даже со скидкой."
            else:
                result = "❌ Торговец обиделся — цена выросла."
        elif choice_id == "leave":
            result = "🚶 Ты ушёл. Ничего не произошло."

    # ── e05: странный флакон ──────────────────────────────────
    elif event_id == "e05":
        if choice_id == "drink":
            if success:
                add_hp(20)
                result = "✅ Вкусно! *+20 HP*."
            else:
                add_status('poison', 2); sub_hp(10)
                result = "❌ Яд! ☠️*Яд(2)* и *−10 HP*."
        elif choice_id == "toss":
            result = "🗑️ Ты выбросил флакон. Ничего не произошло."
        elif choice_id == "take":
            add_item('health_potion')
            result = "🎒 Флакон оказался *зельем здоровья*. Можно использовать потом."

    # ── e06: призрак ──────────────────────────────────────────
    elif event_id == "e06":
        if choice_id == "deceive":
            if success:
                result = "✅ Призрак поверил и исчез."
            else:
                add_status('weakness', 2)
                result = "❌ Призрак разозлился. ⛓️*Слабость(2)*."
        elif choice_id == "fight":
            result = "⚔️ Ты бросаешься в бой с призраком!"
            start_battle = True; battle_enemy_override = "ghost"
        elif choice_id == "ignore":
            result = "🚶 Ты прошёл мимо. Призрак остался."

    # ── e07: свиток с загадкой ────────────────────────────────
    elif event_id == "e07":
        if choice_id == "answer":
            if success:
                _give_random_item(items, 'rare')
                result = "✅ Правильно! Тайник открылся — *редкий предмет*!"
            else:
                sub_hp(5)
                result = "❌ Свиток проклял тебя. *−5 HP*."
        elif choice_id == "burn":
            add_item('health_potion')
            result = "🔥 Тайник открылся. Внутри *зелье здоровья*."
        elif choice_id == "sell":
            add_coins(20)
            result = "💰 Продал свиток за *20 монет*."

    # ── e08: ловушка ──────────────────────────────────────────
    elif event_id == "e08":
        if choice_id == "jump":
            if success:
                result = "✅ Прыжок удался! Миновал ловушку."
            else:
                sub_hp(10)
                result = "❌ Упал! *−10 HP*."
        elif choice_id == "hold":
            if success:
                sub_hp(3)
                result = "✅ Удержался. *−3 HP*."
            else:
                sub_hp(15)
                result = "❌ Сорвался! *−15 HP*."
        elif choice_id == "hide":
            if success:
                _give_random_item(items, 'uncommon')
                result = "✅ Скрытая комната! Нашёл *предмет*."
            else:
                sub_hp(12)
                result = "❌ Ловушка сработала! *−12 HP*."

    # ── e09: голодный зверь ───────────────────────────────────
    elif event_id == "e09":
        if choice_id == "feed":
            if success:
                add_coins(10)
                result = "✅ Зверь наелся и ушёл. *+10 монет*."
            else:
                sub_hp(8)
                result = "❌ Зверь не унялся. *−8 HP*."
        elif choice_id == "run":
            if success:
                result = "✅ Убежал!"
            else:
                sub_hp(10)
                result = "❌ Зверь догнал. *−10 HP*."
        elif choice_id == "fight":
            result = "⚔️ Ты вступаешь в бой!"
            start_battle = True; battle_enemy_override = "wolf"

    # ── e10: колодец ──────────────────────────────────────────
    elif event_id == "e10":
        if choice_id == "look":
            if success:
                _give_random_item(items, 'uncommon')
                result = "✅ Увидел сундук и достал *предмет*!"
            else:
                sub_hp(10)
                result = "❌ Упал в колодец! *−10 HP*."
        elif choice_id == "rope":
            if success:
                _give_random_item(items, 'uncommon')
                result = "✅ Аккуратно достал *предмет*."
            else:
                sub_hp(8)
                result = "❌ Верёвка оборвалась. *−8 HP*."
        elif choice_id == "call":
            if success:
                add_coins(10); add_item('health_potion')
                result = "✅ Путник помог. Отдал *10 монет* и получил *зелье*."
            else:
                result = "🗣️ Никто не ответил."

    # ── e11: загадка пастуха ──────────────────────────────────
    elif event_id == "e11":
        if choice_id == "solve":
            if success:
                add_hp(15)
                result = "✅ Пища! *+15 HP*."
            else:
                result = "❌ Не угадал."
        elif choice_id == "force":
            if success:
                _give_random_item(items, 'basic')
                result = "✅ Скрытый ход! Нашёл *предмет*."
            else:
                sub_hp(5)
                result = "❌ Завал. *−5 HP*."
        elif choice_id == "ignore":
            result = "🚶 Прошёл мимо."

    # ── e12: музыкант ─────────────────────────────────────────
    elif event_id == "e12":
        if choice_id == "listen":
            if success:
                state['charisma_bonus'] = state.get('charisma_bonus', 0) + 1
                result = "✅ Музыка вдохновила! *+1 Харизма* (временно)."
            else:
                result = "❌ Музыка усыпила на мгновение. Ничего полезного."
        elif choice_id == "coin":
            sub_coins(1)
            state['intellect_bonus'] = state.get('intellect_bonus', 0) + 2
            result = "💰 Музыкант дал подсказку. *+2 Интеллект* (временно)."
        elif choice_id == "leave":
            result = "🚶 Ты ушёл."

    # ── e13: печка ────────────────────────────────────────────
    elif event_id == "e13":
        if choice_id == "eat":
            add_hp(12)
            result = "🍲 Вкусная еда! *+12 HP*."
        elif choice_id == "check":
            if success:
                state['regen_bonus'] = state.get('regen_bonus', 0) + 5
                result = "✅ Нашёл рецепт. *+5 к регену*."
            else:
                result = "❌ Ничего интересного."
        elif choice_id == "take":
            if success:
                add_coins(15)
                result = "✅ Продал продукты. *+15 монет*."
            else:
                add_status('poison', 2)
                result = "❌ Еда оказалась тухлой! ☠️*Яд(2)*."

    # ── e14: бросок камня ─────────────────────────────────────
    elif event_id == "e14":
        if choice_id == "throw":
            if success:
                add_item('regen_small')
                result = "✅ Получил *малый эликсир*!"
            else:
                sub_hp(8)
                result = "❌ Камень отлетел обратно! *−8 HP*."
        elif choice_id == "fake":
            if success:
                result = "✅ Провёл проверку без потерь."
            else:
                result = "⚠️ Охрана заметила! Впереди бой!"
                start_battle = True; battle_enemy_override = "skeleton"
        elif choice_id == "pass":
            result = "🚶 Прошёл мимо."

    # ── e15: торговец заклинаниями ────────────────────────────
    elif event_id == "e15":
        if choice_id == "answer":
            if success:
                _give_scroll(items)
                result = "✅ Правильно! Бесплатный *свиток*!"
            else:
                result = "❌ Торговец обиделся."
        elif choice_id == "bribe":
            if success:
                sub_coins(10); _give_scroll(items)
                result = "✅ Сторговался за *10 монет*."
            else:
                result = "⚠️ Торгаш позвал стражу!"
                start_battle = True; battle_enemy_override = "skeleton"
        elif choice_id == "buy":
            conn = get_conn(); c = conn.cursor()
            c.execute('SELECT coins FROM tower_chars WHERE user_id=%s', (user_id,))
            row = c.fetchone(); conn.close()
            if row and row[0] >= 25:
                sub_coins(25); _give_scroll(items)
                result = "✅ Купил *свиток* за 25 монет."
            else:
                result = "❌ Не хватает монет."

    # ── e16: хрустальный шар ─────────────────────────────────
    elif event_id == "e16":
        if choice_id == "grab":
            if success:
                _give_scroll(items)
                result = "✅ Поймал шар! Внутри *свиток заклинания*."
            else:
                sub_hp(10)
                result = "❌ Шар разбился! *−10 HP*."
        elif choice_id == "smash":
            if success:
                add_mp(20)
                result = "✅ Взрыв магии! *+20 MP*."
            else:
                sub_hp(12)
                result = "❌ Магический взрыв! *−12 HP*."
        elif choice_id == "study":
            if success:
                add_item('health_potion')
                result = "✅ Изучил шар. Нашёл *зелье здоровья*."
            else:
                result = "❌ Слишком сложно. Ничего."

    # ── e17: спорящие путники ─────────────────────────────────
    elif event_id == "e17":
        if choice_id == "calm":
            if success:
                add_item('health_potion')
                result = "✅ Помирил их. Один дал *зелье здоровья*."
            else:
                result = "⚠️ Они позвали охрану!"
                start_battle = True; battle_enemy_override = "skeleton"
        elif choice_id == "bribe":
            sub_coins(10)
            result = "💰 Отдал *10 монет*. Путники разошлись."
        elif choice_id == "argue":
            if success:
                state['intellect_bonus'] = state.get('intellect_bonus', 0) + 1
                result = "✅ Полезная информация о башне! *+1 Интеллект* (временно)."
            else:
                result = "⚠️ Спор перерос в драку!"
                start_battle = True; battle_enemy_override = "goblin"

    # ── e18: тёмная комната ───────────────────────────────────
    elif event_id == "e18":
        if choice_id == "go":
            if success:
                add_hp(20)
                result = "✅ Нашёл раненого путника с зельями! *+20 HP*."
            else:
                sub_hp(10)
                result = "❌ Ловушка! *−10 HP*."
        elif choice_id == "shout":
            if success:
                result = "✅ Враг испугался и убежал."
            else:
                result = "⚠️ Привлёк хищника!"
                start_battle = True; battle_enemy_override = "bat"
        elif choice_id == "retreat":
            result = "🚶 Отступил. Ничего не произошло."

    # ── e19: карта ────────────────────────────────────────────
    elif event_id == "e19":
        if choice_id == "pay":
            sub_coins(15)
            state['chest_bonus_floor'] = True
            result = "🗺️ Карта! Шанс найти *сундук* на следующем этаже повышен."
        elif choice_id == "steal":
            if success:
                state['chest_bonus_floor'] = True
                result = "✅ Взял карту бесплатно!"
            else:
                sub_hp(10); sub_coins(10)
                result = "❌ Поймали! *−10 HP, −10 монет*."
        elif choice_id == "ask":
            if success:
                sub_coins(10); state['chest_bonus_floor'] = True
                result = "✅ Сторговался за *10 монет*."
            else:
                result = "❌ Подсунули подделку. Зря потратил время."

    # ── e20: старый колдун ───────────────────────────────────
    elif event_id == "e20":
        if choice_id == "agree":
            sub_hp(10)
            state['intellect_bonus'] = state.get('intellect_bonus', 0) + 3
            result = "✅ Отдал *10 HP* → *+3 Интеллекта* на 3 этажа."
        elif choice_id == "refuse":
            result = "🚶 Ты отказался. Мудрое решение."
        elif choice_id == "trick":
            if success:
                sub_hp(5); state['intellect_bonus'] = state.get('intellect_bonus', 0) + 3
                result = "✅ Перехитрил! *−5 HP* → *+3 Интеллекта*."
            else:
                sub_hp(5); add_status('weakness', 1)
                result = "❌ Колдун разгадал хитрость! *−5 HP + ⛓️Слабость(1)*."

    # ── e21-40: краткие ───────────────────────────────────────
    elif event_id == "e21":
        if choice_id == "pick":
            if success: _give_random_item(items, 'uncommon'); result = "✅ Сундук открыт! *Предмет*."
            else: sub_hp(8); result = "❌ Ловушка! *−8 HP*."
        elif choice_id == "smash":
            if success: _give_random_item(items, 'basic'); result = "✅ Открыт! *Предмет*."
            else: sub_hp(5); result = "❌ Не вышло. *−5 HP*."
        else: result = "🚶 Прошёл мимо."

    elif event_id == "e22":
        if choice_id == "take":
            if success: add_coins(5); result = "✅ *+5 монет* к следующей проверке."
            else: sub_hp(5); result = "❌ Ловушка! *−5 HP*."
        elif choice_id == "pass": result = "🚶 Прошёл мимо."
        else:
            if success: add_item('regen_small'); result = "✅ Нашёл *эликсир регенерации*."
            else: sub_hp(7); result = "❌ Ловушка! *−7 HP*."

    elif event_id == "e23":
        if choice_id == "check":
            if success: _give_random_item(items, 'basic'); result = "✅ Нашёл *предмет*!"
            else: sub_hp(10); result = "❌ Враг! *−10 HP*."
        elif choice_id == "ignore": result = "🚶 Ничего."
        else:
            if success: result = "✅ Отпугнул врага."
            else: result = "⚠️ Привлёк монстра!"; start_battle = True

    elif event_id == "e24":
        if choice_id == "solve":
            if success: _give_random_item(items, 'uncommon'); result = "✅ *Предмет* в награду!"
            else: result = "❌ Не угадал."
        elif choice_id == "pass": result = "🚶 Прошёл мимо."
        else:
            if success: _give_random_item(items, 'basic'); result = "✅ Скрытый тайник!"
            else: sub_hp(5); result = "❌ Ловушка! *−5 HP*."

    elif event_id == "e25":
        if choice_id == "bribe":
            if success: add_item('health_potion'); add_coins(5); result = "✅ Ключ и *+5 монет*."
            else: sub_coins(10); result = "❌ Стражник взял деньги, но не пустил. *−10 монет*."
        elif choice_id == "fight": result = "⚔️ Бой!"; start_battle = True; battle_enemy_override = "skeleton"
        else:
            if success: result = "✅ Обошёл стража."
            else: sub_hp(8); result = "❌ Ловушка! *−8 HP*."

    elif event_id == "e26":
        if choice_id == "grab":
            if success: add_item('health_potion'); result = "✅ *Зелье здоровья*!"
            else: sub_hp(7); result = "❌ Ловушка! *−7 HP*."
        elif choice_id == "careful":
            if success: add_item('health_potion'); add_item('mana_potion'); result = "✅ *2 зелья*!"
            else: sub_hp(5); result = "❌ *−5 HP*."
        else: result = "🚶 Прошёл мимо."

    elif event_id == "e27":
        if choice_id == "help":
            if success: state['charisma_bonus'] = state.get('charisma_bonus', 0)+1; result = "✅ *+1 Харизма* (временно)."
            else: sub_hp(5); result = "❌ Ловушка! *−5 HP*."
        elif choice_id == "ignore": result = "🚶 Ничего."
        else: result = "⚔️ Бой!"; start_battle = True; battle_enemy_override = "ghost"

    elif event_id == "e28":
        if choice_id == "buy":
            conn = get_conn(); c = conn.cursor()
            c.execute('SELECT coins FROM tower_chars WHERE user_id=%s', (user_id,))
            row = c.fetchone(); conn.close()
            if row and row[0] >= 20:
                sub_coins(20); add_item('big_health_potion'); result = "✅ *Большое зелье здоровья*!"
            else: result = "❌ Не хватает монет."
        elif choice_id == "haggle":
            if success: sub_coins(10); add_item('health_potion'); result = "✅ *Зелье* за 10 монет."
            else: sub_coins(25); result = "❌ Цена выросла. *−25 монет*."
        else: result = "🚶 Отказался."

    elif event_id == "e29":
        if choice_id == "take":
            if success: add_mp(10); result = "✅ *+10 MP*!"
            else: sub_hp(5); result = "❌ *−5 HP*."
        elif choice_id == "study":
            if success: _give_scroll(items); result = "✅ Нашёл *свиток заклинания*!"
            else: add_status('weakness', 1); sub_hp(5); result = "❌ Проклятие! *−5 HP + Слабость*."
        else: result = "🚶 Прошёл мимо."

    elif event_id == "e30":
        if choice_id == "use":
            if success: add_hp(20); result = "✅ Свиток сработал! *+20 HP*."
            else: sub_hp(8); result = "❌ Взрыв! *−8 HP*."
        elif choice_id == "sell":
            if success: add_coins(20); result = "✅ *+20 монет*."
            else: add_coins(10); result = "Продал за *10 монет*."
        else: result = "🚶 Оставил лежать."

    elif event_id == "e31":
        if choice_id == "jump":
            if success: result = "✅ Перепрыгнул!"
            else: sub_hp(10); result = "❌ Упал! *−10 HP*."
        elif choice_id == "rope":
            if success: result = "✅ Спустился безопасно."
            else: sub_hp(7); result = "❌ Верёвка оборвалась! *−7 HP*."
        else:
            if success: _give_random_item(items, 'basic'); result = "✅ Нашёл обход и *предмет*!"
            else: sub_hp(5); result = "❌ Ловушка! *−5 HP*."

    elif event_id == "e32":
        if choice_id == "buy":
            conn = get_conn(); c = conn.cursor()
            c.execute('SELECT coins FROM tower_chars WHERE user_id=%s', (user_id,))
            row = c.fetchone(); conn.close()
            if row and row[0] >= 25:
                sub_coins(25); _give_random_item(items, 'basic'); result = "✅ Купил *оружие*."
            else: result = "❌ Не хватает монет."
        elif choice_id == "check":
            if success: sub_coins(15); _give_random_item(items, 'uncommon'); result = "✅ Скидка! *Необычный предмет*."
            else: sub_coins(5); result = "❌ Продешевил. *−5 монет*."
        else:
            if success: _give_random_item(items, 'basic'); result = "✅ Стащил *предмет*!"
            else: sub_hp(10); result = "❌ Поймали! *−10 HP*."

    elif event_id == "e33":
        if choice_id == "red":
            if success: _give_random_item(items, 'rare'); result = "🔴 ✅ *Редкий предмет*!"
            else: sub_hp(8); result = "🔴 ❌ Ловушка! *−8 HP*."
        elif choice_id == "blue":
            if success: state['charisma_bonus'] = state.get('charisma_bonus',0)+2; result = "🔵 ✅ *+2 Харизма* (временно)."
            else: sub_hp(5); result = "🔵 ❌ *−5 HP*."
        else:
            if success: _give_random_item(items, 'uncommon'); result = "🟢 ✅ *Сундук с предметом*!"
            else: sub_hp(7); result = "🟢 ❌ Ловушка! *−7 HP*."

    elif event_id == "e34":
        if choice_id == "decode":
            if success: add_coins(50); result = "✅ Руны разгаданы! Сокровищница: *+50 монет*."
            else: sub_hp(5); result = "❌ Магический отпор. *−5 HP*."
        elif choice_id == "break":
            if success: _give_random_item(items, 'uncommon'); result = "✅ Сундук за дверью! *Предмет*."
            else: sub_hp(8); result = "❌ Взрыв! *−8 HP*."
        else: result = "🚶 Обошёл стороной."

    elif event_id == "e35":
        if choice_id == "play":
            if success: add_coins(20); result = "✅ Выиграл! *+20 монет*."
            else: sub_coins(10); result = "❌ Проиграл. *−10 монет*."
        elif choice_id == "refuse": result = "🚶 Отказался от игры."
        else:
            if success: add_coins(20); result = "✅ Обманул демона! *+20 монет*."
            else: sub_hp(5); result = "❌ Демон разозлился! *−5 HP*."

    elif event_id == "e36":
        if choice_id == "careful":
            if success: result = "✅ Перешёл без потерь."
            else: sub_hp(7); result = "❌ Поскользнулся! *−7 HP*."
        elif choice_id == "rush":
            if success: result = "✅ Перепрыгнул!"
            else: sub_hp(10); result = "❌ Упал! *−10 HP*."
        else: result = "🚶 Обошёл. Всё хорошо."

    elif event_id == "e37":
        if choice_id == "drink":
            if success: add_hp(20); result = "✅ Целебный напиток! *+20 HP*."
            else: add_status('poison', 2); sub_hp(10); result = "❌ Яд! ☠️*Яд(2)* и *−10 HP*."
        elif choice_id == "refuse": result = "🚶 Отказался. Мудро."
        else:
            if success: add_coins(15); result = "✅ Продал напиток. *+15 монет*."
            else: result = "❌ Ведьма не купила."

    elif event_id == "e38":
        if choice_id == "force":
            if success: _give_random_item(items, 'uncommon'); result = "✅ Зверь ушёл! *Предмет* в сундуке."
            else: sub_hp(10); result = "❌ Зверь атаковал! *−10 HP*."
        elif choice_id == "scare":
            if success: _give_random_item(items, 'uncommon'); result = "✅ Зверь убежал! *Предмет*."
            else: sub_hp(8); result = "❌ Не испугался! *−8 HP*."
        else: result = "⚔️ Бой!"; start_battle = True; battle_enemy_override = "bear"

    elif event_id == "e39":
        if choice_id == "take":
            if success: add_mp(5); result = "✅ *+5 MP*."
            else: sub_hp(5); result = "❌ *−5 HP*."
        elif choice_id == "study":
            if success: state['intellect_bonus'] = state.get('intellect_bonus',0)+1; result = "✅ *+1 Интеллект* (временно)."
            else: add_status('weakness',1); sub_hp(5); result = "❌ Проклятие! *−5 HP + Слабость*."
        else: result = "🚶 Прошёл мимо."

    elif event_id == "e40":
        if choice_id == "help":
            if success: _give_random_item(items, 'basic'); result = "✅ Путник дал *предмет* в благодарность."
            else: sub_hp(10); result = "❌ Ловушка! *−10 HP*."
        elif choice_id == "ignore": result = "🚶 Прошёл мимо."
        else:
            if success: add_coins(15); result = "✅ Обманул зовущего. *+15 монет*."
            else: add_status('weakness', 2); result = "❌ Проклятие! *⛓️Слабость(2)*."

    else:
        result = "🚶 Ничего не произошло."

    # Сохраняем HP/MP
    update_char_hp_mp(user_id, max(1, cur_hp), cur_mp)
    save_items(user_id, items)

    return result, start_battle, battle_enemy_override


def _give_random_item(items, tier='basic'):
    """Добавляет случайный предмет в инвентарь"""
    pools = {
        'basic':    ['health_potion','mana_potion','regen_small','bomb','ice_flask'],
        'uncommon': ['health_potion','big_health_potion','mana_potion','bomb','smoke_bomb',
                     'poison_bomb','str_potion','agi_potion','int_potion','speed_potion'],
        'rare':     ['big_health_potion','big_mana_potion','regen_big','second_wind_potion',
                     'scroll_fireball','scroll_ice_arrow','scroll_heal','scroll_mana','scroll_teleport'],
    }
    pool = pools.get(tier, pools['basic'])
    key = random.choice(pool)
    items[key] = items.get(key, 0) + 1

def _give_scroll(items):
    scrolls = ['scroll_fireball','scroll_ice_arrow','scroll_heal','scroll_mana','scroll_teleport']
    key = random.choice(scrolls)
    items[key] = items.get(key, 0) + 1

# ═══════════════════════════════════════════════════════════════
# ХЭНДЛЕРЫ СОБЫТИЙ
# ═══════════════════════════════════════════════════════════════

def send_event(bot, chat_id, user_id, event, state):
    """Показывает карточку события"""
    markup = InlineKeyboardMarkup(row_width=1)
    for ch in event['choices']:
        markup.add(InlineKeyboardButton(
            ch['label'],
            callback_data=f"ev_{event['id']}_{ch['id']}"
        ))
    msg = bot.send_message(chat_id, event['text'],
                           reply_markup=markup, parse_mode='Markdown')
    state['event_msg_id'] = msg.message_id
    save_battle(user_id, state)

def register_tower_events(bot):

    @bot.callback_query_handler(func=lambda call: call.data.startswith('ev_'))
    def cb_event_choice(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        char = get_tower_char(user_id)
        state = get_battle(user_id)
        if not char or not state: return

        # Парсим: ev_{event_id}_{choice_id}
        parts = call.data[3:].split('_', 1)  # убираем "ev_"
        # event_id имеет формат "e01", choice_id — остаток
        # Формат callback: ev_e01_help
        raw = call.data[3:]  # "e01_help"
        event_id = raw[:3]   # "e01"
        choice_id = raw[4:]  # "help"

        event = EVENT_ID_MAP.get(event_id)
        if not event: return

        # Находим выбор
        choice = next((c for c in event['choices'] if c['id'] == choice_id), None)
        if not choice: return

        # Проверка характеристики
        success = True
        if choice['stat'] and choice['dc']:
            success = check(char, choice['stat'], choice['dc'])

        # Применяем результат
        result_text, start_battle, battle_enemy_override = apply_event_outcome(
            event_id, choice_id, success, char, state, user_id)

        # Удаляем сообщение события
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        ev_msg = state.get('event_msg_id')
        if ev_msg:
            try: bot.delete_message(call.message.chat.id, ev_msg)
            except: pass

        # Отправляем результат
        bot.send_message(call.message.chat.id,
            f"📋 *Результат:*\n\n{result_text}", parse_mode='Markdown')

        char = get_tower_char(user_id)

        if start_battle:
            # Начинаем бой с конкретным или случайным врагом
            floor = state['floor']
            if battle_enemy_override and battle_enemy_override in ENEMIES:
                ekey = battle_enemy_override
                e = ENEMIES[ekey]
                ehp = int(e['base_hp'] + floor * e['hp_s'])
                edmg = round(e['base_dmg'] + floor * e['dmg_s'], 1)
            else:
                ekey, ehp, edmg = spawn_enemy(floor)
            e = ENEMIES[ekey]

            state['enemy_key'] = ekey
            state['enemy_hp'] = ehp
            state['enemy_max_hp'] = ehp
            state['enemy_base_dmg'] = edmg
            state['enemy_statuses'] = {}
            state['player_defending'] = False
            state['enemy_dodging'] = False
            state['enemy_blocking'] = False
            state['player_blind'] = False
            state['next_enemy_action'] = roll_enemy_action(ekey, edmg)
            state.pop('active_event', None)

            from tower_battle import send_battle
            send_battle(bot, call.message.chat.id, user_id, char, state,
                        log_lines=[f"⚔️ {e['emoji']} {e['name']} атакует!"])
        else:
            # Убираем флаг события и продолжаем — показываем кнопки для следующего этажа
            state.pop('active_event', None)
            save_battle(user_id, state)

            floor = state['floor']
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("⬆️ Следующий этаж", callback_data="tb_next_floor"),
                InlineKeyboardButton("🚪 Покинуть башню",  callback_data="tb_exit"),
            )
            bot.send_message(call.message.chat.id,
                f"🏯 Этаж *{floor}* пройден. Что дальше?",
                reply_markup=markup, parse_mode='Markdown')
