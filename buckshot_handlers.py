# ============================================================
#  buckshot_handlers.py — Спиншот Дуэль (Buckshot Roulette)
# ============================================================

import random
import time
import json
import psycopg2
import psycopg2.extras
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ─── Константы предметов ─────────────────────────────────────
ITEMS_BASIC    = ['🔎 Лупа', '🪚 Пила', '🍺 Пиво', '🚬 Сигареты', '⛓️ Наручники']
ITEMS_TACTICAL = ITEMS_BASIC + ['📟 Инвертор', '💉 Адреналин', '💊 Лекарства', '📞 Телефон']

# ─── Таблица БД ───────────────────────────────────────────────

def init_roulette_tables(get_conn):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS roulette_state (
            user_id    BIGINT PRIMARY KEY,
            state_json TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS roulette_stats (
            user_id BIGINT PRIMARY KEY,
            wins    INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()


def save_rstate(get_conn, user_id, state):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO roulette_state (user_id, state_json, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE SET state_json=%s, updated_at=NOW()
    ''', (user_id, json.dumps(state, ensure_ascii=False),
          json.dumps(state, ensure_ascii=False)))
    conn.commit()
    conn.close()


def load_rstate(get_conn, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT state_json FROM roulette_state WHERE user_id=%s', (user_id,))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None


def clear_rstate(get_conn, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM roulette_state WHERE user_id=%s', (user_id,))
    conn.commit()
    conn.close()


def add_rwin(get_conn, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO roulette_stats (user_id, wins) VALUES (%s, 1)
        ON CONFLICT (user_id) DO UPDATE SET wins = roulette_stats.wins + 1
    ''', (user_id,))
    conn.commit()
    conn.close()


def get_rwins(get_conn, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT wins FROM roulette_stats WHERE user_id=%s', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0


def get_top_roulette(get_conn, limit=10):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT u.username, r.wins, r.user_id
        FROM roulette_stats r
        JOIN users u ON u.user_id = r.user_id
        ORDER BY r.wins DESC LIMIT %s
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


# ─── Игровая логика ───────────────────────────────────────────

def make_chamber(min_live=1, max_live=4, min_blank=1, max_blank=4):
    """Генерирует случайный магазин патронов."""
    live  = random.randint(min_live, max_live)
    blank = random.randint(min_blank, max_blank)
    chamber = [True] * live + [False] * blank
    random.shuffle(chamber)
    return chamber, live, blank


def hp_for_round(rnd):
    if rnd == 1:
        return 2, 2
    hp = random.randint(2, 6)
    return hp, hp


def calc_winnings(bet, mode, rnd):
    """Рассчитывает текущий выигрыш."""
    if mode == 'classic':
        return round(bet * 1.5)
    else:
        # x2.5 базово, каждые 10 раундов +250%
        multiplier = 2.5
        extra = (rnd - 1) // 10
        for _ in range(extra):
            multiplier *= 2.5
        return round(bet * multiplier)


def hp_to_emoji(hp, icon):
    return icon * hp if hp > 0 else '💀'


def fmt_items(items):
    if not items:
        return '—'
    return ' '.join(items)


# ─── Текст главного сообщения боя ────────────────────────────

def battle_text(state, extra=''):
    rnd    = state['round']
    p_hp   = state['player_hp']
    d_hp   = state['dealer_hp']
    turn   = state['turn']
    live   = state['live_count']
    blank  = state['blank_count']
    shots  = state['shots_fired']
    p_items = fmt_items(state.get('player_items', []))
    d_items = fmt_items(state.get('dealer_items', []))
    show_items = state['round'] > 1

    turn_line = '🔔 Ход у тебя' if turn == 'player' else '👺 Ход дилера'

    ammo_block = ''
    if shots == 0:
        ammo_block = f'\n🟢 Холостых: {blank}\n🔴 Боевых: {live}\n'

    # Эффекты
    effects = []
    if state.get('dealer_skip'):
        effects.append('⛓️ Дилер скован')
    if state.get('saw_active'):
        effects.append('🪚 Пила активна')
    if state.get('extra_turn_used') is False and turn == 'player':
        pass
    eff_line = '  '.join(effects)

    items_block = ''
    if show_items:
        items_block = (
            f'\nПредметы дилера: {d_items}'
            f'\nТвои предметы: {p_items}\n'
        )

    text = (
        f'● — – - Раунд {rnd} - – — ●\n\n'
        f'{turn_line}\n\n'
        f'Ты: {hp_to_emoji(p_hp, "🫀")}\n'
        f'Дилер: {hp_to_emoji(d_hp, "⚡")}\n\n'
        f'• ——————— •\n'
        f'{ammo_block}'
        f'• ——————— •'
        f'{items_block}'
    )
    if eff_line:
        text += f'\n🔹 {eff_line}'
    if extra:
        text += f'\n\n{extra}'
    return text


def battle_keyboard(state):
    """Клавиатура боя в ход игрока."""
    kb = InlineKeyboardMarkup(row_width=2)
    phase = state.get('phase', 'battle')

    if phase == 'gun_drawn':
        kb.add(
            InlineKeyboardButton('🎯 В соперника', callback_data='rlt_shoot_dealer'),
            InlineKeyboardButton('🎭 В себя',      callback_data='rlt_shoot_self'),
        )
        return kb

    # Кнопка взять ружьё
    kb.add(InlineKeyboardButton('🔫 Взять ружьё', callback_data='rlt_take_gun'))

    # Кнопки предметов
    items = state.get('player_items', [])
    for item in items:
        key = item_to_cb(item)
        kb.add(InlineKeyboardButton(item, callback_data=f'rlt_use_{key}'))

    return kb


def item_to_cb(item):
    m = {
        '🔎 Лупа':         'magnify',
        '🪚 Пила':         'saw',
        '🍺 Пиво':         'beer',
        '🚬 Сигареты':     'cigs',
        '⛓️ Наручники':   'cuffs',
        '📟 Инвертор':     'inverter',
        '💉 Адреналин':    'adrenaline',
        '💊 Лекарства':    'meds',
        '📞 Телефон':      'phone',
    }
    return m.get(item, 'unknown')


def cb_to_item(cb):
    m = {
        'magnify':    '🔎 Лупа',
        'saw':        '🪚 Пила',
        'beer':       '🍺 Пиво',
        'cigs':       '🚬 Сигареты',
        'cuffs':      '⛓️ Наручники',
        'inverter':   '📟 Инвертор',
        'adrenaline': '💉 Адреналин',
        'meds':       '💊 Лекарства',
        'phone':      '📞 Телефон',
    }
    return m.get(cb)


# ─── ИИ дилера ────────────────────────────────────────────────

def dealer_turn(state, bot, chat_id, get_conn, user_id):
    """
    Ход дилера. Дилер НЕ видит порядок патронов — только счётчики.
    Текущий патрон становится известен только через Лупу или Телефон.
    """

    def send(text, italic=False):
        if italic:
            bot.send_message(chat_id, f'_{text}_', parse_mode='Markdown')
        else:
            bot.send_message(chat_id, text)
        time.sleep(1.1)

    if state.get('dealer_skip'):
        state['dealer_skip'] = False
        send('⛓️ Дилер скован и пропускает ход')
        return state

    chamber = state['chamber']
    pos     = state['chamber_pos']

    # Дилер знает только счётчики оставшихся патронов
    remaining   = [(i, c) for i, c in enumerate(chamber) if i >= pos]
    live        = sum(1 for _, c in remaining if c)
    blank       = sum(1 for _, c in remaining if not c)
    total       = live + blank
    live_chance = live / total if total > 0 else 0.5

    # Текущий патрон известен только если использовал Лупу/Телефон
    current_is_live = state.get('dealer_known_current')  # None = не знает

    p_hp    = state['player_hp']
    d_hp    = state['dealer_hp']
    items   = state.get('dealer_items', [])
    p_items = state.get('player_items', [])

    # 1. Спасти себя
    if d_hp == 1 and '🚬 Сигареты' in items:
        items.remove('🚬 Сигареты')
        state['dealer_hp'] = min(state['dealer_max_hp'], d_hp + 1)
        d_hp = state['dealer_hp']
        send('🚬 Дилер закуривает сигарету...\n+1 ⚡')

    if d_hp <= 1 and '💊 Лекарства' in items:
        items.remove('💊 Лекарства')
        if random.random() < 0.5:
            state['dealer_hp'] = min(state['dealer_max_hp'], d_hp + 2)
            send('💊 Дилер принял лекарства.\n+2 ⚡')
        else:
            state['dealer_hp'] = max(0, d_hp - 1)
            send('💊 Дилер принял просроченные лекарства.\n-1 ⚡')
        time.sleep(1.1)
        d_hp = state['dealer_hp']
        if d_hp <= 0:
            return state

    # 2. Получить информацию
    # Лупа — узнаёт текущий патрон
    if current_is_live is None and '🔎 Лупа' in items:
        items.remove('🔎 Лупа')
        current_is_live = chamber[pos]  # единственное честное чтение через предмет
        state['dealer_known_current'] = current_is_live
        send('🔍 Дилер использует лупу...')

    # Телефон — узнаёт один случайный патрон
    if '📞 Телефон' in items and total > 1:
        items.remove('📞 Телефон')
        reveal_idx  = random.randint(pos, len(chamber) - 1)
        reveal_type = 'боевой' if chamber[reveal_idx] else 'холостой'
        n = reveal_idx - pos + 1
        if reveal_idx == pos:
            current_is_live = chamber[pos]
            state['dealer_known_current'] = current_is_live
        send(f'📞 Дилер звонит по телефону...\n—«{n}-й патрон — {reveal_type}»')

    # 3. Контроль и подготовка

    # Инвертор — только если ТОЧНО знает что текущий холостой
    if current_is_live is False and '📟 Инвертор' in items and live_chance < 0.4:
        items.remove('📟 Инвертор')
        chamber[pos] = True
        current_is_live = True
        state['chamber'] = chamber
        state['dealer_known_current'] = True
        send('📟 Дилер щёлкает инвертором...\nТекущий патрон инвертирован')

    # Наручники — если у игрока много HP или дилеру плохо
    if '⛓️ Наручники' in items and (p_hp >= 3 or d_hp <= 2):
        items.remove('⛓️ Наручники')
        state['player_skip'] = True
        send('⛓️ Дилер надевает наручники на тебя.\nТы пропускаешь следующий ход')

    # Адреналин — украсть ценный предмет у игрока
    if '💉 Адреналин' in items and p_items:
        steal_priority = ['🔎 Лупа', '⛓️ Наручники', '🪚 Пила', '📞 Телефон']
        stolen = None
        for pref in steal_priority:
            if pref in p_items:
                stolen = pref
                break
        if not stolen:
            stolen = random.choice(p_items)
        if stolen != '💉 Адреналин':
            items.remove('💉 Адреналин')
            p_items.remove(stolen)
            send(f'💉 Дилер вводит адреналин и хватает твой предмет: {stolen}')
            state = dealer_use_stolen(state, stolen, bot, chat_id)
            d_hp = state['dealer_hp']
            p_hp = state['player_hp']
            # Если украл Лупу — узнаёт текущий патрон
            if stolen == '🔎 Лупа' and pos < len(chamber):
                current_is_live = chamber[pos]
                state['dealer_known_current'] = current_is_live

    # Пила — если шанс боевого высокий или у игрока мало HP
    # Не используем если точно знаем что патрон холостой
    if not state.get('saw_active') and '🪚 Пила' in items:
        if current_is_live is not False and (live_chance >= 0.5 or p_hp <= 2):
            items.remove('🪚 Пила')
            state['saw_active'] = True
            send('🪚 Дилер пилит ствол.\nСледующий боевой выстрел нанесёт 2 урона')

    # Пиво — только если ТОЧНО знает что текущий боевой и стрелять невыгодно
    if current_is_live is True and '🍺 Пиво' in items and d_hp > 2 and live_chance <= 0.35:
        items.remove('🍺 Пиво')
        actual_dropped = chamber[pos]
        state['chamber_pos'] += 1
        state['shots_fired'] += 1
        state['dealer_known_current'] = None  # следующий патрон неизвестен
        current_is_live = None
        drop_name = 'Боевой 🔴' if actual_dropped else 'Холостой 🟢'
        send(f'🍺 Дилер делает глоток пива.\nСброшен патрон: {drop_name}')
        # Пересчитываем вероятности
        pos       = state['chamber_pos']
        remaining = [(i, c) for i, c in enumerate(chamber) if i >= pos]
        live      = sum(1 for _, c in remaining if c)
        blank     = sum(1 for _, c in remaining if not c)
        total     = live + blank
        live_chance = live / total if total > 0 else 0.5

    state['dealer_items'] = items
    state['player_items'] = p_items

    # 4. Стрелять
    if state['chamber_pos'] >= len(state['chamber']):
        state, reload_msg = reload_chamber(state)
        send(reload_msg)
        time.sleep(1.1)
        # После перезарядки дилер не знает ни одного патрона
        state['dealer_known_current'] = None
        current_is_live = None
        total2 = state['live_count'] + state['blank_count']
        live_chance = state['live_count'] / total2 if total2 > 0 else 0.5

    send('🔫 Дилер взял ружьё. . .', italic=True)
    time.sleep(1.1)

    # Решение куда стрелять:
    # — точно знает холостой → в себя (получает доп. ход)
    # — точно знает боевой  → в игрока
    # — не знает            → по вероятности (холостой > 70% → в себя)
    if current_is_live is False:
        shoot_self = True
    elif current_is_live is True:
        shoot_self = False
    else:
        shoot_self = live_chance < 0.3

    # Сбрасываем знание — патрон будет израсходован
    state['dealer_known_current'] = None

    if shoot_self:
        send('Дилер целится на себя. . .', italic=True)
        time.sleep(1.1)
        state, hit, damage = fire(state, target='dealer')
        if not hit:
            send('💨 Холостой...')
            if not state.get('_dealer_extra_turn_used'):
                state['_dealer_extra_turn_used'] = True
                state = dealer_turn(state, bot, chat_id, get_conn, user_id)
        else:
            send('💥 Боевой!')
    else:
        send('Дилер целится на тебя. . .', italic=True)
        time.sleep(1.1)
        state, hit, damage = fire(state, target='player')
        if not hit:
            send('💨 Холостой...')
        else:
            send(f'💥 Боевой! -{damage} 🫀')

    state['_dealer_extra_turn_used'] = False
    return state

def dealer_use_stolen(state, item, bot, chat_id):
    """Дилер использует украденный предмет немедленно."""
    d_hp = state['dealer_hp']
    if item == '🔎 Лупа':
        pass  # уже знает патрон
    elif item == '🪚 Пила':
        state['saw_active'] = True
    elif item == '🍺 Пиво':
        if state['chamber_pos'] < len(state['chamber']):
            state['chamber_pos'] += 1
            state['shots_fired'] += 1
    elif item == '🚬 Сигареты':
        state['dealer_hp'] = min(state['dealer_max_hp'], d_hp + 1)
    elif item == '⛓️ Наручники':
        state['player_skip'] = True
    elif item == '💊 Лекарства':
        if random.random() < 0.5:
            state['dealer_hp'] = min(state['dealer_max_hp'], d_hp + 2)
        else:
            state['dealer_hp'] = max(0, d_hp - 1)
    elif item == '📞 Телефон':
        pass  # информация бесполезна для уже краденного
    return state


def fire(state, target='player'):
    """Производит выстрел. Возвращает (state, hit:bool, damage:int)."""
    pos     = state['chamber_pos']
    chamber = state['chamber']

    if pos >= len(chamber):
        return state, False, 0

    is_live = chamber[pos]
    state['chamber_pos'] += 1
    state['shots_fired']  = state.get('shots_fired', 0) + 1

    damage = 0
    if is_live:
        damage = 2 if state.get('saw_active') else 1
        state['saw_active'] = False
        if target in ('player', 'self'):
            state['player_hp'] = max(0, state['player_hp'] - damage)
        else:
            state['dealer_hp'] = max(0, state['dealer_hp'] - damage)

    return state, is_live, damage


def reload_chamber(state):
    """Перезаряжает магазин, сбрасывает эффекты."""
    mode = state.get('mode', 'classic')
    chamber, live, blank = make_chamber()
    state['chamber']      = chamber
    state['chamber_pos']  = 0
    state['live_count']   = live
    state['blank_count']  = blank
    state['shots_fired']  = 0
    state['saw_active']   = False
    state['turn']         = 'player'
    msg = (
        f'🔄 Патроны кончились. Дилер перезаряжает ружьё.\n\n'
        f'🟢 Холостых: {blank}\n'
        f'🔴 Боевых: {live}\n\n'
        f'🔔 Ход возвращается тебе'
    )
    return state, msg


def start_new_round(state, rnd):
    """Инициализирует новый раунд."""
    mode = state.get('mode', 'classic')
    p_hp, d_hp = hp_for_round(rnd)
    chamber, live, blank = make_chamber()
    items_count = random.randint(1, 4)
    item_pool = ITEMS_TACTICAL if mode == 'tactical' else ITEMS_BASIC
    p_items = [random.choice(item_pool) for _ in range(items_count)]
    d_items = [random.choice(item_pool) for _ in range(items_count)]

    state.update({
        'round':          rnd,
        'player_hp':      p_hp,
        'dealer_hp':      d_hp,
        'player_max_hp':  p_hp,
        'dealer_max_hp':  d_hp,
        'chamber':        chamber,
        'chamber_pos':    0,
        'live_count':     live,
        'blank_count':    blank,
        'shots_fired':    0,
        'turn':           'player',
        'phase':          'pick_items' if rnd > 1 else 'battle',
        'items_to_pick':  items_count if rnd > 1 else 0,
        'items_picked':   0,
        'player_items':   [] if rnd > 1 else [],
        'dealer_items':   d_items if rnd > 1 else [],
        'pending_p_items': p_items if rnd > 1 else [],
        'saw_active':     False,
        'dealer_skip':    False,
        'player_skip':    False,
        'extra_turn_used': False,
        '_dealer_extra_turn_used': False,
    })
    return state


# ─── Клавиатуры ───────────────────────────────────────────────

def main_menu_keyboard(has_active, active_round=None):
    kb = InlineKeyboardMarkup(row_width=1)
    if has_active:
        kb.add(InlineKeyboardButton(
            f'▶️ Продолжить | Раунд {active_round}',
            callback_data='rlt_continue'
        ))
    kb.add(InlineKeyboardButton('👤 Игра с пользователем', callback_data='rlt_pvp'))
    kb.add(InlineKeyboardButton('👺 Игра с дилером',       callback_data='rlt_dealer'))
    kb.add(InlineKeyboardButton('🏆 Рекорды',              callback_data='rlt_leaderboard'))
    return kb


def back_to_main_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('🔙 Назад', callback_data='rlt_main'))
    return kb


# ─── Регистрация хэндлеров ────────────────────────────────────

def register_roulette_handlers(bot, get_conn, get_user, add_money, spend_money):

    pending_bet = {}   # user_id: {'mode': str, 'step': str}

    def safe_edit(chat_id, msg_id, text, kb=None, parse_mode=None):
        try:
            bot.edit_message_text(text, chat_id, msg_id,
                                  reply_markup=kb, parse_mode=parse_mode)
        except Exception:
            bot.send_message(chat_id, text, reply_markup=kb, parse_mode=parse_mode)

    def send_main_menu(chat_id, user_id, msg_id=None):
        state = load_rstate(get_conn, user_id)
        has_active  = state is not None and state.get('phase') not in ('finished',)
        active_rnd  = state['round'] if has_active else None
        user = get_user(user_id)
        money = user[2] if user else 0
        exp   = user[3] if user else 0
        wins  = get_rwins(get_conn, user_id)
        text = (
            f'— – - ⬜ СПИНШОТ ДУЭЛЬ ⬛ - – —\n\n'
            f'Денег: 💵 {money:,}\n'
            f'Опыта: ⭐ {exp:,}\n'
            f'Побед: 🎖️ {wins}\n\n'
            f'• – – – – – – – – – – – – – – – – – •'
        )
        kb = main_menu_keyboard(has_active, active_rnd)
        if msg_id:
            safe_edit(chat_id, msg_id, text, kb)
        else:
            bot.send_message(chat_id, text, reply_markup=kb)

    # ─── /roulette ─────────────────────────────────────────────

    @bot.message_handler(commands=['roulette'])
    def cmd_roulette(message):
        user_id = message.from_user.id
        args    = message.text.split()

        if len(args) > 1 and args[1] == 'exit':
            state = load_rstate(get_conn, user_id)
            if state:
                clear_rstate(get_conn, user_id)
                bot.send_message(message.chat.id,
                                 '🚪 Ты вышел из игры. Ставка не возвращается.')
            else:
                bot.send_message(message.chat.id, 'Активной игры нет.')
            return

        send_main_menu(message.chat.id, user_id)

    # ─── Главное меню (callback) ────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'rlt_main')
    def cb_rlt_main(call):
        send_main_menu(call.message.chat.id, call.from_user.id, call.message.message_id)
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data == 'rlt_continue')
    def cb_rlt_continue(call):
        user_id = call.from_user.id
        state   = load_rstate(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id, 'Активной игры нет')
            return
        bot.answer_callback_query(call.id)
        send_battle_message(bot, call.message.chat_id if hasattr(call.message, 'chat_id')
                            else call.message.chat.id, user_id, state, get_conn)

    @bot.callback_query_handler(func=lambda c: c.data == 'rlt_pvp')
    def cb_rlt_pvp(call):
        bot.answer_callback_query(call.id, '🚧 Игра с пользователем пока недоступна!', show_alert=True)

    # ─── Рекорды ───────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'rlt_leaderboard')
    def cb_rlt_leaderboard(call):
        user_id = call.from_user.id
        top     = get_top_roulette(get_conn, 10)
        medals  = ['🥇', '🥈', '🥉']
        text    = '– 🏆 РЕКОРДЫ ТОП 10 ИГРОКОВ 🏆 –\n\n'
        user_place = None

        for i, (uname, wins, uid) in enumerate(top, 1):
            medal = medals[i-1] if i <= 3 else f'{i}.'
            text += f'{medal} {uname} – 🎖️ {wins}\n'
            if uid == user_id:
                user_place = i

        text += '\n• – – – – – – – – – – – – – – – – – •'

        if user_place is None:
            # Найти место игрока
            conn = get_conn()
            c = conn.cursor()
            c.execute('''
                SELECT COUNT(*) + 1 FROM roulette_stats
                WHERE wins > COALESCE((SELECT wins FROM roulette_stats WHERE user_id=%s), -1)
            ''', (user_id,))
            place = c.fetchone()[0]
            conn.close()
            text += f'\n👤 Ты на {place} месте'
            text += '\n• – – – – – – – – – – – – – – – – – •'

        kb = back_to_main_kb()
        safe_edit(call.message.chat.id, call.message.message_id, text, kb)
        bot.answer_callback_query(call.id)

    # ─── Выбор режима ──────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'rlt_dealer')
    def cb_rlt_dealer(call):
        user_id = call.from_user.id
        user    = get_user(user_id)
        money   = user[2] if user else 0
        text = (
            f'— – - 👺 ИГРА С ДИЛЕРОМ 🛎️ - – —\n\n'
            f'Ты заходишь в тёмную комнату…\n'
            f'За столом сидит Дилер и молча крутит барабан судьбы.\n\n'
            f'–«Правила просты:\n'
            f'либо ты выходишь с деньгами… либо не выходишь вовсе.»\n\n'
            f'Денег: 💵 {money:,}\n\n'
            f'Выбери режим игры:\n'
            f'• — — — — — — — — •\n'
            f'1️⃣ 🟢 Классический риск\n'
            f'Простой режим без лишней сложности.\n'
            f'Минимум предметов, больше чистого рандома.\n'
            f'Всего 3 раунда\n'
            f'💰 Множитель: x1.5\n'
            f'• — — — — — — — — •\n'
            f'2️⃣ 🔴 Тактика дилера\n'
            f'Полный режим с предметами и стратегией.\n'
            f'Каждое решение может изменить исход игры.\n'
            f'♾️ Бесконечные раунды.\n'
            f'💰 Множитель: x2.5\n'
            f'• — — — — — — — — •'
        )
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton('🟢 Классический риск', callback_data='rlt_mode_classic'),
            InlineKeyboardButton('🔴 Тактика дилера',    callback_data='rlt_mode_tactical'),
            InlineKeyboardButton('🔙 Назад',              callback_data='rlt_main'),
        )
        safe_edit(call.message.chat.id, call.message.message_id, text, kb)
        bot.answer_callback_query(call.id)

    # ─── Ввод ставки ───────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data in ('rlt_mode_classic', 'rlt_mode_tactical'))
    def cb_rlt_mode(call):
        user_id = call.from_user.id
        mode    = 'classic' if call.data == 'rlt_mode_classic' else 'tactical'
        mode_name = '🟢 Классический риск' if mode == 'classic' else '🔴 Тактика дилера'
        user  = get_user(user_id)
        money = user[2] if user else 0
        pending_bet[user_id] = {
            'mode': mode, 'mode_name': mode_name,
            'chat_id': call.message.chat.id, 'msg_id': call.message.message_id,
        }
        text = (
            f'— – - 👺 ИГРА С ДИЛЕРОМ 🛎️ - – —\n\n'
            f'Денег: 💵 {money:,}\n\n'
            f'Режим: {mode_name}\n\n'
            f'💰 Введи ставку на игру (мин. 1000)'
        )
        kb = back_to_main_kb()
        safe_edit(call.message.chat.id, call.message.message_id, text, kb)
        bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda m: m.from_user.id in pending_bet
                          and pending_bet[m.from_user.id].get('mode') is not None)
    def handle_rlt_bet(message):
        user_id   = message.from_user.id
        info      = pending_bet.get(user_id)
        if not info:
            return

        try:
            bet = int(message.text.strip().replace(',', '').replace(' ', ''))
        except ValueError:
            bot.send_message(message.chat.id, '❌ Введи число!')
            return

        if bet < 1000:
            bot.send_message(message.chat.id, '❌ Минимальная ставка 1000!')
            return

        user  = get_user(user_id)
        money = user[2] if user else 0
        if money < bet:
            bot.send_message(message.chat.id,
                             f'❌ Недостаточно средств! У тебя 💵 {money:,}')
            return

        mode     = info['mode']
        mode_name = info['mode_name']
        winnings = calc_winnings(bet, mode, 3)  # показываем финальный приз

        text = (
            f'Ставка: {bet:,}\n\n'
            f'Режим: {mode_name}\n\n'
            f'– – 💰 Выйгрыш: {winnings:,} – –\n\n'
            f'Продолжить?'
        )
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton('☑️ Начать', callback_data=f'rlt_start_{bet}_{mode}'),
            InlineKeyboardButton('📝 Ввести другую', callback_data=f'rlt_rebet_{mode}'),
        )
        pending_bet[user_id]['bet'] = bet
        bot.send_message(message.chat.id, text, reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('rlt_rebet_'))
    def cb_rlt_rebet(call):
        user_id   = call.from_user.id
        mode      = call.data.split('_')[-1]
        mode_name = '🟢 Классический риск' if mode == 'classic' else '🔴 Тактика дилера'
        user  = get_user(user_id)
        money = user[2] if user else 0
        pending_bet[user_id] = {
            'mode': mode, 'mode_name': mode_name,
            'chat_id': call.message.chat.id, 'msg_id': call.message.message_id,
        }
        text = (
            f'— – - 👺 ИГРА С ДИЛЕРОМ 🛎️ - – —\n\n'
            f'Денег: 💵 {money:,}\n\n'
            f'Режим: {mode_name}\n\n'
            f'💰 Введи ставку на игру (мин. 1000)'
        )
        safe_edit(call.message.chat.id, call.message.message_id, text, back_to_main_kb())
        bot.answer_callback_query(call.id)

    # ─── Старт игры ────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('rlt_start_'))
    def cb_rlt_start(call):
        user_id = call.from_user.id
        parts   = call.data.split('_')
        bet     = int(parts[2])
        mode    = parts[3]

        user  = get_user(user_id)
        money = user[2] if user else 0
        if money < bet:
            bot.answer_callback_query(call.id, '❌ Недостаточно средств!', show_alert=True)
            return

        spend_money(user_id, bet)
        pending_bet.pop(user_id, None)

        state = {
            'mode':      mode,
            'bet':       bet,
            'chat_id':   call.message.chat.id,
            'user_id':   user_id,
        }
        state = start_new_round(state, 1)
        save_rstate(get_conn, user_id, state)

        text = battle_text(state)
        kb   = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton('🔫 Взять ружьё', callback_data='rlt_take_gun'))
        safe_edit(call.message.chat.id, call.message.message_id, text, kb)
        bot.answer_callback_query(call.id)

    # ─── Взять ружьё ───────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'rlt_take_gun')
    def cb_rlt_take_gun(call):
        user_id = call.from_user.id
        state   = load_rstate(get_conn, user_id)
        if not state or state.get('turn') != 'player':
            bot.answer_callback_query(call.id, 'Сейчас не твой ход!')
            return

        state['phase'] = 'gun_drawn'
        save_rstate(get_conn, user_id, state)

        text = battle_text(state, extra='🔫 Ты взял ружьё. Выбери в кого стрелять')
        kb   = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton('🎯 В соперника', callback_data='rlt_shoot_dealer'),
            InlineKeyboardButton('🎭 В себя',      callback_data='rlt_shoot_self'),
        )
        safe_edit(call.message.chat.id, call.message.message_id, text, kb)
        bot.answer_callback_query(call.id)

    # ─── Выстрелы ──────────────────────────────────────────────

    def process_shot(call, target):
        user_id = call.from_user.id
        state   = load_rstate(get_conn, user_id)
        if not state or state.get('turn') != 'player':
            bot.answer_callback_query(call.id, 'Сейчас не твой ход!')
            return
        if state.get('phase') != 'gun_drawn':
            bot.answer_callback_query(call.id, 'Сначала возьми ружьё!')
            return

        bot.answer_callback_query(call.id)
        # Убираем кнопки
        safe_edit(call.message.chat.id, call.message.message_id,
                  battle_text(state))

        aim_text = 'Ты целишься в дилера. . .' if target == 'dealer' else 'Ты целишься на себя. . .'
        bot.send_message(call.message.chat.id, f'_{aim_text}_', parse_mode='Markdown')
        time.sleep(1.1)

        state, hit, damage = fire(state, target)
        if hit:
            bot.send_message(call.message.chat.id, f'💥 Боевой! -{damage} {"⚡" if target == "dealer" else "🫀"}')
        else:
            bot.send_message(call.message.chat.id, '💨 Холостой...')
        time.sleep(1.1)

        state['phase'] = 'battle'

        # Проверка победы/поражения
        if state['dealer_hp'] <= 0:
            handle_round_win(bot, call.message.chat.id, user_id, state, get_conn, add_money)
            return

        if state['player_hp'] <= 0:
            handle_game_loss(bot, call.message.chat.id, user_id, state, get_conn, add_money)
            return

        # Если патроны кончились — перезарядка
        if state['chamber_pos'] >= len(state['chamber']):
            state, reload_msg = reload_chamber(state)
            bot.send_message(call.message.chat.id, reload_msg)
            time.sleep(1.1)
            save_rstate(get_conn, user_id, state)
            send_battle_message(bot, call.message.chat.id, user_id, state, get_conn)
            return

        # Доп. ход при выстреле в себя холостым
        if target == 'self' and not hit and not state.get('extra_turn_used'):
            state['extra_turn_used'] = True
            state['turn'] = 'player'
            state['phase'] = 'battle'
            bot.send_message(call.message.chat.id, '🔔 Холостой в себя — ты получаешь дополнительный ход!')
            time.sleep(1.1)
            save_rstate(get_conn, user_id, state)
            send_battle_message(bot, call.message.chat.id, user_id, state, get_conn)
            return

        # Переход хода к дилеру
        state['turn'] = 'dealer'
        state['extra_turn_used'] = False
        save_rstate(get_conn, user_id, state)

        # Отправляем статус дилера
        bot.send_message(call.message.chat.id, battle_text(state))
        time.sleep(1.1)

        # Ход дилера
        state = dealer_turn(state, bot, call.message.chat.id, get_conn, user_id)

        if state['player_hp'] <= 0:
            handle_game_loss(bot, call.message.chat.id, user_id, state, get_conn, add_money)
            return
        if state['dealer_hp'] <= 0:
            handle_round_win(bot, call.message.chat.id, user_id, state, get_conn, add_money)
            return

        # Перезарядка после хода дилера
        if state['chamber_pos'] >= len(state['chamber']):
            state, reload_msg = reload_chamber(state)
            bot.send_message(call.message.chat.id, reload_msg)
            time.sleep(1.1)

        # Пропуск хода игрока (наручники)
        if state.get('player_skip'):
            state['player_skip'] = False
            bot.send_message(call.message.chat.id,
                             '⛓️ Ты скован и пропускаешь ход. Ход переходит дилеру.')
            time.sleep(1.1)
            save_rstate(get_conn, user_id, state)
            state = dealer_turn(state, bot, call.message.chat.id, get_conn, user_id)
            if state['player_hp'] <= 0:
                handle_game_loss(bot, call.message.chat.id, user_id, state, get_conn, add_money)
                return
            if state['dealer_hp'] <= 0:
                handle_round_win(bot, call.message.chat.id, user_id, state, get_conn, add_money)
                return

        state['turn'] = 'player'
        state['phase'] = 'battle'
        save_rstate(get_conn, user_id, state)
        send_battle_message(bot, call.message.chat.id, user_id, state, get_conn)

    @bot.callback_query_handler(func=lambda c: c.data == 'rlt_shoot_dealer')
    def cb_shoot_dealer(call):
        process_shot(call, 'dealer')

    @bot.callback_query_handler(func=lambda c: c.data == 'rlt_shoot_self')
    def cb_shoot_self(call):
        process_shot(call, 'self')

    # ─── Предметы игрока ───────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('rlt_use_'))
    def cb_rlt_use_item(call):
        user_id = call.from_user.id
        state   = load_rstate(get_conn, user_id)
        if not state or state.get('turn') != 'player':
            bot.answer_callback_query(call.id, 'Сейчас не твой ход!')
            return
        if state.get('phase') == 'gun_drawn':
            bot.answer_callback_query(call.id, 'После взятия ружья предметы нельзя использовать!')
            return

        item_key = call.data[len('rlt_use_'):]
        item_name = cb_to_item(item_key)
        if not item_name:
            bot.answer_callback_query(call.id, 'Неизвестный предмет')
            return

        p_items = state.get('player_items', [])
        if item_name not in p_items:
            bot.answer_callback_query(call.id, 'У тебя нет этого предмета!')
            return

        bot.answer_callback_query(call.id)

        # Адреналин — особый случай (нужно выбрать предмет дилера)
        if item_name == '💉 Адреналин':
            d_items = state.get('dealer_items', [])
            if not d_items:
                bot.send_message(call.message.chat.id,
                                 '💉 У дилера нет предметов для кражи!')
                return
            p_items.remove(item_name)
            state['player_items'] = p_items
            save_rstate(get_conn, user_id, state)
            bot.send_message(call.message.chat.id,
                             '💉 Адреналин\n_Ты срываешься в рывок и перехватываешь чужой шанс._\n\nВыбери предмет у противника:',
                             parse_mode='Markdown',
                             reply_markup=adrenaline_kb(d_items))
            return

        # Использование предмета
        p_items.remove(item_name)
        state['player_items'] = p_items
        state, msg = apply_item(state, item_name, user='player')
        save_rstate(get_conn, user_id, state)

        if state['dealer_hp'] <= 0:
            handle_round_win(bot, call.message.chat.id, user_id, state, get_conn, add_money)
            return
        if state['player_hp'] <= 0:
            handle_game_loss(bot, call.message.chat.id, user_id, state, get_conn, add_money)
            return

        bot.send_message(call.message.chat.id, msg, parse_mode='Markdown')
        time.sleep(1.1)
        send_battle_message(bot, call.message.chat.id, user_id, state, get_conn)

    def adrenaline_kb(d_items):
        kb = InlineKeyboardMarkup(row_width=2)
        for item in d_items:
            if item != '💉 Адреналин':
                kb.add(InlineKeyboardButton(item, callback_data=f'rlt_steal_{item_to_cb(item)}'))
        return kb

    @bot.callback_query_handler(func=lambda c: c.data.startswith('rlt_steal_'))
    def cb_rlt_steal(call):
        user_id  = call.from_user.id
        state    = load_rstate(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id)
            return
        item_key  = call.data[len('rlt_steal_'):]
        item_name = cb_to_item(item_key)
        d_items   = state.get('dealer_items', [])
        if item_name and item_name in d_items:
            d_items.remove(item_name)
            state['dealer_items'] = d_items
            state, msg = apply_item(state, item_name, user='player')
            save_rstate(get_conn, user_id, state)
            bot.send_message(call.message.chat.id,
                             f'💉 Ты украл {item_name} у дилера и сразу использовал!\n\n{msg}',
                             parse_mode='Markdown')
            time.sleep(1.1)
            if state['dealer_hp'] <= 0:
                handle_round_win(bot, call.message.chat.id, user_id, state, get_conn, add_money)
                return
            if state['player_hp'] <= 0:
                handle_game_loss(bot, call.message.chat.id, user_id, state, get_conn, add_money)
                return
        bot.answer_callback_query(call.id)
        send_battle_message(bot, call.message.chat.id, user_id, state, get_conn)

    # ─── Подбор предметов в начале раунда ──────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'rlt_pick_item')
    def cb_rlt_pick_item(call):
        user_id = call.from_user.id
        state   = load_rstate(get_conn, user_id)
        if not state or state.get('phase') != 'pick_items':
            bot.answer_callback_query(call.id)
            return

        pending = state.get('pending_p_items', [])
        if not pending:
            bot.answer_callback_query(call.id, 'Нет предметов для подбора')
            return

        item = pending.pop(0)
        state['player_items'] = state.get('player_items', []) + [item]
        state['items_picked'] = state.get('items_picked', 0) + 1
        state['pending_p_items'] = pending
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f'+ {item}')
        time.sleep(1.1)

        # Все предметы подобраны — начинаем бой
        if state['items_picked'] >= state.get('items_to_pick', 0):
            state['phase'] = 'battle'
            save_rstate(get_conn, user_id, state)
            send_battle_message(bot, call.message.chat.id, user_id, state, get_conn)
        else:
            save_rstate(get_conn, user_id, state)
            # Обновляем кнопку
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton('📦 Взять предмет', callback_data='rlt_pick_item'))
            bot.send_message(
                call.message.chat.id,
                f'📦 Осталось взять: {state["items_to_pick"] - state["items_picked"]}',
                reply_markup=kb
            )

    # ─── Забрать деньги / Играть дальше ────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'rlt_take_money')
    def cb_rlt_take_money(call):
        user_id = call.from_user.id
        state   = load_rstate(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id)
            return
        winnings = calc_winnings(state['bet'], state['mode'], state['round'])
        add_money(user_id, winnings)
        add_rwin(get_conn, user_id)
        clear_rstate(get_conn, user_id)
        bot.answer_callback_query(call.id, f'💵 +{winnings:,}')
        send_main_menu(call.message.chat.id, user_id, call.message.message_id)

    @bot.callback_query_handler(func=lambda c: c.data == 'rlt_continue_play')
    def cb_rlt_continue_play(call):
        user_id = call.from_user.id
        state   = load_rstate(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id)
            return
        next_rnd = state['round'] + 1
        state = start_new_round(state, next_rnd)
        save_rstate(get_conn, user_id, state)
        bot.answer_callback_query(call.id)
        send_round_start(bot, call.message.chat.id, user_id, state, get_conn)


# ─── Вспомогательные функции вне класса ──────────────────────

def apply_item(state, item_name, user='player'):
    """Применяет предмет к состоянию игры. Возвращает (state, message)."""
    p_hp   = state['player_hp']
    d_hp   = state['dealer_hp']
    chamber = state['chamber']
    pos    = state['chamber_pos']
    msg    = ''

    if item_name == '🔎 Лупа':
        if pos < len(chamber):
            current = chamber[pos]
            ctype   = '🔴 Боевой' if current else '🟢 Холостой'
            msg = f'🔍 Лупа\n_Ты всматриваешься в механизм._\n\nТекущий патрон: {ctype}'
        else:
            msg = '🔍 Лупа\nМагазин пуст.'

    elif item_name == '🪚 Пила':
        state['saw_active'] = True
        msg = '🪚 Пила\n_Ты уродуешь ствол._\n\nСледующий боевой выстрел нанесёт 2 урона'

    elif item_name == '🍺 Пиво':
        if pos < len(chamber):
            dropped = chamber[pos]
            state['chamber_pos'] += 1
            state['shots_fired'] = state.get('shots_fired', 0) + 1
            drop_name = '🔴 Боевой' if dropped else '🟢 Холостой'
            msg = f'🍺 Пиво\n_Ты делаешь глоток._\n\nСброшен патрон: {drop_name}'
        else:
            msg = '🍺 Пиво\nМагазин пуст — нечего сбрасывать.'

    elif item_name == '🚬 Сигареты':
        if user == 'player':
            state['player_hp'] = min(state['player_max_hp'], p_hp + 1)
        else:
            state['dealer_hp'] = min(state['dealer_max_hp'], d_hp + 1)
        msg = '🚬 Сигареты\nТы делаешь затяжку.\n\n+1 🫀'

    elif item_name == '⛓️ Наручники':
        if user == 'player':
            state['dealer_skip'] = True
            msg = '⛓️ Наручники\n_Ты сковываешь противника._\n\nДилер пропускает следующий ход'
        else:
            state['player_skip'] = True
            msg = '⛓️ Наручники\n_Дилер сковывает тебя._\n\nТы пропускаешь следующий ход'

    elif item_name == '📟 Инвертор':
        if pos < len(chamber):
            chamber[pos] = not chamber[pos]
            state['chamber'] = chamber
        msg = '📟 Инвертор\n_Ты щёлкаешь реальность наоборот._\n\nТекущий патрон инвертирован'

    elif item_name == '💊 Лекарства':
        if random.random() < 0.5:
            if user == 'player':
                state['player_hp'] = min(state['player_max_hp'], p_hp + 2)
            else:
                state['dealer_hp'] = min(state['dealer_max_hp'], d_hp + 2)
            msg = '💊 Просроченные лекарства\n_Ты делаешь шаг в неизвестность._\n\n+2 🫀'
        else:
            if user == 'player':
                state['player_hp'] = max(0, p_hp - 1)
            else:
                state['dealer_hp'] = max(0, d_hp - 1)
            msg = '💊 Просроченные лекарства\n_Ты делаешь шаг в неизвестность._\n\n-1 🫀'

    elif item_name == '📞 Телефон':
        remaining = [(i, c) for i, c in enumerate(chamber) if i >= pos]
        if remaining:
            ri, rc = random.choice(remaining)
            n      = ri - pos + 1
            rtype  = 'боевой' if rc else 'холостой'
            msg = f'📞 Одноразовый телефон\n_Голос в трубке шепчет:_\n\n–«{n}-й патрон — {rtype}»'
        else:
            msg = '📞 Телефон\nМагазин пуст.'

    return state, msg


def send_battle_message(bot, chat_id, user_id, state, get_conn):
    """Отправляет актуальное сообщение боя с кнопками."""
    text = battle_text(state)
    kb   = battle_keyboard(state)
    bot.send_message(chat_id, text, reply_markup=kb)


def send_round_start(bot, chat_id, user_id, state, get_conn):
    """Отправляет сообщение начала раунда (с подбором предметов или сразу бой)."""
    rnd     = state['round']
    p_hp    = state['player_hp']
    d_hp    = state['dealer_hp']
    live    = state['live_count']
    blank   = state['blank_count']

    if state['phase'] == 'pick_items':
        items_n = state.get('items_to_pick', 0)
        text = (
            f'● — – - Раунд {rnd} - – — ●\n\n'
            f'❔ Раздаются предметы...\n\n'
            f'Ты: {hp_to_emoji(p_hp, "🫀")}\n'
            f'Дилер: {hp_to_emoji(d_hp, "⚡")}\n\n'
            f'• ——————— •\n'
            f'🟢 Холостых: {blank}\n'
            f'🔴 Боевых: {live}\n'
            f'• ——————— •'
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton('📦 Взять предмет', callback_data='rlt_pick_item'))
        bot.send_message(chat_id, text, reply_markup=kb)
    else:
        send_battle_message(bot, chat_id, user_id, state, get_conn)


def handle_round_win(bot, chat_id, user_id, state, get_conn, add_money):
    """Обрабатывает победу в раунде."""
    from buckshot_handlers import save_rstate, clear_rstate, start_new_round, send_round_start, calc_winnings

    rnd      = state['round']
    mode     = state['mode']
    bet      = state['bet']
    winnings = calc_winnings(bet, mode, rnd)

    bot.send_message(chat_id, f'🎉 Раунд {rnd} пройден!')
    time.sleep(1.1)

    max_rounds = 3 if mode == 'classic' else float('inf')
    is_checkpoint = (rnd % 10 == 0) or (rnd == 3 and mode == 'classic')

    if mode == 'classic' and rnd >= 3:
        # Финал классики
        text = (
            f'🎉 Раунд {rnd} пройден!\n\n'
            f'💰 Выйгрыш: {winnings:,}'
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton('💰 Забрать деньги', callback_data='rlt_take_money'))
        bot.send_message(chat_id, text, reply_markup=kb)
        state['phase'] = 'finished'
        save_rstate(get_conn, user_id, state)
        return

    if mode == 'tactical' and rnd >= 3 and rnd % 10 == 0 or (mode == 'tactical' and rnd == 3):
        text = (
            f'🎉 Раунд {rnd} пройден!\n\n'
            f'💰 Выйгрыш: {winnings:,}\n\n'
            f'Продолжить?'
        )
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton('☑️ Играть дальше',  callback_data='rlt_continue_play'),
            InlineKeyboardButton('💰 Забрать деньги', callback_data='rlt_take_money'),
        )
        bot.send_message(chat_id, text, reply_markup=kb)
        state['phase'] = 'checkpoint'
        save_rstate(get_conn, user_id, state)
        return

    # Следующий раунд
    next_rnd = rnd + 1
    state = start_new_round(state, next_rnd)
    save_rstate(get_conn, user_id, state)
    send_round_start(bot, chat_id, user_id, state, get_conn)


def handle_game_loss(bot, chat_id, user_id, state, get_conn, add_money):
    """Обрабатывает поражение."""
    from buckshot_handlers import clear_rstate, calc_winnings

    rnd      = state['round']
    bet      = state['bet']
    consolation = round(bet * 0.05)
    add_money(user_id, consolation)
    clear_rstate(get_conn, user_id)

    text = (
        f'☠️ Игра окончена ☠️\n\n'
        f'🎖️ Рекорд: {rnd} раунд\n\n'
        f'💵 Утешительный приз: +{consolation:,}'
    )
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('🔙 Назад', callback_data='rlt_main'))
    bot.send_message(chat_id, text, reply_markup=kb)
