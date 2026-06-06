# =============================================================================
#  archie.py — Модуль игры «Архив Знаний» для Telegram-бота
#  Команда запуска: .архи
#
#  Подключение в bot.py:
#      from archie import register_archie_handlers
#      register_archie_handlers(bot)
#
#  Файлы данных (кладутся рядом с bot.py или в папку data/):
#      data/words.txt   — список слов, по одному на строку
#      data/facts.txt   — факты/цитаты для награды, по одному на строку
# =============================================================================

import os
import random
import re
import unicodedata

from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

# ---------------------------------------------------------------------------
# Пути к файлам данных
# ---------------------------------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
WORDS_FILE = os.path.join(BASE_DIR, "data", "words.txt")
FACTS_FILE = os.path.join(BASE_DIR, "data", "facts.txt")

# ---------------------------------------------------------------------------
# Загрузка данных
# ---------------------------------------------------------------------------

def _load_lines(path: str, fallback: list[str]) -> list[str]:
    """Читает файл построчно. Если файл не найден — возвращает fallback."""
    if not os.path.exists(path):
        return fallback
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    return lines if lines else fallback

# Встроенные слова — используются если words.txt не найден
FALLBACK_WORDS = [
    "хамелеон", "астрономия", "библиотека", "философия", "горизонт",
    "кристалл", "лабиринт", "магнетизм", "облако", "пирамида",
    "радуга", "симфония", "туманность", "фонтан", "цитадель",
]

# Встроенные факты — используются если facts.txt не найден
FALLBACK_FACTS = [
    "Хамелеоны способны двигать глазами независимо друг от друга.",
    "Осьминоги имеют три сердца и голубую кровь.",
    "Мёд не портится — в египетских гробницах находили мёд возрастом 3000 лет.",
    "Молния бьёт в Землю около 100 раз в секунду.",
    "Самая тихая комната в мире находится в Миннесоте: тишина там настолько глубокая, что люди слышат собственный пульс.",
]

WORDS: list[str] = []
FACTS: list[str] = []

def reload_data() -> None:
    """Перечитывает файлы слов и фактов. Вызвать один раз при старте бота."""
    global WORDS, FACTS
    WORDS = _load_lines(WORDS_FILE, FALLBACK_WORDS)
    FACTS = _load_lines(FACTS_FILE, FALLBACK_FACTS)

reload_data()

# ---------------------------------------------------------------------------
# Хранение сессий  {user_id: session_dict}
# ---------------------------------------------------------------------------
SESSIONS: dict[int, dict] = {}

def _new_session(user_id: int, word: str, grid_data: tuple) -> dict:
    grid_str, cells, size, filler_positions = grid_data
    return {
        "word":             word,
        "grid":             grid_str,
        "cells":            cells,
        "size":             size,
        "filler_positions": filler_positions,
        "hint_applied":     False,
        "attempts":         3,
        "active":           True,
        "used_answers":     set(),
    }

# ---------------------------------------------------------------------------
# Генерация сетки букв
# ---------------------------------------------------------------------------

_RU_LETTERS = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"

def _normalize(text: str) -> str:
    """Верхний регистр + ё→е + убрать пробелы и знаки препинания."""
    text = text.upper().replace("Ё", "Е")
    text = re.sub(r"[^А-ЯA-Z0-9]", "", text)
    return text

def _build_grid(word: str) -> tuple:
    """Возвращает (grid_str, cells, size, filler_positions)"""
    """
    Строит визуальную сетку 4×4 (или 5×5 для длинных слов).
    Буквы слова перемешаны по клеткам; остальное — случайные буквы.
    Часть букв слова (hide_ratio) заменяется на ⬜.

    Возвращает строку вида:
        Х | А | ⬜ | М
        ⬜ | Е | Л | ⬜
        ...
    """
    w = _normalize(word)
    length = len(w)

    # Выбрать размер поля
    if length <= 8:
        size = 4
    else:
        size = 5

    total = size * size

    # Индексы клеток, куда ставим буквы слова (случайные позиции)
    positions = random.sample(range(total), min(length, total))

    # Собрать клетки
    cells = [""] * total
    for i, pos in enumerate(positions):
        cells[pos] = w[i]

    # Остальные клетки — случайные буквы
    for i in range(total):
        if not cells[i]:
            cells[i] = random.choice(_RU_LETTERS)

    # Разбить на строки
    rows = []
    for row_i in range(size):
        row_cells = cells[row_i * size: row_i * size + size]
        rows.append(" | ".join(row_cells))
    filler_positions = [i for i in range(total) if cells[i] not in list(w)]
    return "\n".join(rows), cells, size, filler_positions

def _remove_some_fillers(session: dict, ratio: float = 0.45) -> None:
    """Заменяет часть ненужных букв на ⬜ и обновляет session['grid']."""
    fillers = session["filler_positions"]
    if not fillers:
        return
    remove_count = max(1, round(len(fillers) * ratio))
    to_remove = random.sample(fillers, min(remove_count, len(fillers)))
    for pos in to_remove:
        session["cells"][pos] = "⬜"
    # Убираем использованные позиции из filler_positions
    session["filler_positions"] = [p for p in fillers if p not in to_remove]
    # Перестраиваем строку сетки
    size = session["size"]
    rows = []
    for row_i in range(size):
        row = session["cells"][row_i * size: row_i * size + size]
        rows.append(" | ".join(row))
    session["grid"] = "\n".join(rows)
# ---------------------------------------------------------------------------
# Тексты интерфейса
# ---------------------------------------------------------------------------

_WRONG_MSGS_1 = [
    "📖 Архив не подтвердил ответ.",
    "📖 Символы ещё не сложились в истину.",
    "📖 Среди букв скрыто другое слово.",
    "📖 Эта страница пока не открыта.",
    "📖 Архив хранит иной ответ.",
    "📖 Почти, но не то.",
    "📖 Неправильное прочтение страницы.",
    "📖 Ответ рядом, но не совпадает.",
]

_WRONG_MSGS_2 = [
    "📖 Архив приоткрыл страницу, но не до конца.",
    "📖 Подсказка близко, но не раскрыта.",
    "📖 Ты смотришь в нужную сторону, но не видишь слова.",
    "📖 Ещё один шаг — и Архив, возможно, уступит.",
]

_WRONG_MSGS_LAST = [
    "📖 Последняя попытка. Архив ждёт точного ответа.",
    "📖 Сейчас Архив либо откроется, либо закроется.",
    "📖 Последний взгляд на символы.",
    "📖 Осталась одна строка между тобой и знанием.",
]

_DEFEAT_QUOTES = [
    "«Тот, кто задаёт вопрос, иногда выглядит глупцом лишь на минуту.\nТот, кто не задаёт вопросов, остаётся им дольше.»",
    "«Знание приходит не к самым громким, а к самым внимательным.»",
    "«Ошибка — это не закрытая дверь. Это не тот ключ.»",
    "«Иногда путь к ответу длиннее, чем ожидание ответа.»",
    "«Человек узнаёт больше, когда перестаёт торопиться.»",
    "«Не всякая неудача пуста. Иногда она оставляет точную мысль.»",
    "«Любопытство редко обманывает. Оно просто не обещает лёгкий путь.»",
    "«Архив не наказывает. Архив проверяет, готов ли ты читать дальше.»",
    "«Мудрость часто начинается там, где закончилась самоуверенность.»",
    "«Мы искали истину в знаках, но забыли научиться их понимать.»",
    "«Страница не исчезает. Исчезает только тот, кто перестаёт её искать.»",
    "«То, что кажется ошибкой, иногда просто ждёт другого вопроса.»",
    "«Архив хранит не ответы, а выдержку тех, кто их ищет.»",
    "«Не торопись с выводами. Самые точные ответы часто приходят последними.»",
    "«Сначала смотри, потом называй.»",
]

def _hearts(attempts: int) -> str:
    return "❤️" * attempts + "🖤" * (3 - attempts)

def _game_board(session: dict, header_line: str = "📖 Испытание Архива") -> str:
    return (
        f"{header_line}\n\n"
        f"{_hearts(session['attempts'])}\n\n"
        f"{session['grid']}\n\n"
        f"✍ Отправь предполагаемое слово сообщением.\n"
        f"Регистр букв не имеет значения."
    )

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _pick_word() -> str:
    # Фильтр: только слова 3–12 букв, только кириллица
    pool = [w for w in WORDS if 3 <= len(w) <= 12 and re.fullmatch(r"[а-яёА-ЯЁ]+", w)]
    if not pool:
        pool = FALLBACK_WORDS
    return random.choice(pool).upper()

def _pick_fact() -> str:
    return random.choice(FACTS)

def _pick_defeat_quote() -> str:
    return random.choice(_DEFEAT_QUOTES)

# ---------------------------------------------------------------------------
# Регистрация обработчиков
# ---------------------------------------------------------------------------

def register_archie_handlers(bot: TeleBot) -> None:
    """Вызвать один раз из bot.py: register_archie_handlers(bot)"""

    # ------------------------------------------------------------------
    # Команда .архи
    # ------------------------------------------------------------------
    @bot.message_handler(func=lambda m: m.text and m.text.strip().lower() in (".архи", ".архи"))
    def cmd_archi(message: Message):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📖 Начать", callback_data="archi_start"))
        bot.send_message(
            message.chat.id,
            "📖 *Архив Знаний*\n\n"
            "Перед тобой одно из множества слов, скрытых среди символов Архива.\n\n"
            "Разгадай его, используя наблюдательность, интуицию и память.\n\n"
            "За верный ответ Архив откроет тебе новый фрагмент знаний.\n\n"
            "❤️ Попытки: 3",
            parse_mode="Markdown",
            reply_markup=markup,
        )

    # ------------------------------------------------------------------
    # Кнопка «📖 Начать»
    # ------------------------------------------------------------------
    @bot.callback_query_handler(func=lambda call: call.data == "archi_start")
    def callback_archi_start(call: CallbackQuery):
        user_id = call.from_user.id

        # Проверка активной сессии
        if user_id in SESSIONS and SESSIONS[user_id]["active"]:
            bot.answer_callback_query(
                call.id,
                "📖 Архив уже открыт для тебя. Сначала заверши текущее испытание.",
                show_alert=True,
            )
            return

        bot.answer_callback_query(call.id)

        word = _pick_word()
        grid_data = _build_grid(word)
        SESSIONS[user_id] = _new_session(user_id, word, grid_data)

        bot.send_message(
            call.message.chat.id,
            _game_board(SESSIONS[user_id]),
            parse_mode="Markdown",
        )

    # ------------------------------------------------------------------
    # Обработка текстовых ответов игрока
    # ------------------------------------------------------------------
    @bot.message_handler(
        func=lambda m: (
            m.text
            and m.from_user.id in SESSIONS
            and SESSIONS[m.from_user.id]["active"]
            # Не реагировать на команды и системные слова
            and not m.text.strip().startswith(".")
            and m.text.strip().lower() not in (
                "старт", "начать", "стоп", "ещё раз", "еще раз", "help", "/start"
            )
        )
    )
    def handle_archi_answer(message: Message):
        user_id  = message.from_user.id
        session  = SESSIONS[user_id]
        raw      = message.text.strip()
        answer   = _normalize(raw)
        target   = _normalize(session["word"])

        # Защита от повторного того же ответа
        if answer in session["used_answers"]:
            bot.send_message(
                message.chat.id,
                "📖 Этот ответ уже был засчитан. Попробуй другое слово.",
            )
            return
        session["used_answers"].add(answer)

        # ✅ Верный ответ
        if answer == target:
            session["active"] = False
            fact = _pick_fact()
            bot.send_message(
                message.chat.id,
                f"📖 *Архив открыт.*\n\n"
                f"Слово разгадано: *{session['word']}*\n\n"
                f"📚 *Фрагмент знаний:*\n{fact}",
                parse_mode="Markdown",
            )
            del SESSIONS[user_id]
            return

        # ❌ Неверный ответ
        session["attempts"] -= 1

        # Попытки кончились — поражение
        if session["attempts"] == 0:
            session["active"] = False
            quote = _pick_defeat_quote()
            bot.send_message(
                message.chat.id,
                f"📖 *Архив закрылся.*\n\n"
                f"Загаданное слово: *{session['word']}*\n\n"
                f"🕯 Мысль Архива:\n{quote}",
                parse_mode="Markdown",
            )
            del SESSIONS[user_id]
            return

        # Выбрать сообщение об ошибке по номеру попытки
        attempts_left = session["attempts"]
        # Подсчёт совпадающих букв
        target_letters = set(target)
        answer_letters = set(answer)
        matched = len(target_letters & answer_letters)
        match_hint = f"\n📝 Совпало букв: *{matched}*" if matched > 0 else "\n📝 Совпавших букв нет."

        if attempts_left == 2:
            if not session["hint_applied"]:
                _remove_some_fillers(session)
                session["hint_applied"] = True
            wrong_text = random.choice(_WRONG_MSGS_1)
            extra = f"\n\n💡 Подсказка: всего букв в слове — *{len(session['word'])}*"
        elif attempts_left == 1:
            _remove_some_fillers(session)
            wrong_text = random.choice(_WRONG_MSGS_2)
            first_letter = session['word'][0]
            extra = f"\n\n💡 Подсказка: первая буква — *{first_letter}*"
        else:
            wrong_text = random.choice(_WRONG_MSGS_LAST)
            extra = ""

        bot.send_message(
            message.chat.id,
            f"{wrong_text}{extra}\n\n"
            f"{match_hint}\n\n"
            f"{_hearts(attempts_left)}\n\n"
            f"{session['grid']}\n\n"
            f"✍ Попробуй ещё раз.",
            parse_mode="Markdown",
        )

    # ------------------------------------------------------------------
    # Ответ когда игра уже завершена, а игрок пишет что-то похожее на ответ
    # (опционально — можно убрать если мешает другим хэндлерам)
    # ------------------------------------------------------------------
    @bot.message_handler(
        func=lambda m: (
            m.text
            and m.from_user.id not in SESSIONS
            # Только если сообщение выглядит как одно слово на кириллице
            and re.fullmatch(r"[а-яёА-ЯЁ]{3,15}", m.text.strip())
        ),
        content_types=["text"],
    )
    def handle_archi_after_game(message: Message):
        # Этот хэндлер срабатывает только если нет активной сессии.
        # Намеренно ничего не делаем — не мешаем другим командам бота.
        pass
