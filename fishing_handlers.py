"""
fishing_handlers.py
Вызов из bot.py:
    from fishing_handlers import register_fishing_handlers, traps_checker_loop
    register_fishing_handlers(bot, get_conn, get_user, add_exp, add_money,
                              add_bait, spend_money, check_and_give_achievements)
    threading.Thread(target=traps_checker_loop, args=(bot, get_conn), daemon=True).start()
"""

import time
import random
import threading
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

import fishing as F

# ============================================================
# DB-ХЕЛПЕРЫ (заполняются в register_fishing_handlers)
# ============================================================
_get_conn  = None
_get_user  = None
_add_exp   = None
_add_money = None
_add_bait  = None
_spend_money = None
_check_achievements = None

# ============================================================
# DB-ФУНКЦИИ
# ============================================================

def _add_fish_to_catalog(user_id, fish_name):
    conn = _get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO fish_catalog (user_id, fish_name, count) VALUES (%s, %s, 1)
        ON CONFLICT (user_id, fish_name) DO UPDATE SET count = fish_catalog.count + 1
    ''', (user_id, fish_name))
    conn.commit()
    conn.close()

def _get_catalog(user_id):
    """→ dict {fish_name: count}"""
    conn = _get_conn()
    c = conn.cursor()
    c.execute('SELECT fish_name, count FROM fish_catalog WHERE user_id=%s', (user_id,))
    rows = c.fetchall()
    conn.close()
    return {name: cnt for name, cnt in rows}

def _get_traps(user_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute('SELECT slot, status, started_at FROM traps WHERE user_id=%s ORDER BY slot',
              (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def _set_trap(user_id, slot, chat_id, message_id):
    conn = _get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''UPDATE traps SET status='active', started_at=%s, chat_id=%s, message_id=%s
                 WHERE user_id=%s AND slot=%s''',
              (now, chat_id, message_id, user_id, slot))
    c.execute('UPDATE users SET bait=bait-3 WHERE user_id=%s', (user_id,))
    conn.commit()
    conn.close()

def _reset_trap(user_id, slot):
    conn = _get_conn()
    c = conn.cursor()
    c.execute('''UPDATE traps SET status='empty', started_at=NULL,
                 chat_id=NULL, message_id=NULL WHERE user_id=%s AND slot=%s''',
              (user_id, slot))
    conn.commit()
    conn.close()

def _get_ready_traps():
    conn = _get_conn()
    c = conn.cursor()
    threshold = (datetime.now() - timedelta(hours=1)).isoformat()
    c.execute('''SELECT user_id, slot, chat_id, message_id FROM traps
                 WHERE status='active' AND started_at <= %s''', (threshold,))
    rows = c.fetchall()
    conn.close()
    return rows

def _mark_trap_ready(user_id, slot):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("UPDATE traps SET status='ready' WHERE user_id=%s AND slot=%s", (user_id, slot))
    conn.commit()
    conn.close()

def _upgrade_equipment(user_id, col, new_level):
    conn = _get_conn()
    c = conn.cursor()
    c.execute(f'UPDATE users SET {col}=%s WHERE user_id=%s', (new_level, user_id))
    conn.commit()
    conn.close()

# ============================================================
# UI-ХЕЛПЕРЫ
# ============================================================

def _main_menu_markup():
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("🧰 Снаряжение",  callback_data="fish_equip"),
        InlineKeyboardButton("📒 Каталог",      callback_data="fish_catalog"),
        InlineKeyboardButton("🕸️ Ловушки",      callback_data="fish_traps"),
        InlineKeyboardButton("🎣 Закинуть",      callback_data="fish_cast"),
    )
    return m

def _equip_menu_markup():
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("⏫ Улуч. удочку 🎣",  callback_data="fish_upgrade_rod"),
        InlineKeyboardButton("⏫ Улуч. леску 🧵",   callback_data="fish_upgrade_line"),
        InlineKeyboardButton("⏫ Улуч. крючок 🪝",  callback_data="fish_upgrade_hook"),
        InlineKeyboardButton("⏫ Улуч. катушку ⚙️", callback_data="fish_upgrade_reel"),
        InlineKeyboardButton("🔙 Назад",            callback_data="fish_main"),
    )
    return m

def _fight_markup():
    m = InlineKeyboardMarkup(row_width=1)
    m.add(
        InlineKeyboardButton("🎣 Тянуть",    callback_data="fish_pull"),
        InlineKeyboardButton("🧘 Ослабить",  callback_data="fish_loosen"),
        InlineKeyboardButton("✋ Удерживать", callback_data="fish_hold"),
        InlineKeyboardButton("❌ Отпустить", callback_data="fish_release"),
    )
    return m

def _traps_markup(user_id):
    traps = _get_traps(user_id)
    m = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for slot, status, started_at in traps:
        if status == 'empty':
            buttons.append(InlineKeyboardButton(
                "Установить 🪱×3", callback_data=f"trap_set_{slot}"))
        elif status == 'active':
            started  = datetime.fromisoformat(started_at)
            remaining = (started + timedelta(hours=1)) - datetime.now()
            mins = max(0, int(remaining.total_seconds() // 60))
            buttons.append(InlineKeyboardButton(
                f"⏳ {mins} мин.", callback_data=f"trap_wait_{slot}"))
        elif status == 'ready':
            buttons.append(InlineKeyboardButton(
                "✅ Забрать", callback_data=f"trap_collect_{slot}"))
        else:
            buttons.append(InlineKeyboardButton(
                "Установить 🪱×3", callback_data=f"trap_set_{slot}"))
    m.add(*buttons)
    m.add(InlineKeyboardButton("🔙 Назад", callback_data="fish_main"))
    return m

def _catalog_text(user_id):
    catalog = _get_catalog(user_id)
    total   = sum(1 for v in catalog.values() if v > 0)
    total_count = len(F.FISH_TABLE)

    lines = [
        f"— – - 📒 *КАТАЛОГ ВЫЛОВЛЕННЫХ РЫБ* 📒 - – —\n",
        f"📝 Всего собрано: *{total}/{total_count}*\n",
    ]

    rarity_labels = {
        F.RARITY_COMMON:    '*— – ⚪ Обычные ⚪ – —*',
        F.RARITY_UNCOMMON:  '*— – 🟢 Необычные 🟢 – —*',
        F.RARITY_RARE:      '*— – 🔵 Редкие 🔵 – —*',
        F.RARITY_EPIC:      '*— – 🟣 Эпические 🟣 – —*',
        F.RARITY_LEGENDARY: '*— – 🟡 Легендарные 🟡 – —*',
    }

    for rarity in F.RARITY_ORDER:
        fish_list = F.FISH_BY_RARITY[rarity]
        caught    = sum(1 for f in fish_list if catalog.get(f[2], 0) > 0)
        lines.append(f"\n{rarity_labels[rarity]}\n_Собрано: {caught}/{len(fish_list)}_\n")
        for f in fish_list:
            name  = f[2]
            count = catalog.get(name, 0)
            if count > 0:
                lines.append(f"_{f[1]} {name} × {count}_")
            else:
                lines.append("_❔ ???_")

    lines.append(f"\n— – - - - - - - - - - - - - - - - - - - - - - – —")
    return "\n".join(lines)

def _open_treasure(user_id, chat_id, bot):
    """Открывает сокровище и отправляет сообщение (логика из старого бота)."""
    tiers = [(50, 100, 500, 1), (35, 501, 1000, 3), (10, 1001, 3000, 5), (5, 3001, 10000, 8)]
    weights = [t[0] for t in tiers]
    tier = random.choices(tiers, weights=weights, k=1)[0]
    _, min_m, max_m, egg_count = tier
    if random.random() < 0.5:
        reward = random.randint(min_m, max_m)
        _add_money(user_id, reward)
        return f"🧳 Сокровище: +💵 {reward}"
    else:
        conn = _get_conn()
        c = conn.cursor()
        c.execute('UPDATE users SET eggs=eggs+%s WHERE user_id=%s', (egg_count, user_id))
        conn.commit()
        conn.close()
        return f"🧳 Сокровище: +🥚 {egg_count} яиц"

# ============================================================
# РЕАКТИВНЫЕ ТАЙМЕРЫ (для поклёвки)
# ============================================================

def _on_bite(bot, user_id, wait_msg_id, chat_id):
    """Срабатывает когда пора клевать — редактирует сообщение."""
    with F.sessions_lock:
        session = F.fishing_sessions.get(user_id)
        if not session or session.get('state') != 'waiting_bite':
            return
        session['state'] = 'bite_shown'

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⚡ Подсечь", callback_data="fish_hook"))
    try:
        bot.edit_message_text(
            "💦 Поплавок резко ушёл под воду!\nКлюёт❕",
            chat_id=chat_id,
            message_id=wait_msg_id,
            reply_markup=markup
        )
    except: pass

    # Запускаем таймер реакции
    react_time = session['react_time']
    t = threading.Timer(react_time, _on_react_timeout, args=(bot, user_id, wait_msg_id, chat_id))
    with F.sessions_lock:
        s = F.fishing_sessions.get(user_id)
        if s:
            s['react_timer'] = t
    t.start()


def _on_react_timeout(bot, user_id, msg_id, chat_id):
    """Время реакции истекло — проверяем авто-подсечку, иначе промах."""
    with F.sessions_lock:
        session = F.fishing_sessions.get(user_id)
        if not session or session.get('state') != 'bite_shown':
            return  # игрок успел нажать раньше
        hook_chance = session.get('hook_chance', 0)
        auto_success = random.random() * 100 < hook_chance

        if auto_success:
            session['state'] = 'fighting'
            session['current_tension'] = 2
        else:
            F.fishing_sessions.pop(user_id, None)

    if auto_success:
        _start_fight(bot, user_id, msg_id, chat_id, auto=True)
    else:
        try:
            bot.delete_message(chat_id, msg_id)
        except: pass
        bot.send_message(chat_id,
            "💦 Рыба сорвалась с крючка...\n✖️Вы не успели подсечь!")


def _start_fight(bot, user_id, old_msg_id, chat_id, auto=False):
    """Начинает фазу борьбы с рыбой."""
    with F.sessions_lock:
        session = F.fishing_sessions.get(user_id)
        if not session: return

    fish     = session['fish']  # (rarity, emoji, name, strength, price, exp_min, exp_max, react)
    max_str  = fish[3]
    max_ten  = session['max_tension']

    try:
        bot.delete_message(chat_id, old_msg_id)
    except: pass

    txt = F.fight_text(fish[2], fish[1], max_str, max_str, 2, max_ten)
    msg = bot.send_message(chat_id, txt, reply_markup=_fight_markup())

    with F.sessions_lock:
        s = F.fishing_sessions.get(user_id)
        if s:
            s['fight_msg_id']      = msg.message_id
            s['current_strength']  = max_str
            s['current_tension']   = 2


# ============================================================
# РЕГИСТРАЦИЯ ХЭНДЛЕРОВ
# ============================================================

def register_fishing_handlers(bot, get_conn, get_user, add_exp, add_money,
                               add_bait, spend_money, check_achievements):
    global _get_conn, _get_user, _add_exp, _add_money, _add_bait
    global _spend_money, _check_achievements
    _get_conn           = get_conn
    _get_user           = get_user
    _add_exp            = add_exp
    _add_money          = add_money
    _add_bait           = add_bait
    _spend_money        = spend_money
    _check_achievements = check_achievements

    # ── /fishing ────────────────────────────────────────────
    @bot.message_handler(commands=['fishing'])
    def cmd_fishing(message):
        user_id  = message.from_user.id
        user     = _get_user(user_id)
        money    = user[2] if user else 0
        bait     = user[5] if user else 0
        conn     = _get_conn()
        eq       = F.get_equipment(conn, user_id)
        conn.close()
        bot.send_message(
            message.chat.id,
            F.main_menu_text(money, bait, eq),
            reply_markup=_main_menu_markup(),
            parse_mode='Markdown'
        )

    # ── Главное меню (кнопка Назад) ─────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'fish_main')
    def cb_fish_main(call):
        user_id = call.from_user.id
        user    = _get_user(user_id)
        money   = user[2] if user else 0
        bait    = user[5] if user else 0
        conn    = _get_conn()
        eq      = F.get_equipment(conn, user_id)
        conn.close()
        try:
            bot.edit_message_text(
                F.main_menu_text(money, bait, eq),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_main_menu_markup(),
                parse_mode='Markdown'
            )
        except:
            bot.send_message(
                call.message.chat.id,
                F.main_menu_text(money, bait, eq),
                reply_markup=_main_menu_markup(),
                parse_mode='Markdown'
            )
        bot.answer_callback_query(call.id)

    # ── Снаряжение ──────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'fish_equip')
    def cb_fish_equip(call):
        user_id = call.from_user.id
        user    = _get_user(user_id)
        money   = user[2] if user else 0
        bait    = user[5] if user else 0
        conn    = _get_conn()
        eq      = F.get_equipment(conn, user_id)
        conn.close()
        try:
            bot.edit_message_text(
                F.equipment_menu_text(money, bait, eq),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_equip_menu_markup(),
                parse_mode='Markdown'
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Предпросмотр улучшения ──────────────────────────────
    def _show_upgrade(call, item_key):
        user_id = call.from_user.id
        conn    = _get_conn()
        eq      = F.get_equipment(conn, user_id)
        conn.close()
        cur_lv  = eq.get(item_key, 1)
        text, price = F.upgrade_preview_text(item_key, cur_lv)
        if text is None:
            bot.answer_callback_query(call.id, "✅ Максимальный уровень!")
            return
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("⏫ Улучшить",
                                 callback_data=f"fish_do_upgrade_{item_key}"),
            InlineKeyboardButton("🔙 Назад", callback_data="fish_equip"),
        )
        try:
            bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except: pass
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data == 'fish_upgrade_rod')
    def cb_upgrade_rod(call):  _show_upgrade(call, 'rod')

    @bot.callback_query_handler(func=lambda c: c.data == 'fish_upgrade_line')
    def cb_upgrade_line(call): _show_upgrade(call, 'line')

    @bot.callback_query_handler(func=lambda c: c.data == 'fish_upgrade_hook')
    def cb_upgrade_hook(call): _show_upgrade(call, 'hook')

    @bot.callback_query_handler(func=lambda c: c.data == 'fish_upgrade_reel')
    def cb_upgrade_reel(call): _show_upgrade(call, 'reel')

    # ── Выполнить улучшение ─────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('fish_do_upgrade_'))
    def cb_do_upgrade(call):
        user_id  = call.from_user.id
        item_key = call.data[len('fish_do_upgrade_'):]
        conn     = _get_conn()
        eq       = F.get_equipment(conn, user_id)
        conn.close()
        cur_lv   = eq.get(item_key, 1)

        if cur_lv >= F.MAX_LEVEL:
            bot.answer_callback_query(call.id, "✅ Максимальный уровень!")
            return

        _, price = F.upgrade_preview_text(item_key, cur_lv)
        user     = _get_user(user_id)
        money    = user[2] if user else 0

        if money < price:
            bot.answer_callback_query(
                call.id, f"❌ Недостаточно денег! Нужно 💵{price:,}")
            return

        _spend_money(user_id, price)
        col = F.EQUIPMENT_ITEMS[item_key]['col']
        _upgrade_equipment(user_id, col, cur_lv + 1)
        bot.answer_callback_query(call.id,
            f"✅ {F.EQUIPMENT_ITEMS[item_key]['name']} улучшена до Ур. {cur_lv+1}!")

        # Возвращаем меню снаряжения
        user2  = _get_user(user_id)
        money2 = user2[2] if user2 else 0
        bait2  = user2[5] if user2 else 0
        conn2  = _get_conn()
        eq2    = F.get_equipment(conn2, user_id)
        conn2.close()
        try:
            bot.edit_message_text(
                F.equipment_menu_text(money2, bait2, eq2),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_equip_menu_markup(),
                parse_mode='Markdown'
            )
        except: pass

    # ── Каталог ─────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'fish_catalog')
    def cb_catalog(call):
        user_id = call.from_user.id
        markup  = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="fish_main"))
        try:
            bot.edit_message_text(
                _catalog_text(user_id),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Ловушки ─────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'fish_traps')
    def cb_traps(call):
        user_id = call.from_user.id
        user    = _get_user(user_id)
        money   = user[2] if user else 0
        bait    = user[5] if user else 0
        text    = (
            f"— – - 🕸️ ЛОВУШКИ 🕸️ - – —\n\n"
            f"Денег: 💵 {money}\n"
            f"Наживки: 🪱 {bait}\n\n"
            f"{F.SEP2}"
        )
        try:
            bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_traps_markup(user_id)
            )
        except: pass
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('trap_wait_'))
    def cb_trap_wait(call):
        bot.answer_callback_query(call.id, "⏳ Ещё не готово!")

    @bot.callback_query_handler(func=lambda c: c.data.startswith('trap_set_'))
    def cb_trap_set(call):
        user_id = call.from_user.id
        slot    = int(call.data.split('_')[2])
        user    = _get_user(user_id)
        bait    = user[5] if user else 0
        if bait < 3:
            bot.answer_callback_query(call.id, "❌ Нужно минимум 3 🪱 наживки!")
            return
        _set_trap(user_id, slot, call.message.chat.id, call.message.message_id)
        user2  = _get_user(user_id)
        money2 = user2[2] if user2 else 0
        bait2  = user2[5] if user2 else 0
        text   = (
            f"— – - 🕸️ ЛОВУШКИ 🕸️ - – —\n\n"
            f"Денег: 💵 {money2}\n"
            f"Наживки: 🪱 {bait2}\n\n"
            f"{F.SEP2}"
        )
        try:
            bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_traps_markup(user_id)
            )
        except: pass
        bot.answer_callback_query(call.id, "🕸️ Ловушка установлена!")

    @bot.callback_query_handler(func=lambda c: c.data.startswith('trap_collect_'))
    def cb_trap_collect(call):
        user_id = call.from_user.id
        slot    = int(call.data.split('_')[2])
        rewards = []
        exp_gain = random.randint(10, 100)

        for _ in range(3):
            rarity, fish = F.random_trap_reward()
            if rarity == 'treasure':
                rewards.append(_open_treasure(user_id, call.message.chat.id, bot))
            else:
                name   = fish[2]
                emoji  = fish[1]
                price  = fish[4]
                rname  = F.RARITY_NAMES.get(rarity, '')
                rewards.append(f"+ {emoji} {name} | {rarity} {rname} | +💵{price}")
                _add_fish_to_catalog(user_id, name)
                _add_money(user_id, price)

        _add_exp(user_id, exp_gain)
        _reset_trap(user_id, slot)

        lines = "\n".join(rewards)
        bot.send_message(
            call.message.chat.id,
            f"🕸️ Собрано с ловушки:\n\n{lines}\n\n+ 🌟 {exp_gain} Опыта"
        )

        # Обновляем меню ловушек
        user2  = _get_user(user_id)
        money2 = user2[2] if user2 else 0
        bait2  = user2[5] if user2 else 0
        text   = (
            f"— – - 🕸️ ЛОВУШКИ 🕸️ - – —\n\n"
            f"Денег: 💵 {money2}\n"
            f"Наживки: 🪱 {bait2}\n\n"
            f"{F.SEP2}"
        )
        try:
            bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_traps_markup(user_id)
            )
        except: pass

        # Счётчики достижений
        conn2 = _get_conn()
        c2    = conn2.cursor()
        c2.execute('UPDATE users SET fish_caught=fish_caught+3 WHERE user_id=%s', (user_id,))
        c2.execute('UPDATE users SET fishing_count=fishing_count+1 WHERE user_id=%s', (user_id,))
        conn2.commit()
        conn2.close()
        threading.Thread(
            target=_check_achievements,
            args=(user_id, call.message.chat.id),
            daemon=True
        ).start()
        bot.answer_callback_query(call.id)

    # ── Закинуть удочку ─────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'fish_cast')
    def cb_fish_cast(call):
        user_id = call.from_user.id
        user    = _get_user(user_id)
        bait    = user[5] if user else 0

        if bait < 1:
            bot.answer_callback_query(call.id, "❌ Нет наживок!")
            return

        # Проверяем не в рыбалке ли уже
        with F.sessions_lock:
            if user_id in F.fishing_sessions:
                bot.answer_callback_query(call.id, "❌ Ты уже ловишь рыбу!")
                return

        # Снимаем наживку
        _spend_money(user_id, 0)  # просто вызов для совместимости
        conn = _get_conn()
        c    = conn.cursor()
        c.execute('UPDATE users SET bait=bait-1 WHERE user_id=%s', (user_id,))
        conn.commit()
        conn.close()

        bait_left = bait - 1

        # Получаем снаряжение и выбираем рыбу
        conn2 = _get_conn()
        eq    = F.get_equipment(conn2, user_id)
        conn2.close()

        rod_stats  = F.ROD_LEVELS[eq['rod']]
        line_stats = F.LINE_LEVELS[eq['line']]
        hook_stats = F.HOOK_LEVELS[eq['hook']]

        fish          = F.random_fish(rare_bonus=hook_stats['rare_bonus'])
        react_time    = fish[7] + rod_stats['time_bonus']
        wait_time     = random.uniform(2, 17)
        max_tension   = line_stats['max_tension']
        start_tension = line_stats['start_tension']
        hook_chance   = hook_stats['hook_chance']

        # Отправляем сообщение ожидания
        msg = bot.send_message(
            call.message.chat.id,
            f"- 1 🪱 Наживка ({bait_left})\n"
            f"🎣 Вы закинули удочку...\n\n"
            f"Ожидание клёва. . ."
        )
        bot.answer_callback_query(call.id)

        # Сохраняем сессию
        with F.sessions_lock:
            F.fishing_sessions[user_id] = {
                'state':           'waiting_bite',
                'fish':            fish,
                'react_time':      react_time,
                'max_tension':     max_tension,
                'hook_chance':     hook_chance,
                'rod_damage':      rod_stats['damage'],
                'reel_loosen':     F.REEL_LEVELS[eq['reel']]['loosen'],
                'chat_id':         call.message.chat.id,
                'wait_msg_id':     msg.message_id,
                'current_strength': fish[3],
                'current_tension':  start_tension,
                'fight_msg_id':    None,
            }

        # Запускаем таймер клёва
        t = threading.Timer(
            wait_time, _on_bite,
            args=(bot, user_id, msg.message_id, call.message.chat.id)
        )
        with F.sessions_lock:
            s = F.fishing_sessions.get(user_id)
            if s: s['bite_timer'] = t
        t.start()

        # Счётчик установок наживки
        conn3 = _get_conn()
        c3    = conn3.cursor()
        c3.execute('UPDATE users SET fishing_count=fishing_count+1 WHERE user_id=%s', (user_id,))
        conn3.commit()
        conn3.close()

    # ── Подсечь ─────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'fish_hook')
    def cb_fish_hook(call):
        user_id = call.from_user.id
        with F.sessions_lock:
            session = F.fishing_sessions.get(user_id)
            if not session or session.get('state') != 'bite_shown':
                bot.answer_callback_query(call.id, "⏰ Уже поздно!")
                return
            # Отменяем таймер реакции
            t = session.pop('react_timer', None)
            if t: t.cancel()
            session['state']           = 'fighting'
            session['current_tension'] = 2
            msg_id  = session['wait_msg_id']
            chat_id = session['chat_id']

        bot.answer_callback_query(call.id)
        _start_fight(bot, user_id, msg_id, chat_id)

    # ── Действия борьбы ─────────────────────────────────────
    def _process_fight_action(call, action):
        user_id = call.from_user.id
        with F.sessions_lock:
            session = F.fishing_sessions.get(user_id)
            if not session or session.get('state') != 'fighting':
                bot.answer_callback_query(call.id, "❌ Нет активной рыбалки!")
                return

            fish        = session['fish']
            cur_str     = session['current_strength']
            cur_ten     = session['current_tension']
            max_ten     = session['max_tension']
            max_str     = fish[3]
            rod_dmg     = session['rod_damage']
            reel_loosen = session['reel_loosen']
            is_leg      = fish[0] == F.RARITY_LEGENDARY
            chat_id     = session['chat_id']
            fight_msg   = session['fight_msg_id']

        bot.answer_callback_query(call.id)

        # Действие игрока
        if action == 'pull':
            dmg     = 1 + rod_dmg
            cur_str = max(0, cur_str - dmg)
            cur_ten = cur_ten + 3
            note    = f"🎣 Ты решаешь тянуть!\nУрон: -{dmg} силы рыбы, +3 натяжение"
        elif action == 'loosen':
            cur_str = cur_str + (2 if is_leg else 1)
            cur_ten = max(0, cur_ten - reel_loosen)
            note    = f"🧘 Ты ослабляешь леску!\n+{2 if is_leg else 1} сила рыбы, -{reel_loosen} натяжение"
        elif action == 'hold':
            cur_str = max(0, cur_str - 1)
            cur_ten = cur_ten + 1
            note    = "✋ Ты удерживаешь!\n-1 сила рыбы, +1 натяжение"
        elif action == 'release':
            # Отпустить рыбу
            with F.sessions_lock:
                F.fishing_sessions.pop(user_id, None)
            try:
                bot.delete_message(chat_id, fight_msg)
            except: pass
            user2  = _get_user(user_id)
            money2 = user2[2] if user2 else 0
            bait2  = user2[5] if user2 else 0
            conn   = _get_conn()
            eq     = F.get_equipment(conn, user_id)
            conn.close()
            bot.send_message(
                chat_id,
                f"❌ Ты отпустил рыбу...\n\n{F.main_menu_text(money2, bait2, eq)}",
                reply_markup=_main_menu_markup(),
                parse_mode='Markdown'
            )
            return
        else:
            return

        # Обновляем сообщение — действие игрока
        try:
            bot.edit_message_text(
                F.fight_text(fish[2], fish[1], cur_str, max_str, cur_ten, max_ten, note),
                chat_id=chat_id,
                message_id=fight_msg
            )
        except: pass

        # Проверка победы (сила рыбы = 0)
        if cur_str <= 0:
            with F.sessions_lock:
                F.fishing_sessions.pop(user_id, None)
            _on_fish_caught(bot, user_id, fish, chat_id, fight_msg)
            return

        # Проверка обрыва (натяжение >= макс)
        if cur_ten >= max_ten:
            with F.sessions_lock:
                F.fishing_sessions.pop(user_id, None)
            try:
                bot.delete_message(chat_id, fight_msg)
            except: pass
            bot.send_message(chat_id, "💥 Леска не выдержала и порвалась!\n❌ Рыба ушла...")
            return

        time.sleep(0.5)

        # Случайное действие рыбы
        is_epic_or_leg = fish[0] in (F.RARITY_EPIC, F.RARITY_LEGENDARY)
        fish_text, ten_delta, str_delta = F.fish_action(is_epic_or_legendary=is_epic_or_leg)
        cur_ten = min(max_ten, cur_ten + ten_delta)
        cur_str = min(max_str, cur_str + str_delta)

        # Отправляем действие рыбы новым сообщением
        fish_msg = bot.send_message(chat_id, fish_text)
        time.sleep(0.8)

        # Удаляем сообщение действия рыбы
        try:
            bot.delete_message(chat_id, fish_msg.message_id)
        except: pass

        # Проверка после действия рыбы
        if cur_str <= 0:
            with F.sessions_lock:
                F.fishing_sessions.pop(user_id, None)
            _on_fish_caught(bot, user_id, fish, chat_id, fight_msg)
            return

        if cur_ten >= max_ten:
            with F.sessions_lock:
                F.fishing_sessions.pop(user_id, None)
            try:
                bot.delete_message(chat_id, fight_msg)
            except: pass
            bot.send_message(chat_id, "💥 Леска не выдержала и порвалась!\n❌ Рыба ушла...")
            return

        # Обновляем состояние и сообщение
        with F.sessions_lock:
            s = F.fishing_sessions.get(user_id)
            if s:
                s['current_strength'] = cur_str
                s['current_tension']  = cur_ten

        try:
            bot.edit_message_text(
                F.fight_text(fish[2], fish[1], cur_str, max_str, cur_ten, max_ten),
                chat_id=chat_id,
                message_id=fight_msg,
                reply_markup=_fight_markup()
            )
        except: pass

    @bot.callback_query_handler(func=lambda c: c.data == 'fish_pull')
    def cb_pull(call):    _process_fight_action(call, 'pull')

    @bot.callback_query_handler(func=lambda c: c.data == 'fish_loosen')
    def cb_loosen(call):  _process_fight_action(call, 'loosen')

    @bot.callback_query_handler(func=lambda c: c.data == 'fish_hold')
    def cb_hold(call):    _process_fight_action(call, 'hold')

    @bot.callback_query_handler(func=lambda c: c.data == 'fish_release')
    def cb_release(call): _process_fight_action(call, 'release')

    # ── Рыба поймана ────────────────────────────────────────
    def _on_fish_caught(bot, user_id, fish, chat_id, fight_msg_id):
        rarity   = fish[0]
        emoji    = fish[1]
        name     = fish[2]
        price    = fish[4]
        exp_gain = random.randint(fish[5], fish[6])
        rname    = F.RARITY_NAMES.get(rarity, '')

        _add_fish_to_catalog(user_id, name)
        _add_exp(user_id, exp_gain)
        _add_money(user_id, price)

        try:
            bot.delete_message(chat_id, fight_msg_id)
        except: pass

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🔙 Назад",   callback_data="fish_main"),
            InlineKeyboardButton("📒 Каталог", callback_data="fish_catalog"),
        )
        bot.send_message(
            chat_id,
            f"🎣 Рыба поймана! 🎉\n\n"
            f"{emoji} {name} {rarity} {rname}\n\n"
            f"+ 💵 {price}\n"
            f"+ {exp_gain} 🌟 Опыта",
            reply_markup=markup
        )

        # Счётчики достижений
        conn2 = _get_conn()
        c2    = conn2.cursor()
        c2.execute('UPDATE users SET fish_caught=fish_caught+1 WHERE user_id=%s', (user_id,))
        conn2.commit()
        conn2.close()
        threading.Thread(
            target=_check_achievements,
            args=(user_id, chat_id),
            daemon=True
        ).start()


# ============================================================
# ФОНОВЫЙ ЧЕКЕР ЛОВУШЕК
# ============================================================

def traps_checker_loop(bot, get_conn):
    while True:
        try:
            conn = get_conn()
            c    = conn.cursor()
            threshold = (datetime.now() - timedelta(hours=1)).isoformat()
            c.execute('''SELECT user_id, slot, chat_id, message_id FROM traps
                         WHERE status='active' AND started_at <= %s''', (threshold,))
            rows = c.fetchall()
            conn.close()

            for user_id, slot, chat_id, message_id in rows:
                _mark_trap_ready(user_id, slot)
                # Пробуем обновить кнопки в меню ловушек если оно открыто
                if chat_id and message_id:
                    try:
                        user2  = _get_user(user_id)
                        money2 = user2[2] if user2 else 0
                        bait2  = user2[5] if user2 else 0
                        text   = (
                            f"— – - 🕸️ ЛОВУШКИ 🕸️ - – —\n\n"
                            f"Денег: 💵 {money2}\n"
                            f"Наживки: 🪱 {bait2}\n\n"
                            f"{F.SEP2}"
                        )
                        markup = _traps_markup(user_id)
                        bot.edit_message_text(
                            text,
                            chat_id=chat_id,
                            message_id=message_id,
                            reply_markup=markup
                        )
                    except: pass
        except Exception as e:
            print(f"Traps checker error: {e}")
        time.sleep(30)
