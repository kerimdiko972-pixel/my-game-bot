# =============================================================================
#  memo_game.py — Модуль игры «Мозаика Памяти» для Telegram-бота
#  Команда запуска: .мемо  (или .память)
#
#  Подключение в bot.py (после создания bot):
#      from memo_game import register_memo_handlers
#      register_memo_handlers(bot)
#
#  Использует тот же data/facts.txt что и archie.py
# =============================================================================

import os
import random
import threading

from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

# ---------------------------------------------------------------------------
# Файл фактов (общий с archie.py)
# ---------------------------------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
FACTS_FILE = os.path.join(BASE_DIR, "data", "facts.txt")

FALLBACK_FACTS = [
    "Хамелеоны способны двигать глазами независимо друг от друга.",
    "Осьминоги имеют три сердца и голубую кровь.",
    "Мёд не портится — в египетских гробницах находили мёд возрастом 3000 лет.",
]

FACTS: list[str] = []

def reload_facts() -> None:
    """Перечитывает facts.txt. Вызывается автоматически при импорте."""
    global FACTS
    if not os.path.exists(FACTS_FILE):
        FACTS = FALLBACK_FACTS
        return
    with open(FACTS_FILE, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    FACTS = lines if lines else FALLBACK_FACTS

reload_facts()

# ---------------------------------------------------------------------------
# Константы игры
# ---------------------------------------------------------------------------
SIZE           = 5          # размер поля 5×5
MEMORIZE_TIME  = 15          # секунд на запоминание
PLAY_TIME      = 60         # секунд на восстановление

EMPTY  = "⬜"
COLORS = ["🟥", "🟦", "🟩", "🟨"]

# Цикл переключения при нажатии на клетку
COLOR_CYCLE = [EMPTY, "🟥", "🟦", "🟩", "🟨"]

# Редкие записи Архива (награда 5% при 100%)
RARE_RECORDS = [
    "«Мы пытались сохранить память в камне.\nКамень пережил нас, но не наши имена.»",
    "«Архив не помнит лиц. Только узоры, которые они оставили.»",
    "«Каждая утерянная запись — это мысль, которую никто не успел дочитать.»",
    "«Память — единственная библиотека, которую нельзя сжечь. Но можно забыть.»",
    "«Узор существовал до нас. Мы лишь пытаемся его повторить.»",
]

# ---------------------------------------------------------------------------
# Хранилище сессий  {user_id: session_dict}
# ---------------------------------------------------------------------------
SESSIONS: dict[int, dict] = {}

# ---------------------------------------------------------------------------
# Генерация и отображение поля
# ---------------------------------------------------------------------------

def _generate_grid() -> list[list[str]]:
    """Создаёт 5×5 сетку с 10–15 случайными цветными клетками."""
    grid = [[EMPTY] * SIZE for _ in range(SIZE)]
    colored_count = random.randint(10, 15)
    positions = random.sample(
        [(r, c) for r in range(SIZE) for c in range(SIZE)],
        colored_count,
    )
    for r, c in positions:
        grid[r][c] = random.choice(COLORS)
    return grid

def _grid_to_str(grid: list[list[str]]) -> str:
    """Превращает двумерный список в строку для отображения в сообщении."""
    return "\n".join("".join(row) for row in grid)

def _player_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Строит inline-клавиатуру из текущего состояния поля игрока."""
    session = SESSIONS[user_id]
    markup  = InlineKeyboardMarkup(row_width=SIZE)
    buttons = []
    for r in range(SIZE):
        for c in range(SIZE):
            cell = session["player_grid"][r][c]
            buttons.append(
                InlineKeyboardButton(cell, callback_data=f"memo_{r}_{c}")
            )
    markup.add(*buttons)
    return markup

# ---------------------------------------------------------------------------
# Подсчёт результата
# ---------------------------------------------------------------------------

def _calc_score(original: list[list[str]], player: list[list[str]]) -> int:
    matches = sum(
        1 for r in range(SIZE) for c in range(SIZE)
        if original[r][c] == player[r][c]
    )
    return round(matches / (SIZE * SIZE) * 100)

def _score_label(score: int) -> str:
    if score == 100: return "🏆 Идеальная память"
    if score >= 90:  return "🌟 Почти идеально"
    if score >= 75:  return "✨ Отличный результат"
    if score >= 50:  return "📖 Неплохо"
    if score >= 25:  return "🧩 Есть над чем поработать"
    return "🌫 Узор ускользнул из памяти"

# ---------------------------------------------------------------------------
# Регистрация обработчиков
# ---------------------------------------------------------------------------

def register_memo_handlers(bot: TeleBot) -> None:
    """Вызвать один раз из bot.py: register_memo_handlers(bot)"""

    # ------------------------------------------------------------------
    # Завершение игры (вызывается таймером или вручную)
    # ------------------------------------------------------------------
    def _finish_game(user_id: int, chat_id: int, timed_out: bool = False) -> None:
        session = SESSIONS.get(user_id)
        if not session or not session["active"]:
            return
        session["active"] = False

        # Отменяем таймер если завершение произошло раньше срока
        timer = session.get("timer")
        if timer and not timed_out:
            timer.cancel()

        original   = session["original_grid"]
        player     = session["player_grid"]
        score      = _calc_score(original, player)
        label      = _score_label(score)
        orig_str   = _grid_to_str(original)
        player_str = _grid_to_str(player)

        timeout_note = "⏳ Время истекло. Архив зафиксировал текущий результат.\n\n" if timed_out else ""

        result_text = (
            f"{timeout_note}"
            f"📊 *Проверка завершена*\n\n"
            f"🎯 Совпадение: *{score}%*\n"
            f"{label}\n\n"
            f"Оригинал:\n{orig_str}\n\n"
            f"Твой вариант:\n{player_str}"
        )

        # Редактируем сообщение с полем (убираем кнопки, показываем результат)
        play_msg_id = session.get("play_msg_id")
        if play_msg_id:
            try:
                bot.edit_message_text(
                    result_text,
                    chat_id=chat_id,
                    message_id=play_msg_id,
                    parse_mode="Markdown",
                )
            except Exception:
                bot.send_message(chat_id, result_text, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, result_text, parse_mode="Markdown")

        # Награда за 100%
        if score == 100:
            if random.random() < 0.05:
                rare = random.choice(RARE_RECORDS)
                bot.send_message(
                    chat_id,
                    f"🏆 *Идеальное восстановление*\n\n"
                    f"Архив признал точность твоей памяти.\n\n"
                    f"📜 *Утерянная запись Архива*\n\n{rare}",
                    parse_mode="Markdown",
                )
            else:
                fact = random.choice(FACTS)
                bot.send_message(
                    chat_id,
                    f"🏆 *Идеальное восстановление*\n\n"
                    f"Архив признал точность твоей памяти.\n\n"
                    f"📚 *Фрагмент знаний*\n{fact}",
                    parse_mode="Markdown",
                )

        if user_id in SESSIONS:
            del SESSIONS[user_id]

    # ------------------------------------------------------------------
    # Команда .мемо / .память
    # ------------------------------------------------------------------
    @bot.message_handler(
        func=lambda m: m.text and m.text.strip().lower() in (".мемо", ".память")
    )
    def cmd_memo(message: Message):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎨 Начать", callback_data="memo_start"))
        bot.send_message(
            message.chat.id,
            "🧠 *Мозаика Памяти*\n\n"
            "Архив покажет тебе краткий узор.\n\n"
            "Запомни расположение цветных клеток.\n\n"
            "После исчезновения рисунка тебе предстоит восстановить его по памяти.\n\n"
            f"⏳ Время запоминания: *{MEMORIZE_TIME} секунд*\n"
            f"⏳ Время восстановления: *{PLAY_TIME} секунд*\n"
            f"🎨 Размер поля: *{SIZE}×{SIZE}*",
            parse_mode="Markdown",
            reply_markup=markup,
        )

    # ------------------------------------------------------------------
    # Кнопка «🎨 Начать»
    # ------------------------------------------------------------------
    @bot.callback_query_handler(func=lambda call: call.data == "memo_start")
    def callback_memo_start(call: CallbackQuery):
        user_id = call.from_user.id
        chat_id = call.message.chat.id

        # Защита от двойной сессии
        if user_id in SESSIONS and SESSIONS[user_id]["active"]:
            bot.answer_callback_query(
                call.id,
                "🧠 Испытание памяти уже активно.\n"
                "Заверши текущую попытку прежде чем открывать новый узор.",
                show_alert=True,
            )
            return

        bot.answer_callback_query(call.id)

        grid = _generate_grid()

        SESSIONS[user_id] = {
            "original_grid": grid,
            "player_grid":   [[EMPTY] * SIZE for _ in range(SIZE)],
            "active":        True,
            "play_msg_id":   None,
            "chat_id":       chat_id,
            "first_click":   True,
            "timer":         None,
        }

        grid_str = _grid_to_str(grid)

        # Отправляем рисунок для запоминания
        mem_msg = bot.send_message(
            chat_id,
            f"🧠 *Запомни рисунок*\n\n"
            f"⏳ Осталось: *{MEMORIZE_TIME} секунд*\n\n"
            f"{grid_str}",
            parse_mode="Markdown",
        )

        # Через MEMORIZE_TIME секунд — удаляем и запускаем поле
        def _start_play():
            try:
                bot.delete_message(chat_id, mem_msg.message_id)
            except Exception:
                pass

            session = SESSIONS.get(user_id)
            if not session or not session["active"]:
                return

            play_msg = bot.send_message(
                chat_id,
                f"🎨 *Восстанови рисунок*\n\n"
                f"⏳ Осталось: *{PLAY_TIME} секунд*\n\n"
                f"Нажимай на клетки — они переключают цвет:\n"
                f"⬜ → 🟥 → 🟦 → 🟩 → 🟨 → ⬜",
                parse_mode="Markdown",
                reply_markup=_player_keyboard(user_id),
            )
            session["play_msg_id"] = play_msg.message_id

            # Запускаем таймер на 40 секунд
            t = threading.Timer(
                PLAY_TIME, _finish_game, args=(user_id, chat_id, True)
            )
            session["timer"] = t
            t.start()

        threading.Timer(MEMORIZE_TIME, _start_play).start()

    # ------------------------------------------------------------------
    # Нажатие на клетку поля
    # ------------------------------------------------------------------
    FIRST_CLICK_MSGS = [
        "📖 Архив наблюдает.",
        "🧠 Память восстанавливает детали.",
        "🎨 Символы возвращаются на свои места.",
        "📖 Ты воссоздаёшь забытый фрагмент.",
        "🧩 Рисунок постепенно собирается.",
    ]

    @bot.callback_query_handler(
        func=lambda call: (
            call.data.startswith("memo_")
            and call.data != "memo_start"
            and len(call.data.split("_")) == 3
        )
    )
    def callback_memo_cell(call: CallbackQuery):
        user_id = call.from_user.id
        session = SESSIONS.get(user_id)

        # Сессия не найдена или уже завершена
        if not session:
            bot.answer_callback_query(call.id, "📖 Этот узор уже закрыт Архивом.")
            return
        if not session["active"]:
            bot.answer_callback_query(call.id, "📖 Этот узор уже закрыт Архивом.")
            return

        # Парсим позицию
        _, r, c = call.data.split("_")
        r, c = int(r), int(c)

        # Переключаем цвет
        current    = session["player_grid"][r][c]
        idx        = COLOR_CYCLE.index(current)
        next_color = COLOR_CYCLE[(idx + 1) % len(COLOR_CYCLE)]
        session["player_grid"][r][c] = next_color

        # Сообщение при первом нажатии
        if session["first_click"]:
            session["first_click"] = False
            bot.answer_callback_query(call.id, random.choice(FIRST_CLICK_MSGS))
        else:
            bot.answer_callback_query(call.id)

        # Обновляем клавиатуру
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_player_keyboard(user_id),
            )
        except Exception:
            pass
