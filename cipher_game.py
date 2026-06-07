# =============================================================================
#  cipher_game.py — Модуль игры «Шифр Архива» (Wordle-механика)
#  Команды запуска: .шифр  /  .вордл
#
#  Подключение в bot.py (после создания bot):
#      from cipher_game import register_cipher_handlers
#      register_cipher_handlers(bot)
#
#  Файлы данных:
#      data/wordle.txt  — слова для угадывания (5–8 букв), по одному на строку
#      data/facts.txt   — факты для награды, по одному на строку
# =============================================================================

import os
import random
import re
import threading  # Добавили для фонового удаления
import time

from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

# ---------------------------------------------------------------------------
# Пути к файлам
# ---------------------------------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
WORDLE_FILE = os.path.join(BASE_DIR, "data", "wordle.txt")
FACTS_FILE  = os.path.join(BASE_DIR, "data", "facts.txt")

FALLBACK_WORDS = ["книга", "архив", "тайна", "загадка", "символ", "запись", "страница"]
FALLBACK_FACTS = [
    "Хамелеоны способны двигать глазами независимо друг от друга.",
    "Осьминоги имеют три сердца и голубую кровь.",
    "Мёд не портится — в египетских гробницах находили мёд возрастом 3000 лет.",
]

# Хранилища (заполняются при reload_data)
WORDLE_LIST: list[str] = []   # список для случайного выбора
VALID_SET:   set[str]  = set()  # множество для быстрой проверки наличия
FACTS:      list[str] = []


def _normalize_word(word: str) -> str:
    """Нижний регистр + ё→е + удаление всех символов, кроме букв."""
    if not word:
        return ""
    return re.sub(r"[^а-яa-z]", "", word.lower().replace("ё", "е").strip())

def _load_file(path: str) -> list[str]:
    """Читает файл построчно."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]

def reload_data() -> None:
    global WORDLE_LIST, VALID_SET, FACTS

    raw_wordle = _load_file(WORDLE_FILE)
    normalized = [_normalize_word(w) for w in raw_wordle if _normalize_word(w)]
    
    # Жесткий фильтр на длину СТРОГО от 5 до 8 букв для ВСЕЙ базы данных
    filtered_words = [w for w in normalized if 5 <= len(w) <= 8]
    
    if not filtered_words:
        filtered_words = [_normalize_word(w) for w in FALLBACK_WORDS]
    
    # Синхронизируем списки: и загадываем, и проверяем только нормальные слова!
    WORDLE_LIST = filtered_words
    VALID_SET = set(filtered_words)

    # Факты
    lines = _load_file(FACTS_FILE)
    FACTS = lines if lines else FALLBACK_FACTS

# Первичная загрузка данных при импорте модуля
reload_data()

# ---------------------------------------------------------------------------
# Константы игры
# ---------------------------------------------------------------------------
MAX_ATTEMPTS = 6

HIT   = "🟩"  # правильная буква, правильное место
PLACE = "🟨"  # буква есть, но не на своём месте
MISS  = "⬛"  # буквы нет в слове
EMPTY = "⬛"  # пустая строка (не использованная попытка)

RARE_RECORDS = [
    "«Мы искали знания ради силы.\nПозже поняли, что сила была нужна лишь для поиска знаний.»",
    "«Архив не помнит лиц. Только слова, которые они искали.»",
    "«Каждая расшифрованная запись — это голос из прошлого, который наконец был услышан.»",
    "«Истина редко прячется далеко. Чаще всего она ждёт правильного вопроса.»",
    "«Великий Архив хранит не ответы, а пути к ним.»",
]

DEFEAT_QUOTES = [
    "«Любопытство ценнее безошибочности.»",
    "«Некоторые ответы приходят только после неверных вопросов.»",
    "«Архив не требует идеальности. Он требует настойчивости.»",
    "«Ошибка — это тоже след на пути к знанию.»",
    "«Даже закрытая книга может оставить мысль.»",
    "«Знание любит терпеливых.»",
    "«Неудачная попытка всё ещё остаётся попыткой.»",
    "«Самый короткий путь к ответу редко бывает самым полезным.»",
    "«Иногда важно не найти ответ, а научиться искать.»",
    "«Архив помнит каждого, кто возвращается.»",
]

# ---------------------------------------------------------------------------
# Хранилище сессий игр { user_id: session_dict }
# ---------------------------------------------------------------------------
SESSIONS: dict[int, dict] = {}

# ---------------------------------------------------------------------------
# Вспомогательные функции игрового процесса
# ---------------------------------------------------------------------------

def _pick_word() -> str:
    """Возвращает случайное слово из подготовленного списка."""
    return random.choice(WORDLE_LIST)

def _check_guess(guess: str, target: str) -> list[str]:
    """Wordle-алгоритм с корректной обработкой дублирующихся букв."""
    n = len(target)
    result       = [MISS] * n
    target_chars = list(target)
    guess_chars  = list(guess)

    # Проход 1 — точные совпадения (🟩)
    for i in range(n):
        if guess_chars[i] == target_chars[i]:
            result[i]       = HIT
            target_chars[i] = None
            guess_chars[i]  = None

    # Проход 2 — буква есть, но не на своем месте (🟨)
    for i in range(n):
        if guess_chars[i] is None:
            continue
        if guess_chars[i] in target_chars:
            result[i] = PLACE
            target_chars[target_chars.index(guess_chars[i])] = None

    return result

def _hearts(attempts_left: int) -> str:
    """Отображает шкалу попыток в виде сердец."""
    used = MAX_ATTEMPTS - attempts_left
    return "❤️" * attempts_left + "🖤" * used

def _format_row(word: str, emojis: list[str]) -> str:
    """Форматирует одну строку попытки: буквы через пробел и эмодзи под ними."""
    letters = " ".join(c.upper() for c in word)
    marks   = "".join(emojis)
    return f"{letters}\n{marks}"

def _empty_row(length: int) -> str:
    """Возвращает пустую строку игрового поля."""
    return EMPTY * length

def _build_board(session: dict, footer: str = "✍ Отправь предполагаемое слово сообщением.") -> str:
    """Собирает полное игровое поле из истории попыток."""
    target_len = len(session["word"])
    history    = session["history"]
    remaining  = MAX_ATTEMPTS - len(history)

    lines = [
        "🔐 *Шифр Архива*\n",
        f"{_hearts(session['attempts'])}\n",
        f"Слово содержит *{target_len}* букв.\n",
    ]

    for guess, emojis in history:
        lines.append(_format_row(guess, emojis))

    for _ in range(remaining):
        lines.append(_empty_row(target_len))

    if footer:
        lines.append(f"\n{footer}")
        
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Регистрация обработчиков Telegram-бота
# ---------------------------------------------------------------------------

def _delete_message_delayed(bot: TeleBot, chat_id: int, message_id: int, delay: int = 3):
    """Удаляет сообщение через указанное количество секунд в фоновом потоке."""
    def delayed_delete():
        time.sleep(delay)
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass  # Если игрок сам уже удалил сообщение, бот не выдаст ошибку
            
    threading.Thread(target=delayed_delete, daemon=True).start()


def register_cipher_handlers(bot: TeleBot) -> None:
    """Регистрация хэндлеров для игры в основном файле bot.py."""

    # Команда .шифр / .вордл
    @bot.message_handler(
        func=lambda m: m.text and m.text.strip().lower() in (".шифр", ".вордл")
    )
    def cmd_cipher(message: Message):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔍 Начать расшифровку", callback_data="cipher_start"))
        bot.send_message(
            message.chat.id,
            "🔐 *Шифр Архива*\n\n"
            "Одна из страниц Великого Архива повреждена.\n\n"
            "Слово сохранилось, но его символы скрыты.\n\n"
            "Тебе предстоит восстановить его за ограниченное число попыток.\n\n"
            f"❤️ Попыток: *{MAX_ATTEMPTS}*",
            parse_mode="Markdown",
            reply_markup=markup,
        )

    # Кнопка «🔍 Начать расшифровку»
    @bot.callback_query_handler(func=lambda call: call.data == "cipher_start")
    def callback_cipher_start(call: CallbackQuery):
        user_id = call.from_user.id
        chat_id = call.message.chat.id

        if user_id in SESSIONS and SESSIONS[user_id]["active"]:
            bot.answer_callback_query(
                call.id,
                "📖 Шифр уже открыт.\n"
                "Заверши текущую расшифровку прежде чем начинать новую.",
                show_alert=True,
            )
            return

        bot.answer_callback_query(call.id)

        word = _pick_word()

        SESSIONS[user_id] = {
            "word":     word,
            "attempts": MAX_ATTEMPTS,
            "history":  [],
            "active":   True,
            "chat_id":  chat_id,
            "board_msg_id": None,
        }

        board_text = _build_board(SESSIONS[user_id])
        msg = bot.send_message(chat_id, board_text, parse_mode="Markdown")
        SESSIONS[user_id]["board_msg_id"] = msg.message_id

    # Обработка текстовых ответов игроков
    @bot.message_handler(
        func=lambda m: (
            m.text
            and m.from_user.id in SESSIONS
            and SESSIONS[m.from_user.id]["active"]
            and not m.text.strip().startswith(".")
        )
    )
    def handle_cipher_answer(message: Message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        session = SESSIONS[user_id]

        raw    = message.text.strip()
        guess  = _normalize_word(raw)
        target = session["word"]
        length = len(target)

        # Проверка №1: наличие слова в общих базах данных
                # Проверка №1: наличие слова в общих базах данных
        if guess not in VALID_SET:
            msg = bot.send_message(
                chat_id,
                "📖 Архив не распознал это слово.\n\n"
                "Такой записи нет в Великом Хранилище.\n"
                "_Попытка не расходуется._",
                parse_mode="Markdown",
            )
            # Удаляем это предупреждение через 3 секунды
            _delete_message_delayed(bot, chat_id, msg.message_id, delay=3)
            return

        # Проверка №2: соответствие длины слова оригиналу
        if len(guess) != length:
            msg = bot.send_message(
                chat_id,
                f"📖 Размер шифра не совпадает.\n\n"
                f"Требуется слово из *{length}* букв.\n"
                f"_Попытка не расходуется._",
                parse_mode="Markdown",
            )
            # Удаляем это предупреждение через 3 секунды
            _delete_message_delayed(bot, chat_id, msg.message_id, delay=3)
            return


        # Расчет совпадений букв
        emojis = _check_guess(guess, target)
        session["history"].append((guess, emojis))
        session["attempts"] -= 1

        # Условие Победы
        if all(e == HIT for e in emojis):
            session["active"] = False

            board_text = _build_board(session, footer="")
            _edit_board(bot, session, board_text)

            if random.random() < 0.05:
                reward_text = (
                    f"🏆 *Шифр расшифрован.*\n\n"
                    f"Слово восстановлено: *{target.upper()}*\n\n"
                    f"📜 *Утерянная запись*\n\n{random.choice(RARE_RECORDS)}"
                )
            else:
                fact = random.choice(FACTS)
                reward_text = (
                    f"🏆 *Шифр расшифрован.*\n\n"
                    f"Слово восстановлено: *{target.upper()}*\n\n"
                    f"📚 *Фрагмент знаний*\n\n{fact}"
                )

            bot.send_message(chat_id, reward_text, parse_mode="Markdown")
            del SESSIONS[user_id]
            return

        # Условие Поражения
        if session["attempts"] == 0:
            session["active"] = False

            board_text = _build_board(session, footer="")
            _edit_board(bot, session, board_text)

            quote = random.choice(DEFEAT_QUOTES)
            bot.send_message(
                chat_id,
                f"📖 *Архив закрыл страницу.*\n\n"
                f"Загаданное слово: *{target.upper()}*\n\n"
                f"🕯 *Мысль Архива*\n\n{quote}",
                parse_mode="Markdown",
            )
            del SESSIONS[user_id]
            return

        # Игровой процесс продолжается
        board_text = _build_board(session)
        _edit_board(bot, session, board_text)

    # Игнорирование обычных слов вне активной сессии
    @bot.message_handler(
        func=lambda m: (
            m.text
            and m.from_user.id not in SESSIONS
            and m.text.strip().lower() not in (".шифр", ".вордл")
            and re.fullmatch(r"[а-яёА-ЯЁ]{3,12}", m.text.strip()) is not None
        )
    )
    def handle_cipher_after_game(message: Message):
        pass


# ---------------------------------------------------------------------------
# Утилита редактирования доски
# ---------------------------------------------------------------------------

def _edit_board(bot: TeleBot, session: dict, text: str) -> None:
    """Редактирует существующее сообщение игрового поля. При сбое отправляет новое."""
    try:
        bot.edit_message_text(
            text,
            chat_id=session["chat_id"],
            message_id=session["board_msg_id"],
            parse_mode="Markdown",
        )
    except Exception:
        msg = bot.send_message(session["chat_id"], text, parse_mode="Markdown")
        session["board_msg_id"] = msg.message_id
