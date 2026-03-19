# ============================================================
#  arena_data.py  — Все игровые данные для системы Арены
# ============================================================

import random

# ─── Эмодзи классов ──────────────────────────────────────────
CLASS_EMOJI = {
    'Воин':      '⚔️',
    'Варвар':    '🪓',
    'Рейнджер':  '🏹',
    'Ассасин':   '🌑',
    'Друид':     '🌿',
    'Волшебник': '🪄',
    'Колдун':    '🔥',
}

MAGIC_CLASSES = {'Друид', 'Волшебник', 'Колдун'}

# ─── Базовые характеристики классов ──────────────────────────
CLASS_BASE_STATS = {
    'Воин':      {'str': 13, 'dex': 9,  'con': 13, 'int': 6,  'cha': 8,  'lck': 6},
    'Варвар':    {'str': 14, 'dex': 8,  'con': 14, 'int': 5,  'cha': 6,  'lck': 6},
    'Рейнджер':  {'str': 9,  'dex': 14, 'con': 10, 'int': 8,  'cha': 7,  'lck': 7},
    'Ассасин':   {'str': 8,  'dex': 15, 'con': 9,  'int': 8,  'cha': 7,  'lck': 8},
    'Друид':     {'str': 8,  'dex': 10, 'con': 11, 'int': 9,  'cha': 14, 'lck': 8},
    'Волшебник': {'str': 6,  'dex': 9,  'con': 8,  'int': 15, 'cha': 9,  'lck': 8},
    'Колдун':    {'str': 7,  'dex': 9,  'con': 10, 'int': 8,  'cha': 15, 'lck': 8},
}

CLASS_HP = {
    'Воин':      {'base': 120, 'per_level': 12},
    'Варвар':    {'base': 140, 'per_level': 14},
    'Рейнджер':  {'base': 100, 'per_level': 10},
    'Ассасин':   {'base': 90,  'per_level': 9},
    'Друид':     {'base': 95,  'per_level': 10},
    'Волшебник': {'base': 80,  'per_level': 8},
    'Колдун':    {'base': 85,  'per_level': 9},
}

CLASS_MANA = {
    'Воин':      {'base': 5,  'per_level': 2},
    'Варвар':    {'base': 5,  'per_level': 2},
    'Рейнджер':  {'base': 10, 'per_level': 5},
    'Ассасин':   {'base': 10, 'per_level': 5},
    'Друид':     {'base': 40, 'per_level': 7},
    'Волшебник': {'base': 50, 'per_level': 8},
    'Колдун':    {'base': 55, 'per_level': 8},
}

CLASS_SPEED = {
    'Воин':      6,
    'Варвар':    5,
    'Рейнджер':  9,
    'Ассасин':   10,
    'Друид':     8,
    'Волшебник': 7,
    'Колдун':    7,
}

STARTER_WEAPONS = {
    'Воин':      '⚔️ Меч новичка',
    'Варвар':    '🪓 Деревянный топор',
    'Рейнджер':  '🏹 Лук новичка',
    'Ассасин':   '🗡️ Кинжал новичка',
    'Друид':     '🌿 Посох природы',
    'Волшебник': '🪄 Посох ученика',
    'Колдун':    '🔥 Тёмный жезл',
}

# ─── Таблица опыта (по уровням) ───────────────────────────────
# XP_THRESHOLDS[i] = суммарный XP для достижения уровня (i+1)
XP_THRESHOLDS = [
    0, 100, 400, 900, 1600, 2500, 3600, 4900, 6400, 8100, 10000,
    12100, 14400, 16900, 19600, 22500, 25600, 28900, 32400, 36100, 40000,
    44100, 48400, 52900, 57600, 62500, 67600, 72900, 78400, 84100, 90000,
    96100, 102400, 108900, 115600, 122500, 129600, 136900, 144400, 152100, 160000,
    168100, 176400, 184900, 193600, 202500, 211600, 220900, 230400, 240100,
]

def get_level_from_xp(xp):
    for i in range(len(XP_THRESHOLDS) - 1, -1, -1):
        if xp >= XP_THRESHOLDS[i]:
            return i + 1
    return 1

def get_xp_to_next(xp):
    level = get_level_from_xp(xp)
    if level >= 50:
        return 0
    return XP_THRESHOLDS[level] - xp


# ─── Оружия ─────────────────────────────────────────────────
# stat: 'str' | 'dex' | 'int'
# type: 'melee' | 'ranged' | 'other'
# ability_key: None или строка — ключ обработчика в arena_combat

WEAPONS = {
    # ⚪ Обычные (стартовые — без способностей)
    '⚔️ Меч новичка':        {'rarity':'⚪Обычный','stat':'str','type':'melee', 'base_dmg':4,'ability':None,'ability_key':None},
    '🏹 Лук новичка':         {'rarity':'⚪Обычный','stat':'dex','type':'ranged','base_dmg':4,'ability':None,'ability_key':None},
    '🗡️ Кинжал новичка':     {'rarity':'⚪Обычный','stat':'dex','type':'melee', 'base_dmg':3,'ability':None,'ability_key':None},
    '🌿 Посох природы':       {'rarity':'⚪Обычный','stat':'str','type':'other', 'base_dmg':3,'ability':None,'ability_key':None},
    '🪄 Посох ученика':       {'rarity':'⚪Обычный','stat':'str','type':'other', 'base_dmg':3,'ability':None,'ability_key':None},
    '🔥 Тёмный жезл':         {'rarity':'⚪Обычный','stat':'str','type':'other', 'base_dmg':4,'ability':None,'ability_key':None},
    '🪓 Деревянный топор':    {'rarity':'⚪Обычный','stat':'str','type':'melee', 'base_dmg':5,'ability':None,'ability_key':None},
    '🪵 Тяжёлая дубина':      {'rarity':'⚪Обычный','stat':'str','type':'melee', 'base_dmg':6,'ability':None,'ability_key':None},
    '🔪 Метательный нож':     {'rarity':'⚪Обычный','stat':'dex','type':'ranged','base_dmg':3,'ability':None,'ability_key':None},
    '🪚 Копьё охотника':      {'rarity':'⚪Обычный','stat':'str','type':'melee', 'base_dmg':4,'ability':None,'ability_key':None},
    # 🟢 Необычные
    '⚔️ Стальной клинок стража': {'rarity':'🟢Необычный','stat':'str','type':'melee','base_dmg':7,'ability':None,'ability_key':None},
    '🪓 Секира налётчика':    {'rarity':'🟢Необычный','stat':'str','type':'melee','base_dmg':8,'ability':None,'ability_key':None},
    '🪚 Пика дозорного':      {'rarity':'🟢Необычный','stat':'str','type':'melee','base_dmg':6,'ability':None,'ability_key':None},
    '⚒️ Кузнечный молот':     {'rarity':'🟢Необычный','stat':'str','type':'melee','base_dmg':7,'ability':None,'ability_key':None},
    '🗡️ Клинок наёмника':    {'rarity':'🟢Необычный','stat':'dex','type':'melee','base_dmg':6,'ability':None,'ability_key':None},
    '🗡️ Стилет дуэлянта':    {'rarity':'🟢Необычный','stat':'dex','type':'melee','base_dmg':7,'ability':None,'ability_key':None},
    '🏹 Лук разведчика':      {'rarity':'🟢Необычный','stat':'dex','type':'ranged','base_dmg':6,'ability':None,'ability_key':None},
    '🪄 Кристальный жезл':    {'rarity':'🟢Необычный','stat':'str','type':'other','base_dmg':5,'ability':None,'ability_key':None},
    '🌿 Посох корней':        {'rarity':'🟢Необычный','stat':'str','type':'other','base_dmg':6,'ability':None,'ability_key':None},
    '🪓 Топор лесоруба':      {'rarity':'🟢Необычный','stat':'str','type':'melee','base_dmg':7,'ability':None,'ability_key':None},
    '⚔️ Сабля стражника':    {'rarity':'🟢Необычный','stat':'str','type':'melee','base_dmg':6,'ability':None,'ability_key':None},
    '🔥 Темный осколок':      {'rarity':'🟢Необычный','stat':'str','type':'other','base_dmg':7,'ability':None,'ability_key':None},
    # 🔵 Редкие
    '⚔️ Рунный клинок прорыва': {
        'rarity':'🔵Редкий','stat':'str','type':'melee','base_dmg':8,
        'ability':'при крите +50% урона и 25% шанс 💔Уязвимость(1)',
        'ability_key':'rune_blade'},
    '🪵 Молот оглушающего удара': {
        'rarity':'🔵Редкий','stat':'str','type':'melee','base_dmg':10,
        'ability':'20% шанс ⚡Оглушение(1)',
        'ability_key':'stun_hammer'},
    '🪚 Пика истощения': {
        'rarity':'🔵Редкий','stat':'str','type':'melee','base_dmg':7,
        'ability':'25% шанс ⛓️Слабость(1) и -1 скорость на 1 ход',
        'ability_key':'exhaustion_pike'},
    '🪓 Секира берсерка': {
        'rarity':'🔵Редкий','stat':'str','type':'melee','base_dmg':9,
        'ability':'30% шанс 💪⏫Повышение силы(1)',
        'ability_key':'berserker_axe'},
    '⚔️ Клинок раскалывания': {
        'rarity':'🔵Редкий','stat':'str','type':'melee','base_dmg':8,
        'ability':'крит игнорирует 25% защиты, 20% 🌟⏬(1)',
        'ability_key':'sunder_blade'},
    '🗡️ Кинжал ядовитой тени': {
        'rarity':'🔵Редкий','stat':'dex','type':'melee','base_dmg':6,
        'ability':'35% шанс ☠️Яд(1), при крите +1 стак',
        'ability_key':'poison_dagger'},
    '🏹 Лук меткого выстрела': {
        'rarity':'🔵Редкий','stat':'dex','type':'ranged','base_dmg':8,
        'ability':'+15% к крит, при крите 👁️Слепота(1)',
        'ability_key':'sniper_bow'},
    '🏹 Лук охотника': {
        'rarity':'🔵Редкий','stat':'dex','type':'ranged','base_dmg':9,
        'ability':'первый удар +25% крит, 20% 💔Уязвимость(1)',
        'ability_key':'hunter_bow'},
    '🪄 Жезл искрового удара': {
        'rarity':'🔵Редкий','stat':'str','type':'other','base_dmg':6,
        'ability':'25% ⚡Оглушение(1), при крите гарантировано',
        'ability_key':'spark_wand'},
    '🌿 Посох жизненной силы': {
        'rarity':'🔵Редкий','stat':'str','type':'other','base_dmg':5,
        'ability':'25% 🌿Регенерация(1) владельцу',
        'ability_key':'life_staff'},
    '🔥 Осколок бездны': {
        'rarity':'🔵Редкий','stat':'str','type':'other','base_dmg':8,
        'ability':'30% 🔥Горение(1)',
        'ability_key':'abyss_shard'},
    # 🟣 Эпические
    '🥂 Веер ветров': {
        'rarity':'🟣Эпический','stat':'dex','type':'melee','base_dmg':7,
        'ability':'25% 😶‍🌫️Скрытность(2) и +15% уклонение',
        'ability_key':'wind_fan'},
    '🪄 Жезл ледяного ветра': {
        'rarity':'🟣Эпический','stat':'int','type':'other','base_dmg':8,
        'ability':'25% 🧊Заморозка(1), при крите +1 ход',
        'ability_key':'ice_wand'},
    '🥷 Сайя меча тьмы': {
        'rarity':'🟣Эпический','stat':'str','type':'melee','base_dmg':10,
        'ability':'при крите случайный негативный эффект(1)',
        'ability_key':'shadow_blade'},
    '🔥 Посох огненного духа': {
        'rarity':'🟣Эпический','stat':'int','type':'other','base_dmg':9,
        'ability':'25% 🔥Горение(2), при крите +1',
        'ability_key':'fire_spirit_staff'},
    # 🟡 Легендарные
    '🕷️ Паучий Экскалибур': {
        'rarity':'🟡Легендарный','stat':'str','type':'melee','base_dmg':12,
        'ability':'крит 35% ☠️Яд(2)+😶‍🌫️Скрытность(2)',
        'ability_key':'spider_excalibur'},
    '🌊 Акватический клин': {
        'rarity':'🟡Легендарный','stat':'str','type':'melee','base_dmg':11,
        'ability':'30% 🔥Горение(2), при крите 🌿Регенерация(2)',
        'ability_key':'aqua_wedge'},
    '☁️ Раздор в небесах': {
        'rarity':'🟡Легендарный','stat':'int','type':'other','base_dmg':10,
        'ability':'30% ⚡Оглушение(2)+🧊Заморозка(1)',
        'ability_key':'sky_discord'},
    '⚔️ Двойняшки': {
        'rarity':'🟡Легендарный','stat':'dex','type':'melee','base_dmg':11,
        'ability':'25% 🩸Кровотечение(2)+15% крит',
        'ability_key':'twins'},
    '🏹 Арканический лук': {
        'rarity':'🟡Легендарный','stat':'dex','type':'ranged','base_dmg':12,
        'ability':'30% 👁️Слепота(2), при крите 💔Уязвимость(2)',
        'ability_key':'arcane_bow'},
    '🔥 Клеймор адской искры': {
        'rarity':'🟡Легендарный','stat':'str','type':'melee','base_dmg':13,
        'ability':'35% 🔥Горение(2), крит игнорирует 30% защиты',
        'ability_key':'hellfire_claymore'},
    '🗡️ Лезвие бездны': {
        'rarity':'🟡Легендарный','stat':'dex','type':'melee','base_dmg':11,
        'ability':'крит 30% ☠️Яд(2)+😶‍🌫️Скрытность(2)',
        'ability_key':'abyss_blade'},
    '🪓 Булава грозового титана': {
        'rarity':'🟡Легендарный','stat':'str','type':'melee','base_dmg':12,
        'ability':'25% ⚡Оглушение(2), крит +10% урона',
        'ability_key':'thunder_mace'},
    # 🔴 Реликтовые
    '💎 Аметистовый кинжал': {
        'rarity':'🔴Реликтовый','stat':'dex','type':'melee','base_dmg':13,
        'ability':'крит 40% ☠️Яд(3)+😶‍🌫️Скрытность(3)+20% крит',
        'ability_key':'amethyst_dagger'},
    '🌈 Радужный Экскалибур': {
        'rarity':'🔴Реликтовый','stat':'str','type':'melee','base_dmg':14,
        'ability':'35% 💔Уязвимость(3)+🔥Горение(3), крит +25%',
        'ability_key':'rainbow_excalibur'},
    '🐙 Секира Кракена': {
        'rarity':'🔴Реликтовый','stat':'str','type':'melee','base_dmg':15,
        'ability':'30% ⚡Оглушение(3)+⛓️Слабость(2)',
        'ability_key':'kraken_axe'},
    '🌑 Меч Чёрной Дыры': {
        'rarity':'🔴Реликтовый','stat':'str','type':'melee','base_dmg':15,
        'ability':'крит 🩸Кровотечение(3)+💔Уязвимость(3)+30% крит',
        'ability_key':'black_hole_sword'},
    '☠️ Посох Крика Черепа': {
        'rarity':'🔴Реликтовый','stat':'int','type':'other','base_dmg':12,
        'ability':'35% 🌀Наговор(3)+🔥Горение(3)',
        'ability_key':'skull_staff'},
}

# ─── Артефакты ────────────────────────────────────────────────
ARTIFACTS = {
    # ⚪ Обычные пассивные
    '🧷 Булавка на удачу':    {'rarity':'⚪Обычный','type':'passive','effect':'+1 УДЧ, +1% крит','effect_key':'luck_pin','cooldown':0},
    '🪨 Гладкий камень':      {'rarity':'⚪Обычный','type':'passive','effect':'+1 ТЕЛ, +1% сниж.урона','effect_key':'smooth_stone','cooldown':0},
    '🧿 Капля янтаря':         {'rarity':'⚪Обычный','type':'passive','effect':'+1 ИНТ','effect_key':'amber_drop','cooldown':0},
    '🪢 Узелок памяти':        {'rarity':'⚪Обычный','type':'passive','effect':'+1 ХАР, +1% опыт','effect_key':'memory_knot','cooldown':0},
    '🪶 Перо ветра':           {'rarity':'⚪Обычный','type':'passive','effect':'+1 скорость','effect_key':'wind_feather','cooldown':0},
    '🧸 Плюшевый талисман':   {'rarity':'⚪Обычный','type':'passive','effect':'+1 ТЕЛ, +2 макс.ХП','effect_key':'plush_talisman','cooldown':0},
    '📿 Простой амулет силы': {'rarity':'⚪Обычный','type':'passive','effect':'+1 СИЛ','effect_key':'str_amulet','cooldown':0},
    '🎐 Талисман ветра':       {'rarity':'⚪Обычный','type':'passive','effect':'+1 скорость, +1% крит','effect_key':'wind_talisman','cooldown':0},
    '🧵 Нить защиты':          {'rarity':'⚪Обычный','type':'passive','effect':'+1 ТЕЛ','effect_key':'protection_thread','cooldown':0},
    '📖 Малая записная книга': {'rarity':'⚪Обычный','type':'passive','effect':'+1 ИНТ','effect_key':'small_book','cooldown':0},
    '💍 Медное кольцо удачи': {'rarity':'⚪Обычный','type':'passive','effect':'+1 УДЧ','effect_key':'copper_ring','cooldown':0},
    '🪶 Перо ночной птицы':   {'rarity':'⚪Обычный','type':'passive','effect':'+1 ЛОВ, +1% первый удар','effect_key':'night_feather','cooldown':0},
    '🧿 Глазок-оберег':        {'rarity':'⚪Обычный','type':'passive','effect':'+1 защита от крита','effect_key':'evil_eye','cooldown':0},
    '🧶 Тёплый шарф':          {'rarity':'⚪Обычный','type':'passive','effect':'+1 ТЕЛ, +1 щит/ход','effect_key':'warm_scarf','cooldown':0},
    '🌾 Сухой колос':          {'rarity':'⚪Обычный','type':'passive','effect':'+1 ТЕЛ','effect_key':'dry_ear','cooldown':0},
    '🪵 Тотемная щепка':       {'rarity':'⚪Обычный','type':'passive','effect':'+1 СИЛ','effect_key':'totem_chip','cooldown':0},
    '🪙 Старая монета':        {'rarity':'⚪Обычный','type':'passive','effect':'+2% деньги после боя','effect_key':'old_coin','cooldown':0},
    # ⚪ Обычные активные
    '🕳️ Малый чёрный жетон':  {'rarity':'⚪Обычный','type':'active','effect':'-5% попадание врага на 1 ход','effect_key':'black_token','cooldown':4},
    '🧂 Щепотка соли':         {'rarity':'⚪Обычный','type':'active','effect':'снимает 🩸(1) или ☠️(1)','effect_key':'salt_pinch','cooldown':3},
    '🧊 Кусочек льда':         {'rarity':'⚪Обычный','type':'active','effect':'-1 скорость врага на 1 ход','effect_key':'ice_chunk','cooldown':3},
    '🔥 Уголь тлеющий':        {'rarity':'⚪Обычный','type':'active','effect':'4 урона, 10% 🔥Горение(1)','effect_key':'burning_coal','cooldown':4},
    '🧃 Сладкий нектар':       {'rarity':'⚪Обычный','type':'active','effect':'восстанавливает 5 ХП','effect_key':'sweet_nectar','cooldown':3},
    '🪤 Маленький капкан':     {'rarity':'⚪Обычный','type':'active','effect':'15% ⛓️Слабость(1)','effect_key':'small_trap','cooldown':5},
    '🪞 Тусклое зеркало':      {'rarity':'⚪Обычный','type':'active','effect':'отражает 5% урона 1 ход','effect_key':'dim_mirror','cooldown':4},
    '🧴 Малый эликсир ясности':{'rarity':'⚪Обычный','type':'active','effect':'+3 маны, +1 ИНТ на 1 ход','effect_key':'clarity_elixir','cooldown':4},
    '🪵 Малый тотем защиты':   {'rarity':'⚪Обычный','type':'active','effect':'5 щита на 1 ход','effect_key':'small_totem','cooldown':4},
    '🧪 Малое зелье стойкости':{'rarity':'⚪Обычный','type':'active','effect':'6 ХП, +1 ТЕЛ на 1 ход','effect_key':'endurance_potion','cooldown':3},
    '🕯️ Слабая свеча':         {'rarity':'⚪Обычный','type':'active','effect':'+5% крит на 1 ход','effect_key':'weak_candle','cooldown':3},
    '🔔 Малый колокольчик':    {'rarity':'⚪Обычный','type':'active','effect':'снимает 1 негативный эффект','effect_key':'small_bell','cooldown':4},
    '🎒 Старый брелок-замок':  {'rarity':'⚪Обычный','type':'active','effect':'+2% уклонение на 1 ход','effect_key':'old_lock','cooldown':3},
    '📦 Маленькая шкатулка':   {'rarity':'⚪Обычный','type':'active','effect':'случайный бонус к характ. на 1 ход','effect_key':'small_box','cooldown':5},
    '🧴 Флакон чистой воды':   {'rarity':'⚪Обычный','type':'active','effect':'восстанавливает 7 маны','effect_key':'water_flask','cooldown':3},
    # 🟡 Легендарные
    '🎲 Кости хаоса': {
        'rarity':'🟡Легендарный','type':'active',
        'effect':'случайный бафф(3) себе, случайный дебафф(2) врагу',
        'effect_key':'chaos_dice','cooldown':5},
    '💍 Кольцо двойного удара': {
        'rarity':'🟡Легендарный','type':'passive',
        'effect':'20% шанс повторной атаки (30% если ЛОВ≥10)',
        'effect_key':'double_strike_ring','cooldown':0},
    '🪔 Лампа духа джинна': {
        'rarity':'🟡Легендарный','type':'active',
        'effect':'восст.ХП и ману, 🌟⏫(3)',
        'effect_key':'genie_lamp','cooldown':6},
    '📿 Браслет заклинателя': {
        'rarity':'🟡Легендарный','type':'passive',
        'effect':'+4 ИНТ, заклинания -2 маны',
        'effect_key':'spellcaster_bracelet','cooldown':0},
    '🎺 Рог боевого клича': {
        'rarity':'🟡Легендарный','type':'active',
        'effect':'💪⏫(4), +2 скорость на 2 хода',
        'effect_key':'war_horn','cooldown':5},
    '🕶️ Очки ясного взгляда': {
        'rarity':'🟡Легендарный','type':'passive',
        'effect':'иммунитет к 👁️Слепота, +10% попадание',
        'effect_key':'clarity_glasses','cooldown':0},
    '🪶 Перо времени': {
        'rarity':'🟡Легендарный','type':'active',
        'effect':'дополнительный ход (2 АП)',
        'effect_key':'time_feather','cooldown':6},
    '🧤 Перчатка разрушителя': {
        'rarity':'🟡Легендарный','type':'passive',
        'effect':'+4 СИЛ, +15% урон (если СИЛ≥12 игнорирует 20% защиты)',
        'effect_key':'destroyer_glove','cooldown':0},
    '🍎 Плод вечной жизни': {
        'rarity':'🟡Легендарный','type':'active',
        'effect':'большое лечение + 🌿Регенерация(4)',
        'effect_key':'eternal_fruit','cooldown':6},
    # 🔴 Мифические
    '🌌 Сердце Галактики': {
        'rarity':'🔴Мифический','type':'passive',
        'effect':'+5 ко всем характ., +25% крит, блок 1 дебаффа/ход',
        'effect_key':'galaxy_heart','cooldown':0},
    '✨ Печать Звёздного Дождя': {
        'rarity':'🔴Мифический','type':'active',
        'effect':'🌟⏫(4) на 2 хода, +25% крит',
        'effect_key':'stardust_seal','cooldown':6},
    '☄️ Фрагмент Падающей Звезды': {
        'rarity':'🔴Мифический','type':'active',
        'effect':'сильный урон, ⚡Оглушение(2)+💔Уязвимость(3)',
        'effect_key':'meteor_fragment','cooldown':5},
    '👑 Корона Радужного Владыки': {
        'rarity':'🔴Мифический','type':'passive',
        'effect':'+4 ХАР, +4 УДЧ, +20% шанс эффектов',
        'effect_key':'rainbow_crown','cooldown':0},
    '🧿 Печать древних': {
        'rarity':'🟡Легендарный','type':'passive',
        'effect':'+2 ко всем (если все ≥8 — ещё +2)',
        'effect_key':'ancient_seal','cooldown':0},
}


# ─── Эффекты статусов ────────────────────────────────────────
STATUS_DISPLAY = {
    'weakness':      '⛓️‍💥⏬ Слабость',
    'stun':          '⚡ Оглушение',
    'sleep':         '💤 Усыпление',
    'poison':        '☠️ Яд',
    'vulnerability': '💔 Уязвимость',
    'curse':         '🌀 Наговор',
    'freeze':        '🧊 Заморозка',
    'burn':          '🔥 Горение',
    'blind':         '👁️‍🗨️ Слепота',
    'bleed':         '🩸 Кровотечение',
    'all_down':      '🌟⏬ Снижение всех характ.',
    'all_up':        '🌟⏫ Повышение всех характ.',
    'str_up':        '💪⏫ Повышение силы',
    'dex_up':        '🎯⏫ Повышение ловкости',
    'con_up':        '❤️⏫ Повышение телосложения',
    'int_up':        '💡⏫ Повышение интеллекта',
    'cha_up':        '👄⏫ Повышение харизмы',
    'lck_up':        '🍀⏫ Повышение удачи',
    'regen':         '🌿 Регенерация',
    'stealth':       '😶‍🌫️ Скрытность',
    'thorns':        '🌵 Шипы',
    'radioactive':   '☢️ Радиоактивный',
    'mind':          '🧠 Разум',
    'shield_buff':   '🛡️ Щит',
    'reflect':       '🪞 Отражение',
}

NEGATIVE_EFFECTS = ['weakness','stun','sleep','poison','vulnerability','curse','freeze','burn','blind','bleed','all_down']
POSITIVE_EFFECTS = ['all_up','str_up','dex_up','con_up','int_up','cha_up','lck_up','regen','stealth','thorns','radioactive','mind','shield_buff','reflect']


# ─── Данные гоблина ─────────────────────────────────────────
GOBLIN_DATA = {
    'name': '👹 Гоблин',
    'max_hp': 85,
    'speed': 5,
    'dex': 4,
    'kd': 5,
    'reward_xp': 50,
    'reward_money_range': (5, 20),
    'actions': [
        {
            'name': '⚔️ Обычная атака',
            'weight': 55,
            'key': 'basic_attack',
            'dmg_min': 4, 'dmg_max': 7,
            'can_crit': True,
        },
        {
            'name': '⚡ Быстрый выпад',
            'weight': 20,
            'key': 'quick_lunge',
            'dmg_min': 3, 'dmg_max': 5,
            'extra_crit_bonus': 20,
            'extra_turn_on_crit': True,
        },
        {
            'name': '🩸 Грязный приём',
            'weight': 15,
            'key': 'dirty_trick',
            'dmg_min': 2, 'dmg_max': 4,
            'apply_bleed': 1,
            'blind_chance': 30,
        },
        {
            'name': '🛡️ Осторожность',
            'weight': 10,
            'key': 'caution',
            'is_defend': True,
            'speed_bonus': 2,
        },
    ],
}


def pick_goblin_action():
    """Выбрать случайное действие гоблина по весам"""
    actions = GOBLIN_DATA['actions']
    weights = [a['weight'] for a in actions]
    return random.choices(actions, weights=weights, k=1)[0]


# ─── Вычисление базовых характеристик персонажа ──────────────
def calc_max_hp(cls, level, con, hp_items=0):
    h = CLASS_HP[cls]
    return h['base'] + level * h['per_level'] + con * 10 + hp_items

def calc_max_mana(cls, level, intel, cha, mana_items=0):
    m = CLASS_MANA[cls]
    return m['base'] + level * m['per_level'] + intel * 6 + cha * 3 + mana_items

def calc_kd(dex):
    return round(10 + 0.3 * dex, 1)

def calc_speed(cls, dex, lck, speed_items=0):
    base = CLASS_SPEED[cls]
    return round(base + dex * 1.0 + lck * 0.5 + speed_items, 1)
