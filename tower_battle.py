import psycopg2
import psycopg2.extras
import os
import json
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from tower import (
    get_conn, get_tower_char, calc_max_hp, calc_max_mp,
    WEAPONS, SPELLS, CONSUMABLES, CLASSES, SPELL_CLASSES,
    get_items, save_items, get_mod, safe
)

# ═══════════════════════════════════════════════════════════════
# ВРАГИ
# ═══════════════════════════════════════════════════════════════

ENEMIES = {
    "goblin":        {"name":"Гоблин",           "emoji":"👺","base_hp":20,"hp_s":5, "base_dmg":4, "dmg_s":1.2,"tier":1,
                      "abilities":[{"id":"attack","name":"Атака","w":70},{"id":"dodge","name":"Уклонение","w":30}]},
    "snake":         {"name":"Ядовитая Змея",     "emoji":"🐍","base_hp":15,"hp_s":4, "base_dmg":3, "dmg_s":1.1,"tier":1,
                      "abilities":[{"id":"poison_bite","name":"Укус","w":60},{"id":"sleep_venom","name":"Сонный яд","w":40}]},
    "boar":          {"name":"Кабан-Разрушитель", "emoji":"🐗","base_hp":30,"hp_s":6, "base_dmg":6, "dmg_s":1.5,"tier":2,
                      "abilities":[{"id":"ram","name":"Таран","w":50},{"id":"brutal","name":"Грубая атака","w":50}]},
    "bat":           {"name":"Летучая Тварь",     "emoji":"🦇","base_hp":18,"hp_s":3, "base_dmg":5, "dmg_s":1.3,"tier":1,
                      "abilities":[{"id":"attack","name":"Когти","w":75},{"id":"evade","name":"Уклонение","w":25}]},
    "skeleton":      {"name":"Скелет-Воин",       "emoji":"🧟","base_hp":25,"hp_s":5, "base_dmg":5, "dmg_s":1.4,"tier":2,
                      "abilities":[{"id":"attack","name":"Меч","w":60},{"id":"block","name":"Блок","w":40}]},
    "ghost":         {"name":"Призрачный Страж",  "emoji":"👻","base_hp":20,"hp_s":4, "base_dmg":4, "dmg_s":1.2,"tier":2,
                      "abilities":[{"id":"ethereal","name":"Эфирная атака","w":60},{"id":"illusion","name":"Иллюзия","w":40}]},
    "spider":        {"name":"Огромный Паук",     "emoji":"🕷️","base_hp":22,"hp_s":5, "base_dmg":5, "dmg_s":1.3,"tier":2,
                      "abilities":[{"id":"attack","name":"Когти","w":50},{"id":"web_poison","name":"Паучий яд","w":50}]},
    "dragonling":    {"name":"Дракончик",         "emoji":"🐉","base_hp":35,"hp_s":7, "base_dmg":7, "dmg_s":1.5,"tier":3,
                      "abilities":[{"id":"attack","name":"Когти","w":50},{"id":"fire_breath","name":"Огненное дыхание","w":50}]},
    "owl":           {"name":"Ночная Сова",       "emoji":"🦉","base_hp":18,"hp_s":3, "base_dmg":4, "dmg_s":1.2,"tier":1,
                      "abilities":[{"id":"attack","name":"Когти","w":60},{"id":"blind_hit","name":"Слепота","w":40}]},
    "wolf":          {"name":"Волк",              "emoji":"🐺","base_hp":25,"hp_s":5, "base_dmg":6, "dmg_s":1.4,"tier":2,
                      "abilities":[{"id":"attack","name":"Клыки","w":60},{"id":"speed_up","name":"Ускорение","w":40}]},
    "horse":         {"name":"Дикий Конь",        "emoji":"🐴","base_hp":28,"hp_s":5, "base_dmg":5, "dmg_s":1.3,"tier":2,
                      "abilities":[{"id":"ram","name":"Таран","w":60},{"id":"shock_hit","name":"Шок","w":40}]},
    "bear":          {"name":"Медведь",           "emoji":"🐻","base_hp":40,"hp_s":8, "base_dmg":8, "dmg_s":1.6,"tier":3,
                      "abilities":[{"id":"attack","name":"Лапы","w":60},{"id":"bleed_hit","name":"Кровотечение","w":40}]},
    "fire_dragon":   {"name":"Огнедышащий Дракон","emoji":"🐉","base_hp":50,"hp_s":9, "base_dmg":10,"dmg_s":2.0,"tier":4,
                      "abilities":[{"id":"attack","name":"Когти","w":40},{"id":"fire_breath3","name":"Огненное дыхание","w":60}]},
    "sea_horror":    {"name":"Морской Ужас",      "emoji":"🦈","base_hp":38,"hp_s":7, "base_dmg":9, "dmg_s":1.8,"tier":3,
                      "abilities":[{"id":"attack","name":"Хвост","w":50},{"id":"shock2","name":"Шок","w":50}]},
    "kraken":        {"name":"Кракен-малыш",      "emoji":"🦑","base_hp":30,"hp_s":6, "base_dmg":7, "dmg_s":1.5,"tier":3,
                      "abilities":[{"id":"attack","name":"Щупальца","w":60},{"id":"weakness_hit","name":"Слабость","w":40}]},
    "eagle":         {"name":"Орёл-охотник",      "emoji":"🦅","base_hp":22,"hp_s":4, "base_dmg":5, "dmg_s":1.3,"tier":2,
                      "abilities":[{"id":"attack","name":"Когти","w":60},{"id":"speed_up","name":"Ускорение","w":40}]},
    "krylан":        {"name":"Крылан",            "emoji":"🦇","base_hp":20,"hp_s":3, "base_dmg":4, "dmg_s":1.2,"tier":1,
                      "abilities":[{"id":"attack","name":"Укус","w":60},{"id":"blind_hit","name":"Слепота","w":40}]},
    "rat":           {"name":"Крысолов",          "emoji":"🐀","base_hp":15,"hp_s":3, "base_dmg":3, "dmg_s":1.1,"tier":1,
                      "abilities":[{"id":"attack","name":"Укус","w":60},{"id":"web_poison","name":"Яд","w":40}]},
    "croc":          {"name":"Аллигатор",         "emoji":"🐊","base_hp":35,"hp_s":7, "base_dmg":8, "dmg_s":1.6,"tier":3,
                      "abilities":[{"id":"attack","name":"Хватка","w":60},{"id":"bleed_hit","name":"Кровотечение","w":40}]},
    "deer":          {"name":"Олень-воин",        "emoji":"🦌","base_hp":20,"hp_s":4, "base_dmg":5, "dmg_s":1.3,"tier":2,
                      "abilities":[{"id":"attack","name":"Рога","w":60},{"id":"speed_up3","name":"Ускорение","w":40}]},
    "dino":          {"name":"Малый Дино",        "emoji":"🦖","base_hp":30,"hp_s":6, "base_dmg":7, "dmg_s":1.5,"tier":3,
                      "abilities":[{"id":"attack","name":"Хвост","w":60},{"id":"shock_hit","name":"Шок","w":40}]},
    "sea_spider":    {"name":"Морской Паук",      "emoji":"🐙","base_hp":28,"hp_s":6, "base_dmg":6, "dmg_s":1.4,"tier":3,
                      "abilities":[{"id":"attack","name":"Щупальца","w":50},{"id":"web_poison","name":"Яд","w":50}]},
    "grey_wolf":     {"name":"Серый Волк",        "emoji":"🐺","base_hp":25,"hp_s":5, "base_dmg":6, "dmg_s":1.4,"tier":2,
                      "abilities":[{"id":"attack","name":"Клыки","w":60},{"id":"speed_up","name":"Ускорение","w":40}]},
    "dragon_chick":  {"name":"Драконий Птенец",   "emoji":"🐉","base_hp":30,"hp_s":6, "base_dmg":7, "dmg_s":1.5,"tier":3,
                      "abilities":[{"id":"attack","name":"Когти","w":50},{"id":"fire_breath","name":"Огненное дыхание","w":50}]},
    "otter":         {"name":"Выдра-охотник",     "emoji":"🦦","base_hp":18,"hp_s":4, "base_dmg":4, "dmg_s":1.2,"tier":1,
                      "abilities":[{"id":"attack","name":"Укус","w":70},{"id":"speed_up","name":"Ускорение","w":30}]},
    "crab":          {"name":"Краб-боец",         "emoji":"🦀","base_hp":25,"hp_s":5, "base_dmg":5, "dmg_s":1.3,"tier":2,
                      "abilities":[{"id":"attack","name":"Клешни","w":60},{"id":"weakness_hit","name":"Слабость","w":40}]},
    "wise_owl":      {"name":"Сова-советник",     "emoji":"🦉","base_hp":22,"hp_s":4, "base_dmg":4, "dmg_s":1.2,"tier":2,
                      "abilities":[{"id":"attack","name":"Когти","w":60},{"id":"blind_hit","name":"Слепота","w":40}]},
}

# Тиры врагов по этажам
TIER_BY_FLOOR = {1: [1], 2: [1, 2], 3: [1, 2], 5: [2], 8: [2, 3],
                 12: [2, 3], 18: [3], 25: [3, 4], 35: [4]}

def get_enemy_pool(floor):
    max_tier = 1
    for f, tiers in sorted(TIER_BY_FLOOR.items()):
        if floor >= f:
            max_tier = max(tiers)
    pool = [k for k, v in ENEMIES.items() if v['tier'] <= max_tier]
    return pool

def spawn_enemy(floor):
    pool = get_enemy_pool(floor)
    key = random.choice(pool)
    e = ENEMIES[key]
    hp = int(e['base_hp'] + floor * e['hp_s'])
    dmg = round(e['base_dmg'] + floor * e['dmg_s'], 1)
    return key, hp, dmg

def roll_enemy_action(enemy_key, enemy_dmg):
    e = ENEMIES[enemy_key]
    abilities = e['abilities']
    weights = [a['w'] for a in abilities]
    ability = random.choices(abilities, weights=weights, k=1)[0]
    value = int(enemy_dmg)
    return {"id": ability['id'], "name": ability['name'], "value": value}

def action_announce(action):
    aid = action['id']
    val = action['value']
    texts = {
        "attack":       f"атаковать на {val}",
        "dodge":        "уклониться от следующей атаки",
        "evade":        "уклониться от следующей атаки",
        "ram":          f"таранить на {int(val*1.5)}",
        "brutal":       f"атаковать грубо на {val} (снижает Телосложение)",
        "poison_bite":  f"укусить на {val} + яд",
        "sleep_venom":  f"применить сонный яд",
        "block":        "заблокировать следующий удар",
        "ethereal":     f"эфирно атаковать на {val} (игнор брони)",
        "illusion":     "создать иллюзию (шанс промаха у тебя)",
        "web_poison":   f"атаковать на {val} + яд",
        "fire_breath":  f"выдохнуть огонь на {val} + ожог",
        "fire_breath3": f"выдохнуть огонь на {val} + сильный ожог",
        "blind_hit":    f"атаковать на {val} + слепота",
        "speed_up":     f"ускориться и атаковать на {val}",
        "speed_up3":    f"ускориться и атаковать на {int(val*1.2)}",
        "shock_hit":    f"атаковать на {val} + шок",
        "shock2":       f"атаковать на {val} + шок (2 хода)",
        "bleed_hit":    f"атаковать на {val} + кровотечение",
        "weakness_hit": f"атаковать на {val} + слабость",
    }
    return texts.get(aid, f"атаковать на {val}")

# ═══════════════════════════════════════════════════════════════
# БАЗА ДАННЫХ
# ═══════════════════════════════════════════════════════════════

def init_battle_table():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tower_battles (
            user_id     BIGINT PRIMARY KEY,
            state       TEXT DEFAULT '{}'
        )
    ''')
    conn.commit()
    conn.close()
    print("Таблица tower_battles инициализирована!")

def get_battle(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT state FROM tower_battles WHERE user_id=%s', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        try: return json.loads(row[0])
        except: return None
    return None

def save_battle(user_id, state):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO tower_battles (user_id, state) VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE SET state=EXCLUDED.state
    ''', (user_id, json.dumps(state)))
    conn.commit()
    conn.close()

def delete_battle(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM tower_battles WHERE user_id=%s', (user_id,))
    conn.commit()
    conn.close()

def is_in_battle(user_id):
    return get_battle(user_id) is not None

# ═══════════════════════════════════════════════════════════════
# РАСЧЁТ УРОНА И СТАТУСОВ
# ═══════════════════════════════════════════════════════════════

def calc_player_attack(char, state):
    """Урон игрока оружием с учётом модификаторов"""
    w_key = char.get('weapon')
    w = WEAPONS.get(w_key)
    if w:
        dmg = w['damage'](char)
    else:
        dmg = 3 + get_mod(char['strength'])

    # Слабость: -50% урона
    if 'weakness' in state.get('player_statuses', {}):
        dmg = dmg // 2

    return max(1, int(dmg))

def calc_spell_damage(char, spell_key):
    sp = SPELLS.get(spell_key)
    if not sp or not sp.get('damage'):
        return 0
    return int(sp['damage'](char['intellect']))

def apply_player_damage_to_enemy(state, dmg):
    """Урон по врагу с учётом уклонения/блока врага"""
    if state.get('enemy_dodging'):
        state['enemy_dodging'] = False
        return 0, "уклонился"
    if state.get('enemy_blocking'):
        dmg = dmg // 2
        state['enemy_blocking'] = False
        return dmg, f"заблокировал (урон снижен до {dmg})"
    # Призрак-иллюзия: 20% промах
    if state.get('player_blind') or 'blind' in state.get('player_statuses', {}):
        if random.random() < 0.5:
            return 0, "промахнулся (слепота)"
    state['enemy_hp'] = max(0, state['enemy_hp'] - dmg)
    return dmg, None

def apply_enemy_damage_to_player(char, state, dmg, ignore_armor=False):
    """Урон по игроку с учётом защиты"""
    if state.get('player_defending'):
        dmg = dmg // 2
        state['player_defending'] = False

    # Слепота врага: 50% промах
    enemy_statuses = state.get('enemy_statuses', {})
    if 'blind' in enemy_statuses:
        if random.random() < 0.5:
            return 0
    # Шок врага: не атакует
    if 'shock' in enemy_statuses:
        return 0

    new_hp = char['hp'] - dmg
    # Второе дыхание
    p_st = state.get('player_statuses', {})
    if new_hp <= 0 and 'second_wind' in p_st:
        new_hp = 1
        del p_st['second_wind']
        state['player_statuses'] = p_st

    return max(0, dmg), new_hp

def process_end_of_turn(char, state):
    """Обработка статусов в конце хода. Возвращает (лог, новый hp игрока, новый hp врага)"""
    log = []
    player_hp = char['hp']
    enemy_hp = state['enemy_hp']

    # --- Статусы ИГРОКА ---
    p_st = state.get('player_statuses', {}).copy()
    if 'burn' in p_st:
        dmg = random.randint(5, 10)
        player_hp -= dmg
        log.append(f"🔥 Ожог наносит {dmg} урона тебе")
        p_st['burn'] -= 1
        if p_st['burn'] <= 0: del p_st['burn']
    if 'poison' in p_st:
        dmg = 10 * p_st['poison']
        player_hp -= dmg
        log.append(f"☠️ Яд наносит {dmg} урона тебе")
        p_st['poison'] -= 1
        if p_st['poison'] <= 0: del p_st['poison']
    if 'regen' in p_st:
        heal = 10 * p_st['regen']
        max_hp = calc_max_hp(char)
        player_hp = min(max_hp, player_hp + heal)
        log.append(f"🌿 Регенерация восстанавливает {heal} HP")
        p_st['regen'] -= 1
        if p_st['regen'] <= 0: del p_st['regen']
    # Тик остальных статусов игрока
    for st in ['cold','shock','weakness','blind','fear','sleep','bleed']:
        if st in p_st:
            if st == 'bleed':
                dmg = random.randint(8, 10)
                player_hp -= dmg
                log.append(f"🩸 Кровотечение наносит {dmg} урона")
            p_st[st] -= 1
            if p_st[st] <= 0: del p_st[st]
    state['player_statuses'] = p_st

    # --- Статусы ВРАГА ---
    e_st = state.get('enemy_statuses', {}).copy()
    if 'burn' in e_st:
        dmg = random.randint(5, 10)
        enemy_hp -= dmg
        log.append(f"🔥 Ожог наносит {dmg} урона врагу")
        e_st['burn'] -= 1
        if e_st['burn'] <= 0: del e_st['burn']
    if 'poison' in e_st:
        dmg = 10 * e_st['poison']
        enemy_hp -= dmg
        log.append(f"☠️ Яд наносит {dmg} урона врагу")
        e_st['poison'] -= 1
        if e_st['poison'] <= 0: del e_st['poison']
    if 'bleed' in e_st:
        dmg = random.randint(8, 10)
        enemy_hp -= dmg
        log.append(f"🩸 Кровотечение наносит {dmg} урона врагу")
        e_st['bleed'] -= 1
        if e_st['bleed'] <= 0: del e_st['bleed']
    for st in ['cold','shock','weakness','blind','fear','sleep']:
        if st in e_st:
            e_st[st] -= 1
            if e_st[st] <= 0: del e_st[st]
    state['enemy_statuses'] = e_st

    return log, max(0, player_hp), max(0, enemy_hp)

# ═══════════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════════

STATUS_EMOJI = {
    'burn':'🔥','cold':'❄️','shock':'💫','weakness':'⛓️‍💥','poison':'☠️',
    'blind':'👁️‍🗨️','regen':'🌿','fear':'😱','sleep':'💤','bleed':'🩸','second_wind':'❤️‍🔥',
    'barrier':'🛡️'
}
STATUS_NAME = {
    'burn':'Ожог','cold':'Холод','shock':'Шок','weakness':'Слабость',
    'poison':'Яд','blind':'Слепота','regen':'Регенерация','fear':'Страх',
    'sleep':'Сон','bleed':'Кровотечение','second_wind':'Второе дыхание',
    'barrier':'Барьер'
}

def format_statuses(statuses):
    if not statuses: return ""
    parts = []
    for k, v in statuses.items():
        em = STATUS_EMOJI.get(k, '')
        nm = STATUS_NAME.get(k, k)
        if isinstance(v, int) and v > 1:
            parts.append(f"{em}{nm}×{v}")
        else:
            parts.append(f"{em}{nm}")
    return "  ".join(parts)

def battle_text(char, state, log_lines=None):
    floor = state['floor']
    ekey = state['enemy_key']
    e = ENEMIES[ekey]
    ehp = state['enemy_hp']
    emaxhp = state['enemy_max_hp']
    e_st = state.get('enemy_statuses', {})
    p_st = state.get('player_statuses', {})
    max_hp = calc_max_hp(char)
    max_mp = calc_max_mp(char)
    action = state.get('next_enemy_action', {})

    enemy_status_str = format_statuses(e_st)
    player_status_str = format_statuses(p_st)

    hp_bar = hp_bar_str(ehp, emaxhp)

    text = f"— 🏯 ЭТАЖ {floor} 🏯 —\n\n"
    text += f"– {e['emoji']} {e['name']} –\n"
    text += f"🫀 ХП: {ehp}/{emaxhp}  {hp_bar}\n"
    if enemy_status_str:
        text += f"{enemy_status_str}\n"
    text += "\n"

    if action:
        text += f"_{e['emoji']} Собирается: {action_announce(action)}_\n\n"

    text += f"{'─'*20}\n\n"
    text += f"– ⚔️ {safe(char['char_name'])} –\n"
    text += f"❤️ ХП: {char['hp']}/{max_hp}\n"
    text += f"⚡ Мана: {char['mp']}/{max_mp}\n"
    if player_status_str:
        text += f"{player_status_str}\n"

    if log_lines:
        text += f"\n{'─'*20}\n"
        for line in log_lines[-5:]:
            text += f"• {line}\n"

    return text

def hp_bar_str(hp, max_hp):
    filled = round((hp / max_hp) * 10) if max_hp > 0 else 0
    return "█" * filled + "░" * (10 - filled)

def battle_keyboard(char, state):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⚔️ Атаковать",    callback_data="tb_attack"),
        InlineKeyboardButton("🛡️ Защититься",  callback_data="tb_defend"),
        InlineKeyboardButton("🎒 Рюкзак",       callback_data="tb_bag"),
        InlineKeyboardButton("📜 Навык",         callback_data="tb_skill"),
    )
    if char.get('class_key') in SPELL_CLASSES:
        markup.add(InlineKeyboardButton("💫 Заклинания", callback_data="tb_spells"))
    markup.add(InlineKeyboardButton("❌ Закончить", callback_data="tb_flee"))
    return markup

def victory_keyboard(floor):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⬆️ Следующий этаж", callback_data="tb_next_floor"),
        InlineKeyboardButton("🚪 Покинуть башню",  callback_data="tb_exit"),
    )
    return markup

def reward_items(floor):
    """Случайные награды за этаж"""
    pool = [
        ("health_potion", 40), ("mana_potion", 25), ("bomb", 15),
        ("arrows", 20), ("regen_small", 15), ("ice_flask", 10),
        ("smoke_bomb", 10), ("str_potion", 8), ("agi_potion", 8),
        ("int_potion", 8), ("speed_potion", 8), ("poison_bomb", 10),
        ("big_health_potion", max(1, floor - 5)), ("big_mana_potion", max(1, floor - 8)),
    ]
    keys = [p[0] for p in pool]
    weights = [p[1] for p in pool]
    count = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
    chosen = {}
    for _ in range(count):
        item = random.choices(keys, weights=weights)[0]
        amt = random.randint(1, 3) if item == 'arrows' else 1
        chosen[item] = chosen.get(item, 0) + amt
    return chosen

def exp_for_floor(floor, enemy_key):
    base = 20 + floor * 5
    tier = ENEMIES[enemy_key]['tier']
    return base * tier

# ═══════════════════════════════════════════════════════════════
# ПРИМЕНИТЬ СПОСОБНОСТЬ ВРАГА
# ═══════════════════════════════════════════════════════════════

def apply_enemy_ability(char, state, action):
    """Выполнить действие врага. Возвращает (лог, новый hp игрока)"""
    aid = action['id']
    val = action['value']
    player_hp = char['hp']
    p_st = state.get('player_statuses', {})
    e_st = state.get('enemy_statuses', {})
    log = []

    # Если у врага шок/страх/сон — пропускает ход
    if 'shock' in e_st or 'fear' in e_st or 'sleep' in e_st:
        name = 'shock' if 'shock' in e_st else ('fear' if 'fear' in e_st else 'sleep')
        em = STATUS_EMOJI.get(name, '')
        log.append(f"Враг пропускает ход ({em})")
        return log, player_hp

    # Обработка действий
    if aid == 'attack':
        dmg, nhp = apply_enemy_damage_to_player(char, state, val)
        if dmg:
            player_hp = nhp
            log.append(f"Враг атакует — {dmg} урона")
        else:
            log.append("Враг атакует — промах!")

    elif aid in ('dodge', 'evade'):
        state['enemy_dodging'] = True
        log.append("Враг готовится уклониться от твоей атаки")

    elif aid == 'ram':
        big_dmg = int(val * 1.5)
        dmg, nhp = apply_enemy_damage_to_player(char, state, big_dmg)
        if dmg:
            player_hp = nhp
            log.append(f"⚡ Таран! — {dmg} урона")
        else:
            log.append("Таран — промах!")

    elif aid == 'brutal':
        dmg, nhp = apply_enemy_damage_to_player(char, state, val)
        if dmg:
            player_hp = nhp
            log.append(f"Грубая атака — {dmg} урона")
        # Временно снижаем телосложение (просто доп урон)
        state['player_constitution_debuff'] = state.get('player_constitution_debuff', 0) + 2

    elif aid == 'poison_bite':
        dmg, nhp = apply_enemy_damage_to_player(char, state, val)
        if dmg:
            player_hp = nhp
        p_st['poison'] = p_st.get('poison', 0) + 2
        log.append(f"Укус — {dmg} урона + ☠️Яд")

    elif aid == 'sleep_venom':
        if random.random() < 0.15:
            p_st['sleep'] = 2
            log.append("💤 Сонный яд — ты засыпаешь!")
        else:
            dmg, nhp = apply_enemy_damage_to_player(char, state, val)
            if dmg: player_hp = nhp
            log.append(f"Укус — {dmg} урона (яд не подействовал)")

    elif aid == 'block':
        state['enemy_blocking'] = True
        log.append("🛡️ Враг блокирует следующий удар")

    elif aid == 'ethereal':
        # Игнорирует защиту
        old_def = state.get('player_defending')
        state['player_defending'] = False
        dmg, nhp = apply_enemy_damage_to_player(char, state, val, ignore_armor=True)
        if old_def: state['player_defending'] = old_def
        if dmg:
            player_hp = nhp
            log.append(f"👻 Эфирная атака — {dmg} урона (игнор защиты)")
        else:
            log.append("Эфирная атака — промах!")

    elif aid == 'illusion':
        state['player_blind'] = True
        log.append("👁️ Иллюзия! Твоя следующая атака может промахнуться")

    elif aid == 'web_poison':
        dmg, nhp = apply_enemy_damage_to_player(char, state, val)
        if dmg: player_hp = nhp
        p_st['poison'] = p_st.get('poison', 0) + 2
        log.append(f"☠️ Яд атака — {dmg} урона + Яд(2)")

    elif aid == 'fire_breath':
        dmg, nhp = apply_enemy_damage_to_player(char, state, val)
        if dmg: player_hp = nhp
        p_st['burn'] = max(p_st.get('burn', 0), 2)
        log.append(f"🔥 Огненное дыхание — {dmg} урона + Ожог(2)")

    elif aid == 'fire_breath3':
        dmg, nhp = apply_enemy_damage_to_player(char, state, val)
        if dmg: player_hp = nhp
        p_st['burn'] = max(p_st.get('burn', 0), 3)
        log.append(f"🔥 Огонь — {dmg} урона + Ожог(3)")

    elif aid == 'blind_hit':
        dmg, nhp = apply_enemy_damage_to_player(char, state, val)
        if dmg: player_hp = nhp
        p_st['blind'] = max(p_st.get('blind', 0), 1)
        log.append(f"👁️ Слепящий удар — {dmg} урона + Слепота")

    elif aid in ('speed_up', 'speed_up3'):
        mult = 1.2 if aid == 'speed_up3' else 1.0
        bonus_dmg = int(val * mult)
        dmg, nhp = apply_enemy_damage_to_player(char, state, bonus_dmg)
        if dmg: player_hp = nhp
        log.append(f"🏃 Ускорение + атака — {dmg} урона")

    elif aid == 'shock_hit':
        dmg, nhp = apply_enemy_damage_to_player(char, state, val)
        if dmg: player_hp = nhp
        p_st['shock'] = max(p_st.get('shock', 0), 1)
        log.append(f"💫 Шок атака — {dmg} урона + Шок")

    elif aid == 'shock2':
        dmg, nhp = apply_enemy_damage_to_player(char, state, val)
        if dmg: player_hp = nhp
        p_st['shock'] = max(p_st.get('shock', 0), 2)
        log.append(f"💫 Шок атака — {dmg} урона + Шок(2)")

    elif aid == 'bleed_hit':
        dmg, nhp = apply_enemy_damage_to_player(char, state, val)
        if dmg: player_hp = nhp
        p_st['bleed'] = max(p_st.get('bleed', 0), 2)
        log.append(f"🩸 Кровотечение — {dmg} урона + Кровотечение")

    elif aid == 'weakness_hit':
        dmg, nhp = apply_enemy_damage_to_player(char, state, val)
        if dmg: player_hp = nhp
        p_st['weakness'] = max(p_st.get('weakness', 0), 1)
        log.append(f"⛓️ Слабость — {dmg} урона + Слабость")

    state['player_statuses'] = p_st
    return log, player_hp

# ═══════════════════════════════════════════════════════════════
# ПРИМЕНИТЬ ОРУЖЕЙНЫЙ ЭФФЕКТ
# ═══════════════════════════════════════════════════════════════

def apply_weapon_effect(char, state, weapon_key):
    """Делегирует в data-driven версию из tower_treasury."""
    try:
        from tower_treasury import apply_weapon_effect_v2
        log, _ = apply_weapon_effect_v2(char, state, weapon_key)
        return log
    except Exception:
        return []

# ═══════════════════════════════════════════════════════════════
# ОБНОВЛЕНИЕ HP В БД
# ═══════════════════════════════════════════════════════════════

def update_char_hp_mp(user_id, hp, mp=None):
    conn = get_conn()
    c = conn.cursor()
    if mp is not None:
        c.execute('UPDATE tower_chars SET hp=%s, mp=%s WHERE user_id=%s', (hp, mp, user_id))
    else:
        c.execute('UPDATE tower_chars SET hp=%s WHERE user_id=%s', (hp, user_id))
    conn.commit()
    conn.close()

def update_char_exp_floor(user_id, exp_gain, floor):
    conn = get_conn()
    c = conn.cursor()
    # Получаем текущий exp и уровень
    c.execute('SELECT exp, level, stat_points, best_floor FROM tower_chars WHERE user_id=%s', (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return 0, False
    cur_exp, lvl, pts, best = row
    new_exp = cur_exp + exp_gain
    leveled = False
    lvl_up_count = 0
    while new_exp >= lvl * 100:
        new_exp -= lvl * 100
        lvl += 1
        pts += 3  # 3 ОХ за уровень
        lvl_up_count += 1
        leveled = True
    new_best = max(best, floor)
    c.execute('UPDATE tower_chars SET exp=%s, level=%s, stat_points=%s, best_floor=%s WHERE user_id=%s',
              (new_exp, lvl, pts, new_best, user_id))
    conn.commit()
    conn.close()
    return lvl_up_count, leveled

# ═══════════════════════════════════════════════════════════════
# ОСНОВНОЙ ПОТОК БОЕВЫХ ХЭНДЛЕРОВ
# ═══════════════════════════════════════════════════════════════

def send_battle(bot, chat_id, user_id, char, state, log_lines=None, msg_id_to_delete=None):
    """Удаляет старое боевое сообщение и отправляет новое"""
    if msg_id_to_delete:
        try: bot.delete_message(chat_id, msg_id_to_delete)
        except: pass
    msg = bot.send_message(
        chat_id,
        battle_text(char, state, log_lines),
        reply_markup=battle_keyboard(char, state),
        parse_mode='Markdown'
    )
    state['last_msg_id'] = msg.message_id
    save_battle(user_id, state)
    return msg

def register_tower_battle(bot):

    # ── Блокировка команд во время битвы ──────────────────────
    BLOCKED_COMMANDS = ['/casino', '/garden', '/fishing', '/daily', '/shop']

    @bot.message_handler(func=lambda msg: (
        msg.text and any(msg.text.startswith(cmd) for cmd in BLOCKED_COMMANDS)
        and is_in_battle(msg.from_user.id)
    ))
    def block_during_battle(message):
        bot.send_message(message.chat.id,
            "⚔️ Ты сейчас в *Башне Хаоса*\\!\n"
            "Используй /tower чтобы вернуться в битву\\.",
            parse_mode='MarkdownV2')

    # ── Начать башню ──────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tower_start')
    def cb_tower_start(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        char = get_tower_char(user_id)
        if not char: return

        state = get_battle(user_id)

        # Если есть активная битва с живым врагом — возобновляем
        if state and state.get('enemy_hp', 0) > 0 and 'enemy_key' in state:
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            send_battle(bot, call.message.chat.id, user_id, char, state)
            return

        # Иначе — очищаем устаревшее состояние (победа, событие, сокровищница)
        if state:
            delete_battle(user_id)

        # Начинаем с этажа 1
        floor = 1
        ekey, ehp, edmg = spawn_enemy(floor)
        e = ENEMIES[ekey]
        state = {
            'floor': floor,
            'enemy_key': ekey,
            'enemy_hp': ehp,
            'enemy_max_hp': ehp,
            'enemy_base_dmg': edmg,
            'enemy_statuses': {},
            'player_statuses': {},
            'player_defending': False,
            'enemy_dodging': False,
            'enemy_blocking': False,
            'player_blind': False,
            'next_enemy_action': roll_enemy_action(ekey, edmg),
            'chat_id': call.message.chat.id,
            'last_msg_id': None,
        }
        save_battle(user_id, state)

        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

        send_battle(bot, call.message.chat.id, user_id, char, state,
                    log_lines=[f"⚔️ Ты входишь на этаж {floor}! Встречаешь {e['emoji']} {e['name']}"])

    # ── АТАКОВАТЬ ─────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tb_attack')
    def cb_tb_attack(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        char = get_tower_char(user_id)
        state = get_battle(user_id)
        if not char or not state: return

        log = []
        p_st = state.get('player_statuses', {})

        # Проверяем статусы игрока блокирующие атаку
        if 'shock' in p_st:
            log.append("💫 Шок! Ты пропускаешь ход")
            p_st['shock'] -= 1
            if p_st['shock'] <= 0: del p_st['shock']
            state['player_statuses'] = p_st
        elif 'sleep' in p_st:
            log.append("💤 Ты спишь и пропускаешь ход")
        elif 'fear' in p_st:
            log.append("😱 Страх! Ты не можешь атаковать")
        else:
            # Считаем урон игрока
            dmg = calc_player_attack(char, state)
            state['_double_strike'] = False

            # Эффект оружия
            w_log = apply_weapon_effect(char, state, char.get('weapon'))
            actual_dmg, miss_reason = apply_player_damage_to_enemy(state, dmg)

            if miss_reason:
                log.append(f"❌ Атака — {miss_reason}!")
            else:
                log.append(f"⚔️ Атака — {actual_dmg} урона врагу")
            log.extend(w_log)

            # Двойной удар
            if state.get('_double_strike'):
                dmg2 = calc_player_attack(char, state)
                actual_dmg2, _ = apply_player_damage_to_enemy(state, dmg2)
                log.append(f"⚔️ Второй удар — {actual_dmg2} урона!")

        state['player_blind'] = False

        # Проверяем смерть врага
        if state['enemy_hp'] <= 0:
            _handle_victory(bot, call.message.chat.id, user_id, char, state, log)
            return

        # Ход врага
        action = state.get('next_enemy_action', {})
        enemy_log, new_player_hp = apply_enemy_ability(char, state, action)
        log.extend(enemy_log)

        # Тики статусов
        tick_log, new_player_hp2, new_enemy_hp = process_end_of_turn(
            {**char, 'hp': new_player_hp}, state)
        log.extend(tick_log)
        state['enemy_hp'] = max(0, new_enemy_hp)

        update_char_hp_mp(user_id, max(0, new_player_hp2))
        char = get_tower_char(user_id)

        if char['hp'] <= 0 or state['enemy_hp'] <= 0:
            if state['enemy_hp'] <= 0:
                _handle_victory(bot, call.message.chat.id, user_id, char, state, log)
            else:
                _handle_defeat(bot, call.message.chat.id, user_id, char, state, log)
            return

        # Следующий ход врага
        state['next_enemy_action'] = roll_enemy_action(state['enemy_key'], state['enemy_base_dmg'])
        send_battle(bot, call.message.chat.id, user_id, char, state, log,
                    msg_id_to_delete=state.get('last_msg_id'))

    # ── ЗАЩИТИТЬСЯ ────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tb_defend')
    def cb_tb_defend(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        char = get_tower_char(user_id)
        state = get_battle(user_id)
        if not char or not state: return

        log = ["🛡️ Ты принимаешь защитную стойку (урон снижен вдвое)"]
        state['player_defending'] = True

        # Ход врага
        action = state.get('next_enemy_action', {})
        enemy_log, new_player_hp = apply_enemy_ability(char, state, action)
        log.extend(enemy_log)

        tick_log, new_player_hp2, new_enemy_hp = process_end_of_turn(
            {**char, 'hp': new_player_hp}, state)
        log.extend(tick_log)
        state['enemy_hp'] = max(0, new_enemy_hp)

        update_char_hp_mp(user_id, max(0, new_player_hp2))
        char = get_tower_char(user_id)

        if char['hp'] <= 0 or state['enemy_hp'] <= 0:
            if state['enemy_hp'] <= 0:
                _handle_victory(bot, call.message.chat.id, user_id, char, state, log)
            else:
                _handle_defeat(bot, call.message.chat.id, user_id, char, state, log)
            return

        state['next_enemy_action'] = roll_enemy_action(state['enemy_key'], state['enemy_base_dmg'])
        send_battle(bot, call.message.chat.id, user_id, char, state, log,
                    msg_id_to_delete=state.get('last_msg_id'))

    # ── ЗАКЛИНАНИЯ В БОЮ ──────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tb_spells')
    def cb_tb_spells(call):
        bot.answer_callback_query(call.id)
        char = get_tower_char(call.from_user.id)
        state = get_battle(call.from_user.id)
        if not char or not state: return

        slots = [char.get('spell_slot_1'), char.get('spell_slot_2'), char.get('spell_slot_3')]
        markup = InlineKeyboardMarkup(row_width=1)
        for i, key in enumerate(slots, 1):
            if key and key in SPELLS:
                sp = SPELLS[key]
                can_cast = char['mp'] >= sp['mana']
                prefix = "✅ " if can_cast else "❌ "
                intel = char['intellect']
                dmg_str = f" | 💢{int(sp['damage'](intel))}" if sp.get('damage') else ""
                markup.add(InlineKeyboardButton(
                    f"{prefix}{sp['emoji']} {sp['name']} | ⚡{sp['mana']}{dmg_str}",
                    callback_data=f"tb_cast_{key}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tb_back_to_battle"))
        bot.send_message(call.message.chat.id, "💫 *Выбери заклинание:*",
                         reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tb_cast_'))
    def cb_tb_cast(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        spell_key = call.data.replace('tb_cast_', '')
        char = get_tower_char(user_id)
        state = get_battle(user_id)
        if not char or not state or spell_key not in SPELLS: return

        sp = SPELLS[spell_key]
        log = []

        if char['mp'] < sp['mana']:
            bot.send_message(call.message.chat.id,
                f"❌ Недостаточно маны! Нужно {sp['mana']} ⚡, у тебя {char['mp']}")
            return

        # Потратить ману
        new_mp = char['mp'] - sp['mana']
        update_char_hp_mp(user_id, char['hp'], new_mp)
        char = get_tower_char(user_id)

        # Урон заклинания
        e_st = state.get('enemy_statuses', {})
        p_st = state.get('player_statuses', {})

        if sp.get('damage'):
            dmg = int(sp['damage'](char['intellect']))
            # Бонус от оружия (посохи)
            spell_boost = state.get('weapon_spell_boost', 0.0)
            if spell_boost > 0:
                dmg = int(dmg * (1 + spell_boost))
            # Слабость снижает урон
            if 'weakness' in p_st: dmg = dmg // 2
            actual, miss = apply_player_damage_to_enemy(state, dmg)
            if miss:
                log.append(f"{sp['emoji']} {sp['name']} — {miss}!")
            else:
                log.append(f"{sp['emoji']} {sp['name']} — {actual} урона!")

        # Эффект заклинания
        effect = sp.get('effect')
        if effect:
            eff_key, eff_val = effect
            chance = sp.get('effect_chance', 1.0)
            target = sp.get('target', 'enemy')
            if random.random() < chance:
                if target == 'self':
                    p_st[eff_key] = p_st.get(eff_key, 0) + (eff_val if eff_val > 0 else 1)
                    em = STATUS_EMOJI.get(eff_key, '')
                    log.append(f"{em} Получен статус: {eff_key}")
                elif eff_key == 'barrier':
                    bval = sp.get('barrier_val', lambda i: 10)(char['intellect'])
                    state['player_barrier'] = bval
                    log.append(f"🛡️ Магический барьер: -{bval} урона")
                else:
                    e_st[eff_key] = e_st.get(eff_key, 0) + (eff_val if eff_val > 0 else 1)
                    em = STATUS_EMOJI.get(eff_key, '')
                    log.append(f"{em} Враг получает: {eff_key}")

        state['enemy_statuses'] = e_st
        state['player_statuses'] = p_st

        # Проверяем смерть врага
        if state['enemy_hp'] <= 0:
            _handle_victory(bot, call.message.chat.id, user_id, char, state, log)
            return

        # Ход врага
        action = state.get('next_enemy_action', {})
        enemy_log, new_player_hp = apply_enemy_ability(char, state, action)
        log.extend(enemy_log)

        tick_log, new_player_hp2, new_enemy_hp = process_end_of_turn(
            {**char, 'hp': new_player_hp}, state)
        log.extend(tick_log)
        state['enemy_hp'] = max(0, new_enemy_hp)

        update_char_hp_mp(user_id, max(0, new_player_hp2))
        char = get_tower_char(user_id)

        if char['hp'] <= 0 or state['enemy_hp'] <= 0:
            if state['enemy_hp'] <= 0:
                _handle_victory(bot, call.message.chat.id, user_id, char, state, log)
            else:
                _handle_defeat(bot, call.message.chat.id, user_id, char, state, log)
            return

        state['next_enemy_action'] = roll_enemy_action(state['enemy_key'], state['enemy_base_dmg'])
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        send_battle(bot, call.message.chat.id, user_id, char, state, log,
                    msg_id_to_delete=state.get('last_msg_id'))

    # ── РЮКЗАК В БОЮ ──────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tb_bag')
    def cb_tb_bag(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        char = get_tower_char(user_id)
        state = get_battle(user_id)
        if not char or not state: return

        items = get_items(char)
        usable = {k: v for k, v in items.items()
                  if CONSUMABLES.get(k, {}).get('type') in ('consumable', 'scroll', 'ammo')}

        if not usable:
            bot.answer_callback_query(call.id, "🎒 Нет расходников!", show_alert=True)
            return

        markup = InlineKeyboardMarkup(row_width=1)
        for key, count in usable.items():
            cd = CONSUMABLES[key]
            label = f"{cd['emoji']} {cd['name']}"
            if count > 1: label += f" ×{count}"
            markup.add(InlineKeyboardButton(label, callback_data=f"tb_use_{key}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="tb_back_to_battle"))
        bot.send_message(call.message.chat.id, "🎒 *Выбери предмет:*",
                         reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tb_use_'))
    def cb_tb_use(call):
        bot.answer_callback_query(call.id)
        ikey = call.data.replace('tb_use_', '')
        user_id = call.from_user.id
        char = get_tower_char(user_id)
        state = get_battle(user_id)
        if not char or not state: return

        items = get_items(char)
        if items.get(ikey, 0) <= 0:
            bot.answer_callback_query(call.id, "❌ Предмет закончился!", show_alert=True)
            return

        cd = CONSUMABLES.get(ikey)
        if not cd: return

        log = []
        max_hp = calc_max_hp(char)
        max_mp = calc_max_mp(char)
        new_hp, new_mp = char['hp'], char['mp']
        p_st = state.get('player_statuses', {})

        if ikey in ('health_potion', 'scroll_heal'):
            h = random.randint(25, 50) if ikey == 'health_potion' else random.randint(30, 50)
            new_hp = min(max_hp, new_hp + h)
            log.append(f"❤️ Зелье восстанавливает {h} HP")
        elif ikey == 'big_health_potion':
            h = random.randint(75, 100)
            new_hp = min(max_hp, new_hp + h)
            log.append(f"❤️ Большое зелье восстанавливает {h} HP")
        elif ikey in ('mana_potion', 'scroll_mana'):
            m = random.randint(15, 30) if ikey == 'mana_potion' else random.randint(20, 40)
            new_mp = min(max_mp, new_mp + m)
            log.append(f"⚡ Зелье восстанавливает {m} MP")
        elif ikey == 'big_mana_potion':
            m = random.randint(50, 70)
            new_mp = min(max_mp, new_mp + m)
            log.append(f"⚡ Большое зелье восстанавливает {m} MP")
        elif ikey == 'bomb':
            dmg = random.randint(10, 20)
            apply_player_damage_to_enemy(state, dmg)
            log.append(f"💣 Бомба — {dmg} урона врагу!")
            if random.random() < 0.2:
                state['enemy_statuses']['burn'] = max(state['enemy_statuses'].get('burn', 0), 2)
                log.append("🔥 Взрыв поджигает врага!")
        elif ikey == 'ice_flask':
            dmg = random.randint(5, 10)
            apply_player_damage_to_enemy(state, dmg)
            state['enemy_statuses']['cold'] = max(state['enemy_statuses'].get('cold', 0), 1)
            log.append(f"❄️ Ледяной флакон — {dmg} урона + холод!")
        elif ikey == 'smoke_bomb':
            state['enemy_statuses']['blind'] = max(state['enemy_statuses'].get('blind', 0), 2)
            log.append("🌫️ Дымовая бомба — враг ослеплён на 2 хода!")
        elif ikey == 'poison_bomb':
            state['enemy_statuses']['poison'] = state['enemy_statuses'].get('poison', 0) + 5
            log.append("☠️ Ядовитая бомба — враг получает 5 стаков яда!")
        elif ikey == 'regen_small':
            p_st['regen'] = max(p_st.get('regen', 0), 2)
            log.append("🌿 Малый эликсир — Регенерация(2)")
        elif ikey == 'regen_big':
            p_st['regen'] = max(p_st.get('regen', 0), 5)
            log.append("🌿🌿 Большой эликсир — Регенерация(5)")
        elif ikey == 'second_wind_potion':
            p_st['second_wind'] = 1
            log.append("❤️‍🔥 Второе дыхание активировано!")
        elif ikey == 'str_potion':
            p_st['str_buff'] = p_st.get('str_buff', 0) + 2
            log.append("💪 Зелье силы +2 к Силе!")
        elif ikey == 'speed_potion':
            p_st['spd_buff'] = p_st.get('spd_buff', 0) + 3
            log.append("🏃 Зелье скорости +3!")
        elif ikey == 'scroll_fireball':
            dmg = random.randint(20, 35)
            apply_player_damage_to_enemy(state, dmg)
            state['enemy_statuses']['burn'] = max(state['enemy_statuses'].get('burn', 0), 3)
            log.append(f"🔥 Огненный шар — {dmg} урона + Ожог(3)!")
        elif ikey == 'scroll_ice_arrow':
            dmg = random.randint(15, 25)
            apply_player_damage_to_enemy(state, dmg)
            state['enemy_statuses']['cold'] = max(state['enemy_statuses'].get('cold', 0), 2)
            log.append(f"❄️ Ледяная стрела — {dmg} урона + Холод(2)!")
        else:
            log.append(f"Использован {cd['name']}")

        state['player_statuses'] = p_st

        # Списываем предмет
        items[ikey] -= 1
        if items[ikey] <= 0: del items[ikey]
        save_items(user_id, items)
        update_char_hp_mp(user_id, new_hp, new_mp)
        char = get_tower_char(user_id)

        # Проверяем смерть врага
        if state['enemy_hp'] <= 0:
            _handle_victory(bot, call.message.chat.id, user_id, char, state, log)
            return

        # Ход врага (использование предмета — это ход)
        action = state.get('next_enemy_action', {})
        enemy_log, new_player_hp = apply_enemy_ability(char, state, action)
        log.extend(enemy_log)

        tick_log, nhp2, nehp = process_end_of_turn({**char, 'hp': new_player_hp}, state)
        log.extend(tick_log)
        state['enemy_hp'] = max(0, nehp)

        update_char_hp_mp(user_id, max(0, nhp2))
        char = get_tower_char(user_id)

        if char['hp'] <= 0 or state['enemy_hp'] <= 0:
            if state['enemy_hp'] <= 0:
                _handle_victory(bot, call.message.chat.id, user_id, char, state, log)
            else:
                _handle_defeat(bot, call.message.chat.id, user_id, char, state, log)
            return

        state['next_enemy_action'] = roll_enemy_action(state['enemy_key'], state['enemy_base_dmg'])
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        send_battle(bot, call.message.chat.id, user_id, char, state, log,
                    msg_id_to_delete=state.get('last_msg_id'))

    # ── НАВЫК (заглушка) ──────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tb_skill')
    def cb_tb_skill(call):
        bot.answer_callback_query(call.id, "📜 Система навыков будет добавлена скоро!", show_alert=True)

    # ── НАЗАД К БИТВЕ ─────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tb_back_to_battle')
    def cb_tb_back(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        char = get_tower_char(user_id)
        state = get_battle(user_id)
        if not char or not state: return
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        send_battle(bot, call.message.chat.id, user_id, char, state,
                    msg_id_to_delete=state.get('last_msg_id'))

    # ── СБЕЖАТЬ ───────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tb_flee')
    def cb_tb_flee(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        state = get_battle(user_id)
        if not state: return
        floor = state['floor']
        delete_battle(user_id)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        from tower import tower_main_text, tower_main_keyboard
        char = get_tower_char(user_id)
        bot.send_message(call.message.chat.id,
            f"🚪 Ты покинул башню на *{floor}* этаже.", parse_mode='Markdown')
        if char:
            bot.send_message(call.message.chat.id,
                tower_main_text(char), reply_markup=tower_main_keyboard(char),
                parse_mode='Markdown')

    # ── СЛЕДУЮЩИЙ ЭТАЖ ────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tb_next_floor')
    def cb_tb_next_floor(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        char = get_tower_char(user_id)
        state = get_battle(user_id)
        if not char or not state: return

        floor = state['floor'] + 1
        state['floor'] = floor
        state['enemy_statuses'] = {}
        state['player_defending'] = False
        state['enemy_dodging'] = False
        state['enemy_blocking'] = False
        state['player_blind'] = False

        # Восстанавливаем часть HP между этажами
        max_hp = calc_max_hp(char)
        heal = max(5, max_hp // 10)
        new_hp = min(max_hp, char['hp'] + heal)
        update_char_hp_mp(user_id, new_hp)
        char = get_tower_char(user_id)

        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

        # 35% шанс события вместо боя (не чаще 1 раза за 2 этажа)
        last_event_floor = state.get('last_event_floor', -2)
        event_chance = 0.35
        # 20% шанс сокровищницы (не чаще 1 раза за 4 этажа, не на 1-м)
        last_treasury_floor = state.get('last_treasury_floor', -4)
        treasury_chance = 0.20

        roll = random.random()

        if floor > 1 and (floor - last_treasury_floor >= 4) and roll < treasury_chance:
            # ── СОКРОВИЩНИЦА ───────────────────────────────────
            from tower_treasury import send_treasury
            state['active_treasury'] = True
            state['last_treasury_floor'] = floor
            save_battle(user_id, state)
            bot.send_message(call.message.chat.id,
                f"🏯 *Этаж {floor}* — ❤️ Восстановлено {heal} HP\n\n"
                f"✨ На этом этаже *нет врагов*. Вместо этого...",
                parse_mode='Markdown')
            send_treasury(bot, call.message.chat.id, user_id, floor, char, state)

        elif (floor - last_event_floor >= 2) and (roll - treasury_chance) < event_chance:
            # ── СЛУЧАЙНОЕ СОБЫТИЕ ──────────────────────────────
            from tower_events import get_random_event, send_event
            event = get_random_event()
            state['active_event'] = event['id']
            state['last_event_floor'] = floor
            save_battle(user_id, state)
            bot.send_message(call.message.chat.id,
                f"🏯 *Этаж {floor}* — ❤️ Восстановлено {heal} HP\n\n"
                f"На этом этаже тебя ждёт не бой, а кое-что другое...",
                parse_mode='Markdown')
            send_event(bot, call.message.chat.id, user_id, event, state)
        else:
            # Обычный бой
            ekey, ehp, edmg = spawn_enemy(floor)
            e = ENEMIES[ekey]
            state['enemy_key'] = ekey
            state['enemy_hp'] = ehp
            state['enemy_max_hp'] = ehp
            state['enemy_base_dmg'] = edmg
            state['next_enemy_action'] = roll_enemy_action(ekey, edmg)
            send_battle(bot, call.message.chat.id, user_id, char, state,
                        log_lines=[f"⬆️ Этаж {floor}! {e['emoji']} {e['name']} преграждает путь",
                                    f"❤️ Восстановлено {heal} HP"])

    # ── ПОКИНУТЬ ПОСЛЕ ПОБЕДЫ ─────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == 'tb_exit')
    def cb_tb_exit(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        delete_battle(user_id)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        from tower import tower_main_text, tower_main_keyboard
        char = get_tower_char(user_id)
        if char:
            bot.send_message(call.message.chat.id,
                tower_main_text(char), reply_markup=tower_main_keyboard(char),
                parse_mode='Markdown')

    # ═══════════════════════════════════════════════════════════
    # ПОБЕДА И ПОРАЖЕНИЕ
    # ═══════════════════════════════════════════════════════════

    def _handle_victory(bot, chat_id, user_id, char, state, log):
        floor = state['floor']
        ekey = state['enemy_key']
        e = ENEMIES[ekey]

        # Опыт
        exp_gain = exp_for_floor(floor, ekey)
        lvl_ups, leveled = update_char_exp_floor(user_id, exp_gain, floor)

        # Предметы
        rewards = reward_items(floor)
        items = get_items(char)
        for k, v in rewards.items():
            items[k] = items.get(k, 0) + v
        save_items(user_id, items)

        # Форматируем награды
        reward_parts = []
        for k, v in rewards.items():
            cd = CONSUMABLES.get(k)
            if cd:
                reward_parts.append(f"{cd['emoji']} {cd['name']} ×{v}")

        lvl_text = f"\n🎊 Уровень повышен ×{lvl_ups}! Получено {lvl_ups*3} ОХ" if leveled else ""
        items_text = ", ".join(reward_parts) if reward_parts else "Ничего"

        msg = (f"🎉 *Победа!*\n\n"
               f"{e['emoji']} *{e['name']}* повержен на {floor} этаже!\n\n"
               f"Получено: +*{exp_gain}* ⭐ опыта{lvl_text}\n"
               f"Найдено: {items_text}")

        # Очищаем старое сообщение
        try: bot.delete_message(chat_id, state.get('last_msg_id'))
        except: pass

        markup = victory_keyboard(floor)
        bot.send_message(chat_id, msg, reply_markup=markup, parse_mode='Markdown')
        save_battle(user_id, state)  # сохраняем state для кнопки "следующий этаж"

    def _handle_defeat(bot, chat_id, user_id, char, state, log):
        floor = state['floor']
        ekey = state['enemy_key']
        e = ENEMIES[ekey]

        # Даём немного опыта даже за поражение
        exp_gain = max(5, exp_for_floor(floor, ekey) // 3)
        update_char_exp_floor(user_id, exp_gain, 0)

        # Восстанавливаем 20% HP
        char = get_tower_char(user_id)
        max_hp = calc_max_hp(char)
        new_hp = max(1, max_hp // 5)
        update_char_hp_mp(user_id, new_hp)

        delete_battle(user_id)

        try: bot.delete_message(chat_id, state.get('last_msg_id'))
        except: pass

        log_str = "\n".join(f"• {l}" for l in log[-3:])
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🏯 В меню башни", callback_data="tb_to_menu"))
        bot.send_message(chat_id,
            f"💀 *Ты пал на {floor} этаже...*\n\n"
            f"{e['emoji']} {e['name']} победил тебя.\n\n"
            f"{log_str}\n\n"
            f"❤️ Восстановлено {new_hp} HP. Получено +{exp_gain} ⭐ опыта.",
            reply_markup=markup, parse_mode='Markdown')

    @bot.callback_query_handler(func=lambda call: call.data == 'tb_to_menu')
    def cb_to_menu(call):
        bot.answer_callback_query(call.id)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        from tower import tower_main_text, tower_main_keyboard
        char = get_tower_char(call.from_user.id)
        if char:
            bot.send_message(call.message.chat.id,
                tower_main_text(char), reply_markup=tower_main_keyboard(char),
                parse_mode='Markdown')
