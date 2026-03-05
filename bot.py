import telebot
import time
import sqlite3
import random
from datetime import datetime, timedelta
from config import BOT_TOKEN

bot = telebot.TeleBot(BOT_TOKEN)

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            money       INTEGER DEFAULT 0,
            exp         INTEGER DEFAULT 0,
            seeds       INTEGER DEFAULT 0,
            bait        INTEGER DEFAULT 0,
            last_daily  TEXT DEFAULT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def register_user(user_id, username):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
              (user_id, username))
    conn.commit()
    conn.close()

def update_daily(user_id, money, exp, seeds, bait, timestamp):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''
        UPDATE users SET
            money = money + ?,
            exp = exp + ?,
            seeds = seeds + ?,
            bait = bait + ?,
            last_daily = ?
        WHERE user_id = ?
    ''', (money, exp, seeds, bait, timestamp, user_id))
    conn.commit()
    conn.close()

def get_top_users(limit=15):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT username, money FROM users ORDER BY money DESC LIMIT ?', (limit,))
    top = c.fetchall()
    conn.close()
    return top

# ===== КОМАНДЫ =====

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Открой меню команд, чтобы узнать что тут есть."
    )

@bot.message_handler(commands=['daily'])
def cmd_daily(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    register_user(user_id, username)

    user = get_user(user_id)
    now = datetime.now()

    # Проверяем последнее получение
    if user and user[6]:  # last_daily
        last = datetime.fromisoformat(user[6])
        diff = now - last
        if diff < timedelta(hours=24):
            remaining = timedelta(hours=24) - diff
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            bot.send_message(
                message.chat.id,
                f"⏳ Следующая награда через {hours:02d}:{minutes:02d}"
            )
            return

    # Выдаём награду
    money = random.randint(100, 1000)
    exp   = random.randint(5, 20)
    seeds = random.randint(1, 3)
    bait  = random.randint(1, 3)

    update_daily(user_id, money, exp, seeds, bait, now.isoformat())

    bot.send_message(
        message.chat.id,
        f"🎁 Ежедневная награда 🎁\n\n"
        f"+ {money} 💵 Денег\n"
        f"+ {exp} 🌟 Опыта\n"
        f"+ {seeds} 🌱 Семян\n"
        f"+ {bait} 🪱 Наживок\n\n"
        f"⏳ Ожидай следующую награду через 24:00"
    )

@bot.message_handler(commands=['rating'])
def cmd_rating(message):
    top = get_top_users(15)
    if not top:
        bot.send_message(message.chat.id, "Рейтинг пока пуст!")
        return

    text = "🏆 Рейтинг игроков по деньгам 💵:\n\n"
    for i, (username, money) in enumerate(top, 1):
        text += f"{i}. {username} — {money} 💵\n"

    bot.send_message(message.chat.id, text)

# ===== ЗАПУСК =====
init_db()
print("Бот запущен!")
while True:
    try:
        bot.polling(non_stop=True)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(5)
