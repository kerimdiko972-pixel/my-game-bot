"""
garden_quests.py — задания города для огорода.
Подключение из bot.py:
    from garden_quests import register_quest_handlers
    register_quest_handlers(bot, get_conn, get_user, add_exp, add_money, spend_money)
"""
import json
import random
import threading
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ============================================================
# ДАННЫЕ ЗАДАНИЙ
# ============================================================
# Формат: (npc_emoji, npc_name, quote, requirements, money, exp)
# requirements: {item_key: count}  item_key = эмодзи культуры или recipe_key блюда

QUESTS_COMMON = [
    # культуры
    ('👩🏻‍🍳', 'Салли — шеф-кондитер',
     '«Господи, у меня завтра праздник! Нужна морковь для глазури.»',
     {'🥕': 5}, 500, 300),
    ('👨🏻‍🌾', 'Фермер Джо',
     '«Поможешь на поле? Возьми свежего картофеля — дядям на обед»',
     {'🥔': 8}, 700, 320),
    ('🧑🏻‍🔬', 'Профессор Альберт',
     '«Исследую влияние фруктов на память — нужны яблоки и клубника.»',
     {'🍎': 4, '🍓': 3}, 1200, 650),
    ('👨🏻‍🎨', 'Артьёр Реми',
     '«Мне нужны яркие ягоды для фестивального торта — клубника и вишня!»',
     {'🍓': 4, '🍒': 2}, 1800, 700),
    ('👩🏻‍🍳', 'Повар Нора',
     '«Готовлю суп для приюта — принесёшь картошку и морковку?»',
     {'🥔': 3, '🥕': 3}, 600, 280),
    ('🧑🏻‍🍳', 'Кондитер Мила',
     '«Пеку торт с ананасом — принеси 2 ананаса, пожалуйста.»',
     {'🍍': 2}, 2600, 900),
    ('👨🏻‍🏫', 'Учитель Оскар',
     '«Школьный пикник: нужно кукурузных зерен — для попкорна!»',
     {'🌽': 3}, 1200, 450),
    ('👩🏻‍🌾', 'Бетти — садовница',
     '«Мой сад несёт плоды — нужны яблоки и апельсины для компота.»',
     {'🍎': 4, '🍊': 3}, 1700, 720),
    ('👩🏻‍💼', 'Клер — менеджер кафе',
     '«В меню появится новый салат — требуются помидоры и огурцы.»',
     {'🍅': 6, '🥒': 4}, 1600, 520),
    ('👷🏻', 'Строитель Майк',
     '«После трудового дня строителям нужен маринад — огурцы и помидоры.»',
     {'🥒': 6, '🍅': 4}, 1900, 600),
    ('👩🏻‍🎨', 'Дизайнер Лия',
     '«Нужны ягоды для съёмки — смешанный набор клубники и винограда.»',
     {'🍓': 3, '🍇': 2}, 1900, 700),
    ('👨🏻‍🍳', 'Шеф-повар Бренн',
     '«Готовлю фирменное блюдо — нужно баклажан и перец.»',
     {'🍆': 2, '🫑': 1}, 1300, 540),
    ('👨🏻‍🌾', 'Фермер Рик',
     '«Урожай дынь вышел отлично — поделись 2 дынями для соседей.»',
     {'🍈': 2}, 1400, 520),
    ('👷🏻', 'Строитель Майк',
     '«Завтра у нас корпоратив — хочешь поставить немного маринада?»',
     {'🍅': 5, '🥒': 3}, 1500, 500),
    ('👨🏻‍🎨', 'Художник Тарек',
     '«Для картины нужны яркие арбузы и ананасы.»',
     {'🍉': 1, '🍍': 1}, 2000, 700),
    ('🤹🏻', 'Факир Рахим',
     '«Шоу на площади — спасите попкорном и картошкой фри!»',
     {'🍿': 2, '🍟': 3}, 1600, 500),
    ('🧑🏻‍🔬', 'Исследователь Нова',
     '«Проверяю свойства винограда — привези мне несколько гроздей.»',
     {'🍇': 5}, 2800, 900),
    ('👩🏻‍🌾', 'Агнес — хозяюшка',
     '«У меня гости — нужны яблоки, апельсины и вишня.»',
     {'🍎': 3, '🍊': 3, '🍒': 2}, 3200, 1200),
    ('👩🏻‍🍳', 'Пекарь Оли',
     '«Нужны клубника и яблоки для пирога.»',
     {'🍓': 3, '🍎': 2}, 1600, 560),
    ('🧓🏼', 'Добрая бабушка',
     '«Внучки приедут… Хочу сварить им борщ.»',
     {'🥔': 2, '🥕': 2, '🍅': 2}, 900, 350),
    ('👩🏻‍🍳', 'Доктор Лин',
     '«Нужна здоровая еда для пациентов.»',
     {'🥬': 3, '🥕': 2}, 700, 300),
    ('👩🏽‍🌾', 'Фермерша Ана',
     '«Нужно немного урожая на рынок.»',
     {'🍅': 4, '🥒': 4, '🫑': 2}, 1700, 600),
    ('👩🏻‍🍳', 'Кондитер Элла',
     '«Пеку фруктовый пирог.»',
     {'🍎': 3, '🍓': 3}, 1600, 520),
    ('👨🏻‍🍳', 'Повар Рамир',
     '«Хочу приготовить острый суп.»',
     {'🌶️': 2, '🍅': 2, '🫑': 1}, 1200, 480),
    ('👩🏽‍🌾', 'Фермерка Луна',
     '«Помоги собрать урожай.»',
     {'🥔': 5, '🌽': 2, '🍅': 3}, 2000, 650),
    # блюда из кухни
    ('👮🏻', 'Капитан Маркус',
     '«Ночной патруль голоден — нужно пару порций картошки фри.»',
     {'fried_potato': 2}, 850, 420),
    ('🧑🏻‍🏭', 'Мастер Грегор',
     '«После смены рабочие любят сладкое — привезёшь баночку варенья?»',
     {'jam_straw': 1}, 1600, 820),
    ('👨🏻‍🎤', 'Музыкант Лео',
     '«После концерта нужна тарелка острого супа — для души!»',
     {'soup_spicy': 1}, 1100, 480),
    ('👮🏻‍♀️', 'Инспектор Ли',
     '«Пострадали от жары. Можно пару бутылочек сидра?»',
     {'cider': 1}, 4000, 1100),
    ('🧑🏻‍⚕️', 'Доктор Эмма',
     '«После долгой смены врачам нужен лёгкий салат.»',
     {'salad_veg': 3}, 900, 360),
    ('👨🏻‍🔧', 'Механик Тор',
     '«Завтра у нас корпоратив — хочешь поставить пару банок маринада?»',
     {'pickled_cuc': 2}, 1150, 480),
    ('🧑🏻‍🚒', 'Пожарный Сэм',
     '«На выезде ребятам нужен горшок фермерского супа — согреет!»',
     {'soup_farm': 2}, 1400, 620),
    ('👩🏻‍💼', 'Торговка Мэри',
     '«Клиенты просят компот ассорти — очень нужен!»',
     {'compote_mix': 1}, 3800, 1000),
    ('👩🏻‍🍳', 'Кондитер Зоя',
     '«Мне нужен тропический джем для специального заказа.»',
     {'jam_tropical': 1}, 7500, 1600),
    ('👩🏻‍💼', 'Мадам Эвелин',
     '«Устрою чаепитие — нужно маринованная морковь и капустный салат.»',
     {'pickled_car': 2, 'salad_cabbage': 1}, 1400, 520),
    ('👨🏻‍🍳', 'Шеф-лаборант Рен',
     '«Эксперимент с тропическим вкусом: манго + ананас в джеме.»',
     {'jam_tropical': 1}, 7800, 1700),
    ('👮🏻‍♂️', 'Сержант Ким',
     '«Нужна теплая еда полицейским на посту — борщ в двоём объёме.»',
     {'soup_borsch': 2}, 1600, 780),
    ('🧑🏻‍🔬', 'Исследователь Нова',
     '«Проверяю свойства компота — привези.»',
     {'compote_apple': 1}, 2400, 750),
    ('👩🏻‍⚕️', 'Мира — фитотерапевт',
     '«Готовлю лечебный компот из яблок и клубники для пациентов.»',
     {'compote_apple': 1, 'compote_straw': 1}, 3500, 1000),
    ('👨🏻‍💼', 'Граф Гилен',
     '«На приёме хочу подать лучшее вино — принеси бутылочку винтажа.»',
     {'wine': 1}, 12000, 2500),
    ('👨🏻‍🎤', 'Кроу — уличный артист',
     '«Нужны сладкие угощения — варенье и маринады.»',
     {'jam_straw': 1, 'pickled_tom': 1}, 4000, 1300),
    ('🧑🏻‍🔧', 'Инженер Люк',
     '«Провожу опыты с фруктовым спиртом — привезите пару порций ликёра.»',
     {'liqueur': 1}, 11000, 2000),
    ('👨🏻‍🏭', 'Капитан дока Велл',
     '«Команда требует сидра и пива для праздника на причале.»',
     {'cider': 1, 'beer': 2}, 4500, 1100),
    ('👩🏻‍🍳', 'Повар Лили',
     '«Сегодня жарко, а гости хотят что-нибудь лёгкое и сладкое.»',
     {'salad_fruit': 1}, 1800, 650),
    ('👨🏻‍🎨', 'Художник Арман',
     '«Я пишу летний натюрморт — фруктовый салат был бы идеален.»',
     {'salad_fruit': 1, '🍓': 2}, 2100, 720),
    ('👩🏻‍💼', 'Мадам Эвелин',
     '«Сегодня у меня чаепитие с подругами. Нужно что-то сладкое.»',
     {'jam_melon': 1}, 2600, 850),
    ('🧑🏻‍🍳', 'Шеф Диего',
     '«Экспериментирую с новыми вкусами.»',
     {'jam_melon': 1, '🍈': 1}, 3000, 950),
    ('👨🏻‍🚒', 'Пожарный Том',
     '«После тренировки команда ужасно хочет пить.»',
     {'juice_watermelon': 2}, 2200, 700),
    ('👩🏽‍🌾', 'Фермерка Марта',
     '«Собираем урожай и отмечаем праздник поля.»',
     {'juice_watermelon': 1, '🍉': 1}, 2000, 650),
    ('👨🏻‍🎤', 'Музыкант Рико',
     '«Перед концертом мне нужно что-нибудь лёгкое.»',
     {'salad_fruit': 1, 'juice_watermelon': 1}, 2600, 900),
    ('🧙🏻‍♂️', 'Волшебник Талмор',
     '«Я создаю новое сладкое заклинание.»',
     {'jam_melon': 1, '🍓': 2}, 3400, 1100),
    ('👩🏻‍🏫', 'Сауле',
     '«Сегодня у детей спортивный день.»',
     {'juice_watermelon': 1, '🍎': 2}, 1700, 600),
    ('🧒🏼', 'Жирдяй',
     '«Я нашёл идеальный десерт…»',
     {'salad_fruit': 1, 'jam_melon': 1}, 2400, 780),
    ('👩🏻‍🏫', 'Сауле',
     '«Завтра контрольная… Принеси немного еды для урока.»',
     {'salad_summer': 1, '🍎': 2}, 1200, 500),
    ('👩🏻‍🏫', 'Сауле',
     '«Сегодня урок биологии.»',
     {'🥕': 3, '🥬': 2, '🍅': 2}, 900, 420),
    ('👩🏻‍🏫', 'Сауле',
     '«Готовим школьный обед. Нужно что-то горячее.»',
     {'soup_veg': 1, 'fried_potato': 1}, 1500, 600),
    ('🧒🏼', 'Жирдяй',
     '«Я ОЧЕНЬ голодный…»',
     {'fried_potato': 2}, 800, 250),
    ('🧒🏼', 'Жирдяй',
     '«Хочу сладкое… мама не разрешает, помоги!»',
     {'jam_straw': 1}, 1500, 500),
    ('🧒🏼', 'Жирдяй',
     '«А можно всё сразу? Я сегодня очень голодный…»',
     {'fried_potato': 1, 'popcorn': 1, 'compote_straw': 1}, 2000, 700),
    ('🧓🏼', 'Добрая бабушка',
     '«Я на зиму делаю соленья.»',
     {'pickled_cuc': 1, 'pickled_cab': 1}, 1200, 420),
    ('🧓🏼', 'Добрая бабушка',
     '«Сварю компот для соседей.»',
     {'compote_apple': 1}, 2400, 650),
    ('👩🏻‍🍳', 'Шеф Мари',
     '«Сегодня банкет. Нужны салаты.»',
     {'salad_veg': 1, 'salad_spicy': 1}, 1700, 620),
    ('👩🏻‍⚕️', 'Медсестра Лара',
     '«Нужен компот для больницы.»',
     {'compote_straw': 1}, 2300, 650),
    ('👩🏻‍🍳', 'Повар Софи',
     '«Готовлю праздничный ужин.»',
     {'fried_egg': 1, 'salad_veg': 1}, 2000, 700),
]

QUESTS_RARE = [
    ('🤴🏻', 'Король Алекс',
     '«Сегодня королевский пир. Мне нужно больше лучшего вина!»',
     {'wine': 4}, 70000, 12000),
    ('🤴🏻', 'Король Алекс',
     '«Подайте десерт королю.»',
     {'jam_berry': 3, '🍊': 4}, 30000, 7000),
    ('🤴🏻', 'Король Алекс',
     '«Сегодня праздник урожая.»',
     {'🍉': 4, '🍍': 4, '🥭': 4}, 50000, 4500),
    ('🤡', 'Клоун',
     '«Для цирка нужен попкорн!»',
     {'popcorn': 3}, 2500, 700),
    ('🤡', 'Клоун',
     '«Детям нужны сладости.»',
     {'jam_straw': 1, 'compote_straw': 1}, 3200, 900),
    ('🤡', 'Клоун',
     '«Хочу сделать фруктовый салют!»',
     {'🍉': 1, '🍓': 2, '🍒': 2}, 3000, 800),
    ('👽', 'Пришелец',
     '«Землянин… Я изучаю ваши растения.»',
     {'🌽': 3, '🍍': 1}, 3000, 1000),
    ('👽', 'Пришелец',
     '«Ваши ягоды очень вкусные.»',
     {'🍓': 3, '🍇': 3}, 3500, 1100),
    ('👽', 'Пришелец',
     '«Напиток вашего мира…»',
     {'compote_mix': 1}, 4200, 1200),
    ('🕵🏻‍♂️', 'Детектив',
     '«Слежу за подозреваемым. Нужна еда на засаду.»',
     {'fried_potato': 1, 'compote_apple': 1}, 2200, 800),
    ('🕵🏻‍♂️', 'Детектив',
     '«Расследование идёт долго.»',
     {'soup_farm': 1}, 1200, 500),
    ('🕵🏻‍♂️', 'Детектив',
     '«Нужен перекус в дороге.»',
     {'🍎': 2, '🍊': 2}, 900, 350),
    ('🧙🏻‍♂️', 'Волшебник',
     '«Готовлю магическое варенье.»',
     {'🍓': 2, '🍒': 2}, 3000, 1000),
    ('🧙🏻‍♂️', 'Волшебник',
     '«Мне нужен редкий тропический вкус.»',
     {'jam_tropical': 1}, 8000, 2000),
    ('🧙🏻‍♂️', 'Волшебник',
     '«Зелье бодрости…»',
     {'🍊': 2, '🍎': 2, '🍇': 2}, 2600, 800),
    ('🎅🏻', 'Санта',
     '«Готовлю подарки для детей.»',
     {'🍓': 4, '🍎': 3}, 2400, 900),
    ('🎅🏻', 'Санта',
     '«Эльфы хотят сладкий напиток.»',
     {'compote_straw': 1}, 2500, 800),
    ('🎅🏻', 'Санта',
     '«На Северном полюсе холодно… нужен горячий суп.»',
     {'soup_veg': 2}, 1800, 700),
]

QUEST_SLOTS      = 5
MANUAL_REFRESHES = 3

# ============================================================
# ИМЕНА БЛЮД (для отображения в требованиях)
# ============================================================
RECIPE_DISPLAY = {
    'salad_veg':     '🥗 Овощной салат',
    'salad_summer':  '🥗 Летний салат',
    'salad_spicy':   '🥗 Острый салат',
    'salad_cabbage': '🥗 Капустный салат',
    'salad_fruit':   '🥗 Фруктовый салат',
    'soup_veg':      '🍲 Овощной суп',
    'soup_borsch':   '🍲🫜 Борщ',
    'soup_farm':     '🍲 Фермерский суп',
    'soup_spicy':    '🍲 Острый суп',
    'fried_egg':     '🍆🔥 Жареные баклажаны',
    'fried_potato':  '🍟 Картошка фри',
    'popcorn':       '🍿 Попкорн',
    'pickled_cuc':   '🫙 Маринованные огурцы',
    'pickled_tom':   '🫙 Маринованные помидоры',
    'pickled_pep':   '🫙 Маринованный перец',
    'pickled_cab':   '🫙 Квашеная капуста',
    'pickled_car':   '🫙 Маринованная морковь',
    'compote_apple': '🥤 Яблочный компот',
    'compote_straw': '🥤 Клубничный морс',
    'compote_mix':   '🥤 Ассорти компот',
    'jam_straw':     '🫙 Клубничное варенье',
    'jam_berry':     '🫙 Ягодный джем',
    'jam_tropical':  '🫙🌴 Тропический джем',
    'marmalade':     '🍭🍊 Апельсиновый мармелад',
    'jam_melon':     '🍯🍈 Дыневый джем',
    'juice_watermelon': '🫙🍉 Арбузный сок',
    'beer':          '🍺 Пиво',
    'cider':         '🍾 Сидр',
    'wine':          '🍷 Вино',
    'liqueur':       '🥃 Ликёр',
}

CROP_DISPLAY = {
    '🥔': '🥔 Картошка', '🥕': '🥕 Морковь', '🌽': '🌽 Кукуруза',
    '🫜': '🫜 Свёкла',   '🥬': '🥬 Капуста',  '🍉': '🍉 Арбуз',
    '🍈': '🍈 Дыня',     '🍍': '🍍 Ананас',   '🌾': '🌾 Пшеница',
    '🍅': '🍅 Помидор',  '🥒': '🥒 Огурец',   '🫑': '🫑 Болгарский перец',
    '🍆': '🍆 Баклажан', '🌶️': '🌶️ Перчик',  '🍓': '🍓 Клубника',
    '🍇': '🍇 Виноград', '🍎': '🍎 Яблоко',   '🍊': '🍊 Апельсин',
    '🥭': '🥭 Манго',    '🍒': '🍒 Вишня',
}

def item_display_name(key):
    if key in RECIPE_DISPLAY:
        return RECIPE_DISPLAY[key]
    return CROP_DISPLAY.get(key, key)

def is_crop(key):
    return key in CROP_DISPLAY

# ============================================================
# DB
# ============================================================
_get_conn    = None
_get_user    = None
_add_exp     = None
_add_money   = None
_spend_money = None

def _init_quest_db():
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS quest_slots (
        user_id     BIGINT,
        slot_num    INTEGER,
        quest_data  TEXT DEFAULT NULL,
        is_done     BOOLEAN DEFAULT FALSE,
        PRIMARY KEY (user_id, slot_num)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS quest_meta (
        user_id          BIGINT PRIMARY KEY,
        refreshes_left   INTEGER DEFAULT 3,
        last_auto_reset  TEXT DEFAULT NULL
    )''')
    conn.commit()
    conn.close()

def _ensure_quest_rows(user_id):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('INSERT INTO quest_meta (user_id, refreshes_left, last_auto_reset) VALUES (%s,3,%s) ON CONFLICT DO NOTHING',
              (user_id, datetime.now().isoformat()))
    for s in range(1, QUEST_SLOTS + 1):
        c.execute('INSERT INTO quest_slots (user_id, slot_num) VALUES (%s,%s) ON CONFLICT DO NOTHING',
                  (user_id, s))
    conn.commit()
    conn.close()

def _get_meta(user_id):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT refreshes_left, last_auto_reset FROM quest_meta WHERE user_id=%s', (user_id,))
    r = c.fetchone()
    conn.close()
    return r  # (refreshes_left, last_auto_reset)

def _get_quest_slots(user_id):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT slot_num, quest_data, is_done FROM quest_slots WHERE user_id=%s ORDER BY slot_num',
              (user_id,))
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        qd = json.loads(r[1]) if r[1] else None
        result.append({'slot': r[0], 'quest': qd, 'done': r[2]})
    return result

def _save_quests(user_id, quests_list):
    """quests_list: список из 5 словарей quest или None."""
    conn = _get_conn()
    c    = conn.cursor()
    for i, q in enumerate(quests_list):
        slot = i + 1
        data = json.dumps(q, ensure_ascii=False) if q else None
        c.execute('UPDATE quest_slots SET quest_data=%s, is_done=FALSE WHERE user_id=%s AND slot_num=%s',
                  (data, user_id, slot))
    conn.commit()
    conn.close()

def _mark_quest_done(user_id, slot_num):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('UPDATE quest_slots SET is_done=TRUE WHERE user_id=%s AND slot_num=%s',
              (user_id, slot_num))
    conn.commit()
    conn.close()

def _set_refreshes(user_id, count):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('UPDATE quest_meta SET refreshes_left=%s WHERE user_id=%s', (count, user_id))
    conn.commit()
    conn.close()

def _set_auto_reset(user_id):
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('UPDATE quest_meta SET last_auto_reset=%s, refreshes_left=3 WHERE user_id=%s',
              (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def _roll_quests():
    """Генерирует 5 случайных заданий."""
    result = []
    for _ in range(QUEST_SLOTS):
        if random.random() < 0.05:
            pool = QUESTS_RARE
        else:
            pool = QUESTS_COMMON
        npc_e, npc_name, quote, reqs, money, exp = random.choice(pool)
        result.append({
            'npc_emoji': npc_e,
            'npc_name':  npc_name,
            'quote':     quote,
            'reqs':      reqs,
            'money':     money,
            'exp':       exp,
        })
    return result

# ============================================================
# ИНВЕНТАРЬ
# ============================================================
def _get_available_items(user_id):
    """Возвращает {item_key: [(quality, count), ...]} из обоих инвентарей."""
    conn = _get_conn()
    c    = conn.cursor()
    c.execute('SELECT crop_emoji, quality, count FROM garden_inventory WHERE user_id=%s AND count>0',
              (user_id,))
    crops = c.fetchall()
    c.execute('SELECT recipe_key, quality, count FROM goods_inventory WHERE user_id=%s AND count>0',
              (user_id,))
    goods = c.fetchall()
    conn.close()

    result = {}
    for emoji, qual, cnt in crops:
        result.setdefault(emoji, []).append((qual, cnt))
    for rk, qual, cnt in goods:
        result.setdefault(rk, []).append((qual, cnt))
    return result

def _spend_item(user_id, item_key, quality):
    """Списывает 1 единицу предмета."""
    conn = _get_conn()
    c    = conn.cursor()
    if is_crop(item_key):
        c.execute('''UPDATE garden_inventory SET count=count-1
                     WHERE user_id=%s AND crop_emoji=%s AND quality=%s AND count>0''',
                  (user_id, item_key, quality))
    else:
        c.execute('''UPDATE goods_inventory SET count=count-1
                     WHERE user_id=%s AND recipe_key=%s AND quality=%s AND count>0''',
                  (user_id, item_key, quality))
    updated = c.rowcount
    conn.commit()
    conn.close()
    return updated > 0

def _return_items(user_id, collected):
    """Возвращает предметы из сессии. collected: {item_key|quality: count}"""
    conn = _get_conn()
    c    = conn.cursor()
    for key, cnt in collected.items():
        item_key, quality = key.split('|')
        quality = int(quality)
        if is_crop(item_key):
            c.execute('''INSERT INTO garden_inventory (user_id, crop_emoji, quality, count) VALUES (%s,%s,%s,%s)
                         ON CONFLICT (user_id, crop_emoji, quality) DO UPDATE SET count=garden_inventory.count+%s''',
                      (user_id, item_key, quality, cnt, cnt))
        else:
            c.execute('''INSERT INTO goods_inventory (user_id, recipe_key, quality, count) VALUES (%s,%s,%s,%s)
                         ON CONFLICT (user_id, recipe_key, quality) DO UPDATE SET count=goods_inventory.count+%s''',
                      (user_id, item_key, quality, cnt, cnt))
    conn.commit()
    conn.close()

# ============================================================
# СЕССИИ СДАЧИ ПРЕДМЕТОВ
# ============================================================
_quest_sessions = {}
_session_lock   = threading.Lock()

# ============================================================
# ТЕКСТЫ
# ============================================================
SEP = "• — — — — — — — — •"

def _req_text(reqs):
    parts = []
    for k, v in reqs.items():
        parts.append(f"{item_display_name(k)} ×{v}")
    return ", ".join(parts)

def _quest_block(slot_data):
    q = slot_data['quest']
    if not q:
        return f"{SEP}\n[Пустой слот]\n"
    if slot_data['done']:
        return (f"{SEP}\n"
                f"_{q['npc_emoji']} ~~{q['npc_name']}~~_\n"
                f"✅ Выполнено\n")
    reqs_str = _req_text(q['reqs'])
    # Прогресс не храним глобально — показываем только требования
    return (f"{SEP}\n"
            f"{q['npc_emoji']} {q['npc_name']}\n"
            f"— {q['quote']}\n"
            f"Требует: {reqs_str}\n"
            f"Вознаграждение: +💵{q['money']:,}, +⭐{q['exp']:,}\n")

def _quests_menu_text(user_id, slots, meta):
    user  = _get_user(user_id)
    money = user[2] if user else 0
    exp   = user[3] if user else 0

    refreshes_left, last_auto = meta
    # Таймер до авто-обновления
    if last_auto:
        next_reset = datetime.fromisoformat(last_auto) + timedelta(hours=24)
        left_sec   = max(0, (next_reset - datetime.now()).total_seconds())
        h = int(left_sec // 3600)
        m = int((left_sec % 3600) // 60)
        s = int(left_sec % 60)
        timer_str = f"{h} ч. {m} мин. {s} сек."
    else:
        timer_str = "скоро"

    lines = [
        f"— – - 📋 ЗАДАНИЯ ГОРОДА 📋 - – —\n",
        f"Деньги: 💵 {money:,}",
        f"Опыта: ⭐ {exp:,}\n",
        f"🔄 Обновить задания: {refreshes_left}/{MANUAL_REFRESHES}",
        f"⏳ Новые задания через: {timer_str}\n",
    ]
    for s in slots:
        lines.append(_quest_block(s))
    lines.append(SEP)
    return "\n".join(lines)

def _quests_markup(slots, has_refreshes):
    m = InlineKeyboardMarkup(row_width=1)
    for s in slots:
        if s['quest'] and not s['done']:
            q = s['quest']
            m.add(InlineKeyboardButton(
                f"{q['npc_emoji']} {q['npc_name']}",
                callback_data=f"quest_npc_{s['slot']}"
            ))
    nav = [
        InlineKeyboardButton("🔙 Назад",      callback_data="grd_main"),
        InlineKeyboardButton("📦 Инвентарь",  callback_data="grd_inventory"),
    ]
    if has_refreshes:
        nav.insert(1, InlineKeyboardButton("🔄 Обновить", callback_data="quest_refresh"))
    m.add(*nav)
    return m

def _delivery_text(user_id, quest, slot_num, collected):
    """Текст сдачи предметов нпс."""
    q     = quest
    lines = [f"{q['npc_emoji']} {q['npc_name']}",
             f"— {q['quote']}",
             f"Требует: {_req_text(q['reqs'])}\n",
             "Отдано:"]
    for item_key, need in q['reqs'].items():
        got = sum(v for k, v in collected.items() if k.split('|')[0] == item_key)
        status = f"✅" if got >= need else f"{got}/{need}"
        lines.append(f"  {item_display_name(item_key)} {status}")
    lines.append("\nВыберите продукты для сдачи:")
    return "\n".join(lines)

def _delivery_markup(user_id, quest, slot_num, collected):
    reqs = quest['reqs']
    inv  = _get_available_items(user_id)
    m    = InlineKeyboardMarkup(row_width=1)

    # Проверяем всё ли собрано
    all_done = all(
        sum(v for k, v in collected.items() if k.split('|')[0] == ik) >= need
        for ik, need in reqs.items()
    )

    if all_done:
        m.add(
            InlineKeyboardButton("✅ Сдать", callback_data=f"quest_submit_{slot_num}"),
            InlineKeyboardButton("🔙 Назад", callback_data=f"quest_cancel_{slot_num}"),
        )
        return m

    # Кнопки нужных предметов
    for item_key, need in reqs.items():
        got = sum(v for k, v in collected.items() if k.split('|')[0] == item_key)
        if got >= need:
            continue
        items = inv.get(item_key, [])
        for qual, cnt in sorted(items, key=lambda x: -x[0]):
            if cnt > 0:
                from garden import quality_str
                m.add(InlineKeyboardButton(
                    f"{item_display_name(item_key)} {quality_str(qual)} ×{cnt}",
                    callback_data=f"quest_give_{slot_num}_{item_key}_{qual}"
                ))

    m.add(InlineKeyboardButton("🔙 Назад", callback_data=f"quest_cancel_{slot_num}"))
    return m

# ============================================================
# РЕГИСТРАЦИЯ ХЭНДЛЕРОВ
# ============================================================

def register_quest_handlers(bot, get_conn, get_user, add_exp, add_money, spend_money):
    global _get_conn, _get_user, _add_exp, _add_money, _spend_money
    _get_conn    = get_conn
    _get_user    = get_user
    _add_exp     = add_exp
    _add_money   = add_money
    _spend_money = spend_money
    _init_quest_db()

    def _open_quests(call):
        user_id = call.from_user.id
        _ensure_quest_rows(user_id)
        meta  = _get_meta(user_id)
        slots = _get_quest_slots(user_id)

        # Авто-сброс если прошло 24 часа
        last_auto = meta[1]
        if last_auto:
            elapsed = (datetime.now() - datetime.fromisoformat(last_auto)).total_seconds()
            if elapsed >= 86400:
                new_quests = _roll_quests()
                _save_quests(user_id, new_quests)
                _set_auto_reset(user_id)
                meta  = _get_meta(user_id)
                slots = _get_quest_slots(user_id)

        # Если задания пустые — генерируем
        if all(s['quest'] is None for s in slots):
            new_quests = _roll_quests()
            _save_quests(user_id, new_quests)
            _set_auto_reset(user_id)
            meta  = _get_meta(user_id)
            slots = _get_quest_slots(user_id)

        has_ref = meta[0] > 0
        try:
            bot.edit_message_text(
                _quests_menu_text(user_id, slots, meta),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_quests_markup(slots, has_ref),
                parse_mode='Markdown'
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Открыть задания ─────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'grd_quests')
    def cb_grd_quests(call):
        _open_quests(call)

    # ── Обновить задания ─────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == 'quest_refresh')
    def cb_quest_refresh(call):
        user_id = call.from_user.id
        meta    = _get_meta(user_id)
        if not meta or meta[0] <= 0:
            bot.answer_callback_query(call.id, "❌ Обновления закончились!")
            return
        new_quests = _roll_quests()
        _save_quests(user_id, new_quests)
        _set_refreshes(user_id, meta[0] - 1)
        _open_quests(call)

    # ── Нажать на НПС ────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('quest_npc_'))
    def cb_quest_npc(call):
        user_id  = call.from_user.id
        slot_num = int(call.data[len('quest_npc_'):])
        slots    = _get_quest_slots(user_id)
        slot_d   = next((s for s in slots if s['slot'] == slot_num), None)
        if not slot_d or not slot_d['quest'] or slot_d['done']:
            bot.answer_callback_query(call.id, "❌ Задание недоступно!")
            return

        quest = slot_d['quest']
        inv   = _get_available_items(user_id)

        # Проверка наличия всех нужных предметов
        missing = []
        for item_key, need in quest['reqs'].items():
            total = sum(cnt for _, cnt in inv.get(item_key, []))
            if total < need:
                missing.append(f"{item_display_name(item_key)} ×{need}")

        if missing:
            bot.answer_callback_query(
                call.id,
                "❌ Не хватает: " + ", ".join(missing) + " ‼️",
                show_alert=True
            )
            return

        # Инициализируем сессию
        with _session_lock:
            _quest_sessions[user_id] = {
                'slot_num':  slot_num,
                'quest':     quest,
                'collected': {},
            }

        try:
            bot.edit_message_text(
                _delivery_text(user_id, quest, slot_num, {}),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_delivery_markup(user_id, quest, slot_num, {}),
                parse_mode='Markdown'
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Отдать предмет ───────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('quest_give_'))
    def cb_quest_give(call):
        user_id = call.from_user.id
        parts   = call.data[len('quest_give_'):].split('_')
        slot_num = int(parts[0])
        item_key = parts[1]
        quality  = int(parts[2])

        with _session_lock:
            session = _quest_sessions.get(user_id)
        if not session or session['slot_num'] != slot_num:
            bot.answer_callback_query(call.id, "❌ Сессия истекла!")
            return

        quest     = session['quest']
        collected = session['collected']
        need      = quest['reqs'].get(item_key, 0)
        got       = sum(v for k, v in collected.items() if k.split('|')[0] == item_key)

        if got >= need:
            bot.answer_callback_query(call.id, f"✅ {item_display_name(item_key)} уже набрано!")
            return

        if not _spend_item(user_id, item_key, quality):
            bot.answer_callback_query(call.id, "❌ Недостаточно!")
            return

        with _session_lock:
            s = _quest_sessions.get(user_id)
            if s:
                key = f"{item_key}|{quality}"
                s['collected'][key] = s['collected'].get(key, 0) + 1

        collected = _quest_sessions[user_id]['collected']
        try:
            bot.edit_message_text(
                _delivery_text(user_id, quest, slot_num, collected),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_delivery_markup(user_id, quest, slot_num, collected),
                parse_mode='Markdown'
            )
        except: pass
        bot.answer_callback_query(call.id)

    # ── Отмена сдачи ─────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('quest_cancel_'))
    def cb_quest_cancel(call):
        user_id  = call.from_user.id
        slot_num = int(call.data[len('quest_cancel_'):])

        with _session_lock:
            session = _quest_sessions.pop(user_id, None)

        if session and session['collected']:
            _return_items(user_id, session['collected'])

        _open_quests(call)

    # ── Сдать задание ─────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith('quest_submit_'))
    def cb_quest_submit(call):
        user_id  = call.from_user.id
        slot_num = int(call.data[len('quest_submit_'):])

        with _session_lock:
            session = _quest_sessions.pop(user_id, None)

        if not session:
            bot.answer_callback_query(call.id, "❌ Сессия истекла!")
            return

        quest = session['quest']
        _mark_quest_done(user_id, slot_num)
        _add_money(user_id, quest['money'])
        _add_exp(user_id, quest['exp'])

        bot.send_message(
            call.message.chat.id,
            f"🎉 Задание выполнено!\n\n"
            f"Получено: +💵{quest['money']:,}, +⭐{quest['exp']:,}"
        )
        _open_quests(call)
