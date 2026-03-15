"""
garden_handlers.py
Вызов из bot.py:
    from garden_handlers import register_garden_handlers
    register_garden_handlers(bot, get_conn, get_user, add_exp, add_money, spend_money)
"""
import threading
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import garden as G

_get_conn    = None
_get_user    = None
_add_exp     = None
_add_money   = None
_spend_money = None
_check_achievements = None

# ============================================================
# DB ФУНКЦИИ
# ============================================================

def _init_garden_db():
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS garden_plots (
        user_id    BIGINT,
        bed        INTEGER,
        slot       INTEGER,
        crop_emoji TEXT    DEFAULT NULL,
        planted_at TEXT    DEFAULT NULL,
        watered_at TEXT    DEFAULT NULL,
        fert_growth  INTEGER DEFAULT 0,
        fert_quality INTEGER DEFAULT 0,
        fert_yield   INTEGER DEFAULT 0,
        fert_name    TEXT    DEFAULT NULL,
        PRIMARY KEY (user_id, bed, slot)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS garden_seeds (
        user_id    BIGINT,
        crop_emoji TEXT,
        count      INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, crop_emoji)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS garden_inventory (
        user_id    BIGINT,
        crop_emoji TEXT,
        quality    INTEGER,
        count      INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, crop_emoji, quality)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS garden_fertilizers (
        user_id   BIGINT,
        fert_key  TEXT,
        count     INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, fert_key)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS garden_harvest_log (
        id          SERIAL PRIMARY KEY,
        user_id     BIGINT,
        crop_emoji  TEXT,
        quality     INTEGER,
        harvested_at TEXT
    )''')
    try:
        c.execute("ALTER TABLE garden_plots ADD COLUMN IF NOT EXISTS fert_name TEXT DEFAULT NULL")
        conn.commit()
    except: conn.rollback()
    conn.commit()
    conn.close()

def _ensure_slots(user_id):
    conn = _get_conn()
    c    = conn.cursor()
    for bed_num, binfo in G.BED_TYPES.items():
        for s in range(1, binfo['slots'] + 1):
            c.execute(
                'INSERT INTO garden_plots (user_id, bed, slot) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',
                (user_id, bed_num, s)
            )
    conn.commit()
    conn.close()

def _get_slots(user_id, bed_num):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute(
        'SELECT slot,crop_emoji,planted_at,watered_at,fert_growth,fert_quality,fert_yield,fert_name '
        'FROM garden_plots WHERE user_id=%s AND bed=%s ORDER BY slot',
        (user_id, bed_num)
    )
    rows = c.fetchall()
    conn.close()
    return [{'slot': r[0], 'crop_emoji': r[1], 'planted_at': r[2],
             'watered_at': r[3], 'fert_growth': r[4],
             'fert_quality': r[5], 'fert_yield': r[6], 'fert_name': r[7]} for r in rows]


def _get_slot(user_id, bed_num, slot_num):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute(
        'SELECT slot,crop_emoji,planted_at,watered_at,fert_growth,fert_quality,fert_yield,fert_name '
        'FROM garden_plots WHERE user_id=%s AND bed=%s AND slot=%s',
        (user_id, bed_num, slot_num)
    )
    r = c.fetchone()
    conn.close()
    if not r:
        return None
    return {'slot': r[0], 'crop_emoji': r[1], 'planted_at': r[2],
            'watered_at': r[3], 'fert_growth': r[4],
            'fert_quality': r[5], 'fert_yield': r[6], 'fert_name': r[7]}

def _get_seeds(user_id):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT crop_emoji, count FROM garden_seeds WHERE user_id=%s AND count>0', (user_id,))
    rows = c.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

def _add_seed(user_id, crop_emoji, amount=1):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('''INSERT INTO garden_seeds (user_id, crop_emoji, count) VALUES (%s,%s,%s)
                 ON CONFLICT (user_id, crop_emoji) DO UPDATE SET count=garden_seeds.count+%s''',
              (user_id, crop_emoji, amount, amount))
    conn.commit()
    conn.close()

def _spend_seed(user_id, crop_emoji):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('UPDATE garden_seeds SET count=count-1 WHERE user_id=%s AND crop_emoji=%s AND count>0',
              (user_id, crop_emoji))
    updated = c.rowcount
    conn.commit()
    conn.close()
    return updated > 0

def _get_fertilizers(user_id):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT fert_key, count FROM garden_fertilizers WHERE user_id=%s AND count>0', (user_id,))
    rows = c.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

def _add_fertilizer(user_id, fert_key, amount=1):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('''INSERT INTO garden_fertilizers (user_id, fert_key, count) VALUES (%s,%s,%s)
                 ON CONFLICT (user_id, fert_key) DO UPDATE SET count=garden_fertilizers.count+%s''',
              (user_id, fert_key, amount, amount))
    conn.commit()
    conn.close()

def _spend_fertilizer(user_id, fert_key):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('UPDATE garden_fertilizers SET count=count-1 WHERE user_id=%s AND fert_key=%s AND count>0',
              (user_id, fert_key))
    updated = c.rowcount
    conn.commit()
    conn.close()
    return updated > 0

def _add_to_inventory(user_id, crop_emoji, quality, count=1):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('''INSERT INTO garden_inventory (user_id, crop_emoji, quality, count) VALUES (%s,%s,%s,%s)
                 ON CONFLICT (user_id, crop_emoji, quality) DO UPDATE SET count=garden_inventory.count+%s''',
              (user_id, crop_emoji, quality, count, count))
    conn.commit()
    conn.close()

def _get_inventory(user_id):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT crop_emoji, quality, count FROM garden_inventory WHERE user_id=%s AND count>0 ORDER BY crop_emoji, quality',
              (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows  # [(emoji, quality, count), ...]

def _log_harvest(user_id, crop_emoji, quality):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('INSERT INTO garden_harvest_log (user_id, crop_emoji, quality, harvested_at) VALUES (%s,%s,%s,%s)',
              (user_id, crop_emoji, quality, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def _plant_slot(user_id, bed_num, slot_num, crop_emoji):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('''UPDATE garden_plots SET crop_emoji=%s, planted_at=%s,
                 watered_at=NULL, fert_growth=0, fert_quality=0, fert_yield=0, fert_name=NULL
                 WHERE user_id=%s AND bed=%s AND slot=%s''',
              (crop_emoji, datetime.now().isoformat(), user_id, bed_num, slot_num))
    conn.commit()
    conn.close()

def _water_slot(user_id, bed_num, slot_num):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('UPDATE garden_plots SET watered_at=%s WHERE user_id=%s AND bed=%s AND slot=%s',
              (datetime.now().isoformat(), user_id, bed_num, slot_num))
    conn.commit()
    conn.close()

def _apply_fertilizer(user_id, bed_num, slot_num, fert_key):
    fert = G.FERTILIZERS[fert_key]
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('''UPDATE garden_plots SET
                 fert_growth=fert_growth+%s,
                 fert_quality=fert_quality+%s,
                 fert_yield=fert_yield+%s,
                 fert_name=%s
                 WHERE user_id=%s AND bed=%s AND slot=%s''',
              (fert['growth'], fert['quality'], fert['yield'],
               f"{fert['emoji']} {fert['name']}",
               user_id, bed_num, slot_num))
    conn.commit()
    conn.close()

def _clear_slot(user_id, bed_num, slot_num):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('''UPDATE garden_plots SET crop_emoji=NULL, planted_at=NULL,
                 watered_at=NULL, fert_growth=0, fert_quality=0, fert_yield=0
                 WHERE user_id=%s AND bed=%s AND slot=%s''',
              (user_id, bed_num, slot_num))
    conn.commit()
    conn.close()

def _regrow_slot(user_id, bed_num, slot_num):
    """Перезапускает таймер роста (для кустов и деревьев)."""
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('''UPDATE garden_plots SET planted_at=%s, watered_at=NULL
                 WHERE user_id=%s AND bed=%s AND slot=%s''',
              (datetime.now().isoformat(), user_id, bed_num, slot_num))
    conn.commit()
    conn.close()

def _harvest_slot(user_id, bed_num, slot_num, slot_row):
    """Собирает урожай. Возвращает (emoji, quality, count) или None."""
    if not slot_row or not slot_row['crop_emoji']:
        return None
    if not G.is_ready(slot_row):
        return None

    crop_e  = slot_row['crop_emoji']
    qual    = G.roll_quality(slot_row.get('fert_quality', 0))
    count   = (3 if bed_num == 3 else 1) + slot_row.get('fert_yield', 0)
    
    _add_to_inventory(user_id, crop_e, qual, count)
    _log_harvest(user_id, crop_e, qual)

    bed_info = G.BED_TYPES.get(bed_num, {})
    if bed_info.get('regrow'):
        _regrow_slot(user_id, bed_num, slot_num)
    else:
        _clear_slot(user_id, bed_num, slot_num)

    conn2 = _get_conn()
    c2    = conn2.cursor()
    c2.execute('UPDATE users SET vegs_harvested=vegs_harvested+1 WHERE user_id=%s', (user_id,))
    conn2.commit()
    conn2.close()

    return crop_e, qual, count

# ============================================================
# СТАТИСТИКА ДЛЯ ГЛАВНОГО МЕНЮ
# ============================================================

def _garden_stats(user_id):
    planted = 0
    ready   = 0
    now     = datetime.now()

    for bed_num in [1, 2, 3]:
        slots = _get_slots(user_id, bed_num)
        for s in slots:
            if s['crop_emoji']:
                planted += 1
                if G.is_ready(s, now):
                    ready += 1

    conn = _get_conn()
    c    = conn.cursor()
    since = (now - timedelta(hours=24)).isoformat()
    c.execute('SELECT COUNT(*), MAX(quality) FROM garden_harvest_log WHERE user_id=%s AND harvested_at>=%s',
              (user_id, since))
    row = c.fetchone()

    # Считаем готовые блюда в зданиях
    c.execute('SELECT COUNT(*) FROM cooking_slots WHERE user_id=%s AND is_done=TRUE AND recipe_key IS NOT NULL',
              (user_id,))
    bld_row = c.fetchone()
    conn.close()

    today_count  = row[0] or 0
    best_q       = row[1] or 0
    bld_ready    = bld_row[0] if bld_row else 0
    return planted, ready, bld_ready, today_count, best_q

# ============================================================
# ТЕКСТЫ И РАЗМЕТКИ
# ============================================================

def _main_menu_text(user_id):
    import garden as G
    w_emoji, w_name, w_effect = G.weather_info()
    user    = _get_user(user_id)
    money   = user[2] if user else 0
    exp     = user[3] if user else 0
    planted, ready, bld_ready, today_count, best_q = _garden_stats(user_id)
    best_str = G.quality_str(best_q) if best_q else '—'
    return (
        f"🚜 — – – – ФЕРМА – – – — 🚜\n\n"
        f"💰 Деньги: 💵 {money}\n"
        f"⭐ Опыт: {exp}\n\n"
        f"{G.SEP}\n\n"
        f"Погода: {w_emoji} {w_name}\nЭффект: {w_effect}\n\n"
        f"🎲 Событие: —\n\n"
        f"{G.SEP}\n\n"
        f"🪏 Посажено: {planted}\n"
        f"🌾 Созрело: {ready}\n"
        f"🍯 Готово в зданиях: {bld_ready}\n\n"
        f"{G.SEP}\n\n"
        f"📈 Урожай сегодня: {today_count}\n"
        f"🌟 Лучшее качество: {best_str}"
    )

def _main_menu_markup():
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("🌱 Грядки",    callback_data="grd_beds_1"),
        InlineKeyboardButton("🏪 Рынок",     callback_data="grd_market"),
    )
    m.add(
        InlineKeyboardButton("🛍️ Магазин",  callback_data="grd_shop_1"),
        InlineKeyboardButton("🏭 Здания",    callback_data="grd_buildings"),
    )
    m.add(
        InlineKeyboardButton("📋 Задания",   callback_data="grd_quests"),
        InlineKeyboardButton("📦 Инвентарь", callback_data="grd_inventory"),
    )
    return m

def _seeds_text(user_id):
    seeds = _get_seeds(user_id)
    if not seeds:
        return "📦 Семена: пусто"
    lines = []
    for em, cnt in seeds.items():
        name = G.CROPS.get(em, {}).get('name', em)
        lines.append(f"  {em} {name} ×{cnt}")
    return "📦 Семена:\n" + "\n".join(lines)

def _bed_menu_text(user_id, bed_num):
    import garden as G
    w_emoji, w_name, w_effect = G.weather_info()
    binfo = G.BED_TYPES[bed_num]
    return (
        f"— – – 🪏 ГРЯДКА №{bed_num} 🪏 – – —\n\n"
        f"Погода: {w_emoji} {w_name}\nЭффект: {w_effect}\n\n"
        f"🎲 Событие: —\n\n"
        f"{G.SEP}\n\n"
        f"{_seeds_text(user_id)}\n\n"
        f"{G.SEP}"
    )

def _bed_markup(user_id, bed_num):
    slots   = _get_slots(user_id, bed_num)
    binfo   = G.BED_TYPES[bed_num]
    total   = binfo['slots']
    now     = datetime.now()
    m       = InlineKeyboardMarkup(row_width=5)
    buttons = []

    for s in slots:
        snum = s['slot']
        em   = G.get_slot_emoji(s, now)
        buttons.append(InlineKeyboardButton(
            f"{snum}.{em}", callback_data=f"grd_slot_{bed_num}_{snum}"
        ))

    m.add(*buttons)

    nav = []
    nav.append(InlineKeyboardButton("🔙 Назад", callback_data="grd_main"))
    nav.append(InlineKeyboardButton("🧺 Собрать все", callback_data=f"grd_harvest_all_{bed_num}"))
    if bed_num > 1:
        nav.append(InlineKeyboardButton(f"⏪ Грядка №{bed_num-1}", callback_data=f"grd_beds_{bed_num-1}"))
    if bed_num < 3:
        nav.append(InlineKeyboardButton(f"⏩ Грядка №{bed_num+1}", callback_data=f"grd_beds_{bed_num+1}"))
    m.add(*nav)
    return m

def _slot_info_text(user_id, bed_num, slot_num, slot_row):
    import garden as G
    w_emoji, w_name, w_effect = G.weather_info()
    crop_e = slot_row['crop_emoji']
    crop   = G.CROPS.get(crop_e, {})
    name   = crop.get('name', crop_e)
    grow_e = {1: '🌱', 2: '🌿', 3: '🌳'}.get(bed_num, '🌱')
    pct, left = G.growth_progress(slot_row)
    ws, has_water = G.water_status(slot_row)
    gb, qb = G.growth_bonuses(slot_row)

    return (
        f"— – – 🪏 ГРЯДКА №{bed_num} 🪏 – – —\n\n"
        f"Погода: {w_emoji} {w_name}\nЭффект: {w_effect}\n\n"
        f"🎲 Событие: —\n\n"
        f"{G.SEP}\n\n"
        f"{grow_e} {crop_e}{name}\n\n"
        f"📈 Рост: {pct}%\n"
        f"⏳ До сбора: {G.format_time(left)}\n\n"
        f"💧 Влажность: {ws}\n"
        f"🧪 Удобрение: {slot_row['fert_name'] if slot_row.get('fert_name') else '❌'}\n\n"
        f"⏫ Бонусы роста: +{gb}%\n"
        f"⏫ Бонусы качества: +{qb}%\n\n"
        f"{G.SEP}"
    )

def _slot_info_markup(bed_num, slot_num):
    m = InlineKeyboardMarkup(row_width=3)
    m.add(
        InlineKeyboardButton("💧 Полить",   callback_data=f"grd_water_{bed_num}_{slot_num}"),
        InlineKeyboardButton("🧪 Удобрить", callback_data=f"grd_fert_{bed_num}_{slot_num}"),
        InlineKeyboardButton("🪏 Выкопать", callback_data=f"grd_dig_{bed_num}_{slot_num}"),
    )
    m.add(InlineKeyboardButton("🔙 Назад", callback_data=f"grd_beds_{bed_num}"))
    return m

def _plant_choice_text(user_id, bed_num, slot_num):
    import garden as G
    w_emoji, w_name, w_effect = G.weather_info()
    return (
        f"— – – 🪏 ГРЯДКА №{bed_num} 🪏 – – —\n\n"
        f"Погода: {w_emoji} {w_name}\nЭффект: {w_effect}\n\n"
        f"🎲 Событие: —\n\n"
        f"{G.SEP}\n\n"
        f"{_seeds_text(user_id)}\n\n"
        f"{G.SEP}\n\n"
        f"🟫 Пустой слот\nПосади что нибудь сюда\n\n"
        f"{G.SEP}"
    )

def _plant_choice_markup(user_id, bed_num, slot_num):
    seeds = _get_seeds(user_id)
    m     = InlineKeyboardMarkup(row_width=4)
    btns  = []
    for em, cnt in seeds.items():
        crop = G.CROPS.get(em, {})
        if crop.get('bed') == bed_num and cnt > 0:
            btns.append(InlineKeyboardButton(
                f"{em}×{cnt}", callback_data=f"grd_plant_{bed_num}_{slot_num}_{em}"
            ))
    if btns:
        m.add(*btns)
    m.add(InlineKeyboardButton("🔙 Назад", callback_data=f"grd_beds_{bed_num}"))
    return m

# ============================================================
# РЕГИСТРАЦИЯ ХЭНДЛЕРОВ
# ============================================================

def register_garden_handlers(bot, get_conn, get_user, add_exp, add_money, spend_money, check_achievements):
    global _get_conn, _get_user, _add_exp, _add_money, _spend_money
    _get_conn    = get_conn
    _get_user    = get_user
    _add_exp     = add_exp
    _add_money   = add_money
    _spend_money = spend_money
    _check_achievements = check_achievements

    _init_garden_db()

    # ── /garden ─────────────────────────────────────────────
    @bot.message_handler(commands=['farm'])
    def cmd_garden(message):
        user_id = message.from_user.id
        _ensure_slots(user_id)
        bot.send_message(
            message.chat.id,
            _main_menu_text(user_id),
            reply_markup=_main_menu_markup()
        )

    # ── Главное меню ────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'grd_main')
    def cb_grd_main(call):
        user_id = call.from_user.id
        _ensure_slots(user_id)
        try:
            bot.edit_message_text(
                _main_menu_text(user_id),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_main_menu_markup()
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── В разработке ────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'grd_wip')
    def cb_grd_wip(call):
        bot.answer_callback_query(call.id, "🔧 В разработке")

    # ── Меню грядки ─────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('grd_beds_'))
    def cb_grd_beds(call):
        user_id  = call.from_user.id
        bed_num  = int(call.data.split('_')[2])
        _ensure_slots(user_id)
        try:
            bot.edit_message_text(
                _bed_menu_text(user_id, bed_num),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_bed_markup(user_id, bed_num)
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Клик по слоту ───────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('grd_slot_'))
    def cb_grd_slot(call):
        user_id  = call.from_user.id
        parts    = call.data.split('_')
        bed_num  = int(parts[2])
        slot_num = int(parts[3])
        slot_row = _get_slot(user_id, bed_num, slot_num)

        if not slot_row or not slot_row['crop_emoji']:
            # Пустой — показать выбор семян
            try:
                bot.edit_message_text(
                    _plant_choice_text(user_id, bed_num, slot_num),
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=_plant_choice_markup(user_id, bed_num, slot_num)
                )
            except: pass
        elif G.is_ready(slot_row):
            # Созрело — собрать
            result = _harvest_slot(user_id, bed_num, slot_num, slot_row)
            if result:
                crop_e, qual, count = result
                name = G.CROPS.get(crop_e, {}).get('name', crop_e)
                bot.answer_callback_query(call.id,
                    f"+{count}{crop_e} {G.quality_str(qual)}")
                threading.Thread(
            target=_check_achievements,
            args=(user_id, call.message.chat.id),
            daemon=True
        ).start()
            try:
                bot.edit_message_text(
                    _bed_menu_text(user_id, bed_num),
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=_bed_markup(user_id, bed_num)
                )
            except: pass
        else:
            # Растёт — показать инфо
            try:
                bot.edit_message_text(
                    _slot_info_text(user_id, bed_num, slot_num, slot_row),
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=_slot_info_markup(bed_num, slot_num)
                )
            except: pass
            bot.answer_callback_query(call.id)

    # ── Посадить семя ────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('grd_plant_'))
    def cb_grd_plant(call):
        user_id  = call.from_user.id
        parts    = call.data.split('_')
        bed_num  = int(parts[2])
        slot_num = int(parts[3])
        crop_e   = parts[4]

        if not _spend_seed(user_id, crop_e):
            bot.answer_callback_query(call.id, "❌ Семян нет!")
            return

        _plant_slot(user_id, bed_num, slot_num, crop_e)
        slot_row = _get_slot(user_id, bed_num, slot_num)
        name     = G.CROPS.get(crop_e, {}).get('name', crop_e)
        bot.answer_callback_query(call.id, f"🌱 Посажено: {crop_e} {name}")

        conn2 = _get_conn()
        c2    = conn2.cursor()
        c2.execute('UPDATE users SET seeds_planted=seeds_planted+1 WHERE user_id=%s', (user_id,))
        conn2.commit()
        conn2.close()

        try:
            bot.edit_message_text(
                _slot_info_text(user_id, bed_num, slot_num, slot_row),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_slot_info_markup(bed_num, slot_num)
            )
        except: pass

    # ── Полить ──────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('grd_water_'))
    def cb_grd_water(call):
        user_id  = call.from_user.id
        parts    = call.data.split('_')
        bed_num  = int(parts[2])
        slot_num = int(parts[3])

        slot_row = _get_slot(user_id, bed_num, slot_num)
        ws, has_water = G.water_status(slot_row)
        if has_water:
            bot.answer_callback_query(call.id, "❎ Растение уже полито!")
            return

        _water_slot(user_id, bed_num, slot_num)
        slot_row = _get_slot(user_id, bed_num, slot_num)
        bot.answer_callback_query(call.id, "💧 Полито! +10% к росту на 15 мин.")
        try:
            bot.edit_message_text(
                _slot_info_text(user_id, bed_num, slot_num, slot_row),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_slot_info_markup(bed_num, slot_num)
            )
        except: pass

    # ── Удобрить — выбор ────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('grd_fert_'))
    def cb_grd_fert(call):
        user_id  = call.from_user.id
        parts    = call.data.split('_')
        bed_num  = int(parts[2])
        slot_num = int(parts[3])

        ferts = _get_fertilizers(user_id)
        slot_row = _get_slot(user_id, bed_num, slot_num)
        if slot_row and (slot_row.get('fert_growth') or slot_row.get('fert_quality') or slot_row.get('fert_yield')):
            bot.answer_callback_query(call.id, "❌ Удобрение уже применено!")
            return

        lines = []
        for fk, cnt in ferts.items():
            fd = G.FERTILIZERS.get(fk)
            if not fd: continue
            effects = []
            if fd['growth']:  effects.append(f"⏫Рост +{fd['growth']}%")
            if fd['quality']: effects.append(f"⭐Кач +{fd['quality']}%")
            if fd['yield']:   effects.append(f"📦Урожай +{fd['yield']}")
            lines.append(f"{fd['emoji']} {fd['name']} ×{cnt} — {', '.join(effects)}")

        text = (
            f"🧪 Выбери удобрение для этого растения:\n\n"
            f"📦 Список твоих удобрений:\n" + "\n".join(lines)
        )
        m = InlineKeyboardMarkup(row_width=3)
        btns = []
        for fk, cnt in ferts.items():
            fd = G.FERTILIZERS.get(fk)
            if fd:
                btns.append(InlineKeyboardButton(
                    f"{fd['emoji']}{fd['name']}",
                    callback_data=f"grd_apply_{bed_num}_{slot_num}_{fk}"
                ))
        m.add(*btns)
        m.add(InlineKeyboardButton("❌ Отмена", callback_data=f"grd_slot_{bed_num}_{slot_num}"))

        try:
            bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=m
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Применить удобрение ──────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('grd_apply_'))
    def cb_grd_apply(call):
        user_id  = call.from_user.id
        parts    = call.data.split('_')
        bed_num  = int(parts[2])
        slot_num = int(parts[3])
        fert_key = '_'.join(parts[4:])

        if not _spend_fertilizer(user_id, fert_key):
            bot.answer_callback_query(call.id, "❌ Удобрение закончилось!")
            return

        _apply_fertilizer(user_id, bed_num, slot_num, fert_key)
        fd = G.FERTILIZERS[fert_key]
        bot.answer_callback_query(call.id, f"✅ {fd['name']} применено!")

        slot_row = _get_slot(user_id, bed_num, slot_num)
        try:
            bot.edit_message_text(
                _slot_info_text(user_id, bed_num, slot_num, slot_row),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_slot_info_markup(bed_num, slot_num)
            )
        except: pass

    # ── Выкопать — подтверждение ─────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('grd_dig_'))
    def cb_grd_dig(call):
        user_id  = call.from_user.id
        parts    = call.data.split('_')
        bed_num  = int(parts[2])
        slot_num = int(parts[3])
        slot_row = _get_slot(user_id, bed_num, slot_num)
        if not slot_row or not slot_row['crop_emoji']:
            bot.answer_callback_query(call.id, "❌ Слот пустой!")
            return

        crop_e = slot_row['crop_emoji']
        name   = G.CROPS.get(crop_e, {}).get('name', crop_e)
        m = InlineKeyboardMarkup(row_width=2)
        m.add(
            InlineKeyboardButton("❌ Отмена",  callback_data=f"grd_slot_{bed_num}_{slot_num}"),
            InlineKeyboardButton("🪏 Выкопать", callback_data=f"grd_digok_{bed_num}_{slot_num}"),
        )
        try:
            bot.edit_message_text(
                f"🪏 Ты собираешься выкопать {crop_e} {name} ❎\n\nПродолжить?",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=m
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Выкопать — выполнить ─────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('grd_digok_'))
    def cb_grd_digok(call):
        user_id  = call.from_user.id
        parts    = call.data.split('_')
        bed_num  = int(parts[2])
        slot_num = int(parts[3])
        _clear_slot(user_id, bed_num, slot_num)
        bot.answer_callback_query(call.id, "🪏 Растение выкопано")
        try:
            bot.edit_message_text(
                _bed_menu_text(user_id, bed_num),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_bed_markup(user_id, bed_num)
            )
        except: pass

    # ── Собрать всё ─────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('grd_harvest_all_'))
    def cb_grd_harvest_all(call):
        user_id = call.from_user.id
        bed_num = int(call.data.split('_')[3])
        slots   = _get_slots(user_id, bed_num)
        results = []

        for s in slots:
            if s['crop_emoji'] and G.is_ready(s):
                result = _harvest_slot(user_id, bed_num, s['slot'], s)
                if result:
                    crop_e, qual, count = result
                    name = G.CROPS.get(crop_e, {}).get('name', crop_e)
                    results.append(f"+{count}{crop_e} {name} {G.quality_str(qual)}")

        if results:
            threading.Thread(
            target=_check_achievements,
            args=(user_id, call.message.chat.id),
            daemon=True
        ).start()
            bot.send_message(call.message.chat.id,
                "🧺 Собрано:\n" + "\n".join(results))
        else:
            bot.answer_callback_query(call.id, "❌ Нечего собирать!")

        try:
            bot.edit_message_text(
                _bed_menu_text(user_id, bed_num),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_bed_markup(user_id, bed_num)
            )
        except: pass
        if results:
            bot.answer_callback_query(call.id)

    # ── Магазин страница 1 (семена) ──────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'grd_shop_1')
    def cb_grd_shop1(call):
        user_id = call.from_user.id
        user    = _get_user(user_id)
        money   = user[2] if user else 0

        lines = [f"*🛒 — – - МАГАЗИН - – — 🛒*\n\n💰 Денег: 💵 {money}\n",
                 "*• – – – – – – 🛍️ ТОВАРЫ 1 🛍️ – – – – – – •*\n",
                 "— — • 🌱 • Семена • 🌱 • — —\n",
                 "_• • • Земля • • •_"]
        for em, d in G.CROPS.items():
            if d['bed'] == 1:
                lines.append(f"_🌱{em} Семена {d['name']} ×1 – 💵 {d['seed_price']}_")
        lines.append("_• • • Кусты • • •_")
        for em, d in G.CROPS.items():
            if d['bed'] == 2:
                lines.append(f"_🌿{em} Семена {d['name']} ×1 – 💵 {d['seed_price']}_")
        lines.append("_• • • Деревья • • •_")
        for em, d in G.CROPS.items():
            if d['bed'] == 3:
                lines.append(f"_🌳{em} Саженец {d['name']} ×1 – 💵 {d['seed_price']}_")
        lines.append(f"\n{G.SEP2}")

        m = InlineKeyboardMarkup(row_width=4)
        btns = []
        for em in G.CROPS:
            btns.append(InlineKeyboardButton(em, callback_data=f"grd_buy_seed_{em}"))
        m.add(*btns)
        m.add(
            InlineKeyboardButton("🔙 Назад",        callback_data="grd_main"),
            InlineKeyboardButton("⏩ След. Страница", callback_data="grd_shop_2"),
        )
        try:
            bot.edit_message_text(
                "\n".join(lines),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=m,
                parse_mode='Markdown'
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Купить семя ─────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('grd_buy_seed_'))
    def cb_grd_buy_seed(call):
        user_id  = call.from_user.id
        crop_e   = call.data[len('grd_buy_seed_'):]
        crop     = G.CROPS.get(crop_e)
        if not crop:
            bot.answer_callback_query(call.id, "❌ Ошибка!")
            return
        user  = _get_user(user_id)
        money = user[2] if user else 0
        price = crop['seed_price']
        if money < price:
            bot.answer_callback_query(call.id, f"❌ Нужно 💵{price}!")
            return
        _spend_money(user_id, price)
        _add_seed(user_id, crop_e)
        name = crop['name']
        bot.answer_callback_query(call.id, f"✅ Куплено +1 {crop_e} Семена {name}")

    # ── Магазин страница 2 (удобрения) ───────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'grd_shop_2')
    def cb_grd_shop2(call):
        user_id = call.from_user.id
        user    = _get_user(user_id)
        money   = user[2] if user else 0

        lines = [f"*🛒 — – - МАГАЗИН - – — 🛒*\n\n💰 Денег: 💵 {money}\n",
                 "*• – – – – – – 🛍️ ТОВАРЫ 2 🛍️ – – – – – – •*\n",
                 "— — • 🧪 • Удобрения • 🧪 • — —\n"]
        for fk, fd in G.FERTILIZERS.items():
            effects = []
            if fd['growth']:  effects.append(f"⏫ Скорость роста +{fd['growth']}%")
            if fd['quality']: effects.append(f"⭐ Шанс качества +{fd['quality']}%")
            if fd['yield']:   effects.append(f"📦 Урожай +{fd['yield']}")
            lines.append(f"_{fd['emoji']} {fd['name']} — 💵{fd['price']}_")
            lines.append(f"_{', '.join(effects)}_\n")
        lines.append(G.SEP2)

        m = InlineKeyboardMarkup(row_width=3)
        m.add(
            InlineKeyboardButton("⚡1️⃣", callback_data="grd_buy_fert_rostostim_1"),
            InlineKeyboardButton("⚡2️⃣", callback_data="grd_buy_fert_rostostim_2"),
            InlineKeyboardButton("⚡3️⃣", callback_data="grd_buy_fert_rostostim_3"),
            InlineKeyboardButton("⭐1️⃣", callback_data="grd_buy_fert_kachestivt_1"),
            InlineKeyboardButton("⭐2️⃣", callback_data="grd_buy_fert_kachestivt_2"),
            InlineKeyboardButton("⭐3️⃣", callback_data="grd_buy_fert_kachestivt_3"),
            InlineKeyboardButton("🌾1️⃣", callback_data="grd_buy_fert_urozhay_1"),
            InlineKeyboardButton("🌾2️⃣", callback_data="grd_buy_fert_urozhay_2"),
            InlineKeyboardButton("🌾3️⃣", callback_data="grd_buy_fert_urozhay_3"),
        )
        m.add(InlineKeyboardButton("🔙 Назад", callback_data="grd_shop_1"))

        try:
            bot.edit_message_text(
                "\n".join(lines),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=m,
                parse_mode='Markdown'
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Купить удобрение ─────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('grd_buy_fert_'))
    def cb_grd_buy_fert(call):
        user_id  = call.from_user.id
        fert_key = call.data[len('grd_buy_fert_'):]
        fd       = G.FERTILIZERS.get(fert_key)
        if not fd:
            bot.answer_callback_query(call.id, "❌ Ошибка!")
            return
        user  = _get_user(user_id)
        money = user[2] if user else 0
        if money < fd['price']:
            bot.answer_callback_query(call.id, f"❌ Нужно 💵{fd['price']}!")
            return
        _spend_money(user_id, fd['price'])
        _add_fertilizer(user_id, fert_key)
        bot.answer_callback_query(call.id, f"✅ Куплено: {fd['emoji']} {fd['name']}")

    # ── Инвентарь ───────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'grd_inventory')
    def cb_grd_inventory(call):
        user_id = call.from_user.id
        inv     = _get_inventory(user_id)
        seeds   = _get_seeds(user_id)
        ferts   = _get_fertilizers(user_id)

        # Культуры
        crop_lines = []
        for crop_e, qual, cnt in inv:
            name = G.CROPS.get(crop_e, {}).get('name', crop_e)
            crop_lines.append(f"  {crop_e} {name} {G.quality_str(qual)} ×{cnt}")

        # Семена
        seed_lines = []
        for em, cnt in seeds.items():
            name = G.CROPS.get(em, {}).get('name', em)
            seed_lines.append(f"  {em} {name} ×{cnt}")

        # Удобрения
        fert_lines = []
        for fk, cnt in ferts.items():
            fd = G.FERTILIZERS.get(fk)
            if fd:
                fert_lines.append(f"  {fd['emoji']} {fd['name']} ×{cnt}")

        text = f"— – - 📦 ИНВЕНТАРЬ 📦 - – —\n\n"
        text += "– Собранные культуры –\n"
        text += ("\n".join(crop_lines) if crop_lines else "  пусто") + "\n\n"
        text += "– Семена/Саженцы –\n"
        text += ("\n".join(seed_lines) if seed_lines else "  пусто") + "\n\n"
        # Товары из зданий
        from garden_buildings import _get_goods_inventory, RECIPES, quality_str as bq_str
        goods      = _get_goods_inventory(user_id)
        goods_lines = []
        for rk, qual, cnt in goods:
            rec = RECIPES.get(rk, {})
            goods_lines.append(f"  {rec.get('emoji','')} {rec.get('name', rk)} {bq_str(qual)} ×{cnt}")

        text += "– Удобрения –\n"
        text += ("\n".join(fert_lines) if fert_lines else "  пусто") + "\n\n"
        text += "– Товары –\n"
        text += ("\n".join(goods_lines) if goods_lines else "  пусто") + "\n\n"
        text += G.SEP2

        m = InlineKeyboardMarkup()
        m.add(InlineKeyboardButton("🔙 Назад", callback_data="grd_main"))
        try:
            bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=m
            )
        except: pass
        bot.answer_callback_query(call.id)
