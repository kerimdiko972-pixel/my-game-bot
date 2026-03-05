import telebot
import time
from config import BOT_TOKEN

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def cmd_start(message):
    username = message.from_user.first_name
    bot.send_message(
        message.chat.id,
        f"Привет, {username}! 👋\n\n"
        "Открой меню команд, чтобы узнать что тут есть."
    )

print("Бот запущен!")
while True:
    try:
        bot.polling(non_stop=True)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(5)