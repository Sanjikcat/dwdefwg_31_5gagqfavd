import os
import asyncio
from datetime import datetime
import mysql.connector
from mysql.connector import pooling
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ---------- Настройки ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6486579332"))

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Установи его в Railway → Variables.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- Пул соединений с MySQL ----------
dbconfig = {
    "host": os.getenv("MYSQLHOST", "localhost"),
    "user": os.getenv("MYSQLUSER", "root"),
    "password": os.getenv("MYSQLPASSWORD", ""),
    "database": os.getenv("MYSQLDATABASE", "railway"),
    "port": int(os.getenv("MYSQLPORT", "3306"))
}

pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **dbconfig)

# ---------- Утилита для запросов ----------
def execute_query(query, params=None, commit=False):
    conn = pool.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if commit:
            conn.commit()
    finally:
        cursor.close()
        conn.close()

# ---------- Создание таблиц ----------
execute_query("""
CREATE TABLE IF NOT EXISTS students (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10),
    is_premium BOOLEAN
)
""", commit=True)

execute_query("""
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    message TEXT,
    date DATETIME,
    type VARCHAR(20)
)
""", commit=True)

# ---------- Главное меню ----------
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🆘 Помощь")],
        [KeyboardButton(text="✉️ Сообщение админу")]
    ],
    resize_keyboard=True
)

# ---------- START ----------
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для студентов METU!\n\n"
        "/help — помощь\n"
        "/privacy — политика конфиденциальности\n"
        "/myid — ваш ID\n"
        "/letter текст — написать отделу",
        reply_markup=main_menu
    )

# ---------- HELP ----------
@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "🆘 Помощь:\n\n"
        "/start — главное меню\n"
        "/help — справка\n"
        "/privacy — политика конфиденциальности\n"
        "/myid — ваш Telegram ID\n"
        "/letter текст — написать админу"
    )

# ---------- PRIVACY ----------
@dp.message(Command("privacy"))
async def privacy(message: types.Message):
    await message.answer(
        "🔐 Политика конфиденциальности:\n"
        "1) Сохраняем ваш Telegram ID, имя и сообщения.\n"
        "2) Данные не передаются третьим лицам.\n"
        "3) Для удаления напишите /letter."
    )

# ---------- MYID ----------
@dp.message(Command("myid"))
async def myid(message: types.Message):
    user = message.from_user
    await message.answer(
        f"🆔 Ваш Telegram ID: `{user.id}`\n"
        f"👤 Username: @{user.username or 'нет'}",
        parse_mode="Markdown"
    )

# ---------- LETTER ----------
@dp.message(Command("letter"))
async def letter(message: types.Message):
    text = message.text.replace("/letter", "").strip()
    if not text:
        return await message.answer("❌ Напиши так: /letter текст")

    user = message.from_user
    execute_query(
        "INSERT INTO messages (user_id, message, date, type) VALUES (%s, %s, %s, %s)",
        (user.id, text, datetime.now(), "letter"),
        commit=True
    )

    await message.answer("✅ Письмо отправлено админу!")
    await bot.send_message(ADMIN_ID, f"📨 Письмо от @{user.username or 'Без ника'} ({user.id}):\n{text}")

# ---------- REPLY (только админ) ----------
@dp.message(Command("reply"))
async def reply(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ У вас нет прав использовать эту команду.")

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.answer("Используй: /reply user_id текст")

    user_id, text = int(args[1]), args[2]
    try:
        await bot.send_message(user_id, f"📩 Ответ от администрации:\n\n{text}")
        await message.answer("✅ Ответ отправлен")
    except:
        await message.answer("⚠ Не удалось отправить сообщение")

# ---------- ОБЩИЙ ХЭНДЛЕР (последний!) ----------
@dp.message(F.text)
async def forward_msg(message: types.Message):
    if message.text.startswith("/"):
        return  # команды не трогаем

    user = message.from_user

    execute_query("""
    INSERT INTO students (user_id, username, first_name, last_name, language_code, is_premium)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        username=VALUES(username),
        first_name=VALUES(first_name),
        last_name=VALUES(last_name),
        language_code=VALUES(language_code),
        is_premium=VALUES(is_premium)
    """, (
        user.id,
        user.username,
        user.first_name,
        user.last_name,
        user.language_code,
        1 if getattr(user, "is_premium", False) else 0
    ), commit=True)

    execute_query(
        "INSERT INTO messages (user_id, message, date, type) VALUES (%s, %s, %s, %s)",
        (user.id, message.text, datetime.now(), "message"),
        commit=True
    )

    await bot.send_message(
        ADMIN_ID,
        f"📩 Сообщение от @{user.username or 'Без ника'} ({user.id}):\n{message.text}"
    )

# ---------- Запуск ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
