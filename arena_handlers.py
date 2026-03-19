# ============================================================
#  arena_handlers.py  — Telegram-хэндлеры для Арены
#  Механика хода: по скорости, 2 АП, кнопка Завершить,
#  затем ход врага автоматически с новым сообщением.
# ============================================================

import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from arena_data import (
    CLASS_EMOJI, CLASS_BASE_STATS, MAGIC_CLASSES, WEAPONS, ARTIFACTS,
    STATUS_DISPLAY, POSITIVE_EFFECTS, NEGATIVE_EFFECTS,
    calc_max_hp, calc_max_mana, calc_kd, calc_speed,
    get_level_from_xp, get_xp_to_next, pick_goblin_action, GOBLIN_DATA
)
from arena_db import (
    init_arena_tables, get_arena_fighters, create_fighter,
    get_fighter_by_slot, get_fighter_by_id, update_fighter,
    delete_fighter, save_battle_state, load_battle_state,
    clear_battle_state, build_battle_fighter
)
from arena_combat import (
    init_battle, do_attack, execute_goblin_action, use_active_artifact,
    apply_passive_artifact_stats, tick_effects_start_of_turn,
    tick_effects_end_of_turn, end_of_round_bleed_decay, format_effects,
    add_effect, remove_one_negative, is_stunned
)

pending_arena = {}

# ================== ФОРМАТИРОВАНИЕ ==================

def fmt_fighter_list(fighters):
    lines = ['— – - 🔵 ⚔️ А Р Е Н А ⚔️ 🔴 - – —\n', 'Твои бойцы:\n']
    nums = ['1️⃣', '2️⃣', '3️⃣']
    for slot in (1, 2, 3):
        f = fighters[slot]
        num = nums[slot - 1]
        if f:
            em = CLASS_EMOJI.get(f['class'], '👤')
            lines.append(f'{num} {em} {f["name"]} | {f["class"]} Ур.{f["level"]}')
        else:
            lines.append(f'{num} [Пусто]')
    return '\n'.join(lines)


def fmt_fighter_card(fighter_row):
    cls  = fighter_row['class']
    lvl  = fighter_row['level']
    xp   = fighter_row['xp']
    sp   = fighter_row['sp']
    name = fighter_row['name']
    em   = CLASS_EMOJI.get(cls, '')
    s, d, co = fighter_row['str'], fighter_row['dex'], fighter_row['con']
    i, ch, lk = fighter_row['intel'], fighter_row['cha'], fighter_row['lck']
    max_hp   = calc_max_hp(cls, lvl, co)
    max_mana = calc_max_mana(cls, lvl, i, ch)
    kd       = calc_kd(d)
    speed    = calc_speed(cls, d, lk)
    xp_next  = get_xp_to_next(xp)
    art1   = fighter_row.get('artifact1') or 'Нет'
    art2   = fighter_row.get('artifact2') or 'Нет'
    weapon = fighter_row.get('weapon') or 'Нет'
    return (
        f'— – - 🔵 ⚔️ А Р Е Н А ⚔️ 🔴 - – —\n\n'
        f'🎖️ Рекорд: {fighter_row.get("record_floor", 0)} этаж\n\n'
        f'• - - - - - - - - - - - - - - - - - •\n\n'
        f'— - - {name} - - —\n'
        f'Класс: {em} {cls}\n'
        f'⭐ Уровень: {lvl} ({xp_next} XP до след.)\n'
        f'✨ SP: {sp}\n\n'
        f'❤️ ХП: {max_hp}\n'
        f'🛡️ КД: {kd}\n'
        f'🔷 Мана: {max_mana}\n\n'
        f'💪 СИЛ: {s}\n'
        f'🎯 ЛОВ: {d}\n'
        f'❤️ ТЕЛ: {co}\n'
        f'💡 ИНТ: {i}\n'
        f'👄 ХАР: {ch}\n'
        f'🍀 УДЧ: {lk}\n'
        f'🏃 СКР: {speed}\n\n'
        f'• - - - - - - - - - - - - - - - - - •\n\n'
        f'— - - 🎒 Снаряжение 🎒 - - —\n\n'
        f'💰 Монет: {fighter_row.get("money", 0)}\n\n'
        f'Оружие: {weapon}\n\n'
        f'Артефакт №1: {art1}\n'
        f'Артефакт №2: {art2}\n\n'
        f'• - - - - - - - - - - - - - - - - - •'
    )


def fighter_card_keyboard(fighter_row):
    em  = CLASS_EMOJI.get(fighter_row['class'], '👤')
    fid = fighter_row['id']
    kb  = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('🏞️ Приключение',       callback_data=f'arena_adv_{fid}'),
        InlineKeyboardButton('❔ Случайный бой ⚔️',   callback_data=f'arena_rand_{fid}'),
    )
    kb.add(
        InlineKeyboardButton('👤 Бой с игроком ⚔️',  callback_data=f'arena_pvp_{fid}'),
        InlineKeyboardButton(f'{em} Мой Боец',        callback_data=f'arena_card_{fid}'),
    )
    kb.add(
        InlineKeyboardButton('🎒 Снаряжение',         callback_data=f'arena_equip_{fid}'),
        InlineKeyboardButton('🏆 Лидеры',             callback_data=f'arena_leaders_{fid}'),
    )
    kb.add(InlineKeyboardButton('🔁 Поменять персонажа', callback_data=f'arena_switch_{fid}'))
    return kb


def fmt_battle(state):
    p     = state['player']
    e     = state['enemy']
    ap    = p.get('ap', 2)
    phase = state.get('phase', 'player_turn')
    stance_names = {
        'normal': 'Нейтральная', 'battle': 'Боевая',
        'defense': 'Защитная', 'precise': 'Точная', 'dodge': 'Уклонения',
    }
    stance   = stance_names.get(p.get('stance', 'normal'), 'Нейтральная')
    p_effs   = format_effects(p.get('effects', {}))
    e_effs   = format_effects(e.get('effects', {}))
    log_text = state.get('log', ['...'])[-1]
    next_act = state.get('goblin_next_action', {}).get('name', '???')
    enemy_hint = f'\nСледующий ход врага: {next_act}' if phase == 'player_turn' else ''
    phase_label = 'Твой ход' if phase == 'player_turn' else '⏳ Обработка...'
    return (
        f'— – - ⚔️ Б О Й ⚔️ - – —\n'
        f'👤 {p["name"]} 🆚 {e["name"]}\n\n'
        f'❤️ {p["name"]}: {p["hp"]} / {p["max_hp"]}\n'
        f'🔷 Мана: {p["mana"]} / {p["max_mana"]}\n'
        f'🏃 Скорость: {p.get("speed", 5)}\n'
        f'⚡ AP: {ap}\n'
        f'🧘 Стойка: {stance}\n\n'
        f'💪 СИЛ: {p["str"]}  '
        f'🎯 ЛОВ: {p["dex"]}  '
        f'❤️ ТЕЛ: {p["con"]}\n'
        f'💡 ИНТ: {p["int"]}  '
        f'👄 ХАР: {p["cha"]}  '
        f'🍀 УДЧ: {p["lck"]}\n\n'
        f'{e["name"]}: {e["hp"]} / {e["max_hp"]}\n'
        f'🏃 Скорость: {e.get("speed", 5)}\n\n'
        f'• – – – – – – – – – – – – – – – •\n\n'
        f'🎯 Эффекты:\n\n'
        f'👤 {p["name"]}:\n{p_effs}\n\n'
        f'{e["name"]}:\n{e_effs}\n\n'
        f'• – – – – – – – – – – – – – – – •\n\n'
        f'📜 Ход боя:\n{log_text}'
        f'{enemy_hint}\n\n'
        f'— {phase_label} —'
    )


def battle_keyboard(state):
    p   = state['player']
    cls = p.get('class', '')
    kb  = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('⚔️ Атака',    callback_data='arena_atk'),
        InlineKeyboardButton('🛡️ Защита',   callback_data='arena_def'),
    )
    row = [InlineKeyboardButton('✨ Навыки', callback_data='arena_skills')]
    if cls in MAGIC_CLASSES:
        row.append(InlineKeyboardButton('🔮 Заклинания', callback_data='arena_spells'))
    kb.add(*row)
    kb.add(
        InlineKeyboardButton('🧘 Стойка',    callback_data='arena_stance'),
        InlineKeyboardButton('🎒 Инвентарь', callback_data='arena_inv'),
    )
    kb.add(
        InlineKeyboardButton('🛎️ Завершить ход', callback_data='arena_end_turn'),
        InlineKeyboardButton('🏃 Сбежать',        callback_data='arena_run'),
    )
    return kb


def enemy_turn_keyboard(fighter_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('Продолжить', callback_data=f'arena_next_turn_{fighter_id}'))
    return kb


def finished_keyboard(fighter_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton('🔁 Бой снова',    callback_data=f'arena_rand_{fighter_id}'))
    kb.add(InlineKeyboardButton('🗺️ Меню арены',   callback_data=f'arena_switch_{fighter_id}'))
    return kb


def fmt_inventory(state):
    p      = state['player']
    art1   = p.get('artifact1') or 'Нет'
    art2   = p.get('artifact2') or 'Нет'
    weapon = p.get('weapon') or 'Нет'
    cd     = p.get('artifact_cooldowns', {})
    def cd_str(art_name):
        if not art_name or art_name == 'Нет' or art_name not in ARTIFACTS:
            return ''
        rem = cd.get(ARTIFACTS[art_name]['effect_key'], 0)
        return f' ⏳{rem}' if rem > 0 else ''
    return (
        f'— – - 🎒 И Н В Е Н Т А Р Ь - – —\n\n'
        f'👤 {p["name"]}: {CLASS_EMOJI.get(p["class"], "👤")} {p["class"]} | Ур.{p["level"]}\n\n'
        f'💰 Золото: {p.get("money", 0)}\n\n'
        f'• – – – – – – – – – – – – – – – •\n'
        f'⚔️ Снаряжение:\n\n'
        f'Оружие: {weapon}\n\n'
        f'Артефакт №1: {art1}{cd_str(art1)}\n'
        f'Артефакт №2: {art2}{cd_str(art2)}\n\n'
        f'• – – – – – – – – – – – – – – – •'
    )


def inventory_keyboard(state):
    p  = state['player']
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(p.get('weapon') or '⚔️ Оружие: Нет', callback_data='arena_inv_weapon'))
    for i, slot in enumerate(['artifact1', 'artifact2'], 1):
        art = p.get(slot)
        label = art if art else f'Артефакт №{i}: Нет'
        cb = f'arena_use_art_{i}' if art else 'arena_inv_empty'
        kb.add(InlineKeyboardButton(label, callback_data=cb))
    kb.add(InlineKeyboardButton('🔙 Назад', callback_data='arena_back_battle'))
    return kb


def fmt_stance_menu(current):
    names = {
        'normal': 'Нейтральная', 'battle': '⚔️ Боевая',
        'defense': '🛡️ Защитная', 'precise': '🎯 Точная', 'dodge': '👣 Уклонения',
    }
    return (
        f'— 🧘 С Т О Й К И —\n\n'
        f'Текущая: {names.get(current, "Нейтральная")}\n\n'
        f'• - - - - - - - •\n'
        f'⚔️ Боевая стойка\n+2 к урону\n+5% к шансу крита\n-1 к телосложению\n'
        f'• - - - - - - - •\n'
        f'🛡️ Защитная стойка\n-20% входящего урона\n+2 к телосложению\n-2 к урону\n'
        f'• - - - - - - - •\n'
        f'🎯 Точная стойка\n+10% к попаданию дальнобойных\n-1 к скорости\n'
        f'• - - - - - - - •\n'
        f'👣 Стойка уклонения\n+15% к уклонению\n+1 к скорости\n-2 к урону\n'
        f'• - - - - - - - •'
    )


def stance_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('⚔️ Боевая',    callback_data='arena_st_battle'),
        InlineKeyboardButton('🛡️ Защитная',  callback_data='arena_st_defense'),
        InlineKeyboardButton('🎯 Точная',    callback_data='arena_st_precise'),
        InlineKeyboardButton('👣 Уклонение', callback_data='arena_st_dodge'),
    )
    kb.add(InlineKeyboardButton('🔙 Назад', callback_data='arena_back_battle'))
    return kb


# ================== ИГРОВАЯ ЛОГИКА ==================

def _safe_edit(bot, chat_id, msg_id, text, kb=None):
    try:
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def _start_player_turn(state):
    player = state['player']
    msgs   = []
    msgs.extend(tick_effects_start_of_turn(player))
    player['ap']        = 2
    player['defending'] = False
    state['phase']      = 'player_turn'
    for slot in ['artifact1', 'artifact2']:
        art = player.get(slot)
        if art and art in ARTIFACTS and ARTIFACTS[art]['effect_key'] == 'warm_scarf':
            player['shield'] = player.get('shield', 0) + 1
    return msgs


def _execute_goblin_turn(state):
    msgs   = []
    goblin = state['enemy']
    player = state['player']

    msgs.extend(tick_effects_start_of_turn(goblin))

    if goblin['hp'] <= 0:
        state['phase']  = 'finished'
        state['winner'] = 'player'
        return msgs

    action = state.get('goblin_next_action', pick_goblin_action())
    msgs.append(f'Гоблин использует: {action["name"]}')
    msgs.extend(execute_goblin_action(goblin, player, action))

    if goblin.pop('_extra_turn', False) and player['hp'] > 0 and goblin['hp'] > 0:
        extra_act = pick_goblin_action()
        msgs.append(f'Дополнительный ход гоблина: {extra_act["name"]}')
        msgs.extend(execute_goblin_action(goblin, player, extra_act))

    msgs.extend(tick_effects_end_of_turn(goblin))
    end_of_round_bleed_decay(goblin)
    goblin['defending'] = False

    if player['hp'] <= 0:
        state['phase']  = 'finished'
        state['winner'] = 'goblin'
        msgs.append(f'{player["name"]} пал в бою...')
        return msgs

    state['goblin_next_action'] = pick_goblin_action()
    state['round'] = state.get('round', 1) + 1

    cds = player.get('artifact_cooldowns', {})
    for k in list(cds):
        cds[k] -= 1
        if cds[k] <= 0:
            del cds[k]

    msgs.extend(tick_effects_end_of_turn(player))
    end_of_round_bleed_decay(player)

    start_msgs = _start_player_turn(state)
    if start_msgs:
        msgs.extend(start_msgs)

    if player['hp'] <= 0:
        state['phase']  = 'finished'
        state['winner'] = 'goblin'
        msgs.append(f'{player["name"]} умер от эффектов...')

    return msgs


def _check_death(state, get_conn, user_id):
    player = state['player']
    enemy  = state['enemy']
    if enemy['hp'] <= 0 and state.get('winner') != 'goblin':
        state['phase']  = 'finished'
        state['winner'] = 'player'
        reward = _end_battle_rewards(state, get_conn, user_id)
        return True, reward
    if player['hp'] <= 0 or state.get('winner') == 'goblin':
        state['phase']  = 'finished'
        state['winner'] = 'goblin'
        return True, f'{player["name"]} пал в бою...'
    return False, ''


def _end_battle_rewards(state, get_conn, user_id):
    player     = state['player']
    fid        = player['id']
    xp_gain    = GOBLIN_DATA['reward_xp']
    money_gain = random.randint(*GOBLIN_DATA['reward_money_range'])
    fighter    = get_fighter_by_id(get_conn, fid)
    new_xp     = fighter['xp'] + xp_gain
    new_money  = fighter['money'] + money_gain
    old_level  = get_level_from_xp(fighter['xp'])
    new_level  = get_level_from_xp(new_xp)
    update_fighter(get_conn, fid, xp=new_xp, money=new_money, level=new_level)
    lvl_msg = f'\nНовый уровень: {new_level}!' if new_level > old_level else ''
    return f'Победа!\n\n+{xp_gain} XP\n+{money_gain} монет{lvl_msg}'


def _do_player_action(call, get_conn):
    user_id = call.from_user.id
    state   = load_battle_state(get_conn, user_id)
    if not state:
        return None, '❌ Бой не найден'
    if state.get('phase') != 'player_turn':
        return None, '⏳ Сейчас не твой ход!'
    if state['player'].get('ap', 0) <= 0:
        return None, '❌ Нет АП! Нажми 🛎️ Завершить ход.'
    return state, None


# ================== РЕГИСТРАЦИЯ ==================

def register_arena_handlers(bot, get_conn):

    @bot.message_handler(commands=['arena'])
    def cmd_arena(message):
        user_id  = message.from_user.id
        fighters = get_arena_fighters(get_conn, user_id)
        text = fmt_fighter_list(fighters)
        kb   = InlineKeyboardMarkup(row_width=1)
        for slot in (1, 2, 3):
            if fighters[slot]:
                f  = fighters[slot]
                em = CLASS_EMOJI.get(f['class'], '')
                kb.add(InlineKeyboardButton(
                    f'{em} {f["name"]} (Ур.{f["level"]})',
                    callback_data=f'arena_view_{slot}'
                ))
            else:
                kb.add(InlineKeyboardButton(
                    f'➕ Создать (слот {slot})',
                    callback_data=f'arena_create_{slot}'
                ))
        bot.send_message(message.chat.id, text, reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_view_'))
    def cb_arena_view(call):
        user_id = call.from_user.id
        slot    = int(call.data.split('_')[-1])
        fighter = get_fighter_by_slot(get_conn, user_id, slot)
        if not fighter:
            bot.answer_callback_query(call.id, 'Боец не найден')
            return
        _safe_edit(bot, call.message.chat.id, call.message.message_id,
                   fmt_fighter_card(fighter), fighter_card_keyboard(fighter))
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_create_'))
    def cb_arena_create(call):
        user_id = call.from_user.id
        slot    = int(call.data.split('_')[-1])
        pending_arena[user_id] = {
            'action': 'waiting_name', 'slot': slot,
            'chat_id': call.message.chat.id, 'msg_id': call.message.message_id,
        }
        try:
            bot.edit_message_text(
                f'Введи имя для своего бойца (макс. 25 символов):\nСлот: {slot}',
                call.message.chat.id, call.message.message_id
            )
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda m: m.from_user.id in pending_arena
                          and pending_arena[m.from_user.id].get('action') == 'waiting_name')
    def handle_arena_name(message):
        user_id = message.from_user.id
        name    = message.text.strip()[:25]
        if not name:
            bot.send_message(message.chat.id, 'Имя не может быть пустым!')
            return
        state          = pending_arena[user_id]
        state['name']  = name
        state['action'] = 'choosing_class'
        kb = InlineKeyboardMarkup(row_width=2)
        for cls, em in CLASS_EMOJI.items():
            kb.add(InlineKeyboardButton(f'{em} {cls}', callback_data=f'arena_cls_{cls}'))
        kb.add(InlineKeyboardButton('📝🔙 Изменить имя', callback_data=f'arena_rename_{state["slot"]}'))
        bot.send_message(message.chat.id, f'Имя бойца: {name}\n\nВыбери класс:', reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_rename_'))
    def cb_arena_rename(call):
        user_id = call.from_user.id
        slot    = int(call.data.split('_')[-1])
        pending_arena[user_id] = {
            'action': 'waiting_name', 'slot': slot,
            'chat_id': call.message.chat.id, 'msg_id': call.message.message_id,
        }
        try:
            bot.edit_message_text(
                f'Введи имя для своего бойца (макс. 25 символов):\nСлот: {slot}',
                call.message.chat.id, call.message.message_id
            )
        except Exception:
            bot.send_message(call.message.chat.id, 'Введи имя:')
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_cls_')
                                  and c.from_user.id in pending_arena
                                  and pending_arena[c.from_user.id].get('action') == 'choosing_class')
    def cb_arena_class(call):
        user_id = call.from_user.id
        cls     = call.data[len('arena_cls_'):]
        if cls not in CLASS_EMOJI:
            bot.answer_callback_query(call.id, 'Неизвестный класс')
            return
        state   = pending_arena.pop(user_id)
        name    = state.get('name', 'Безымянный')
        slot    = state.get('slot', 1)
        try:
            fighter = create_fighter(get_conn, user_id, slot, name, cls)
        except Exception as e:
            bot.answer_callback_query(call.id, f'Ошибка: {e}')
            return
        _safe_edit(bot, call.message.chat.id, call.message.message_id,
                   fmt_fighter_card(fighter), fighter_card_keyboard(fighter))
        bot.answer_callback_query(call.id, f'Боец {name} создан!')

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_card_'))
    def cb_arena_card(call):
        user_id = call.from_user.id
        fid     = int(call.data.split('_')[-1])
        fighter = get_fighter_by_id(get_conn, fid)
        if not fighter or fighter.get('user_id') != user_id:
            bot.answer_callback_query(call.id, 'Боец не найден')
            return
        _safe_edit(bot, call.message.chat.id, call.message.message_id,
                   fmt_fighter_card(fighter), fighter_card_keyboard(fighter))
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_switch_'))
    def cb_arena_switch(call):
        user_id  = call.from_user.id
        fighters = get_arena_fighters(get_conn, user_id)
        text = fmt_fighter_list(fighters)
        kb   = InlineKeyboardMarkup(row_width=1)
        for slot in (1, 2, 3):
            if fighters[slot]:
                f  = fighters[slot]
                em = CLASS_EMOJI.get(f['class'], '')
                kb.add(InlineKeyboardButton(
                    f'{em} {f["name"]} (Ур.{f["level"]})',
                    callback_data=f'arena_view_{slot}'
                ))
            else:
                kb.add(Inl']  = 'finished'
        state['winner'] = 'player'
        return msgs

    action = state.get('goblin_next_action', pick_goblin_action())
    msgs.append(f'Гоблин использует: {action["name"]}')
    msgs.extend(execute_goblin_action(goblin, player, action))

    if goblin.pop('_extra_turn', False) and player['hp'] > 0 and goblin['hp'] > 0:
        extra_act = pick_goblin_action()
        msgs.append(f'Дополнительный ход гоблина: {extra_act["name"]}')
        msgs.extend(execute_goblin_action(goblin, player, extra_act))

    msgs.extend(tick_effects_end_of_turn(goblin))
    end_of_round_bleed_decay(goblin)
    goblin['defending'] = False

    if player['hp'] <= 0:
        state['phase']  = 'finished'
        state['winner'] = 'goblin'
        msgs.append(f'{player["name"]} пал в бою...')
        return msgs

    state['goblin_next_action'] = pick_goblin_action()
    state['round'] = state.get('round', 1) + 1

    cds = player.get('artifact_cooldowns', {})
    for k in list(cds):
        cds[k] -= 1
        if cds[k] <= 0:
            del cds[k]

    msgs.extend(tick_effects_end_of_turn(player))
    end_of_round_bleed_decay(player)

    start_msgs = _start_player_turn(state)
    if start_msgs:
        msgs.extend(start_msgs)

    if player['hp'] <= 0:
        state['phase']  = 'finished'
        state['winner'] = 'goblin'
        msgs.append(f'{player["name"]} умер от эффектов...')

    return msgs


def _check_death(state, get_conn, user_id):
    player = state['player']
    enemy  = state['enemy']
    if enemy['hp'] <= 0 and state.get('winner') != 'goblin':
        state['phase']  = 'finished'
        state['winner'] = 'player'
        reward = _end_battle_rewards(state, get_conn, user_id)
        return True, reward
    if player['hp'] <= 0 or state.get('winner') == 'goblin':
        state['phase']  = 'finished'
        state['winner'] = 'goblin'
        return True, f'{player["name"]} пал в бою...'
    return False, ''


def _end_battle_rewards(state, get_conn, user_id):
    player     = state['player']
    fid        = player['id']
    xp_gain    = GOBLIN_DATA['reward_xp']
    money_gain = random.randint(*GOBLIN_DATA['reward_money_range'])
    fighter    = get_fighter_by_id(get_conn, fid)
    new_xp     = fighter['xp'] + xp_gain
    new_money  = fighter['money'] + money_gain
    old_level  = get_level_from_xp(fighter['xp'])
    new_level  = get_level_from_xp(new_xp)
    update_fighter(get_conn, fid, xp=new_xp, money=new_money, level=new_level)
    lvl_msg = f'\nНовый уровень: {new_level}!' if new_level > old_level else ''
    return f'Победа!\n\n+{xp_gain} XP\n+{money_gain} монет{lvl_msg}'


def _do_player_action(call, get_conn):
    user_id = call.from_user.id
    state   = load_battle_state(get_conn, user_id)
    if not state:
        return None, 'Бой не найден'
    if state.get('phase') != 'player_turn':
        return None, 'Сейчас не твой ход!'
    if state['player'].get('ap', 0) <= 0:
        return None, 'Нет АП! Нажми Завершить ход.'
    return state, None


# ================== РЕГИСТРАЦИЯ ==================

def register_arena_handlers(bot, get_conn):

    @bot.message_handler(commands=['arena'])
    def cmd_arena(message):
        user_id  = message.from_user.id
        fighters = get_arena_fighters(get_conn, user_id)
        text = fmt_fighter_list(fighters)
        kb   = InlineKeyboardMarkup(row_width=1)
        for slot in (1, 2, 3):
            if fighters[slot]:
                f  = fighters[slot]
                em = CLASS_EMOJI.get(f['class'], '')
                kb.add(InlineKeyboardButton(
                    f'{em} {f["name"]} (Ур.{f["level"]})',
                    callback_data=f'arena_view_{slot}'
                ))
            else:
                kb.add(InlineKeyboardButton(
                    f'+ Создать (слот {slot})',
                    callback_data=f'arena_create_{slot}'
                ))
        bot.send_message(message.chat.id, text, reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_view_'))
    def cb_arena_view(call):
        user_id = call.from_user.id
        slot    = int(call.data.split('_')[-1])
        fighter = get_fighter_by_slot(get_conn, user_id, slot)
        if not fighter:
            bot.answer_callback_query(call.id, 'Боец не найден')
            return
        _safe_edit(bot, call.message.chat.id, call.message.message_id,
                   fmt_fighter_card(fighter), fighter_card_keyboard(fighter))
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_create_'))
    def cb_arena_create(call):
        user_id = call.from_user.id
        slot    = int(call.data.split('_')[-1])
        pending_arena[user_id] = {
            'action': 'waiting_name', 'slot': slot,
            'chat_id': call.message.chat.id, 'msg_id': call.message.message_id,
        }
        try:
            bot.edit_message_text(
                f'Введи имя для своего бойца (макс. 25 символов):\nСлот: {slot}',
                call.message.chat.id, call.message.message_id
            )
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda m: m.from_user.id in pending_arena
                          and pending_arena[m.from_user.id].get('action') == 'waiting_name')
    def handle_arena_name(message):
        user_id = message.from_user.id
        name    = message.text.strip()[:25]
        if not name:
            bot.send_message(message.chat.id, 'Имя не может быть пустым!')
            return
        state          = pending_arena[user_id]
        state['name']  = name
        state['action'] = 'choosing_class'
        kb = InlineKeyboardMarkup(row_width=2)
        for cls, em in CLASS_EMOJI.items():
            kb.add(InlineKeyboardButton(f'{em} {cls}', callback_data=f'arena_cls_{cls}'))
        kb.add(InlineKeyboardButton('Изменить имя', callback_data=f'arena_rename_{state["slot"]}'))
        bot.send_message(message.chat.id, f'Имя бойца: {name}\n\nВыбери класс:', reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_rename_'))
    def cb_arena_rename(call):
        user_id = call.from_user.id
        slot    = int(call.data.split('_')[-1])
        pending_arena[user_id] = {
            'action': 'waiting_name', 'slot': slot,
            'chat_id': call.message.chat.id, 'msg_id': call.message.message_id,
        }
        try:
            bot.edit_message_text(
                f'Введи имя для своего бойца (макс. 25 символов):\nСлот: {slot}',
                call.message.chat.id, call.message.message_id
            )
        except Exception:
            bot.send_message(call.message.chat.id, 'Введи имя:')
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_cls_')
                                  and c.from_user.id in pending_arena
                                  and pending_arena[c.from_user.id].get('action') == 'choosing_class')
    def cb_arena_class(call):
        user_id = call.from_user.id
        cls     = call.data[len('arena_cls_'):]
        if cls not in CLASS_EMOJI:
            bot.answer_callback_query(call.id, 'Неизвестный класс')
            return
        state   = pending_arena.pop(user_id)
        name    = state.get('name', 'Безымянный')
        slot    = state.get('slot', 1)
        try:
            fighter = create_fighter(get_conn, user_id, slot, name, cls)
        except Exception as e:
            bot.answer_callback_query(call.id, f'Ошибка: {e}')
            return
        _safe_edit(bot, call.message.chat.id, call.message.message_id,
                   fmt_fighter_card(fighter), fighter_card_keyboard(fighter))
        bot.answer_callback_query(call.id, f'Боец {name} создан!')

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_card_'))
    def cb_arena_card(call):
        user_id = call.from_user.id
        fid     = int(call.data.split('_')[-1])
        fighter = get_fighter_by_id(get_conn, fid)
        if not fighter or fighter.get('user_id') != user_id:
            bot.answer_callback_query(call.id, 'Боец не найден')
            return
        _safe_edit(bot, call.message.chat.id, call.message.message_id,
                   fmt_fighter_card(fighter), fighter_card_keyboard(fighter))
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_switch_'))
    def cb_arena_switch(call):
        user_id  = call.from_user.id
        fighters = get_arena_fighters(get_conn, user_id)
        text = fmt_fighter_list(fighters)
        kb   = InlineKeyboardMarkup(row_width=1)
        for slot in (1, 2, 3):
            if fighters[slot]:
                f  = fighters[slot]
                em = CLASS_EMOJI.get(f['class'], '')
                kb.add(InlineKeyboardButton(
                    f'{em} {f["name"]} (Ур.{f["level"]})',
                    callback_data=f'arena_view_{slot}'
                ))
            else:
                kb.add(InlineKeyboardButton(
                    f'+ Создать (слот {slot})',
                    callback_data=f'arena_create_{slot}'
                ))
        _safe_edit(bot, call.message.chat.id, call.message.message_id, text, kb)
        bot.answer_callback_query(call.id)

    # --- Заглушки ---

    @bot.callback_query_handler(func=lambda c: any(c.data.startswith(p) for p in
                                  ('arena_adv_', 'arena_pvp_', 'arena_leaders_', 'arena_equip_')))
    def cb_stub(call):
        bot.answer_callback_query(call.id, 'Ещё в разработке!', show_alert=True)

    @bot.callback_query_handler(func=lambda c: c.data in ('arena_skills', 'arena_spells'))
    def cb_stub_skills(call):
        bot.answer_callback_query(call.id, 'Ещё в разработке!', show_alert=True)

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_inv_empty')
    def cb_inv_empty(call):
        bot.answer_callback_query(call.id)

    # ================== СЛУЧАЙНЫЙ БОЙ ==================

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_rand_'))
    def cb_arena_random_battle(call):
        user_id = call.from_user.id
        fid     = int(call.data.split('_')[-1])
        fighter = get_fighter_by_id(get_conn, fid)
        if not fighter or fighter.get('user_id') != user_id:
            bot.answer_callback_query(call.id, 'Боец не найден')
            return
        existing = load_battle_state(get_conn, user_id)
        if existing and existing.get('phase') not in ('finished', None):
            bot.answer_callback_query(call.id, 'У тебя уже есть активный бой!', show_alert=True)
            return

        state = init_battle(fighter)
        p_spd = state['player'].get('speed', 5)
        e_spd = state['enemy'].get('speed', 5)

        if e_spd > p_spd:
            # Гоблин ходит первым
            state['phase'] = 'goblin_turn'
            state['log']   = [f'Вы встретили {state["enemy"]["name"]}!\nГоблин быстрее и ходит первым!']
            save_battle_state(get_conn, user_id, state)
            goblin_msgs  = _execute_goblin_turn(state)
            log_text     = '\n'.join(goblin_msgs)
            finished, rt = _check_death(state, get_conn, user_id)
            save_battle_state(get_conn, user_id, state)
            if finished:
                full = fmt_battle(state) + f'\n\n{rt}'
                _safe_edit(bot, call.message.chat.id, call.message.message_id,
                           full, finished_keyboard(fid))
            else:
                bot.send_message(call.message.chat.id, f'Ход гоблина:\n{log_text}')
                state['log'] = [f'Вы встретили {state["enemy"]["name"]}! Гоблин походил первым.']
                save_battle_state(get_conn, user_id, state)
                _safe_edit(bot, call.message.chat.id, call.message.message_id,
                           fmt_battle(state), battle_keyboard(state))
        else:
            # Игрок ходит первым
            state['log'] = [f'Вы встретили {state["enemy"]["name"]}!\nОн собирается: {state["goblin_next_action"]["name"]}']
            save_battle_state(get_conn, user_id, state)
            _safe_edit(bot, call.message.chat.id, call.message.message_id,
                       fmt_battle(state), battle_keyboard(state))
        bot.answer_callback_query(call.id)

    # ================== ДЕЙСТВИЯ ИГРОКА ==================

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_atk')
    def cb_arena_attack(call):
        user_id      = call.from_user.id
        state, err   = _do_player_action(call, get_conn)
        if err:
            bot.answer_callback_query(call.id, err, show_alert=True)
            return
        player = state['player']
        enemy  = state['enemy']
        result = do_attack(player, enemy, True)
        msgs   = result['messages']
        # Двойной удар
        for slot in ['artifact1', 'artifact2']:
            art = player.get(slot)
            if art and art in ARTIFACTS and ARTIFACTS[art]['effect_key'] == 'double_strike_ring':
                chance = 30 if player.get('dex', 0) >= 10 else 20
                if random.randint(1, 100) <= chance:
                    msgs.append('Двойной удар!')
                    r2 = do_attack(player, enemy, True)
                    msgs.extend(r2['messages'])
        player['ap'] -= 1
        player['defending'] = False
        finished, rt = _check_death(state, get_conn, user_id)
        state['log'] = ['\n'.join(msgs)]
        save_battle_state(get_conn, user_id, state)
        if finished:
            _safe_edit(bot, call.message.chat.id, call.message.message_id,
                       fmt_battle(state) + f'\n\n{rt}', finished_keyboard(player['id']))
        else:
            _safe_edit(bot, call.message.chat.id, call.message.message_id,
                       fmt_battle(state), battle_keyboard(state))
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_def')
    def cb_arena_defend(call):
        user_id    = call.from_user.id
        state, err = _do_player_action(call, get_conn)
        if err:
            bot.answer_callback_query(call.id, err, show_alert=True)
            return
        player = state['player']
        player['defending'] = True
        player['ap'] -= 1
        state['log'] = ['Ты занял защитную позицию! Следующий урон -50%.']
        save_battle_state(get_conn, user_id, state)
        _safe_edit(bot, call.message.chat.id, call.message.message_id,
                   fmt_battle(state), battle_keyboard(state))
        bot.answer_callback_query(call.id)

    # ─── Завершить ход → сразу ход врага ────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_end_turn')
    def cb_arena_end_turn(call):
        user_id = call.from_user.id
        state   = load_battle_state(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id, 'Бой не найден')
            return
        if state.get('phase') != 'player_turn':
            bot.answer_callback_query(call.id, 'Сейчас не твой ход!')
            return

        bot.answer_callback_query(call.id)

        # 1. Сразу убираем кнопки — показываем что идёт ход врага
        state['phase'] = 'goblin_turn'
        state['log']   = ['⏳ Ход завершён...']
        save_battle_state(get_conn, user_id, state)
        _safe_edit(bot, call.message.chat.id, call.message.message_id,
                   fmt_battle(state))  # без кнопок

        # 2. Выполняем ход гоблина
        goblin_msgs  = _execute_goblin_turn(state)
        log_text     = '\n'.join(goblin_msgs) if goblin_msgs else '...'
        finished, rt = _check_death(state, get_conn, user_id)
        save_battle_state(get_conn, user_id, state)

        # 3. Отправляем отдельное сообщение с действиями врага
        enemy_name = state['enemy']['name']
        bot.send_message(call.message.chat.id, f'{enemy_name}:\n\n{log_text}')

        # 4. Отправляем новое сообщение боя
        if finished:
            bot.send_message(
                call.message.chat.id,
                fmt_battle(state) + f'\n\n{rt}',
                reply_markup=finished_keyboard(state['player']['id'])
            )
        else:
            state['log'] = [
                f'Раунд {state.get("round", 1)}. Твой ход!\n'
                f'Гоблин собирается: {state["goblin_next_action"]["name"]}'
            ]
            save_battle_state(get_conn, user_id, state)
            bot.send_message(
                call.message.chat.id,
                fmt_battle(state),
                reply_markup=battle_keyboard(state)
            )

    # ─── Сбежать ─────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_run')
    def cb_arena_run(call):
        user_id = call.from_user.id
        state   = load_battle_state(get_conn, user_id)
        if not state or state.get('phase') != 'player_turn':
            bot.answer_callback_query(call.id, 'Нельзя сбежать сейчас!')
            return
        player     = state['player']
        run_chance = max(30, min(80, 50 + (player.get('speed', 5) - state['enemy'].get('speed', 5)) * 5))
        if random.randint(1, 100) <= run_chance:
            clear_battle_state(get_conn, user_id)
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton('Меню арены', callback_data=f'arena_switch_{player["id"]}'))
            _safe_edit(bot, call.message.chat.id, call.message.message_id,
                       f'{player["name"]} успешно сбежал!', kb)
        else:
            state['phase'] = 'goblin_turn'
            state['log']   = ['Не удалось сбежать! Гоблин атакует!']
            save_battle_state(get_conn, user_id, state)
            goblin_msgs  = _execute_goblin_turn(state)
            log_text     = '\n'.join(goblin_msgs)
            finished, rt = _check_death(state, get_conn, user_id)
            save_battle_state(get_conn, user_id, state)
            bot.send_message(call.message.chat.id, f'Ход {state["enemy"]["name"]}:\n\n{log_text}')
            if finished:
                _safe_edit(bot, call.message.chat.id, call.message.message_id,
                           fmt_battle(state) + f'\n\n{rt}', finished_keyboard(player['id']))
            else:
                state['log'] = ['Гоблин атаковал в ответ на попытку побега!']
                save_battle_state(get_conn, user_id, state)
                _safe_edit(bot, call.message.chat.id, call.message.message_id,
                           fmt_battle(state), battle_keyboard(state))
        bot.answer_callback_query(call.id)

    # ─── Стойки ──────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_stance')
    def cb_stance_menu(call):
        state = load_battle_state(get_conn, call.from_user.id)
        if not state:
            bot.answer_callback_query(call.id, 'Бой не найден')
            return
        _safe_edit(bot, call.message.chat.id, call.message.message_id,
                   fmt_stance_menu(state['player'].get('stance', 'normal')), stance_keyboard())
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_st_'))
    def cb_set_stance(call):
        user_id = call.from_user.id
        state   = load_battle_state(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id, 'Бой не найден')
            return
        mapping = {
            'arena_st_battle':  'battle',
            'arena_st_defense': 'defense',
            'arena_st_precise': 'precise',
            'arena_st_dodge':   'dodge',
        }
        state['player']['stance'] = mapping.get(call.data, 'normal')
        save_battle_state(get_conn, user_id, state)
        _safe_edit(bot, call.message.chat.id, call.message.message_id,
                   fmt_battle(state), battle_keyboard(state))
        bot.answer_callback_query(call.id, 'Стойка изменена')

    # ─── Инвентарь ───────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_inv')
    def cb_inventory(call):
        state = load_battle_state(get_conn, call.from_user.id)
        if not state:
            bot.answer_callback_query(call.id, 'Бой не найден')
            return
        _safe_edit(bot, call.message.chat.id, call.message.message_id,
                   fmt_inventory(state), inventory_keyboard(state))
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_inv_weapon')
    def cb_inv_weapon(call):
        state = load_battle_state(get_conn, call.from_user.id)
        if not state:
            bot.answer_callback_query(call.id, 'Бой не найден')
            return
        weapon_name = state['player'].get('weapon', 'Нет')
        if not weapon_name or weapon_name not in WEAPONS:
            bot.answer_callback_query(call.id, 'Оружие не найдено', show_alert=True)
            return
        w = WEAPONS[weapon_name]
        stat_map  = {'str': 'Сила', 'dex': 'Ловкость', 'int': 'Интеллект'}
        stat_name = stat_map.get(w['stat'], w['stat'])
        ability   = w.get('ability') or 'нет'
        text = (
            f'{weapon_name}\n'
            f'{w["rarity"]}\n\n'
            f'Основная характеристика: {stat_name}\n'
            f'Тип: {w["type"]}\n'
            f'Урон: {w["base_dmg"]} + {stat_name}\n'
            f'Способность: {ability}'
        )
        from arena_data import WEAPON_STICKERS
        sticker_id = WEAPON_STICKERS.get(weapon_name)
        if sticker_id:
            try:
                bot.send_sticker(call.message.chat.id, sticker_id)
            except Exception as e:
                print(f'Sticker error: {e}')
        bot.send_message(call.message.chat.id, text)
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_use_art_'))
    def cb_use_artifact(call):
        user_id    = call.from_user.id
        state, err = _do_player_action(call, get_conn)
        if err:
            bot.answer_callback_query(call.id, err, show_alert=True)
            return
        art_num  = int(call.data.split('_')[-1])
        player   = state['player']
        enemy    = state['enemy']
        art_name = player.get(f'artifact{art_num}')
        if not art_name or art_name not in ARTIFACTS:
            bot.answer_callback_query(call.id, 'Артефакт не найден', show_alert=True)
            return
        if ARTIFACTS[art_name]['type'] != 'active':
            bot.answer_callback_query(call.id, 'Пассивный артефакт — работает автоматически.', show_alert=True)
            return
        msgs = use_active_artifact(player, enemy, art_name)
        player['ap'] -= 1
        finished, rt = _check_death(state, get_conn, user_id)
        state['log'] = ['\n'.join(msgs)]
        save_battle_state(get_conn, user_id, state)
        if finished:
            _safe_edit(bot, call.message.chat.id, call.message.message_id,
                       fmt_battle(state) + f'\n\n{rt}', finished_keyboard(player['id']))
        else:
            _safe_edit(bot, call.message.chat.id, call.message.message_id,
                       fmt_inventory(state), inventory_keyboard(state))
        bot.answer_callback_query(call.id, 'Артефакт использован')

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_back_battle')
    def cb_back_battle(call):
        state = load_battle_state(get_conn, call.from_user.id)
        if not state:
            bot.answer_callback_query(call.id, 'Бой не найден')
            return
        _safe_edit(bot, call.message.chat.id, call.message.message_id,
                   fmt_battle(state), battle_keyboard(state))
        bot.answer_callback_query(call.id)
