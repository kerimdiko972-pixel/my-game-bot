# ============================================================
#  buckshot_pvp.py — PvP модуль для Спиншот Дуэли
#  Игра с живым игроком. Интегрируется с buckshot_handlers.py
# ============================================================

import random
import time
import json
import threading
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from buckshot_handlers import (
    ITEMS_BASIC, ITEMS_TACTICAL,
    make_chamber, hp_for_round, calc_winnings,
    hp_to_emoji, fmt_items, apply_item, item_to_cb, cb_to_item,
    fire, reload_chamber, start_new_round
)

# ─── Таймеры (секунд) ────────────────────────────────────────
CHALLENGE_EXPIRE_SEC = 120   # вызов истекает через 2 мин
TURN_WARN_SEC        = 45    # предупреждение через 45 сек
TURN_TIMEOUT_SEC     = 75    # поражение через 75 сек


# ═══════════════════════════════════════════════════════════
#  БД
# ═══════════════════════════════════════════════════════════

def init_pvp_tables(get_conn):
    conn = get_conn()
    c = conn.cursor()

    # Ожидающие вызовы
    c.execute('''
        CREATE TABLE IF NOT EXISTS roulette_challenges (
            id           SERIAL PRIMARY KEY,
            from_user_id BIGINT,
            to_user_id   BIGINT,
            mode         TEXT,
            bet          INTEGER,
            status       TEXT DEFAULT 'pending',
            created_at   TIMESTAMP DEFAULT NOW()
        )
    ''')

    # Активные PvP-матчи
    c.execute('''
        CREATE TABLE IF NOT EXISTS roulette_pvp (
            match_id     SERIAL PRIMARY KEY,
            player1_id   BIGINT,
            player2_id   BIGINT,
            state_json   TEXT,
            status       TEXT DEFAULT 'active',
            updated_at   TIMESTAMP DEFAULT NOW()
        )
    ''')

    conn.commit()
    conn.close()


def save_pvp(get_conn, match_id, state):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        UPDATE roulette_pvp
        SET state_json=%s, updated_at=NOW()
        WHERE match_id=%s
    ''', (json.dumps(state, ensure_ascii=False), match_id))
    conn.commit()
    conn.close()


def load_pvp_by_user(get_conn, user_id):
    """Возвращает (match_id, state) активного матча игрока или (None, None)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT match_id, state_json FROM roulette_pvp
        WHERE status='active' AND (player1_id=%s OR player2_id=%s)
        ORDER BY updated_at DESC LIMIT 1
    ''', (user_id, user_id))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0], json.loads(row[1])
    return None, None


def load_pvp_by_match(get_conn, match_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT state_json FROM roulette_pvp WHERE match_id=%s', (match_id,))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None


def close_pvp(get_conn, match_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE roulette_pvp SET status='finished' WHERE match_id=%s", (match_id,))
    conn.commit()
    conn.close()


def create_pvp_match(get_conn, p1_id, p2_id, state):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO roulette_pvp (player1_id, player2_id, state_json)
        VALUES (%s, %s, %s) RETURNING match_id
    ''', (p1_id, p2_id, json.dumps(state, ensure_ascii=False)))
    match_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    return match_id


def save_challenge(get_conn, from_id, to_id, mode, bet):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO roulette_challenges (from_user_id, to_user_id, mode, bet)
        VALUES (%s, %s, %s, %s) RETURNING id
    ''', (from_id, to_id, mode, bet))
    cid = c.fetchone()[0]
    conn.commit()
    conn.close()
    return cid


def get_challenge(get_conn, challenge_id):
    conn = get_conn()
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    c.execute('SELECT * FROM roulette_challenges WHERE id=%s', (challenge_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def update_challenge_status(get_conn, challenge_id, status):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE roulette_challenges SET status=%s WHERE id=%s', (status, challenge_id))
    conn.commit()
    conn.close()


def get_pending_challenges(get_conn, to_user_id):
    """Входящие вызовы для игрока."""
    conn = get_conn()
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    c.execute('''
        SELECT rc.*, u.username as from_username
        FROM roulette_challenges rc
        JOIN users u ON u.user_id = rc.from_user_id
        WHERE rc.to_user_id=%s AND rc.status='pending'
        ORDER BY rc.created_at DESC
    ''', (to_user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_players(get_conn, exclude_id, limit=10):
    """Недавно активные игроки (у кого есть private_chat_id)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT user_id, username FROM users
        WHERE user_id != %s AND private_chat_id IS NOT NULL
        ORDER BY user_id DESC LIMIT %s
    ''', (exclude_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows


# ═══════════════════════════════════════════════════════════
#  Инициализация PvP-матча
# ═══════════════════════════════════════════════════════════

def init_pvp_state(p1_id, p1_name, p2_id, p2_name,
                   p1_chat_id, p2_chat_id, mode, bet):
    """Создаёт начальное состояние PvP-матча."""
    state = {
        'mode':      mode,
        'bet':       bet,
        # Игроки
        'p1_id':     p1_id,
        'p1_name':   p1_name,
        'p1_chat':   p1_chat_id,
        'p2_id':     p2_id,
        'p2_name':   p2_name,
        'p2_chat':   p2_chat_id,
        # Кто сейчас ходит: 'p1' | 'p2'
        'turn':      'p1',
        'first_of_round': 'p1',  # кто ходит первым в этом раунде
        'phase':     'battle',   # battle | gun_drawn | pick_items | finished
        'round':     1,
        # HP
        'p1_hp':     2,
        'p1_max_hp': 2,
        'p2_hp':     2,
        'p2_max_hp': 2,
        # Патроны
        'chamber':     [],
        'chamber_pos': 0,
        'live_count':  0,
        'blank_count': 0,
        'shots_fired': 0,
        # Предметы
        'p1_items':  [],
        'p2_items':  [],
        'pending_p1_items': [],
        'pending_p2_items': [],
        'items_to_pick': 0,
        'p1_items_picked': 0,
        'p2_items_picked': 0,
        # Эффекты
        'saw_active':    False,
        'p1_skip':       False,
        'p2_skip':       False,
        'extra_turn_used': False,
        # Таймер хода
        'turn_started_at': datetime.now().isoformat(),
        'turn_warned':     False,
    }
    # Генерируем первый магазин
    chamber, live, blank = make_chamber()
    state['chamber']     = chamber
    state['live_count']  = live
    state['blank_count'] = blank
    return state


def pvp_start_round(state, rnd):
    """Сбрасывает состояние для нового раунда."""
    mode = state.get('mode', 'classic')
    hp   = hp_for_round(rnd)[0]  # одинаковое HP для обоих
    chamber, live, blank = make_chamber()
    items_count = random.randint(1, 4) if rnd > 1 else 0
    item_pool   = ITEMS_TACTICAL if mode == 'tactical' else ITEMS_BASIC
    p1_items = [random.choice(item_pool) for _ in range(items_count)]
    p2_items = [random.choice(item_pool) for _ in range(items_count)]

    state.update({
        'round':             rnd,
        'p1_hp':             hp,
        'p1_max_hp':         hp,
        'p2_hp':             hp,
        'p2_max_hp':         hp,
        'chamber':           chamber,
        'chamber_pos':       0,
        'live_count':        live,
        'blank_count':       blank,
        'shots_fired':       0,
        'turn':              'p1',
        'first_of_round':    'p1',
        'phase':             'pick_items' if rnd > 1 else 'battle',
        'items_to_pick':     items_count,
        'p1_items_picked':   0,
        'p2_items_picked':   0,
        'p1_items':          [] if rnd > 1 else [],
        'p2_items':          [] if rnd > 1 else [],
        'pending_p1_items':  p1_items,
        'pending_p2_items':  p2_items,
        'saw_active':        False,
        'p1_skip':           False,
        'p2_skip':           False,
        'extra_turn_used':   False,
        'turn_started_at':   datetime.now().isoformat(),
        'turn_warned':       False,
    })
    return state


# ═══════════════════════════════════════════════════════════
#  Форматирование сообщений
# ═══════════════════════════════════════════════════════════

def pvp_battle_text(state, viewer_id):
    """Генерирует текст боя для конкретного игрока."""
    p1_id  = state['p1_id']
    p2_id  = state['p2_id']
    rnd    = state['round']
    shots  = state['shots_fired']

    is_p1  = (viewer_id == p1_id)
    my_hp  = state['p1_hp'] if is_p1 else state['p2_hp']
    op_hp  = state['p2_hp'] if is_p1 else state['p1_hp']
    my_items  = state['p1_items'] if is_p1 else state['p2_items']
    op_items  = state['p2_items'] if is_p1 else state['p1_items']

    turn   = state['turn']
    is_my_turn = (turn == 'p1' and is_p1) or (turn == 'p2' and not is_p1)
    turn_line  = '🔔 Ход у тебя' if is_my_turn else '🔔 Ход соперника'

    ammo_block = ''
    if shots == 0:
        ammo_block = f'🟢 Холостых: {state["blank_count"]}\n🔴 Боевых: {state["live_count"]}\n'

    # Эффекты
    effects = []
    if state.get('saw_active'):
        effects.append('🪚 Следующий выстрел усилен')
    my_skipped  = (state.get('p1_skip') and is_p1) or (state.get('p2_skip') and not is_p1)
    op_skipped  = (state.get('p2_skip') and is_p1) or (state.get('p1_skip') and not is_p1)
    if op_skipped:
        effects.append('⛓️ Противник скован')
    eff_line = '\n'.join(effects)

    items_block = ''
    if rnd > 1:
        items_block = (
            f'\nПредметы соперника: {fmt_items(op_items)}'
            f'\nТвои предметы: {fmt_items(my_items)}\n'
        )

    text = (
        f'● — – - Раунд {rnd} - – — ●\n\n'
        f'{turn_line}\n\n'
        f'Ты: {hp_to_emoji(my_hp, "🫀")}\n'
        f'Противник: {hp_to_emoji(op_hp, "🫀")}\n\n'
        f'• ——————— •\n'
        f'{ammo_block}'
        f'• ——————— •'
        f'{items_block}'
    )
    if eff_line:
        text += f'\n\n🔹 {eff_line}'
    return text


def pvp_battle_keyboard(state, viewer_id):
    """Клавиатура для активного игрока."""
    p1_id = state['p1_id']
    is_p1 = (viewer_id == p1_id)
    turn  = state['turn']
    is_my_turn = (turn == 'p1' and is_p1) or (turn == 'p2' and not is_p1)

    kb = InlineKeyboardMarkup(row_width=2)

    if not is_my_turn:
        # Не твой ход — кнопок нет
        return kb

    phase = state.get('phase', 'battle')

    if phase == 'gun_drawn':
        kb.add(
            InlineKeyboardButton('🎯 В соперника', callback_data='pvp_shoot_op'),
            InlineKeyboardButton('🎭 В себя',      callback_data='pvp_shoot_self'),
        )
        return kb

    kb.add(InlineKeyboardButton('🔫 Взять ружьё', callback_data='pvp_take_gun'))

    my_items = state['p1_items'] if is_p1 else state['p2_items']
    for item in my_items:
        key = item_to_cb(item)
        kb.add(InlineKeyboardButton(item, callback_data=f'pvp_use_{key}'))

    return kb


def waiting_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('⏳ Ожидание хода соперника...', callback_data='pvp_noop'))
    return kb


# ═══════════════════════════════════════════════════════════
#  Рассылка сообщений обоим игрокам
# ═══════════════════════════════════════════════════════════

PRIVATE_ITEMS = {'🔎 Лупа', '📞 Телефон', '📟 Инвертор'}


def notify_both(bot, state, match_id, actor_id,
                private_msg, public_msg, parse_mode=None):
    """
    Отправляет actor_id — private_msg (полное),
    сопернику     — public_msg (короткое).
    """
    p1_id   = state['p1_id']
    p2_id   = state['p2_id']
    p1_chat = state['p1_chat']
    p2_chat = state['p2_chat']

    opponent_id   = p2_id   if actor_id == p1_id else p1_id
    opponent_chat = p2_chat if actor_id == p1_id else p1_chat
    actor_chat    = p1_chat if actor_id == p1_id else p2_chat

    try:
        bot.send_message(actor_chat, private_msg, parse_mode=parse_mode)
    except Exception as e:
        print(f'[PvP] notify actor error: {e}')
    time.sleep(0.3)
    try:
        bot.send_message(opponent_chat, public_msg, parse_mode=parse_mode)
    except Exception as e:
        print(f'[PvP] notify opponent error: {e}')


def send_battle_to_both(bot, state, match_id):
    """Отправляет обоим игрокам актуальное сообщение боя."""
    p1_id   = state['p1_id']
    p2_id   = state['p2_id']
    p1_chat = state['p1_chat']
    p2_chat = state['p2_chat']

    for uid, chat in [(p1_id, p1_chat), (p2_id, p2_chat)]:
        text = pvp_battle_text(state, uid)
        kb   = pvp_battle_keyboard(state, uid)
        try:
            bot.send_message(chat, text, reply_markup=kb)
        except Exception as e:
            print(f'[PvP] send_battle_to_both error uid={uid}: {e}')
        time.sleep(0.3)


# ═══════════════════════════════════════════════════════════
#  Логика выстрела в PvP
# ═══════════════════════════════════════════════════════════

def pvp_fire(state, actor_id, target):
    """
    target: 'opponent' | 'self'
    Возвращает (state, is_live, damage).
    """
    p1_id = state['p1_id']
    is_p1 = (actor_id == p1_id)

    if target == 'self':
        fire_target = 'p1' if is_p1 else 'p2'
    else:
        fire_target = 'p2' if is_p1 else 'p1'

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
        hp_key = f'{fire_target}_hp'
        state[hp_key] = max(0, state[hp_key] - damage)

    return state, is_live, damage


def switch_turn(state):
    """Переключает ход между игроками."""
    state['turn'] = 'p2' if state['turn'] == 'p1' else 'p1'
    state['turn_started_at'] = datetime.now().isoformat()
    state['turn_warned']     = False
    state['extra_turn_used'] = False
    return state


def actor_name(state, actor_id):
    return state['p1_name'] if actor_id == state['p1_id'] else state['p2_name']


def get_actor_id_from_turn(state):
    return state['p1_id'] if state['turn'] == 'p1' else state['p2_id']


# ═══════════════════════════════════════════════════════════
#  Завершение матча
# ═══════════════════════════════════════════════════════════

def pvp_end_match(bot, state, match_id, winner_id, get_conn,
                  add_money, add_exp, add_rwin):
    """Завершает PvP-матч, начисляет награды."""
    p1_id   = state['p1_id']
    p2_id   = state['p2_id']
    p1_chat = state['p1_chat']
    p2_chat = state['p2_chat']
    bet     = state['bet']
    mode    = state['mode']
    rnd     = state['round']

    loser_id    = p2_id if winner_id == p1_id else p1_id
    winner_chat = p1_chat if winner_id == p1_id else p2_chat
    loser_chat  = p2_chat if winner_id == p1_id else p1_chat

    winnings = bet * 2  # победитель забирает обе ставки
    exp_gain = 200 + rnd * 50

    add_money(winner_id, winnings)
    add_exp(winner_id, exp_gain)
    add_rwin(get_conn, winner_id)

    close_pvp(get_conn, match_id)

    from buckshot_handlers import save_rstate, clear_rstate
    clear_rstate(get_conn, p1_id)
    clear_rstate(get_conn, p2_id)

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton('👤 Игра с игроком', callback_data='rlt_pvp_menu'),
        InlineKeyboardButton('👺 Игра с дилером', callback_data='rlt_dealer'),
        InlineKeyboardButton('🏆 Рекорды',         callback_data='rlt_leaderboard'),
    )

    try:
        bot.send_message(
            winner_chat,
            f'🏆 Ты победил!\n\n'
            f'💵 Выигрыш: {winnings:,}\n'
            f'🎖️ Побед добавлено: +1\n'
            f'⭐ Опыт добавлен: +{exp_gain:,}',
            reply_markup=kb
        )
    except Exception as e:
        print(f'[PvP] winner notify error: {e}')

    try:
        bot.send_message(
            loser_chat,
            f'💀 Ты проиграл...\n\n'
            f'💵 Потеря ставки: {bet:,}',
            reply_markup=kb
        )
    except Exception as e:
        print(f'[PvP] loser notify error: {e}')


def pvp_forfeit(bot, state, match_id, quitter_id, reason,
                get_conn, add_money, add_exp, add_rwin):
    """Засчитывает поражение вышедшему игроку."""
    p1_id = state['p1_id']
    winner_id = state['p2_id'] if quitter_id == p1_id else p1_id
    pvp_end_match(bot, state, match_id, winner_id,
                  get_conn, add_money, add_exp, add_rwin)
    # Уведомляем победителя отдельно
    winner_chat = state['p1_chat'] if winner_id == p1_id else state['p2_chat']
    try:
        bot.send_message(winner_chat,
                         f'🏳️ Противник покинул матч. Победа присуждается тебе!')
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
#  Таймер хода
# ═══════════════════════════════════════════════════════════

def start_turn_timer(bot, get_conn, add_money, add_exp, add_rwin):
    """Фоновый поток, проверяющий таймауты ходов."""
    def loop():
        while True:
            try:
                conn = get_conn()
                c = conn.cursor()
                c.execute('''
                    SELECT match_id, state_json
                    FROM roulette_pvp
                    WHERE status='active'
                ''')
                rows = c.fetchall()
                conn.close()

                for match_id, state_json in rows:
                    state = json.loads(state_json)
                    ts_str = state.get('turn_started_at')
                    if not ts_str:
                        continue
                    ts      = datetime.fromisoformat(ts_str)
                    elapsed = (datetime.now() - ts).total_seconds()
                    actor_id = get_actor_id_from_turn(state)
                    actor_chat = state['p1_chat'] if actor_id == state['p1_id'] else state['p2_chat']

                    if elapsed >= TURN_TIMEOUT_SEC:
                        # Поражение по таймауту
                        pvp_forfeit(bot, state, match_id, actor_id,
                                    'timeout', get_conn, add_money, add_exp, add_rwin)
                    elif elapsed >= TURN_WARN_SEC and not state.get('turn_warned'):
                        # Предупреждение
                        try:
                            bot.send_message(
                                actor_chat,
                                '⚠️ Твой ход! Осталось ~30 секунд, иначе засчитается поражение.'
                            )
                        except Exception:
                            pass
                        state['turn_warned'] = True
                        save_pvp(get_conn, match_id, state)

            except Exception as e:
                print(f'[PvP timer] error: {e}')
            time.sleep(10)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


# ═══════════════════════════════════════════════════════════
#  Также таймер истечения вызовов
# ═══════════════════════════════════════════════════════════

def start_challenge_timer(bot, get_conn):
    def loop():
        while True:
            try:
                conn = get_conn()
                c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                c.execute('''
                    SELECT * FROM roulette_challenges
                    WHERE status='pending'
                    AND created_at < NOW() - INTERVAL '%s seconds'
                ''', (CHALLENGE_EXPIRE_SEC,))
                expired = c.fetchall()
                conn.close()
                for ch in expired:
                    update_challenge_status(get_conn, ch['id'], 'expired')
                    from_chat = _get_private_chat(get_conn, ch['from_user_id'])
                    if from_chat:
                        try:
                            bot.send_message(from_chat,
                                             '⏳ Вызов истёк — игрок не ответил.')
                        except Exception:
                            pass
            except Exception as e:
                print(f'[Challenge timer] error: {e}')
            time.sleep(15)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


def _get_private_chat(get_conn, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT private_chat_id FROM users WHERE user_id=%s', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else None


# ═══════════════════════════════════════════════════════════
#  Регистрация хэндлеров
# ═══════════════════════════════════════════════════════════

def register_pvp_handlers(bot, get_conn, get_user,
                           add_money, spend_money, add_exp, add_rwin):

    pending_pvp = {}   # user_id: {'step': str, ...}

    def safe_edit(chat_id, msg_id, text, kb=None):
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, text, reply_markup=kb)

    def get_username(user_id):
        user = get_user(user_id)
        return (user[1] or f'id{user_id}') if user else f'id{user_id}'

    # ─── Меню PvP ───────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'rlt_pvp_menu')
    def cb_pvp_menu(call):
        user_id = call.from_user.id
        text = (
            '👤 ИГРА С ИГРОКОМ\n\n'
            'Выбери способ дуэли:'
        )
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton('📨 Вызвать игрока',    callback_data='pvp_invite_list'),
            InlineKeyboardButton('🔎 Найти по @username', callback_data='pvp_invite_username'),
            InlineKeyboardButton('📜 Мои вызовы',        callback_data='pvp_my_challenges'),
            InlineKeyboardButton('🔙 Назад',              callback_data='rlt_main'),
        )
        safe_edit(call.message.chat.id, call.message.message_id, text, kb)
        bot.answer_callback_query(call.id)

    # ─── Список игроков ─────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_invite_list')
    def cb_pvp_invite_list(call):
        user_id = call.from_user.id
        players = get_recent_players(get_conn, user_id, limit=10)
        if not players:
            bot.answer_callback_query(call.id, 'Нет доступных игроков', show_alert=True)
            return
        text = 'Выбери игрока для дуэли:'
        kb   = InlineKeyboardMarkup(row_width=1)
        for uid, uname in players:
            kb.add(InlineKeyboardButton(
                f'👤 {uname or f"id{uid}"}',
                callback_data=f'pvp_select_{uid}'
            ))
        kb.add(InlineKeyboardButton('🔙 Назад', callback_data='rlt_pvp_menu'))
        safe_edit(call.message.chat.id, call.message.message_id, text, kb)
        bot.answer_callback_query(call.id)

    # ─── Поиск по @username ──────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_invite_username')
    def cb_pvp_invite_username(call):
        user_id = call.from_user.id
        pending_pvp[user_id] = {
            'step':    'enter_username',
            'chat_id': call.message.chat.id,
            'msg_id':  call.message.message_id,
        }
        safe_edit(call.message.chat.id, call.message.message_id,
                  '🔎 Введи @username игрока:',
                  InlineKeyboardMarkup().add(
                      InlineKeyboardButton('🔙 Назад', callback_data='rlt_pvp_menu')
                  ))
        bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda m: m.from_user.id in pending_pvp
                          and pending_pvp[m.from_user.id].get('step') == 'enter_username')
    def handle_pvp_username(message):
        user_id  = message.from_user.id
        uname    = message.text.strip().lstrip('@')
        info     = pending_pvp.get(user_id, {})

        conn = get_conn()
        c = conn.cursor()
        c.execute('SELECT user_id, username, private_chat_id FROM users WHERE username=%s', (uname,))
        row = c.fetchone()
        conn.close()

        if not row or not row[2]:
            bot.send_message(message.chat.id,
                             f'❌ Игрок @{uname} не найден или не запускал бота.\n\nВыбери другого.')
            return

        target_id = row[0]
        if target_id == user_id:
            bot.send_message(message.chat.id, '❌ Нельзя вызвать самого себя!')
            return

        pending_pvp.pop(user_id, None)
        _show_challenge_setup(bot, message.chat.id, user_id, target_id, uname, pending_pvp)

    # ─── Выбор игрока из списка ──────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('pvp_select_'))
    def cb_pvp_select(call):
        user_id   = call.from_user.id
        target_id = int(call.data.split('_')[-1])
        target_name = get_username(target_id)
        bot.answer_callback_query(call.id)
        _show_challenge_setup(bot, call.message.chat.id, user_id,
                              target_id, target_name, pending_pvp,
                              msg_id=call.message.message_id)

    # ─── Выбор режима для вызова ─────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('pvp_cmode_'))
    def cb_pvp_cmode(call):
        user_id = call.from_user.id
        mode    = call.data[len('pvp_cmode_'):]
        info    = pending_pvp.get(user_id, {})
        if not info:
            bot.answer_callback_query(call.id)
            return
        pending_pvp[user_id]['mode'] = mode
        pending_pvp[user_id]['mode_name'] = '🟢 Классический риск' if mode == 'classic' else '🔴 Тактика дилера'
        pending_pvp[user_id]['step'] = 'enter_bet'

        user  = get_user(user_id)
        money = user[2] if user else 0
        text  = (
            f'⚔️ Создание вызова\n\n'
            f'Игрок: {info["target_name"]}\n'
            f'Режим: {pending_pvp[user_id]["mode_name"]}\n\n'
            f'Денег: 💵 {money:,}\n\n'
            f'💰 Введи ставку (мин. 500):'
        )
        safe_edit(call.message.chat.id, call.message.message_id, text,
                  InlineKeyboardMarkup().add(
                      InlineKeyboardButton('🔙 Назад', callback_data='rlt_pvp_menu')
                  ))
        bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda m: m.from_user.id in pending_pvp
                          and pending_pvp[m.from_user.id].get('step') == 'enter_bet')
    def handle_pvp_bet(message):
        user_id = message.from_user.id
        info    = pending_pvp.get(user_id, {})

        try:
            bet = int(message.text.strip().replace(',', '').replace(' ', ''))
        except ValueError:
            bot.send_message(message.chat.id, '❌ Введи число!')
            return

        if bet < 500:
            bot.send_message(message.chat.id, '❌ Минимальная ставка 500!')
            return

        user  = get_user(user_id)
        money = user[2] if user else 0
        if money < bet:
            bot.send_message(message.chat.id,
                             f'❌ Недостаточно средств! У тебя 💵 {money:,}')
            return

        pending_pvp[user_id]['bet']  = bet
        pending_pvp[user_id]['step'] = 'confirm'

        text = (
            f'⚔️ Создание вызова\n\n'
            f'Игрок: {info["target_name"]}\n'
            f'Режим: {info["mode_name"]}\n'
            f'Ставка: {bet:,}\n\n'
            f'Подтвердить вызов?'
        )
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton('✅ Отправить вызов', callback_data='pvp_confirm_challenge'),
            InlineKeyboardButton('🔙 Назад',            callback_data='rlt_pvp_menu'),
        )
        bot.send_message(message.chat.id, text, reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_confirm_challenge')
    def cb_pvp_confirm(call):
        user_id = call.from_user.id
        info    = pending_pvp.pop(user_id, None)
        if not info:
            bot.answer_callback_query(call.id)
            return

        user  = get_user(user_id)
        money = user[2] if user else 0
        bet   = info['bet']
        if money < bet:
            bot.answer_callback_query(call.id, '❌ Недостаточно средств!', show_alert=True)
            return

        target_id   = info['target_id']
        target_name = info['target_name']
        mode        = info['mode']
        mode_name   = info['mode_name']
        from_name   = get_username(user_id)

        # Резервируем ставку
        spend_money(user_id, bet)

        cid = save_challenge(get_conn, user_id, target_id, mode, bet)

        # Отправляем вызов цели
        target_chat = _get_private_chat(get_conn, target_id)
        if not target_chat:
            bot.answer_callback_query(call.id, '❌ Не удалось отправить вызов.', show_alert=True)
            # Возвращаем деньги
            add_money(user_id, bet)
            update_challenge_status(get_conn, cid, 'cancelled')
            return

        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton('✅ Принять',   callback_data=f'pvp_accept_{cid}'),
            InlineKeyboardButton('❌ Отклонить', callback_data=f'pvp_decline_{cid}'),
        )
        try:
            bot.send_message(
                target_chat,
                f'⚔️ Тебя вызвали на дуэль!\n\n'
                f'Противник: @{from_name}\n'
                f'Режим: {mode_name}\n'
                f'Ставка: {bet:,}\n\n'
                f'Принять вызов?',
                reply_markup=kb
            )
        except Exception as e:
            print(f'[PvP] send challenge error: {e}')

        safe_edit(call.message.chat.id, call.message.message_id,
                  f'✅ Вызов отправлен игроку @{target_name}!\nОжидаем ответа...',
                  InlineKeyboardMarkup().add(
                      InlineKeyboardButton('🔙 В меню', callback_data='rlt_main')
                  ))
        bot.answer_callback_query(call.id)

    # ─── Принять / отклонить вызов ──────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('pvp_accept_'))
    def cb_pvp_accept(call):
        user_id     = call.from_user.id
        challenge_id = int(call.data.split('_')[-1])
        ch          = get_challenge(get_conn, challenge_id)

        if not ch or ch['status'] != 'pending':
            bot.answer_callback_query(call.id, '❌ Вызов недействителен', show_alert=True)
            return
        if ch['to_user_id'] != user_id:
            bot.answer_callback_query(call.id, '❌ Это не твой вызов', show_alert=True)
            return

        bet = ch['bet']
        user = get_user(user_id)
        money = user[2] if user else 0
        if money < bet:
            bot.answer_callback_query(call.id, f'❌ Недостаточно средств! Нужно {bet:,}', show_alert=True)
            return

        spend_money(user_id, bet)
        update_challenge_status(get_conn, challenge_id, 'accepted')

        p1_id    = ch['from_user_id']
        p2_id    = user_id
        p1_name  = get_username(p1_id)
        p2_name  = get_username(p2_id)
        p1_chat  = _get_private_chat(get_conn, p1_id)
        p2_chat  = call.message.chat.id
        mode     = ch['mode']
        mode_name = '🟢 Классический риск' if mode == 'classic' else '🔴 Тактика дилера'

        state    = init_pvp_state(p1_id, p1_name, p2_id, p2_name,
                                  p1_chat, p2_chat, mode, bet)
        match_id = create_pvp_match(get_conn, p1_id, p2_id, state)
        state['match_id'] = match_id
        save_pvp(get_conn, match_id, state)

        start_text = (
            f'⚔️ Дуэль началась!\n\n'
            f'Противник: {{}}\n'
            f'Ставка: {bet:,}\n'
            f'Режим: {mode_name}\n\n'
            f'Готовься к первому раунду...'
        )
        time.sleep(0.5)
        # Отправляем обоим
        try:
            bot.send_message(p1_chat,
                             start_text.format(f'@{p2_name}'))
        except Exception:
            pass
        time.sleep(0.5)
        try:
            bot.send_message(p2_chat,
                             start_text.format(f'@{p1_name}'))
        except Exception:
            pass

        time.sleep(1.1)
        send_battle_to_both(bot, state, match_id)
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('pvp_decline_'))
    def cb_pvp_decline(call):
        user_id      = call.from_user.id
        challenge_id = int(call.data.split('_')[-1])
        ch           = get_challenge(get_conn, challenge_id)

        if not ch or ch['status'] != 'pending':
            bot.answer_callback_query(call.id)
            return

        update_challenge_status(get_conn, challenge_id, 'declined')
        decliner_name = get_username(user_id)

        # Возвращаем деньги отправителю
        add_money(ch['from_user_id'], ch['bet'])
        from_chat = _get_private_chat(get_conn, ch['from_user_id'])
        if from_chat:
            try:
                bot.send_message(from_chat,
                                 f'❌ Игрок @{decliner_name} отклонил вызов. Ставка возвращена.')
            except Exception:
                pass

        safe_edit(call.message.chat.id, call.message.message_id,
                  '❌ Ты отклонил вызов.',
                  InlineKeyboardMarkup().add(
                      InlineKeyboardButton('🔙 В меню', callback_data='rlt_main')
                  ))
        bot.answer_callback_query(call.id)

    # ─── Мои вызовы ─────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_my_challenges')
    def cb_pvp_my_challenges(call):
        user_id    = call.from_user.id
        challenges = get_pending_challenges(get_conn, user_id)
        if not challenges:
            bot.answer_callback_query(call.id, 'Нет входящих вызовов', show_alert=True)
            return

        text = '📜 Входящие вызовы:\n\n'
        kb   = InlineKeyboardMarkup(row_width=2)
        for ch in challenges:
            mode_name = 'Классика' if ch['mode'] == 'classic' else 'Тактика'
            text += f'⚔️ @{ch["from_username"]} | {mode_name} | {ch["bet"]:,} 💵\n'
            kb.add(
                InlineKeyboardButton(f'✅ @{ch["from_username"]}', callback_data=f'pvp_accept_{ch["id"]}'),
                InlineKeyboardButton('❌', callback_data=f'pvp_decline_{ch["id"]}'),
            )
        kb.add(InlineKeyboardButton('🔙 Назад', callback_data='rlt_pvp_menu'))
        safe_edit(call.message.chat.id, call.message.message_id, text, kb)
        bot.answer_callback_query(call.id)

    # ─── Взять ружьё (PvP) ──────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_take_gun')
    def cb_pvp_take_gun(call):
        user_id  = call.from_user.id
        match_id, state = load_pvp_by_user(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id, 'Матч не найден')
            return
        if get_actor_id_from_turn(state) != user_id:
            bot.answer_callback_query(call.id, '⏳ Сейчас не твой ход!')
            return

        state['phase'] = 'gun_drawn'
        save_pvp(get_conn, match_id, state)
        bot.answer_callback_query(call.id)

        # Обновляем сообщение только активному игроку
        actor_chat = state['p1_chat'] if user_id == state['p1_id'] else state['p2_chat']
        text = pvp_battle_text(state, user_id) + '\n\n🔫 Ты взял ружьё, выбери цель:'
        kb   = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton('🎯 В соперника', callback_data='pvp_shoot_op'),
            InlineKeyboardButton('🎭 В себя',      callback_data='pvp_shoot_self'),
        )
        bot.send_message(actor_chat, text, reply_markup=kb)

    # ─── Выстрелы (PvP) ─────────────────────────────────────

    def process_pvp_shot(call, target):
        user_id  = call.from_user.id
        match_id, state = load_pvp_by_user(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id, 'Матч не найден')
            return
        if get_actor_id_from_turn(state) != user_id:
            bot.answer_callback_query(call.id, '⏳ Сейчас не твой ход!')
            return
        if state.get('phase') != 'gun_drawn':
            bot.answer_callback_query(call.id, 'Сначала возьми ружьё!')
            return

        bot.answer_callback_query(call.id)
        state['phase'] = 'battle'

        aname = actor_name(state, user_id)
        target_word = 'в себя' if target == 'self' else 'в соперника'

        # Сообщение о прицеливании
        actor_chat = state['p1_chat'] if user_id == state['p1_id'] else state['p2_chat']
        op_chat    = state['p2_chat'] if user_id == state['p1_id'] else state['p1_chat']
        aim_txt    = f'Ты целишься {target_word}. . .'

        bot.send_message(actor_chat, f'_{aim_txt}_', parse_mode='Markdown')
        bot.send_message(op_chat,    f'_{aname} целится {target_word}. . ._', parse_mode='Markdown')
        time.sleep(1.1)

        state, is_live, damage = pvp_fire(state, user_id, target)

        if is_live:
            dmg_target = 'тебя' if target == 'self' else 'соперника'
            private_result = f'💥 Боевой! -{damage} 🫀 ({dmg_target})'
            public_result  = f'💥 Боевой! @{aname} -{damage} 🫀'
        else:
            private_result = '💨 Холостой...'
            public_result  = f'💨 Холостой... (@{aname})'

        bot.send_message(actor_chat, private_result)
        time.sleep(0.3)
        bot.send_message(op_chat, public_result)
        time.sleep(1.1)

        # Проверка победы
        p1_dead = state['p1_hp'] <= 0
        p2_dead = state['p2_hp'] <= 0

        if p1_dead or p2_dead:
            winner_id = state['p2_id'] if p1_dead else state['p1_id']
            save_pvp(get_conn, match_id, state)
            pvp_end_match(bot, state, match_id, winner_id,
                          get_conn, add_money, add_exp, add_rwin)
            return

        # Патроны кончились — перезарядка
        if state['chamber_pos'] >= len(state['chamber']):
            state, reload_msg = _pvp_reload(state)
            bot.send_message(actor_chat, reload_msg)
            time.sleep(0.3)
            bot.send_message(op_chat, reload_msg)
            time.sleep(1.1)
            save_pvp(get_conn, match_id, state)
            send_battle_to_both(bot, state, match_id)
            return

        # Доп. ход при холостом в себя
        if target == 'self' and not is_live and not state.get('extra_turn_used'):
            state['extra_turn_used'] = True
            bot.send_message(actor_chat, '🔔 Холостой в себя — ты получаешь дополнительный ход!')
            time.sleep(0.3)
            bot.send_message(op_chat, f'🔔 @{aname} получает дополнительный ход!')
            time.sleep(1.1)
            save_pvp(get_conn, match_id, state)
            send_battle_to_both(bot, state, match_id)
            return

        # Проверка скипа
        state = switch_turn(state)
        next_actor_id = get_actor_id_from_turn(state)
        next_key = 'p1' if next_actor_id == state['p1_id'] else 'p2'
        if state.get(f'{next_key}_skip'):
            state[f'{next_key}_skip'] = False
            skip_chat = state['p1_chat'] if next_actor_id == state['p1_id'] else state['p2_chat']
            other_chat = state['p2_chat'] if next_actor_id == state['p1_id'] else state['p1_chat']
            bot.send_message(skip_chat,  '⛓️ Ты скован и пропускаешь ход!')
            bot.send_message(other_chat, f'⛓️ @{get_username(next_actor_id)} скован и пропускает ход!')
            time.sleep(1.1)
            state = switch_turn(state)

        save_pvp(get_conn, match_id, state)
        send_battle_to_both(bot, state, match_id)

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_shoot_op')
    def cb_pvp_shoot_op(call):
        process_pvp_shot(call, 'opponent')

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_shoot_self')
    def cb_pvp_shoot_self(call):
        process_pvp_shot(call, 'self')

    # ─── Предметы (PvP) ─────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('pvp_use_'))
    def cb_pvp_use_item(call):
        user_id  = call.from_user.id
        match_id, state = load_pvp_by_user(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id, 'Матч не найден')
            return
        if get_actor_id_from_turn(state) != user_id:
            bot.answer_callback_query(call.id, '⏳ Сейчас не твой ход!')
            return
        if state.get('phase') == 'gun_drawn':
            bot.answer_callback_query(call.id, 'После взятия ружья предметы нельзя использовать!')
            return

        item_key  = call.data[len('pvp_use_'):]
        item_name = cb_to_item(item_key)
        if not item_name:
            bot.answer_callback_query(call.id, 'Неизвестный предмет')
            return

        is_p1    = (user_id == state['p1_id'])
        items_key = 'p1_items' if is_p1 else 'p2_items'
        my_items  = state.get(items_key, [])

        if item_name not in my_items:
            bot.answer_callback_query(call.id, 'У тебя нет этого предмета!')
            return

        bot.answer_callback_query(call.id)

        # Адреналин — украсть у соперника
        if item_name == '💉 Адреналин':
            op_key   = 'p2_items' if is_p1 else 'p1_items'
            op_items = state.get(op_key, [])
            if not op_items:
                bot.send_message(call.message.chat.id,
                                 '💉 У соперника нет предметов для кражи!')
                return
            my_items.remove(item_name)
            state[items_key] = my_items
            save_pvp(get_conn, match_id, state)
            # Показываем список предметов соперника
            kb = InlineKeyboardMarkup(row_width=2)
            for itm in op_items:
                if itm != '💉 Адреналин':
                    kb.add(InlineKeyboardButton(itm, callback_data=f'pvp_steal_{item_to_cb(itm)}'))
            actor_chat = state['p1_chat'] if is_p1 else state['p2_chat']
            bot.send_message(
                actor_chat,
                '💉 Адреналин\n_Ты срываешься в рывок._\n\nВыбери предмет у соперника:',
                parse_mode='Markdown', reply_markup=kb
            )
            op_chat = state['p2_chat'] if is_p1 else state['p1_chat']
            bot.send_message(op_chat, f'💉 @{get_username(user_id)} использует Адреналин...')
            return

        my_items.remove(item_name)
        state[items_key] = my_items

        # Применяем предмет к общему состоянию
        # Для PvP нужно отдельно отслеживать кто "player" кто "opponent"
        # Конвертируем state в формат apply_item
        tmp_state = {
            'player_hp':     state['p1_hp']    if is_p1 else state['p2_hp'],
            'player_max_hp': state['p1_max_hp'] if is_p1 else state['p2_max_hp'],
            'dealer_hp':     state['p2_hp']    if is_p1 else state['p1_hp'],
            'dealer_max_hp': state['p2_max_hp'] if is_p1 else state['p1_max_hp'],
            'chamber':       state['chamber'],
            'chamber_pos':   state['chamber_pos'],
            'shots_fired':   state['shots_fired'],
            'saw_active':    state['saw_active'],
            'dealer_skip':   state.get('p2_skip' if is_p1 else 'p1_skip', False),
            'player_skip':   state.get('p1_skip' if is_p1 else 'p2_skip', False),
        }
        tmp_state, msg = apply_item(tmp_state, item_name, user='player')

        # Синхронизируем обратно
        if is_p1:
            state['p1_hp']   = tmp_state['player_hp']
            state['p2_hp']   = tmp_state['dealer_hp']
            state['p2_skip'] = tmp_state.get('dealer_skip', False)
        else:
            state['p2_hp']   = tmp_state['player_hp']
            state['p1_hp']   = tmp_state['dealer_hp']
            state['p1_skip'] = tmp_state.get('dealer_skip', False)
        state['chamber']     = tmp_state['chamber']
        state['chamber_pos'] = tmp_state['chamber_pos']
        state['shots_fired'] = tmp_state['shots_fired']
        state['saw_active']  = tmp_state['saw_active']

        # Определяем публичность предмета
        actor_chat = state['p1_chat'] if is_p1 else state['p2_chat']
        op_chat    = state['p2_chat'] if is_p1 else state['p1_chat']
        aname      = get_username(user_id)

        is_private = item_name in PRIVATE_ITEMS

        bot.send_message(actor_chat, msg, parse_mode='Markdown')
        time.sleep(1.1)
        if is_private:
            bot.send_message(op_chat, f'@{aname} использует {item_name}.')
        else:
            # Публичный — показать короткий результат сопернику
            short_msg = _public_item_msg(item_name, aname, tmp_state, is_p1)
            bot.send_message(op_chat, short_msg)
        time.sleep(1.1)

        # Проверка смерти
        p1_dead = state['p1_hp'] <= 0
        p2_dead = state['p2_hp'] <= 0
        if p1_dead or p2_dead:
            winner_id = state['p2_id'] if p1_dead else state['p1_id']
            save_pvp(get_conn, match_id, state)
            pvp_end_match(bot, state, match_id, winner_id,
                          get_conn, add_money, add_exp, add_rwin)
            return

        save_pvp(get_conn, match_id, state)
        send_battle_to_both(bot, state, match_id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('pvp_steal_'))
    def cb_pvp_steal(call):
        user_id  = call.from_user.id
        match_id, state = load_pvp_by_user(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id)
            return
        item_key  = call.data[len('pvp_steal_'):]
        item_name = cb_to_item(item_key)
        is_p1     = (user_id == state['p1_id'])
        op_key    = 'p2_items' if is_p1 else 'p1_items'
        op_items  = state.get(op_key, [])

        if item_name and item_name in op_items:
            op_items.remove(item_name)
            state[op_key] = op_items

            # Применяем украденный предмет
            tmp_state = {
                'player_hp':     state['p1_hp']    if is_p1 else state['p2_hp'],
                'player_max_hp': state['p1_max_hp'] if is_p1 else state['p2_max_hp'],
                'dealer_hp':     state['p2_hp']    if is_p1 else state['p1_hp'],
                'dealer_max_hp': state['p2_max_hp'] if is_p1 else state['p1_max_hp'],
                'chamber':       state['chamber'],
                'chamber_pos':   state['chamber_pos'],
                'shots_fired':   state['shots_fired'],
                'saw_active':    state['saw_active'],
                'dealer_skip':   state.get('p2_skip' if is_p1 else 'p1_skip', False),
                'player_skip':   False,
            }
            tmp_state, msg = apply_item(tmp_state, item_name, user='player')
            if is_p1:
                state['p1_hp']   = tmp_state['player_hp']
                state['p2_hp']   = tmp_state['dealer_hp']
                state['p2_skip'] = tmp_state.get('dealer_skip', False)
            else:
                state['p2_hp']   = tmp_state['player_hp']
                state['p1_hp']   = tmp_state['dealer_hp']
                state['p1_skip'] = tmp_state.get('dealer_skip', False)
            state['chamber']     = tmp_state['chamber']
            state['chamber_pos'] = tmp_state['chamber_pos']
            state['shots_fired'] = tmp_state['shots_fired']
            state['saw_active']  = tmp_state['saw_active']

            actor_chat = state['p1_chat'] if is_p1 else state['p2_chat']
            op_chat    = state['p2_chat'] if is_p1 else state['p1_chat']
            aname      = get_username(user_id)

            bot.send_message(actor_chat,
                             f'💉 Ты украл {item_name} у соперника!\n\n{msg}',
                             parse_mode='Markdown')
            time.sleep(1.1)
            bot.send_message(op_chat, f'💉 @{aname} украл у тебя {item_name}!')
            time.sleep(1.1)

            p1_dead = state['p1_hp'] <= 0
            p2_dead = state['p2_hp'] <= 0
            if p1_dead or p2_dead:
                winner_id = state['p2_id'] if p1_dead else state['p1_id']
                save_pvp(get_conn, match_id, state)
                pvp_end_match(bot, state, match_id, winner_id,
                              get_conn, add_money, add_exp, add_rwin)
                bot.answer_callback_query(call.id)
                return

        save_pvp(get_conn, match_id, state)
        bot.answer_callback_query(call.id)
        send_battle_to_both(bot, state, match_id)

    # ─── Подбор предметов в начале раунда (PvP) ─────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_pick_item')
    def cb_pvp_pick_item(call):
        user_id  = call.from_user.id
        match_id, state = load_pvp_by_user(get_conn, user_id)
        if not state or state.get('phase') != 'pick_items':
            bot.answer_callback_query(call.id)
            return

        is_p1 = (user_id == state['p1_id'])
        pending_key = 'pending_p1_items' if is_p1 else 'pending_p2_items'
        items_key   = 'p1_items'         if is_p1 else 'p2_items'
        picked_key  = 'p1_items_picked'  if is_p1 else 'p2_items_picked'

        pending = state.get(pending_key, [])
        if not pending:
            bot.answer_callback_query(call.id, 'Предметы закончились')
            return

        item = pending.pop(0)
        state[items_key]  = state.get(items_key, []) + [item]
        state[picked_key] = state.get(picked_key, 0) + 1
        state[pending_key] = pending

        bot.answer_callback_query(call.id)
        actor_chat = state['p1_chat'] if is_p1 else state['p2_chat']
        bot.send_message(actor_chat, f'+ {item}')
        time.sleep(1.1)

        # Оба игрока подобрали — начинаем бой
        if (state.get('p1_items_picked', 0) >= state['items_to_pick'] and
                state.get('p2_items_picked', 0) >= state['items_to_pick']):
            state['phase'] = 'battle'
            save_pvp(get_conn, match_id, state)
            send_battle_to_both(bot, state, match_id)
        else:
            save_pvp(get_conn, match_id, state)
            # Если этот игрок уже набрал, ждём второго
            if state[picked_key] >= state['items_to_pick']:
                bot.send_message(actor_chat,
                                 '✅ Ты набрал предметы. Ожидаем соперника...')
            else:
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton('📦 Взять предмет', callback_data='pvp_pick_item'))
                remain = state['items_to_pick'] - state[picked_key]
                bot.send_message(actor_chat, f'📦 Осталось взять: {remain}', reply_markup=kb)

    # ─── Заглушка нажатия не в свой ход ─────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_noop')
    def cb_pvp_noop(call):
        bot.answer_callback_query(call.id, '⏳ Ожидай хода соперника')


# ═══════════════════════════════════════════════════════════
#  Вспомогательные функции
# ═══════════════════════════════════════════════════════════

def _show_challenge_setup(bot, chat_id, user_id, target_id, target_name,
                          pending_pvp, msg_id=None):
    pending_pvp[user_id] = {
        'step':        'choose_mode',
        'target_id':   target_id,
        'target_name': target_name,
        'chat_id':     chat_id,
    }
    text = (
        f'⚔️ Создание вызова\n\n'
        f'Игрок: @{target_name}\n\n'
        f'Выбери режим:'
    )
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton('🟢 Классический риск', callback_data='pvp_cmode_classic'),
        InlineKeyboardButton('🔴 Тактика дилера',    callback_data='pvp_cmode_tactical'),
        InlineKeyboardButton('🔙 Назад',              callback_data='rlt_pvp_menu'),
    )
    if msg_id:
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)


def _pvp_reload(state):
    """Перезаряжает магазин в PvP, возвращает ход первому игроку раунда."""
    chamber, live, blank = make_chamber()
    state['chamber']      = chamber
    state['chamber_pos']  = 0
    state['live_count']   = live
    state['blank_count']  = blank
    state['shots_fired']  = 0
    state['saw_active']   = False
    state['turn']         = state.get('first_of_round', 'p1')
    state['turn_started_at'] = datetime.now().isoformat()
    state['turn_warned']     = False
    msg = (
        f'🔄 Патроны кончились. Перезарядка.\n\n'
        f'🟢 Холостых: {blank}\n'
        f'🔴 Боевых: {live}\n\n'
        f'🔔 Ход возвращается первому игроку раунда'
    )
    return state, msg


def _public_item_msg(item_name, aname, tmp_state, is_p1):
    """Короткое публичное сообщение для соперника."""
    msgs = {
        '🍺 Пиво':         f'🍺 @{aname} выпил пиво — патрон сброшен.',
        '🚬 Сигареты':     f'🚬 @{aname} закурил — +1 🫀',
        '⛓️ Наручники':   f'⛓️ @{aname} надел наручники — ты пропускаешь ход!',
        '🪚 Пила':         f'🪚 @{aname} пилит ствол — следующий выстрел усилен.',
        '💉 Адреналин':    f'💉 @{aname} использует адреналин.',
        '💊 Лекарства':    f'💊 @{aname} принял лекарства.',
    }
    return msgs.get(item_name, f'@{aname} использует {item_name}.')
