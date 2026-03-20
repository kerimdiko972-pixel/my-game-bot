# ============================================================
#  buckshot_pvp.py — PvP модуль для Спиншот Дуэли
# ============================================================

import random
import time
import json
import threading
import psycopg2
import psycopg2.extras
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from buckshot_handlers import (
    ITEMS_BASIC, ITEMS_TACTICAL,
    make_chamber, hp_for_round,
    hp_to_emoji, fmt_items, apply_item, item_to_cb, cb_to_item,
)

CHALLENGE_EXPIRE_SEC = 120
TURN_WARN_SEC        = 45
TURN_TIMEOUT_SEC     = 75

PRIVATE_ITEMS = {'🔎 Лупа', '📞 Телефон', '📟 Инвертор'}


# ═══════════════════════════════════════════════════════════
#  БД
# ═══════════════════════════════════════════════════════════

def init_pvp_tables(get_conn):
    conn = get_conn()
    c = conn.cursor()
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS roulette_pvp (
            match_id   SERIAL PRIMARY KEY,
            player1_id BIGINT,
            player2_id BIGINT,
            state_json TEXT,
            status     TEXT DEFAULT 'active',
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    conn.commit()
    conn.close()


def save_pvp(get_conn, match_id, state):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        UPDATE roulette_pvp SET state_json=%s, updated_at=NOW()
        WHERE match_id=%s
    ''', (json.dumps(state, ensure_ascii=False), match_id))
    conn.commit()
    conn.close()


def load_pvp_by_user(get_conn, user_id):
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
        VALUES (%s,%s,%s,%s) RETURNING id
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


def _get_private_chat(get_conn, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT private_chat_id FROM users WHERE user_id=%s', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else None


# ═══════════════════════════════════════════════════════════
#  Инициализация состояния
# ═══════════════════════════════════════════════════════════

def init_pvp_state(p1_id, p1_name, p2_id, p2_name,
                   p1_chat, p2_chat, mode, bet):
    chamber, live, blank = make_chamber()
    return {
        'mode':     mode,
        'bet':      bet,
        'p1_id':    p1_id,   'p1_name': p1_name,  'p1_chat': p1_chat,
        'p2_id':    p2_id,   'p2_name': p2_name,  'p2_chat': p2_chat,
        'turn':     'p1',
        'first_of_round': 'p1',
        'phase':    'battle',
        'round':    1,
        'p1_hp':    2, 'p1_max_hp': 2,
        'p2_hp':    2, 'p2_max_hp': 2,
        'chamber':       chamber,
        'chamber_pos':   0,
        'live_count':    live,
        'blank_count':   blank,
        'shots_fired':   0,
        'p1_items':  [], 'p2_items':  [],
        'pending_p1_items': [], 'pending_p2_items': [],
        'items_to_pick':   0,
        'p1_items_picked': 0, 'p2_items_picked': 0,
        'saw_active':    False,
        'p1_skip':       False, 'p2_skip': False,
        'extra_turn_used': False,
        'turn_started_at': datetime.now().isoformat(),
        'turn_warned':     False,
        # Счёт раундов
        'p1_wins': 0,
        'p2_wins': 0,
        'wins_to_win': 3,
    }


def pvp_start_round(state, rnd):
    mode        = state.get('mode', 'classic')
    hp          = hp_for_round(rnd)[0]
    chamber, live, blank = make_chamber()
    items_count = random.randint(1, 4) if rnd > 1 else 0
    item_pool   = ITEMS_TACTICAL if mode == 'tactical' else ITEMS_BASIC
    p1_items    = [random.choice(item_pool) for _ in range(items_count)]
    p2_items    = [random.choice(item_pool) for _ in range(items_count)]
    state.update({
        'round': rnd,
        'p1_hp': hp, 'p1_max_hp': hp,
        'p2_hp': hp, 'p2_max_hp': hp,
        'chamber': chamber, 'chamber_pos': 0,
        'live_count': live, 'blank_count': blank,
        'shots_fired': 0,
        'turn': 'p1', 'first_of_round': 'p1',
        'phase': 'pick_items' if rnd > 1 else 'battle',
        'items_to_pick': items_count,
        'p1_items_picked': 0, 'p2_items_picked': 0,
        'p1_items': [], 'p2_items': [],
        'pending_p1_items': p1_items,
        'pending_p2_items': p2_items,
        'saw_active': False,
        'p1_skip': False, 'p2_skip': False,
        'extra_turn_used': False,
        'turn_started_at': datetime.now().isoformat(),
        'turn_warned': False,
    })
    return state


# ═══════════════════════════════════════════════════════════
#  Форматирование
# ═══════════════════════════════════════════════════════════

def pvp_battle_text(state, viewer_id):
    p1_id   = state['p1_id']
    is_p1   = (viewer_id == p1_id)
    rnd     = state['round']
    shots   = state['shots_fired']

    my_hp   = state['p1_hp'] if is_p1 else state['p2_hp']
    op_hp   = state['p2_hp'] if is_p1 else state['p1_hp']
    my_name = state['p1_name'] if is_p1 else state['p2_name']
    op_name = state['p2_name'] if is_p1 else state['p1_name']
    my_items  = state.get('p1_items', []) if is_p1 else state.get('p2_items', [])
    op_items  = state.get('p2_items', []) if is_p1 else state.get('p1_items', [])

    turn = state['turn']
    is_my_turn = (turn == 'p1' and is_p1) or (turn == 'p2' and not is_p1)
    turn_line  = '🔔 Ход у тебя' if is_my_turn else f'🔔 Ход {op_name}'
    p1_wins = state.get('p1_wins', 0)
    p2_wins = state.get('p2_wins', 0)
    my_wins = p1_wins if is_p1 else p2_wins
    op_wins = p2_wins if is_p1 else p1_wins
    wins_to_win = state.get('wins_to_win', 3)
    score_line = f'🏅 {my_name}: {my_wins}  vs  {op_name}: {op_wins}  (до {wins_to_win})'

    ammo_block = ''
    if shots == 0:
        ammo_block = (f'🟢 Холостых: {state["blank_count"]}\n'
                      f'🔴 Боевых: {state["live_count"]}\n')

    effects = []
    if state.get('saw_active'):
        effects.append('🪚 Следующий выстрел усилен')
    op_skipped = (state.get('p2_skip') and is_p1) or (state.get('p1_skip') and not is_p1)
    if op_skipped:
        effects.append(f'⛓️ {op_name} скован')
    eff_line = '\n'.join(effects)

    items_block = ''
    if rnd > 1:
        items_block = (
            f'\nПредметы {op_name}: {fmt_items(op_items)}'
            f'\nТвои предметы: {fmt_items(my_items)}\n'
        )

    text = (
        f'● — – - Раунд {rnd} - – — ●\n\n'
        f'{score_line}\n\n'
        f'{turn_line}\n\n'
        f'{my_name}: {hp_to_emoji(my_hp, "🫀")}\n'
        f'{op_name}: {hp_to_emoji(op_hp, "🫀")}\n\n'
        f'• ——————— •\n'
        f'{ammo_block}'
        f'• ——————— •'
        f'{items_block}'
    )
    if eff_line:
        text += f'\n\n🔹 {eff_line}'
    return text


def pvp_battle_keyboard(state, viewer_id):
    p1_id      = state['p1_id']
    is_p1      = (viewer_id == p1_id)
    turn       = state['turn']
    is_my_turn = (turn == 'p1' and is_p1) or (turn == 'p2' and not is_p1)
    phase      = state.get('phase', 'battle')
    kb         = InlineKeyboardMarkup(row_width=2)

    # Фаза подбора предметов
    if phase == 'pick_items':
        picked_key = 'p1_items_picked' if is_p1 else 'p2_items_picked'
        picked     = state.get(picked_key, 0)
        to_pick    = state.get('items_to_pick', 0)
        if picked < to_pick:
            kb.add(InlineKeyboardButton('📦 Взять предмет', callback_data='pvp_pick_item'))
        else:
            kb.add(InlineKeyboardButton('⏳ Ожидаем соперника...', callback_data='pvp_noop'))
        return kb

    if not is_my_turn:
        kb.add(InlineKeyboardButton('⏳ Ход соперника...', callback_data='pvp_noop'))
        return kb

    if phase == 'gun_drawn':
        kb.add(
            InlineKeyboardButton('🎯 В соперника', callback_data='pvp_shoot_op'),
            InlineKeyboardButton('🎭 В себя',      callback_data='pvp_shoot_self'),
        )
        return kb

    # Обычный ход
    kb.add(InlineKeyboardButton('🔫 Взять ружьё', callback_data='pvp_take_gun'))
    my_items = state.get('p1_items', []) if is_p1 else state.get('p2_items', [])
    for item in my_items:
        kb.add(InlineKeyboardButton(item, callback_data=f'pvp_use_{item_to_cb(item)}'))
    return kb


def send_battle_to_both(bot, state, match_id):
    for uid, chat in [
        (state['p1_id'], state['p1_chat']),
        (state['p2_id'], state['p2_chat']),
    ]:
        if not chat:
            print(f'[PvP] send_battle_to_both: chat is None for uid={uid}')
            continue
        text = pvp_battle_text(state, uid)
        kb   = pvp_battle_keyboard(state, uid)
        try:
            bot.send_message(chat, text, reply_markup=kb)
        except Exception as e:
            print(f'[PvP] send_battle_to_both error uid={uid} chat={chat}: {e}')
        time.sleep(0.4)


# ═══════════════════════════════════════════════════════════
#  Выстрел в PvP
# ═══════════════════════════════════════════════════════════

def pvp_fire(state, actor_id, target):
    is_p1 = (actor_id == state['p1_id'])
    fire_target = ('p1' if is_p1 else 'p2') if target == 'self' \
                  else ('p2' if is_p1 else 'p1')
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
    state['turn'] = 'p2' if state['turn'] == 'p1' else 'p1'
    state['turn_started_at'] = datetime.now().isoformat()
    state['turn_warned']     = False
    state['extra_turn_used'] = False
    return state


def get_actor_id_from_turn(state):
    return state['p1_id'] if state['turn'] == 'p1' else state['p2_id']


def pvp_reload(state):
    chamber, live, blank = make_chamber()
    state.update({
        'chamber': chamber, 'chamber_pos': 0,
        'live_count': live, 'blank_count': blank,
        'shots_fired': 0, 'saw_active': False,
        'turn': state.get('first_of_round', 'p1'),
        'turn_started_at': datetime.now().isoformat(),
        'turn_warned': False,
    })
    return state, (
        f'🔄 Патроны кончились. Перезарядка.\n\n'
        f'🟢 Холостых: {blank}\n🔴 Боевых: {live}\n\n'
        f'🔔 Ход возвращается первому игроку раунда'
    )


# ═══════════════════════════════════════════════════════════
#  Завершение матча
# ═══════════════════════════════════════════════════════════

def pvp_end_match(bot, state, match_id, winner_id,
                  get_conn, add_money, add_exp, add_rwin):
    p1_id   = state['p1_id']
    p2_id   = state['p2_id']
    p1_chat = state['p1_chat']
    p2_chat = state['p2_chat']
    bet     = state['bet']
    rnd     = state['round']

    winner_chat = p1_chat if winner_id == p1_id else p2_chat
    loser_chat  = p2_chat if winner_id == p1_id else p1_chat
    winnings    = bet * 2
    exp_gain    = 200 + rnd * 50

    add_money(winner_id, winnings)
    add_exp(winner_id, exp_gain)
    add_rwin(get_conn, winner_id)
    close_pvp(get_conn, match_id)

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton('👤 Игра с игроком', callback_data='rlt_pvp_menu'),
        InlineKeyboardButton('👺 Игра с дилером', callback_data='rlt_dealer'),
        InlineKeyboardButton('🏆 Рекорды',         callback_data='rlt_leaderboard'),
    )
    if winner_chat:
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
    if loser_chat:
        try:
            bot.send_message(
                loser_chat,
                f'💀 Ты проиграл...\n\n💵 Потеря ставки: {bet:,}',
                reply_markup=kb
            )
        except Exception as e:
            print(f'[PvP] loser notify error: {e}')


def pvp_handle_round_end(bot, state, match_id, round_winner_id,
                          get_conn, add_money, add_exp, add_rwin):
    """Обрабатывает конец раунда: +1 балл победителю, старт нового или конец матча."""
    p1_id = state['p1_id']
    p2_id = state['p2_id']
    is_p1_winner = (round_winner_id == p1_id)

    if is_p1_winner:
        state['p1_wins'] += 1
    else:
        state['p2_wins'] += 1

    p1_wins     = state['p1_wins']
    p2_wins     = state['p2_wins']
    wins_to_win = state.get('wins_to_win', 3)
    p1_name     = state['p1_name']
    p2_name     = state['p2_name']
    p1_chat     = state['p1_chat']
    p2_chat     = state['p2_chat']
    rnd         = state['round']

    winner_name = p1_name if is_p1_winner else p2_name
    loser_name  = p2_name if is_p1_winner else p1_name

    round_msg = (
        f'🎉 Раунд {rnd} завершён!\n\n'
        f'Победил: {winner_name}\n\n'
        f'🏅 Счёт: {p1_name} {p1_wins} — {p2_wins} {p2_name}'
    )
    safe_send_raw = lambda chat, text: _safe_send_static(bot, chat, text)
    safe_send_raw(p1_chat, round_msg)
    time.sleep(0.5)
    safe_send_raw(p2_chat, round_msg)
    time.sleep(1.1)

    # Кто-то набрал нужное количество побед — конец матча
    if p1_wins >= wins_to_win or p2_wins >= wins_to_win:
        match_winner_id = p1_id if p1_wins >= wins_to_win else p2_id
        save_pvp(get_conn, match_id, state)
        pvp_end_match(bot, state, match_id, match_winner_id,
                      get_conn, add_money, add_exp, add_rwin)
        return

    # Иначе — следующий раунд
    next_rnd = rnd + 1
    state = pvp_start_round(state, next_rnd)
    save_pvp(get_conn, match_id, state)

    # Сообщение о новом раунде
    new_rnd_msg = (
        f'⚔️ Раунд {next_rnd} начинается!\n\n'
        f'🏅 Счёт: {p1_name} {state["p1_wins"]} — {state["p2_wins"]} {p2_name}'
    )
    safe_send_raw(p1_chat, new_rnd_msg)
    time.sleep(0.5)
    safe_send_raw(p2_chat, new_rnd_msg)
    time.sleep(1.1)

    # Если раунд > 1 — отправляем сообщение о подборе предметов, иначе сразу бой
    if state['phase'] == 'pick_items':
        items_n = state.get('items_to_pick', 0)
        for uid, chat in [(p1_id, p1_chat), (p2_id, p2_chat)]:
            if not chat:
                continue
            text = pvp_battle_text(state, uid)
            kb   = pvp_battle_keyboard(state, uid)
            try:
                bot.send_message(chat, text, reply_markup=kb)
            except Exception as e:
                print(f'[PvP] new round send error uid={uid}: {e}')
            time.sleep(0.4)
    else:
        send_battle_to_both(bot, state, match_id)


def _safe_send_static(bot, chat_id, text, **kwargs):
    if not chat_id:
        return
    try:
        bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        print(f'[PvP] _safe_send_static error chat={chat_id}: {e}')


def pvp_forfeit(bot, state, match_id, quitter_id,
                get_conn, add_money, add_exp, add_rwin):
    p1_id     = state['p1_id']
    winner_id = state['p2_id'] if quitter_id == p1_id else p1_id
    winner_chat = state['p1_chat'] if winner_id == p1_id else state['p2_chat']
    pvp_end_match(bot, state, match_id, winner_id,
                  get_conn, add_money, add_exp, add_rwin)
    if winner_chat:
        try:
            bot.send_message(winner_chat, '🏳️ Противник покинул матч. Победа твоя!')
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
#  Таймеры
# ═══════════════════════════════════════════════════════════

def start_turn_timer(bot, get_conn, add_money, add_exp, add_rwin):
    def loop():
        while True:
            try:
                conn = get_conn()
                c = conn.cursor()
                c.execute("SELECT match_id, state_json FROM roulette_pvp WHERE status='active'")
                rows = c.fetchall()
                conn.close()
                for match_id, state_json in rows:
                    try:
                        state   = json.loads(state_json)
                        ts_str  = state.get('turn_started_at')
                        if not ts_str:
                            continue
                        elapsed = (datetime.now() - datetime.fromisoformat(ts_str)).total_seconds()
                        actor_id   = get_actor_id_from_turn(state)
                        actor_chat = state['p1_chat'] if actor_id == state['p1_id'] else state['p2_chat']
                        if elapsed >= TURN_TIMEOUT_SEC:
                            pvp_forfeit(bot, state, match_id, actor_id,
                                        get_conn, add_money, add_exp, add_rwin)
                        elif elapsed >= TURN_WARN_SEC and not state.get('turn_warned'):
                            if actor_chat:
                                try:
                                    bot.send_message(
                                        actor_chat,
                                        '⚠️ Твой ход! Осталось ~30 секунд, иначе поражение.'
                                    )
                                except Exception:
                                    pass
                            state['turn_warned'] = True
                            save_pvp(get_conn, match_id, state)
                    except Exception as e:
                        print(f'[PvP timer match {match_id}] {e}')
            except Exception as e:
                print(f'[PvP timer] {e}')
            time.sleep(10)
    threading.Thread(target=loop, daemon=True).start()


def start_challenge_timer(bot, get_conn):
    def loop():
        while True:
            try:
                conn = get_conn()
                c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                c.execute(f'''
                    SELECT * FROM roulette_challenges
                    WHERE status='pending'
                    AND created_at < NOW() - INTERVAL '{CHALLENGE_EXPIRE_SEC} seconds'
                ''')
                expired = c.fetchall()
                conn.close()
                for ch in expired:
                    update_challenge_status(get_conn, ch['id'], 'expired')
                    from_chat = _get_private_chat(get_conn, ch['from_user_id'])
                    if from_chat:
                        try:
                            bot.send_message(from_chat, '⏳ Вызов истёк — игрок не ответил.')
                        except Exception:
                            pass
            except Exception as e:
                print(f'[Challenge timer] {e}')
            time.sleep(15)
    threading.Thread(target=loop, daemon=True).start()


# ═══════════════════════════════════════════════════════════
#  Регистрация хэндлеров
# ═══════════════════════════════════════════════════════════

def register_pvp_handlers(bot, get_conn, get_user,
                           add_money, spend_money, add_exp, add_rwin):

    pending_pvp = {}

    def safe_edit(chat_id, msg_id, text, kb=None):
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, text, reply_markup=kb)

    def safe_send(chat_id, text, **kwargs):
        if not chat_id:
            print(f'[PvP] safe_send: chat_id is None, text={text[:50]}')
            return
        try:
            bot.send_message(chat_id, text, **kwargs)
        except Exception as e:
            print(f'[PvP] safe_send error chat={chat_id}: {e}')

    def get_username(user_id):
        user = get_user(user_id)
        return (user[1] or f'id{user_id}') if user else f'id{user_id}'

    def back_kb():
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton('🔙 В меню', callback_data='rlt_main'))
        return kb

    # ─── Меню PvP ────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'rlt_pvp_menu')
    def cb_pvp_menu(call):
        text = '👤 ИГРА С ИГРОКОМ\n\nВыбери способ дуэли:'
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton('📨 Вызвать игрока',     callback_data='pvp_invite_list'),
            InlineKeyboardButton('🔎 Найти по @username', callback_data='pvp_invite_username'),
            InlineKeyboardButton('📜 Мои вызовы',         callback_data='pvp_my_challenges'),
            InlineKeyboardButton('🔙 Назад',               callback_data='rlt_main'),
        )
        safe_edit(call.message.chat.id, call.message.message_id, text, kb)
        bot.answer_callback_query(call.id)

    # ─── Список игроков ──────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_invite_list')
    def cb_pvp_invite_list(call):
        players = get_recent_players(get_conn, call.from_user.id)
        if not players:
            bot.answer_callback_query(call.id, 'Нет доступных игроков', show_alert=True)
            return
        kb = InlineKeyboardMarkup(row_width=1)
        for uid, uname in players:
            kb.add(InlineKeyboardButton(
                f'👤 {uname or f"id{uid}"}',
                callback_data=f'pvp_select_{uid}'
            ))
        kb.add(InlineKeyboardButton('🔙 Назад', callback_data='rlt_pvp_menu'))
        safe_edit(call.message.chat.id, call.message.message_id,
                  'Выбери игрока для дуэли:', kb)
        bot.answer_callback_query(call.id)

    # ─── Поиск по @username ───────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_invite_username')
    def cb_pvp_invite_username(call):
        user_id = call.from_user.id
        pending_pvp[user_id] = {'step': 'enter_username'}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton('🔙 Назад', callback_data='rlt_pvp_menu'))
        safe_edit(call.message.chat.id, call.message.message_id,
                  '🔎 Введи @username игрока:', kb)
        bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda m: m.from_user.id in pending_pvp
                          and pending_pvp[m.from_user.id].get('step') == 'enter_username')
    def handle_pvp_username(message):
        user_id = message.from_user.id
        uname   = message.text.strip().lstrip('@')
        conn = get_conn()
        c = conn.cursor()
        c.execute('SELECT user_id, username, private_chat_id FROM users WHERE username=%s', (uname,))
        row = c.fetchone()
        conn.close()
        if not row or not row[2]:
            bot.send_message(message.chat.id,
                             f'❌ Игрок @{uname} не найден или не запускал бота в личку.')
            return
        if row[0] == user_id:
            bot.send_message(message.chat.id, '❌ Нельзя вызвать самого себя!')
            return
        pending_pvp.pop(user_id, None)
        _show_challenge_setup(bot, message.chat.id, user_id,
                              row[0], uname, pending_pvp)

    # ─── Выбор игрока из списка ───────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('pvp_select_'))
    def cb_pvp_select(call):
        user_id    = call.from_user.id
        target_id  = int(call.data.split('_')[-1])
        target_name = get_username(target_id)
        bot.answer_callback_query(call.id)
        _show_challenge_setup(bot, call.message.chat.id, user_id,
                              target_id, target_name, pending_pvp,
                              msg_id=call.message.message_id)

    # ─── Выбор режима для вызова ──────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('pvp_cmode_'))
    def cb_pvp_cmode(call):
        user_id = call.from_user.id
        info    = pending_pvp.get(user_id, {})
        if not info:
            bot.answer_callback_query(call.id)
            return
        mode      = call.data[len('pvp_cmode_'):]
        mode_name = '🟢 Классический риск' if mode == 'classic' else '🔴 Тактика дилера'
        info.update({'mode': mode, 'mode_name': mode_name, 'step': 'enter_bet'})
        user  = get_user(user_id)
        money = user[2] if user else 0
        text = (
            f'⚔️ Создание вызова\n\n'
            f'Игрок: @{info["target_name"]}\n'
            f'Режим: {mode_name}\n\n'
            f'Денег: 💵 {money:,}\n\n'
            f'💰 Введи ставку (мин. 500):'
        )
        safe_edit(call.message.chat.id, call.message.message_id, text,
                  InlineKeyboardMarkup().add(
                      InlineKeyboardButton('🔙 Назад', callback_data='rlt_pvp_menu')))
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
            bot.send_message(message.chat.id, f'❌ Недостаточно средств! У тебя 💵 {money:,}')
            return
        info.update({'bet': bet, 'step': 'confirm'})
        text = (
            f'⚔️ Создание вызова\n\n'
            f'Игрок: @{info["target_name"]}\n'
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
        target_chat = _get_private_chat(get_conn, target_id)
        if not target_chat:
            bot.answer_callback_query(
                call.id, '❌ Игрок не запускал бота в личку — вызов невозможен.', show_alert=True)
            return
        spend_money(user_id, bet)
        cid = save_challenge(get_conn, user_id, target_id, mode, bet)
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton('✅ Принять',   callback_data=f'pvp_accept_{cid}'),
            InlineKeyboardButton('❌ Отклонить', callback_data=f'pvp_decline_{cid}'),
        )
        safe_send(target_chat,
                  f'⚔️ Тебя вызвали на дуэль!\n\n'
                  f'Противник: @{from_name}\n'
                  f'Режим: {mode_name}\n'
                  f'Ставка: {bet:,}\n\n'
                  f'Принять вызов?',
                  reply_markup=kb)
        safe_edit(call.message.chat.id, call.message.message_id,
                  f'✅ Вызов отправлен @{target_name}!\nОжидаем ответа...', back_kb())
        bot.answer_callback_query(call.id)

    # ─── Принять / отклонить ─────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('pvp_accept_'))
    def cb_pvp_accept(call):
        user_id      = call.from_user.id
        challenge_id = int(call.data.split('_')[-1])
        ch           = get_challenge(get_conn, challenge_id)
        if not ch or ch['status'] != 'pending':
            bot.answer_callback_query(call.id, '❌ Вызов недействителен', show_alert=True)
            return
        if ch['to_user_id'] != user_id:
            bot.answer_callback_query(call.id, '❌ Это не твой вызов', show_alert=True)
            return
        bet  = ch['bet']
        user = get_user(user_id)
        if (user[2] if user else 0) < bet:
            bot.answer_callback_query(call.id, f'❌ Нужно {bet:,}', show_alert=True)
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

        if not p1_chat:
            # p1 не имеет приватного чата — возвращаем деньги p2
            add_money(user_id, bet)
            update_challenge_status(get_conn, challenge_id, 'cancelled')
            bot.answer_callback_query(call.id, '❌ Ошибка: инициатор недоступен.', show_alert=True)
            return

        state    = init_pvp_state(p1_id, p1_name, p2_id, p2_name,
                                  p1_chat, p2_chat, mode, bet)
        match_id = create_pvp_match(get_conn, p1_id, p2_id, state)
        state['match_id'] = match_id
        save_pvp(get_conn, match_id, state)

        start_text = (
            f'⚔️ Дуэль началась!\n\n'
            f'Противник: @{{}}\n'
            f'Ставка: {bet:,}\n'
            f'Режим: {mode_name}\n\n'
            f'Готовься к первому раунду...'
        )
        time.sleep(0.5)
        safe_send(p1_chat, start_text.format(p2_name))
        time.sleep(0.5)
        safe_send(p2_chat, start_text.format(p1_name))
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
        add_money(ch['from_user_id'], ch['bet'])
        from_chat = _get_private_chat(get_conn, ch['from_user_id'])
        safe_send(from_chat,
                  f'❌ @{get_username(user_id)} отклонил вызов. Ставка возвращена.')
        safe_edit(call.message.chat.id, call.message.message_id,
                  '❌ Ты отклонил вызов.', back_kb())
        bot.answer_callback_query(call.id)

    # ─── Мои вызовы ──────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_my_challenges')
    def cb_pvp_my_challenges(call):
        challenges = get_pending_challenges(get_conn, call.from_user.id)
        if not challenges:
            bot.answer_callback_query(call.id, 'Нет входящих вызовов', show_alert=True)
            return
        text = '📜 Входящие вызовы:\n\n'
        kb   = InlineKeyboardMarkup(row_width=2)
        for ch in challenges:
            mode_n = 'Классика' if ch['mode'] == 'classic' else 'Тактика'
            text += f'⚔️ @{ch["from_username"]} | {mode_n} | {ch["bet"]:,} 💵\n'
            kb.add(
                InlineKeyboardButton(f'✅ @{ch["from_username"]}', callback_data=f'pvp_accept_{ch["id"]}'),
                InlineKeyboardButton('❌', callback_data=f'pvp_decline_{ch["id"]}'),
            )
        kb.add(InlineKeyboardButton('🔙 Назад', callback_data='rlt_pvp_menu'))
        safe_edit(call.message.chat.id, call.message.message_id, text, kb)
        bot.answer_callback_query(call.id)

    # ─── Взять ружьё ─────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_take_gun')
    def cb_pvp_take_gun(call):
        user_id = call.from_user.id
        match_id, state = load_pvp_by_user(get_conn, user_id)
        if not state:
            bot.answer_callback_query(call.id, '❌ Матч не найден')
            return
        if get_actor_id_from_turn(state) != user_id:
            bot.answer_callback_query(call.id, '⏳ Сейчас не твой ход!')
            return
        if state.get('phase') == 'gun_drawn':
            bot.answer_callback_query(call.id, 'Ружьё уже взято!')
            return
        state['phase'] = 'gun_drawn'
        save_pvp(get_conn, match_id, state)
        bot.answer_callback_query(call.id)

        actor_chat = state['p1_chat'] if user_id == state['p1_id'] else state['p2_chat']
        text = pvp_battle_text(state, user_id) + '\n\n🔫 Ты взял ружьё, выбери цель:'
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton('🎯 В соперника', callback_data='pvp_shoot_op'),
            InlineKeyboardButton('🎭 В себя',      callback_data='pvp_shoot_self'),
        )
        safe_send(actor_chat, text, reply_markup=kb)

    # ─── Выстрелы ────────────────────────────────────────────

    def process_pvp_shot(call, target):
        user_id = call.from_user.id
        try:
            match_id, state = load_pvp_by_user(get_conn, user_id)
            if not state:
                bot.answer_callback_query(call.id, '❌ Матч не найден')
                return
            if get_actor_id_from_turn(state) != user_id:
                bot.answer_callback_query(call.id, '⏳ Сейчас не твой ход!')
                return
            if state.get('phase') != 'gun_drawn':
                bot.answer_callback_query(call.id, '🔫 Сначала возьми ружьё!')
                return

            bot.answer_callback_query(call.id)
            state['phase'] = 'battle'

            is_p1       = (user_id == state['p1_id'])
            my_name     = state['p1_name'] if is_p1 else state['p2_name']
            op_name     = state['p2_name'] if is_p1 else state['p1_name']
            actor_chat  = state['p1_chat'] if is_p1 else state['p2_chat']
            op_chat     = state['p2_chat'] if is_p1 else state['p1_chat']
            target_word = 'в себя' if target == 'self' else f'в {op_name}'

            safe_send(actor_chat, f'_Ты целишься {target_word}. . ._', parse_mode='Markdown')
            safe_send(op_chat,    f'_{my_name} целится {target_word}. . ._', parse_mode='Markdown')
            time.sleep(1.1)

            state, is_live, damage = pvp_fire(state, user_id, target)

            if is_live:
                dmg_who   = 'тебя' if target == 'self' else op_name
                priv_txt  = f'💥 Боевой! -{damage} 🫀 ({dmg_who})'
                pub_txt   = f'💥 Боевой! {my_name} нанёс -{damage} 🫀 ({dmg_who})'
            else:
                priv_txt = '💨 Холостой...'
                pub_txt  = f'💨 Холостой... ({my_name})'

            safe_send(actor_chat, priv_txt)
            time.sleep(0.4)
            safe_send(op_chat, pub_txt)
            time.sleep(1.1)

            # Конец раунда (смерть)
            p1_dead = state['p1_hp'] <= 0
            p2_dead = state['p2_hp'] <= 0
            if p1_dead or p2_dead:
                round_winner_id = state['p2_id'] if p1_dead else state['p1_id']
                save_pvp(get_conn, match_id, state)
                pvp_handle_round_end(bot, state, match_id, round_winner_id,
                                     get_conn, add_money, add_exp, add_rwin)
                return

            # Перезарядка
            if state['chamber_pos'] >= len(state['chamber']):
                state, reload_msg = pvp_reload(state)
                safe_send(actor_chat, reload_msg)
                time.sleep(0.4)
                safe_send(op_chat, reload_msg)
                time.sleep(1.1)
                save_pvp(get_conn, match_id, state)
                send_battle_to_both(bot, state, match_id)
                return

            # Доп. ход при холостом в себя
            if target == 'self' and not is_live and not state.get('extra_turn_used'):
                state['extra_turn_used'] = True
                safe_send(actor_chat, '🔔 Холостой в себя — ты получаешь дополнительный ход!')
                time.sleep(0.4)
                safe_send(op_chat, f'🔔 {my_name} получает дополнительный ход!')
                time.sleep(1.1)
                save_pvp(get_conn, match_id, state)
                send_battle_to_both(bot, state, match_id)
                return

            # Переключение хода
            state = switch_turn(state)
            next_id  = get_actor_id_from_turn(state)
            next_key = 'p1' if next_id == state['p1_id'] else 'p2'
            if state.get(f'{next_key}_skip'):
                state[f'{next_key}_skip'] = False
                skip_chat  = state['p1_chat'] if next_id == state['p1_id'] else state['p2_chat']
                other_chat = state['p2_chat'] if next_id == state['p1_id'] else state['p1_chat']
                skip_name  = state['p1_name'] if next_id == state['p1_id'] else state['p2_name']
                safe_send(skip_chat,  '⛓️ Ты скован и пропускаешь ход!')
                safe_send(other_chat, f'⛓️ {skip_name} скован и пропускает ход!')
                time.sleep(1.1)
                state = switch_turn(state)

            save_pvp(get_conn, match_id, state)
            send_battle_to_both(bot, state, match_id)

        except Exception as e:
            print(f'[PvP] process_pvp_shot error user={user_id} target={target}: {e}')
            import traceback
            traceback.print_exc()

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_shoot_op')
    def cb_pvp_shoot_op(call):
        process_pvp_shot(call, 'opponent')

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_shoot_self')
    def cb_pvp_shoot_self(call):
        process_pvp_shot(call, 'self')

    # ─── Предметы ────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith('pvp_use_'))
    def cb_pvp_use_item(call):
        user_id = call.from_user.id
        try:
            match_id, state = load_pvp_by_user(get_conn, user_id)
            if not state:
                bot.answer_callback_query(call.id, '❌ Матч не найден')
                return
            if get_actor_id_from_turn(state) != user_id:
                bot.answer_callback_query(call.id, '⏳ Сейчас не твой ход!')
                return
            if state.get('phase') == 'gun_drawn':
                bot.answer_callback_query(call.id, '❌ После взятия ружья предметы нельзя использовать!')
                return

            item_key  = call.data[len('pvp_use_'):]
            item_name = cb_to_item(item_key)
            if not item_name:
                bot.answer_callback_query(call.id, 'Неизвестный предмет')
                return

            is_p1     = (user_id == state['p1_id'])
            items_key = 'p1_items' if is_p1 else 'p2_items'
            my_items  = list(state.get(items_key, []))

            if item_name not in my_items:
                bot.answer_callback_query(call.id, 'У тебя нет этого предмета!')
                return

            bot.answer_callback_query(call.id)

            actor_chat = state['p1_chat'] if is_p1 else state['p2_chat']
            op_chat    = state['p2_chat'] if is_p1 else state['p1_chat']
            my_name    = state['p1_name'] if is_p1 else state['p2_name']

            # Адреналин
            if item_name == '💉 Адреналин':
                op_key   = 'p2_items' if is_p1 else 'p1_items'
                op_items = list(state.get(op_key, []))
                stealable = [i for i in op_items if i != '💉 Адреналин']
                if not stealable:
                    safe_send(actor_chat, '💉 У соперника нет предметов для кражи!')
                    return
                my_items.remove(item_name)
                state[items_key] = my_items
                save_pvp(get_conn, match_id, state)
                kb = InlineKeyboardMarkup(row_width=2)
                for itm in stealable:
                    kb.add(InlineKeyboardButton(itm, callback_data=f'pvp_steal_{item_to_cb(itm)}'))
                safe_send(actor_chat,
                          '💉 Адреналин\n_Ты срываешься в рывок._\n\nВыбери предмет у соперника:',
                          parse_mode='Markdown', reply_markup=kb)
                safe_send(op_chat, f'💉 {my_name} использует Адреналин...')
                return

            # Применяем предмет
            my_items.remove(item_name)
            state[items_key] = my_items

            tmp = _state_to_tmp(state, is_p1)
            tmp, msg = apply_item(tmp, item_name, user='player')
            _tmp_to_state(tmp, state, is_p1)

            is_private = item_name in PRIVATE_ITEMS
            safe_send(actor_chat, msg, parse_mode='Markdown')
            time.sleep(1.1)
            if is_private:
                safe_send(op_chat, f'{my_name} использует {item_name}.')
            else:
                safe_send(op_chat, _public_msg(item_name, my_name, tmp))
            time.sleep(1.1)

            p1_dead = state['p1_hp'] <= 0
            p2_dead = state['p2_hp'] <= 0
            if p1_dead or p2_dead:
                round_winner_id = state['p2_id'] if p1_dead else state['p1_id']
                save_pvp(get_conn, match_id, state)
                pvp_handle_round_end(bot, state, match_id, round_winner_id,
                                     get_conn, add_money, add_exp, add_rwin)
                return

            save_pvp(get_conn, match_id, state)
            send_battle_to_both(bot, state, match_id)

        except Exception as e:
            print(f'[PvP] use_item error user={user_id}: {e}')
            import traceback
            traceback.print_exc()

    @bot.callback_query_handler(func=lambda c: c.data.startswith('pvp_steal_'))
    def cb_pvp_steal(call):
        user_id = call.from_user.id
        try:
            match_id, state = load_pvp_by_user(get_conn, user_id)
            if not state:
                bot.answer_callback_query(call.id)
                return
            item_key  = call.data[len('pvp_steal_'):]
            item_name = cb_to_item(item_key)
            is_p1     = (user_id == state['p1_id'])
            op_key    = 'p2_items' if is_p1 else 'p1_items'
            op_items  = list(state.get(op_key, []))

            if not item_name or item_name not in op_items:
                bot.answer_callback_query(call.id, 'Предмет уже не у соперника')
                return

            bot.answer_callback_query(call.id)
            op_items.remove(item_name)
            state[op_key] = op_items

            actor_chat = state['p1_chat'] if is_p1 else state['p2_chat']
            op_chat    = state['p2_chat'] if is_p1 else state['p1_chat']
            my_name    = state['p1_name'] if is_p1 else state['p2_name']

            tmp = _state_to_tmp(state, is_p1)
            tmp, msg = apply_item(tmp, item_name, user='player')
            _tmp_to_state(tmp, state, is_p1)

            safe_send(actor_chat, f'💉 Ты украл {item_name}!\n\n{msg}', parse_mode='Markdown')
            time.sleep(1.1)
            safe_send(op_chat, f'💉 {my_name} украл у тебя {item_name}!')
            time.sleep(1.1)

            p1_dead = state['p1_hp'] <= 0
            p2_dead = state['p2_hp'] <= 0
            if p1_dead or p2_dead:
                round_winner_id = state['p2_id'] if p1_dead else state['p1_id']
                save_pvp(get_conn, match_id, state)
                pvp_handle_round_end(bot, state, match_id, round_winner_id,
                                     get_conn, add_money, add_exp, add_rwin)
                return

            save_pvp(get_conn, match_id, state)
            send_battle_to_both(bot, state, match_id)
        except Exception as e:
            print(f'[PvP] steal error user={user_id}: {e}')

    # ─── Подбор предметов ────────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_pick_item')
    def cb_pvp_pick_item(call):
        user_id = call.from_user.id
        try:
            match_id, state = load_pvp_by_user(get_conn, user_id)
            if not state or state.get('phase') != 'pick_items':
                bot.answer_callback_query(call.id)
                return

            is_p1       = (user_id == state['p1_id'])
            pending_key = 'pending_p1_items' if is_p1 else 'pending_p2_items'
            items_key   = 'p1_items'         if is_p1 else 'p2_items'
            picked_key  = 'p1_items_picked'  if is_p1 else 'p2_items_picked'
            actor_chat  = state['p1_chat'] if is_p1 else state['p2_chat']

            pending = list(state.get(pending_key, []))
            if not pending:
                bot.answer_callback_query(call.id, 'Предметы закончились')
                return

            item = pending.pop(0)
            state[items_key]   = state.get(items_key, []) + [item]
            state[picked_key]  = state.get(picked_key, 0) + 1
            state[pending_key] = pending

            bot.answer_callback_query(call.id)
            safe_send(actor_chat, f'+ {item}')
            time.sleep(1.1)

            to_pick = state['items_to_pick']
            p1_done = state.get('p1_items_picked', 0) >= to_pick
            p2_done = state.get('p2_items_picked', 0) >= to_pick

            if p1_done and p2_done:
                state['phase'] = 'battle'
                save_pvp(get_conn, match_id, state)
                send_battle_to_both(bot, state, match_id)
            else:
                save_pvp(get_conn, match_id, state)
                if state[picked_key] >= to_pick:
                    safe_send(actor_chat, '✅ Ты взял все предметы. Ожидаем соперника...')
                else:
                    remain = to_pick - state[picked_key]
                    kb = InlineKeyboardMarkup()
                    kb.add(InlineKeyboardButton('📦 Взять предмет', callback_data='pvp_pick_item'))
                    safe_send(actor_chat, f'📦 Осталось взять: {remain}', reply_markup=kb)
        except Exception as e:
            print(f'[PvP] pick_item error user={user_id}: {e}')

    @bot.callback_query_handler(func=lambda c: c.data == 'pvp_noop')
    def cb_pvp_noop(call):
        bot.answer_callback_query(call.id, '⏳ Ожидай хода соперника')


# ═══════════════════════════════════════════════════════════
#  Вспомогательные
# ═══════════════════════════════════════════════════════════

def _show_challenge_setup(bot, chat_id, user_id, target_id,
                           target_name, pending_pvp, msg_id=None):
    pending_pvp[user_id] = {
        'step': 'choose_mode',
        'target_id': target_id,
        'target_name': target_name,
    }
    text = f'⚔️ Создание вызова\n\nИгрок: @{target_name}\n\nВыбери режим:'
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


def _state_to_tmp(state, is_p1):
    """Конвертирует PvP-state в формат apply_item (player = текущий игрок)."""
    return {
        'player_hp':     state['p1_hp']    if is_p1 else state['p2_hp'],
        'player_max_hp': state['p1_max_hp'] if is_p1 else state['p2_max_hp'],
        'dealer_hp':     state['p2_hp']    if is_p1 else state['p1_hp'],
        'dealer_max_hp': state['p2_max_hp'] if is_p1 else state['p1_max_hp'],
        'chamber':       list(state['chamber']),
        'chamber_pos':   state['chamber_pos'],
        'shots_fired':   state['shots_fired'],
        'saw_active':    state.get('saw_active', False),
        'dealer_skip':   state.get('p2_skip' if is_p1 else 'p1_skip', False),
        'player_skip':   False,
    }


def _tmp_to_state(tmp, state, is_p1):
    """Синхронизирует результат apply_item обратно в PvP-state."""
    if is_p1:
        state['p1_hp']   = tmp['player_hp']
        state['p2_hp']   = tmp['dealer_hp']
        state['p2_skip'] = tmp.get('dealer_skip', False)
    else:
        state['p2_hp']   = tmp['player_hp']
        state['p1_hp']   = tmp['dealer_hp']
        state['p1_skip'] = tmp.get('dealer_skip', False)
    state['chamber']     = tmp['chamber']
    state['chamber_pos'] = tmp['chamber_pos']
    state['shots_fired'] = tmp['shots_fired']
    state['saw_active']  = tmp.get('saw_active', False)


def _public_msg(item_name, actor_name, tmp):
    msgs = {
        '🍺 Пиво':       f'🍺 {actor_name} выпил пиво — патрон сброшен.',
        '🚬 Сигареты':   f'🚬 {actor_name} закурил — +1 🫀',
        '⛓️ Наручники': f'⛓️ {actor_name} надел наручники — ты пропускаешь следующий ход!',
        '🪚 Пила':       f'🪚 {actor_name} пилит ствол — следующий выстрел усилен.',
        '💊 Лекарства':  f'💊 {actor_name} принял лекарства.',
    }
    return msgs.get(item_name, f'{actor_name} использует {item_name}.')
