# ============================================================
#  arena_handlers.py  — Telegram-хэндлеры для Арены
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


# ─── Хранилище состояний ввода (ожидание текста от пользователя)
# pending_arena[user_id] = {'action': str, 'slot': int, 'chat_id': int, 'msg_id': int, ...}
pending_arena = {}


# ═══════════════════════════════════════════════════════════
#  Форматирование текстов
# ═══════════════════════════════════════════════════════════

def fmt_fighter_list(fighters: dict) -> str:
    """Текст меню со списком бойцов."""
    lines = ['— – - 🔵 ⚔️ А Р Е Н А ⚔️ 🔴 - – —\n', 'Твои бойцы:\n']
    for slot in (1, 2, 3):
        f = fighters[slot]
        num = ['1️⃣', '2️⃣', '3️⃣'][slot - 1]
        if f:
            cls   = f['class']
            emoji = CLASS_EMOJI.get(cls, '👤')
            lvl   = f['level']
            lines.append(f'{num} {emoji} {f["name"]} | {cls} Ур.{lvl}')
        else:
            lines.append(f'{num} [Пусто]')
    return '\n'.join(lines)


def fmt_fighter_card(fighter_row: dict) -> str:
    """Карточка персонажа."""
    cls   = fighter_row['class']
    lvl   = fighter_row['level']
    xp    = fighter_row['xp']
    sp    = fighter_row['sp']
    name  = fighter_row['name']
    emoji = CLASS_EMOJI.get(cls, '👤')

    s    = fighter_row['str']
    d    = fighter_row['dex']
    co   = fighter_row['con']
    i    = fighter_row['intel']
    ch   = fighter_row['cha']
    lk   = fighter_row['lck']

    max_hp   = calc_max_hp(cls, lvl, co)
    max_mana = calc_max_mana(cls, lvl, i, ch)
    kd       = calc_kd(d)
    speed    = calc_speed(cls, d, lk)
    xp_next  = get_xp_to_next(xp)

    art1 = fighter_row.get('artifact1') or 'Нет'
    art2 = fighter_row.get('artifact2') or 'Нет'
    weapon = fighter_row.get('weapon') or 'Нет'

    return (
        f'— – - 🔵 ⚔️ А Р Е Н А ⚔️ 🔴 - – —\n\n'
        f'🎖️ Рекорд: {fighter_row.get("record_floor", 0)} этаж\n\n'
        f'• - - - - - - - - - - - - - - - - - •\n\n'
        f'— - - {name} - - —\n'
        f'Класс: {emoji} {cls}\n'
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


def fighter_card_keyboard(fighter_row: dict) -> InlineKeyboardMarkup:
    cls = fighter_row['class']
    emoji = CLASS_EMOJI.get(cls, '👤')
    fid   = fighter_row['id']
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('🏞️ Приключение', callback_data=f'arena_adv_{fid}'),
        InlineKeyboardButton('❔ Случайный бой ⚔️', callback_data=f'arena_rand_{fid}'),
    )
    kb.add(
        InlineKeyboardButton('👤 Бой с игроком ⚔️', callback_data=f'arena_pvp_{fid}'),
        InlineKeyboardButton(f'{emoji} Мой Боец', callback_data=f'arena_card_{fid}'),
    )
    kb.add(
        InlineKeyboardButton('🎒 Снаряжение', callback_data=f'arena_equip_{fid}'),
        InlineKeyboardButton('🏆 Лидеры', callback_data=f'arena_leaders_{fid}'),
    )
    kb.add(
        InlineKeyboardButton('🔁 Поменять персонажа', callback_data=f'arena_switch_{fid}'),
    )
    return kb


def fmt_battle(state: dict) -> str:
    p = state['player']
    e = state['enemy']
    ap = p.get('ap', 2)

    stance_names = {
        'normal': 'Нейтральная',
        'battle': '⚔️ Боевая',
        'defense': '🛡️ Защитная',
        'precise': '🎯 Точная',
        'dodge': '👣 Уклонения',
    }
    stance = stance_names.get(p.get('stance', 'normal'), 'Нейтральная')

    p_effs = format_effects(p.get('effects', {}))
    e_effs = format_effects(e.get('effects', {}))

    log_lines = state.get('log', [])
    log_text  = log_lines[-1] if log_lines else '...'

    next_action = state.get('goblin_next_action', {})
    next_act_name = next_action.get('name', '???')

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
        f'📜 Ход боя:\n{log_text}\n\n'
        f'🔮 Следующий ход врага: {next_act_name}'
    )


def battle_keyboard(state: dict) -> InlineKeyboardMarkup:
    p   = state['player']
    cls = p.get('class', '')
    kb  = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('⚔️ Атака', callback_data='arena_atk'),
        InlineKeyboardButton('🛡️ Защита', callback_data='arena_def'),
    )
    row = [InlineKeyboardButton('✨ Навыки', callback_data='arena_skills')]
    if cls in MAGIC_CLASSES:
        row.append(InlineKeyboardButton('🔮 Заклинания', callback_data='arena_spells'))
    kb.add(*row)
    kb.add(
        InlineKeyboardButton('🧘 Стойка', callback_data='arena_stance'),
        InlineKeyboardButton('🎒 Инвентарь', callback_data='arena_inv'),
    )
    kb.add(InlineKeyboardButton('🏃 Сбежать', callback_data='arena_run'))
    return kb


def fmt_inventory(state: dict) -> str:
    p = state['player']
    art1 = p.get('artifact1') or 'Нет'
    art2 = p.get('artifact2') or 'Нет'
    weapon = p.get('weapon') or 'Нет'

    # Показываем кулдауны
    cd = p.get('artifact_cooldowns', {})
    def cd_str(art_name):
        if not art_name or art_name == 'Нет':
            return ''
        if art_name in ARTIFACTS:
            key = ARTIFACTS[art_name]['effect_key']
            rem = cd.get(key, 0)
            if rem > 0:
                return f' ⏳{rem}'
        return ''

    return (
        f'— – - 🎒 И Н В Е Н Т А Р Ь - – —\n\n'
        f'👤 {p["name"]}: {CLASS_EMOJI.get(p["class"], "")} {p["class"]} | Ур.{p["level"]}\n\n'
        f'💰 Золото: {p.get("money", 0)}\n\n'
        f'• – – – – – – – – – – – – – – – •\n'
        f'⚔️ Снаряжение:\n\n'
        f'Оружие: {weapon}\n\n'
        f'Артефакт №1: {art1}{cd_str(art1)}\n'
        f'Артефакт №2: {art2}{cd_str(art2)}\n\n'
        f'• – – – – – – – – – – – – – – – •'
    )


def inventory_keyboard(state: dict) -> InlineKeyboardMarkup:
    p  = state['player']
    kb = InlineKeyboardMarkup(row_width=1)
    weapon = p.get('weapon') or 'Нет'
    kb.add(InlineKeyboardButton(f'🗡️ {weapon}', callback_data='arena_inv_weapon'))

    for i, slot in enumerate(['artifact1', 'artifact2'], 1):
        art = p.get(slot)
        if art:
            kb.add(InlineKeyboardButton(f'{art}', callback_data=f'arena_use_art_{i}'))
        else:
            kb.add(InlineKeyboardButton(f'Артефакт №{i}: Нет', callback_data=f'arena_inv_empty'))
    kb.add(InlineKeyboardButton('🔙 Назад', callback_data='arena_back_battle'))
    return kb


def fmt_stance_menu(current: str) -> str:
    stance_names = {
        'normal': 'Нейтральная',
        'battle': '⚔️ Боевая',
        'defense': '🛡️ Защитная',
        'precise': '🎯 Точная',
        'dodge': '👣 Уклонения',
    }
    cur_name = stance_names.get(current, 'Нейтральная')
    return (
        f'— 🧘 С Т О Й К И —\n\n'
        f'Текущая: {cur_name}\n\n'
        f'• - - - - - - - •\n'
        f'⚔️ Боевая стойка\n+2 к урону\n+5% к шансу крита\n-1 к телосложению\n'
        f'• - - - - - - - •\n'
        f'🛡️ Защитная стойка\n-20% входящего урона\n+2 к телосложению\n-2 к урону\n'
        f'• - - - - - - - •\n'
        f'🎯 Точная стойка\n+10% к шансу попадания дальнобойных атак\n-1 к скорости\n'
        f'• - - - - - - - •\n'
        f'👣 Стойка уклонения\n+15% к уклонению\n+1 к скорости\n-2 к урону\n'
        f'• - - - - - - - •'
    )


def stance_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('⚔️ Боевая',     callback_data='arena_st_battle'),
        InlineKeyboardButton('🛡️ Защитная',   callback_data='arena_st_defense'),
        InlineKeyboardButton('🎯 Точная',     callback_data='arena_st_precise'),
        InlineKeyboardButton('👣 Уклонение',  callback_data='arena_st_dodge'),
    )
    kb.add(InlineKeyboardButton('🔙 Назад', callback_data='arena_back_battle'))
    return kb


# ═══════════════════════════════════════════════════════════
#  Игровая логика
# ═══════════════════════════════════════════════════════════

def process_goblin_turn_full(state: dict) -> list[str]:
    """
    Выполняет ход гоблина и обновляет состояние.
    Возвращает список строк для лога.
    """
    msgs = []
    goblin = state['enemy']
    player = state['player']
    action = state['goblin_next_action']

    # Начало хода гоблина: эффекты
    msgs.extend(tick_effects_start_of_turn(goblin))

    if goblin['hp'] <= 0:
        state['phase']  = 'finished'
        state['winner'] = 'player'
        return msgs

    # Действие гоблина
    act_msgs = execute_goblin_action(goblin, player, action)
    msgs.extend(act_msgs)

    # Дополнительный ход гоблина (быстрый выпад + крит)
    if goblin.pop('_extra_turn', False) and player['hp'] > 0 and goblin['hp'] > 0:
        next_act = pick_goblin_action()
        extra_msgs = execute_goblin_action(goblin, player, next_act)
        msgs.extend(extra_msgs)

    # Конец хода гоблина
    msgs.extend(tick_effects_end_of_turn(goblin))
    end_of_round_bleed_decay(goblin)
    goblin['defending'] = False

    if player['hp'] <= 0:
        state['phase']  = 'finished'
        state['winner'] = 'goblin'
        msgs.append(f'💀 {player["name"]} пал в бою...')
        return msgs

    # Новый ход игрока
    state['round'] += 1
    player['ap']       = 2
    player['defending'] = False

    # Начало хода игрока: эффекты
    msgs.extend(tick_effects_start_of_turn(player))

    if player['hp'] <= 0:
        state['phase']  = 'finished'
        state['winner'] = 'goblin'
        msgs.append(f'💀 {player["name"]} умер от эффектов...')
        return msgs

    # Конец хода игрока (часть эффектов)
    msgs.extend(tick_effects_end_of_turn(player))
    end_of_round_bleed_decay(player)

    # Кулдауны артефактов
    cds = player.get('artifact_cooldowns', {})
    for k in list(cds.keys()):
        if cds[k] > 0:
            cds[k] -= 1
        if cds[k] <= 0:
            del cds[k]

    # Тёплый шарф: +1 щит
    for art_slot in ['artifact1', 'artifact2']:
        art = player.get(art_slot)
        if art and art in ARTIFACTS and ARTIFACTS[art]['effect_key'] == 'warm_scarf':
            player['shield'] = player.get('shield', 0) + 1

    # Следующее действие гоблина
    state['goblin_next_action'] = pick_goblin_action()
    state['phase'] = 'player_turn'

    return msgs


def check_double_strike(player: dict, enemy: dict) -> list[str]:
    """Проверить артефакт 'Кольцо двойного удара'"""
    msgs = []
    for slot in ['artifact1', 'artifact2']:
        art = player.get(slot)
        if art and art in ARTIFACTS and ARTIFACTS[art]['effect_key'] == 'double_strike_ring':
            chance = 30 if player.get('dex', 0) >= 10 else 20
            if random.randint(1, 100) <= chance:
                msgs.append('💍 Двойной удар!')
                weapon_name = player.get('weapon')
                weapon_data = WEAPONS.get(weapon_name)
                if weapon_data:
                    result = do_attack(player, enemy, True)
                    msgs.extend(result['messages'])
    return msgs


def end_battle_rewards(state: dict, get_conn, user_id: int) -> str:
    """Выдаёт награды и обновляет бойца в БД."""
    player = state['player']
    fid    = player['id']

    xp_gain    = GOBLIN_DATA['reward_xp']
    money_gain = random.randint(*GOBLIN_DATA['reward_money_range'])

    # Бонусы артефактов к деньгам
    for slot in ['artifact1', 'artifact2']:
        art = player.get(slot)
        if art and art in ARTIFACTS:
            key = ARTIFACTS[art]['effect_key']
            if key in ('old_coin', 'potted_token'):
                money_gain = int(money_gain * 1.02)

    # Бонус к XP от Узелка памяти
    for slot in ['artifact1', 'artifact2']:
        art = player.get(slot)
        if art and art in ARTIFACTS and ARTIFACTS[art]['effect_key'] == 'memory_knot':
            xp_gain = int(xp_gain * 1.01)

    # Получаем текущие значения из БД
    fighter = get_fighter_by_id(get_conn, fid)
    new_xp    = fighter['xp'] + xp_gain
    new_money = fighter['money'] + money_gain
    old_level = get_level_from_xp(fighter['xp'])
    new_level = get_level_from_xp(new_xp)

    update_fighter(get_conn, fid, xp=new_xp, money=new_money, level=new_level)

    lvl_msg = ''
    if new_level > old_level:
        lvl_msg = f'\n🎉 Новый уровень: {new_level}!'

    return (
        f'🏆 Победа!\n\n'
        f'+{xp_gain} XP\n'
        f'+{money_gain} 💰\n'
        f'{lvl_msg}'
    )


# ═══════════════════════════════════════════════════════════
#  Регистрация хэндлеров
# ═══════════════════════════════════════════════════════════

def register_arena_handlers(bot, get_conn):
    """Регистрирует все хэндлеры арены."""

    # ─── /arena ────────────────────────────────────────────

    @bot.message_handler(commands=['arena'])
    def cmd_arena(message):
        user_id = message.from_user.id
        fighters = get_arena_fighters(get_conn, user_id)

        text = fmt_fighter_list(fighters)
        kb   = InlineKeyboardMarkup(row_width=1)

        for slot in (1, 2, 3):
            if fighters[slot]:
                f = fighters[slot]
                cls_em = CLASS_EMOJI.get(f['class'], '👤')
                kb.add(InlineKeyboardButton(
                    f'👁️ {cls_em} {f["name"]} (Ур.{f["level"]})',
                    callback_data=f'arena_view_{slot}'
                ))
            else:
                kb.add(InlineKeyboardButton(
                    f'➕ Создать (слот {slot})',
                    callback_data=f'arena_create_{slot}'
                ))

        bot.send_message(message.chat.id, text, reply_markup=kb)


    # ─── Просмотр / выбор бойца ────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_view_'))
    def cb_arena_view(call):
        user_id = call.from_user.id
        slot    = int(call.data.split('_')[-1])
        fighter = get_fighter_by_slot(get_conn, user_id, slot)
        if not fighter:
            bot.answer_callback_query(call.id, 'Боец не найден')
            return

        text = fmt_fighter_card(fighter)
        kb   = fighter_card_keyboard(fighter)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)
        bot.answer_callback_query(call.id)


    # ─── Создание бойца: шаг 1 — запрос имени ──────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_create_'))
    def cb_arena_create(call):
        user_id = call.from_user.id
        slot    = int(call.data.split('_')[-1])

        pending_arena[user_id] = {
            'action':  'waiting_name',
            'slot':    slot,
            'chat_id': call.message.chat.id,
            'msg_id':  call.message.message_id,
        }

        try:
            bot.edit_message_text(
                f'📝 Введи имя для своего бойца (макс. 25 символов):\n\n'
                f'Слот: {slot}',
                call.message.chat.id, call.message.message_id
            )
        except:
            pass
        bot.answer_callback_query(call.id)


    # ─── Шаг 2: получить имя и показать выбор класса ────────

    @bot.message_handler(func=lambda m: m.from_user.id in pending_arena
                          and pending_arena[m.from_user.id].get('action') == 'waiting_name')
    def handle_arena_name(message):
        user_id = message.from_user.id
        name    = message.text.strip()[:25]

        if not name:
            bot.send_message(message.chat.id, '❌ Имя не может быть пустым!')
            return

        state = pending_arena[user_id]
        state['name']   = name
        state['action'] = 'choosing_class'

        kb = InlineKeyboardMarkup(row_width=2)
        for cls, em in CLASS_EMOJI.items():
            kb.add(InlineKeyboardButton(f'{em} {cls}', callback_data=f'arena_cls_{cls}'))
        kb.add(InlineKeyboardButton('📝🔙 Изменить имя', callback_data=f'arena_rename_{state["slot"]}'))

        bot.send_message(
            message.chat.id,
            f'👤 Имя бойца: {name}\n\nВыбери класс бойца:',
            reply_markup=kb
        )


    # ─── Переименовать (вернуться к вводу имени) ────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_rename_'))
    def cb_arena_rename(call):
        user_id = call.from_user.id
        slot    = int(call.data.split('_')[-1])
        pending_arena[user_id] = {
            'action':  'waiting_name',
            'slot':    slot,
            'chat_id': call.message.chat.id,
            'msg_id':  call.message.message_id,
        }
        try:
            bot.edit_message_text(
                f'📝 Введи имя для своего бойца (макс. 25 символов):\nСлот: {slot}',
                call.message.chat.id, call.message.message_id
            )
        except:
            bot.send_message(call.message.chat.id,
                             f'📝 Введи имя для своего бойца (макс. 25 символов):')
        bot.answer_callback_query(call.id)


    # ─── Шаг 3: выбор класса → создание бойца ───────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_cls_')
                                  and c.from_user.id in pending_arena
                                  and pending_arena[c.from_user.id].get('action') == 'choosing_class')
    def cb_arena_class(call):
        user_id = call.from_user.id
        cls     = call.data[len('arena_cls_'):]

        if cls not in CLASS_EMOJI:
            bot.answer_callback_query(call.id, 'Неизвестный класс')
            return

        state = pending_arena.pop(user_id)
        name  = state.get('name', 'Безымянный')
        slot  = state.get('slot', 1)

        try:
            fighter = create_fighter(get_conn, user_id, slot, name, cls)
        except Exception as e:
            bot.answer_callback_query(call.id, f'Ошибка: {e}')
            return

        text = fmt_fighter_card(fighter)
        kb   = fighter_card_keyboard(fighter)

        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)
        bot.answer_callback_query(call.id, f'✅ Боец {name} создан!')


    # ─── Карточка бойца (повторный просмотр) ────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_card_'))
    def cb_arena_card(call):
        user_id = call.from_user.id
        fid     = int(call.data.split('_')[-1])
        fighter = get_fighter_by_id(get_conn, fid)
        if not fighter or fighter.get('user_id') != user_id:
            bot.answer_callback_query(call.id, 'Боец не найден')
            return
        text = fmt_fighter_card(fighter)
        kb   = fighter_card_keyboard(fighter)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
        except:
            pass
        bot.answer_callback_query(call.id)


    # ─── Переключить персонажа ───────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_switch_'))
    def cb_arena_switch(call):
        user_id  = call.from_user.id
        fighters = get_arena_fighters(get_conn, user_id)
        text = fmt_fighter_list(fighters)
        kb   = InlineKeyboardMarkup(row_width=1)
        for slot in (1, 2, 3):
            if fighters[slot]:
                f = fighters[slot]
                em = CLASS_EMOJI.get(f['class'], '👤')
                kb.add(InlineKeyboardButton(
                    f'👁️ {em} {f["name"]} (Ур.{f["level"]})',
                    callback_data=f'arena_view_{slot}'
                ))
            else:
                kb.add(InlineKeyboardButton(
                    f'➕ Создать (слот {slot})',
                    callback_data=f'arena_create_{slot}'
                ))
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)
        bot.answer_callback_query(call.id)


    # ─── Заглушки (в разработке) ─────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_adv_'))
    def cb_arena_adv(call):
        bot.answer_callback_query(call.id, '🚧 Приключения пока в разработке!', show_alert=True)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_pvp_'))
    def cb_arena_pvp(call):
        bot.answer_callback_query(call.id, '🚧 Бой с игроком пока в разработке!', show_alert=True)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_leaders_'))
    def cb_arena_leaders(call):
        bot.answer_callback_query(call.id, '🚧 Рейтинг пока в разработке!', show_alert=True)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_equip_'))
    def cb_arena_equip(call):
        bot.answer_callback_query(call.id, '🚧 Магазин снаряжения пока в разработке!', show_alert=True)

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_skills')
    def cb_arena_skills(call):
        bot.answer_callback_query(call.id, '🚧 Навыки ещё в разработке!', show_alert=True)

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_spells')
    def cb_arena_spells(call):
        bot.answer_callback_query(call.id, '🚧 Заклинания ещё в разработке!', show_alert=True)

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_inv_empty')
    def cb_arena_inv_empty(call):
        bot.answer_callback_query(call.id, 'Слот артефакта пуст', show_alert=False)

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_inv_weapon')
    def cb_arena_inv_weapon(call):
        state = load_battle_state(get_conn, call.from_user.id)
        if not state:
            bot.answer_callback_query(call.id, 'Бой не найден')
            return
        weapon_name = state['player'].get('weapon', 'Нет')
        if weapon_name and weapon_name in WEAPONS:
            w = WEAPONS[weapon_name]
            stat_map = {'str': 'Сила', 'dex': 'Ловкость', 'int': 'Интеллект'}
            stat_name = stat_map.get(w['stat'], w['stat'])
            ability = w.get('ability') or '—'
            text = (
                f'{weapon_name}\n'
                f'— {w["rarity"]} —\n\n'
                f'Тип: {w["type"]}\n'
                f'Основная характеристика: {stat_name}\n'
                f'Урон: {w["base_dmg"]} + {stat_name.upper()}\n'
                f'Способность: {ability}'
            )
            bot.answer_callback_query(call.id, text, show_alert=True)
        else:
            bot.answer_callback_query(call.id, f'Оружие: {weapon_name}', show_alert=True)


    # ══════════════════════════════════════════════════════
    #  СЛУЧАЙНЫЙ БОЙ
    # ══════════════════════════════════════════════════════

    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_rand_'))
    def cb_arena_random_battle(call):
        user_id = call.from_user.id
        fid     = int(call.data.split('_')[-1])
        fighter = get_fighter_by_id(get_conn, fid)

        if not fighter or fighter.get('user_id') != user_id:
            bot.answer_callback_query(call.id, 'Боец не найден')
            return

        # Проверяем активный бой
        existing = load_battle_state(get_conn, user_id)
        if existing and existing.get('phase') != 'finished':
            bot.answer_callback_query(call.id, 'У тебя уже есть активный бой!', show_alert=True)
            return

        state = init_battle(fighter)
        save_battle_state(get_conn, user_id, state)

        text = fmt_battle(state)
        kb   = battle_keyboard(state)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)
        bot.answer_callback_query(call.id)


    # ─── Атака ──────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_atk')
    def cb_arena_attack(call):
        user_id = call.from_user.id
        state   = load_battle_state(get_conn, user_id)
        if not state or state['phase'] != 'player_turn':
            bot.answer_callback_query(call.id, 'Не твой ход!')
            return

        player = state['player']
        enemy  = state['enemy']

        if player.get('ap', 0) <= 0:
            bot.answer_callback_query(call.id, 'Нет АП!', show_alert=True)
            return

        # Атакуем
        result = do_attack(player, enemy, True)
        msgs   = result['messages']

        # Двойной удар
        double_msgs = check_double_strike(player, enemy)
        msgs.extend(double_msgs)

        player['ap'] -= 1
        player['defending'] = False

        log_text = '\n'.join(msgs)

        # Враг умер?
        if enemy['hp'] <= 0:
            state['phase']  = 'finished'
            state['winner'] = 'player'
            reward_text = end_battle_rewards(state, get_conn, user_id)
            state['log'] = [log_text + f'\n\n{reward_text}']
            save_battle_state(get_conn, user_id, state)
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton('🔁 Бой снова', callback_data=f'arena_rand_{player["id"]}'))
            kb.add(InlineKeyboardButton('🗺️ В меню арены', callback_data=f'arena_switch_{player["id"]}'))
            try:
                bot.edit_message_text(f'— ⚔️ Б О Й ⚔️ —\n\n{log_text}\n\n{reward_text}',
                                      call.message.chat.id, call.message.message_id, reply_markup=kb)
            except:
                bot.send_message(call.message.chat.id, f'{log_text}\n\n{reward_text}', reply_markup=kb)
            bot.answer_callback_query(call.id)
            return

        # Ход гоблина если AP = 0
        if player['ap'] <= 0:
            goblin_msgs = process_goblin_turn_full(state)
            log_text += '\n\n👹 Ход врага:\n' + '\n'.join(goblin_msgs)

        if state['phase'] == 'finished':
            save_battle_state(get_conn, user_id, state)
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton('🔁 Бой снова', callback_data=f'arena_rand_{player["id"]}'))
            kb.add(InlineKeyboardButton('🗺️ В меню арены', callback_data=f'arena_switch_{player["id"]}'))
            try:
                bot.edit_message_text(f'— ⚔️ Б О Й ⚔️ —\n\n{log_text}',
                                      call.message.chat.id, call.message.message_id, reply_markup=kb)
            except:
                bot.send_message(call.message.chat.id, log_text, reply_markup=kb)
            bot.answer_callback_query(call.id)
            return

        state['log'] = [log_text]
        save_battle_state(get_conn, user_id, state)
        text = fmt_battle(state)
        kb   = battle_keyboard(state)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)
        bot.answer_callback_query(call.id)


    # ─── Защита ──────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_def')
    def cb_arena_defend(call):
        user_id = call.from_user.id
        state   = load_battle_state(get_conn, user_id)
        if not state or state['phase'] != 'player_turn':
            bot.answer_callback_query(call.id, 'Не твой ход!')
            return

        player = state['player']
        if player.get('ap', 0) <= 0:
            bot.answer_callback_query(call.id, 'Нет АП!', show_alert=True)
            return

        player['defending'] = True
        player['ap'] -= 1
        msgs = ['🛡️ Ты принял защитную позицию! Следующий удар -50% урона']

        # Если AP = 0 → ход гоблина
        if player['ap'] <= 0:
            goblin_msgs = process_goblin_turn_full(state)
            msgs += ['', '👹 Ход врага:'] + goblin_msgs

        log_text = '\n'.join(msgs)
        state['log'] = [log_text]

        if state['phase'] == 'finished':
            save_battle_state(get_conn, user_id, state)
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton('🔁 Бой снова', callback_data=f'arena_rand_{player["id"]}'))
            kb.add(InlineKeyboardButton('🗺️ В меню арены', callback_data=f'arena_switch_{player["id"]}'))
            try:
                bot.edit_message_text(f'— ⚔️ Б О Й ⚔️ —\n\n{log_text}',
                                      call.message.chat.id, call.message.message_id, reply_markup=kb)
            except:
                bot.send_message(call.message.chat.id, log_text, reply_markup=kb)
            bot.answer_callback_query(call.id)
            return

        save_battle_state(get_conn, user_id, state)
        text = fmt_battle(state)
        kb   = battle_keyboard(state)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)
        bot.answer_callback_query(call.id)


    # ─── Сбежать ─────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_run')
    def cb_arena_run(call):
        user_id = call.from_user.id
        state   = load_battle_state(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id, 'Бой не найден')
            return

        player = state['player']

        # Шанс сбежать на основе скорости
        player_speed = player.get('speed', 5)
        enemy_speed  = state['enemy'].get('speed', 5)
        run_chance   = max(30, min(80, 50 + (player_speed - enemy_speed) * 5))

        if random.randint(1, 100) <= run_chance:
            clear_battle_state(get_conn, user_id)
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton('🗺️ В меню арены', callback_data=f'arena_switch_{player["id"]}'))
            try:
                bot.edit_message_text(
                    f'🏃 {player["name"]} успешно сбежал с поля боя!',
                    call.message.chat.id, call.message.message_id, reply_markup=kb
                )
            except:
                bot.send_message(call.message.chat.id, '🏃 Ты сбежал!', reply_markup=kb)
        else:
            # Не удалось сбежать — гоблин атакует
            msgs = ['🏃 Не удалось сбежать! Враг атаковал!']
            goblin_msgs = process_goblin_turn_full(state)
            msgs.extend(goblin_msgs)
            log_text = '\n'.join(msgs)
            state['log'] = [log_text]

            if state['phase'] == 'finished':
                save_battle_state(get_conn, user_id, state)
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton('🔁 Бой снова', callback_data=f'arena_rand_{player["id"]}'))
                try:
                    bot.edit_message_text(f'— ⚔️ Б О Й ⚔️ —\n\n{log_text}',
                                          call.message.chat.id, call.message.message_id, reply_markup=kb)
                except:
                    bot.send_message(call.message.chat.id, log_text, reply_markup=kb)
            else:
                save_battle_state(get_conn, user_id, state)
                text = fmt_battle(state)
                kb   = battle_keyboard(state)
                try:
                    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
                except:
                    bot.send_message(call.message.chat.id, text, reply_markup=kb)

        bot.answer_callback_query(call.id)


    # ─── Стойки ──────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_stance')
    def cb_arena_stance_menu(call):
        user_id = call.from_user.id
        state   = load_battle_state(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id, 'Бой не найден')
            return
        current = state['player'].get('stance', 'normal')
        text = fmt_stance_menu(current)
        kb   = stance_keyboard()
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)
        bot.answer_callback_query(call.id)


    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_st_'))
    def cb_arena_set_stance(call):
        user_id = call.from_user.id
        state   = load_battle_state(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id, 'Бой не найден')
            return

        stance_map = {
            'arena_st_battle':  'battle',
            'arena_st_defense': 'defense',
            'arena_st_precise': 'precise',
            'arena_st_dodge':   'dodge',
        }
        new_stance = stance_map.get(call.data, 'normal')
        state['player']['stance'] = new_stance
        save_battle_state(get_conn, user_id, state)

        text = fmt_battle(state)
        kb   = battle_keyboard(state)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)
        bot.answer_callback_query(call.id, f'✅ Стойка изменена')


    # ─── Инвентарь ───────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_inv')
    def cb_arena_inventory(call):
        user_id = call.from_user.id
        state   = load_battle_state(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id, 'Бой не найден')
            return
        text = fmt_inventory(state)
        kb   = inventory_keyboard(state)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)
        bot.answer_callback_query(call.id)


    @bot.callback_query_handler(func=lambda c: c.data.startswith('arena_use_art_'))
    def cb_arena_use_artifact(call):
        user_id = call.from_user.id
        state   = load_battle_state(get_conn, user_id)
        if not state or state['phase'] != 'player_turn':
            bot.answer_callback_query(call.id, 'Нельзя сейчас использовать артефакт')
            return

        art_num = int(call.data.split('_')[-1])  # 1 или 2
        player  = state['player']
        enemy   = state['enemy']

        if player.get('ap', 0) <= 0:
            bot.answer_callback_query(call.id, 'Нет АП!', show_alert=True)
            return

        art_slot = f'artifact{art_num}'
        art_name = player.get(art_slot)
        if not art_name:
            bot.answer_callback_query(call.id, 'Нет артефакта', show_alert=True)
            return

        if art_name not in ARTIFACTS:
            bot.answer_callback_query(call.id, 'Неизвестный артефакт', show_alert=True)
            return

        if ARTIFACTS[art_name]['type'] != 'active':
            bot.answer_callback_query(call.id,
                f'Это пассивный артефакт — он работает автоматически.', show_alert=True)
            return

        msgs = use_active_artifact(player, enemy, art_name)
        player['ap'] -= 1

        log_text = '\n'.join(msgs)

        # Враг умер от артефакта?
        if enemy['hp'] <= 0:
            state['phase']  = 'finished'
            state['winner'] = 'player'
            reward_text = end_battle_rewards(state, get_conn, user_id)
            state['log'] = [log_text + f'\n\n{reward_text}']
            save_battle_state(get_conn, user_id, state)
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton('🔁 Бой снова', callback_data=f'arena_rand_{player["id"]}'))
            try:
                bot.edit_message_text(f'— ⚔️ Б О Й ⚔️ —\n\n{log_text}\n\n{reward_text}',
                                      call.message.chat.id, call.message.message_id, reply_markup=kb)
            except:
                bot.send_message(call.message.chat.id, f'{log_text}\n\n{reward_text}', reply_markup=kb)
            bot.answer_callback_query(call.id)
            return

        # Ход гоблина если AP = 0
        if player['ap'] <= 0:
            goblin_msgs = process_goblin_turn_full(state)
            log_text += '\n\n👹 Ход врага:\n' + '\n'.join(goblin_msgs)

        state['log'] = [log_text]
        save_battle_state(get_conn, user_id, state)

        if state['phase'] == 'finished':
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton('🔁 Бой снова', callback_data=f'arena_rand_{player["id"]}'))
            try:
                bot.edit_message_text(f'— ⚔️ Б О Й ⚔️ —\n\n{log_text}',
                                      call.message.chat.id, call.message.message_id, reply_markup=kb)
            except:
                bot.send_message(call.message.chat.id, log_text, reply_markup=kb)
            bot.answer_callback_query(call.id)
            return

        text = fmt_battle(state)
        kb   = battle_keyboard(state)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)
        bot.answer_callback_query(call.id, '✅ Артефакт использован')


    # ─── Назад в бой ─────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'arena_back_battle')
    def cb_arena_back_battle(call):
        user_id = call.from_user.id
        state   = load_battle_state(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id, 'Бой не найден')
            return
        text = fmt_battle(state)
        kb   = battle_keyboard(state)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
        except:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)
        bot.answer_callback_query(call.id)
