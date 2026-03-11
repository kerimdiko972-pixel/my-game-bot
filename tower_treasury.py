import json
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from tower import (
    get_conn, get_tower_char, calc_max_hp, calc_max_mp,
    WEAPONS, SPELLS, SPELL_CLASSES, get_items, save_items,
    get_mod, safe, get_owned_list
)
from tower_battle import get_battle, save_battle, delete_battle, update_char_hp_mp

# ═══════════════════════════════════════════════════════════════
# ДАННЫЕ ЭФФЕКТОВ ОРУЖИЙ (полный список, используется в бою)
# ═══════════════════════════════════════════════════════════════
# Каждый эффект: {"status": str, "turns": int, "chance": float}
# Спецэффекты:   {"double": True, "chance": float}
#                {"mp_regen": True, "chance": float}
#                {"ignore_armor": True}
#                {"spell_boost": float}
#                {"consumes": "arrows"|"bolts", "dmg_bonus": float}

WEAPON_EFFECT_DATA = {
    # ⚪ Начальные
    "starter_barbarian": [{"status": "weakness", "turns": 1, "chance": 0.20}],
    "starter_assassin":  [{"status": "bleed",    "turns": 1, "chance": 0.10}],
    "starter_ranger":    [{"double": True,                   "chance": 0.15}],
    "starter_mage":      [{"mp_regen": True,                 "chance": 0.15}],
    "starter_warlock":   [{"status": "poison",   "turns": 1, "chance": 0.15}],

    # 🟢 Необычные (луки/арбалеты требуют боеприпасы, посохи дают бонус)
    "short_bow":         [{"consumes": "arrows",  "dmg_bonus": 1.1}],
    "hunting_bow":       [{"consumes": "arrows",  "dmg_bonus": 1.1}],
    "throwing_knife":    [{"consumes": "bolts",   "dmg_bonus": 1.1}],
    "guard_crossbow":    [{"consumes": "bolts",   "dmg_bonus": 1.1}],
    "hunt_crossbow":     [{"consumes": "bolts",   "dmg_bonus": 1.1}],
    "apprentice_staff":  [{"mp_regen": True,                 "chance": 1.0, "val": 1}],
    "battle_wand":       [{"spell_boost": 0.05}],

    # 🔵 Редкие — 50% шанс
    "flaming_blade":     [{"status": "burn",     "turns": 2, "chance": 0.50}],
    "ice_axe":           [{"status": "cold",     "turns": 2, "chance": 0.50}],
    "lightning_blade":   [{"status": "shock",    "turns": 1, "chance": 0.50}],
    "poison_dagger":     [{"status": "poison",   "turns": 3, "chance": 0.50}],
    "blood_sickle":      [{"status": "bleed",    "turns": 3, "chance": 0.50}],
    "wind_hunter_bow":   [{"consumes": "arrows", "dmg_bonus": 1.2},
                          {"double": True,                   "chance": 0.15}],
    "storm_crossbow":    [{"consumes": "bolts",  "dmg_bonus": 1.2},
                          {"status": "shock",    "turns": 1, "chance": 0.50}],
    "ice_guard_spear":   [{"status": "cold",     "turns": 2, "chance": 0.50}],
    "flame_hammer":      [{"status": "burn",     "turns": 2, "chance": 0.50}],
    "black_magic_staff": [{"spell_boost": 0.10}],
    "dark_wand":         [{"status": "weakness", "turns": 2, "chance": 0.50}],
    "thunder_staff":     [{"status": "shock",    "turns": 1, "chance": 0.50}],
    "ice_storm_staff":   [{"status": "cold",     "turns": 3, "chance": 0.50}],
    "fury_fire_staff":   [{"status": "burn",     "turns": 3, "chance": 0.50}],
    "plague_knight":     [{"status": "poison",   "turns": 3, "chance": 0.50}],
    "cult_dagger":       [{"status": "bleed",    "turns": 3, "chance": 0.50}],
    "storm_blade":       [{"status": "shock",    "turns": 2, "chance": 0.50}],

    # 🟣 Эпические — 65% шанс
    "arctic_hammer":     [{"status": "cold",     "turns": 3, "chance": 0.65}],
    "flame_blade":       [{"status": "burn",     "turns": 3, "chance": 0.65}],
    "lightning_dagger":  [{"status": "shock",    "turns": 2, "chance": 0.65}],
    "poison_sickle":     [{"status": "poison",   "turns": 4, "chance": 0.65}],
    "blood_blade_epic":  [{"status": "bleed",    "turns": 4, "chance": 0.65}],
    "light_warrior":     [{"double": True,                   "chance": 0.30}],
    "shadow_bow":        [{"consumes": "arrows", "dmg_bonus": 1.3},
                          {"status": "blind",    "turns": 1, "chance": 0.40}],
    "storm_crossbow_e":  [{"consumes": "bolts",  "dmg_bonus": 1.3},
                          {"status": "shock",    "turns": 2, "chance": 0.50}],
    "ice_staff_epic":    [{"status": "cold",     "turns": 3, "chance": 0.65},
                          {"spell_boost": 0.10}],
    "fire_will_staff":   [{"status": "burn",     "turns": 3, "chance": 0.65},
                          {"spell_boost": 0.10}],
    "lightning_storm_staff": [{"status": "shock", "turns": 2, "chance": 0.65},
                              {"spell_boost": 0.10}],
    "poison_dark_staff": [{"status": "poison",   "turns": 4, "chance": 0.65},
                          {"spell_boost": 0.10}],

    # 🟠 Легендарные — 80% шанс
    "fire_fang":             [{"status": "burn",     "turns": 4, "chance": 0.80}],
    "ice_fury":              [{"status": "cold",     "turns": 3, "chance": 0.80}],
    "lightning_discharge_leg":[{"status": "shock",   "turns": 1, "chance": 0.80}],
    "plague_blade":          [{"status": "poison",   "turns": 4, "chance": 0.80}],
    "blood_fury":            [{"status": "bleed",    "turns": 4, "chance": 0.80}],
    "lightbearer_sword":     [{"ignore_armor": True}],
    "ice_storm_staff_leg":   [{"status": "cold",     "turns": 4, "chance": 0.80},
                              {"status": "shock",    "turns": 2, "chance": 0.80},
                              {"spell_boost": 0.15}],
}

# ═══════════════════════════════════════════════════════════════
# ПРИМЕНЕНИЕ ЭФФЕКТА ОРУЖИЯ (вызывается из tower_battle при атаке)
# ═══════════════════════════════════════════════════════════════

def apply_weapon_effect_v2(char, state, weapon_key):
    """
    Полностью data-driven применение эффектов оружия.
    Возвращает (список_лога, израсходованы_ли_боеприпасы).
    """
    effects = WEAPON_EFFECT_DATA.get(weapon_key, [])
    if not effects:
        return [], True

    e_st = state.get('enemy_statuses', {})
    p_st = state.get('player_statuses', {})
    log = []
    ok = True  # боеприпасы (arrows/bolts) в наличии

    spell_boost = state.get('weapon_spell_boost', 0.0)

    for eff in effects:
        # Расход боеприпасов
        if 'consumes' in eff:
            ammo_key = eff['consumes']
            items = get_items(char)
            if items.get(ammo_key, 0) > 0:
                items[ammo_key] -= 1
                if items[ammo_key] <= 0:
                    del items[ammo_key]
                save_items(char['user_id'], items)
                # Бонус урона от боеприпасов уже встроен в weapon damage formula
            else:
                log.append(f"❌ Нет боеприпасов ({ammo_key})! Атака слабее.")
                ok = False
            continue

        # Бонус к заклинаниям (хранится в state)
        if 'spell_boost' in eff:
            state['weapon_spell_boost'] = eff['spell_boost']
            continue

        # Игнор брони — флаг в state
        if eff.get('ignore_armor'):
            state['_ignore_armor'] = True
            continue

        chance = eff.get('chance', 1.0)
        if random.random() > chance:
            continue

        # Двойной удар
        if eff.get('double'):
            state['_double_strike'] = True
            log.append("✨ *Двойной удар!*")
            continue

        # Регенерация маны
        if eff.get('mp_regen'):
            from tower import calc_max_mp
            max_mp = calc_max_mp(char)
            regen_val = eff.get('val', get_mod(char['intellect']))
            regen_val = max(1, regen_val)
            new_mp = min(max_mp, char['mp'] + regen_val)
            update_char_hp_mp(char['user_id'], char['hp'], new_mp)
            log.append(f"⚡ Оружие восстанавливает *{regen_val} MP*!")
            continue

        # Статус на врага
        if 'status' in eff:
            st = eff['status']
            turns = eff['turns']
            e_st[st] = max(e_st.get(st, 0), turns)
            em = _STATUS_EMOJI.get(st, '')
            name = _STATUS_NAME.get(st, st)
            log.append(f"{em} *{name}({turns})* наложен на врага!")

    state['enemy_statuses'] = e_st
    state['player_statuses'] = p_st
    return log, ok

_STATUS_EMOJI = {
    'burn':'🔥','cold':'❄️','shock':'💫','weakness':'⛓️‍💥','poison':'☠️',
    'blind':'👁️‍🗨️','regen':'🌿','fear':'😱','sleep':'💤','bleed':'🩸',
    'second_wind':'❤️‍🔥','barrier':'🛡️'
}
_STATUS_NAME = {
    'burn':'Ожог','cold':'Холод','shock':'Шок','weakness':'Слабость',
    'poison':'Яд','blind':'Слепота','regen':'Регенерация','fear':'Страх',
    'sleep':'Сон','bleed':'Кровотечение','second_wind':'Второе дыхание',
    'barrier':'Барьер'
}

# ═══════════════════════════════════════════════════════════════
# ПУЛЫ ОРУЖИЙ ПО РЕДКОСТИ И ЭТАЖУ
# ═══════════════════════════════════════════════════════════════

_WEAPONS_BY_RARITY = {
    '🟢': [k for k,v in WEAPONS.items() if v['rarity'] == '🟢'],
    '🔵': [k for k,v in WEAPONS.items() if v['rarity'] == '🔵'],
    '🟣': [k for k,v in WEAPONS.items() if v['rarity'] == '🟣'],
    '🟠': [k for k,v in WEAPONS.items() if v['rarity'] == '🟠'],
}

_SPELLS_BY_LEVEL = {}
for sk, sv in SPELLS.items():
    lvl = sv['level']
    _SPELLS_BY_LEVEL.setdefault(lvl, []).append(sk)

def _floor_weapon_rarity(floor):
    if floor >= 25:
        return random.choices(['🟣','🟠'], weights=[55,45])[0]
    elif floor >= 15:
        return random.choices(['🔵','🟣'], weights=[50,50])[0]
    elif floor >= 6:
        return random.choices(['🟢','🔵'], weights=[40,60])[0]
    else:
        return random.choices(['🟢','🔵'], weights=[75,25])[0]

def _floor_spell_levels(floor):
    if floor >= 25: return [4, 5]
    elif floor >= 15: return [3, 4]
    elif floor >= 8:  return [2, 3]
    else:             return [1, 2]

def pick_treasury_loot(floor, class_key):
    """Возвращает словарь с лутом сокровищницы."""
    loot = {}

    # Оружие
    rarity = _floor_weapon_rarity(floor)
    pool = _WEAPONS_BY_RARITY.get(rarity, [])
    if pool:
        loot['weapon'] = random.choice(pool)

    # Заклинание (только маг/колдун)
    if class_key in SPELL_CLASSES:
        levels = _floor_spell_levels(floor)
        spell_pool = []
        for lvl in levels:
            spell_pool.extend(_SPELLS_BY_LEVEL.get(lvl, []))
        if spell_pool:
            loot['spell'] = random.choice(spell_pool)

    # Монеты
    loot['coins'] = random.randint(floor * 5, floor * 15)

    return loot

# ═══════════════════════════════════════════════════════════════
# ЗАПИСЬ ОРУЖИЯ В БАЗУ ДАННЫХ
# ═══════════════════════════════════════════════════════════════

def add_weapon_to_owned(user_id, weapon_key):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT owned_weapons FROM tower_chars WHERE user_id=%s', (user_id,))
    row = c.fetchone()
    if row:
        try:
            owned = json.loads(row[0] or '[]')
        except:
            owned = []
        if weapon_key not in owned:
            owned.append(weapon_key)
        c.execute('UPDATE tower_chars SET owned_weapons=%s WHERE user_id=%s',
                  (json.dumps(owned), user_id))
        conn.commit()
    conn.close()

def add_spell_to_learned(user_id, spell_key):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT learned_spells FROM tower_chars WHERE user_id=%s', (user_id,))
    row = c.fetchone()
    already = False
    if row:
        try:
            learned = json.loads(row[0] or '[]')
        except:
            learned = []
        if spell_key in learned:
            already = True
        else:
            learned.append(spell_key)
            c.execute('UPDATE tower_chars SET learned_spells=%s WHERE user_id=%s',
                      (json.dumps(learned), user_id))
            conn.commit()
    conn.close()
    return not already  # True = новое заклинание

def add_coins_to_char(user_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE tower_chars SET coins=coins+%s WHERE user_id=%s', (amount, user_id))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════════════════════════
# ХЭНДЛЕРЫ СОКРОВИЩНИЦЫ
# ═══════════════════════════════════════════════════════════════

def send_treasury(bot, chat_id, user_id, floor, char, state):
    """Отправляет карточку сокровищницы"""
    loot = pick_treasury_loot(floor, char.get('class_key', ''))
    state['treasury_loot'] = loot
    save_battle(user_id, state)

    lines = [f"💎 *СОКРОВИЩНИЦА — ЭТАЖ {floor}* 💎\n"]

    markup = InlineKeyboardMarkup(row_width=1)

    if 'weapon' in loot:
        wk = loot['weapon']
        w = WEAPONS[wk]
        eff_list = WEAPON_EFFECT_DATA.get(wk, [])
        eff_str = _describe_effects(eff_list)
        dmg_val = w['damage'](char)
        lines.append(
            f"{w['rarity']} *{w['name']}*\n"
            f"⚔️ Урон: ~{dmg_val}  |  📊 {w['rarity_name']}\n"
            f"✨ {eff_str or 'Нет эффекта'}"
        )
        markup.add(InlineKeyboardButton(
            f"🗡️ Взять {w['name']}", callback_data=f"tr_weapon_{wk}"))

    if 'spell' in loot:
        sk = loot['spell']
        sp = SPELLS[sk]
        learned = get_owned_list(char, 'learned_spells')
        already = sk in learned
        label = f"{'✅' if already else '📖'} Выучить {sp['emoji']} {sp['name']} (ур.{sp['level']})"
        lines.append(
            f"\n{sp['emoji']} *{sp['name']}* (уровень {sp['level']})\n"
            f"⚡ Мана: {sp['mana']} | {sp['desc']}"
        )
        markup.add(InlineKeyboardButton(label, callback_data=f"tr_spell_{sk}"))

    if 'coins' in loot:
        lines.append(f"\n💰 Монеты: *{loot['coins']}*")
        markup.add(InlineKeyboardButton(
            f"💰 Взять {loot['coins']} монет", callback_data="tr_coins"))

    markup.add(InlineKeyboardButton("🚪 Пройти мимо", callback_data="tr_skip"))

    bot.send_message(chat_id, "\n".join(lines), reply_markup=markup, parse_mode='Markdown')

def _describe_effects(eff_list):
    if not eff_list:
        return None
    parts = []
    for e in eff_list:
        if 'status' in e:
            em = _STATUS_EMOJI.get(e['status'], '')
            nm = _STATUS_NAME.get(e['status'], e['status'])
            ch = int(e.get('chance', 1.0) * 100)
            parts.append(f"{em}{nm}({e['turns']}) {ch}%")
        elif e.get('double'):
            parts.append(f"✨Двойной удар {int(e.get('chance',0)*100)}%")
        elif e.get('mp_regen'):
            parts.append("⚡Регенерация маны")
        elif e.get('ignore_armor'):
            parts.append("🔓Игнор брони")
        elif 'spell_boost' in e:
            parts.append(f"💫+{int(e['spell_boost']*100)}% к заклинаниям")
        elif 'consumes' in e:
            parts.append(f"🏹Требует {e['consumes']}")
    return ", ".join(parts)

def register_tower_treasury(bot):

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tr_'))
    def cb_treasury(call):
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        char = get_tower_char(user_id)
        state = get_battle(user_id)
        if not char or not state: return

        loot = state.get('treasury_loot', {})
        action = call.data[3:]  # убираем "tr_"

        result_lines = []

        if action.startswith('weapon_'):
            wk = action[7:]
            w = WEAPONS.get(wk)
            if w:
                add_weapon_to_owned(user_id, wk)
                result_lines.append(f"🗡️ *{w['rarity']} {w['name']}* добавлено в рюкзак!")
                result_lines.append("_(Экипируй в меню Башни → Рюкзак)_")

        elif action.startswith('spell_'):
            sk = action[6:]
            sp = SPELLS.get(sk)
            if sp:
                is_new = add_spell_to_learned(user_id, sk)
                if is_new:
                    result_lines.append(f"📖 Заклинание *{sp['emoji']} {sp['name']}* изучено!")
                    result_lines.append("_(Назначь в слоты через меню Заклинания)_")
                else:
                    result_lines.append(f"✅ Это заклинание уже изучено.")

        elif action == 'coins':
            coins = loot.get('coins', 0)
            if coins:
                add_coins_to_char(user_id, coins)
                result_lines.append(f"💰 Получено *{coins} монет*!")

        elif action == 'skip':
            result_lines.append("🚪 Ты прошёл мимо сокровищницы.")

        # Убираем лут из state чтобы не взять дважды
        state.pop('treasury_loot', None)
        state.pop('active_treasury', None)
        save_battle(user_id, state)

        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

        if result_lines:
            bot.send_message(call.message.chat.id,
                "\n".join(result_lines), parse_mode='Markdown')

        # Кнопки продолжения
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("⬆️ Следующий этаж", callback_data="tb_next_floor"),
            InlineKeyboardButton("🚪 Покинуть башню",  callback_data="tb_exit"),
        )
        markup.add(InlineKeyboardButton("🏯 Меню башни", callback_data="tb_to_menu"))
        floor = state.get('floor', 1)
        char = get_tower_char(user_id)
        bot.send_message(call.message.chat.id,
            f"🏯 Этаж *{floor}* пройден. Что дальше?",
            reply_markup=markup, parse_mode='Markdown')
