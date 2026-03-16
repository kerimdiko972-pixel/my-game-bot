"""
garden_market.py — глобальный рынок фермы.
Подключение из bot.py:
    from garden_market import register_market_handlers
    register_market_handlers(bot, get_conn, get_user, add_money, spend_money)
"""
import json
import math
import threading
import random
import threading
import time as _time
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ============================================================
# КОНСТАНТЫ
# ============================================================
ITEMS_PER_PAGE   = 10
MY_SLOTS         = 5
MAX_STACK        = 10

QUALITY_MULT = {1: 1.0, 2: 1.5, 3: 2.0, 4: 3.0, 5: 5.0}

NPC_NAMES = [
    "Sitjs_51","KrutoiMo17","Не сегодня😈","Настя🎀","StasNeStas","Eggqwi_",
    "Max_Play77","Лёха_тут","Alina💫","Kaktusik23","ProstoDen","DarkFox_91",
    "Vika🌸","Roman4ik","YarikGG","Misha_777","PolinaLove","SanyaTop",
    "Артёмчик","Vlad_404","ZloyKot😼","Соня✨","Даня_Тут","CrazyNikita",
    "OlyaSun","TimkaPlay","BananBoy","Glebik_12","Милана💖","RealStepan",
    "DimaStorm","TurboEgor","Настроение_0","ShadowMark","AntonLive",
    "ПростоКирилл","Sladkaya🍓","MaximusPlay","KatyaMoon","Владосик",
    "FireDen","PandaMisha🐼","GreenTea_","SilentFox","SeregaGG","LeraSky",
    "Prosto_Ilya","LuckyArtem","DarkNastya","Kot_Begemot"
]

def quality_str(q):
    return {1:'⭐',2:'⭐⭐',3:'⭐⭐⭐',4:'⭐⭐⭐⭐',5:'⭐⭐⭐⭐⭐'}.get(q, '⭐')

SEP = "• – – – – – – – – – – – – – – – – •"

# ============================================================
# ДАННЫЕ ТОВАРОВ (цены и отображение)
# ============================================================
# Импортируем из garden и garden_buildings при использовании

def _base_price(item_key):
    """Базовая цена товара."""
    try:
        import garden as G
        if item_key in G.CROPS:
            return G.CROPS[item_key]['price']
    except: pass
    try:
        from garden_buildings import RECIPES
        if item_key in RECIPES:
            return RECIPES[item_key]['price']
    except: pass
    return 100

def _item_display(item_key):
    """Отображаемое имя товара."""
    try:
        import garden as G
        if item_key in G.CROPS:
            return f"{item_key} {G.CROPS[item_key]['name']}"
    except: pass
    try:
        from garden_buildings import RECIPES
        if item_key in RECIPES:
            r = RECIPES[item_key]
            return f"{r['emoji']} {r['name']}"
    except: pass
    return item_key

def _calc_price(item_key, quality, count, finished_at=None):
    base = _base_price(item_key) * count * QUALITY_MULT.get(quality, 1.0)
    if item_key in ('wine', 'cider') and finished_at:
        try:
            from garden_buildings import aging_mult
            base = base * aging_mult(finished_at)
        except: pass
    return int(base)

# ============================================================
# DB
# ============================================================
_get_conn    = None
_get_user    = None
_add_money   = None
_spend_money = None

def _init_market_db():
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS market_listings (
        id           SERIAL PRIMARY KEY,
        seller_id    BIGINT,
        seller_name  TEXT,
        item_key     TEXT,
        quality      INTEGER,
        count        INTEGER,
        price        INTEGER,
        listed_at    TEXT,
        slot_num     INTEGER,
        auto_buy_at  TEXT DEFAULT NULL
    )''')
    try:
        c.execute("ALTER TABLE market_listings ADD COLUMN IF NOT EXISTS auto_buy_at TEXT DEFAULT NULL")
        conn.commit()
    except: conn.rollback()
    conn.commit()
    conn.close()

def _get_listings_page(user_id, page):
    """Возвращает (listings, total_pages)."""
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT COUNT(*) FROM market_listings WHERE seller_id != %s', (user_id,))
    total = c.fetchone()[0]
    total_pages = max(1, math.ceil(total / ITEMS_PER_PAGE))
    offset = (page - 1) * ITEMS_PER_PAGE
    c.execute('''SELECT id, seller_id, seller_name, item_key, quality, count, price
                 FROM market_listings WHERE seller_id != %s
                 ORDER BY listed_at DESC LIMIT %s OFFSET %s''',
              (user_id, ITEMS_PER_PAGE, offset))
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'seller_id': r[1], 'seller_name': r[2],
             'item_key': r[3], 'quality': r[4], 'count': r[5], 'price': r[6]}
            for r in rows], total_pages

def _get_my_listings(user_id):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT id, item_key, quality, count, price, slot_num FROM market_listings WHERE seller_id=%s ORDER BY slot_num',
              (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'item_key': r[1], 'quality': r[2],
             'count': r[3], 'price': r[4], 'slot_num': r[5]} for r in rows]

def _free_slot(user_id):
    my = _get_my_listings(user_id)
    used = {l['slot_num'] for l in my}
    for s in range(1, MY_SLOTS + 1):
        if s not in used:
            return s
    return None

def _add_listing(user_id, seller_name, item_key, quality, count, price, slot_num):
    delay    = random.randint(30, 3600)
    buy_time = (datetime.now() + timedelta(seconds=delay)).isoformat()
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('''INSERT INTO market_listings
                 (seller_id, seller_name, item_key, quality, count, price, listed_at, slot_num, auto_buy_at)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
              (user_id, seller_name, item_key, quality, count, price,
               datetime.now().isoformat(), slot_num, buy_time))
    conn.commit()
    conn.close()

def _remove_listing(listing_id):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('DELETE FROM market_listings WHERE id=%s', (listing_id,))
    conn.commit()
    conn.close()

def _buy_listing(listing_id, buyer_id):
    """Атомарная покупка. Возвращает listing dict или None."""
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT * FROM market_listings WHERE id=%s', (listing_id,))
    r = c.fetchone()
    if not r:
        conn.close()
        return None
    listing = {'id': r[0], 'seller_id': r[1], 'seller_name': r[2],
               'item_key': r[3], 'quality': r[4], 'count': r[5], 'price': r[6]}
    if listing['seller_id'] == buyer_id:
        conn.close()
        return None
    c.execute('DELETE FROM market_listings WHERE id=%s', (listing_id,))
    conn.commit()
    conn.close()
    return listing

def _add_to_inventory(user_id, item_key, quality, count):
    conn = _get_conn()
    c    = conn.cursor()
    try:
        import garden as G
        if item_key in G.CROPS:
            c.execute('''INSERT INTO garden_inventory (user_id, crop_emoji, quality, count) VALUES (%s,%s,%s,%s)
                         ON CONFLICT (user_id, crop_emoji, quality) DO UPDATE SET count=garden_inventory.count+%s''',
                      (user_id, item_key, quality, count, count))
            conn.commit()
            conn.close()
            return
    except: pass
    c.execute('''INSERT INTO goods_inventory (user_id, recipe_key, quality, count) VALUES (%s,%s,%s,%s)
                 ON CONFLICT (user_id, recipe_key, quality) DO UPDATE SET count=goods_inventory.count+%s''',
              (user_id, item_key, quality, count, count))
    conn.commit()
    conn.close()

def _get_finished_at(user_id, item_key, quality):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT finished_at FROM goods_inventory WHERE user_id=%s AND recipe_key=%s AND quality=%s',
              (user_id, item_key, quality))
    r = c.fetchone()
    conn.close()
    return r[0] if r and r[0] else None

def _spend_item(user_id, item_key, quality, count):
    conn = _get_conn()
    c    = conn.cursor()
    try:
        import garden as G
        if item_key in G.CROPS:
            c.execute('''UPDATE garden_inventory SET count=count-%s
                         WHERE user_id=%s AND crop_emoji=%s AND quality=%s AND count>=%s''',
                      (count, user_id, item_key, quality, count))
            updated = c.rowcount
            conn.commit()
            conn.close()
            return updated > 0
    except: pass
    c.execute('''UPDATE goods_inventory SET count=count-%s
                 WHERE user_id=%s AND recipe_key=%s AND quality=%s AND count>=%s''',
              (count, user_id, item_key, quality, count))
    updated = c.rowcount
    conn.commit()
    conn.close()
    return updated > 0

def _get_inventory_for_market(user_id):
    """Возвращает {item_key: [(quality, count), ...]}."""
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT crop_emoji, quality, count FROM garden_inventory WHERE user_id=%s AND count>0', (user_id,))
    crops = c.fetchall()
    c.execute('SELECT recipe_key, quality, count FROM goods_inventory WHERE user_id=%s AND count>0', (user_id,))
    goods = c.fetchall()
    conn.close()
    result = {}
    for k, q, cnt in crops:
        result.setdefault(k, []).append((q, cnt))
    for k, q, cnt in goods:
        result.setdefault(k, []).append((q, cnt))
    return result

# ============================================================
# СЕССИИ ВЫСТАВЛЕНИЯ ТОВАРА
# ============================================================
_market_sessions = {}
_session_lock    = threading.Lock()

# ============================================================
# ТЕКСТЫ И РАЗМЕТКИ
# ============================================================

def _market_text(user_id, listings, page, total_pages):
    user  = _get_user(user_id)
    money = user[2] if user else 0
    exp   = user[3] if user else 0

    lines = [f"— – - 🏪 РЫНОК 🏪 - – —\n",
             f"Денег: 💵 {money:,}",
             f"Опыта: ⭐ {exp:,}\n",
             SEP,
             f"\nСтраница {page} / {total_pages}\n"]

    if not listings:
        lines.append("_Товаров пока нет_")
    else:
        for l in listings:
            lines.append(
                f"{_item_display(l['item_key'])} {quality_str(l['quality'])} ×{l['count']}"
                f" — 💵{l['price']:,} — 👤{l['seller_name']}"
            )
    lines.append(f"\n{SEP}")
    return "\n".join(lines)

def _market_markup(listings, page, total_pages):
    m = InlineKeyboardMarkup(row_width=1)
    for l in listings:
        m.add(InlineKeyboardButton(
            f"{_item_display(l['item_key'])} {quality_str(l['quality'])} ×{l['count']}",
            callback_data=f"mkt_buy_{l['id']}_p{page}"
        ))
    nav = [
        InlineKeyboardButton("🏪 Мои товары",  callback_data="mkt_my"),
        InlineKeyboardButton("📦 Инвентарь",   callback_data="grd_inventory"),
    ]
    nav2 = [InlineKeyboardButton("🔙 Назад", callback_data="grd_main")]
    if page > 1:
        nav2.append(InlineKeyboardButton("⏪ Прошлая", callback_data=f"mkt_page_{page-1}"))
    if page < total_pages:
        nav2.append(InlineKeyboardButton("⏩ Следующая", callback_data=f"mkt_page_{page+1}"))
    m.add(*nav)
    m.add(*nav2)
    return m

def _my_listings_text(user_id):
    user  = _get_user(user_id)
    money = user[2] if user else 0
    my    = _get_my_listings(user_id)
    used  = {l['slot_num']: l for l in my}

    lines = [f"— – - 🏪 МОИ ТОВАРЫ 🏪 - – —\n",
             f"💰 Денег: 💵 {money:,}\n"]
    for s in range(1, MY_SLOTS + 1):
        lines.append(f"• – – – – – – – – – – – – – – •")
        if s in used:
            l = used[s]
            lines.append(
                f"{s}️⃣ {_item_display(l['item_key'])} {quality_str(l['quality'])} ×{l['count']}"
                f"\n💵 {l['price']:,}"
            )
        else:
            lines.append(f"{s}️⃣ [Пусто]")
    lines.append("• – – – – – – – – – – – – – – •")
    return "\n".join(lines)

def _my_listings_markup(user_id):
    m  = InlineKeyboardMarkup(row_width=2)
    my = _get_my_listings(user_id)
    m.add(InlineKeyboardButton("➕ Добавить", callback_data="mkt_add_type"))
    if my:
        m.add(InlineKeyboardButton("❎ Убрать", callback_data="mkt_remove_pick"))
    m.add(InlineKeyboardButton("🔙 Назад", callback_data="mkt_page_1"))
    return m

# ============================================================
# РЕГИСТРАЦИЯ ХЭНДЛЕРОВ
# ============================================================

def register_market_handlers(bot, get_conn, get_user, add_money, spend_money):
    global _get_conn, _get_user, _add_money, _spend_money
    _get_conn    = get_conn
    _get_user    = get_user
    _add_money   = add_money
    _spend_money = spend_money
    _init_market_db()

    def _show_market(call, page=1):
        user_id = call.from_user.id
        listings, total_pages = _get_listings_page(user_id, page)
        try:
            bot.edit_message_text(
                _market_text(user_id, listings, page, total_pages),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_market_markup(listings, page, total_pages)
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Открыть рынок ───────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'grd_market')
    def cb_grd_market(call):
        _show_market(call, 1)

    # ── Страница рынка ──────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('mkt_page_'))
    def cb_mkt_page(call):
        page = int(call.data[len('mkt_page_'):])
        _show_market(call, page)

    # ── Купить товар ────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('mkt_buy_'))
    def cb_mkt_buy(call):
        user_id = call.from_user.id
        parts   = call.data[len('mkt_buy_'):].split('_p')
        lid     = int(parts[0])
        page    = int(parts[1]) if len(parts) > 1 else 1

        user  = _get_user(user_id)
        money = user[2] if user else 0

        # Проверяем листинг
        conn = _get_conn()
        c    = conn.cursor()
        c.execute('SELECT price, seller_id FROM market_listings WHERE id=%s', (lid,))
        r = c.fetchone()
        conn.close()

        if not r:
            bot.answer_callback_query(call.id, "❌ Товар уже куплен!", show_alert=True)
            _show_market(call, page)
            return
        price, seller_id = r
        if seller_id == user_id:
            bot.answer_callback_query(call.id, "❌ Нельзя купить свой товар!")
            return
        if money < price:
            bot.answer_callback_query(call.id, f"❌ Нужно 💵{price:,}!", show_alert=True)
            return

        listing = _buy_listing(lid, user_id)
        if not listing:
            bot.answer_callback_query(call.id, "❌ Товар уже куплен!", show_alert=True)
            _show_market(call, page)
            return

        _spend_money(user_id, listing['price'])
        _add_money(listing['seller_id'], listing['price'])
        _add_to_inventory(user_id, listing['item_key'], listing['quality'], listing['count'])

        buyer_user  = _get_user(user_id)
        buyer_name  = buyer_user[1] if buyer_user else str(user_id)
        item_text   = f"{_item_display(listing['item_key'])} {quality_str(listing['quality'])} ×{listing['count']}"

        # Уведомление продавцу
        try:
            seller_user = _get_user(listing['seller_id'])
            if seller_user and len(seller_user) > 22 and seller_user[22]:
                bot.send_message(
                    seller_user[22],
                    f"💰 {buyer_name} купил у тебя:\n\n"
                    f"{item_text}\n\n"
                    f"Получено: +💵{listing['price']:,}"
                )
        except: pass

        # Уведомление покупателю
        bot.send_message(
            call.message.chat.id,
            f"🎉 Покупка успешна!\n\nВы купили:\n{item_text}\n\nПотрачено: 💵{listing['price']:,}"
        )
        bot.answer_callback_query(call.id)
        _show_market(call, page)

    # ── Мои товары ──────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'mkt_my')
    def cb_mkt_my(call):
        user_id = call.from_user.id
        try:
            bot.edit_message_text(
                _my_listings_text(user_id),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_my_listings_markup(user_id)
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Добавить товар — выбор типа ─────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'mkt_add_type')
    def cb_mkt_add_type(call):
        user_id = call.from_user.id
        slot    = _free_slot(user_id)
        if not slot:
            bot.answer_callback_query(call.id, "❌ Все слоты заняты!", show_alert=True)
            return
        m = InlineKeyboardMarkup(row_width=2)
        m.add(
            InlineKeyboardButton("🌾 Урожай", callback_data="mkt_add_crops_1"),
            InlineKeyboardButton("🍲 Еда",    callback_data="mkt_add_food_1"),
        )
        m.add(InlineKeyboardButton("🔙 Назад", callback_data="mkt_my"))
        try:
            bot.edit_message_text(
                "Выбери тип товара для продажи:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=m
            )
        except: pass
        bot.answer_callback_query(call.id)

    def _show_add_items(call, item_type, page):
        user_id = call.from_user.id
        inv     = _get_inventory_for_market(user_id)

        try:
            import garden as G
            from garden_buildings import RECIPES
        except: pass

        # Фильтруем по типу
        items = []
        for item_key, variants in inv.items():
            is_crop = item_key in G.CROPS
            is_food = item_key in RECIPES
            if item_type == 'crops' and not is_crop: continue
            if item_type == 'food'  and not is_food:  continue
            for qual, cnt in variants:
                if cnt > 0:
                    items.append((item_key, qual, cnt))

        items_per_page = 8
        total_pages    = max(1, math.ceil(len(items) / items_per_page))
        start          = (page - 1) * items_per_page
        page_items     = items[start:start + items_per_page]

        m = InlineKeyboardMarkup(row_width=1)
        for item_key, qual, cnt in page_items:
            show_cnt = min(cnt, MAX_STACK)
            m.add(InlineKeyboardButton(
                f"{_item_display(item_key)} {quality_str(qual)} ×{show_cnt}",
                callback_data=f"mkt_pick_{item_key}_{qual}_{show_cnt}"
            ))

        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton("⏪", callback_data=f"mkt_add_{item_type}_{page-1}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton("⏩", callback_data=f"mkt_add_{item_type}_{page+1}"))
        if nav:
            m.add(*nav)
        m.add(InlineKeyboardButton("🔙 Назад", callback_data="mkt_add_type"))

        try:
            bot.edit_message_text(
                f"Выбери товар для продажи (страница {page}/{total_pages}):",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=m
            )
        except: pass
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('mkt_add_crops_'))
    def cb_mkt_add_crops(call):
        page = int(call.data[len('mkt_add_crops_'):])
        _show_add_items(call, 'crops', page)

    @bot.callback_query_handler(func=lambda c: c.data.startswith('mkt_add_food_'))
    def cb_mkt_add_food(call):
        page = int(call.data[len('mkt_add_food_'):])
        _show_add_items(call, 'food', page)

    # ── Выбрать товар для продажи ───────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('mkt_pick_'))
    def cb_mkt_pick(call):
        user_id = call.from_user.id
        data    = call.data[len('mkt_pick_'):]
        parts   = data.split('_')
        quality  = int(parts[-2])
        max_cnt  = int(parts[-1])
        item_key = '_'.join(parts[:-2])

        rec_price = _calc_price(item_key, quality, 1)

        fat = _get_finished_at(user_id, item_key, quality) if item_key in ('wine', 'cider') else None

        with _session_lock:
            _market_sessions[user_id] = {
                'item_key':    item_key,
                'quality':     quality,
                'max_count':   max_cnt,
                'count':       1,
                'custom_price': None,
                'state':       'picking',
                'finished_at': fat,
            }

        _show_pick_menu(bot, call, user_id)
        bot.answer_callback_query(call.id)


    def _show_pick_menu(bot, call, user_id):
        with _session_lock:
            s = _market_sessions.get(user_id)
        if not s: return

        item_key  = s['item_key']
        quality   = s['quality']
        count     = s['count']
        max_count = s['max_count']
        finished_at = s.get('finished_at')
        rec_price   = _calc_price(item_key, quality, count, finished_at)
        item_text = f"{_item_display(item_key)} {quality_str(quality)} ×{count}"

        text = (
            f"🏪 Выбрано на продажу: {item_text}\n\n"
            f"📝 Введите цену сообщением:\n"
            f"(💰 Рекомендованная цена: 💵 {rec_price:,})\n"
            f"Допустимо: от 💵{int(rec_price*0.6):,} до 💵{int(rec_price*1.4):,}"
        )
        m = InlineKeyboardMarkup(row_width=1)
        if count < max_count:
            m.add(InlineKeyboardButton(
                f"➕ {_item_display(item_key)} {quality_str(quality)} ×{count + 1}",
                callback_data=f"mkt_addone_{item_key}_{quality}_{max_count}"
            ))
        m.add(InlineKeyboardButton("❎ Отмена", callback_data="mkt_cancel_pick"))
        try:
            bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=m
            )
        except: pass

    # ── Подтвердить выставление ─────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'mkt_confirm')
    def cb_mkt_confirm(call):
        user_id = call.from_user.id
        with _session_lock:
            session = _market_sessions.pop(user_id, None)
        if not session:
            bot.answer_callback_query(call.id, "❌ Сессия истекла!")
            return

        slot = _free_slot(user_id)
        if not slot:
            bot.answer_callback_query(call.id, "❌ Все слоты заняты!", show_alert=True)
            return

        if not _spend_item(user_id, session['item_key'], session['quality'], session['count']):
            bot.answer_callback_query(call.id, "❌ Товара больше нет в инвентаре!")
            return

        user        = _get_user(user_id)
        seller_name = user[1] if user else str(user_id)
        price = session.get('custom_price') or session.get('price', 0)
        _add_listing(user_id, seller_name, session['item_key'],
                     session['quality'], session['count'], price, slot)

        bot.answer_callback_query(call.id, "✅ Товар выставлен на рынок!")
        # Возвращаем в мои товары
        try:
            bot.edit_message_text(
                _my_listings_text(user_id),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_my_listings_markup(user_id)
            )
        except: pass

    @bot.callback_query_handler(func=lambda c: c.data.startswith('mkt_addone_'))
    def cb_mkt_addone(call):
        user_id = call.from_user.id
        data    = call.data[len('mkt_addone_'):]
        parts   = data.split('_')
        max_cnt  = int(parts[-1])
        quality  = int(parts[-2])
        item_key = '_'.join(parts[:-2])

        with _session_lock:
            s = _market_sessions.get(user_id)
            if s and s['count'] < max_cnt:
                s['count'] += 1

        _show_pick_menu(bot, call, user_id)
        bot.answer_callback_query(call.id)


    @bot.callback_query_handler(func=lambda c: c.data == 'mkt_cancel_pick')
    def cb_mkt_cancel_pick(call):
        user_id = call.from_user.id
        with _session_lock:
            _market_sessions.pop(user_id, None)
        try:
            bot.edit_message_text(
                _my_listings_text(user_id),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_my_listings_markup(user_id)
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Убрать товар — выбор ────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'mkt_remove_pick')
    def cb_mkt_remove_pick(call):
        user_id = call.from_user.id
        my      = _get_my_listings(user_id)
        if not my:
            bot.answer_callback_query(call.id, "❌ Нет товаров!")
            return
        m = InlineKeyboardMarkup(row_width=1)
        for l in my:
            m.add(InlineKeyboardButton(
                f"❎ {l['slot_num']}️⃣ {_item_display(l['item_key'])} {quality_str(l['quality'])} ×{l['count']}",
                callback_data=f"mkt_remove_{l['id']}"
            ))
        m.add(InlineKeyboardButton("🔙 Назад", callback_data="mkt_my"))
        try:
            bot.edit_message_text(
                "Выбери товар который хочешь снять с продажи:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=m
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Убрать конкретный товар ─────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('mkt_remove_'))
    def cb_mkt_remove(call):
        user_id = call.from_user.id
        lid     = int(call.data[len('mkt_remove_'):])

        conn = _get_conn()
        c    = conn.cursor()
        c.execute('SELECT item_key, quality, count, seller_id FROM market_listings WHERE id=%s', (lid,))
        r = c.fetchone()
        conn.close()

        if not r or r[3] != user_id:
            bot.answer_callback_query(call.id, "❌ Ошибка!")
            return

        _remove_listing(lid)
        _add_to_inventory(user_id, r[0], r[1], r[2])
        bot.answer_callback_query(call.id, "✅ Товар снят с продажи и возвращён в инвентарь!")

        try:
            bot.edit_message_text(
                _my_listings_text(user_id),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_my_listings_markup(user_id)
            )
        except: pass
            
    @bot.message_handler(func=lambda message: (
        message.from_user.id in _market_sessions and
        _market_sessions[message.from_user.id].get('state') == 'picking'
    ))
    def handle_market_price_input(message):
        user_id = message.from_user.id
        with _session_lock:
            s = _market_sessions.get(user_id)
        if not s: return

        try:
            price = int(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "❌ Введи целое число!")
            return

        rec_price = _calc_price(s['item_key'], s['quality'], s['count'])
        min_price = int(rec_price * 0.6)
        max_price = int(rec_price * 1.4)

        if price < min_price or price > max_price:
            bot.send_message(
                message.chat.id,
                f"❌ Цена должна быть от 💵{min_price:,} до 💵{max_price:,}!"
            )
            return

        with _session_lock:
            s['custom_price'] = price
            s['state']        = 'confirming'

        item_text = f"{_item_display(s['item_key'])} {quality_str(s['quality'])} ×{s['count']}"
        m = InlineKeyboardMarkup(row_width=1)
        m.add(
            InlineKeyboardButton("✅ Разместить", callback_data="mkt_confirm"),
            InlineKeyboardButton("❎ Отмена",     callback_data="mkt_cancel_pick"),
        )
        bot.send_message(
            message.chat.id,
            f"🏪 Выбрано на продажу: {item_text}\n\n"
            f"💰 Цена: 💵 {price:,}\n\n"
            f"Подтвердить?",
            reply_markup=m
        )

def npc_buyer_loop(bot, get_conn_fn, get_user_fn, add_money_fn):
    while True:
        try:
            conn = get_conn_fn()
            c    = conn.cursor()
            now  = datetime.now().isoformat()
            c.execute('''SELECT id, seller_id, item_key, quality, count, price
                         FROM market_listings WHERE auto_buy_at <= %s''', (now,))
            rows = c.fetchall()
            conn.close()

            for lid, seller_id, item_key, quality, count, price in rows:
                conn2 = get_conn_fn()
                c2    = conn2.cursor()
                c2.execute('DELETE FROM market_listings WHERE id=%s', (lid,))
                deleted = c2.rowcount
                conn2.commit()
                conn2.close()

                if deleted == 0:
                    continue

                add_money_fn(seller_id, price)
                npc_name  = random.choice(NPC_NAMES)
                item_text = f"{_item_display(item_key)} {quality_str(quality)} ×{count}"

                try:
                    seller = get_user_fn(seller_id)
                    if seller and len(seller) > 22 and seller[22]:
                        bot.send_message(
                            seller[22],
                            f"💰 {npc_name} купил у тебя:\n\n"
                            f"{item_text}\n\n"
                            f"Получено: +💵{price:,}"
                        )
                except: pass

        except Exception as e:
            print(f"NPC buyer error: {e}")
        _time.sleep(15)
